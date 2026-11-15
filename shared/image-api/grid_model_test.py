# -*- coding: utf-8 -*-
"""Same 2x2 prompt across models/relays, to find whether a sharper variant exists.

Usage:
  python grid_model_test.py            # runs the built-in matrix
Each run costs one call. Prompt is shared with the earlier A/B (prompt.txt).
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
SOURCE_PROMPT = ROOT / "runs" / "20261109-063916-grid2x2-ab" / "prompt.txt"
RUN = ROOT / "runs" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-model-matrix")
SIZE = "2048x1152"
UA = "OpenAI/Python 1.60.0"

MATRIX = [
    {"tag": "old-2.6-sunburst", "base": "https://dklapi.com/v1",
     "env": "IMAGE_RELAY_KEY_1K", "reg": "IMAGE_RELAY_KEY_1K", "model": "gpt-image-2.6-sunburst"},
    {"tag": "new-2.6-sunburst", "base": "https://api.mxwell.ai/v1",
     "env": "MXWELL_API_KEY", "reg": "IMAGE_API_KEY_MX", "model": "gpt-image-2.6-sunburst"},
    {"tag": "new-2.6", "base": "https://api.mxwell.ai/v1",
     "env": "MXWELL_API_KEY", "reg": "IMAGE_API_KEY_MX", "model": "gpt-image-2.6"},
    {"tag": "new-2.5-flare", "base": "https://api.mxwell.ai/v1",
     "env": "MXWELL_API_KEY", "reg": "IMAGE_API_KEY_MX", "model": "gpt-image-2.5-flare"},
]


def key_for(target: dict) -> str:
    value = os.environ.get(target["env"])
    if value:
        return value
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, target["reg"])[0]


def call(target: dict, prompt: str) -> dict:
    payload = json.dumps({"model": target["model"], "prompt": prompt, "size": SIZE, "n": 1},
                         ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{target['base']}/images/generations", data=payload, method="POST",
        headers={"Authorization": f"Bearer {key_for(target)}",
                 "Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": UA})
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            raw, status = response.read(), response.status
    except urllib.error.HTTPError as exc:
        raw, status = exc.read(), exc.code
    elapsed = round(time.time() - started, 1)
    info = {"tag": target["tag"], "model": target["model"], "base": target["base"],
            "http_status": status, "elapsed_s": elapsed}
    if status != 200:
        try:
            info["error"] = json.loads(raw.decode("utf-8"))
        except Exception:
            info["error"] = raw[:300].decode("utf-8", "replace")
        info["ok"] = False
        return info
    data = json.loads(raw.decode("utf-8"))
    item = (data.get("data") or [{}])[0]
    png = RUN / f"{target['tag']}.png"
    (RUN / f"{target['tag']}-response.json").write_bytes(raw)
    if item.get("b64_json"):
        png.write_bytes(base64.b64decode(item["b64_json"]))
    elif item.get("url"):
        with urllib.request.urlopen(item["url"], timeout=600) as response:
            png.write_bytes(response.read())
    with Image.open(png) as image:
        image.load()
        gray = np.asarray(image.convert("L"), dtype=np.float64)
        rgb = np.asarray(image.convert("RGB"), dtype=np.float64)
        hsv = np.asarray(image.convert("HSV"), dtype=np.float64)
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1]
           + gray[1:-1, :-2] + gray[1:-1, 2:])
    gx = np.abs(np.diff(gray, axis=1))
    gy = np.abs(np.diff(gray, axis=0))
    info.update({
        "ok": True, "dims": list(image.size), "bytes": png.stat().st_size,
        "quality_field": data.get("quality"), "size_field": data.get("size"),
        "lap_var": round(float(lap.var()), 1),
        "edge_per_contrast": round(float(((gx > 20).mean() + (gy > 20).mean()) / 2 * 1000 / gray.std()), 3),
        "mean_lum": round(float(gray.mean()), 1),
        "std_lum": round(float(gray.std()), 1),
        "mean_sat": round(float(hsv[:, :, 1].mean()), 1),
        "clip_high_frac": round(float((rgb.max(axis=2) >= 250).mean()), 4),
    })
    return info


def main() -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    prompt = SOURCE_PROMPT.read_text(encoding="utf-8")
    (RUN / "prompt.txt").write_text(prompt, encoding="utf-8")
    results = []
    for target in MATRIX:
        print(f"call {target['tag']} ({target['model']})", flush=True)
        info = call(target, prompt)
        results.append(info)
        print(json.dumps(info, ensure_ascii=False), flush=True)
        (RUN / "report.json").write_text(json.dumps(results, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    return 0 if all(item.get("ok") for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
