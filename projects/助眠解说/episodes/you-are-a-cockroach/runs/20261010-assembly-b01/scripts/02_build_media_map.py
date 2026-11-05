# -*- coding: utf-8 -*-
"""Build media-map.json: choose I2V/V3 vs P1 affine per shot."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_common import (
    EP, RUN, STILLS, I2V_LANCZOS, I2V_MANIFEST, AFFINE_OLD,
    load_json, atomic_json, update_checkpoint, log_stage, ffprobe_duration, now_iso,
)

# Legal extension: V3 (I2V + last-frame affine). No loop for this episode.
# If I2V missing/undecodable -> whole-shot P1 from still.
# Affine-class shots always P1 at final duration (re-render; do not loop 7s).

def main():
    update_checkpoint(stage="media_map", completed=["create_run", "build_timeline"],
                      running=["build_media_map"], next_action="generate media-map.json")
    tl = load_json(RUN / "timeline.json")
    i2v_list = load_json(I2V_MANIFEST)
    i2v_by = {x["shot"]: x for x in i2v_list}
    old_affine_plan = load_json(AFFINE_OLD / "affine_plan.json")
    old_views = {s["id"]: s for s in old_affine_plan["shots"]}

    entries = []
    stats = {"v1": 0, "v3": 0, "p1": 0, "fallback_from_i2v": 0, "pending_review": 0}
    for sh in tl["shots"]:
        sid = sh["id"]
        target = float(sh["timeline_seconds"])
        still = STILLS / f"{sid}.jpg"
        if not still.is_file():
            raise SystemExit(f"missing still: {still}")
        cand = sh["media_candidate"]
        entry = {
            "shot_id": sid,
            "section": sh["section"],
            "paragraph_id": sh["paragraph_id"],
            "target_seconds": target,
            "frame_count": sh["frame_count"],
            "start_frame": sh["start_frame"],
            "end_frame": sh["end_frame"],
            "still_path": str(still.resolve()),
            "media_candidate": cand,
            "visual_qa": None,
            "pending_review": False,
            "combo": None,
            "shot_class": None,
            "source_path": None,
            "fallback_path": None,
            "available_i2v_seconds": 0.0,
            "generated_motion_seconds": 0.0,
            "tail_extension_seconds": 0.0,
            "tail_extension_mode": "none",
            "reason": "",
            "class_change_reason": "",
            "needs_affine_render": False,
            "affine_source": None,
            "affine_duration_s": None,
            "i2v_path": None,
        }
        view = old_views.get(sid)
        if view:
            entry["start_view"] = view["start_view"]
            entry["end_view"] = view["end_view"]
            entry["curve"] = view.get("curve", {"type": "ramped_linear", "ramp_s": 0.75})
        else:
            # default gentle push-in
            entry["start_view"] = [0.09, 0.09, 0.82, 0.82]
            entry["end_view"] = [0.025, 0.025, 0.95, 0.95]
            entry["curve"] = {"type": "ramped_linear", "ramp_s": min(0.75, max(0.2, target / 10))}

        if cand == "real_video" and sid in i2v_by:
            meta = i2v_by[sid]
            lanczos = Path(meta.get("lanczos") or "")
            if not lanczos.is_file():
                # try standard name
                lanczos = I2V_LANCZOS / f"{sid}-ltx-lanczos-1920x1080.mp4"
            decode_ok = bool(meta.get("decode_ok", meta.get("ok")))
            visual_qa = meta.get("visual_qa", "pending")
            entry["visual_qa"] = visual_qa
            if visual_qa == "pending":
                entry["pending_review"] = True
                stats["pending_review"] += 1
            if lanczos.is_file() and decode_ok:
                try:
                    i2v_s = ffprobe_duration(lanczos)
                except Exception:
                    i2v_s = meta.get("frames", 121) / float(meta.get("fps", 24))
                entry["available_i2v_seconds"] = i2v_s
                entry["i2v_path"] = str(lanczos.resolve())
                if i2v_s + 1e-3 >= target:
                    entry["combo"] = "V1"
                    entry["shot_class"] = "image_to_video"
                    entry["source_path"] = str(lanczos.resolve())
                    entry["generated_motion_seconds"] = target
                    entry["reason"] = "I2V covers full shot; V1"
                    stats["v1"] += 1
                else:
                    # V3: I2V + last-frame affine for remainder (whitelist; not original still splice)
                    rem = target - i2v_s
                    # snap rem to integral frames at 30fps
                    rem_frames = max(2, int(round(rem * 30)))
                    rem = rem_frames / 30.0
                    entry["combo"] = "V3"
                    entry["shot_class"] = "image_to_video"
                    entry["source_path"] = str(lanczos.resolve())
                    entry["generated_motion_seconds"] = i2v_s
                    entry["tail_extension_seconds"] = rem
                    entry["tail_extension_mode"] = "affine"
                    entry["needs_affine_render"] = True
                    entry["affine_source"] = "i2v_last_frame"
                    entry["affine_duration_s"] = rem
                    entry["reason"] = "I2V short; V3 last-frame affine fill"
                    stats["v3"] += 1
            else:
                entry["combo"] = "P1"
                entry["shot_class"] = "image_camera_motion"
                entry["needs_affine_render"] = True
                entry["affine_source"] = "still"
                entry["affine_duration_s"] = target
                entry["fallback_path"] = str(still.resolve())
                entry["class_change_reason"] = "i2v_missing_or_undecodable"
                entry["reason"] = "fallback whole-shot P1 from still"
                stats["p1"] += 1
                stats["fallback_from_i2v"] += 1
        else:
            # affine candidate or missing i2v
            entry["combo"] = "P1"
            entry["shot_class"] = "image_camera_motion"
            entry["needs_affine_render"] = True
            entry["affine_source"] = "still"
            entry["affine_duration_s"] = target
            entry["source_path"] = None
            entry["fallback_path"] = str(still.resolve())
            if cand == "real_video":
                entry["class_change_reason"] = "i2v_asset_absent"
                stats["fallback_from_i2v"] += 1
            entry["reason"] = "planned affine / P1 at final duration"
            stats["p1"] += 1

        # duration must be integral frames for camera_motion
        if entry["needs_affine_render"] and entry["affine_duration_s"] is not None:
            frames = max(2, int(round(entry["affine_duration_s"] * 30)))
            entry["affine_duration_s"] = frames / 30.0

        entries.append(entry)

    media_map = {
        "schema_version": 1,
        "created_at": now_iso(),
        "run": str(RUN),
        "policy": {
            "i2v_extension": "V3 last-frame affine (whitelist); no loop; no original-still splice in same shot",
            "affine_short": "re-render P1 at final duration; no 7s loop",
            "visual_qa_pending": "allowed in draft; not marked passed",
        },
        "stats": stats,
        "shots": entries,
    }
    out = RUN / "media-map.json"
    atomic_json(out, media_map)
    log_stage("02_media_map", f"wrote {out}; stats={stats}")
    update_checkpoint(stage="media_map", completed=["create_run", "build_timeline", "build_media_map"],
                      running=[], next_action="prepare shot media (affine rerender + V3) and audio stems")
    print("OK media-map", stats)

if __name__ == "__main__":
    main()