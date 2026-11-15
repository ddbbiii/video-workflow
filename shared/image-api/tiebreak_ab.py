# -*- coding: utf-8 -*-
"""Tie-breaker: mxwell vs xxcapi on suspense content that actually causes rework.

Prompts: S1 repeat (hands, new sample), S2 evidence, S4 lock.
Both relays, 3 calls each. Outputs + delivery-size metrics + 2-column sheets.
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
RUN = ROOT / "runs" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-tiebreak")
SUS = ROOT / "runs" / "20261109-071606-suspense-ab"
SIZE = "2048x1152"
UA = "OpenAI/Python 1.60.0"
FONT = r"C:\Windows\Fonts\msyh.ttc"

RELAYS = [
    {"tag": "mxwell", "base": "https://api.mxwell.ai/v1", "env": "MXWELL_API_KEY",
     "reg": "IMAGE_API_KEY_MX", "model": "gpt-image-2.5-sunburst", "price": "0.02 元"},
    {"tag": "xxcapi", "base": "https://xxcapi.com/v1", "env": "XXC_API_KEY",
     "reg": "IMAGE_API_KEY_XXC", "model": "AZ-gpt-image-2.5-sunburst", "price": "0.018 元"},
]


def key_for(relay: dict) -> str:
    value = os.environ.get(relay["env"])
    if value:
        return value
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, relay["reg"])[0]


def metrics(image: Image.Image) -> dict:
    gray = np.asarray(image.convert("L"), dtype=np.float64)
    gx = np.abs(np.diff(gray, axis=1))
    gy = np.abs(np.diff(gray, axis=0))
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1]
           + gray[1:-1, :-2] + gray[1:-1, 2:])
    return {"lap_var": round(float(lap.var()), 1),
            "edge_per_contrast": round(float(((gx > 20).mean() + (gy > 20).mean()) / 2 * 1000 / gray.std()), 3)}


def call(relay: dict, prompt: str, label: str) -> dict:
    payload = json.dumps({"model": relay["model"], "prompt": prompt, "size": SIZE, "n": 1},
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
    elapsed = round(time.time() - started, 1)
    (RUN / f"{relay['tag']}-{label}-response.json").write_bytes(raw)
    info = {"relay": relay["tag"], "prompt": label, "http_status": status, "elapsed_s": elapsed}
    if status != 200:
        info["ok"] = False
        info["error"] = raw[:200].decode("utf-8", "replace")
        return info
    data = json.loads(raw.decode("utf-8"))
    item = (data.get("data") or [{}])[0]
    png = RUN / f"{relay['tag']}-{label}.png"
    if item.get("b64_json"):
        png.write_bytes(base64.b64decode(item["b64_json"]))
    else:
        with urllib.request.urlopen(item["url"], timeout=600) as response:
            png.write_bytes(response.read())
    with Image.open(png) as image:
        native = image.convert("RGB")
        dims = list(image.size)
    delivery = native.resize((1920, 1080), Image.LANCZOS)
    delivery.save(RUN / f"{relay['tag']}-{label}-1080.png")
    info.update({"ok": True, "dims": dims, "bytes": png.stat().st_size,
                 "native": metrics(native), "delivery": metrics(delivery)})
    return info


def sheet(label: str, title: str) -> Path:
    tiles = []
    for relay in RELAYS:
        path = RUN / f"{relay['tag']}-{label}-1080.png"
        if path.exists():
            tiles.append((relay, Image.open(path).convert("RGB")))
    box = (620, 150, 1500, 950)
    crop_w, crop_h = box[2] - box[0], box[3] - box[1]
    pad, header = 10, 52
    canvas = Image.new("RGB", (crop_w * len(tiles) + pad * (len(tiles) + 1), crop_h + header + pad),
                       (14, 14, 16))
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, 6), title, fill=(232, 232, 232), font=ImageFont.truetype(FONT, 23))
    for index, (relay, frame) in enumerate(tiles):
        x = pad + index * (crop_w + pad)
        canvas.paste(frame.crop(box), (x, header))
        draw.text((x, header - 20), f"{relay['tag']} · {relay['price']}",
                  fill=(150, 210, 240), font=ImageFont.truetype(FONT, 18))
    out = RUN / f"sheet-{label}.png"
    canvas.save(out)
    return out


def main() -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    prompts = json.loads((SUS / "prompts.json").read_text(encoding="utf-8"))
    by_name = {name: text for name, text in prompts}
    jobs = [
        ("S1b", by_name["S1-person"], "S1 · 持钥匙（第二次抽样）"),
        ("S2", by_name["S2-evidence"], "S2 · 证据特写"),
        ("S4", by_name["S4-lock"], "S4 · 门锁特写"),
    ]
    results = []
    for label, prompt, _ in jobs:
        for relay in RELAYS:
            print(f"{relay['tag']} {label}", flush=True)
            info = call(relay, prompt, label)
            results.append(info)
            print(json.dumps({k: info[k] for k in ("relay", "prompt", "ok", "elapsed_s", "dims") if k in info}
                             | {"native_lap": info.get("native", {}).get("lap_var"),
                                "delivery_lap": info.get("delivery", {}).get("lap_var")},
                             ensure_ascii=False), flush=True)
            (RUN / "report.json").write_text(json.dumps(results, ensure_ascii=False, indent=1),
                                             encoding="utf-8")
    for label, _, title in jobs:
        print(sheet(label, title), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
