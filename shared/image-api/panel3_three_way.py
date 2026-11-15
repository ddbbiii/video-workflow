# -*- coding: utf-8 -*-
"""Three-way delivery check on the 2x2 grid: crop panel 3, upscale to 1920x1080, compare."""
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
    ("dklapi 0.16 元 · 2048x1152", A / "dklapi-G.png"),
    ("mxwell 0.02 元 · 2048x1152", A / "mxwell-G.png"),
    ("xxcapi 约 0.13 元 · 1672x941", B / "xxcapi-G.png"),
]


def panel3(path: Path) -> Image.Image:
    with Image.open(path) as image:
        image = image.convert("RGB")
        width, height = image.size
        return image.crop((0, height // 2, width // 2, height))


def stats(image: Image.Image) -> dict:
    gray = np.asarray(image.convert("L"), dtype=np.float64)
    gx = np.abs(np.diff(gray, axis=1))
    gy = np.abs(np.diff(gray, axis=0))
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1]
           + gray[1:-1, :-2] + gray[1:-1, 2:])
    return {"lap_var": round(float(lap.var()), 1),
            "edge_per_contrast": round(float(((gx > 20).mean() + (gy > 20).mean()) / 2 * 1000 / gray.std()), 3)}


def main() -> None:
    records = []
    tiles = []
    for caption, path in SOURCES:
        if not path.exists():
            continue
        panel = panel3(path)
        upscaled = panel.resize((1920, 1080), Image.LANCZOS)
        record = {"relay": caption, "panel_size": list(panel.size), **stats(upscaled)}
        records.append(record)
        print(record, flush=True)
        tiles.append((caption, upscaled))
    (OUT / "panel3-1080p.json").write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")

    # 100% crop of the same relative area in every delivery frame
    box = (560, 200, 1460, 800)
    crop_w, crop_h = box[2] - box[0], box[3] - box[1]
    pad, header = 10, 52
    canvas = Image.new("RGB", (crop_w * len(tiles) + pad * (len(tiles) + 1), crop_h + header + pad),
                       (14, 14, 16))
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, 6), "格子裁片 → 1920x1080 → 100% 局部（机械臂）",
              fill=(232, 232, 232), font=ImageFont.truetype(FONT, 24))
    for index, (caption, image) in enumerate(tiles):
        x = pad + index * (crop_w + pad)
        canvas.paste(image.crop(box), (x, header))
        draw.text((x, header - 20), caption, fill=(230, 230, 230), font=ImageFont.truetype(FONT, 17))
    canvas.save(OUT / "panel3-1080p-zoom.png")
    print(OUT / "panel3-1080p-zoom.png", flush=True)


if __name__ == "__main__":
    main()
