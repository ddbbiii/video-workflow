# -*- coding: utf-8 -*-
"""Generate one master visual for the v2 slice-intro technical test.

This is a single paid call on new1 (mxwell). It is not a production batch.
Output: projects/人生体验/planning/intro-test-v2/master-visual.png
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

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "projects" / "人生体验" / "planning" / "intro-test-v2" / "master-visual.png"
BASE = "https://api.mxwell.ai/v1"
MODEL = "gpt-image-2.6"
SIZE = "2048x1152"
UA = "OpenAI/Python 1.60.0"

PROMPT = (
    "2D hand-drawn comic illustration, 16:9 widescreen, cinematic first-person view. "
    "In the lower foreground, one grimy hand holds a rusted key and a crumpled photograph; "
    "the other hand pushes open a bent metal door. Beyond the door: a ruined city intersection "
    "at dusk, abandoned cars with open doors, thin smoke, ash falling, a pack of lean stray dogs "
    "in the middle distance. Muted desaturated earth palette of ochre, grey-green and brown, "
    "one strong red-orange glow from a distant fire, clear dark-brown line art, ligne claire, "
    "flat cel shading with soft gradients, detailed cross-hatched ruins, hard directional light, "
    "film grain, slight paper texture, no text, no letters, no numbers, no watermark, no logo."
)


def key() -> str:
    value = os.environ.get("MXWELL_API_KEY")
    if value:
        return value
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, "IMAGE_API_KEY_MX")[0]


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    (OUT.parent / "master-prompt.txt").write_text(PROMPT, encoding="utf-8")
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
    print("status", status, "elapsed", round(time.time() - started, 1))
    if status != 200:
        print(raw[:500].decode("utf-8", "replace"))
        return 1
    data = json.loads(raw.decode("utf-8"))
    item = (data.get("data") or [{}])[0]
    if item.get("b64_json"):
        OUT.write_bytes(base64.b64decode(item["b64_json"]))
    elif item.get("url"):
        with urllib.request.urlopen(item["url"], timeout=600) as response:
            OUT.write_bytes(response.read())
    else:
        print("no image in response")
        return 1
    print("saved", OUT, OUT.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
