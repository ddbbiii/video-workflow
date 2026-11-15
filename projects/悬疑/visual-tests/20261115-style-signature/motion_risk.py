# -*- coding: utf-8 -*-
"""网点动起来会不会爬纹：用亚像素级推拉模拟量化。

做法：对同一张图分别以 scale=1.000/1.004/1.008 裁切后重采样回 1672×941
（等价于 0.4%/0.8% 的推近一步），在平坦墙面区域比较像素差与高频能量的变化。
差值越大，说明画面纹理对采样网格越敏感 —— 慢推时就会"爬"。

对照：v3（无网点）vs v4（烘焙网点）。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
W, H = 1672, 941
PATCH = (360, 150, 760, 420)  # A1 左上墙面：平坦、有网点、无边缘


def zoom(img: Image.Image, scale: float) -> Image.Image:
    cw, ch = round(W / scale), round(H / scale)
    left, top = (W - cw) // 2, (H - ch) // 2
    return img.crop((left, top, left + cw, top + ch)).resize((W, H), Image.BICUBIC)


def patch(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("L").crop(PATCH), dtype=np.float64)


def hf_energy(a: np.ndarray) -> float:
    lap = (-4 * a[1:-1, 1:-1] + a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:])
    return float(lap.var())


def dot_pitch(a: np.ndarray) -> float:
    """自相关估计网点间距（像素）：取水平方向第一个次峰。"""
    x = a - a.mean()
    ac = np.correlate(x[0], x[0], mode="full")[len(x[0]) - 1:]
    ac = ac / (ac[0] + 1e-9)
    for lag in range(3, 25):
        if ac[lag - 1] < ac[lag] and ac[lag] > ac[lag + 1] and ac[lag] > 0.12:
            return float(lag)
    return 0.0


def main() -> int:
    import sys
    names = sys.argv[1:] or ["A1-v3", "A1-v4", "A1-v3-post"]
    for name in names:
        path = RAW / f"{name}.png"
        if not path.exists():
            print(f"{name}: missing")
            continue
        img = Image.open(path).convert("RGB")
        base = patch(img)
        hf0 = hf_energy(base)
        row = [f"{name:14s} hf={hf0:7.1f} pitch={dot_pitch(np.asarray(img.convert('L').crop(PATCH))):4.1f}px"]
        for s in (1.004, 1.008, 1.012):
            p = patch(zoom(img, s))
            mad = float(np.abs(p - base).mean())
            hf = hf_energy(p)
            row.append(f"z{s:.3f}: mad={mad:5.2f} hf={hf:7.1f} ({(hf / hf0 - 1) * 100:+5.1f}%)")
        print(" | ".join(row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
