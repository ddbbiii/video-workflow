# -*- coding: utf-8 -*-
"""Build SRT/ASS from timeline utterance timings (processed VO; no ASR required for draft)."""
from __future__ import annotations
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_common import RUN, SR, FONT_DIR, load_json, atomic_json, log_stage, now_iso

SUBS = RUN / "subs"
SUBS.mkdir(parents=True, exist_ok=True)

MAX_CHARS = 22


def srt_ts(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def ass_ts(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    cs = int(round(seconds * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def clean_display(text: str) -> str:
    t = text.strip()
    t = re.sub(r"[。！？；;，,、：:]+$", "", t)
    return t


def split_lines(text: str) -> list[str]:
    t = clean_display(text)
    if len(t) <= MAX_CHARS:
        return [t]
    # split on punctuation first
    parts = re.split(r"(?<=[，,、；;：:])", t)
    lines, buf = [], ""
    for p in parts:
        if not p:
            continue
        if buf and len(buf) + len(p) > MAX_CHARS:
            lines.append(clean_display(buf))
            buf = p
        else:
            buf += p
    if buf:
        lines.append(clean_display(buf))
    # hard wrap leftovers
    out = []
    for line in lines:
        while len(line) > MAX_CHARS:
            out.append(line[:MAX_CHARS])
            line = line[MAX_CHARS:]
        if line:
            out.append(line)
    return out or [t]


def main():
    tl = load_json(RUN / "timeline.json")
    events = []
    for u in tl["utterances"]:
        start = u["start_sample"] / SR
        end = u["end_sample"] / SR
        # display end +0.3s but not into next
        end_disp = end + 0.3
        lines = split_lines(u["text"])
        # distribute time across lines if multiple
        if len(lines) == 1:
            events.append({"start": start, "end": end_disp, "text": lines[0], "uid": u["id"]})
        else:
            span = max(0.7, end - start)
            piece = span / len(lines)
            for i, line in enumerate(lines):
                s = start + i * piece
                e = start + (i + 1) * piece
                if i == len(lines) - 1:
                    e = end_disp
                events.append({"start": s, "end": e, "text": line, "uid": u["id"]})

    # prevent overlaps
    for i in range(len(events) - 1):
        if events[i]["end"] > events[i + 1]["start"] - 0.04:
            events[i]["end"] = max(events[i]["start"] + 0.05, events[i + 1]["start"] - 0.04)

    srt_path = SUBS / "body.srt"
    with srt_path.open("w", encoding="utf-8") as f:
        for i, ev in enumerate(events, 1):
            f.write(f"{i}\n{srt_ts(ev['start'])} --> {srt_ts(ev['end'])}\n{ev['text']}\n\n")

    ass_path = SUBS / "body.ass"
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Source Han Sans SC Heavy,96,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,5,2,2,96,96,118,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with ass_path.open("w", encoding="utf-8") as f:
        f.write(header)
        for ev in events:
            f.write(f"Dialogue: 0,{ass_ts(ev['start'])},{ass_ts(ev['end'])},Default,,0,0,0,,{ev['text']}\n")

    atomic_json(SUBS / "subtitle_events.json", {"created_at": now_iso(), "count": len(events), "events": events,
                                               "fontsdir": str(FONT_DIR), "note": "draft timing from processed VO utterance bounds; ASR refine optional"})
    log_stage("05_subs", f"srt={srt_path} ass={ass_path} events={len(events)}")
    print(f"OK subs events={len(events)}")

if __name__ == "__main__":
    main()