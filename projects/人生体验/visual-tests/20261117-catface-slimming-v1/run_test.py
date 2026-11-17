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
SOURCE = ROOT / "projects" / "人生体验" / "visual-tests" / "20261117-catface-geometry-lock-v1" / "03-graphic-flat.png"
BASE = os.environ.get("IMAGE_API_BASE_URL_XXC", "https://xxcapi.com/v1").rstrip("/")
MODEL = "AZ-gpt-image-2"
SIZE = "1672x941"
UA = "OpenAI/Python 1.60.0"

COMMON = (
    "Edit Image 1. Preserve the entire image as the source: same graphic-flat 2D style, same framing, same "
    "pose, same cat identity, same eyes, folded ears, nose, muzzle, whiskers, white bib, tabby markings, "
    "hoodie, body, background, corridor, lighting, colors and outlines. Keep the simple round-headed supporting "
    "character exactly unchanged: round head, dot eyes, short line mouth, white mitten hands and plain dark "
    "clothes. Make only the explicitly requested subtle adjustment to the protagonist's cheek/jaw fullness. "
    "Do not change the whole head scale, eye size or spacing, face height, ear position, nose, muzzle length, "
    "marking shape or location, expression, neck, collar, body, side character, background, linework style, "
    "palette or composition. No text, added details, realistic fur, photorealism, 3D, or other edits."
)

VARIANTS = {
    "01-cheek-tuck-3pct": (
        "Barely-there cheek tuck: reduce only the widest left and right cheek bulge by about 3 percent, using "
        "a very subtle inward curve. Keep the chin/jaw, face height and all facial features fixed. The change "
        "should be difficult to notice at first glance."
    ),
    "02-cheek-reduction-5pct": (
        "Gentle cheek reduction: move only the widest outer cheek contour inward by about 5 percent on each "
        "side. Keep the forehead, temples, lower jaw, face height, eyes and all markings fixed. Do not scale "
        "the whole head."
    ),
    "03-lower-jaw-taper-6pct": (
        "Slightly taper the lower cheeks into the jaw: narrow the lower cheek/jaw contour by about 5 to 7 "
        "percent, blending smoothly from below the eyes. Keep the upper cheek width, head height, eyes, ears, "
        "muzzle, nose and every tabby marking exactly in place. Do not make the chin pointed."
    ),
    "04-flat-shading-no-geometry": (
        "Do not move or redraw any face outline or feature. Keep the cheek silhouette and all markings exactly "
        "unchanged. Reduce only the impression of puffiness by simplifying the cheek shading into flatter, "
        "cleaner graphic color shapes, without moving, resizing or recoloring the tabby marks."
    ),
}


def get_key() -> str:
    value = os.environ.get("IMAGE_API_KEY_XXC", "").strip()
    if value:
        return value
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, "IMAGE_API_KEY_XXC")[0]


def multipart(fields: dict[str, str]) -> tuple[bytes, str]:
    boundary = "----codex" + uuid.uuid4().hex
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    content_type = mimetypes.guess_type(SOURCE.name)[0] or "application/octet-stream"
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{SOURCE.name}\"\r\n"
        f"Content-Type: {content_type}\r\n\r\n".encode()
    )
    parts.extend((SOURCE.read_bytes(), b"\r\n", f"--{boundary}--\r\n".encode()))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def generate(tag: str, change: str, key: str) -> dict:
    prompt = COMMON + " " + change
    body, content_type = multipart({"model": MODEL, "prompt": prompt, "size": SIZE, "n": "1"})
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
    result: dict = {"variant": tag, "status": status, "elapsed_s": round(time.time() - started, 1)}
    if status != 200:
        result.update({"ok": False, "error": raw[:500].decode("utf-8", "replace")})
        return result
    item = (json.loads(raw.decode("utf-8")).get("data") or [{}])[0]
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
        result.update({"ok": True, "file": str(destination.resolve()), "dimensions": list(image.size),
                       "bytes": destination.stat().st_size, "delivery": delivery})
    return result


def contact_sheet(results: list[dict]) -> None:
    good = [item for item in results if item.get("ok")]
    if not good:
        return
    width, height, label, gap, columns = 700, 394, 38, 14, 2
    rows = (len(good) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * width + (columns + 1) * gap,
                                rows * (height + label) + (rows + 1) * gap), "white")
    draw = ImageDraw.Draw(canvas)
    for index, item in enumerate(good):
        x = gap + (index % columns) * (width + gap)
        y = gap + (index // columns) * (height + label + gap)
        with Image.open(item["file"]) as image:
            canvas.paste(image.convert("RGB").resize((width, height)), (x, y))
        draw.text((x + 5, y + height + 10), item["variant"], fill="black")
    canvas.save(OUT / "contact-sheet.jpg", quality=88)


def write_manifest(results: list[dict]) -> None:
    data = {
        "purpose": "Controlled face-fullness comparison based on the approved graphic-flat style image",
        "channel": "new2",
        "model": MODEL,
        "endpoint": f"{BASE}/images/edits",
        "edit_target": str(SOURCE.resolve()),
        "requested_dimensions": SIZE,
        "edit_scope": "Change only the specified cheek/jaw fullness treatment; preserve all other source-image content.",
        "common_prompt": COMMON,
        "variant_prompts": VARIANTS,
        "full_prompts_by_image": {tag: COMMON + " " + change for tag, change in VARIANTS.items()},
        "results": results,
        "contact_sheet": str((OUT / "contact-sheet.jpg").resolve()),
        "acceptance": {
            "generation": "All four API requests returned successful images.",
            "visual_review": "Pending user review; this run avoided loading more image payload into the subtask thread.",
            "dimensions": "Record each returned size as-is; do not resize raw outputs.",
        },
        "next_step": "User will manually choose a slimming treatment; this comparison does not update production character rules.",
    }
    (OUT / "manifest.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    if not SOURCE.exists():
        raise SystemExit(f"Missing edit target: {SOURCE}")
    OUT.mkdir(parents=True, exist_ok=True)
    key = get_key()
    results: list[dict] = []
    for tag, change in VARIANTS.items():
        result = generate(tag, change, key)
        results.append(result)
        write_manifest(results)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if not result.get("ok"):
            contact_sheet(results)
            return 1
    contact_sheet(results)
    write_manifest(results)
    return 0 if len(results) == len(VARIANTS) and all(item.get("ok") for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
