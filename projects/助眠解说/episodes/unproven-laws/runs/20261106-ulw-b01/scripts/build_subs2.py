# -*- coding: utf-8 -*-
"""Rebuild body subtitles with short, fully visible cues."""
import json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from subsplit import timed_cues

RUN = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws\runs\20261106-ulw-b01")
OUT = RUN / "subtitles"
OUT.mkdir(exist_ok=True)


def ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return "%d:%02d:%05.2f" % (h, m, s)


def intro_dur():
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(RUN / "intro" / "intro.mp4")],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def main():
    tl = json.loads((RUN / "timeline.json").read_text(encoding="utf-8"))
    off = intro_dur()
    head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: body,SourceHanSansSC,54,&H00E8F0F5,&H00E8F0F5,&H0012100C,&H00000000,0,0,0,0,100,100,0,0,1,3,0,2,110,110,72,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for u in tl["utterances"]:
        for s, e, text in timed_cues(u["start"], u["end"] - u["start"], u["text"], maxlen=18, max_lines=1):
            events.append("Dialogue: 0,%s,%s,body,,0,0,0,,%s" % (ts(s + off), ts(e + off), text))
    # write utf-8 with BOM for libass
    (OUT / "body.ass").write_text("\ufeff" + head + "\n".join(events) + "\n", encoding="utf-8")
    srt = []
    for i, u in enumerate(tl["utterances"], 1):
        def st(t):
            t += off; h = int(t // 3600); m = int(t % 3600 // 60); s = int(t % 60); ms = int((t % 1) * 1000)
            return "%02d:%02d:%02d,%03d" % (h, m, s, ms)
        srt.append("%d\n%s --> %s\n%s\n" % (i, st(u["start"]), st(u["end"]), u["text"]))
    (OUT / "body.srt").write_text("\n".join(srt), encoding="utf-8")
    print("cues", len(events), "intro", round(off, 2))


if __name__ == "__main__":
    main()
