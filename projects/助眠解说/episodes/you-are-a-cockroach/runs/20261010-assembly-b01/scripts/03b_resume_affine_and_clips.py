# -*- coding: utf-8 -*-
"""Resume: one full affine plan with --resume, then build per-shot clips."""
from __future__ import annotations
import json, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_common import (
    RUN, FFMPEG, PYTHON, CAMERA_MOTION, FPS,
    load_json, atomic_json, update_checkpoint, log_stage, now_iso, run_cmd,
)

MEDIA = RUN / "media"
TAIL = MEDIA / "tail_frames"
AFFINE_OUT = MEDIA / "affine"
V3_OUT = MEDIA / "v3"
SHOT_OUT = MEDIA / "shot"
PLANS = MEDIA / "affine_plans"
for d in (V3_OUT, SHOT_OUT, PLANS):
    d.mkdir(parents=True, exist_ok=True)


def ensure_duration_ok(duration_s: float) -> float:
    frames = max(2, int(round(duration_s * FPS)))
    return frames / FPS


def make_curve(duration_s: float, template):
    span = (max(2, int(round(duration_s * FPS))) - 1) / FPS
    curve = dict(template or {"type": "ramped_linear", "ramp_s": 0.75})
    if curve.get("type") == "ramped_linear":
        ramp = float(curve.get("ramp_s", 0.75))
        max_ramp = span / 2 - 1e-3
        if max_ramp <= 0.05:
            return {"type": "smoothstep"}
        curve["ramp_s"] = min(ramp, max_ramp)
    return curve


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


def concat_videos(parts, dst: Path) -> None:
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
                      running=["resume_affine_and_clips"],
                      next_action="full affine plan resume + shot clips")
    mm = load_json(RUN / "media-map.json")
    shots = mm["shots"]
    need = [s for s in shots if s["needs_affine_render"]]
    specs = []
    for s in need:
        dur = ensure_duration_ok(float(s["affine_duration_s"]))
        if s["affine_source"] == "i2v_last_frame":
            src = TAIL / f"{s['shot_id']}.png"
            if not src.is_file():
                raise FileNotFoundError(src)
            sid = f"{s['shot_id']}_tail"
        else:
            src = Path(s["still_path"])
            sid = s["shot_id"]
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

    plan_path = PLANS / "affine_all.json"
    atomic_json(plan_path, {
        "schema_version": 1,
        "backend": "affine",
        "output": {"width": 1920, "height": 1080, "fps": FPS},
        "transition_s": 0,
        "shots": specs,
    })
    # If existing manifest has shots not in plan, wipe manifest but keep completed mp4s that match ids
    man = AFFINE_OUT / "manifest.json"
    if man.is_file():
        old = load_json(man)
        planned = {s["id"] for s in specs}
        # rewrite manifest keeping only overlapping complete shots
        kept = [s for s in old.get("shots", []) if s.get("id") in planned]
        old["shots"] = kept
        old["plan"] = str(plan_path.resolve())
        old["status"] = "running"
        atomic_json(man, old)
        log_stage("03b_resume", f"rewrote manifest kept={len(kept)}")

    log_stage("03b_resume", f"rendering full affine plan n={len(specs)}")
    t0 = time.time()
    rc = run_cmd([str(PYTHON), str(CAMERA_MOTION), str(plan_path), "--out", str(AFFINE_OUT), "--resume"],
                 RUN / "logs" / "affine_render_all.log")
    log_stage("03b_resume", f"affine_all exit={rc} seconds={time.time()-t0:.1f}")
    if rc != 0:
        raise SystemExit(f"affine_all failed rc={rc}")

    atomic_json(RUN / "media-map.json", mm)

    def build_one(s):
        sid = s["shot_id"]
        dst = SHOT_OUT / f"{sid}.mp4"
        if dst.is_file() and dst.stat().st_size > 1000:
            s["delivery_clip"] = str(dst.resolve())
            return {"shot_id": sid, "combo": s["combo"], "path": str(dst), "frames": s["frame_count"], "skipped": True}
        if s["combo"] == "V1":
            to_30fps_clip(Path(s["i2v_path"]), dst, duration_s=s["frame_count"] / FPS)
        elif s["combo"] == "V3":
            i2v30 = V3_OUT / f"{sid}_i2v30.mp4"
            tail = AFFINE_OUT / f"{s['affine_clip_id']}.mp4"
            if not tail.is_file():
                raise RuntimeError(f"missing tail {tail}")
            to_30fps_clip(Path(s["i2v_path"]), i2v30, duration_s=float(s["generated_motion_seconds"]))
            concat = V3_OUT / f"{sid}_concat.mp4"
            concat_videos([i2v30, tail], concat)
            cmd = [str(FFMPEG), "-y", "-i", str(concat), "-frames:v", str(s["frame_count"]),
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(dst)]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(f"trim v3 failed {sid}: {r.stderr[-400:]}")
        else:
            src = AFFINE_OUT / f"{s['affine_clip_id']}.mp4"
            if not src.is_file():
                raise RuntimeError(f"missing p1 {src}")
            cmd = [str(FFMPEG), "-y", "-i", str(src), "-frames:v", str(s["frame_count"]),
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(dst)]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(f"p1 trim failed {sid}: {r.stderr[-400:]}")
        s["delivery_clip"] = str(dst.resolve())
        return {"shot_id": sid, "combo": s["combo"], "path": str(dst), "frames": s["frame_count"]}

    log_stage("03b_resume", "building shot clips")
    results = []
    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = [ex.submit(build_one, s) for s in shots]
        done = 0
        for fut in as_completed(futs):
            done += 1
            rec = fut.result()
            results.append(rec)
            if done % 10 == 0 or done == len(futs):
                log_stage("03b_resume", f"shot clips {done}/{len(futs)} last={rec['shot_id']}")

    atomic_json(RUN / "media-map.json", mm)
    atomic_json(MEDIA / "shot_clips_manifest.json", {"shots": results, "count": len(results), "created_at": now_iso()})
    update_checkpoint(stage="chapter_assembly",
                      completed=["create_run", "build_timeline", "build_media_map", "prepare_shot_media"],
                      running=[], next_action="assemble chapters")
    print(f"OK resume clips={len(results)}")

if __name__ == "__main__":
    main()