# -*- coding: utf-8 -*-
"""Assemble the single overview deliverable: 4 rows (panels) x 2 columns (old/new)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RUN = Path(__file__).resolve().parent / "runs" / "20261109-063916-grid2x2-ab"
CELLS = RUN / "cells"
OUT = RUN / "compare" / "overview-4x2.png"
FONT = r"C:\Windows\Fonts\arial.ttf"
GAP = 8
HEADER = 40
LABEL_W = 118


def main() -> None:
    cell_w, cell_h = Image.open(CELLS / "old-p1.png").size
    scale = 0.62
    thumb_w, thumb_h = int(cell_w * scale), int(cell_h * scale)
    width = LABEL_W + thumb_w * 2 + GAP * 3
    height = HEADER + (thumb_h + GAP) * 4 + GAP
    canvas = Image.new("RGB", (width, height), (14, 14, 16))
    draw = ImageDraw.Draw(canvas)
    title = ImageFont.truetype(FONT, 22)
    label = ImageFont.truetype(FONT, 18)
    small = ImageFont.truetype(FONT, 15)
    draw.text((GAP, 10), "Complex 2x2 grid, identical prompt · gpt-image-2.5-sunburst · 2048x1152",
              fill=(232, 232, 232), font=title)
    draw.text((LABEL_W + GAP + thumb_w // 2 - 40, HEADER - 2), "OLD · dklapi", fill=(240, 200, 120), font=label)
    draw.text((LABEL_W + GAP * 2 + thumb_w + thumb_w // 2 - 45, HEADER - 2), "NEW · mxwell",
              fill=(120, 210, 240), font=label)
    names = {1: "P1 wide\n3 chimneys", 2: "P2 macro\n5 tubeworms", 3: "P3 ROV arm\nsample", 4: "P4 vent rim\n4 shrimp"}
    for index in range(1, 5):
        y = HEADER + 24 + (index - 1) * (thumb_h + GAP)
        for line_no, line in enumerate(names[index].split("\n")):
            draw.text((GAP, y + thumb_h // 2 - 18 + line_no * 20), line, fill=(210, 210, 210), font=small)
        for col, tag in enumerate(("old", "new")):
            x = LABEL_W + GAP + col * (thumb_w + GAP)
            thumb = Image.open(CELLS / f"{tag}-p{index}.png").convert("RGB").resize(
                (thumb_w, thumb_h), Image.LANCZOS)
            canvas.paste(thumb, (x, y))
    canvas.save(OUT)
    print(OUT, canvas.size)


if __name__ == "__main__":
    main()
