# -*- coding: utf-8 -*-
"""Does the candidate relay render real detail above 2048 wide?

Calls mxwell at 4096x2304 and compares high-frequency detail at native size and after
downscaling to 2048 wide. If the 4096 render is genuine, the downscaled version keeps
more texture than the native 2048 render (i.e. requesting big and downscaling wins).
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
RUN = ROOT / "runs" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-size-test")
PROMPT = (ROOT / "runs" / "20261109-063916-grid2x2-ab" / "prompt.txt").read_text(encoding="utf-8")
BASE = "https://api.mxwell.ai/v1"
MODEL = "gpt-image-2.5-sunburst"
SIZE = "4096x2304"
UA = "OpenAI/Python 1.60.0"


def key() -> str:
    value = os.environ.get("MXWELL_API_KEY")
    if value:
        return value
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, "IMAGE_API_KEY_MX")[0]


def stats(path: Path, label: str) -> dict:
    with Image.open(path) as image:
        gray = np.asarray(image.convert("L"), dtype=np.float64)
        rgb = np.asarray(image.convert("RGB"), dtype=np.float64)
    gx = np.abs(np.diff(gray, axis=1))
    gy = np.abs(np.diff(gray, axis=0))
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1]
           + gray[1:-1, :-2] + gray[1:-1, 2:])
    return {"label": label, "dims": list(image.size),
            "lap_var": round(float(lap.var()), 1),
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
        with urllib.request.urlopen(request, timeout=900) as response:
            raw, status = response.read(), response.status
    except urllib.error.HTTPError as exc:
        raw, status = exc.read(), exc.code
    elapsed = round(time.time() - started, 1)
    print("http", status, "elapsed", elapsed, flush=True)
    (RUN / "response.json").write_bytes(raw)
    if status != 200:
        print(raw[:500].decode("utf-8", "replace"))
        return 1
    data = json.loads(raw.decode("utf-8"))
    item = (data.get("data") or [{}])[0]
    png = RUN / "grid-4096.png"
    if item.get("b64_json"):
        png.write_bytes(base64.b64decode(item["b64_json"]))
    elif item.get("url"):
        with urllib.request.urlopen(item["url"], timeout=900) as response:
            png.write_bytes(response.read())
    report = {"requested": SIZE, "size_field": data.get("size"), "elapsed_s": elapsed,
              "bytes": png.stat().st_size, "stats": []}
    report["stats"].append(stats(png, "native-4096"))
    with Image.open(png) as image:
        small = png.with_name("grid-4096-down2048.png")
        image.convert("RGB").resize((2048, 2048 * image.height // image.width), Image.LANCZOS).save(small)
    report["stats"].append(stats(small, "downscaled-2048"))
    native2048 = ROOT / "runs" / "20261109-063916-grid2x2-ab" / "raw" / "new-grid.png"
    report["stats"].append(stats(native2048, "native-2048 (earlier call)"))
    (RUN / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    for row in report["stats"]:
        print(row, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
