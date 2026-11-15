# -*- coding: utf-8 -*-
"""Extra probes for the 2026-11-12 dkl three-way run.

1) 1:1 crop sheets: central 400x400 of panel 2 for each channel (no resampling),
   so softness is visible pixel for pixel.
2) Native-size probe on the cheap dkl key: same G-grid prompt at 1024x576,
   compared against a 1024x576 downscale of its 2048x1152 output. If the small
   native render is much sharper per pixel, the 2048 output was upscaled.
"""
from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
import winreg
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

RUN = Path(r"E:\program\1project\video\shared\image-api\runs\20261112-114824-dkl3way-2x2")
CMP = RUN / "compare"
RAW = RUN / "raw"
UA = "OpenAI/Python 1.60.0"
KEY_ENV = "IMAGE_API_KEY_DKL2"
BASE = "https://dklapi.com/v1"
MODEL = "gpt-image-2.5-sunburst"
CH = ["dkl-old", "dkl-new", "new2"]
LABEL = {"dkl-old": "DKL 旧 key · 0.16 元", "dkl-new": "DKL 新 key · 0.015 元",
         "new2": "NEW2 xxcapi · 0.018 元"}


def font(size: int):
    for path in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\arial.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def lap(gray: np.ndarray) -> float:
    g = gray.astype(np.float64)
    return float((-4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1]
                  + g[1:-1, :-2] + g[1:-1, 2:]).var())


def key() -> str:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, KEY_ENV)[0]


def crop_sheet(prompt: str, panel: int, size: int = 400) -> Path:
    tiles = []
    for ch in CH:
        cell = Image.open(RUN / "cells" / f"{ch}-{prompt}-p{panel}.png").convert("RGB")
        w, h = cell.size
        left, top = (w - size) // 2, (h - size) // 2
        tiles.append(cell.crop((left, top, left + size, top + size)))
    pad, header = 10, 44
    canvas = Image.new("RGB", (size * 3 + pad * 4, size + header + pad), (14, 14, 16))
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, 8), f"{prompt} · 第 {panel} 格 中央 400px 1:1（未缩放）",
              fill=(232, 232, 232), font=font(21))
    for i, (ch, tile) in enumerate(zip(CH, tiles)):
        x = pad + i * (size + pad)
        canvas.paste(tile, (x, header))
        draw.text((x, header - 16), LABEL[ch], fill=(240, 200, 120), font=font(15))
    out = CMP / f"crop100-{prompt}-p{panel}.png"
    canvas.save(out)
    return out


def native_probe() -> dict:
    prompt = (RUN / "prompt-G-grid.txt").read_text(encoding="utf-8")
    payload = {"model": MODEL, "prompt": prompt, "size": "1024x576", "n": 1}
    request = urllib.request.Request(
        f"{BASE}/images/generations",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {key()}", "Content-Type": "application/json",
                 "Accept": "application/json", "User-Agent": UA})
    started = time.time()
    status, raw = None, b""
    try:
        with urllib.request.urlopen(request, timeout=900) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read()
    elapsed = round(time.time() - started, 1)
    (RAW / "dkl-new-G-grid-1024-response.json").write_bytes(raw)
    info = {"status": status, "elapsed_s": elapsed}
    if status != 200:
        info["error"] = raw[:300].decode("utf-8", "replace")
        return info
    item = (json.loads(raw.decode("utf-8")).get("data") or [{}])[0]
    path = RAW / "dkl-new-G-grid-1024.png"
    if item.get("b64_json"):
        path.write_bytes(base64.b64decode(item["b64_json"]))
    else:
        with urllib.request.urlopen(
                urllib.request.Request(item["url"], headers={"User-Agent": UA}),
                timeout=900) as response:
            path.write_bytes(response.read())
    small = Image.open(path).convert("RGB")
    info["dims"] = list(small.size)
    info["lap_var_native"] = round(lap(np.asarray(small.convert("L"))), 1)
    big = Image.open(RAW / "dkl-new-G-grid.png").convert("RGB").resize(small.size, Image.LANCZOS)
    info["lap_var_2048_downscaled"] = round(lap(np.asarray(big.convert("L"))), 1)
    big.save(CMP / "dkl-new-G-grid-2048-downscaled-1024.png")
    return info


def main() -> int:
    out = {}
    for prompt, panel in (("G-grid", 2), ("S-grid", 3), ("G-grid", 3)):
        out[f"crop-{prompt}-{panel}"] = str(crop_sheet(prompt, panel))
    out["native_probe"] = native_probe()
    (RUN / "probe-extra.json").write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
