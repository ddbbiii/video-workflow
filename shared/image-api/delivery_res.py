# -*- coding: utf-8 -*-
"""Delivery-resolution check: crop a grid cell, upscale to 1920x1080 like the pipeline does,
optionally add one mild unsharp mask, and show a 100% crop side by side.

This is the number that matters: cells are 1016x568 and get upscaled to 1920x1080.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

RUN = Path(__file__).resolve().parent / "runs" / "20261109-063916-grid2x2-ab"
CELLS = RUN / "cells"
OUT = RUN / "compare"
FONT = r"C:\Windows\Fonts\arial.ttf"


def upscale(cell: Path, sharpen: bool) -> Image.Image:
    image = Image.open(cell).convert("RGB").resize((1920, 1080), Image.LANCZOS)
    if sharpen:
        image = image.filter(ImageFilter.UnsharpMask(radius=2, percent=80, threshold=2))
    return image


def panel(panel: int, region: tuple[int, int, int, int], x: int, y: int, w: int, h: int) -> Image.Image:
    canvas = Image.new("RGB", (w * 4 + 30, h + 50), (14, 14, 16))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(FONT, 20)
    labels = ["OLD 1080p", "OLD 1080p +USM", "NEW 1080p", "NEW 1080p +USM"]
    for index, (tag, sharpen) in enumerate((("old", False), ("old", True), ("new", False), ("new", True))):
        image = upscale(CELLS / f"{tag}-p{panel}.png", sharpen)
        crop = image.crop(region)
        canvas.paste(crop, (10 + index * (w + 5), 40))
        draw.text((10 + index * (w + 5), 12), labels[index], fill=(235, 235, 235), font=font)
    return canvas


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    # panel 1: wide chimney texture; panel 3: gripper metal (the hardest case)
    panel(1, (560, 180, 1330, 750), 0, 0, 770, 570).save(OUT / "delivery-p1.png")
    panel(3, (300, 200, 1070, 770), 0, 0, 770, 570).save(OUT / "delivery-p3.png")
    print("ok")


if __name__ == "__main__":
    main()
