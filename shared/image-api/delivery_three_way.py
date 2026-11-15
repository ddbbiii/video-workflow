# -*- coding: utf-8 -*-
"""Delivery-size (1920x1080) comparison for the suspense shots across three relays."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
A = ROOT / "runs" / "20261109-073513-three-way"
B = ROOT / "runs" / "20261109-074040-three-way"
OUT = ROOT / "runs" / "20261109-075000-three-way-combined"
FONT = r"C:\Windows\Fonts\msyh.ttc"

SOURCES = [
    ("dklapi 0.16", A / "dklapi-{s}.png", "single"),
    ("mxwell 0.02", A / "mxwell-{s}.png", "single"),
    ("xxcapi 0.018", B / "xxcapi-{s}.png", "single"),
]


def stats(image: Image.Image) -> dict:
    gray = np.asarray(image.convert("L"), dtype=np.float64)
    gx = np.abs(np.diff(gray, axis=1))
    gy = np.abs(np.diff(gray, axis=0))
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1]
           + gray[1:-1, :-2] + gray[1:-1, 2:])
    return {"lap_var": round(float(lap.var()), 1),
            "edge_per_contrast": round(float(((gx > 20).mean() + (gy > 20).mean()) / 2 * 1000 / gray.std()), 3)}


def load(path: Path, grid: bool) -> Image.Image:
    image = Image.open(path).convert("RGB")
    if grid:  # single quadrant (top-left) for the turn-sheet check
        width, height = image.size
        image = image.crop((0, 0, width // 2, height // 2))
    return image.resize((1920, 1080), Image.LANCZOS)


def main() -> None:
    report = {}
    for shot, grid in (("S1", False), ("S5", True)):
        rows = []
        frames = []
        for caption, pattern, _ in SOURCES:
            path = Path(str(pattern).format(s=shot))
            if not path.exists():
                continue
            frame = load(path, grid)
            rows.append({"relay": caption, **stats(frame)})
            frames.append((caption, frame))
        report[shot] = rows
        for row in rows:
            print(shot, row, flush=True)
        # 100% crop: face area for S1, face quadrant for S5
        box = (700, 120, 1500, 900) if shot == "S1" else (1050, 150, 1850, 930)
        crop_w, crop_h = box[2] - box[0], box[3] - box[1]
        pad, header = 10, 52
        canvas = Image.new("RGB", (crop_w * len(frames) + pad * (len(frames) + 1), crop_h + header + pad),
                           (14, 14, 16))
        draw = ImageDraw.Draw(canvas)
        draw.text((pad, 6), f"{shot} · 1080p 交付 · 100% 局部", fill=(232, 232, 232),
                  font=ImageFont.truetype(FONT, 24))
        for index, (caption, frame) in enumerate(frames):
            x = pad + index * (crop_w + pad)
            canvas.paste(frame.crop(box), (x, header))
            draw.text((x, header - 20), caption, fill=(230, 230, 230), font=ImageFont.truetype(FONT, 17))
        canvas.save(OUT / f"delivery-{shot}-zoom.png")
        print(OUT / f"delivery-{shot}-zoom.png", flush=True)
    (OUT / "delivery-suspense.json").write_text(json.dumps(report, ensure_ascii=False, indent=1),
                                                encoding="utf-8")


if __name__ == "__main__":
    main()
