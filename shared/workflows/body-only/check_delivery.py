# -*- coding: utf-8 -*-
"""Deliverable gate for the 2026-11-14 body-only contract.

Checks a final video + its SRT:
  * exactly one video stream, zero audio streams, zero subtitle streams
  * duration matches frame count / frame rate within 1.5 frames
  * SRT starts at 00:00:00,000 (body-only timeline), ends within the video
  * every cue <= 20 visible characters, single line
  * cue text is non-empty

Exit code 1 on any failure. Usage:
  python check_delivery.py --video <final>.mp4 --srt <final>.srt
"""
import argparse
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

TS = re.compile(
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*"
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})"
)


def visible_len(text):
    return sum(1 for ch in text if unicodedata.category(ch)[0] in ("L", "N"))


def ts_seconds(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000.0


def probe(video):
    cmd = ["ffprobe", "-v", "error", "-print_format", "json",
           "-show_streams", "-show_format", str(video)]
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if out.returncode != 0:
        raise RuntimeError("ffprobe failed: " + (out.stderr or "").strip())
    data = json.loads(out.stdout)
    streams = data.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    sub_streams = [s for s in streams if s.get("codec_type") == "subtitle"]
    fmt = data.get("format", {})
    duration = float(fmt.get("duration") or 0.0)
    v = video_streams[0] if video_streams else {}
    rate = v.get("avg_frame_rate") or v.get("r_frame_rate") or "0/1"
    try:
        num, den = rate.split("/")
        fps = float(num) / float(den) if float(den) else 0.0
    except Exception:
        fps = 0.0
    frames = v.get("nb_frames")
    try:
        frames = int(frames) if frames not in (None, "N/A") else None
    except Exception:
        frames = None
    if frames is None and fps > 0:
        frames = int(round(duration * fps))
    return dict(duration=duration, fps=fps, frames=frames,
                n_video=len(video_streams), n_audio=len(audio_streams),
                n_sub=len(sub_streams), width=v.get("width"), height=v.get("height"))


def read_srt(path):
    raw = Path(path).read_text(encoding="utf-8-sig")
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    cues = []
    for block in re.split(r"\n\s*\n", raw.strip()):
        lines = block.split("\n")
        ti = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if ti is None:
            continue
        m = TS.search(lines[ti])
        if not m:
            continue
        start = ts_seconds(*m.groups()[:4])
        end = ts_seconds(*m.groups()[4:])
        text_lines = [x.strip() for x in lines[ti + 1:] if x.strip()]
        cues.append(dict(start=start, end=end, text=" ".join(text_lines),
                         multiline=len(text_lines) > 1))
    return cues


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--srt", required=True)
    ap.add_argument("--max-chars", type=int, default=20)
    ap.add_argument("--start-tolerance", type=float, default=0.001)
    ap.add_argument("--json", default="")
    args = ap.parse_args(argv)

    fails = []
    info = {}

    if not Path(args.video).exists():
        fails.append("video not found: %s" % args.video)
    if not Path(args.srt).exists():
        fails.append("srt not found: %s" % args.srt)
    if fails:
        print("FAIL: " + "; ".join(fails))
        return 1

    try:
        p = probe(args.video)
    except Exception as exc:
        print("FAIL: %s" % exc)
        return 1
    info.update(p)
    if p["n_video"] != 1:
        fails.append("video streams = %d (want 1)" % p["n_video"])
    if p["n_audio"] != 0:
        fails.append("audio streams = %d (want 0)" % p["n_audio"])
    if p["n_sub"] != 0:
        fails.append("subtitle streams = %d (want 0)" % p["n_sub"])
    if p["duration"] <= 0:
        fails.append("duration <= 0")
    if p["frames"] and p["fps"] > 0:
        expected = p["frames"] / p["fps"]
        if abs(expected - p["duration"]) > 1.5 / p["fps"]:
            fails.append("duration %.3fs vs frames/fps %.3fs (>1.5 frames)"
                         % (p["duration"], expected))

    cues = read_srt(args.srt)
    info["cues"] = len(cues)
    if not cues:
        fails.append("no SRT cues parsed")
    else:
        first, last = cues[0]["start"], max(c["end"] for c in cues)
        info["first_start"] = first
        info["last_end"] = last
        if abs(first - 0.0) > args.start_tolerance:
            fails.append("first cue starts at %.3fs (want 0.000; body-only timeline)" % first)
        if p["duration"] and last > p["duration"] + 0.05:
            fails.append("last cue ends at %.3fs > video %.3fs" % (last, p["duration"]))
        over = [i + 1 for i, c in enumerate(cues) if visible_len(c["text"]) > args.max_chars]
        if over:
            fails.append("cues over %d chars: %s" % (args.max_chars, over[:10]))
        multiline = [i + 1 for i, c in enumerate(cues) if c["multiline"]]
        if multiline:
            fails.append("multiline cues: %s" % multiline[:10])
        empty = [i + 1 for i, c in enumerate(cues) if not c["text"].strip()]
        if empty:
            fails.append("empty cues: %s" % empty[:10])
        info["max_chars"] = max(visible_len(c["text"]) for c in cues)

    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(
            dict(video=args.video, srt=args.srt, info=info, fails=fails),
            ensure_ascii=False, indent=1), encoding="utf-8")

    if fails:
        print("FAIL")
        for f in fails:
            print(" - " + f)
        return 1

    print("PASS  video=%dx%d %.3fs %d frames @ %.3f fps  streams=1/0/0  "
          "cues=%d first=0.000 max_chars=%d"
          % (info.get("width") or 0, info.get("height") or 0, info["duration"],
             info.get("frames") or 0, info.get("fps") or 0,
             info["cues"], info.get("max_chars") or 0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
