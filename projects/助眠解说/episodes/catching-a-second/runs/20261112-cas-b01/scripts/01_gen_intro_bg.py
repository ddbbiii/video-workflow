# -*- coding: utf-8 -*-
"""E 版片头：一次 2x2 网格生成 4 张背景，裁格后存 1920x1080。

通道按 channel-policy.json v4-dkl2-first：dkl2（dklapi，gpt-image-2.5-sunburst，2048x1152）。
裁格内缩 4 px（白边门禁），再缩到 1920x1080。
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
import winreg
from pathlib import Path

from PIL import Image

EP = Path(__file__).resolve().parents[3]
OUT = EP / "assets" / "intro"
OUT.mkdir(parents=True, exist_ok=True)

BASE = "https://dklapi.com/v1"
MODEL = "gpt-image-2.5-sunburst"
SIZE = "2048x1152"
UA = "OpenAI/Python 1.60.0"
KEY_ENV = "IMAGE_API_KEY_DKL2"

PROMPT = (
    "A single square image divided into a 2x2 grid of four equal cinematic panels, "
    "separated by thin dark gutters. All four panels share one look: cold teal-blue night "
    "palette with restrained amber and warm gold highlights, photorealistic materials, "
    "volumetric haze, deep layered perspective, calm dreamlike documentary mood, 16:9 "
    "widescreen framing inside each panel.\n"
    "Top-left: a domed astronomical observatory on a mountain ridge at night, the dome slit "
    "open, faint star field above, snow on the ground, warm lamplight spilling from a low door.\n"
    "Top-right: inside the observatory, an antique meridian transit telescope on a heavy pier, "
    "a paper chart recorder turning on a brass drum, a single amber lamp, cold blue moonlight "
    "through the slit.\n"
    "Bottom-left: a laboratory bench with a long horizontal vacuum tube of polished steel and "
    "glass, ceramic insulators, a small oven glowing faint orange at one end, cables, quiet "
    "dust in the air.\n"
    "Bottom-right: a vertical vacuum chamber with laser beams crossing inside, a faint "
    "luminous cloud suspended at the crossing point, teal-blue glow, amber reflections on "
    "metal flanges.\n"
    "No text, no letters, no numbers, no labels, no arrows, no diagrams, no UI, no watermark, "
    "no border, no caption."
)


def api_key() -> str:
    value = os.environ.get(KEY_ENV)
    if value:
        return value
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, KEY_ENV)[0]


def main() -> None:
    payload = json.dumps({"model": MODEL, "prompt": PROMPT, "size": SIZE, "n": 1},
                         ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE}/images/generations", data=payload, method="POST",
        headers={"Authorization": f"Bearer {api_key()}",
                 "Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": UA})
    t0 = time.time()
    try:
        with urllib.request.urlopen(request, timeout=900) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        raw, status = exc.read(), exc.code
    print("http", status, "elapsed", round(time.time() - t0, 1))
    if status != 200:
        print(raw[:500].decode("utf-8", "replace"))
        raise SystemExit(1)

    data = json.loads(raw.decode("utf-8"))
    item = data["data"][0]
    if item.get("b64_json"):
        png = base64.b64decode(item["b64_json"])
    else:
        url = item["url"]
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=300) as resp:
                    png = resp.read()
                break
            except Exception as exc:  # CDN 抖动时重试
                print("download retry", attempt + 1, exc)
                time.sleep(3)
        else:
            raise SystemExit("download failed")

    grid_path = OUT / "bg-grid.png"
    grid_path.write_bytes(png)
    img = Image.open(grid_path).convert("RGB")
    print("grid size", img.size)

    w, h = img.size
    cw, ch = w // 2, h // 2
    inset = 4
    names = ["bg1-observatory-exterior", "bg2-transit-telescope",
             "bg3-vacuum-tube", "bg4-laser-chamber"]
    boxes = [(0, 0), (cw, 0), (0, ch), (cw, ch)]
    meta = {"prompt": PROMPT, "model": MODEL, "size": SIZE, "grid": str(grid_path),
            "panels": []}
    for name, (x, y) in zip(names, boxes):
        box = (x + inset, y + inset, x + cw - inset, y + ch - inset)
        panel = img.crop(box).resize((1920, 1080), Image.LANCZOS)
        path = OUT / f"{name}.png"
        panel.save(path)
        meta["panels"].append({"name": name, "path": str(path), "box": box,
                               "size": list(panel.size)})
        print("saved", path.name)

    (OUT / "bg-meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                      encoding="utf-8")


if __name__ == "__main__":
    main()
