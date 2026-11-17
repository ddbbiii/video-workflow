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

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets" / "人生体验" / "characters" / "catman-20261113" / "character-reference"
TARGET = ASSETS / "turnaround.png"
IDENTITY = ASSETS / "ref-face.png"
STYLE = ASSETS / "face-style-D.png"
BASE = os.environ.get("IMAGE_API_BASE_URL_XXC", "https://xxcapi.com/v1").rstrip("/")
MODEL = "AZ-gpt-image-2"
SIZE = "1536x1024"
UA = "OpenAI/Python 1.60.0"

PROMPT = """
Edit the supplied approved three-view character turnaround. Return one clean white-background
character sheet with exactly the same canvas, three equal vertical panels, view order, character
scale, full-body poses, clothing, body proportions, hoodie folds, trousers, hands, feet, outlines,
lighting, and all non-head pixels as closely as possible. This is a tightly scoped face-identity
correction only. Match the approved identity reference: eyes with black pupils occupying most of each
eye, a thin warm amber iris rim, one small highlight, and gently hooded upper lids; small Scottish Fold
ears folded forward and close against the skull; cream muzzle pads with visible whisker-root dots and
three fine, long white whiskers fanning outward on each side. Keep the clean D-style illustrated
linework and flat color treatment. Do not copy photographic fur texture.

Correct the FRONT and SIDE cat heads to match the approved individual cat identity:
EYES: reduce the oversized anime-eye appearance; preserve the eye spacing and gaze direction, make
the black pupils occupy most of each eye, use only a thin warm amber iris rim, keep a small highlight,
and let the upper lids gently hood the eyes. Do not make the eyes tiny or sleepy.
EARS: make the Scottish Fold ears short, low, and folded forward close against the skull, with only a
small folded edge visible from the front. In profile, show a clearly folded ear lying close to the head,
not a curled upright ear, not a round loop, and not a pointed standing ear.
WHISKERS: keep the cream muzzle pads and nose geometry; define the whisker-root dots and add three
fine, long white whiskers on each side, fanning naturally outward. Keep them delicate and readable,
not thick black lines.
Preserve the orange-and-cream markings and head silhouette. The BACK head remains turned away; only
make its folded ears low and close to the skull. Do not add facial features to the back view. Preserve
the hoodie collar beneath the chin. Do not change the body, clothes, poses, panel dividers, background,
or add labels, text, props, extra characters, or extra limbs. This is not a redesign or a new character.
""".strip()


def get_key() -> str:
    value = os.environ.get("IMAGE_API_KEY_XXC", "").strip()
    if value:
        return value
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, "IMAGE_API_KEY_XXC")[0]


def multipart(paths: list[Path]) -> tuple[bytes, str]:
    boundary = "----codex" + uuid.uuid4().hex
    chunks = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"model\"\r\n\r\n{MODEL}\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"prompt\"\r\n\r\n{PROMPT}\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"size\"\r\n\r\n{SIZE}\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"n\"\r\n\r\n1\r\n".encode(),
    ]
    for path in paths:
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{path.name}\"\r\n"
            f"Content-Type: {content_type}\r\n\r\n".encode()
        )
        chunks.extend((path.read_bytes(), b"\r\n"))
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def main() -> int:
    for path in (TARGET, IDENTITY, STYLE):
        if not path.is_file():
            raise SystemExit(f"Missing input image: {path}")
    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT / "turnaround-face-refined-candidate.png"
    body, content_type = multipart([TARGET])
    request = urllib.request.Request(
        f"{BASE}/images/edits",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {get_key()}",
            "Content-Type": content_type,
            "Accept": "application/json",
            "User-Agent": UA,
        },
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=900) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as error:
        status, raw = error.code, error.read()
    if status != 200:
        error = raw[:1000].decode("utf-8", "replace")
        failure = {
            "purpose": "Face identity refinement candidate for the approved catman turnaround",
            "endpoint": f"{BASE}/images/edits",
            "model": MODEL,
            "inputs": {"edit_target": str(TARGET), "identity_and_style_references_used_for_prompt_review": [str(IDENTITY), str(STYLE)]},
            "attempt": {"http_status": status, "elapsed_s": round(time.time() - started, 1), "error": error},
            "status": "No image returned; formal turnaround was not changed.",
        }
        (OUT / "manifest.json").write_text(json.dumps(failure, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"ok": False, "status": status, "error": error}, ensure_ascii=False))
        return 1

    item = (json.loads(raw.decode("utf-8")).get("data") or [{}])[0]
    if item.get("b64_json"):
        output.write_bytes(base64.b64decode(item["b64_json"]))
    elif item.get("url"):
        download = urllib.request.Request(item["url"], headers={"User-Agent": UA})
        with urllib.request.urlopen(download, timeout=300) as response:
            output.write_bytes(response.read())
    else:
        raise RuntimeError("API returned neither b64_json nor url")

    with Image.open(output) as image:
        image.load()
        dimensions = list(image.size)
    manifest = {
        "purpose": "Face identity refinement candidate for the approved catman turnaround",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "endpoint": f"{BASE}/images/edits",
        "model": MODEL,
        "size": SIZE,
        "inputs": {"edit_target": str(TARGET), "identity_and_style_references_used_for_prompt_review": [str(IDENTITY), str(STYLE)]},
        "output": str(output.resolve()),
        "dimensions": dimensions,
        "prompt": PROMPT,
        "status": "Candidate only; pending user review. The formal turnaround was not overwritten.",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "file": str(output.resolve()), "dimensions": dimensions,
                      "elapsed_s": round(time.time() - started, 1)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
