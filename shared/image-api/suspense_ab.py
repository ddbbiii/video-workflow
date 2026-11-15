# -*- coding: utf-8 -*-
"""Suspense-line evaluation: 4 single shots + 1 two-by-two character sheet, both relays.

Suspense line rules (rules/悬疑/visual.md): desaturated cel-shaded anime, cold grey-blue with
one controlled warm light, legible horror, no text/UI, normal proportions, evidence must read.
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
RUN = ROOT / "runs" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-suspense-ab")
MODEL = "gpt-image-2.5-sunburst"
SIZE = "2048x1152"
UA = "OpenAI/Python 1.60.0"

STYLE = (
    "cinematic desaturated comic-panel space, mature simplified cel-shaded anime characters with "
    "normal proportions, cold grey-blue palette with exactly one controlled warm light source, "
    "ordinary lived-in urban interior, legible horror staging through space and objects, clear "
    "foreground subject and props, slight off-center composition, volumetric dust, 16:9, "
    "sharp clean line work, rich material texture, no text, no letters, no numbers, no labels, "
    "no UI, no watermark, no gore, no chibi proportions, no photorealistic faces."
)

SHOTS = [
    ("S1-person", STYLE + " " + (
        "Full-body shot of a mature cel-shaded anime man in his thirties, short black hair, grey "
        "wool coat over a dark shirt, standing still in the doorway of a dim apartment, facing the "
        "camera. His right hand is raised at chest height holding a small brass key ring with two "
        "keys, fingers clearly separated and anatomically correct. Behind him a single warm desk "
        "lamp lights one wall; the rest of the room is cold blue shadow. Eye level camera, 50 mm."
    )),
    ("S2-evidence", STYLE + " " + (
        "Extreme close-up on a dark wooden table: a hand holds a crumpled paper receipt with faint "
        "illegible grey print lines (no readable characters at all), beside a cheap ballpoint pen "
        "and a chipped ceramic cup. Warm lamp light from the left, cold window light from the "
        "right, shallow depth of field, 100 mm macro, crisp paper fibre and skin texture."
    )),
    ("S3-corridor", STYLE + " " + (
        "Wide symmetrical shot of a narrow apartment corridor at night, peeling beige paint, "
        "worn wooden floor, one door at the far end standing ajar with warm light spilling out "
        "across the floor, all other doors closed and dark. No people. Cold blue ambient light "
        "from a small window on the left, deep but detailed shadows, 24 mm, eye level."
    )),
    ("S4-lock", STYLE + " " + (
        "Close-up of an old brass mortise lock and a heavy chain on a scratched apartment door, "
        "a key inserted and turned halfway, paint chipped around the strike plate, dust in the "
        "grooves, cold light from the left rimming the metal, 85 mm, shallow depth of field."
    )),
    ("S5-turnsheet", (
        "A single 2x2 grid of four panels separated by thin dark gutters, six pixels wide. The same "
        "character in every panel: mature simplified cel-shaded anime man, thirties, short black "
        "hair, grey wool coat over a dark shirt, neutral standing pose, flat even studio lighting, "
        "plain mid-grey background. Top-left: full-body front view. Top-right: full-body side view, "
        "90 degrees. Bottom-left: full-body back view. Bottom-right: front facial close-up, flat "
        "lighting, clear eyes, eyebrows, nose and mouth. Identical proportions, identical clothing "
        "and hair in all four panels, full body not cropped. " + STYLE
    )),
]

TARGETS = [
    {"tag": "old", "base": "https://dklapi.com/v1", "env": "IMAGE_RELAY_KEY_1K", "reg": "IMAGE_RELAY_KEY_1K"},
    {"tag": "new", "base": "https://api.mxwell.ai/v1", "env": "MXWELL_API_KEY", "reg": "IMAGE_API_KEY_MX"},
]


def key_for(target: dict) -> str:
    value = os.environ.get(target["env"])
    if value:
        return value
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, target["reg"])[0]


def metrics(path: Path) -> dict:
    with Image.open(path) as image:
        gray = np.asarray(image.convert("L"), dtype=np.float64)
        hsv = np.asarray(image.convert("HSV"), dtype=np.float64)
    gx = np.abs(np.diff(gray, axis=1))
    gy = np.abs(np.diff(gray, axis=0))
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1]
           + gray[1:-1, :-2] + gray[1:-1, 2:])
    return {"lap_var": round(float(lap.var()), 1),
            "edge_per_contrast": round(float(((gx > 20).mean() + (gy > 20).mean()) / 2 * 1000 / gray.std()), 3),
            "mean_lum": round(float(gray.mean()), 1),
            "mean_sat": round(float(hsv[:, :, 1].mean()), 1)}


def call(target: dict, label: str, prompt: str) -> dict:
    payload = json.dumps({"model": MODEL, "prompt": prompt, "size": SIZE, "n": 1},
                         ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{target['base']}/images/generations", data=payload, method="POST",
        headers={"Authorization": f"Bearer {key_for(target)}", "Content-Type": "application/json",
                 "Accept": "application/json", "User-Agent": UA})
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            raw, status = response.read(), response.status
    except urllib.error.HTTPError as exc:
        raw, status = exc.read(), exc.code
    elapsed = round(time.time() - started, 1)
    (RUN / f"{target['tag']}-{label}-response.json").write_bytes(raw)
    info = {"tag": target["tag"], "shot": label, "http_status": status, "elapsed_s": elapsed}
    if status != 200:
        info["ok"] = False
        info["error"] = raw[:300].decode("utf-8", "replace")
        return info
    data = json.loads(raw.decode("utf-8"))
    item = (data.get("data") or [{}])[0]
    png = RUN / f"{target['tag']}-{label}.png"
    if item.get("b64_json"):
        png.write_bytes(base64.b64decode(item["b64_json"]))
    else:
        with urllib.request.urlopen(item["url"], timeout=600) as response:
            png.write_bytes(response.read())
    info.update({"ok": True, "dims": list(Image.open(png).size), "bytes": png.stat().st_size})
    info.update(metrics(png))
    return info


def main() -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    (RUN / "prompts.json").write_text(json.dumps(SHOTS, ensure_ascii=False, indent=1), encoding="utf-8")
    results = []
    for label, prompt in SHOTS:
        for target in TARGETS:
            print(f"{target['tag']} {label}", flush=True)
            info = call(target, label, prompt)
            results.append(info)
            print(json.dumps(info, ensure_ascii=False), flush=True)
            (RUN / "report.json").write_text(json.dumps(results, ensure_ascii=False, indent=1),
                                             encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
