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

IDENTITY_LOCK = (
    "Preserve this exact individual cat's visible facial geometry and identity. Do not redesign or beautify. "
    "Keep the same broad round cheek silhouette, the same small outward-folded ears lying close to the skull, "
    "the same eye spacing and eye size, same large near-black pupils with narrow amber rings, same small pink "
    "nose, same short muzzle width, same cream muzzle pads, same white whiskers, same forehead blaze/M and the "
    "same orange cheek-mark positions and shapes. Do not enlarge the eyes, narrow the cheeks, lengthen the "
    "muzzle, erect the ears, move the markings, invent new spots, or replace the cat with a generic orange cat. "
    "Use Image 1 only for identity geometry and marking placement. Do not carry over its photographic fur, "
    "lighting, or surface texture."
)

COMMON = (
    "Create a face-focused horizontal 16:9 2D anime story illustration. The protagonist is a cat-headed "
    "person with this exact orange Scottish Fold face. Show head, short neck, shoulders and upper chest; the "
    "cat face is large and clearly readable, taking roughly half the frame height. Head sits naturally into "
    "the short neck and grey hoodie opening; no floating head or pasted seam. The protagonist's body is a "
    "compact upright human form in a grey hoodie; if paws are visible, they are rounded cat paws. Include one "
    "small but clearly visible supporting character at frame right in the required simple cartoon design: "
    "smooth round head, two dot eyes, one short line mouth, no nose and no detailed facial features, white "
    "mitten hands without fingers, plain dark simple clothes. Never render the supporting character as an "
    "ordinary realistic person. Both characters share a clean illustrated language, but the supporting figure "
    "stays much simpler. Apartment corridor, closed door and wall lamp in soft focus, muted cool-neutral palette "
    "with a small warm lamp accent. Medium-close two-shot, protagonist at left and supporting figure at right. "
    "No text, watermark, logo, UI, photorealism, 3D, plastic toy look, photographic fur strands, soft photo "
    "highlights, extra people or extra limbs."
)

VARIANTS = {
    "01-clean-cel": (
        "Render the cat face as clean cel anime: precise consistent dark grey-blue contour, broad flat color "
        "shapes, a few short intentional fur accents, and two or three clean hard-edged shadow shapes. Keep the "
        "facial geometry and markings exactly as specified."
    ),
    "02-gentle-ink": (
        "Render as refined hand-drawn anime ink: clean slightly hand-drawn contours, controlled line accents "
        "around the eyes, muzzle and tabby markings, flat color masses and restrained cel shadows. No pencil "
        "smudging, scratchy crosshatching or photoreal fur detail. Keep every facial feature in its original "
        "position and proportion."
    ),
    "03-graphic-flat": (
        "Render as restrained graphic anime: crisp outer contour, simple interior lines, grouped flat fur "
        "colors. Reproduce the source tabby markings in the same locations and with the same direction; do not "
        "turn them into abstract cheek patches or decorative symbols. Keep the source face proportions unchanged."
    ),
    "04-soft-illustration": (
        "Render as softly painted 2D anime illustration: controlled brush-shaped color transitions on the face, "
        "clean designed contour and restrained soft background depth. The face must remain an illustration, "
        "with no individual realistic hairs, photographic shine or airbrushed skin-like shading. Keep exact source "
        "facial geometry and marking placement."
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
    content_type = mimetypes.guess_type(REFERENCE.name)[0] or "application/octet-stream"
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{REFERENCE.name}\"\r\n"
        f"Content-Type: {content_type}\r\n\r\n".encode()
    )
    parts.extend((REFERENCE.read_bytes(), b"\r\n", f"--{boundary}--\r\n".encode()))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def generate(tag: str, variant_prompt: str, key: str) -> dict:
    prompt = f"{IDENTITY_LOCK} {COMMON} {variant_prompt}"
    data, content_type = multipart({"model": MODEL, "prompt": prompt, "size": SIZE, "n": "1"})
    request = urllib.request.Request(
        f"{BASE}/images/edits", data=data, method="POST",
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


def make_contact_sheet(results: list[dict]) -> None:
    good = [item for item in results if item.get("ok")]
    if not good:
        return
    width, height, label, gap = 620, 349, 36, 16
    columns = 2
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


def write_manifest(results: list[dict], acceptance: dict | str = "Pending visual review") -> None:
    prompts = {tag: f"{IDENTITY_LOCK} {COMMON} {prompt}" for tag, prompt in VARIANTS.items()}
    data = {
        "purpose": "Face-focused anime-rendering comparison with strict identity and marking locks",
        "channel": "new2",
        "model": MODEL,
        "endpoint": f"{BASE}/images/edits",
        "reference": str(REFERENCE.resolve()),
        "requested_dimensions": SIZE,
        "identity_lock": IDENTITY_LOCK,
        "common_prompt": COMMON,
        "variant_prompts": VARIANTS,
        "full_prompts": prompts,
        "results": results,
        "contact_sheet": str((OUT / "contact-sheet.jpg").resolve()),
        "acceptance": acceptance,
        "next_step": "Only candidates that preserve the original cat's face geometry and markings may proceed to a full scene style test.",
    }
    (OUT / "manifest.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    if not REFERENCE.exists():
        raise SystemExit(f"Missing reference: {REFERENCE}")
    OUT.mkdir(parents=True, exist_ok=True)
    key = get_key()
    results = []
    for tag, prompt in VARIANTS.items():
        result = generate(tag, prompt, key)
        results.append(result)
        write_manifest(results)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if not result.get("ok"):
            make_contact_sheet(results)
            return 1
    make_contact_sheet(results)
    write_manifest(results)
    return 0 if len(results) == len(VARIANTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
