# -*- coding: utf-8 -*-
"""Pilot: regenerate 20 suspense shots on NEW1 with the exact same prompts/anchors.

Measures first-pass acceptance and retry recovery under interim-v2 (new1 first, max 3
attempts), and saves side-by-side comparisons against the existing OLD stills.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import time
import urllib.error
import urllib.request
import uuid
import winreg
from pathlib import Path

import numpy as np
from PIL import Image

EP = Path(r"E:\program\1project\video\projects\悬疑\episodes\20261107-bingli")
OUT = Path(r"E:\program\1project\video\shared\image-api\runs") / (time.strftime("%Y%m%d-%H%M%S") + "-pilot20-new1")
BASE = "https://api.mxwell.ai/v1"
MODEL = "gpt-image-2.5-sunburst"
SIZE = "2048x1152"
TARGET = (2048, 1152)
MAX_ATTEMPTS = 3
UA = "OpenAI/Python 1.60.0"
STYLE = (
    "成熟简化赛璐璐动漫/漫画静帧，低饱和冷灰蓝，仅一处受控暖光，"
    "道具用较重墨线勾边，暗部保留细节，关键物证一眼可辨，构图克制、轻微偏心，16:9 横屏。"
    "所有纸张、屏幕、标签上的文字和数字都模糊不可辨认，无可读汉字或数字。"
    "禁止：写实照片、3D渲染、幼态Q版、大眼萌系、高饱和、重暗角、血浆、怪物、通栏文字、水印、UI。"
)
ANCHORS = {"周砚": "zhouyan.png", "林晚": "linwan.png", "小满": "xiaoman.png"}


def key() -> str:
    value = os.environ.get("IMAGE_API_KEY_MX")
    if value:
        return value
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, "IMAGE_API_KEY_MX")[0]


def multipart(fields: dict[str, str], files: dict[str, Path]) -> tuple[bytes, str]:
    boundary = "----dsh" + uuid.uuid4().hex
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode("utf-8"))
    for name, path in files.items():
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}[]"; '
                      f'filename="{path.name}"\r\nContent-Type: {ctype}\r\n\r\n'.encode("utf-8"))
        chunks.append(path.read_bytes())
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def anchor_for(visual: str) -> Path | None:
    for name, filename in ANCHORS.items():
        if name in visual:
            path = EP / "image" / "anchor" / filename
            if path.exists():
                return path
    return None


def call(prompt: str, anchor: Path | None) -> tuple[bytes, int, float]:
    started = time.time()
    if anchor:
        body, ctype = multipart(
            {"model": MODEL, "prompt": prompt + "\n保持参考图中人物的脸型、发型、年龄和服装一致。",
             "size": SIZE, "n": "1"},
            {"image": anchor},
        )
        url = BASE + "/images/edits"
    else:
        body = json.dumps({"model": MODEL, "prompt": prompt, "size": SIZE, "n": 1},
                          ensure_ascii=False).encode("utf-8")
        ctype = "application/json"
        url = BASE + "/images/generations"
    request = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Authorization": f"Bearer {key()}", "Content-Type": ctype,
                                              "Accept": "application/json", "User-Agent": UA})
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            raw, status = response.read(), response.status
    except urllib.error.HTTPError as exc:
        raw, status = exc.read(), exc.code
    return raw, status, round(time.time() - started, 1)


def lap(image: Image.Image) -> float:
    gray = np.asarray(image.convert("L"), dtype=np.float64)
    kernel = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1]
              + gray[1:-1, :-2] + gray[1:-1, 2:])
    return round(float(kernel.var()), 1)


def gate(path: Path) -> tuple[bool, dict, list[str]]:
    reasons = []
    with Image.open(path) as image:
        dims = list(image.size)
        gray = np.asarray(image.convert("L"), dtype=np.float64)
        std = float(gray.std())
        sharp = lap(image)
        delivery = lap(image.convert("RGB").resize((1920, 1080), Image.LANCZOS))
    if tuple(dims) != TARGET:
        reasons.append(f"size {dims[0]}x{dims[1]}")
    if std < 20:
        reasons.append(f"std {std:.1f}")
    if sharp < 60:
        reasons.append(f"lap {sharp}")
    if delivery < 15:
        reasons.append(f"delivery_lap {delivery}")
    return not reasons, {"dims": dims, "std": round(std, 1), "lap": sharp, "delivery_lap": delivery}, reasons


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    shots = json.loads((EP / "storyboard" / "shots.json").read_text(encoding="utf-8"))["shots"]
    evidence = [s for s in shots if s.get("evidence_id")]
    character = [s for s in shots if not s.get("evidence_id") and any(n in s["visual"] for n in ANCHORS)]
    environment = [s for s in shots if not s.get("evidence_id") and s not in character]
    pick = evidence[:7] + character[:7] + environment[:6]
    result = {"policy": "interim-v2", "channel": "new1", "shots": [], "first_pass": 0, "passed": 0,
              "attempts_total": 0, "cost_yuan": 0.0}
    (OUT / "selection.json").write_text(json.dumps([s["id"] for s in pick], ensure_ascii=False), encoding="utf-8")

    for shot in pick:
        prompt = STYLE + "\n\n" + shot["visual"]
        anchor = anchor_for(shot["visual"])
        attempts = []
        final = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            raw, status, elapsed = call(prompt, anchor)
            (OUT / f"{shot['id']}-a{attempt}.json").write_bytes(raw)
            ok = False
            reasons = []
            if status == 200:
                data = json.loads(raw.decode("utf-8"))
                item = (data.get("data") or [{}])[0]
                png = OUT / f"{shot['id']}-a{attempt}.png"
                if item.get("b64_json"):
                    png.write_bytes(base64.b64decode(item["b64_json"]))
                else:
                    with urllib.request.urlopen(item["url"], timeout=600) as response:
                        png.write_bytes(response.read())
                ok, metrics, reasons = gate(png)
                attempts.append({"attempt": attempt, "http": status, "elapsed": elapsed, **metrics,
                                 "passed": ok, "reasons": reasons})
                if ok:
                    final = png
                    break
            else:
                attempts.append({"attempt": attempt, "http": status, "elapsed": elapsed,
                                 "passed": False, "reasons": ["http " + str(status)]})
        result["attempts_total"] += len(attempts)
        result["first_pass"] += 1 if attempts and attempts[0]["passed"] else 0
        result["passed"] += 1 if final else 0
        result["cost_yuan"] = round(result["attempts_total"] * 0.02, 2)
        result["shots"].append({"id": shot["id"], "evidence": bool(shot.get("evidence_id")),
                                "anchor": anchor.name if anchor else None,
                                "attempts": attempts, "final": str(final) if final else None})
        (OUT / "report.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({"id": shot["id"], "attempts": len(attempts),
                          "first": attempts[0]["passed"] if attempts else False,
                          "final": bool(final)}, ensure_ascii=False), flush=True)

    n = len(pick)
    print(json.dumps({"shots": n, "first_pass": result["first_pass"], "passed": result["passed"],
                      "attempts": result["attempts_total"], "cost": result["cost_yuan"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
