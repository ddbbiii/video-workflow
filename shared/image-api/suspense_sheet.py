# -*- coding: utf-8 -*-
"""Contact sheet for the suspense A/B: 5 shots x (OLD | NEW), plus a pricing check printout."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RUN = Path(__file__).resolve().parent / "runs" / "20261109-071606-suspense-ab"
OUT = RUN / "compare-suspense.png"
FONT = r"C:\Windows\Fonts\msyh.ttc"
SHOTS = [("S1-person", "S1 人物全身+手部"), ("S2-evidence", "S2 证据特写"),
         ("S3-corridor", "S3 夜走廊"), ("S4-lock", "S4 门锁特写"),
         ("S5-turnsheet", "S5 三视图拼版")]


def main() -> None:
    scale = 0.52
    tile_w, tile_h = int(2048 * scale), int(1152 * scale)
    pad, header = 10, 44
    width = tile_w * 2 + pad * 3
    height = header + (tile_h + pad) * len(SHOTS) + pad
    canvas = Image.new("RGB", (width, height), (14, 14, 16))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(FONT, 22)
    tag = ImageFont.truetype(FONT, 20)
    draw.text((pad, 10), "悬疑线 A/B · gpt-image-2.5-sunburst · 2048x1152 · 同一提示词",
              fill=(232, 232, 232), font=font)
    for index, (shot, label) in enumerate(SHOTS):
        y = header + index * (tile_h + pad)
        draw.text((pad, y + 2), label, fill=(210, 210, 210), font=tag)
        for col, relay in enumerate(("old", "new")):
            path = RUN / f"{relay}-{shot}.png"
            with Image.open(path) as image:
                thumb = image.convert("RGB").resize((tile_w, tile_h), Image.LANCZOS)
            x = pad + col * (tile_w + pad)
            canvas.paste(thumb, (x, y + 28))
            if index == 0:
                draw.text((x, y + 4), "OLD" if relay == "old" else "NEW", fill=(240, 200, 120) if relay == "old" else (120, 210, 240), font=tag)
    canvas.save(OUT)
    print(OUT, canvas.size)


if __name__ == "__main__":
    main()
