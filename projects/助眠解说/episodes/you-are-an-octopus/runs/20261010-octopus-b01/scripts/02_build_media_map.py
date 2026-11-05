# -*- coding: utf-8 -*-
"""Build media-map.json for octopus from timeline + stills (+ optional I2V)."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_common import (
    EP, RUN, STILLS, load_json, atomic_json, update_checkpoint, log_stage, now_iso, write_status,
)

I2V_MANIFEST_CANDIDATES = [
    EP / "runs" / "20261010-i2v-pilot-b01" / "i2v_manifest.json",
    EP / "runs" / "20261010-i2v-batch-b01" / "i2v_manifest.json",
]


def load_i2v():
    """Merge manifests; prefer longer frames (batch 289 over pilot 121)."""
    by = {}
    for p in I2V_MANIFEST_CANDIDATES:
        if p.exists():
            for x in load_json(p):
                prev = by.get(x["shot"])
                # prefer longer frames
                if prev is None or int(x.get("frames") or 0) >= int(prev.get("frames") or 0):
                    by[x["shot"]] = {**x, "_manifest": str(p)}
    return by


def default_views(target: float, image_motion: dict | None):
    im = image_motion or {}
    direction = (im.get("direction") or "push_in").lower()
    # gentle push-in defaults matching sleep-aid style
    start = [0.09, 0.09, 0.82, 0.82]
    end = [0.025, 0.025, 0.95, 0.95]
    if "left" in direction or direction == "pan_left":
        start, end = [0.12, 0.08, 0.82, 0.84], [0.02, 0.08, 0.82, 0.84]
    elif "right" in direction or direction == "pan_right":
        start, end = [0.02, 0.08, 0.82, 0.84], [0.12, 0.08, 0.82, 0.84]
    ramp = min(0.75, max(0.2, target / 10))
    return start, end, {"type": "ramped_linear", "ramp_s": ramp}


def main():
    update_checkpoint(stage="media_map", in_progress=["build_media_map", "stills"], next_action="media-map.json")
    tl = load_json(RUN / "timeline.json")
    i2v_by = load_i2v()
    entries = []
    stats = {"v1": 0, "v3": 0, "p1": 0, "v3_pending_i2v": 0, "missing_still": 0, "fallback_from_i2v": 0}
    missing_stills = []

    for sh in tl["shots"]:
        sid = sh["id"]
        target = float(sh["timeline_seconds"])
        still = STILLS / f"{sid}.jpg"
        start_view, end_view, curve = default_views(target, sh.get("image_motion"))
        entry = {
            "shot_id": sid,
            "beat_id": sh.get("beat_id"),
            "section": sh["section"],
            "paragraph_ids": sh.get("paragraph_ids"),
            "target_seconds": target,
            "frame_count": sh["frame_count"],
            "start_frame": sh["start_frame"],
            "end_frame": sh["end_frame"],
            "still_path": str(still.resolve()) if still.is_file() else None,
            "strategy_planned": sh.get("strategy_planned"),
            "strategy_effective": sh.get("strategy_effective"),
            "shot_class_effective": sh.get("shot_class_effective"),
            "visual_qa": None,
            "pending_review": False,
            "combo": None,
            "shot_class": None,
            "source_path": None,
            "available_i2v_seconds": 0.0,
            "generated_motion_seconds": 0.0,
            "tail_extension_seconds": 0.0,
            "tail_extension_mode": "none",
            "reason": "",
            "needs_affine_render": False,
            "needs_i2v": False,
            "affine_source": None,
            "affine_duration_s": None,
            "i2v_path": None,
            "start_view": start_view,
            "end_view": end_view,
            "curve": curve,
            "overflow_extra_views": sh.get("overflow_extra_views", 0),
        }
        if not still.is_file():
            entry["reason"] = "missing_still"
            entry["combo"] = "PENDING_STILL"
            stats["missing_still"] += 1
            missing_stills.append(sid)
            entries.append(entry)
            continue

        want_v3 = sh.get("strategy_effective") == "V3"
        if want_v3 and sid in i2v_by and i2v_by[sid].get("ok"):
            meta = i2v_by[sid]
            lanczos = Path(meta.get("lanczos") or "")
            if lanczos.is_file():
                # durations filled later by ffprobe in assemble; store path now
                entry["i2v_path"] = str(lanczos.resolve())
                entry["combo"] = "V3"
                entry["shot_class"] = "image_to_video"
                entry["source_path"] = str(lanczos.resolve())
                entry["needs_affine_render"] = True
                entry["affine_source"] = "i2v_last_frame"
                entry["tail_extension_mode"] = "affine"
                entry["reason"] = "I2V available; V3 + last-frame affine fill at assemble"
                entry["visual_qa"] = meta.get("visual_qa", "pending")
                if entry["visual_qa"] == "pending":
                    entry["pending_review"] = True
                stats["v3"] += 1
            else:
                want_v3 = True  # fall through pending
                i2v_by.pop(sid, None)

        if entry["combo"] is None and want_v3 and sid not in i2v_by:
            entry["combo"] = "V3_PENDING"
            entry["shot_class"] = "image_to_video"
            entry["needs_i2v"] = True
            entry["needs_affine_render"] = True  # provisional P1 until I2V lands
            entry["affine_source"] = "still"
            entry["affine_duration_s"] = target
            entry["reason"] = "V3 planned; I2V not ready — provisional still affine"
            stats["v3_pending_i2v"] += 1
        elif entry["combo"] is None:
            entry["combo"] = "P1"
            entry["shot_class"] = "image_camera_motion"
            entry["needs_affine_render"] = True
            entry["affine_source"] = "still"
            entry["affine_duration_s"] = target
            entry["source_path"] = str(still.resolve())
            entry["reason"] = "P1 camera motion from still"
            stats["p1"] += 1

        entries.append(entry)

    out = {
        "schema_version": 1,
        "episode": "you-are-an-octopus",
        "run": str(RUN),
        "created_at": now_iso(),
        "stats": stats,
        "missing_stills": missing_stills,
        "shots": entries,
    }
    atomic_json(RUN / "media-map.json", out)
    log_stage("02_media_map", f"shots={len(entries)} stats={stats} missing={len(missing_stills)}")
    update_checkpoint(
        stage="media_map_done",
        in_progress=["stills"],
        next_action="finish stills; I2V pilot when ch08-b09 ready; affine P1 in parallel",
        media_map_stats=stats,
        stills_missing=len(missing_stills),
    )
    write_status(
        f"# STATUS 你是一只章鱼 — 20261010-octopus-b01\n\n"
        f"- 时间：{now_iso()}\n"
        f"- 时间轴/门禁/atempo：完成；media-map 已出（P1={stats['p1']} V3待I2V={stats['v3_pending_i2v']} 缺静帧={stats['missing_still']}）\n"
        f"- 下一：静帧补齐 → I2V 试点 → affine → 拼装；片头分钟已按正文回填\n"
    )
    print("OK media-map", stats, "missing", len(missing_stills))


if __name__ == "__main__":
    main()
