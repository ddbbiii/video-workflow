# -*- coding: utf-8 -*-
"""把网点放到后期：屏幕空间 AM 网点，压进暗部。

动机：烘焙进图里的网点会随推拉重采样（实测 0.4% 推近，墙面像素差是 v3 的 3.5 倍）。
屏幕空间网点固定在输出网格上，镜头怎么动，点距不变。

用法：
  python post_halftone.py <in.png> <out.png> [--cell 8] [--max 0.55]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from motion_risk import patch, zoom, hf_energy  # noqa: E402


def screen(size: tuple[int, int], cell: int) -> np.ndarray:
    """经典圆形网点阈值矩阵，按 cell 平铺；返回 0–1 的覆盖阈值。"""
    h, w = size
    yy, xx = np.mgrid[0:h, 0:w]
    cx = (xx % cell) - (cell - 1) / 2
    cy = (yy % cell) - (cell - 1) / 2
    r = np.sqrt(cx ** 2 + cy ** 2)
    return np.clip(r / (cell / 2), 0, 1)


def apply_halftone(src: Path, dst: Path, cell: int = 8, max_cov: float = 0.55) -> None:
    rgb = np.asarray(Image.open(src).convert("RGB"), dtype=np.float64)
    lum = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]) / 255.0
    # 暗部越暗，覆盖率越高；高光完全不印点
    darkness = np.clip((0.50 - lum) / 0.50, 0, 1) ** 1.5
    cov = np.clip(darkness * max_cov, 0, 1)
    # 专色不印点：饱和像素保护起来，红色证据保持干净
    chroma = rgb.max(axis=2) - rgb.min(axis=2)
    cov = np.where(chroma > 45, 0.0, cov)
    thr = screen(rgb.shape[:2], cell)
    dots = (thr < cov).astype(np.float64)
    ink = np.array([20.0, 24.0, 30.0])  # 墨色略偏蓝，别用纯黑
    out = rgb * (1 - dots[..., None]) + ink * dots[..., None]
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(dst)


def main(argv):
    src, dst = Path(argv[0]), Path(argv[1])
    cell = int(argv[argv.index("--cell") + 1]) if "--cell" in argv else 8
    apply_halftone(src, dst, cell=cell)
    print("wrote", dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
