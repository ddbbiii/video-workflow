# -*- coding: utf-8 -*-
"""Delivery-size (1920x1080) sharpness for suspense shots: OLD vs NEW2."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
SUS = ROOT / "runs" / "20261109-071606-suspense-ab"
TIE = ROOT / "runs" / "20261109-074623-tiebreak"
OUT = ROOT / "runs" / "20261109-075000-three-way-combined"

PAIRS = [
    ("S1 持钥匙（第二次抽样）", SUS / "old-S1-person.png", TIE / "xxcapi-S1b.png"),
    ("S2 证据特写", SUS / "old-S2-evidence.png", TIE / "xxcapi-S2.png"),
    ("S4 门锁特写", SUS / "old-S4-lock.png", TIE / "xxcapi-S4.png"),
    ("S5 三视图（左上格）", SUS / "old-S5-turnsheet.png", (ROOT / "runs" / "20261109-074040-three-way" / "xxcapi-S5.png")),
]


def stats(image: Image.Image) -> dict:
    gray = np.asarray(image.convert("L"), dtype=np.float64)
    gx = np.abs(np.diff(gray, axis=1))
    gy = np.abs(np.diff(gray, axis=0))
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1]
           + gray[1:-1, :-2] + gray[1:-1, 2:])
    return {"lap_var": round(float(lap.var()), 1),
            "edge_per_contrast": round(float(((gx > 20).mean() + (gy > 20).mean()) / 2 * 1000 / gray.std()), 3)}


def frame(path: Path, quadrant: bool) -> dict | None:
    if not path.exists():
        return None
    with Image.open(path) as image:
        img = image.convert("RGB")
        if quadrant:
            width, height = img.size
            img = img.crop((0, 0, width // 2, height // 2))
    return stats(img.resize((1920, 1080), Image.LANCZOS))


rows = []
for name, old_path, new_path in PAIRS:
    row = {"shot": name, "old": frame(old_path, "三视图" in name), "new2": frame(new_path, "三视图" in name)}
    rows.append(row)
    print(json.dumps(row, ensure_ascii=False), flush=True)

(OUT / "delivery-old-vs-new2.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                                              encoding="utf-8")
