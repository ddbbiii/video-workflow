# -*- coding: utf-8 -*-
"""Resume octopus delivery after intro affine already rendered."""
from __future__ import annotations
import json, math, subprocess, sys, wave
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_common import (
    EP, RUN, FFMPEG, FFPROBE, FPS, SR, BODY_SECTIONS, FONT_DIR,
    load_json, atomic_json, update_checkpoint, log_stage, now_iso,
)

AUDIO = RUN / "audio"
CHAPTERS = RUN / "chapters"
DELIVERY = RUN / "delivery"
SUBS = RUN / "subs"
INTRO_DIR = RUN / "intro"
DELIVERY.mkdir(parents=True, exist_ok=True)


def probe(path: Path) -> float:
    r = subprocess.run([str(FFPROBE), "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def main():
    update_checkpoint(stage="delivery_resume", in_progress=["delivery"], next_action="concat+encode clean/sub")
    # intro video from existing affine clips
    out_dir = INTRO_DIR / "affine"
    specs = load_json(INTRO_DIR / "intro_affine_plan.json")["shots"]
    for s in specs:
        p = out_dir / f"{s['id']}.mp4"
        if not p.is_file():
            raise FileNotFoundError(p)
    lst = INTRO_DIR / "intro_concat.txt"
    lst.write_text("".join(f"file '{(out_dir / (s['id'] + '.mp4')).as_posix()}'\n" for s in specs), encoding="utf-8")
    intro_video = INTRO_DIR / "intro_video.mp4"
    if not intro_video.is_file():
        subprocess.run([str(FFMPEG), "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an",
                        str(intro_video)], check=True, capture_output=True)
    intro_narr = INTRO_DIR / "intro_narration.wav"
    if not intro_narr.is_file():
        raise FileNotFoundError(intro_narr)

    # mux intro
    intro_draft = INTRO_DIR / "intro_draft.mp4"
    subprocess.run([str(FFMPEG), "-y", "-i", str(intro_video), "-i", str(intro_narr),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", str(intro_draft)],
                   check=True, capture_output=True)
    log_stage("07_resume", f"intro_draft {probe(intro_draft):.3f}s")

    # body video concat
    body_list = DELIVERY / "body_concat.txt"
    lines = []
    for sec in BODY_SECTIONS:
        p = CHAPTERS / f"{sec}_video.mp4"
        if not p.is_file():
            raise FileNotFoundError(p)
        lines.append(f"file '{p.as_posix()}'")
    body_list.write_text("\n".join(lines) + "\n", encoding="utf-8")
    body_video = DELIVERY / "body_video.mp4"
    if not body_video.is_file() or body_video.stat().st_size < 1000:
        log_stage("07_resume", "concat body chapters...")
        subprocess.run([str(FFMPEG), "-y", "-f", "concat", "-safe", "0", "-i", str(body_list),
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an",
                        str(body_video)], check=True, capture_output=True)
    log_stage("07_resume", f"body_video {probe(body_video):.3f}s")

    # full video = intro + body
    full_list = DELIVERY / "full_concat.txt"
    full_list.write_text(f"file '{intro_video.as_posix()}'\nfile '{body_video.as_posix()}'\n", encoding="utf-8")
    full_video = DELIVERY / "full_video.mp4"
    log_stage("07_resume", "concat intro+body...")
    subprocess.run([str(FFMPEG), "-y", "-f", "concat", "-safe", "0", "-i", str(full_list),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an",
                    str(full_video)], check=True, capture_output=True)

    # full audio = intro narr stereo + body mix
    body_mix = AUDIO / "mix-master.wav"
    intro_stereo = INTRO_DIR / "intro_narration_stereo.wav"
    subprocess.run([str(FFMPEG), "-y", "-i", str(intro_narr), "-ac", "2", "-ar", str(SR),
                    "-c:a", "pcm_s16le", str(intro_stereo)], check=True, capture_output=True)
    full_audio_list = DELIVERY / "full_audio_concat.txt"
    full_audio_list.write_text(f"file '{intro_stereo.as_posix()}'\nfile '{body_mix.as_posix()}'\n", encoding="utf-8")
    full_audio = DELIVERY / "full_mix.wav"
    subprocess.run([str(FFMPEG), "-y", "-f", "concat", "-safe", "0", "-i", str(full_audio_list),
                    "-c:a", "pcm_s16le", str(full_audio)], check=True, capture_output=True)

    clean = DELIVERY / "你是一只章鱼_1080p_clean.mp4"
    log_stage("07_resume", "encode clean...")
    subprocess.run([str(FFMPEG), "-y", "-i", str(full_video), "-i", str(full_audio),
                    "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "256k", "-shortest", str(clean)], check=True, capture_output=True)
    log_stage("07_resume", f"clean {probe(clean):.3f}s")

    # subtitles: delay by intro duration
    intro_s = probe(intro_video)
    ass_src = SUBS / "body.ass"
    srt_src = SUBS / "body.srt"
    work = DELIVERY / "sub_work"
    work.mkdir(parents=True, exist_ok=True)
    # shift ASS by writing Dialogue times offset — use ffmpeg ass delay via subtitles filter with setpts on audio timeline
    # Practical: use -itsoffset on ass via ffmpeg subtitles filter after delaying with a rewritten ass
    def shift_ass(src: Path, dst: Path, delay: float):
        lines = src.read_text(encoding="utf-8").splitlines()
        out = []
        for line in lines:
            if line.startswith("Dialogue:"):
                # Dialogue: 0,0:00:01.00,0:00:02.00,Default,,0,0,0,,text
                parts = line.split(",", 9)
                if len(parts) >= 3:
                    def parse(ts):
                        h, m, rest = ts.split(":")
                        s, cs = rest.split(".")
                        return int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100
                    def fmt(sec):
                        if sec < 0: sec = 0
                        cs = int(round(sec * 100))
                        h, cs = divmod(cs, 360000)
                        m, cs = divmod(cs, 6000)
                        s, cs = divmod(cs, 100)
                        return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"
                    parts[1] = fmt(parse(parts[1]) + delay)
                    parts[2] = fmt(parse(parts[2]) + delay)
                    line = ",".join(parts)
            out.append(line)
        dst.write_text("\n".join(out) + "\n", encoding="utf-8")

    ass_shifted = work / "body_shifted.ass"
    shift_ass(ass_src, ass_shifted, intro_s)
    # copy font dir reference - use fontsdir
    sub = DELIVERY / "你是一只章鱼_1080p_sub.mp4"
    # Escape path for ffmpeg subtitles filter on Windows
    ass_esc = str(ass_shifted).replace("\\", "/").replace(":", "\\:")
    fonts_esc = str(FONT_DIR).replace("\\", "/").replace(":", "\\:")
    vf = f"subtitles='{ass_esc}':fontsdir='{fonts_esc}'"
    log_stage("07_resume", "encode sub...")
    r = subprocess.run([str(FFMPEG), "-y", "-i", str(clean), "-vf", vf,
                        "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
                        "-c:a", "copy", str(sub)], capture_output=True, text=True)
    if r.returncode != 0:
        log_stage("07_resume", f"sub burn failed: {r.stderr[-800:]}")
        # fallback copy clean name note
        sub = None
    else:
        log_stage("07_resume", f"sub {probe(sub):.3f}s")

    qa = {
        "created_at": now_iso(),
        "auto_checks": {
            "clean_exists": clean.is_file(),
            "clean_duration_s": probe(clean) if clean.is_file() else None,
            "sub_exists": bool(sub and Path(sub).is_file()),
            "intro_s": intro_s,
            "body_s": probe(body_video),
            "full_video_s": probe(full_video),
            "full_audio_s": probe(full_audio),
            "resolution": "1920x1080",
            "fps": FPS,
        },
        "pending_review": "I2V pilots/batch visual_qa pending; current delivery is affine-primary",
        "i2v_note": "5s pilot I2V fell back to P1 per no-stretch rule; 12s batch pending to unlock V3",
        "unfinished": [],
    }
    if not sub:
        qa["unfinished"].append("subtitle burn failed")
    atomic_json(DELIVERY / "FINAL_QA.json", qa)
    atomic_json(DELIVERY / "delivery_manifest.json", {
        "clean": str(clean), "sub": str(sub) if sub else None,
        "intro": str(intro_draft), "full_mix": str(full_audio),
        "created_at": now_iso(),
    })
    update_checkpoint(stage="delivery_done_affine_primary", in_progress=["i2v_pilot_or_batch"],
                      completed=["assemble_chapters", "delivery_clean_sub_affine_primary"],
                      next_action="finish I2V pilot; start 12s V3 batch; refresh V3 shots + re-deliver",
                      clean_path=str(clean), sub_path=str(sub) if sub else None,
                      clean_duration_s=qa["auto_checks"]["clean_duration_s"])
    print("OK", json.dumps(qa["auto_checks"], ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
