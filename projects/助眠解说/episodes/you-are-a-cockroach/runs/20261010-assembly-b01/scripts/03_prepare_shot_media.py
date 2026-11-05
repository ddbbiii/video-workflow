# -*- coding: utf-8 -*-
"""Extract I2V last frames, re-render affines, build per-shot 30fps clips (V1/V3/P1)."""
from __future__ import annotations
import json, math, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_common import (
    RUN, FFMPEG, FFPROBE, PYTHON, CAMERA_MOTION, FPS,
    load_json, atomic_json, update_checkpoint, log_stage, now_iso, run_cmd,
)

MEDIA = RUN / "media"
TAIL = MEDIA / "tail_frames"
AFFINE_OUT = MEDIA / "affine"
V3_OUT = MEDIA / "v3"
SHOT_OUT = MEDIA / "shot"
PLANS = MEDIA / "affine_plans"
for d in (TAIL, AFFINE_OUT, V3_OUT, SHOT_OUT, PLANS):
    d.mkdir(parents=True, exist_ok=True)


def ensure_duration_ok(duration_s: float) -> float:
    frames = max(2, int(round(duration_s * FPS)))
    return frames / FPS


def make_curve(duration_s: float, template: dict | None) -> dict:
    span = (max(2, int(round(duration_s * FPS))) - 1) / FPS
    curve = dict(template or {"type": "ramped_linear", "ramp_s": 0.75})
    if curve.get("type") == "ramped_linear":
        ramp = float(curve.get("ramp_s", 0.75))
        max_ramp = span / 2 - 1e-3
        if max_ramp <= 0.05:
            return {"type": "smoothstep"}
        curve["ramp_s"] = min(ramp, max_ramp)
    return curve


def extract_last_frame(video: Path, out_png: Path) -> None:
    if out_png.is_file() and out_png.stat().st_size > 1000:
        return
    # seek near end
    cmd = [str(FFMPEG), "-y", "-sseof", "-0.1", "-i", str(video), "-frames:v", "1", "-q:v", "2", str(out_png)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not out_png.is_file():
        cmd = [str(FFMPEG), "-y", "-i", str(video), "-vf", "select=eq(n\\,0)", "-vsync", "vfr", "-frames:v", "1", str(out_png)]
        # better: get nb_frames
        probe = subprocess.run([str(FFPROBE), "-v", "error", "-select_streams", "v:0",
                                "-count_frames", "-show_entries", "stream=nb_read_frames",
                                "-of", "csv=p=0", str(video)], capture_output=True, text=True)
        n = 0
        try:
            n = int(probe.stdout.strip().split(",")[0] or 0)
        except Exception:
            n = 0
        if n > 1:
            cmd = [str(FFMPEG), "-y", "-i", str(video), "-vf", f"select=eq(n\\,{n-1})", "-vsync", "vfr",
                   "-frames:v", "1", str(out_png)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"last frame failed {video}: {r.stderr[-500:]}")


def build_affine_plan(shots_spec: list, plan_path: Path) -> None:
    plan = {
        "schema_version": 1,
        "backend": "affine",
        "output": {"width": 1920, "height": 1080, "fps": FPS},
        "transition_s": 0,
        "shots": shots_spec,
    }
    atomic_json(plan_path, plan)


def render_affine_plan(plan_path: Path, out_dir: Path, log_name: str) -> int:
    log = RUN / "logs" / log_name
    return run_cmd([str(PYTHON), str(CAMERA_MOTION), str(plan_path), "--out", str(out_dir), "--resume"], log)


def to_30fps_clip(src: Path, dst: Path, duration_s: float | None = None) -> None:
    if dst.is_file() and dst.stat().st_size > 1000:
        return
    cmd = [str(FFMPEG), "-y", "-i", str(src), "-vf", f"fps={FPS},scale=1920:1080:flags=lanczos",
           "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p"]
    if duration_s is not None:
        cmd += ["-t", f"{duration_s:.6f}"]
    cmd.append(str(dst))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"fps convert failed {src}: {r.stderr[-400:]}")


def concat_videos(parts: list[Path], dst: Path) -> None:
    if dst.is_file() and dst.stat().st_size > 1000:
        return
    lst = dst.with_suffix(".txt")
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    cmd = [str(FFMPEG), "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(dst)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"concat failed {dst}: {r.stderr[-400:]}")


def main():
    update_checkpoint(stage="chapter_assembly",
                      completed=["create_run", "build_timeline", "build_media_map"],
                      running=["prepare_shot_media"],
                      next_action="extract frames + affine render + per-shot clips")
    mm = load_json(RUN / "media-map.json")
    shots = mm["shots"]

    # 1) extract last frames for V3
    v3 = [s for s in shots if s["combo"] == "V3"]
    log_stage("03_prepare", f"extracting {len(v3)} last frames")
    def _ext(s):
        png = TAIL / f"{s['shot_id']}.png"
        extract_last_frame(Path(s["i2v_path"]), png)
        return s["shot_id"]
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(_ext, s) for s in v3]
        for i, fut in enumerate(as_completed(futs), 1):
            sid = fut.result()
            if i % 10 == 0 or i == len(futs):
                log_stage("03_prepare", f"last frames {i}/{len(futs)} last={sid}")

    # 2) build affine plan(s) for all needs_affine_render
    need = [s for s in shots if s["needs_affine_render"]]
    specs = []
    for s in need:
        dur = ensure_duration_ok(float(s["affine_duration_s"]))
        if s["affine_source"] == "i2v_last_frame":
            src = TAIL / f"{s['shot_id']}.png"
            sid = f"{s['shot_id']}_tail"
        else:
            src = Path(s["still_path"])
            sid = s["shot_id"]
        # for very long duration, ramp must be valid
        curve = make_curve(dur, s.get("curve"))
        specs.append({
            "id": sid,
            "source": str(src.resolve()),
            "duration_s": dur,
            "start_view": s["start_view"],
            "end_view": s["end_view"],
            "curve": curve,
        })
        s["affine_clip_id"] = sid
        s["affine_duration_s"] = dur

    # split into batches of 20 for progress
    batch_size = 20
    batches = [specs[i:i+batch_size] for i in range(0, len(specs), batch_size)]
    log_stage("03_prepare", f"affine specs={len(specs)} batches={len(batches)}")
    for bi, batch in enumerate(batches):
        plan_path = PLANS / f"affine_batch_{bi:02d}.json"
        build_affine_plan(batch, plan_path)
        # validate
        rc = run_cmd([str(PYTHON), str(CAMERA_MOTION), str(plan_path), "--out", str(AFFINE_OUT), "--validate-only"],
                     RUN / "logs" / f"affine_validate_{bi:02d}.log")
        if rc != 0:
            raise SystemExit(f"affine validate failed batch {bi}")
        t1 = time.time()
        rc = render_affine_plan(plan_path, AFFINE_OUT, f"affine_render_{bi:02d}.log")
        log_stage("03_prepare", f"affine batch {bi} exit={rc} seconds={time.time()-t1:.1f}")
        if rc != 0:
            raise SystemExit(f"affine render failed batch {bi}")

    atomic_json(RUN / "media-map.json", mm)  # with affine_clip_id updates

    # 3) build final per-shot clips
    log_stage("03_prepare", "building per-shot clips")
    manifest = {"created_at": now_iso(), "shots": []}

    def build_one(s):
        sid = s["shot_id"]
        dst = SHOT_OUT / f"{sid}.mp4"
        target = float(s["target_seconds"])
        # snap to timeline frame count
        target = s["frame_count"] / FPS
        if s["combo"] == "V1":
            to_30fps_clip(Path(s["i2v_path"]), dst, duration_s=target)
        elif s["combo"] == "V3":
            i2v30 = V3_OUT / f"{sid}_i2v30.mp4"
            tail = AFFINE_OUT / f"{s['affine_clip_id']}.mp4"
            if not tail.is_file():
                raise RuntimeError(f"missing tail affine {tail}")
            # convert i2v to 30fps for generated portion
            gen_s = float(s["generated_motion_seconds"])
            to_30fps_clip(Path(s["i2v_path"]), i2v30, duration_s=gen_s)
            # trim/pad to exact target: i2v30 + tail, then trim
            concat = V3_OUT / f"{sid}_concat.mp4"
            concat_videos([i2v30, tail], concat)
            # trim to exact frame count
            cmd = [str(FFMPEG), "-y", "-i", str(concat), "-frames:v", str(s["frame_count"]),
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(dst)]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(f"trim v3 failed {sid}: {r.stderr[-400:]}")
        else:  # P1
            src = AFFINE_OUT / f"{s['affine_clip_id']}.mp4"
            if not src.is_file():
                raise RuntimeError(f"missing p1 affine {src}")
            # ensure exact frame count
            cmd = [str(FFMPEG), "-y", "-i", str(src), "-frames:v", str(s["frame_count"]),
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(dst)]
            if dst.is_file() and dst.stat().st_size > 1000:
                pass
            else:
                r = subprocess.run(cmd, capture_output=True, text=True)
                if r.returncode != 0:
                    raise RuntimeError(f"p1 trim failed {sid}: {r.stderr[-400:]}")
        s["delivery_clip"] = str(dst.resolve())
        return {"shot_id": sid, "combo": s["combo"], "path": str(dst), "frames": s["frame_count"]}

    # sequential for stability (CPU already heavy from affine); can parallel light ffmpeg
    results = []
    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = {ex.submit(build_one, s): s["shot_id"] for s in shots}
        done = 0
        for fut in as_completed(futs):
            done += 1
            rec = fut.result()
            results.append(rec)
            if done % 10 == 0 or done == len(futs):
                log_stage("03_prepare", f"shot clips {done}/{len(futs)} last={rec['shot_id']}")

    atomic_json(RUN / "media-map.json", mm)
    atomic_json(MEDIA / "shot_clips_manifest.json", {"shots": results, "count": len(results)})
    log_stage("03_prepare", f"done shot clips={len(results)}")
    update_checkpoint(stage="chapter_assembly",
                      completed=["create_run", "build_timeline", "build_media_map", "prepare_shot_media"],
                      running=[], next_action="assemble chapters + audio/subs")
    print(f"OK prepare_shot_media clips={len(results)}")

if __name__ == "__main__":
    main()