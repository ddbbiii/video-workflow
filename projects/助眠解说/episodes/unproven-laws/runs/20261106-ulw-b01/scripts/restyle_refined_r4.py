# -*- coding: utf-8 -*-
"""Restyle refined subtitle timeline to approved style_r4 (96px, max 3 lines)."""
import re
from pathlib import Path
from PIL import ImageFont

RUN = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws\runs\20261106-ulw-b01")
FONT_PATH = r"E:\program\1project\video\assets\助眠解说\subtitles\style-r4\fonts\SourceHanSansSC-Heavy.otf"
MAX_W = 1500.0
SIZES = [96, 84, 72, 64]


def clean(t):
    t = re.sub(r"\{\\fs\d+\}", "", t)
    return t.replace("\\N", "").strip()


def wrap(text, font, max_w, max_lines=3):
    lines, cur = [], ""
    for ch in text:
        if font.getlength(cur + ch) > max_w and cur:
            lines.append(cur); cur = ""
            if len(lines) >= max_lines:
                return None
        cur += ch
    if cur:
        lines.append(cur)
    return lines if len(lines) <= max_lines else None


def main():
    src = RUN / "subtitles" / "body_refined.ass"
    rows = []
    for l in src.read_text(encoding="utf-8-sig").splitlines():
        if l.startswith("Dialogue:"):
            p = l.split(",", 9)
            rows.append((p[1], p[2], clean(p[9])))
    print("cues", len(rows))

    events = []
    sizes = {}
    for st, en, text in rows:
        chosen = None
        for size in SIZES:
            f = ImageFont.truetype(FONT_PATH, size)
            lines = wrap(text, f, MAX_W, 3)
            if lines:
                chosen = (size, lines); break
        if not chosen:
            f = ImageFont.truetype(FONT_PATH, 56)
            chosen = (56, wrap(text, f, MAX_W, 4) or [text])
        size, lines = chosen
        sizes[size] = sizes.get(size, 0) + 1
        body = "\\N".join(lines)
        if size != 96:
            body = "{\\fs%d}" % size + body
        events.append((st, en, body))
    print("sizes", sizes)

    head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: body,Source Han Sans SC Heavy,96,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,5,2,2,96,96,118,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    out = "\n".join("Dialogue: 0,%s,%s,body,,0,0,0,,%s" % (s, e, t) for s, e, t in events)
    (RUN / "subtitles" / "body_refined_r4.ass").write_text("\ufeff" + head + out + "\n", encoding="utf-8")
    print("written", RUN / "subtitles" / "body_refined_r4.ass")


if __name__ == "__main__":
    main()
