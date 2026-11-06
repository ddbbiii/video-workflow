# -*- coding: utf-8 -*-
"""Restyle intro transition subtitles to style_r4 96, keep Hook/Title cards."""
import re
from pathlib import Path
from PIL import ImageFont

INTRO = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws\runs\20261106-ulw-b01\intro")
FONT_PATH = r"E:\program\1project\video\assets\助眠解说\subtitles\style-r4\fonts\SourceHanSansSC-Heavy.otf"
MAX_W = 1500.0
SIZES = [96, 84, 72, 64]


def clean(t):
    t = re.sub(r"\{\\[^}]*\}", "", t)
    return t.replace("\\N", "").strip()


def wrap(text, font, max_w, max_lines=3):
    clauses = re.findall(r"[^，；：、]*[，；：、]?", text)
    clauses = [c for c in clauses if c]
    lines, cur = [], ""
    for cl in clauses:
        if font.getlength(cur + cl) <= max_w:
            cur += cl
        else:
            if cur:
                lines.append(cur); cur = ""
            if font.getlength(cl) <= max_w:
                cur = cl
            else:
                for ch in cl:
                    if cur and font.getlength(cur + ch) > max_w:
                        lines.append(cur); cur = ""
                    cur += ch
    if cur:
        lines.append(cur)
    return lines if len(lines) <= max_lines else None


def main():
    src = INTRO / "intro.ass"
    lines = src.read_text(encoding="utf-8-sig").splitlines()

    new_bodies = []
    for l in lines:
        if l.startswith("Dialogue:"):
            p = l.split(",", 9)
            if p[3] != "body":
                continue
            text = clean(p[9])
            chosen = None
            for size in SIZES:
                f = ImageFont.truetype(FONT_PATH, size)
                ls = wrap(text, f, MAX_W, 3)
                if ls:
                    chosen = (size, ls); break
            if not chosen:
                chosen = (56, [text])
            size, ls = chosen
            body = "\\N".join(ls)
            if size != 96:
                body = "{\\fs%d}" % size + body
            new_bodies.append((p[1], p[2], body))
    print("body cues", len(new_bodies))

    out, bi = [], 0
    for l in lines:
        if l.startswith("Style: body"):
            out.append("Style: body,Source Han Sans SC Heavy,96,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,5,2,2,96,96,118,1")
        elif l.startswith("Dialogue:"):
            p = l.split(",", 9)
            if p[3] == "body":
                st, en, txt = new_bodies[bi]; bi += 1
                out.append("Dialogue: 0,%s,%s,body,,0,0,0,,%s" % (st, en, txt))
            else:
                out.append(l)
        else:
            out.append(l)
    (INTRO / "intro_r4.ass").write_text("\ufeff" + "\n".join(out) + "\n", encoding="utf-8")
    print("written", INTRO / "intro_r4.ass")


if __name__ == "__main__":
    main()
