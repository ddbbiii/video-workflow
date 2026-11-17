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

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
REFERENCE = ROOT / "assets" / "人生体验" / "characters" / "catman-20261113" / "character-reference" / "ref-face.png"
BASE = os.environ.get("IMAGE_API_BASE_URL_XXC", "https://xxcapi.com/v1").rstrip("/")
MODEL = "AZ-gpt-image-2"
SIZE = "1672x941"
UA = "OpenAI/Python 1.60.0"

COMMON = (
    "Illustrate a 16:9 hand-drawn 2D story scene in a lived-in apartment corridor. Use Image 1 only as the "
    "protagonist's identity reference. Show the same orange Scottish Fold cat-headed person: broad round face, "
    "full cheeks, short muzzle, small folded ears close to the crown, large dark round eyes with a narrow amber rim, "
    "pink nose, cream muzzle, white whiskers, cream-orange tabby markings including the forehead M, and white "
    "chest bib. Compact upright human body about 3.2 head-heights, very short neck, gray hoodie, black trousers, "
    "rounded cat-paw hands and bare cat-paw feet, no tail. Beside him is the same ordinary human supporting "
    "character in every version: a young adult Chinese man with short straight black hair, natural adult body "
    "proportions, muted navy jacket over a light shirt and dark trousers. He stands facing the cat character in a "
    "calm conversation, hands relaxed. Render both characters with the same clean dark grey-blue outline, flat "
    "colors and restrained hard-edged shadows; the human remains recognizably human, not a cat and not a blank "
    "mannequin. Background: modest apartment corridor with one doorway, wall lamp, potted plant and subtle wall "
    "wear; carefully painted environment with soft depth and contact shadows. Medium-full two-shot, both characters "
    "visible from head to mid-shin, cat character on the right and human on the left, similar visual weight, clear "
    "space between them. Neutral conversational expressions, no dramatic action. No text, letters, numbers, logo, "
    "watermark, photoreal human, 3D render, plastic toy look, extra limbs, human fingers on the cat character, "
    "shoes on the cat character, or tail."
)

VARIANTS = {
    "01-balanced-render": (
        "Direction 1, balanced rendering: retain all distinctive facial features and tabby pattern. Use medium "
        "fur detail, with a few clean illustrated strokes rather than photographic strands. The cat face and body "
        "share one outline weight, one light direction, and the same hard-edged shadow language. Shape the hoodie "
        "collar and hood so they gently support the head and visually join the very short neck to the shoulders."
    ),
    "02-proportion-bridge": (
        "Direction 2, proportion bridge: retain the same facial features and face detail, but make the cat head "
        "modestly smaller, about ten percent relative to the previous proportions, and make the shoulders a little "
        "broader. Keep the compact 3.2-head-height body and very short neck. Use a clearly shaped hood opening and "
        "collar that support the head without hiding the face. Do not turn him into a generic human or a full cat."
    ),
    "03-bib-collar-flow": (
        "Direction 3, bib and collar flow: keep the current head scale and all facial identity features. Retain the "
        "white chest bib, and let the pale inner edge of the hoodie opening visually echo and frame the bib so the "
        "face-to-chest transition feels designed as one character. Simplify fur to fewer broader strokes while "
        "keeping the forehead M, cheek stripes, eyes, muzzle, nose and whiskers clearly recognizable. Do not turn "
        "the bib into a shirt or cover it with the hoodie."
    ),
    "04-richer-body-language": (
        "Direction 4, body language: keep the current head scale, face details and markings. Give the hoodie and "
        "trousers slightly richer hand-drawn treatment with a few deliberate fabric folds, two or three flat tones "
        "per garment and the same subtle line character used around the cat face. Keep shadows hard-edged and "
        "restrained. The human supporting character uses the same illustration finish. The face may remain the "
        "most detailed area, but avoid any photographic or 3D rendering."
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
    payload, content_type = multipart(
        {"model": MODEL, "prompt": COMMON + " " + detail, "size": SIZE, "n": "1"}, REFERENCE
    )
    request = urllib.request.Request(
        f"{BASE}/images/edits",
        data=payload,
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
    data = json.loads(raw.decode("utf-8"))
    item = (data.get("data") or [{}])[0]
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


def make_contact_sheet(results: list[dict]) -> Path:
    tile_w, tile_h, label_h, gap = 780, 439, 34, 16
    canvas = Image.new("RGB", (tile_w * 2 + gap * 3, (tile_h + label_h) * 2 + gap * 3), "white")
    draw = ImageDraw.Draw(canvas)
    for index, result in enumerate(results):
        source = Image.open(result["file"]).convert("RGB")
        source.thumbnail((tile_w, tile_h), Image.Resampling.LANCZOS)
        x = gap + (index % 2) * (tile_w + gap)
        y = gap + (index // 2) * (tile_h + label_h + gap)
        canvas.paste(source, (x, y))
        draw.text((x + 5, y + tile_h + 8), result["variant"], fill="#202020")
    path = OUT / "contact-sheet.jpg"
    canvas.save(path, quality=88)
    return path


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
    contact_sheet = make_contact_sheet(results) if results else None
    manifest = {
        "purpose": "Four-direction style test for cat-head integration with one supporting human character",
        "channel": "new2",
        "model": MODEL,
        "endpoint": f"{BASE}/images/edits",
        "reference": str(REFERENCE.resolve()),
        "requested_dimensions": SIZE,
        "common_prompt": COMMON,
        "variant_prompts": VARIANTS,
        "results": results,
        "contact_sheet": str(contact_sheet.resolve()) if contact_sheet else None,
        "acceptance": "Pending visual review",
        "next_step": "Compare face identity, head-body integration and consistency with the supporting human character.",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if len(results) == len(VARIANTS) and all(item.get("ok") for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
