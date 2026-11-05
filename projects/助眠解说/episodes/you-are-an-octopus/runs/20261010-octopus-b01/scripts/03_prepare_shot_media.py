# -*- coding: utf-8 -*-
"""Prepare per-shot clips for octopus.

Rules:
- Never stretch / reverse / ping-pong I2V.
- V3: play I2V at native speed + last-frame affine tail (default 2s, hard max 3.5s).
- If i2v_dur + allowed_tail < target: whole-shot fallback to existing P1 affine.
- Reuse already-rendered affine mp4s under media/affine{,_r2,_r3}; do not re-render P1.
"""
from __future__ import annotations
import json, math, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_common import (
    RUN, FFMPEG, FFPROBE, PYTHON, CAMERA_MOTION, FPS, STILLS,
    load_json, atomic_json, update_checkpoint, log_stage, now_iso, run_cmd, ffprobe_duration,
)

MEDIA = RUN / "media"
TAIL = MEDIA / "tail_frames"
AFFINE_OUT = MEDIA / "affine_tail"  # only new short tails for V3
V3_OUT = MEDIA / "v3"
SHOT_OUT = MEDIA / "shot"
PLANS = MEDIA / "affine_plans"
for d in (TAIL, AFFINE_OUT, V3_OUT, SHOT_OUT, PLANS):
    d.mkdir(parents=True, exist_ok=True)

AFFINE_DIRS = [MEDIA / "affine", MEDIA / "affine_r2", MEDIA / "affine_r3", AFFINE_OUT]
I2V_MANIFESTS = [
    RUN.parent / "20261010-i2v-pilot-b01" / "i2v_manifest.json",
    RUN.parent / "20261010-i2v-batch-b01" / "i2v_manifest.json",
]
TAIL_DEFAULT = 2.0
TAIL_HARD_MAX = 3.5


def find_affine(shot_id: str) -> Path | None:
    for d in AFFINE_DIRS:
        p = d / f"{shot_id}.mp4"
        if p.is_file() and p.stat().st_size > 1000:
            return p
    return None


def load_i2v_index():
    """Merge manifests; prefer ok+lanczos with longer frames (batch over pilot)."""
    by = {}
    for p in I2V_MANIFESTS:
        if not p.exists():
            continue
        for x in load_json(p):
            if x.get("ok") and x.get("lanczos") and Path(x["lanczos"]).is_file():
                prev = by.get(x["shot"])
                if prev is None or int(x.get("frames") or 0) >= int(prev.get("frames") or 0):
                    by[x["shot"]] = x  # prefer longer frames
    return by


def extract_last_frame(video: Path, out_png: Path) -> None:
    if out_png.is_file() and out_png.stat().st_size > 1000:
        return
    cmd = [str(FFMPEG), "-y", "-sseof", "-0.15", "-i", str(video), "-frames:v", "1", "-q:v", "2", str(out_png)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not out_png.is_file():
        raise RuntimeError(f"last frame failed {video}: {(r.stderr or '')[-400:]}")


def make_curve(duration_s: float) -> dict:
    span = (max(2, int(round(duration_s * FPS))) - 1) / FPS
    if span < 0.4:
        return {"type": "smoothstep"}
    return {"type": "ramped_linear", "ramp_s": min(0.5, max(0.05, span / 2 - 0.01))}


def render_tail_affine(shot_id: str, png: Path, duration_s: float, start_view, end_view) -> Path:
    out = AFFINE_OUT / f"{shot_id}_tail.mp4"
    if out.is_file() and out.stat().st_size > 1000:
        # verify duration roughly
        try:
            if abs(ffprobe_duration(out) - duration_s) < 0.15:
                return out
        except Exception:
            pass
    frames = max(2, int(round(duration_s * FPS)))
    dur = frames / FPS
    plan_path = PLANS / f"tail_{shot_id}.json"
    plan = {
        "schema_version": 1,
        "backend": "affine",
        "output": {"width": 1920, "height": 1080, "fps": FPS},
        "transition_s": 0,
        "shots": [{
            "id": f"{shot_id}_tail",
            "source": str(png.resolve()),
            "duration_s": dur,
            "start_view": start_view,
            "end_view": end_view,
            "curve": make_curve(dur),
        }],
    }
    atomic_json(plan_path, plan)
    # per-shot out dir avoids camera_motion --resume manifest clashes under shared affine_tail/
    shot_out = AFFINE_OUT / f"_run_{shot_id}"
    shot_out.mkdir(parents=True, exist_ok=True)
    rc = run_cmd([str(PYTHON), str(CAMERA_MOTION), str(plan_path), "--out", str(shot_out)],
                 RUN / "logs" / f"affine_tail_{shot_id}.log")
    produced = shot_out / f"{shot_id}_tail.mp4"
    if rc != 0 or not produced.is_file():
        raise RuntimeError(f"tail affine failed {shot_id} rc={rc}")
    # copy into flat name expected by callers
    import shutil as _shutil
    _shutil.copy2(produced, out)
    return out


def to_30fps_clip(src: Path, dst: Path, duration_s: float | None = None) -> None:
    if dst.is_file() and dst.stat().st_size > 1000:
        return
    cmd = [str(FFMPEG), "-y", "-i", str(src), "-vf", f"fps={FPS},scale=1920:1080:flags=lanczos,setsar=1",
           "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p"]
    if duration_s is not None:
        cmd += ["-t", f"{duration_s:.6f}"]
    cmd.append(str(dst))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"fps convert failed {src}: {(r.stderr or '')[-400:]}")


def concat_videos(parts: list[Path], dst: Path) -> None:
    lst = dst.with_suffix(".txt")
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    cmd = [str(FFMPEG), "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(dst)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"concat failed {dst}: {(r.stderr or '')[-400:]}")


def trim_frames(src: Path, dst: Path, frame_count: int) -> None:
    if dst.is_file() and dst.stat().st_size > 1000:
        # quick check frames via duration
        try:
            if abs(ffprobe_duration(dst) - frame_count / FPS) < 0.08:
                return
        except Exception:
            pass
    cmd = [str(FFMPEG), "-y", "-i", str(src), "-frames:v", str(frame_count),
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(dst)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"trim failed {src}: {(r.stderr or '')[-400:]}")


def main():
    update_checkpoint(stage="prepare_shot_media", in_progress=["prepare_shot_media"],
                      next_action="build shot clips with V3/fallback rules")
    mm = load_json(RUN / "media-map.json")
    i2v_by = load_i2v_index()
    shots = mm["shots"]
    stats = {"v3_used": 0, "v3_fallback_affine": 0, "p1": 0, "missing_affine": 0, "errors": []}
    results = []

    def build_one(s):
        sid = s["shot_id"]
        dst = SHOT_OUT / f"{sid}.mp4"
        target = s["frame_count"] / FPS
        planned_v3 = (s.get("strategy_effective") == "V3") or (s.get("combo") in ("V3", "V3_PENDING"))
        meta = i2v_by.get(sid)
        use_v3 = False
        i2v_path = None
        i2v_dur = 0.0
        if planned_v3 and meta:
            i2v_path = Path(meta["lanczos"])
            i2v_dur = ffprobe_duration(i2v_path)
            # planned tail from timeline / PRODUCTION_PLAN
            # remainder fill up to HARD_MAX; never stretch I2V
            need_tail = max(0.0, target - i2v_dur)
            allow_tail = TAIL_HARD_MAX
            if need_tail <= allow_tail + 1e-3:
                use_v3 = True
            else:
                # not enough — whole-shot fallback
                use_v3 = False

        if use_v3:
            png = TAIL / f"{sid}.png"
            extract_last_frame(i2v_path, png)
            tail_s = 0.0
            need_tail = max(0.0, target - i2v_dur)
            # snap tail to frames so concat matches
            tail_frames = max(0, s["frame_count"] - int(round(i2v_dur * FPS)))
            if tail_frames < 1:
                # I2V alone covers; trim I2V
                to_30fps_clip(i2v_path, dst, duration_s=target)
                combo = "V3"
                reason = "i2v_covers_target"
                gen_s, tail_s = target, 0.0
            else:
                tail_s = tail_frames / FPS
                start_view = s.get("start_view") or [0.09, 0.09, 0.82, 0.82]
                end_view = s.get("end_view") or [0.025, 0.025, 0.95, 0.95]
                # gentle hold-ish: tiny push from near-full frame
                start_view = [0.02, 0.02, 0.96, 0.96]
                end_view = [0.01, 0.01, 0.98, 0.98]
                tail_mp4 = render_tail_affine(sid, png, tail_s, start_view, end_view)
                i2v30 = V3_OUT / f"{sid}_i2v30.mp4"
                to_30fps_clip(i2v_path, i2v30, duration_s=None)
                concat = V3_OUT / f"{sid}_concat.mp4"
                concat_videos([i2v30, tail_mp4], concat)
                trim_frames(concat, dst, s["frame_count"])
                combo = "V3"
                reason = "i2v_plus_lastframe_tail"
                gen_s = i2v_dur
            s.update({
                "combo": combo, "shot_class": "image_to_video",
                "i2v_path": str(i2v_path), "source_path": str(i2v_path),
                "available_i2v_seconds": round(i2v_dur, 4),
                "generated_motion_seconds": round(gen_s, 4),
                "tail_extension_seconds": round(tail_s, 4),
                "tail_extension_mode": "affine" if tail_s > 0 else "none",
                "reason": reason, "strategy_effective": "V3",
                "needs_i2v": False, "fallback_from_i2v": False,
                "delivery_clip": str(dst.resolve()),
            })
            return {"shot_id": sid, "combo": "V3", "path": str(dst), "frames": s["frame_count"]}

        # P1 or V3 fallback
        aff = find_affine(sid)
        if aff is None:
            # last resort: render from still
            still = Path(s["still_path"]) if s.get("still_path") else (STILLS / f"{sid}.jpg")
            if not still.is_file():
                raise FileNotFoundError(f"no affine and no still for {sid}")
            start_view = s.get("start_view") or [0.09, 0.09, 0.82, 0.82]
            end_view = s.get("end_view") or [0.025, 0.025, 0.95, 0.95]
            plan_path = PLANS / f"p1_{sid}.json"
            dur = s["frame_count"] / FPS
            atomic_json(plan_path, {
                "schema_version": 1, "backend": "affine",
                "output": {"width": 1920, "height": 1080, "fps": FPS}, "transition_s": 0,
                "shots": [{"id": sid, "source": str(still.resolve()), "duration_s": dur,
                           "start_view": start_view, "end_view": end_view, "curve": make_curve(dur)}],
            })
            rc = run_cmd([str(PYTHON), str(CAMERA_MOTION), str(plan_path), "--out", str(MEDIA / "affine"), "--resume"],
                         RUN / "logs" / f"affine_fallback_{sid}.log")
            aff = find_affine(sid)
            if aff is None:
                raise RuntimeError(f"affine missing after render {sid} rc={rc}")

        trim_frames(aff, dst, s["frame_count"])
        fell = bool(planned_v3 and meta)
        pending = bool(planned_v3 and not meta)
        reason = (
            "v3_fallback_i2v_too_short" if fell else
            ("v3_pending_used_affine" if pending else "p1_camera_motion")
        )
        s.update({
            "combo": "P1", "shot_class": "image_camera_motion",
            "source_path": str(aff.resolve()),
            "affine_path": str(aff.resolve()),
            "available_i2v_seconds": round(i2v_dur, 4) if meta else 0.0,
            "generated_motion_seconds": 0.0,
            "tail_extension_seconds": 0.0,
            "tail_extension_mode": "none",
            "reason": reason,
            "strategy_effective": "P1",
            "strategy_planned": s.get("strategy_planned") or ("V3" if planned_v3 else "P1"),
            "fallback_from_i2v": fell,
            "needs_i2v": pending,
            "delivery_clip": str(dst.resolve()),
        })
        return {"shot_id": sid, "combo": "P1", "path": str(dst), "frames": s["frame_count"],
                "fallback": fell, "pending_i2v": pending}

    log_stage("03_prepare", f"building {len(shots)} shot clips; i2v_ready={len(i2v_by)}")
    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = {ex.submit(build_one, s): s["shot_id"] for s in shots}
        done = 0
        for fut in as_completed(futs):
            done += 1
            sid = futs[fut]
            try:
                rec = fut.result()
                results.append(rec)
                if rec["combo"] == "V3":
                    stats["v3_used"] += 1
                else:
                    if rec.get("fallback"):
                        stats["v3_fallback_affine"] += 1
                    else:
                        stats["p1"] += 1
            except Exception as e:
                stats["errors"].append({"shot": sid, "error": repr(e)[:400]})
                log_stage("03_prepare", f"ERROR {sid}: {e!r}")
            if done % 20 == 0 or done == len(futs):
                log_stage("03_prepare", f"progress {done}/{len(futs)} stats={stats}")

    atomic_json(RUN / "media-map.json", mm)
    atomic_json(MEDIA / "shot_clips_manifest.json", {
        "created_at": now_iso(), "stats": stats, "shots": results, "count": len(results),
    })
    update_checkpoint(
        stage="prepare_shot_media_done" if not stats["errors"] else "prepare_shot_media_partial",
        in_progress=["i2v_pilot"] if len(i2v_by) < 6 else [],
        completed=list(dict.fromkeys((load_json(RUN / "CHECKPOINT.json").get("completed") or []) + ["prepare_shot_media_pass1"])),
        next_action="continue I2V; refresh shot clips when more I2V land; audio/subs/chapters",
        shot_prep_stats=stats,
        shot_clips=len(results),
    )
    print("OK prepare", stats, "clips", len(results))
    return 0 if not stats["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
