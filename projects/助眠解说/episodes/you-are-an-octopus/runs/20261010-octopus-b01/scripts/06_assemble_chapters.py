# -*- coding: utf-8 -*-
"""Assemble per-chapter draft MP4s from shot clips + chapter narration."""
from __future__ import annotations
import subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_common import (
    RUN, FFMPEG, FFPROBE, FPS, BODY_SECTIONS,
    load_json, atomic_json, update_checkpoint, log_stage, now_iso,
)

CHAPTERS = RUN / "chapters"
SHOT = RUN / "media" / "shot"
AUDIO = RUN / "audio"
CHAPTERS.mkdir(parents=True, exist_ok=True)


def concat_shots(shot_ids, out_video: Path):
    lst = out_video.with_suffix(".txt")
    paths = []
    for sid in shot_ids:
        p = SHOT / f"{sid}.mp4"
        if not p.is_file():
            raise FileNotFoundError(p)
        paths.append(p)
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in paths), encoding="utf-8")
    cmd = [str(FFMPEG), "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(out_video)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-600:])


def mux(video: Path, audio: Path, out: Path):
    cmd = [str(FFMPEG), "-y", "-i", str(video), "-i", str(audio),
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-600:])


def probe(path: Path):
    r = subprocess.run([str(FFPROBE), "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def main():
    update_checkpoint(stage="chapter_assembly",
                      completed=["create_run", "build_timeline", "build_media_map", "prepare_shot_media"],
                      running=["assemble_chapters"], next_action="chapter drafts")
    tl = load_json(RUN / "timeline.json")
    idx = load_json(RUN / "chapters_index.json")
    by_sec = {c["section"]: c for c in idx["chapters"]}
    results = []
    for sec in BODY_SECTIONS:
        if sec not in by_sec:
            continue
        ch = by_sec[sec]
        v_silent = CHAPTERS / f"{sec}_video.mp4"
        draft = CHAPTERS / f"{sec}_draft.mp4"
        log_stage("06_chapters", f"assemble {sec} shots={len(ch['shot_ids'])}")
        concat_shots(ch["shot_ids"], v_silent)
        narr = AUDIO / f"narration-{sec}.wav"
        if not narr.is_file():
            raise FileNotFoundError(narr)
        mux(v_silent, narr, draft)
        vd, ad = probe(v_silent), probe(narr)
        results.append({
            "section": sec,
            "draft": str(draft),
            "video_only": str(v_silent),
            "shot_count": len(ch["shot_ids"]),
            "video_s": vd,
            "audio_s": ad,
            "delta_s": vd - ad,
        })
        log_stage("06_chapters", f"{sec} video={vd:.3f} audio={ad:.3f} delta={vd-ad:.3f}")
    atomic_json(CHAPTERS / "chapters_manifest.json", {"created_at": now_iso(), "chapters": results})
    update_checkpoint(stage="chapter_assembly",
                      completed=["create_run", "build_timeline", "build_media_map", "prepare_shot_media", "assemble_chapters"],
                      running=[], next_action="intro resolve + full body concat + delivery")
    print("OK chapters", len(results))

if __name__ == "__main__":
    main()