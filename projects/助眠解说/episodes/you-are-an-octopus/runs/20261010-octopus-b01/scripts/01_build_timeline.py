# -*- coding: utf-8 -*-
"""Build timeline.json from processed VO + utterances + SHOT_PLAN (octopus)."""
from __future__ import annotations
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_common import (
    EP, RUN, SR, FPS, GAP_INTRA, GAP_INTER_PARA, GAP_INTER_CHAPTER,
    BODY_SECTIONS, VO_DIR, load_json, atomic_json, update_checkpoint, log_stage,
    vo_rel_path, now_iso, write_status,
)


def split_beat(D: float, s01_strategy: str):
    """Return (s01_seconds, s02_seconds, effective_s01_strategy, note)."""
    if D <= 0:
        return 0.1, 0.1, "P1", "empty_beat_pad"
    if s01_strategy == "V3" and D >= 12.0:
        native = min(12.0, D - 4.0)
        s01 = native + 2.0  # native + default tail
        s02 = D - s01
        if s02 < 2.0:
            s02 = 2.0
            s01 = D - s02
        return s01, s02, "V3", "v3_native_plus_tail"
    # short V3 or planned P1: equal share
    note = "short_v3_to_two_p1" if s01_strategy == "V3" else "two_p1_equal"
    half = D / 2.0
    return half, half, "P1", note


def main():
    t0 = now_iso()
    update_checkpoint(stage="timeline", in_progress=["build_timeline"], next_action="generate timeline.json")
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
        meta = items.get(rel) or items.get(rel.replace("/", "\\"))
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
            para_map[pid] = {
                "id": pid, "section": u["section"],
                "start_sample": u["start_sample"], "end_sample": u["end_sample"],
                "utterance_ids": [u["id"]],
            }
        else:
            para_map[pid]["end_sample"] = u["end_sample"]
            para_map[pid]["utterance_ids"].append(u["id"])

    body_shots = [s for s in sp["shots"] if not str(s["id"]).startswith("intro-art")]
    by_beat = defaultdict(list)
    for s in body_shots:
        by_beat[s["beat_id"]].append(s)

    shots = []
    overflow_candidates = []
    for beat_id, ss in by_beat.items():
        ss = sorted(ss, key=lambda x: x.get("timing", {}).get("order", 99))
        if len(ss) != 2:
            raise SystemExit(f"beat {beat_id} has {len(ss)} shots, expected 2")
        pids = list(ss[0]["paragraph_ids"])
        if not pids:
            raise SystemExit(f"beat {beat_id} empty paragraph_ids")
        for pid in pids:
            if pid not in para_map:
                raise SystemExit(f"beat {beat_id} missing para {pid}")
        start_sample = para_map[pids[0]]["start_sample"]
        end_sample = para_map[pids[-1]]["end_sample"]
        # extend if middle paras out of order
        for pid in pids:
            start_sample = min(start_sample, para_map[pid]["start_sample"])
            end_sample = max(end_sample, para_map[pid]["end_sample"])
        D = (end_sample - start_sample) / SR
        s01_plan = ss[0].get("strategy") or "P1"
        s01_s, s02_s, eff, note = split_beat(D, s01_plan)
        s01_samples = int(round(s01_s * SR))
        # ensure cover full beat
        if s01_samples >= (end_sample - start_sample):
            s01_samples = max(1, (end_sample - start_sample) // 2)
        mid = start_sample + s01_samples
        utt_ids = []
        for pid in pids:
            utt_ids.extend(para_map[pid]["utterance_ids"])

        specs = [
            (ss[0], start_sample, mid, eff, note),
            (ss[1], mid, end_sample, "P1", "remainder_or_equal"),
        ]
        for shot, a, b, strat, snote in specs:
            target_s = (b - a) / SR
            planned = shot.get("strategy") or "P1"
            shot_class = "image_to_video" if strat == "V3" else "image_camera_motion"
            # overflow marker for long P1 remainder
            extra_views = 0
            if strat == "P1" and target_s > 24.0:
                extra_views = int(math.ceil(target_s / 24.0)) - 1
                overflow_candidates.append({
                    "shot_id": shot["id"], "beat_id": beat_id,
                    "target_seconds": target_s, "extra_views": extra_views,
                    "rule": "split_remaining_P1_every_24s",
                })
            shots.append({
                "id": shot["id"],
                "beat_id": beat_id,
                "paragraph_ids": pids,
                "section": shot["section"],
                "utterance_ids": utt_ids,
                "start_sample": a,
                "end_sample": b,
                "target_seconds": target_s,
                "strategy_planned": planned,
                "strategy_effective": strat,
                "shot_class_planned": shot.get("shot_class"),
                "shot_class_effective": shot_class,
                "allocation_note": snote,
                "motion_prompt": shot.get("motion_prompt"),
                "image_motion": shot.get("image_motion"),
                "tail_extension_seconds": shot.get("tail_extension_seconds", 0),
                "overflow_extra_views": extra_views,
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
    # intro processed seconds (p001+p002; p003 pending)
    intro_utts = [u for u in ut["utterances"] if u["section"] == "intro" and u.get("runnable", True)]
    intro_seconds = 0.0
    for u in intro_utts:
        rel = vo_rel_path(u["id"])
        meta = items.get(rel) or items.get(rel.replace("/", "\\"))
        if meta and meta.get("ok"):
            intro_seconds += float(meta["seconds"])

    timeline = {
        "schema_version": 1,
        "episode": "you-are-an-octopus",
        "run": str(RUN),
        "created_at": t0,
        "sr": SR,
        "fps": FPS,
        "gaps": {
            "intra_utterance_s": GAP_INTRA,
            "inter_paragraph_s": GAP_INTER_PARA,
            "inter_chapter_s": GAP_INTER_CHAPTER,
        },
        "body_total_samples": total_samples,
        "body_total_seconds_audio": total_seconds,
        "body_total_frames": total_frames,
        "body_total_seconds_video": total_frames / FPS,
        "vo_manifest_total_seconds": vm.get("total_seconds"),
        "intro_processed_seconds_partial": round(intro_seconds, 3),
        "vo_note": "manifest src is seed7-final; paths are processed atempo0.7304; do not re-atempo",
        "utterances": utterances,
        "paragraphs": list(para_map.values()),
        "shots": shots_sorted,
        "overflow_candidates": overflow_candidates,
        "intro": {"status": "pending_minute_resolve", "note": "intro-p03 not yet generated; use prepare_handoff after body seconds"},
        "v3_effective_count": sum(1 for s in shots_sorted if s["strategy_effective"] == "V3"),
        "p1_effective_count": sum(1 for s in shots_sorted if s["strategy_effective"] == "P1"),
    }
    out = RUN / "timeline.json"
    atomic_json(out, timeline)

    chapters = {}
    for sh in shots_sorted:
        chapters.setdefault(sh["section"], {
            "section": sh["section"], "shot_ids": [],
            "start_frame": sh["start_frame"], "end_frame": sh["end_frame"],
        })
        chapters[sh["section"]]["shot_ids"].append(sh["id"])
        chapters[sh["section"]]["end_frame"] = sh["end_frame"]
        chapters[sh["section"]]["start_frame"] = min(chapters[sh["section"]]["start_frame"], sh["start_frame"])
    for sec, ch in chapters.items():
        ch["start_sample"] = next(u["start_sample"] for u in utterances if u["section"] == sec)
        ch["end_sample"] = max(u["end_sample"] for u in utterances if u["section"] == sec)
        ch["audio_seconds"] = (ch["end_sample"] - ch["start_sample"]) / SR
        ch["video_seconds"] = (ch["end_frame"] - ch["start_frame"]) / FPS
    atomic_json(RUN / "chapters_index.json", {"chapters": [chapters[s] for s in BODY_SECTIONS if s in chapters]})

    log_stage(
        "01_timeline",
        f"wrote {out}; audio_s={total_seconds:.3f}; video_s={total_frames/FPS:.3f}; "
        f"shots={len(shots_sorted)}; v3_eff={timeline['v3_effective_count']}; overflow={len(overflow_candidates)}",
    )
    update_checkpoint(
        stage="timeline_done",
        in_progress=["stills"],
        completed=list(dict.fromkeys((load_json(RUN / "CHECKPOINT.json").get("completed") or []) + [
            "tts", "vo_gate", "vo_process", "timeline",
        ])),
        next_action="continue stills to 198; then I2V pilot when GPU free; affine+assemble",
        body_seconds=round(total_seconds, 2),
        timeline_video_seconds=round(total_frames / FPS, 2),
        vo_processed_count=len(items),
        vo_processed_total_s=vm.get("total_seconds"),
        v3_effective=timeline["v3_effective_count"],
        overflow_candidate_count=len(overflow_candidates),
    )
    write_status(
        f"# STATUS 你是一只章鱼 — 20261010-octopus-b01\n\n"
        f"- 时间：{now_iso()}\n"
        f"- TTS/门禁/atempo：完成（280 wav，processed total≈{vm.get('total_seconds')}s）\n"
        f"- 时间轴：正文音频 {total_seconds:.1f}s / 视频 {total_frames/FPS:.1f}s；V3有效 {timeline['v3_effective_count']}；溢出候选 {len(overflow_candidates)}\n"
        f"- 下一：静帧补齐→I2V试点→affine→章节拼装；片头分钟句待正文秒回填\n"
    )
    print(
        f"OK timeline shots={len(shots_sorted)} audio_s={total_seconds:.3f} "
        f"video_s={total_frames/FPS:.3f} v3_eff={timeline['v3_effective_count']} overflow={len(overflow_candidates)}"
    )


if __name__ == "__main__":
    main()
