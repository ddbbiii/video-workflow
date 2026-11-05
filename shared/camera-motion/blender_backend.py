"""Blender backend driver for shared camera-motion.

Resolves a Blender executable, exports per-shot trajectory views, launches a
headless scene script, then encodes PNG frames with the same FFmpeg settings as
the affine backend. Never silently falls back to affine.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

# Local imports work both as package sibling and script directory.
from camera_motion import progress, sample_matrix, view_at, write_json, probe, digest

SCENE_SCRIPT = Path(__file__).with_name("blender_scene.py")

ENGINE_VERSION = "blender-1.0"
_OWNED_LOCKS = {}

# Shared GPU lock plus the legacy Comfy lock guard.
_DEFAULT_GPU_LOCK_CANDIDATES = (
    Path(__file__).resolve().parents[2] / "work" / "cache" / "gpu.lock",
    Path(__file__).resolve().parents[2] / "runtime" / "comfy" / "cache" / "gpu.lock",
)


def _gpu_lock_path(plan: dict | None = None) -> Path:
    configured = (plan or {}).get("gpu_lock") or os.environ.get("CAMERA_MOTION_GPU_LOCK")
    if configured:
        return Path(configured)
    return _DEFAULT_GPU_LOCK_CANDIDATES[0]


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        # OpenProcess returns NULL if process is gone; use tasklist as portable check.
        try:
            out = subprocess.check_output(["tasklist", "/FI", f"PID eq {pid}"], text=True, stderr=subprocess.DEVNULL)
            return str(pid) in out
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def acquire_gpu_lock(plan: dict | None = None, owner: str = "camera-motion-blender", timeout_s: float = 3600.0) -> Path:
    """Acquire shared GPU lock for EEVEE / Cycles-GPU. Raises on timeout."""
    path = _gpu_lock_path(plan)
    legacy_guard = _DEFAULT_GPU_LOCK_CANDIDATES[1]
    if legacy_guard.exists():
        raise TimeoutError(f"legacy GPU lock exists: {legacy_guard}; inspect ownership before continuing")
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + timeout_s
    payload = {"owner": owner, "pid": os.getpid(), "token": uuid.uuid4().hex, "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    while True:
        if path.exists():
            # Another owner may still be writing JSON after exclusive creation.
            # Treat unknown or stale locks as occupied; recovery must be explicit.
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
                other = int(existing.get("pid") or 0)
            except Exception:
                other = 0
            if time.time() > deadline:
                raise TimeoutError(f"GPU lock occupied by pid={other or 'unknown'} at {path}; inspect lock ownership before recovery")
            time.sleep(min(2.0, max(.01, deadline - time.time())))
            continue
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
            _OWNED_LOCKS[str(path.resolve())] = payload['token']
            return path
        except FileExistsError:
            if time.time() > deadline:
                raise TimeoutError(f"GPU lock busy at {path}")
            time.sleep(0.5)


def release_gpu_lock(path: Path | None):
    if not path:
        return
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            key = str(path.resolve())
            token = _OWNED_LOCKS.get(key)
            if token and data.get("token") == token and int(data.get("pid") or 0) == os.getpid():
                path.unlink()
                _OWNED_LOCKS.pop(key, None)
    except Exception:
        pass



class BlenderUnavailable(RuntimeError):
    """Raised when backend=blender is requested but Blender cannot run."""


def resolve_blender_exe(plan: dict | None = None, explicit: str | Path | None = None) -> Path:
    """Resolve Blender executable without embedding machine-specific defaults in callers.

    Priority:
      1. explicit argument / CLI (if provided and missing -> hard fail, no fallthrough)
      2. plan['blender_exe'] (absolute, or relative to plan['_plan_dir'])
      3. env CAMERA_MOTION_BLENDER
      4. `blender` on PATH
    """
    if explicit:
        path = Path(explicit)
        if path.is_file():
            return path.resolve()
        raise BlenderUnavailable(f"Explicit Blender path not found: {path}")

    candidates: list[Path] = []
    if plan:
        configured = plan.get("blender_exe")
        if configured:
            path = Path(configured)
            if not path.is_absolute():
                base = Path(plan.get("_plan_dir") or ".")
                path = (base / path).resolve()
            if not path.is_file():
                raise BlenderUnavailable(f"Configured Blender path not found: {path}")
            return path.resolve()
    env = os.environ.get("CAMERA_MOTION_BLENDER")
    if env:
        candidates.append(Path(env))
    which = shutil.which("blender")
    if which:
        candidates.append(Path(which))

    tried = []
    for path in candidates:
        tried.append(str(path))
        if path.is_file():
            return path.resolve()
    raise BlenderUnavailable(
        "Blender executable not found. Set CAMERA_MOTION_BLENDER, pass --blender, "
        f"or plan['blender_exe']. Tried: {tried or ['<none>']}"
    )


def source_size_exif(path: Path) -> list[int]:
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        return list(image.size)


def build_views(shot: dict) -> list[list[float]]:
    return [view_at(shot, i).tolist() for i in range(shot["frames"])]


def build_matrices(shot: dict, sw: int, sh: int, width: int, height: int) -> list[list[list[float]]]:
    matrices = []
    for i in range(shot["frames"]):
        matrices.append(sample_matrix(view_at(shot, i), sw, sh, width, height).tolist())
    return matrices


def frame_paths(frames_dir: Path, count: int) -> list[Path]:
    return [frames_dir / f"frame_{i:05d}.png" for i in range(count)]


def valid_frame(path: Path, size=None) -> bool:
    try:
        with Image.open(path) as image:
            if image.format != "PNG" or (size is not None and image.size != tuple(size)):
                return False
            image.verify()
        with Image.open(path) as image:
            image.load()
        return True
    except (OSError, ValueError):
        return False


def complete_frames(frames_dir: Path, count: int, size=None) -> bool:
    paths = frame_paths(frames_dir, count)
    return all(valid_frame(p, size) for p in paths)


def first_missing_frame(frames_dir: Path, count: int, size=None) -> int:
    for i, path in enumerate(frame_paths(frames_dir, count)):
        if not valid_frame(path, size):
            return i
    return count


def encode_png_sequence(frames_dir: Path, count: int, output: Path, fps: int, width: int, height: int):
    """Encode lossless PNG frames with the same H.264 settings as affine render()."""
    part = output.with_name(output.stem + ".partial.mp4")
    pattern = str(frames_dir / "frame_%05d.png")
    with tempfile.TemporaryFile() as log:
        cmd = [
            "ffmpeg", "-v", "error", "-y",
            "-framerate", str(fps),
            "-i", pattern,
            "-frames:v", str(count),
            "-an",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(part),
        ]
        process = subprocess.Popen(cmd, stderr=log)
        if process.wait() != 0:
            log.seek(0)
            raise RuntimeError(log.read().decode(errors="replace") or "ffmpeg encode failed")
    data = probe(part)
    stream = data["streams"][0]
    if (
        len(data["streams"]) != 1
        or (stream["width"], stream["height"]) != (width, height)
        or stream["avg_frame_rate"] != f"{fps}/1"
        or int(stream["nb_frames"]) != count
    ):
        raise RuntimeError("Encoded Blender stream differs from planned frame count/size/fps")
    subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(part), "-f", "null", "-"], check=True, capture_output=True)
    part.replace(output)


def run_blender_job(blender_exe: Path, job_path: Path, log_path: Path) -> dict:
    if not SCENE_SCRIPT.is_file():
        raise BlenderUnavailable(f"Missing scene script: {SCENE_SCRIPT}")
    cmd = [
        str(blender_exe),
        "--background",
        "--factory-startup",
        "--python", str(SCENE_SCRIPT),
        "--",
        "--job", str(job_path),
    ]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        log.write("CMD: " + " ".join(cmd) + "\n")
        log.flush()
        proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, text=True)
    text = log_path.read_text(encoding="utf-8", errors="replace")
    if proc.returncode != 0 or "CAMERA_MOTION_BLENDER_DONE" not in text:
        raise RuntimeError(f"Blender job failed (code={proc.returncode}); see {log_path}")
    report_path = Path(json.loads(job_path.read_text(encoding="utf-8"))["report_path"])
    if not report_path.exists():
        raise RuntimeError(f"Blender report missing: {report_path}")
    return json.loads(report_path.read_text(encoding="utf-8"))


def render_shot(shot: dict, output: Path, settings: dict, plan: dict, blender_exe: Path, cache_root: Path) -> tuple[list, dict]:
    """Render one shot via Blender PNG sequence + FFmpeg. Returns (matrices, timing_info)."""
    width, height, fps = (settings[k] for k in ("width", "height", "fps"))
    source = Path(shot["source"])
    sw, sh = source_size_exif(source)
    views = build_views(shot)
    matrices = build_matrices(shot, sw, sh, width, height)

    samples = plan.get("blender_samples", 4)
    interpolation = plan.get("blender_interpolation", "Linear")
    if type(samples) is not int or not 1 <= samples <= 4096:
        raise ValueError("blender_samples must be an integer from 1 to 4096")
    if interpolation not in ("Closest", "Linear", "Cubic"):
        raise ValueError("Unsupported blender_interpolation")
    engine = plan.get("blender_engine", "CYCLES")
    use_gpu = bool(plan.get("blender_use_gpu", False))
    if engine not in ("CYCLES", "BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        raise ValueError(f"Unsupported Blender render engine {engine!r}")
    cache_spec = {"source_hash": digest(source), "views": views, "size": [width, height],
                  "engine": engine, "gpu": use_gpu, "samples": samples, "interpolation": interpolation,
                  "scene_hash": digest(SCENE_SCRIPT), "driver_hash": digest(__file__),
                  "exe": str(blender_exe.resolve()), "exe_mtime": blender_exe.stat().st_mtime_ns,
                  "exe_size": blender_exe.stat().st_size}
    import hashlib
    cache_key = hashlib.sha256(json.dumps(cache_spec, sort_keys=True).encode()).hexdigest()
    shot_cache = cache_root / shot["id"] / cache_key
    frames_dir = shot_cache / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    job_path = shot_cache / "job.json"
    report_path = shot_cache / "blender_report.json"
    log_path = shot_cache / "blender.log"
    write_json(shot_cache / "cache_spec.json", cache_spec)
    prepared = shot_cache / "source.png"
    if not prepared.exists():
        with Image.open(source) as image:
            ImageOps.exif_transpose(image).convert("RGB").save(prepared)

    timing = {"init_s": 0.0, "render_s": 0.0, "encode_s": 0.0, "frames": shot["frames"]}
    t0 = time.perf_counter()

    needs_gpu = use_gpu or str(engine).startswith("BLENDER_EEVEE")

    if not complete_frames(frames_dir, shot["frames"], [width, height]):
        start = first_missing_frame(frames_dir, shot["frames"], [width, height])
        job = {
            "image": str(prepared.resolve()),
            "width": width,
            "height": height,
            "source_size": [sw, sh],
            "views": views,
            "frames_dir": str(frames_dir.resolve()),
            "report_path": str(report_path.resolve()),
            "start_frame": start,
            "engine": engine,
            "use_gpu": use_gpu,
            "samples": samples,
            "interpolation": interpolation,
        }
        write_json(job_path, job)
        timing["init_s"] = time.perf_counter() - t0
        t1 = time.perf_counter()
        lock_path = None
        try:
            if needs_gpu:
                lock_path = acquire_gpu_lock(plan, owner=f"camera-motion:{shot['id']}")
                timing["gpu_lock"] = str(lock_path)
            report = run_blender_job(blender_exe, job_path, log_path)
        finally:
            release_gpu_lock(lock_path)
        timing["render_s"] = time.perf_counter() - t1
        timing["blender_report"] = report
    else:
        timing["init_s"] = time.perf_counter() - t0
        timing["cache_hit"] = True
        if report_path.exists():
            timing["blender_report"] = json.loads(report_path.read_text(encoding="utf-8"))

    if not complete_frames(frames_dir, shot["frames"], [width, height]):
        missing = first_missing_frame(frames_dir, shot["frames"], [width, height])
        raise RuntimeError(f"Frame cache incomplete for {shot['id']} at index {missing}")

    t2 = time.perf_counter()
    encode_png_sequence(frames_dir, shot["frames"], output, fps, width, height)
    timing["encode_s"] = time.perf_counter() - t2
    timing["total_s"] = time.perf_counter() - t0
    timing["frames_dir"] = str(frames_dir.resolve())
    timing["cache_key"] = cache_key
    timing["avg_frame_s"] = timing["render_s"] / shot["frames"] if shot["frames"] and not timing.get("cache_hit") else None
    return matrices, timing


def trajectory_payload(shot: dict, matrices: list, sw: int, sh: int) -> dict:
    return {
        "coordinate_system": "source_pixels_after_exif_top_left_origin",
        "source_size": [sw, sh],
        "inverse_sample_matrices": matrices,
        "shot": shot,
        "backend": "blender",
        "adjacent_frame_transform": "inv(P_next) @ P_current maps output pixel coordinates from frame i into frame i+1 output coordinates",
    }
