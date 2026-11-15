# -*- coding: utf-8 -*-
"""Does local RealESRGAN close the gap for the cheap relay?

Inputs (all the same P3 gripper scene):
  A  NEW single 1024x576   (native size that is sharpest per pixel on this relay)
  B  NEW 2048 grid cell    (1016x568, what we get today from a 2x2 grid)
  C  OLD 2048 grid cell    (reference, what production uses)

For each: plain Lanczos ->1920x1080 and RealESRGAN_x4plus ->1920x1080.
Runs on CPU (GPU jobs need the shared queue); tile 256, overlap 16.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont
from spandrel import ModelLoader

ROOT = Path(__file__).resolve().parent
RUN = ROOT / "runs" / "20261109-071018-single-sizes"
AB = ROOT / "runs" / "20261109-063916-grid2x2-ab"
OUT = ROOT / "runs" / "20261109-072000-sr-compare"
MODEL = Path(r"E:\program\1project\video\shared\runtime\comfy\models\models\upscale_models\RealESRGAN_x4plus.pth")
TILE, PAD = 256, 16
FONT = r"C:\Windows\Fonts\msyh.ttc"

INPUTS = {
    "A-new-1024": RUN / "1024-576.png",
    "B-new-grid": AB / "cells" / "new-p3.png",
    "C-old-grid": AB / "cells" / "old-p3.png",
}


def upscale(image: Image.Image, model) -> Image.Image:
    arr = np.asarray(image.convert("RGB")).copy()
    height, width = arr.shape[:2]
    result = np.empty((height * 4, width * 4, 3), dtype=np.uint8)
    with torch.inference_mode():
        for y in range(0, height, TILE):
            for x in range(0, width, TILE):
                right, bottom = min(x + TILE, width), min(y + TILE, height)
                x0, y0 = max(0, x - PAD), max(0, y - PAD)
                x1, y1 = min(width, right + PAD), min(height, bottom + PAD)
                tile = torch.from_numpy(arr[y0:y1, x0:x1].copy()).permute(2, 0, 1).unsqueeze(0).float() / 255
                prediction = model(tile).clamp(0, 1)
                pixels = (prediction[0].permute(1, 2, 0).numpy() * 255).round().astype(np.uint8)
                result[y * 4:bottom * 4, x * 4:right * 4] = pixels[(y - y0) * 4:(bottom - y0) * 4,
                                                                   (x - x0) * 4:(right - x0) * 4]
    return Image.fromarray(result)


def stats(path: Path) -> dict:
    with Image.open(path) as image:
        gray = np.asarray(image.convert("L"), dtype=np.float64)
    gx = np.abs(np.diff(gray, axis=1))
    gy = np.abs(np.diff(gray, axis=0))
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1]
           + gray[1:-1, :-2] + gray[1:-1, 2:])
    return {"lap_var": round(float(lap.var()), 1),
            "edge_per_contrast": round(float(((gx > 20).mean() + (gy > 20).mean()) / 2 * 1000 / gray.std()), 3)}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    model = ModelLoader().load_from_file(str(MODEL)).eval()
    records = []
    pairs = {}
    for label, src in INPUTS.items():
        with Image.open(src) as image:
            image = image.convert("RGB")
            base = OUT / f"{label}-lanczos1080.png"
            image.resize((1920, 1080), Image.LANCZOS).save(base)
            started = time.time()
            big = upscale(image, model)
            big.save(OUT / f"{label}-sr-native4x.png")
            sr = OUT / f"{label}-sr1080.png"
            big.resize((1920, 1080), Image.LANCZOS).save(sr)
            rec = {"label": label, "source": str(src), "source_size": list(image.size),
                   "seconds": round(time.time() - started, 1),
                   "lanczos": str(base), "sr": str(sr),
                   "stats_lanczos": stats(base), "stats_sr": stats(sr)}
            records.append(rec)
            pairs[label] = (base, sr)
            print(json.dumps(rec, ensure_ascii=False), flush=True)
            del big
    (OUT / "report.json").write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")

    # 100% crop sheet: old reference vs new variants
    box = (330, 180, 1180, 760)
    cell_w, cell_h = box[2] - box[0], box[3] - box[1]
    columns = [("C-old-grid", "lanczos"), ("C-old-grid", "sr"),
               ("B-new-grid", "sr"), ("A-new-1024", "sr"), ("A-new-1024", "lanczos")]
    sheet = Image.new("RGB", (cell_w * len(columns) + 8 * (len(columns) + 1), cell_h + 48), (14, 14, 16))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(FONT, 19)
    names = {"C-old-grid": "OLD 2048", "B-new-grid": "NEW 2x2", "A-new-1024": "NEW 1024"}
    for index, (label, kind) in enumerate(columns):
        path = pairs[label][0] if kind == "lanczos" else pairs[label][1]
        with Image.open(path) as image:
            crop = image.crop(box)
        x = 8 + index * (cell_w + 8)
        sheet.paste(crop, (x, 40))
        suffix = "" if kind == "lanczos" else " +RealESRGAN"
        draw.text((x, 10), f"{names[label]}{suffix}", fill=(235, 235, 235), font=font)
    sheet.save(OUT / "zoom-compare.png")
    print("OUT", OUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
