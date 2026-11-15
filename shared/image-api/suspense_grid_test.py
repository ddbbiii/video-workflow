# -*- coding: utf-8 -*-
"""Suspense 2x2 feasibility: one grid with the same character in four scenes.

Checks (a) identity across the four panels, (b) per-panel detail at 1080p, (c) whether
evidence-sized props survive the crop. One call on OLD (0.16).
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
RUN = ROOT / "runs" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-suspense-grid2x2")
BASE = "https://dklapi.com/v1"
MODEL = "gpt-image-2.5-sunburst"
SIZE = "2048x1152"
UA = "OpenAI/Python 1.60.0"

PROMPT = (
    "A single 2x2 grid of four distinct cinematic stills, separated by thin dark gutters six "
    "pixels wide, each panel a complete 16:9 frame. The same character in every panel: mature "
    "simplified cel-shaded anime man, thirties, short black hair, grey wool coat over a dark "
    "shirt. Same cold grey-blue palette, one warm lamp as the only warm source, ordinary lived-in "
    "urban interior, legible staging, clean line work, rich material texture, no text, no letters, "
    "no numbers, no labels, no UI, no watermark, no gore, no chibi proportions, no photorealistic "
    "faces. "
    "Panel 1 (top-left): he stands in a dim apartment corridor facing the camera, one hand in his "
    "coat pocket, a door ajar behind him with warm light spilling on the floor. "
    "Panel 2 (top-right): medium shot from behind his shoulder as he looks at a desk lamp and a "
    "scattered stack of papers, his face in profile lit by the lamp. "
    "Panel 3 (bottom-left): close-up of his hand turning a brass door key in a lock, cold light "
    "from the left rimming the metal, his coat cuff visible. "
    "Panel 4 (bottom-right): he sits on the edge of a bed in a dark room, elbows on knees, face "
    "half in shadow, one warm bedside lamp behind him. "
    "Continuity: identical face, hair, coat length and belt in all four panels; no panel repeats "
    "another panel's composition."
)


def key() -> str:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, "IMAGE_RELAY_KEY_1K")[0]


def metrics(image: Image.Image) -> dict:
    gray = np.asarray(image.convert("L"), dtype=np.float64)
    gx = np.abs(np.diff(gray, axis=1))
    gy = np.abs(np.diff(gray, axis=0))
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1]
           + gray[1:-1, :-2] + gray[1:-1, 2:])
    return {"lap_var": round(float(lap.var()), 1),
            "edge_per_contrast": round(float(((gx > 20).mean() + (gy > 20).mean()) / 2 * 1000 / gray.std()), 3)}


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
    grid = RUN / "grid.png"
    if item.get("b64_json"):
        grid.write_bytes(base64.b64decode(item["b64_json"]))
    else:
        with urllib.request.urlopen(item["url"], timeout=600) as response:
            grid.write_bytes(response.read())
    with Image.open(grid) as image:
        image = image.convert("RGB")
        width, height = image.size
        half_w, half_h = width // 2, height // 2
        boxes = [(4, 4, half_w - 4, half_h - 4),
                 (half_w + 4, 4, width - 4, half_h - 4),
                 (4, half_h + 4, half_w - 4, height - 4),
                 (half_w + 4, half_h + 4, width - 4, height - 4)]
        report = {"elapsed_s": elapsed, "dims": [width, height], "panels": []}
        for index, box in enumerate(boxes, start=1):
            cell = image.crop(box)
            cell.save(RUN / f"p{index}.png")
            delivery = cell.resize((1920, 1080), Image.LANCZOS)
            delivery.save(RUN / f"p{index}-1080.png")
            row = {"panel": index, "cell": list(cell.size), **metrics(delivery)}
            report["panels"].append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    (RUN / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(RUN, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
