# -*- coding: utf-8 -*-
"""Build ASS subtitles from the utterance timeline, offset by intro duration."""
import json, subprocess
from pathlib import Path

RUN = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws\runs\20261106-ulw-b01")
OUT = RUN / "subtitles"
OUT.mkdir(exist_ok=True)


def ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return "%d:%02d:%05.2f" % (h, m, s)


def intro_dur():
    p = RUN / "intro" / "intro.mp4"
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(p)], capture_output=True, text=True)
    return float(r.stdout.strip())


def main():
    tl = json.loads((RUN / "timeline.json").read_text(encoding="utf-8"))
    off = intro_dur()
    head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: body,SourceHanSansSC,54,&H00E8F0F5,&H00E8F0F5,&H0012100C,&H00000000,0,0,0,0,100,100,0,0,1,3,0,2,120,120,72,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for u in tl["utterances"]:
        st, en = u["start"] + off, u["end"] + off
        txt = u["text"].replace("\n", " ")
        lines.append("Dialogue: 0,%s,%s,body,,0,0,0,,%s" % (ts(st), ts(en), txt))
    (OUT / "body.ass").write_text(head + "\n".join(lines) + "\n", encoding="utf-8")

    srt = []
    for i, u in enumerate(tl["utterances"], 1):
        def st(t):
            t += off; h = int(t // 3600); m = int(t % 3600 // 60); s = int(t % 60); ms = int((t % 1) * 1000)
            return "%02d:%02d:%02d,%03d" % (h, m, s, ms)
        srt.append("%d\n%s --> %s\n%s\n" % (i, st(u["start"]), st(u["end"]), u["text"]))
    (OUT / "body.srt").write_text("\n".join(srt), encoding="utf-8")
    print("subs", len(lines), "intro_off", round(off, 2))


if __name__ == "__main__":
    main()
