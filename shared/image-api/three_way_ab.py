# -*- coding: utf-8 -*-
"""Three-way A/B: dklapi (0.16), mxwell (0.02), xxcapi (0.07 list).

Three prompts, same model gpt-image-2.5-sunburst, same 2048x1152:
  G  complex 2x2 deep-sea grid (from the earlier A/B)
  S1 suspense: full-body character holding a key ring (hands)
  S5 suspense: 2x2 character turn-sheet (identity consistency)

One call per relay per prompt, no retry. Outputs images, per-image metrics and 3-column
comparison sheets.
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
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
RUN = ROOT / "runs" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-three-way")
AB = ROOT / "runs" / "20261109-063916-grid2x2-ab"
SUS = ROOT / "runs" / "20261109-071606-suspense-ab"
MODEL = "gpt-image-2.5-sunburst"
SIZE = "2048x1152"
UA = "OpenAI/Python 1.60.0"
FONT = r"C:\Windows\Fonts\msyh.ttc"

RELAYS = [
    {"tag": "dklapi", "base": "https://dklapi.com/v1",
     "env": "IMAGE_RELAY_KEY_1K", "reg": "IMAGE_RELAY_KEY_1K", "price": "0.16 元"},
    {"tag": "mxwell", "base": "https://api.mxwell.ai/v1",
     "env": "MXWELL_API_KEY", "reg": "IMAGE_API_KEY_MX", "price": "0.02 元"},
    {"tag": "xxcapi", "base": "https://xxcapi.com/v1",
     "env": "XXC_API_KEY", "reg": "IMAGE_API_KEY_XXC", "price": "0.07（站点标价）", "model": "AZ-gpt-image-2.5-sunburst"},
]


def key_for(relay: dict) -> str:
    value = os.environ.get(relay["env"])
    if value:
        return value
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, relay["reg"])[0]


def metrics(path: Path) -> dict:
    with Image.open(path) as image:
        gray = np.asarray(image.convert("L"), dtype=np.float64)
        rgb = np.asarray(image.convert("RGB"), dtype=np.float64)
        hsv = np.asarray(image.convert("HSV"), dtype=np.float64)
    gx = np.abs(np.diff(gray, axis=1))
    gy = np.abs(np.diff(gray, axis=0))
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1]
           + gray[1:-1, :-2] + gray[1:-1, 2:])
    return {"lap_var": round(float(lap.var()), 1),
            "edge_per_contrast": round(float(((gx > 20).mean() + (gy > 20).mean()) / 2 * 1000 / gray.std()), 3),
            "mean_lum": round(float(gray.mean()), 1),
            "mean_sat": round(float(hsv[:, :, 1].mean()), 1),
            "clip_high_frac": round(float((rgb.max(axis=2) >= 250).mean()), 4)}


def call(relay: dict, prompt: str, label: str) -> dict:
    payload = json.dumps({"model": relay.get("model", MODEL), "prompt": prompt, "size": SIZE, "n": 1},
                         ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{relay['base']}/images/generations", data=payload, method="POST",
        headers={"Authorization": f"Bearer {key_for(relay)}", "Content-Type": "application/json",
                 "Accept": "application/json", "User-Agent": UA})
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            raw, status = response.read(), response.status
    except urllib.error.HTTPError as exc:
        raw, status = exc.read(), exc.code
    except Exception as exc:
        return {"relay": relay["tag"], "prompt": label, "ok": False, "error": f"{type(exc).__name__}: {exc}"}
    elapsed = round(time.time() - started, 1)
    (RUN / f"{relay['tag']}-{label}-response.json").write_bytes(raw)
    info = {"relay": relay["tag"], "prompt": label, "http_status": status, "elapsed_s": elapsed}
    if status != 200:
        try:
            info["error"] = json.loads(raw.decode("utf-8"))
        except Exception:
            info["error"] = raw[:300].decode("utf-8", "replace")
        info["ok"] = False
        return info
    data = json.loads(raw.decode("utf-8"))
    item = (data.get("data") or [{}])[0]
    png = RUN / f"{relay['tag']}-{label}.png"
    if item.get("b64_json"):
        png.write_bytes(base64.b64decode(item["b64_json"]))
        info["delivery"] = "b64_json"
    elif item.get("url"):
        info["delivery"] = "url"
        with urllib.request.urlopen(item["url"], timeout=600) as response:
            png.write_bytes(response.read())
    else:
        info["ok"] = False
        info["error"] = "no image field"
        return info
    with Image.open(png) as image:
        info["dims"] = list(image.size)
        info["format"] = image.format
    info.update({"ok": True, "bytes": png.stat().st_size, "size_field": data.get("size"),
                 "quality_field": data.get("quality")})
    info.update(metrics(png))
    return info


def make_sheet(label: str, title: str, height_scale: float = 0.42) -> Path:
    tiles = []
    for relay in RELAYS:
        path = RUN / f"{relay['tag']}-{label}.png"
        if path.exists():
            tiles.append((relay, Image.open(path).convert("RGB")))
    if not tiles:
        return RUN / "none.png"
    width = tiles[0][1].width
    tile_w, tile_h = int(width * height_scale), int(tiles[0][1].height * height_scale)
    pad, header = 10, 46
    canvas = Image.new("RGB", (tile_w * len(tiles) + pad * (len(tiles) + 1), tile_h + header + pad),
                       (14, 14, 16))
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, 8), title, fill=(232, 232, 232), font=ImageFont.truetype(FONT, 24))
    for index, (relay, image) in enumerate(tiles):
        x = pad + index * (tile_w + pad)
        canvas.paste(image.resize((tile_w, tile_h), Image.LANCZOS), (x, header))
        draw.text((x, header - 18), f"{relay['tag']} · {relay['price']}",
                  fill=(240, 200, 120) if relay["tag"] == "dklapi" else (150, 210, 240),
                  font=ImageFont.truetype(FONT, 18))
    out = RUN / f"sheet-{label}.png"
    canvas.save(out)
    return out


def main() -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    grid = (AB / "prompt.txt").read_text(encoding="utf-8")
    susp = json.loads((SUS / "prompts.json").read_text(encoding="utf-8"))
    prompts = [("G", grid), ("S1", susp[0][1]), ("S5", susp[4][1])]
    (RUN / "prompts.json").write_text(json.dumps(prompts, ensure_ascii=False, indent=1), encoding="utf-8")
    results = []
    only = os.environ.get('ONLY', '').split(',') if os.environ.get('ONLY') else []
    for label, prompt in prompts:
        for relay in RELAYS:
            if only and relay['tag'] not in only:
                continue
            print(f"{relay['tag']} {label}", flush=True)
            info = call(relay, prompt, label)
            results.append(info)
            print(json.dumps({k: info[k] for k in ("relay", "prompt", "ok", "elapsed_s", "dims",
                                                   "bytes", "delivery", "lap_var", "mean_sat")
                              if k in info}, ensure_ascii=False), flush=True)
            (RUN / "report.json").write_text(json.dumps(results, ensure_ascii=False, indent=1),
                                             encoding="utf-8")
    print(make_sheet("G", "G · 复杂 2x2 深海四格"), flush=True)
    print(make_sheet("S1", "S1 · 悬疑人物全身 + 持钥匙手", 0.62), flush=True)
    print(make_sheet("S5", "S5 · 悬疑三视图拼版", 0.62), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
