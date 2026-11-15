# -*- coding: utf-8 -*-
"""Crispness metrics across all grid variants + 100% zoom crops for a chosen pair."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent / "runs"
AB = BASE / "20261109-063916-grid2x2-ab"
HQ = BASE / "20261109-064114-grid2x2-quality-high"

VARIANTS = [
    ("old-default", AB / "raw" / "old-grid.png"),
    ("new-default", AB / "raw" / "new-grid.png"),
    ("old-high", HQ / "old-high-grid.png"),
    ("new-high", HQ / "new-high-grid.png"),
]

REGION = (300, 120, 760, 480)  # gripper / sample area, same coords in every cell 3


def crispness(path: Path) -> dict:
    with Image.open(path) as image:
        gray = np.asarray(image.convert("L"), dtype=np.float64)
        rgb = np.asarray(image.convert("RGB"), dtype=np.float64)
    gx = np.abs(np.diff(gray, axis=1))
    gy = np.abs(np.diff(gray, axis=0))
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1]
           + gray[1:-1, :-2] + gray[1:-1, 2:])
    height, width = gray.shape
    blocks = gray[: height // 2 * 2, : width // 2 * 2].reshape(height // 2, 2, width // 2, 2)
    return {
        "file": path.name,
        "bytes": path.stat().st_size,
        "mean_lum": round(float(gray.mean()), 1),
        "std_lum": round(float(gray.std()), 1),
        "lap_var": round(float(lap.var()), 1),
        "edge_frac_gt20": round(float(((gx > 20).mean() + (gy > 20).mean()) / 2), 4),
        # crispness normalised by global contrast, so a darker render is not penalised twice
        "edge_per_contrast": round(float((gx > 20).mean() * 1000 / gray.std()), 3),
        "within_2x2_std": round(float(blocks.std(axis=(1, 3)).mean()), 2),
        "clip_high_frac": round(float((rgb.max(axis=2) >= 250).mean()), 4),
    }


def zoom_pair(left: Path, right: Path, label_left: str, label_right: str, out: Path) -> Path:
    cells = []
    for path in (left, right):
        with Image.open(path) as image:
            cell = image.convert("RGB").crop((4, 4, 1016, 568))
        cells.append(cell.crop(REGION).resize(
            ((REGION[2] - REGION[0]) * 2, (REGION[3] - REGION[1]) * 2), Image.NEAREST))
    width, height = cells[0].size
    pad, header = 10, 40
    canvas = Image.new("RGB", (width * 2 + pad * 3, height + header + pad * 2), (16, 16, 18))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 22)
    draw.text((pad, 8), label_left, fill=(235, 235, 235), font=font)
    draw.text((pad * 2 + width, 8), label_right, fill=(235, 235, 235), font=font)
    canvas.paste(cells[0], (pad, header + pad))
    canvas.paste(cells[1], (pad * 2 + width, header + pad))
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    return out


def main() -> int:
    rows = [crispness(path) for _, path in VARIANTS]
    for row in rows:
        print(row)
    if len(sys.argv) == 6:  # <left.png> <right.png> <left label> <right label> <out.png>
        zoom_pair(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4], Path(sys.argv[5]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
