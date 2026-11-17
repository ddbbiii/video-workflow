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
    "Create a horizontal 16:9 hand-drawn 2D anime story illustration. Use Image 1 solely to preserve the "
    "protagonist's identity and facial geometry; do not copy its photographic fur texture, lighting, or "
    "surface rendering. The protagonist is the same orange Scottish Fold cat-headed person: preserve the "
    "round cheek silhouette, small ears folded forward, eye spacing and size, short muzzle, pink nose, cream "
    "muzzle pads, white whiskers, forehead M and cheek tabby placement. Keep these recognizable features, "
    "but render them as deliberate illustrated shapes, not a realistic cat photograph. He has a compact upright "
    "human body about 3 to 3.2 head-heights, very short neck, grey hoodie, black trousers, rounded cat-paw "
    "hands and bare cat-paw feet, no tail. The head sits naturally into the short neck and hoodie collar; no "
    "floating head or pasted-on seam."
    " Include exactly one supporting character, always in the established simple cartoon style: a smooth round "
    "head, exactly two small dot eyes, one short line mouth, no nose or detailed facial features, small white "
    "mitten hands without fingers, plain dark simple clothes built from a few flat shapes. Keep the supporting "
    "figure minimal, secondary, and consistent. Absolutely no realistic or detailed human rendering for the "
    "supporting character."
    " Both figures share the chosen direction's 2D illustrated language, but keep the supporting figure simpler. "
    "Apartment corridor, same closed door and wall lamp, readable depth, muted cool-neutral palette with a small "
    "warm lamp accent, medium two-shot at eye level, protagonist at frame left and supporting character at "
    "frame right, both visible from head to mid-thigh. No text, letters, numbers, logo, watermark, UI, extra "
    "people, photorealism, 3D rendering, photographic fur strands, plastic toy appearance, or extra limbs."
)

DIRECTIONS = {
    "01-cel-anime": (
        "Direction 1, crisp cel anime: clean confident dark grey-blue contour of one consistent weight, broad "
        "flat fur shapes, only a few intentional tabby strokes, simplified but recognizable facial planes, and "
        "two or three hard-edged cel-shadow shapes. Keep the eyes and facial proportions from the reference; "
        "no soft airbrush shading or individual fur strands."
    ),
    "02-inked-anime": (
        "Direction 2, hand-inked anime: elegant deliberate ink contours with slight hand-drawn character, "
        "controlled fine strokes limited to the face's tabby markings and whisker roots, broad clean color "
        "shapes, and restrained cel shadows. The result must still read as an animation illustration, not a "
        "realistic animal portrait or pencil study."
    ),
    "03-retro-graphic": (
        "Direction 3, retro graphic anime: stronger outer silhouette, clear inner contour accents, limited "
        "flat color groups, and tabby markings drawn as graphic patches. Keep the exact familiar cheek, ear, "
        "eye, muzzle and nose proportions; energetic graphic design without changing the cat's identity. No "
        "halftone noise, grain, or photographic fur."
    ),
    "04-painted-anime": (
        "Direction 4, gentle painted anime: broad controlled illustrated fur strokes and soft painted depth "
        "in the corridor, while keeping facial shapes, hoodie, and body clearly designed and non-photographic. "
        "Use restrained painterly color transitions only as clean drawn shapes; no grain, no paper texture, "
        "no individual realistic hairs. Give the clothes enough illustrated folds to harmonize with the face."
    ),
}

SCENES = {
    "A-standing": (
        "Scene A: both characters stand side by side beside the closed apartment door, calmly facing slightly "
        "toward the viewer. The protagonist's relaxed cat paws rest near the hoodie hem. The supporting "
        "character's two white mittens hang simply at the sides."
    ),
    "B-gesture": (
        "Scene B: same corridor, same door, same lighting, camera distance, and left-right staging. The "
        "protagonist turns his head slightly and listens. The round-headed supporting character makes one "
        "small readable white-mitten gesture toward the closed door. Keep both silhouettes and faces clear."
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


def generate(tag: str, prompt: str, key: str) -> dict:
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
    width, height, label, gap, columns = 420, 236, 35, 12, 4
    rows = (len(good) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * width + (columns + 1) * gap,
                                rows * (height + label) + (rows + 1) * gap), "white")
    draw = ImageDraw.Draw(canvas)
    for index, item in enumerate(good):
        x = gap + (index % columns) * (width + gap)
        y = gap + (index // columns) * (height + label + gap)
        with Image.open(item["file"]) as image:
            canvas.paste(image.convert("RGB").resize((width, height)), (x, y))
        draw.text((x + 5, y + height + 9), item["variant"], fill="black")
    canvas.save(OUT / "contact-sheet.jpg", quality=88)


def write_manifest(results: list[dict], reviewed: bool = False) -> None:
    prompts = {
        f"{direction}__{scene}": COMMON + " " + direction_text + " " + scene_text
        for direction, direction_text in DIRECTIONS.items()
        for scene, scene_text in SCENES.items()
    }
    acceptance = "Pending visual review"
    if reviewed:
        acceptance = {
            "contact_sheet_reviewed": True,
            "01-cel-anime": "Best at reducing the realistic-fur contrast while keeping the face recognizable; the face is still textured, but reads most clearly as an anime drawing.",
            "02-inked-anime": "Linework is deliberate and illustrated, but the face retains prominent fine fur rendering and still reads relatively realistic.",
            "03-retro-graphic": "The graphic contours and cheek patches help, but much of the fur surface still looks realistic; the style shift is subtler than requested.",
            "04-painted-anime": "The background and clothing are softer, but the face remains fur-detailed and more realistic than the body.",
            "support_character": "All eight panels show the specified simple round head, dot eyes, short line mouth, white mitten hands, and plain dark clothes; no realistic human side character appears.",
            "overall": "Direction 01 is the clearest anime option in this batch. Directions 02 to 04 retain more realistic fur and should be treated as exploratory comparisons, not as solved versions.",
        }
    data = {
        "purpose": "Anime-rendering style exploration for the life-experience cat protagonist, with the required simple cartoon supporting character",
        "channel": "new2",
        "model": MODEL,
        "endpoint": f"{BASE}/images/edits",
        "reference": str(REFERENCE.resolve()),
        "requested_dimensions": SIZE,
        "common_prompt": COMMON,
        "direction_prompts": DIRECTIONS,
        "scene_prompts": SCENES,
        "full_prompts_by_image": prompts,
        "results": results,
        "contact_sheet": str((OUT / "contact-sheet.jpg").resolve()),
        "acceptance": acceptance,
        "next_step": "User will manually choose which rendering direction to develop; no persistent style change is made in this test batch.",
    }
    (OUT / "manifest.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    if not REFERENCE.exists():
        raise SystemExit(f"Missing reference: {REFERENCE}")
    OUT.mkdir(parents=True, exist_ok=True)
    key = get_key()
    results: list[dict] = []
    for direction, direction_text in DIRECTIONS.items():
        for scene, scene_text in SCENES.items():
            tag = f"{direction}__{scene}"
            result = generate(tag, COMMON + " " + direction_text + " " + scene_text, key)
            results.append(result)
            write_manifest(results)
            print(json.dumps(result, ensure_ascii=False), flush=True)
            if not result.get("ok"):
                contact_sheet(results)
                return 1
    contact_sheet(results)
    write_manifest(results)
    return 0 if len(results) == 8 and all(item.get("ok") for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
