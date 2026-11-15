# -*- coding: utf-8 -*-
"""Pipeline demo: OLD reference vs NEW (plain / +RealESRGAN / +RealESRGAN+grade) at 1080p."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageEnhance, ImageFont
from spandrel import ModelLoader

ROOT = Path(__file__).resolve().parent
AB = ROOT / "runs" / "20261109-063916-grid2x2-ab"
OUT = ROOT / "runs" / "20261109-072500-pipeline-demo"
MODEL = Path(r"E:\program\1project\video\shared\runtime\comfy\models\models\upscale_models\RealESRGAN_x4plus.pth")
TILE, PAD = 256, 16
FONT = r"C:\Windows\Fonts\msyh.ttc"


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


def grade(image: Image.Image) -> Image.Image:
    """Cool the warm cast down and tame highlights: -15% saturation, slight teal in shadows."""
    rgb = np.asarray(image.convert("RGB")).astype(np.float32) / 255
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    sat = 0.85
    rgb = lum[..., None] + (rgb - lum[..., None]) * sat
    # teal lift in shadows (weight fades out above 0.35 luminance)
    weight = np.clip((0.35 - lum) / 0.35, 0, 1)[..., None]
    tint = np.array([0.94, 1.0, 1.04], dtype=np.float32)
    rgb = rgb * (1 - weight * 0.55) + rgb * tint * (weight * 0.55)
    # soft highlight roll-off above 0.85
    over = np.clip((rgb - 0.85) / 0.15, 0, 1)
    rgb = rgb - over * over * 0.10
    return Image.fromarray((np.clip(rgb, 0, 1) * 255).round().astype(np.uint8))


def build(panel: int, model, box: tuple[int, int, int, int]) -> Path:
    old = Image.open(AB / "cells" / f"old-p{panel}.png").convert("RGB")
    new = Image.open(AB / "cells" / f"new-p{panel}.png").convert("RGB")
    old1080 = old.resize((1920, 1080), Image.LANCZOS)
    new_plain = new.resize((1920, 1080), Image.LANCZOS)
    new_sr = upscale(new, model).resize((1920, 1080), Image.LANCZOS)
    new_graded = grade(new_sr)
    items = [("OLD · dklapi", old1080), ("NEW 原图", new_plain),
             ("NEW + RealESRGAN", new_sr), ("NEW + SR + 调色", new_graded)]
    crop_w, crop_h = box[2] - box[0], box[3] - box[1]
    canvas = Image.new("RGB", (crop_w * 4 + 8 * 5, crop_h + 48), (14, 14, 16))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(FONT, 19)
    for index, (label, image) in enumerate(items):
        x = 8 + index * (crop_w + 8)
        canvas.paste(image.crop(box), (x, 40))
        draw.text((x, 10), label, fill=(235, 235, 235), font=font)
    path = OUT / f"demo-p{panel}.png"
    canvas.save(path)
    return path


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    model = ModelLoader().load_from_file(str(MODEL)).eval()
    print(build(1, model, (520, 160, 1400, 760)), flush=True)
    print(build(3, model, (300, 170, 1180, 770)), flush=True)
    # save the graded full frames too, for the motion test later
    for panel in (1, 3):
        new = Image.open(AB / "cells" / f"new-p{panel}.png").convert("RGB")
        grade(upscale(new, model).resize((1920, 1080), Image.LANCZOS)).save(OUT / f"new-p{panel}-sr-graded1080.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
