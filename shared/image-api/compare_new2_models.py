# -*- coding: utf-8 -*-
"""Controlled image-model comparison on the existing XXC/new2 endpoint."""
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
from datetime import datetime
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "projects" / "人生体验" / "visual-tests" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-new2-models")
RAW = RUN / "raw"
REFERENCE = ROOT / "projects" / "人生体验" / "episodes" / "20261113-tumu" / "image" / "refs" / "cat-face-crop.png"
BASE = os.environ.get("IMAGE_API_BASE_URL_XXC", "https://xxcapi.com/v1").rstrip("/")
UA = "OpenAI/Python 1.60.0"
SIZE = "1672x941"
MODELS = [
    ("sunburst", "AZ-gpt-image-2.5-sunburst"),
    ("image-2", "AZ-gpt-image-2"),
    ("flare", "AZ-gpt-image-2.5-flare"),
]
STYLE = (
    "2D hand-drawn comic illustration, dark brown clean linework, flat colors, hard-edged shadows, "
    "subtle paper grain, horizontal 16:9 composition. No readable text, letters, numbers or watermark. "
    "No 3D, photorealism, plastic toy appearance, global sepia or uniform ochre wash. "
    "The same Scottish Fold orange tabby cat character as the reference: round full cheeks, short muzzle, "
    "small forward-folded ears, black eyes with a narrow amber rim, pink nose, cream muzzle, white whiskers, "
    "white chest bib, orange tabby markings on forehead and cheeks. Semi-realistic fur on face, flat-shaded "
    "short adult human body, about three heads tall, narrow shoulders, very short neck, five-fingered bare "
    "human hands, no tail. Use reference only to preserve the cat identity and markings, not its lighting, "
    "composition, background or color palette."
)
SHOTS = [
    ("S01-character", "Medium full shot, summer evening in an old Chinese apartment corridor. The cat-headed "
     "character wears a short-sleeved school uniform and stands by the doorway, holding a blank white exam "
     "result sheet with no marks or text. Slightly raised ears, restrained hopeful expression. Warm sunset "
     "from the corridor entrance, cool violet shadows, off-center composition. Palette: muted orange, brown, "
     "grey-green and charcoal; the blank paper is the only bright area."),
    ("S21-action", "Night study room, medium shot. The same cat-headed character sits at a desk covered with "
     "unmarked draft pages showing only simple abstract line diagrams, resting the chin on one hand while "
     "studying. One warm desk lamp, room outside the lamp pool nearly black, blue-black window. Keep both "
     "hands anatomically clear and readable; no letters, numbers, formulas or legible writing. Muted grey, "
     "sage, charcoal and brown palette with one small warm lamp accent."),
    ("S51-detail", "Close shot at a sunlit construction site at noon. The same cat-headed worker in a plain "
     "work shirt tips a yellow safety helmet forward; a thin stream of sweat pours from inside the helmet. "
     "The helmet and pouring water are the focal point, character face remains recognizable, hand clearly "
     "grips the helmet rim. Hard overhead light, pale concrete, muted worksite palette with helmet yellow "
     "as the only saturated accent. No text or logos."),
]


def get_key() -> str:
    value = os.environ.get("IMAGE_API_KEY_XXC", "").strip()
    if value:
        return value
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, "IMAGE_API_KEY_XXC")[0]


def multipart(fields: dict[str, str], image_path: Path) -> tuple[bytes, str]:
    boundary = "----codex" + uuid.uuid4().hex
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    ctype = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{image_path.name}\"\r\nContent-Type: {ctype}\r\n\r\n".encode())
    chunks.extend((image_path.read_bytes(), b"\r\n", f"--{boundary}--\r\n".encode()))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def run_one(tag: str, model: str, shot: str, body: str, key: str) -> dict:
    stem = f"{tag}-{shot}"
    fields = {"model": model, "prompt": f"{STYLE} {body}", "size": SIZE, "n": "1"}
    payload, content_type = multipart(fields, REFERENCE)
    request = urllib.request.Request(
        f"{BASE}/images/edits", data=payload, method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": content_type,
                 "Accept": "application/json", "User-Agent": UA})
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=900) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read()
    except Exception as exc:
        return {"model": model, "shot": shot, "ok": False, "error": f"{type(exc).__name__}: {exc}"}
    result = {"model": model, "shot": shot, "status": status, "elapsed_s": round(time.time() - started, 1)}
    if status != 200:
        result.update({"ok": False, "error": raw[:500].decode("utf-8", "replace")})
        return result
    try:
        data = json.loads(raw.decode("utf-8"))
        item = (data.get("data") or [{}])[0]
        dest = RAW / f"{stem}.png"
        if item.get("b64_json"):
            dest.write_bytes(base64.b64decode(item["b64_json"]))
            delivery = "b64_json"
        elif item.get("url"):
            req = urllib.request.Request(item["url"], headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=300) as response:
                dest.write_bytes(response.read())
            delivery = "url"
        else:
            raise ValueError("response has neither b64_json nor url")
        with Image.open(dest) as image:
            image.load()
            result.update({"ok": True, "file": str(dest.resolve()), "dims": list(image.size),
                           "bytes": dest.stat().st_size, "delivery": delivery})
    except Exception as exc:
        result.update({"ok": False, "error": f"response parse/download failed: {type(exc).__name__}: {exc}"})
    return result


def main() -> int:
    if not REFERENCE.exists():
        raise SystemExit(f"Missing reference image: {REFERENCE}")
    RAW.mkdir(parents=True, exist_ok=True)
    key = get_key()
    results = []
    for shot, prompt in SHOTS:
        for tag, model in MODELS:
            result = run_one(tag, model, shot, prompt, key)
            results.append(result)
            (RUN / "report.json").write_text(json.dumps({"size_requested": SIZE, "reference": str(REFERENCE), "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({k: v for k, v in result.items() if k != "error"}, ensure_ascii=False), flush=True)
            if not result.get("ok"):
                print(json.dumps({"shot": shot, "model": model, "error": result.get("error")}, ensure_ascii=False), flush=True)
                if "quota" in str(result.get("error", "")).lower() or result.get("status") in (401, 402, 403):
                    return 1
    return 0 if all(item.get("ok") for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
