# -*- coding: utf-8 -*-
"""Is the softness specific to 2x2 grids, or does this relay upscale every size?

Renders the P3 (ROV gripper) panel as a SINGLE 16:9 image on the candidate relay at
2048x1152, then compares its per-pixel crispness with the same panel inside the 2048
2x2 grid. If the single is much sharper, the fix is "4 single calls instead of 1 grid".
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
import winreg
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
RUN = ROOT / "runs" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-single-panel")
BASE = "https://api.mxwell.ai/v1"
MODEL = "gpt-image-2.5-sunburst"
SIZE = "2048x1152"
UA = "OpenAI/Python 1.60.0"

STYLE = (
    "Cinematic deep-sea documentary still, 16:9 widescreen, near-black teal-blue water full of "
    "fine suspended particles, one amber ROV floodlight at about 3200 K as the only warm source, "
    "photorealistic materials, volumetric haze, high dynamic range, razor-sharp focus on the "
    "subject, rich micro-texture. No text, no letters, no numbers, no watermark."
)
PROMPT = STYLE + " " + (
    "Medium close-up inside the ROV work area. A black robotic manipulator arm enters from the "
    "lower left, its parallel jaws gripping a fist-sized piece of shimmering sulphide rock; "
    "visible bolts, hydraulic lines and scratched paint on the arm; the sample glows amber in the "
    "lamp beam against dark blue water. 35 mm, slight low angle."
)


def key() -> str:
    value = os.environ.get("MXWELL_API_KEY")
    if value:
        return value
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, "IMAGE_API_KEY_MX")[0]


def metrics(path: Path) -> dict:
    with Image.open(path) as image:
        gray = np.asarray(image.convert("L"), dtype=np.float64)
        rgb = np.asarray(image.convert("RGB"), dtype=np.float64)
    gx = np.abs(np.diff(gray, axis=1))
    gy = np.abs(np.diff(gray, axis=0))
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1]
           + gray[1:-1, :-2] + gray[1:-1, 2:])
    return {"lap_var": round(float(lap.var()), 1),
            "edge_per_contrast": round(float(((gx > 20).mean() + (gy > 20).mean()) / 2 * 1000 / gray.std()), 3),
            "mean_lum": round(float(gray.mean()), 1),
            "clip_high_frac": round(float((rgb.max(axis=2) >= 250).mean()), 4)}


def main() -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    (RUN / "prompt.txt").write_text(PROMPT, encoding="utf-8")
    payload = json.dumps({"model": MODEL, "prompt": PROMPT, "size": SIZE, "n": 1},
                         ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE}/images/generations", data=payload, method="POST",
        headers={"Authorization": f"Bearer {key()}", "Content-Type": "application/json",
                 "Accept": "application/json", "User-Agent": UA})
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            raw, status = response.read(), response.status
    except urllib.error.HTTPError as exc:
        raw, status = exc.read(), exc.code
    elapsed = round(time.time() - started, 1)
    (RUN / "response.json").write_bytes(raw)
    if status != 200:
        print(status, raw[:400].decode("utf-8", "replace"))
        return 1
    data = json.loads(raw.decode("utf-8"))
    item = (data.get("data") or [{}])[0]
    png = RUN / "single-2048.png"
    if item.get("b64_json"):
        png.write_bytes(base64.b64decode(item["b64_json"]))
    else:
        with urllib.request.urlopen(item["url"], timeout=600) as response:
            png.write_bytes(response.read())
    report = {"model": MODEL, "size_requested": SIZE, "size_field": data.get("size"),
              "elapsed_s": elapsed, "bytes": png.stat().st_size}
    report.update(metrics(png))
    grid_cell = ROOT / "runs" / "20261109-063916-grid2x2-ab" / "cells" / "new-p3.png"
    if grid_cell.exists():
        report["grid_cell_p3"] = metrics(grid_cell)
    (RUN / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
