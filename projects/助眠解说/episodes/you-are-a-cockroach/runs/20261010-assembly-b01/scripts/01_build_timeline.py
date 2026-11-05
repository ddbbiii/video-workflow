# -*- coding: utf-8 -*-
"""Build timeline.json from processed VO + utterances + SHOT_PLAN."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_common import (
    EP, RUN, SR, FPS, GAP_INTRA, GAP_INTER_PARA, GAP_INTER_CHAPTER,
    BODY_SECTIONS, VO_DIR, load_json, atomic_json, update_checkpoint, log_stage,
    vo_rel_path, now_iso,
)

def main():
    t0 = now_iso()
    update_checkpoint(stage="timeline", completed=["create_run"], running=["build_timeline"],
                      next_action="generate timeline.json")
    ut = load_json(EP / "audio" / "utterances.json")
    vm = load_json(VO_DIR / "manifest.json")
    sp = load_json(EP / "visual" / "SHOT_PLAN.json")
    items = vm["items"]

    body_utts = [u for u in ut["utterances"] if u["section"] in BODY_SECTIONS and u.get("runnable", True)]
    utterances = []
    cursor_samples = 0
    prev_section = None
    prev_para = None
    for u in body_utts:
        rel = vo_rel_path(u["id"])
        meta = items.get(rel)
        if not meta or not meta.get("ok"):
            raise SystemExit(f"missing processed vo: {rel}")
        path = str((VO_DIR / rel).resolve())
        if not Path(path).is_file():
            raise SystemExit(f"vo file missing: {path}")
        gap_s = 0.0
        if prev_section is not None:
            if u["section"] != prev_section:
                gap_s = GAP_INTER_CHAPTER
            elif u["paragraph_id"] != prev_para:
                gap_s = GAP_INTER_PARA
            else:
                gap_s = GAP_INTRA
        gap_samples = int(round(gap_s * SR))
        cursor_samples += gap_samples
        dur_s = float(meta["seconds"])
        dur_samples = int(round(dur_s * SR))
        start_sample = cursor_samples
        end_sample = start_sample + dur_samples
        utterances.append({
            "id": u["id"],
            "paragraph_id": u["paragraph_id"],
            "section": u["section"],
            "text": u["text"],
            "path": path,
            "sr": SR,
            "start_sample": start_sample,
            "end_sample": end_sample,
            "seconds": dur_s,
            "gap_before_s": gap_s,
        })
        cursor_samples = end_sample
        prev_section = u["section"]
        prev_para = u["paragraph_id"]

    total_samples = cursor_samples
    total_seconds = total_samples / SR

    para_map = {}
    for u in utterances:
        pid = u["paragraph_id"]
        if pid not in para_map:
            para_map[pid] = {"id": pid, "section": u["section"], "start_sample": u["start_sample"],
                             "end_sample": u["end_sample"], "utterance_ids": [u["id"]]}
        else:
            para_map[pid]["end_sample"] = u["end_sample"]
            para_map[pid]["utterance_ids"].append(u["id"])

    body_shots_plan = [s for s in sp["shots"] if not str(s["id"]).startswith("intro-art")]
    shots = []
    for s in body_shots_plan:
        pid = s["paragraph_id"]
        para = para_map[pid]
        a, b = s["anchor"]["paragraph_interval_share"]
        p0, p1 = para["start_sample"], para["end_sample"]
        span = p1 - p0
        start_sample = p0 + int(round(a * span))
        end_sample = p0 + int(round(b * span))
        if end_sample <= start_sample:
            end_sample = start_sample + max(1, int(round(0.1 * SR)))
        target_s = (end_sample - start_sample) / SR
        shots.append({
            "id": s["id"],
            "paragraph_id": pid,
            "section": para["section"],
            "utterance_ids": list(s.get("utterance_ids") or para["utterance_ids"]),
            "start_sample": start_sample,
            "end_sample": end_sample,
            "target_seconds": target_s,
            "media_candidate": s.get("media_candidate"),
            "shot_class_planned": ("image_to_video" if s.get("media_candidate") == "real_video" else "image_camera_motion"),
            "paragraph_interval_share": [a, b],
        })

    shots_sorted = sorted(shots, key=lambda x: (BODY_SECTIONS.index(x["section"]), x["start_sample"], x["id"]))
    for sh in shots_sorted:
        sh["start_frame"] = int(round(sh["start_sample"] * FPS / SR))
        sh["end_frame"] = int(round(sh["end_sample"] * FPS / SR))
        if sh["end_frame"] <= sh["start_frame"]:
            sh["end_frame"] = sh["start_frame"] + max(2, int(round(sh["target_seconds"] * FPS)))
        sh["frame_count"] = sh["end_frame"] - sh["start_frame"]
        sh["timeline_seconds"] = sh["frame_count"] / FPS

    for i in range(1, len(shots_sorted)):
        prev, cur = shots_sorted[i - 1], shots_sorted[i]
        if cur["start_frame"] != prev["end_frame"]:
            cur["start_frame"] = prev["end_frame"]
            if cur["end_frame"] <= cur["start_frame"]:
                cur["end_frame"] = cur["start_frame"] + max(2, prev.get("frame_count", 2))
            cur["frame_count"] = cur["end_frame"] - cur["start_frame"]
            cur["timeline_seconds"] = cur["frame_count"] / FPS

    total_frames = shots_sorted[-1]["end_frame"] if shots_sorted else 0
    timeline = {
        "schema_version": 1,
        "episode": "you-are-a-cockroach",
        "run": str(RUN),
        "created_at": t0,
        "sr": SR,
        "fps": FPS,
        "gaps": {"intra_utterance_s": GAP_INTRA, "inter_paragraph_s": GAP_INTER_PARA, "inter_chapter_s": GAP_INTER_CHAPTER},
        "body_total_samples": total_samples,
        "body_total_seconds_audio": total_seconds,
        "body_total_frames": total_frames,
        "body_total_seconds_video": total_frames / FPS,
        "vo_manifest_total_seconds": vm.get("total_seconds"),
        "vo_note": "manifest src is raw; paths here are processed wav; do not re-atempo",
        "utterances": utterances,
        "paragraphs": list(para_map.values()),
        "shots": shots_sorted,
        "intro": {"status": "pending_minute_resolve", "note": "intro-p03 not yet generated"},
    }
    out = RUN / "timeline.json"
    atomic_json(out, timeline)
    chapters = {}
    for sh in shots_sorted:
        chapters.setdefault(sh["section"], {"section": sh["section"], "shot_ids": [], "start_frame": sh["start_frame"], "end_frame": sh["end_frame"]})
        chapters[sh["section"]]["shot_ids"].append(sh["id"])
        chapters[sh["section"]]["end_frame"] = sh["end_frame"]
        chapters[sh["section"]]["start_frame"] = min(chapters[sh["section"]]["start_frame"], sh["start_frame"])
    for sec, ch in chapters.items():
        ch["start_sample"] = next(u["start_sample"] for u in utterances if u["section"] == sec)
        ch["end_sample"] = max(u["end_sample"] for u in utterances if u["section"] == sec)
        ch["audio_seconds"] = (ch["end_sample"] - ch["start_sample"]) / SR
        ch["video_seconds"] = (ch["end_frame"] - ch["start_frame"]) / FPS
    atomic_json(RUN / "chapters_index.json", {"chapters": [chapters[s] for s in BODY_SECTIONS if s in chapters]})
    log_stage("01_timeline", f"wrote {out}; audio_s={total_seconds:.3f}; video_s={total_frames/FPS:.3f}; shots={len(shots_sorted)}")
    update_checkpoint(stage="timeline", completed=["create_run", "build_timeline"], running=[],
                      next_action="build media-map.json")
    print(f"OK timeline shots={len(shots_sorted)} audio_s={total_seconds:.3f} video_s={total_frames/FPS:.3f}")

if __name__ == "__main__":
    main()