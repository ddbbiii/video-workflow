# -*- coding: utf-8 -*-
"""2x2 网格生图 → 裁 4 格 → 1920x1080。

用法：
  python 02_gen_shots.py groups.json group-id
groups.json: {"groups":[{"id":"g01","panels":[{"shot":"S03","desc":"..."},...]}]}
通道：channel-policy v4-dkl2-first（dkl2，2048x1152）。
裁格内缩 4 px，再缩到 1920x1080。
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
import winreg
from pathlib import Path

from PIL import Image

EP = Path(__file__).resolve().parents[3]
SHOTS = EP / "assets" / "shots"
SHOTS.mkdir(parents=True, exist_ok=True)

BASE = "https://dklapi.com/v1"
MODEL = "gpt-image-2.5-sunburst"
SIZE = "2048x1152"
UA = "OpenAI/Python 1.60.0"
KEY_ENV = "IMAGE_API_KEY_DKL2"

STYLE = ("cinematic science-fantasy documentary still, deep teal-blue night palette with "
         "controlled amber and warm gold highlights, photorealistic materials, volumetric "
         "atmosphere, layered depth, reflective surfaces, asymmetrical composition, subtle "
         "surrealism, calm dreamlike mood, 16:9 widescreen\n"
         "No text, no letters, no numbers, no labels, no arrows, no diagrams, no charts, "
         "no UI, no watermark, no border, no caption, no logo.")


def api_key() -> str:
    value = os.environ.get(KEY_ENV)
    if value:
        return value
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, KEY_ENV)[0]


def build_prompt(panels: list[dict]) -> str:
    order = ["top-left", "top-right", "bottom-left", "bottom-right"]
    lines = ["A single 16:9 image divided into a 2x2 grid of four equal cinematic panels, "
             "separated by thin dark gutters."]
    for slot, panel in zip(order, panels):
        lines.append(f"{slot}: {panel['desc']}")
    return "\n".join(lines) + "\n" + STYLE


def generate(prompt: str, out_png: Path) -> None:
    payload = json.dumps({"model": MODEL, "prompt": prompt, "size": SIZE, "n": 1},
                         ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE}/images/generations", data=payload, method="POST",
        headers={"Authorization": f"Bearer {api_key()}",
                 "Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": UA})
    t0 = time.time()
    try:
        with urllib.request.urlopen(request, timeout=900) as response:
            raw, status = response.read(), response.status
    except urllib.error.HTTPError as exc:
        raw, status = exc.read(), exc.code
    print("http", status, "elapsed", round(time.time() - t0, 1))
    if status != 200:
        print(raw[:400].decode("utf-8", "replace"))
        raise SystemExit(1)
    item = json.loads(raw.decode("utf-8"))["data"][0]
    if item.get("b64_json"):
        png = base64.b64decode(item["b64_json"])
    else:
        for attempt in range(3):
            try:
                req = urllib.request.Request(item["url"], headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=300) as resp:
                    png = resp.read()
                break
            except Exception as exc:
                print("download retry", attempt + 1, exc)
                time.sleep(3)
        else:
            raise SystemExit("download failed")
    out_png.write_bytes(png)


def main() -> None:
    spec_path = Path(sys.argv[1])
    gid = sys.argv[2]
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    group = next(g for g in spec["groups"] if g["id"] == gid)
    out_dir = SHOTS / gid
    out_dir.mkdir(parents=True, exist_ok=True)
    grid = out_dir / "grid.png"
    prompt = build_prompt(group["panels"])
    (out_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    generate(prompt, grid)

    img = Image.open(grid).convert("RGB")
    w, h = img.size
    cw, ch = w // 2, h // 2
    inset = 4
    boxes = [(0, 0), (cw, 0), (0, ch), (cw, ch)]
    meta = {"group": gid, "grid": str(grid), "size": [w, h], "panels": []}
    for panel, (x, y) in zip(group["panels"], boxes):
        box = (x + inset, y + inset, x + cw - inset, y + ch - inset)
        im = img.crop(box).resize((1920, 1080), Image.LANCZOS)
        p = out_dir / f"{panel['shot']}.png"
        im.save(p)
        meta["panels"].append({"shot": panel["shot"], "path": str(p), "desc": panel["desc"]})
        print("saved", p.name)
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                       encoding="utf-8")


if __name__ == "__main__":
    main()
