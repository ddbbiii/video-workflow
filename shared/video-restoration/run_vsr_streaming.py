"""RealBasicVSR single-clip runner (memory-bounded, spatially tiled, CLI driven).

Same model / spatial overlap-weighted tiling / FFmpeg encode path as the accepted
c04 run (20261007-vsr-baseline-c04-spatial-full); only configuration, safety
gates, failure bookkeeping, VRAM policy and audio handling were changed.

Resume is NOT supported: a failed run keeps its directory and manifest
(status=failed) and must be re-run in a NEW --output-dir (new run-id).

Exit codes: 0 ok (QA not fail) | 1 runtime failure (manifest status=failed)
            2 config/validation rejected | 3 output dir exists
            4 GPU lock busy | 5 run completed but QA status=fail
"""
import argparse
import datetime
import gc
import json
import logging
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import traceback
from fractions import Fraction
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
DEFAULT_MODEL = "damo/cv_realbasicvsr_video-super-resolution_videolq"
DEFAULT_LOCK = PROJECT / "shared" / "work" / "cache" / "gpu.lock"
LEGACY_LOCK = PROJECT / "shared" / "runtime" / "comfy" / "cache" / "gpu.lock"
FFMPEG_FALLBACK_DIR = Path(r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages"
                           r"\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe"
                           r"\ffmpeg-8.1.2-full_build-shared\bin")
SCALE = 4
VERIFIED_TILE = (640, 352)   # (w, h) input pixels, verified on RTX 5060 Ti 16GB
FALLBACK_TILE = (320, 176)
AUTO_TILE_MIN_USABLE_GB = 6.0  # usable = free - reserve; below this use FALLBACK_TILE
MIN_TILE = 64

EXIT_OK, EXIT_RUNTIME, EXIT_CONFIG, EXIT_OUTPUT_EXISTS, EXIT_LOCK_BUSY, EXIT_QA_FAIL = 0, 1, 2, 3, 4, 5
INJECT_CHOICES = ("none", "model_load", "encode", "oom_once", "oom_twice")


class ConfigError(Exception):
    def __init__(self, message, code=EXIT_CONFIG, stage="validate"):
        super().__init__(message)
        self.code = code
        self.stage = stage


class LockBusy(Exception):
    pass


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def parse_size(text, what):
    try:
        w, h = [int(v) for v in text.lower().replace(",", "x").split("x")]
    except Exception:
        raise ConfigError(f"{what} must look like WIDTHxHEIGHT, got {text!r}", stage="validate_args")
    return w, h


def find_tool(name, override):
    if override:
        p = Path(override)
        if not p.is_file():
            raise ConfigError(f"{name} not found at {override}", stage="validate_tools")
        return str(p)
    found = shutil.which(name)
    if found:
        return found
    fallback = FFMPEG_FALLBACK_DIR / f"{name}.exe"
    if fallback.is_file():
        return str(fallback)
    raise ConfigError(f"{name} not found on PATH or at {FFMPEG_FALLBACK_DIR}", stage="validate_tools")


def probe(path, ffprobe, what):
    proc = subprocess.run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise ConfigError(f"{what} is not a readable media file: {proc.stderr.strip()[:300]}", stage="probe_input")
    data = json.loads(proc.stdout or "{}")
    streams = data.get("streams", [])
    videos = [s for s in streams if s.get("codec_type") == "video"]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    if not videos:
        raise ConfigError(f"{what} has no video stream", stage="probe_input")
    v = videos[0]
    rate = v.get("r_frame_rate") or v.get("avg_frame_rate") or "0/1"
    fps = Fraction(rate) if rate != "0/0" else Fraction(0)
    if fps <= 0:
        raise ConfigError(f"{what} has no valid frame rate ({rate})", stage="probe_input")
    nb = int(v["nb_frames"]) if str(v.get("nb_frames", "")).isdigit() else None
    duration = float(data.get("format", {}).get("duration", v.get("duration", 0.0)) or 0.0)
    if nb is None:
        nb = int(round(duration * float(fps)))
    return {"path": str(path), "width": int(v["width"]), "height": int(v["height"]),
            "fps": f"{fps.numerator}/{fps.denominator}", "fps_float": float(fps), "frames": nb,
            "duration": duration, "video_codec": v.get("codec_name"), "pix_fmt": v.get("pix_fmt"),
            "video_streams": len(videos), "audio_streams": len(audios),
            "audio": [{"codec": a.get("codec_name"), "channels": a.get("channels"),
                       "sample_rate": a.get("sample_rate"), "duration": float(a.get("duration", 0) or 0)}
                      for a in audios]}


def check_first_frame_decodes(path, ffmpeg):
    proc = subprocess.run([ffmpeg, "-v", "error", "-i", str(path), "-frames:v", "1", "-f", "null", "-"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise ConfigError(f"input video is not decodable: {proc.stderr.strip()[:300]}", stage="probe_input")


def file_stat(path):
    st = Path(path).stat()
    return {"path": str(path), "bytes": st.st_size,
            "mtime": datetime.datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(timespec="seconds")}


def nvidia_smi():
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free",
                              "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=20)
        name, total, used, free = [v.strip() for v in out.stdout.strip().splitlines()[0].split(",")]
        return {"name": name, "total_mib": int(total), "used_mib": int(used), "free_mib": int(free)}
    except Exception as exc:  # informational only
        return {"error": repr(exc)}


def ffmpeg_version(ffmpeg):
    try:
        return subprocess.run([ffmpeg, "-version"], capture_output=True, text=True).stdout.splitlines()[0]
    except Exception as exc:
        return repr(exc)


def pkg_version(name):
    try:
        return metadata.version(name)
    except Exception:
        return None


def build_parser():
    p = argparse.ArgumentParser(
        description="RealBasicVSR streaming x4 restoration of ONE clip -> raw + delivery MP4, "
                    "manifest.json, run.log, then QA (qa_single_vsr.py). No resume: failed runs need a new --output-dir.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("--input", required=True, help="source video (absolute path)")
    p.add_argument("--baseline", default=None, help="optional Lanczos baseline video for QA comparison / fallback")
    p.add_argument("--output-dir", required=True, help="NEW run directory; must not exist; parent must exist")
    p.add_argument("--output-size", default="1920x1080", help="delivery size WxH (Lanczos downscale of x4 output)")
    p.add_argument("--model", default=DEFAULT_MODEL, help="ModelScope model id")
    p.add_argument("--tile-size", default="auto",
                   help="spatial tile WxH in INPUT pixels (multiples of 8, >=64) or 'auto' "
                        "(640x352 if free VRAM - reserve >= %.0f GB, else 320x176)" % AUTO_TILE_MIN_USABLE_GB)
    p.add_argument("--overlap", type=int, default=32, help="tile overlap in input pixels (0 <= overlap < min(tile)/2)")
    p.add_argument("--chunk-size", type=int, default=1, help="temporal chunk size in frames (1..64)")
    p.add_argument("--max-frames", type=int, default=0, help="process only the first N frames (0 = all); for smoke tests")
    p.add_argument("--drop-audio", action="store_true", help="explicitly drop the source audio (default: keep it)")
    p.add_argument("--dry-run", action="store_true", help="validate + probe + print plan only; no model, no GPU, no run dir")
    p.add_argument("--shot-id", default=None, help="shot id used in output names (default: input file stem)")
    p.add_argument("--run-id", default=None, help="run id recorded in manifest (default: output dir name)")
    p.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto", help="inference device")
    p.add_argument("--reserve-gb", type=float, default=2.0, help="VRAM safety reserve for auto tile selection")
    p.add_argument("--crf", type=int, default=14, help="libx264 CRF of delivery file")
    p.add_argument("--preset", default="slow", help="libx264 preset of delivery file")
    p.add_argument("--lock-path", default=str(DEFAULT_LOCK), help="shared GPU lock file (exclusive create)")
    p.add_argument("--lock-owner", default="zhumian-vsr-rerun", help="owner written into the GPU lock")
    p.add_argument("--ffmpeg", default=None, help="ffmpeg executable (default: PATH, then WinGet Gyan build)")
    p.add_argument("--ffprobe", default=None, help="ffprobe executable (default: PATH, then WinGet Gyan build)")
    p.add_argument("--no-qa", action="store_true", help="do not run qa_single_vsr.py after a completed run")
    p.add_argument("--qa-compare", default=None, help="extra video (e.g. previous VSR) passed to QA as --compare-vsr")
    p.add_argument("--inject-failure", choices=INJECT_CHOICES, default="none",
                   help="TEST ONLY: simulate model-load failure, encode failure, or CUDA OOM (once/twice)")
    return p


def validate(args):
    """Static checks; nothing is created here."""
    tools = {"ffmpeg": find_tool("ffmpeg", args.ffmpeg), "ffprobe": find_tool("ffprobe", args.ffprobe)}
    if args.tile_size.lower() == "auto":
        tile = None
        min_tile = min(FALLBACK_TILE)
    else:
        tile = parse_size(args.tile_size, "--tile-size")
        if any(v < MIN_TILE or v % 8 for v in tile):
            raise ConfigError(f"--tile-size values must be multiples of 8 and >= {MIN_TILE}, got {args.tile_size}",
                              stage="validate_args")
        min_tile = min(tile)
    if args.overlap < 0 or args.overlap * 2 >= min_tile:
        raise ConfigError(f"--overlap must satisfy 0 <= overlap < {min_tile}/2, got {args.overlap}", stage="validate_args")
    if not 1 <= args.chunk_size <= 64:
        raise ConfigError(f"--chunk-size must be 1..64, got {args.chunk_size}", stage="validate_args")
    if args.max_frames < 0:
        raise ConfigError("--max-frames must be >= 0", stage="validate_args")
    if args.reserve_gb < 0:
        raise ConfigError("--reserve-gb must be >= 0", stage="validate_args")
    out_w, out_h = parse_size(args.output_size, "--output-size")
    if out_w <= 0 or out_h <= 0 or out_w % 2 or out_h % 2:
        raise ConfigError("--output-size values must be positive even numbers", stage="validate_args")
    if not args.model.strip():
        raise ConfigError("--model must not be empty", stage="validate_args")

    out_dir = Path(args.output_dir).resolve()
    if out_dir.exists():
        raise ConfigError(f"output dir already exists (refusing to touch it): {out_dir}",
                          code=EXIT_OUTPUT_EXISTS, stage="validate_output")
    if not out_dir.parent.is_dir():
        raise ConfigError(f"parent of output dir does not exist: {out_dir.parent}", stage="validate_output")

    inp = Path(args.input).resolve()
    if not inp.is_file():
        raise ConfigError(f"input missing: {inp}", stage="validate_input")
    info = probe(inp, tools["ffprobe"], "input")
    check_first_frame_decodes(inp, tools["ffmpeg"])
    baseline = None
    if args.baseline:
        b = Path(args.baseline).resolve()
        if not b.is_file():
            raise ConfigError(f"baseline missing: {b}", stage="validate_baseline")
        baseline = {"path": str(b), "probe": probe(b, tools["ffprobe"], "baseline"), "stat": file_stat(b)}
    compare = None
    if args.qa_compare:
        c = Path(args.qa_compare).resolve()
        if not c.is_file():
            raise ConfigError(f"--qa-compare file missing: {c}", stage="validate_args")
        compare = str(c)

    expected_frames = min(info["frames"], args.max_frames) if args.max_frames else info["frames"]
    expected_duration = expected_frames / info["fps_float"]
    if info["audio_streams"] and args.drop_audio:
        audio_policy = "drop"
    elif info["audio_streams"]:
        audio_policy = "preserve"
    else:
        audio_policy = "none"
    shot = args.shot_id or inp.stem
    raw_name = f"{shot}-realbasicvsr-raw-{info['width'] * SCALE}x{info['height'] * SCALE}.mp4"
    hq_name = f"{shot}-realbasicvsr-{out_w}x{out_h}.mp4"
    return {
        "run_id": args.run_id or out_dir.name, "shot_id": shot, "input": str(inp), "input_probe": info,
        "input_stat": file_stat(inp), "baseline": baseline, "qa_compare": compare,
        "output_dir": str(out_dir), "output_size": [out_w, out_h], "model": args.model,
        "tile_request": "auto" if tile is None else {"w": tile[0], "h": tile[1]}, "overlap": args.overlap,
        "chunk_size": args.chunk_size, "max_frames": args.max_frames, "expected_frames": expected_frames,
        "expected_duration_s": round(expected_duration, 6), "drop_audio": bool(args.drop_audio),
        "audio_policy": audio_policy, "device_request": args.device, "reserve_gb": args.reserve_gb,
        "crf": args.crf, "preset": args.preset, "lock_path": str(Path(args.lock_path).resolve()),
        "legacy_lock_path": str(LEGACY_LOCK), "lock_owner": args.lock_owner, "tools": tools,
        "inject_failure": args.inject_failure, "run_qa": not args.no_qa,
        "outputs": {"raw": str(out_dir / raw_name), "delivery": str(out_dir / hq_name),
                    "manifest": str(out_dir / "manifest.json"), "log": str(out_dir / "run.log")},
        "resume_supported": False,
    }


def encode_command(cfg, raw_path, frames_done):
    ff = cfg["tools"]["ffmpeg"]
    out_w, out_h = cfg["output_size"]
    cmd = [ff, "-v", "error", "-n", "-i", raw_path]
    if cfg["audio_policy"] == "preserve":
        if cfg["max_frames"] and frames_done < cfg["input_probe"]["frames"]:
            # smoke/partial run: trim source audio to the processed duration
            cmd += ["-t", f"{frames_done / cfg['input_probe']['fps_float']:.6f}"]
        cmd += ["-i", cfg["input"], "-map", "0:v:0", "-map", "1:a:0"]
    else:
        cmd += ["-map", "0:v:0"]
    vcodec = "libx264_INJECTED_ENCODE_FAILURE" if cfg["inject_failure"] == "encode" else "libx264"
    cmd += ["-vf", f"scale={out_w}:{out_h}:flags=lanczos,setsar=1", "-c:v", vcodec, "-preset", cfg["preset"],
            "-crf", str(cfg["crf"]), "-pix_fmt", "yuv420p"]
    cmd += ["-c:a", "aac", "-b:a", "192k"] if cfg["audio_policy"] == "preserve" else ["-an"]
    cmd += ["-movflags", "+faststart", cfg["outputs"]["delivery"]]
    return cmd


class Manifest:
    def __init__(self, path):
        self.path = Path(path)
        self.data = {}

    def update(self, **kw):
        self.data.update(kw)
        self.data["updated"] = now_iso()
        tmp = self.path.with_name(self.path.name + ".tmp")
        payload = json.dumps(self.data, ensure_ascii=False, indent=2)
        for attempt in range(10):
            try:
                tmp.write_text(payload, encoding="utf-8")
                os.replace(tmp, self.path)
                return
            except PermissionError:  # Windows: a reader may hold the file briefly
                time.sleep(0.2 * (attempt + 1))
        raise RuntimeError(f"cannot atomically write {self.path}")


class GpuLock:
    """Project mutex: refuse if legacy comfy lock exists; exclusive-create shared/work/cache/gpu.lock;
    only ever remove a lock whose pid+token are ours. A hard-killed process leaves its lock:
    operator must confirm the pid is gone before removing it by hand (never done by this script)."""

    def __init__(self, path, legacy, owner, run_dir):
        self.path, self.legacy, self.owner, self.run_dir = Path(path), Path(legacy), owner, run_dir
        self.token = f"{os.getpid()}-{time.time_ns()}"
        self.held = False

    def acquire(self):
        if self.legacy.exists():
            raise LockBusy(f"legacy GPU lock exists: {self.legacy}: {self.legacy.read_text(encoding='utf-8', errors='replace')[:500]}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.path.open("x", encoding="utf-8") as fh:
                json.dump({"owner": self.owner, "pid": os.getpid(), "token": self.token, "host": socket.gethostname(),
                           "started": now_iso(), "run_dir": self.run_dir,
                           "cleanup_policy": "released by owning process in finally; stale lock after hard kill "
                                             "must be checked (pid alive?) and removed manually"}, fh,
                          ensure_ascii=False)
        except FileExistsError:
            raise LockBusy(f"GPU lock exists: {self.path}: {self.path.read_text(encoding='utf-8', errors='replace')[:500]}")
        self.held = True
        return self.read()

    def read(self):
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def release(self):
        if not self.held:
            return {"released": False, "reason": "not held"}
        data = self.read()
        if data and data.get("pid") == os.getpid() and data.get("token") == self.token:
            self.path.unlink()
            self.held = False
            return {"released": True, "lock_exists_after": self.path.exists()}
        return {"released": False, "reason": f"lock content not ours, left untouched: {data}"}


def _starts(length, tile, overlap):
    if tile >= length:
        return [0]
    step = max(1, tile - overlap)
    values = list(range(0, length - tile + 1, step))
    if values[-1] != length - tile:
        values.append(length - tile)
    return values


def tile_layout(width, height, tile_w, tile_h, overlap):
    return {"xs": _starts(width, tile_w, overlap), "ys": _starts(height, tile_h, overlap)}


class Runner:
    def __init__(self, cfg, lock):
        self.cfg = cfg
        self.lock = lock
        self.out = Path(cfg["output_dir"])
        self.manifest = Manifest(cfg["outputs"]["manifest"])
        self.stage = "init"
        self.frames_done = 0
        self.oom_injections_left = {"oom_once": 1, "oom_twice": 2}.get(cfg["inject_failure"], 0)
        self.downgraded = False
        self.tile_history = []
        self.log = logging.getLogger("vsr")

    def setup_logging(self):
        self.log.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        fh = logging.FileHandler(self.cfg["outputs"]["log"], encoding="utf-8")
        fh.setFormatter(fmt)
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        self.log.addHandler(fh)
        self.log.addHandler(sh)

    def set_stage(self, stage):
        self.stage = stage
        self.log.info("stage=%s", stage)
        self.manifest.update(stage=stage)

    def execute(self, lock_info):
        self.setup_logging()
        started = time.monotonic()
        try:
            # first manifest write happens before any heavy import / model work
            self.manifest.update(
                status="running", stage="init", started=now_iso(), config=self.cfg, lock=lock_info,
                frames_completed=0, total_frames=self.cfg["expected_frames"], progress=0.0,
                log=self.cfg["outputs"]["log"], visual_qa="pending_review", resume_supported=False,
                failure_policy="no resume: rerun in a new run directory")
            import numpy as np  # noqa: F401
            import cv2
            import torch
            self.manifest.update(
                environment={"host": socket.gethostname(), "python": sys.version, "executable": sys.executable,
                             "platform": platform.platform(), "torch": torch.__version__,
                             "torch_cuda": torch.version.cuda, "opencv": cv2.__version__,
                             "numpy": pkg_version("numpy"), "modelscope": pkg_version("modelscope"),
                             "ffmpeg": ffmpeg_version(self.cfg["tools"]["ffmpeg"]), "gpu_nvidia_smi": nvidia_smi()})
            self.log.info("resolved config:\n%s", json.dumps(self.cfg, ensure_ascii=False, indent=2))
            self._run(started)
            return EXIT_OK
        except BaseException as exc:  # record every failure, then exit non-zero
            tb = traceback.format_exc()
            self.log.error("FAILED at stage=%s: %s: %s\n%s", self.stage, type(exc).__name__, exc, tb)
            try:
                self.manifest.update(status="failed", failed_stage=self.stage, error_type=type(exc).__name__,
                                     error_summary=str(exc)[:1000], traceback_tail=tb[-4000:],
                                     frames_completed=self.frames_done, finished=now_iso(),
                                     elapsed_s=round(time.monotonic() - started, 1))
            except Exception as mexc:
                self.log.error("could not write failed manifest: %r", mexc)
            return EXIT_RUNTIME

    def _device(self, torch):
        req = self.cfg["device_request"]
        if req == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("--device cuda requested but CUDA is not available")
        if req == "cpu" or (req == "auto" and not torch.cuda.is_available()):
            return torch.device("cpu")
        return torch.device("cuda")

    def _select_tiles(self, torch, device):
        req = self.cfg["tile_request"]
        info = {"policy": "explicit" if req != "auto" else "auto"}
        if device.type == "cuda":
            free, total = torch.cuda.mem_get_info(device)
            info.update(free_gb=round(free / 2 ** 30, 2), total_gb=round(total / 2 ** 30, 2),
                        reserve_gb=self.cfg["reserve_gb"])
        if req != "auto":
            tile = (req["w"], req["h"])
        elif device.type != "cuda":
            tile = FALLBACK_TILE
            info["reason"] = "cpu device"
        else:
            usable = info["free_gb"] - self.cfg["reserve_gb"]
            info["usable_gb"] = round(usable, 2)
            if usable >= AUTO_TILE_MIN_USABLE_GB:
                tile, info["reason"] = VERIFIED_TILE, f"usable {usable:.2f} GB >= {AUTO_TILE_MIN_USABLE_GB} GB"
            elif usable >= 1.0:
                tile, info["reason"] = FALLBACK_TILE, f"usable {usable:.2f} GB < {AUTO_TILE_MIN_USABLE_GB} GB"
            else:
                raise RuntimeError(f"not enough free VRAM: free {info['free_gb']} GB, reserve {self.cfg['reserve_gb']} GB")
        if self.cfg["overlap"] * 2 >= min(tile):
            raise RuntimeError(f"overlap {self.cfg['overlap']} too large for tile {tile}")
        info["selected"] = {"w": tile[0], "h": tile[1], "overlap": self.cfg["overlap"]}
        return tile, info

    def _blend_window(self, torch, height, width, overlap, device):
        edge = max(1, overlap)
        wy = torch.ones(height, device=device)
        wx = torch.ones(width, device=device)
        ramp_y = torch.linspace(1.0 / (edge + 1), 1.0, edge, device=device)
        ramp_x = torch.linspace(1.0 / (edge + 1), 1.0, edge, device=device)
        wy[:edge] = ramp_y
        wy[-edge:] = torch.flip(ramp_y, dims=[0])
        wx[:edge] = ramp_x
        wx[-edge:] = torch.flip(ramp_x, dims=[0])
        return (wy[:, None] * wx[None, :])[None, None]

    def _infer_tiles(self, torch, model, tensor, device, tile_w, tile_h):
        overlap = self.cfg["overlap"]
        _, frames, channels, height, width = tensor.shape
        out_h, out_w = height * SCALE, width * SCALE
        accum = torch.zeros((1, frames, channels, out_h, out_w), device=device)
        weights = torch.zeros((1, frames, 1, out_h, out_w), device=device)
        layout = tile_layout(width, height, tile_w, tile_h, overlap)
        with torch.inference_mode():
            for y in layout["ys"]:
                for x in layout["xs"]:
                    if self.oom_injections_left > 0:
                        self.oom_injections_left -= 1
                        raise getattr(torch.cuda, "OutOfMemoryError", RuntimeError)(
                            "CUDA out of memory. (INJECTED test failure)")
                    tile = tensor[:, :, :, y:y + min(tile_h, height), x:x + min(tile_w, width)]
                    th, tw = tile.shape[-2:]
                    pad_h = (8 - th % 8) % 8
                    pad_w = (8 - tw % 8) % 8
                    if pad_h or pad_w:
                        tile = torch.nn.functional.pad(tile, (0, pad_w, 0, pad_h), mode="reflect")
                    result = model._inference_forward(tile)["output"].clamp(0, 1)
                    result = result[..., :th * SCALE, :tw * SCALE]
                    window = self._blend_window(torch, th * SCALE, tw * SCALE, overlap * SCALE, device)
                    oy, ox = y * SCALE, x * SCALE
                    accum[..., oy:oy + th * SCALE, ox:ox + tw * SCALE] += result * window
                    weights[..., oy:oy + th * SCALE, ox:ox + tw * SCALE] += window
                    del tile, result, window
        return accum / weights.clamp_min(1e-6)

    @staticmethod
    def _is_oom(torch, exc):
        oom_type = getattr(torch.cuda, "OutOfMemoryError", None)
        return (oom_type is not None and isinstance(exc, oom_type)) or "out of memory" in str(exc).lower()

    def _run(self, started):
        import cv2
        import numpy as np
        import torch
        cfg = self.cfg
        if cfg["max_frames"]:
            self.log.info("partial run: max_frames=%d", cfg["max_frames"])

        self.set_stage("preflight_decode")
        proc = subprocess.run([cfg["tools"]["ffmpeg"], "-v", "error", "-i", cfg["input"], "-f", "null", "-"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0 or proc.stderr.strip():
            raise RuntimeError(f"input full decode failed: {proc.stderr.strip()[:500]}")

        self.set_stage("model_load")
        device = self._device(torch)
        if cfg["inject_failure"] == "model_load":
            raise RuntimeError("INJECTED model load failure (test)")
        from modelscope.pipelines import pipeline
        from modelscope.utils.constant import Tasks
        pipe = pipeline(Tasks.video_super_resolution, model=cfg["model"])
        # ModelScope may leave the wrapper on CPU even when CUDA is visible.
        pipe.model.to(device)
        pipe.model.eval()
        gpu = {"device": str(device)}
        if device.type == "cuda":
            props = torch.cuda.get_device_properties(device)
            gpu.update(name=props.name, total_gb=round(props.total_memory / 2 ** 30, 2))
            torch.cuda.reset_peak_memory_stats(device)
        self.manifest.update(device=gpu)

        self.set_stage("select_tiles")
        tile, tile_info = self._select_tiles(torch, device)
        tile_w, tile_h = tile
        in_w, in_h = cfg["input_probe"]["width"], cfg["input_probe"]["height"]
        self.tile_history.append({"from_frame": 0, "w": tile_w, "h": tile_h, "overlap": cfg["overlap"],
                                  "layout": tile_layout(in_w, in_h, tile_w, tile_h, cfg["overlap"])})
        self.manifest.update(tile_selection=tile_info, tiles_final={"w": tile_w, "h": tile_h, "overlap": cfg["overlap"]},
                             tile_history=self.tile_history, oom_downgrade=None)
        self.log.info("tiles: %s", json.dumps(tile_info))

        self.set_stage("inference")
        infer_started = time.monotonic()
        cap = cv2.VideoCapture(cfg["input"])
        if not cap.isOpened():
            raise RuntimeError("cv2 cannot open input")
        fps = cfg["input_probe"]["fps_float"]
        raw_path = cfg["outputs"]["raw"]
        writer = None
        limit = cfg["expected_frames"]
        chunk_index = 0
        try:
            while self.frames_done < limit:
                chunk = []
                while len(chunk) < cfg["chunk_size"] and self.frames_done + len(chunk) < limit:
                    ok, frame = cap.read()
                    if not ok:
                        break
                    chunk.append(frame)
                if not chunk:
                    break
                t0 = time.monotonic()
                first = self.frames_done
                rgb = np.stack([f[:, :, ::-1] for f in chunk]).astype(np.float32) / 255.0
                tensor = torch.from_numpy(rgb).permute(0, 3, 1, 2).unsqueeze(0).to(device)
                while True:
                    try:
                        output = self._infer_tiles(torch, pipe.model, tensor, device, tile_w, tile_h).cpu()
                        break
                    except Exception as exc:
                        if not self._is_oom(torch, exc):
                            raise
                        gc.collect()
                        if device.type == "cuda":
                            torch.cuda.empty_cache()
                        if self.downgraded:
                            raise RuntimeError(f"CUDA OOM again after the single allowed downgrade "
                                               f"(tile {tile_w}x{tile_h}, frames {first}-{first + len(chunk) - 1}); stopping") from exc
                        new_w, new_h = max(MIN_TILE, tile_w // 2 // 8 * 8), max(MIN_TILE, tile_h // 2 // 8 * 8)
                        if cfg["overlap"] * 2 >= min(new_w, new_h) or (new_w, new_h) == (tile_w, tile_h):
                            raise RuntimeError(f"CUDA OOM and tile {tile_w}x{tile_h} cannot be halved further") from exc
                        self.downgraded = True
                        info = {"at_frame": first, "from": {"w": tile_w, "h": tile_h}, "to": {"w": new_w, "h": new_h},
                                "error": str(exc)[:300], "time": now_iso()}
                        self.log.warning("OOM -> downgrade tiles %dx%d -> %dx%d, retrying frames %d-%d once",
                                         tile_w, tile_h, new_w, new_h, first, first + len(chunk) - 1)
                        tile_w, tile_h = new_w, new_h
                        self.tile_history.append({"from_frame": first, "w": tile_w, "h": tile_h, "overlap": cfg["overlap"],
                                                  "layout": tile_layout(in_w, in_h, tile_w, tile_h, cfg["overlap"])})
                        self.manifest.update(oom_downgrade=info, tile_history=self.tile_history,
                                             tiles_final={"w": tile_w, "h": tile_h, "overlap": cfg["overlap"]})
                for i in range(output.shape[1]):
                    image = (output[0, i].permute(1, 2, 0).numpy() * 255.0).round().astype(np.uint8)[:, :, ::-1]
                    if writer is None:
                        h, w = image.shape[:2]
                        writer = cv2.VideoWriter(raw_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
                        if not writer.isOpened():
                            raise RuntimeError("cannot open raw VSR output writer")
                    writer.write(np.ascontiguousarray(image))
                    self.frames_done += 1
                del tensor, output, rgb, chunk
                gc.collect()
                vram = None
                if device.type == "cuda":
                    vram = {"alloc_gb": round(torch.cuda.memory_allocated(device) / 2 ** 30, 2),
                            "peak_gb": round(torch.cuda.max_memory_allocated(device) / 2 ** 30, 2)}
                    torch.cuda.empty_cache()
                dt = time.monotonic() - t0
                self.log.info("chunk %d frames %d-%d tile %dx%d ov %d %.1fs vram %s progress %d/%d",
                              chunk_index, first, self.frames_done - 1, tile_w, tile_h, cfg["overlap"], dt,
                              vram, self.frames_done, limit)
                self.manifest.update(frames_completed=self.frames_done,
                                     progress=round(self.frames_done / max(1, limit), 4),
                                     last_chunk={"index": chunk_index, "frames": [first, self.frames_done - 1],
                                                 "seconds": round(dt, 2), "vram": vram})
                chunk_index += 1
        finally:
            cap.release()
            if writer is not None:
                writer.release()
        if self.frames_done != limit:
            raise RuntimeError(f"decoded/processed {self.frames_done} frames, expected {limit}")
        inference_s = round(time.monotonic() - infer_started, 1)
        peak = None
        if device.type == "cuda":
            peak = {"max_allocated_gb": round(torch.cuda.max_memory_allocated(device) / 2 ** 30, 2),
                    "max_reserved_gb": round(torch.cuda.max_memory_reserved(device) / 2 ** 30, 2)}
        del pipe
        gc.collect()
        if device.type == "cuda":
            torch.cuda.empty_cache()
        self.manifest.update(inference_s=inference_s, vram_peak=peak)

        self.set_stage("encode")
        cmd = encode_command(cfg, raw_path, self.frames_done)
        self.log.info("encode: %s", subprocess.list2cmdline(cmd))
        self.manifest.update(encode_command=cmd)
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg encode failed (rc={proc.returncode}): {proc.stderr.strip()[:800]}")

        self.set_stage("verify_decode")
        decode = {}
        for key in ("raw", "delivery"):
            p = subprocess.run([cfg["tools"]["ffmpeg"], "-v", "error", "-i", cfg["outputs"][key], "-f", "null", "-"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            decode[key] = {"returncode": p.returncode, "stderr": p.stderr.strip()[:500]}
            if p.returncode != 0 or p.stderr.strip():
                raise RuntimeError(f"full decode of {key} failed: {p.stderr.strip()[:500]}")
        self.manifest.update(status="completed", stage="done", finished=now_iso(), frames=self.frames_done,
                             fps=cfg["input_probe"]["fps"], decode_check=decode, decode_ok=True,
                             realbasicvsr_raw=cfg["outputs"]["raw"], delivery=cfg["outputs"]["delivery"],
                             audio_policy=cfg["audio_policy"], elapsed_s=round(time.monotonic() - started, 1),
                             qa_status="not_run", visual_qa="pending_review")
        self.log.info("completed: %d frames, inference %.1fs", self.frames_done, inference_s)


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        cfg = validate(args)
    except ConfigError as exc:
        print(f"[vsr] REJECTED (exit {exc.code}) stage={exc.stage}: {exc}", file=sys.stderr)
        return exc.code

    if args.dry_run:
        lock_path = Path(cfg["lock_path"])
        plan = {"dry_run": True, "config": cfg,
                "encode_command": encode_command(cfg, cfg["outputs"]["raw"], cfg["expected_frames"]),
                "lock_status": {"lock_exists": lock_path.exists(), "legacy_lock_exists": LEGACY_LOCK.exists()},
                "gpu_nvidia_smi": nvidia_smi(),
                "would_create": cfg["output_dir"], "model_loaded": False, "run_dir_created": False}
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return EXIT_OK

    lock = GpuLock(cfg["lock_path"], LEGACY_LOCK, cfg["lock_owner"], cfg["output_dir"])
    try:
        lock_info = lock.acquire()
    except LockBusy as exc:
        print(f"[vsr] GPU LOCK BUSY (exit {EXIT_LOCK_BUSY}): {exc}", file=sys.stderr)
        return EXIT_LOCK_BUSY
    runner = None
    code = EXIT_RUNTIME
    try:
        out = Path(cfg["output_dir"])
        try:
            out.mkdir(parents=False, exist_ok=False)  # exclusive create
        except FileExistsError:
            print(f"[vsr] REJECTED (exit {EXIT_OUTPUT_EXISTS}): output dir appeared concurrently: {out}", file=sys.stderr)
            return EXIT_OUTPUT_EXISTS
        runner = Runner(cfg, lock)
        code = runner.execute(lock_info)
    finally:
        rel = lock.release()
        rel["checked"] = now_iso()
        rel["lock_file_exists_now"] = Path(cfg["lock_path"]).exists()
        if runner is not None:
            try:
                runner.manifest.update(lock_release=rel)
                runner.log.info("lock release: %s", rel)
            except Exception:
                pass
        print(f"[vsr] lock release: {rel}", file=sys.stderr)

    if code == EXIT_OK and cfg["run_qa"]:
        qa_cmd = [sys.executable, str(ROOT / "qa_single_vsr.py"), "--run-dir", cfg["output_dir"]]
        if cfg["qa_compare"]:
            qa_cmd += ["--compare-vsr", cfg["qa_compare"]]
        runner.log.info("QA: %s", subprocess.list2cmdline(qa_cmd))
        qa_rc = subprocess.run(qa_cmd).returncode
        runner.log.info("QA exit code %d", qa_rc)
        if qa_rc == EXIT_QA_FAIL:
            return EXIT_QA_FAIL
        if qa_rc != 0:
            runner.log.error("QA crashed (rc=%d); run is completed but qa_status unknown", qa_rc)
            return EXIT_RUNTIME
    return code


if __name__ == "__main__":
    sys.exit(main())
