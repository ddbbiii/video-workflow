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

from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
REFERENCE = ROOT / "assets" / "人生体验" / "characters" / "catman-20261113" / "character-reference" / "ref-face.png"
BASE = os.environ.get("IMAGE_API_BASE_URL_XXC", "https://xxcapi.com/v1").rstrip("/")
MODEL = "AZ-gpt-image-2"
SIZE = "1672x941"
UA = "OpenAI/Python 1.60.0"

COMMON = (
    "Create a polished 2D hand-drawn narrative illustration in a horizontal 16:9 frame. "
    "Use Image 1 only as the protagonist's identity reference. The protagonist is the same orange "
    "Scottish Fold cat-headed person: compact round head, full cheeks, short muzzle, small ears folded "
    "forward, large round black eyes with a narrow amber rim and a small highlight, pink nose, cream muzzle, "
    "white whiskers, cream-orange tabby markings including the forehead M, and a white chest bib. "
    "He has a short stocky upright human body about 3.2 head-heights, very short neck, narrow shoulders, "
    "grey hoodie and black trousers; hands and feet are small rounded cat paws, no shoes, no tail. "
    "The head, short neck and hoodie collar must read as one deliberately designed character silhouette: "
    "the hood and collar gently support the base of the head, shoulders sit naturally beneath it, and there "
    "is no visible seam, floating head, or pasted-on effect. One consistent dark grey-blue outline weight "
    "and coherent light direction across head and body. Character uses clean flat fills and restrained "
    "hard-edged shadows; background is a carefully painted apartment corridor with a visible doorway and "
    "wall lamp, subtle depth, contact shadow, and soft ambient light. Medium shot, three-quarter view, "
    "character slightly off-center, relaxed neutral expression, both cat paws visible near the hoodie hem. "
    "Cool-neutral muted palette with a small warm lamp accent. No text, letters, numbers, watermark, logo, "
    "photoreal human skin, 3D render, plastic toy look, extra limbs, or human fingers."
)

VARIANTS = {
    "A-graphic-face": (
        "Variant A: preserve the cat's recognizable identity anchors and expression, but translate the face "
        "into the same graphic hand-drawn language as the body. Render fur as a few broad, clean flat shapes; "
        "keep only a small number of short tabby strokes. Simplify tiny fur strands and fine facial texture. "
        "The eyes, folded ears, round cheeks, short muzzle, nose, whiskers and M marking remain clear and "
        "recognizable."
    ),
    "B-feature-preserved": (
        "Variant B: preserve the reference cat's facial features and markings as closely as possible: the exact "
        "round cheek silhouette, folded ear shape, eye spacing and shape, short muzzle, pink nose, cream muzzle, "
        "white whiskers, forehead M and cheek tabby pattern. Keep the face more detailed than Variant A, while "
        "rendering its fur in controlled illustrated strokes and giving its outlines, shadow direction and edge "
        "quality the same hand-drawn finish as the hoodie and body. Do not change the identity or make the head "
        "larger than the reference character proportions."
    ),
}


def get_key() -> str:
    value = os.environ.get("IMAGE_API_KEY_XXC", "").strip()
    if value:
        return value
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, "IMAGE_API_KEY_XXC")[0]


def multipart(fields: dict[str, str], image_path: Path) -> tuple[bytes, str]:
    boundary = "----codex" + uuid.uuid4().hex
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode()
        )
    content_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; "
        f"filename=\"{image_path.name}\"\r\nContent-Type: {content_type}\r\n\r\n".encode()
    )
    parts.extend((image_path.read_bytes(), b"\r\n", f"--{boundary}--\r\n".encode()))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def generate(tag: str, detail: str, key: str) -> dict:
    prompt = COMMON + " " + detail
    body, content_type = multipart(
        {"model": MODEL, "prompt": prompt, "size": SIZE, "n": "1"}, REFERENCE
    )
    request = urllib.request.Request(
        f"{BASE}/images/edits",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
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
    result: dict = {"variant": tag, "status": status, "elapsed_s": round(time.time() - started, 1)}
    if status != 200:
        result.update({"ok": False, "error": raw[:500].decode("utf-8", "replace")})
        return result
    payload = json.loads(raw.decode("utf-8"))
    item = (payload.get("data") or [{}])[0]
    destination = OUT / f"{tag}.png"
    if item.get("b64_json"):
        destination.write_bytes(base64.b64decode(item["b64_json"]))
        delivery = "b64_json"
    elif item.get("url"):
        download = urllib.request.Request(item["url"], headers={"User-Agent": UA})
        with urllib.request.urlopen(download, timeout=300) as response:
            destination.write_bytes(response.read())
        delivery = "url"
    else:
        raise ValueError("Response has neither b64_json nor url")
    with Image.open(destination) as image:
        image.load()
        result.update(
            {
                "ok": True,
                "file": str(destination.resolve()),
                "dimensions": list(image.size),
                "bytes": destination.stat().st_size,
                "delivery": delivery,
            }
        )
    return result


def main() -> int:
    if not REFERENCE.exists():
        raise SystemExit(f"Missing reference: {REFERENCE}")
    key = get_key()
    results = []
    for tag, detail in VARIANTS.items():
        result = generate(tag, detail, key)
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if not result.get("ok"):
            break
    manifest = {
        "purpose": "A/B concept test for cat-head integration in the life-experience line",
        "channel": "new2",
        "model": MODEL,
        "endpoint": f"{BASE}/images/edits",
        "reference": str(REFERENCE.resolve()),
        "requested_dimensions": SIZE,
        "common_prompt": COMMON,
        "variant_prompts": VARIANTS,
        "results": results,
        "acceptance": "Pending visual review",
        "next_step": "Compare face identity, head-neck transition, and style consistency at full size.",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if len(results) == len(VARIANTS) and all(item.get("ok") for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
