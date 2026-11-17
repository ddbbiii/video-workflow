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

OUT = Path(__file__).resolve().parent
REFERENCE = Path(r"E:\Temp\codex-clipboard-8c0cdac7-cca4-4e5e-8cc0-8e76ab5f09f2.png")
BASE = os.environ.get("IMAGE_API_BASE_URL_XXC", "https://xxcapi.com/v1").rstrip("/")
MODEL = "AZ-gpt-image-2"
SIZE = "1536x1024"
UA = "OpenAI/Python 1.60.0"

LOCK = (
    "Edit Image 1 directly. This is a style-rendering change only. Preserve the exact original composition, "
    "camera, crop, framing, head size and placement, orientation, pose, and plain white background. Show only "
    "the same cat face as in the source: no body, shoulders, clothing, props, scene, added objects, text, or "
    "border. Preserve identity geometry exactly: broad full cheek silhouette; exact eye spacing, shape, and "
    "size; folded ear shape and placement; nose placement and shape; muzzle width and proportions; whiskers; "
    "and the exact placement, shape, and direction of every forehead blaze and stripe. Do not slim or reshape "
    "the face, enlarge the eyes, move features, change markings, beautify, or make a generic kawaii redesign. "
    "Do not retain photographic fur rendering, photorealistic texture, glossy photo highlights, or 3D volume. "
    "Keep the result clearly drawn as 2D anime art."
)

VARIANTS = {
    "A-clean-cel": (
        "Render in clean cel anime: crisp, confident contour lines; broad, simple flat color fills; a few "
        "carefully placed flat shadow shapes; minimal interior linework. Keep the original colors and all "
        "identity details in their exact original positions."
    ),
    "B-hand-ink": (
        "Render as hand-drawn anime ink art: assured, slightly organic ink contours and only a few purposeful "
        "strokes that clarify the original stripes, muzzle, and whiskers. Use restrained flat color groups and "
        "very limited shadow. No scratchy sketching or extra decorative strokes."
    ),
    "C-storybook-painted": (
        "Render as a soft Japanese storybook painting in drawn anime style. Simplify fur into a few broad, "
        "grouped painted shapes with gentle brush edges, while keeping the cheek, eyes, ears, muzzle, nose, "
        "whiskers, and markings geometrically identical to the source. Keep the white background white. It "
        "must still look illustrated, not photographic."
    ),
    "D-bold-graphic": (
        "Render as elegant graphic 2D animation art: a bold but refined outer contour, clean interior lines, "
        "broad flat color regions, and a small number of controlled shadow shapes. Keep the same source colors "
        "and marking layout, with no poster elements, graphic framing, or added design."
    ),
}


def get_key() -> str:
    value = os.environ.get("IMAGE_API_KEY_XXC", "").strip()
    if value:
        return value
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, "IMAGE_API_KEY_XXC")[0]


def multipart(prompt: str) -> tuple[bytes, str]:
    boundary = "----codex" + uuid.uuid4().hex
    parts = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"model\"\r\n\r\n{MODEL}\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"prompt\"\r\n\r\n{prompt}\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"size\"\r\n\r\n{SIZE}\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"n\"\r\n\r\n1\r\n".encode(),
    ]
    mime = mimetypes.guess_type(REFERENCE.name)[0] or "application/octet-stream"
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{REFERENCE.name}\"\r\n"
        f"Content-Type: {mime}\r\n\r\n".encode()
    )
    parts.extend((REFERENCE.read_bytes(), b"\r\n", f"--{boundary}--\r\n".encode()))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def generate(tag: str, prompt: str, key: str) -> dict:
    body, content_type = multipart(prompt)
    request = urllib.request.Request(
        f"{BASE}/images/edits", data=body, method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": content_type,
                 "Accept": "application/json", "User-Agent": UA})
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=900) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as error:
        status, raw = error.code, error.read()
    item_result = {"variant": tag, "status": status, "elapsed_s": round(time.time() - started, 1)}
    if status != 200:
        item_result.update({"ok": False, "error": raw[:500].decode("utf-8", "replace")})
        return item_result
    data = (json.loads(raw.decode("utf-8")).get("data") or [{}])[0]
    destination = OUT / f"{tag}.png"
    if data.get("b64_json"):
        destination.write_bytes(base64.b64decode(data["b64_json"]))
        delivery = "b64_json"
    elif data.get("url"):
        with urllib.request.urlopen(urllib.request.Request(data["url"], headers={"User-Agent": UA}), timeout=300) as response:
            destination.write_bytes(response.read())
        delivery = "url"
    else:
        raise ValueError("Response has neither b64_json nor url")
    with Image.open(destination) as image:
        image.load()
        item_result.update({"ok": True, "file": str(destination.resolve()), "dimensions": list(image.size),
                            "bytes": destination.stat().st_size, "delivery": delivery})
    return item_result


def contact_sheet(results: list[dict]) -> None:
    good = [item for item in results if item.get("ok")]
    if not good:
        return
    width, height, label, gap = 420, 236, 34, 12
    canvas = Image.new("RGB", (2 * width + 3 * gap, 2 * (height + label) + 3 * gap), "white")
    draw = ImageDraw.Draw(canvas)
    for index, item in enumerate(good):
        x, y = gap + (index % 2) * (width + gap), gap + (index // 2) * (height + label + gap)
        with Image.open(item["file"]) as image:
            canvas.paste(image.convert("RGB").resize((width, height)), (x, y))
        draw.text((x + 4, y + height + 8), item["variant"], fill="black")
    canvas.save(OUT / "contact-sheet.jpg", quality=86)


def save_manifest(results: list[dict], acceptance: dict | str = "Pending visual review") -> None:
    payload = {
        "purpose": "Four anime rendering styles applied directly to the uploaded cat-face image",
        "channel": "new2",
        "model": MODEL,
        "endpoint": f"{BASE}/images/edits",
        "reference": str(REFERENCE.resolve()),
        "reference_dimensions": list(Image.open(REFERENCE).size),
        "requested_dimensions": SIZE,
        "identity_and_composition_lock": LOCK,
        "style_prompts": VARIANTS,
        "full_prompts": {tag: f"{LOCK} {style}" for tag, style in VARIANTS.items()},
        "results": results,
        "contact_sheet": str((OUT / "contact-sheet.jpg").resolve()),
        "acceptance": acceptance,
    }
    (OUT / "manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    if not REFERENCE.exists():
        raise SystemExit(f"Missing reference image: {REFERENCE}")
    OUT.mkdir(parents=True, exist_ok=True)
    key = get_key()
    results = []
    for tag, style in VARIANTS.items():
        prompt = f"{LOCK} {style}"
        result = generate(tag, prompt, key)
        results.append(result)
        save_manifest(results)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if not result.get("ok"):
            contact_sheet(results)
            return 1
    contact_sheet(results)
    save_manifest(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
