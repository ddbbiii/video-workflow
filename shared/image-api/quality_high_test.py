# -*- coding: utf-8 -*-
"""Same prompt, explicit quality="high" on both relays, to test whether the
sharpness gap between old (dklapi) and new (mxwell) is a quality-setting issue."""
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
RUN = ROOT / "runs" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-grid2x2-quality-high")
MODEL = "gpt-image-2.5-sunburst"
SIZE = "2048x1152"
PROMPT = (ROOT / "runs" / "20261109-063916-grid2x2-ab" / "prompt.txt").read_text(encoding="utf-8")
UA = "OpenAI/Python 1.60.0"
TARGETS = [
    {"tag": "old-high", "base": "https://dklapi.com/v1",
     "env": "IMAGE_RELAY_KEY_1K", "reg": "IMAGE_RELAY_KEY_1K"},
    {"tag": "new-high", "base": "https://api.mxwell.ai/v1",
     "env": "MXWELL_API_KEY", "reg": "IMAGE_API_KEY_MX"},
]


def key_for(name: str) -> str:
    value = os.environ.get(name)
    if value:
        return value
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, name)[0]


def call(base: str, key: str, tag: str) -> dict:
    payload = json.dumps({"model": MODEL, "prompt": PROMPT, "size": SIZE, "n": 1,
                          "quality": "high"}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{base}/images/generations", data=payload, method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "Accept": "application/json", "User-Agent": UA})
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            raw, status = response.read(), response.status
    except urllib.error.HTTPError as exc:
        raw, status = exc.read(), exc.code
    elapsed = round(time.time() - started, 1)
    (RUN / f"{tag}-response.json").write_bytes(raw)
    info = {"tag": tag, "base": base, "http_status": status, "elapsed_s": elapsed}
    if status != 200:
        try:
            info["error"] = json.loads(raw.decode("utf-8"))
        except Exception:
            info["error"] = raw[:400].decode("utf-8", "replace")
        info["ok"] = False
        return info
    data = json.loads(raw.decode("utf-8"))
    item = (data.get("data") or [{}])[0]
    png = RUN / f"{tag}-grid.png"
    if item.get("b64_json"):
        png.write_bytes(base64.b64decode(item["b64_json"]))
    elif item.get("url"):
        with urllib.request.urlopen(item["url"], timeout=600) as image_response:
            png.write_bytes(image_response.read())
    with Image.open(png) as image:
        image.load()
        dims = image.size
        gray = np.asarray(image.convert("L"), dtype=np.float64)
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1]
           + gray[1:-1, :-2] + gray[1:-1, 2:])
    info.update({"ok": True, "dims": list(dims), "bytes": png.stat().st_size,
                 "quality_field": data.get("quality"), "size_field": data.get("size"),
                 "sharpness_lap_var": round(float(lap.var()), 1),
                 "mean_lum": round(float(gray.mean()), 1)})
    return info


def main() -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    (RUN / "prompt.txt").write_text(PROMPT, encoding="utf-8")
    results = []
    for target in TARGETS:
        key = key_for(target["env"] if os.environ.get(target["env"]) else target["reg"])
        print(f"call {target['tag']}", flush=True)
        info = call(target["base"], key, target["tag"])
        results.append(info)
        print(json.dumps(info, ensure_ascii=False), flush=True)
        (RUN / "report.json").write_text(
            json.dumps({"model": MODEL, "size": SIZE, "quality_requested": "high",
                        "results": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if all(item.get("ok") for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
