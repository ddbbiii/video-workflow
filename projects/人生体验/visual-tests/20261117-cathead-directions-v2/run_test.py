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
REFERENCE = ROOT / "assets" / "人生体验" / "characters" / "catman-20261113" / "reference-v8" / "ref-face.png"
BASE = os.environ.get("IMAGE_API_BASE_URL_XXC", "https://xxcapi.com/v1").rstrip("/")
MODEL = "AZ-gpt-image-2"
SIZE = "1672x941"
UA = "OpenAI/Python 1.60.0"

COMMON = (
    "Create a polished hand-drawn 2D story illustration in a horizontal 16:9 frame. Use Image 1 only to "
    "preserve the protagonist's identity. Show exactly two characters in the same quiet apartment corridor: "
    "the protagonist and the same supporting character. The protagonist is the same orange Scottish Fold "
    "cat-headed person, retaining the reference's compact round head, full cheeks, short muzzle, folded ears, "
    "large round dark eyes with a narrow amber rim, pink nose, cream muzzle, white whiskers, forehead M and "
    "orange tabby markings. He has a compact upright human body around 3 to 3.2 head-heights, very short neck, "
    "grey hoodie, black trousers, rounded cat-paw hands and bare cat-paw feet, no tail. The head, neck and "
    "hoodie collar must look intentionally connected, with the hood/collar supporting the base of the head; "
    "no floating head or pasted-on seam."
    " The supporting character MUST be a very simple round-headed cartoon person, matching the established "
    "side-character design: one smooth round pale head, exactly two tiny dot eyes, one short simple line mouth, "
    "no detailed facial features; small white mitten/glove hands with no fingers; plain dark simple clothes "
    "made from a few flat shapes. Use a compact simple silhouette and the same dark grey-blue outline weight "
    "as the protagonist. Keep this figure deliberately minimal and secondary. Do not render the supporting "
    "character as an ordinary detailed human, portrait, realistic person, anime character or 3D figure; no "
    "hair strands, eyebrows, nose, detailed ears, skin texture, fingers or detailed anatomy."
    " Both characters share clean 2D linework, restrained flat fills and hard-edged shadows. The apartment "
    "corridor has a clear doorway, wall lamp and quiet depth; cool-neutral muted palette with one warm lamp "
    "accent. No text, letters, numbers, logos, UI, watermark, extra people, photorealism, 3D rendering, "
    "plastic toy appearance, extra limbs or human fingers on the protagonist."
)

DIRECTIONS = {
    "01-balanced": (
        "Direction 1, balanced face treatment: preserve all recognizable face features and their proportions, "
        "but use a middle level of facial detail. Keep the cheek shape, eye spacing, folded ears, muzzle, pink "
        "nose and tabby pattern. Reduce only the finest fur strands to a few controlled illustrated strokes. "
        "Use one coherent outline and light direction across head and body; let the hood and collar cradle the "
        "short neck naturally."
    ),
    "02-proportion": (
        "Direction 2, proportion bridge: preserve the face identity and markings in full, but make the head "
        "slightly smaller relative to the torso and make the shoulders modestly broader, while keeping the "
        "overall compact 3-to-3.2-head-height character proportion. Maintain the very short neck and have the "
        "hoodie collar support the head naturally. Do not shrink or redesign facial features."
    ),
    "03-collar-body": (
        "Direction 3, collar and body bridge: keep the reference face details and current head scale. Connect "
        "the white chest bib visually to the pale hood opening and collar so the transition looks designed "
        "without turning the body into fur. Give the hoodie and sleeves a little more hand-drawn fold and "
        "tonal detail to meet the face halfway; keep them clearly 2D, restrained, and less detailed than the "
        "face."
    ),
}

SCENES = {
    "A-standing": (
        "Scene A: medium two-shot, eye-level three-quarter view. Both characters stand beside the same closed "
        "apartment door, side by side with a little space between them. The protagonist stands at frame left; "
        "the simple round-headed supporting character stands at frame right. Both look calmly toward the "
        "viewer, neutral posture, both figures visible from head to mid-thigh."
    ),
    "B-gesture": (
        "Scene B: the same medium two-shot, eye-level three-quarter view, same apartment corridor, same door, "
        "same lighting and left-right staging. The protagonist stands at frame left and listens with a slight "
        "head turn. The same simple round-headed supporting character at frame right makes one small white-mitten "
        "hand gesture toward the closed doorway. Both figures are visible from head to mid-thigh; keep the "
        "gesture simple and readable."
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


def make_manifest(results: list[dict]) -> dict:
    prompts = {
        f"{direction}__{scene}": COMMON + " " + direction_text + " " + scene_text
        for direction, direction_text in DIRECTIONS.items()
        for scene, scene_text in SCENES.items()
    }
    return {
        "purpose": "Six-image comparison of cat-head integration directions, with required simple round-headed supporting character",
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
        "acceptance": "Pending visual review",
        "next_step": "Compare the three protagonist treatments while checking that every supporting character follows the simple round-headed cartoon design.",
    }


def write_manifest(results: list[dict]) -> None:
    (OUT / "manifest.json").write_text(
        json.dumps(make_manifest(results), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def generate(tag: str, prompt: str, key: str) -> dict:
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


def write_contact_sheet(results: list[dict]) -> None:
    good = [item for item in results if item.get("ok") and Path(item["file"]).exists()]
    if not good:
        return
    thumb_w, thumb_h, label_h, gap = 560, 315, 42, 14
    cols = 2
    rows = (len(good) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * thumb_w + (cols + 1) * gap, rows * (thumb_h + label_h) + (rows + 1) * gap), "white")
    draw = ImageDraw.Draw(canvas)
    for index, item in enumerate(good):
        x = gap + (index % cols) * (thumb_w + gap)
        y = gap + (index // cols) * (thumb_h + label_h + gap)
        with Image.open(item["file"]) as image:
            canvas.paste(image.convert("RGB").resize((thumb_w, thumb_h)), (x, y))
        draw.text((x + 6, y + thumb_h + 12), item["variant"], fill="black")
    canvas.save(OUT / "contact-sheet.jpg", quality=88)


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
                write_contact_sheet(results)
                return 1
    write_contact_sheet(results)
    manifest = make_manifest(results)
    manifest["acceptance"] = {
        item["variant"]: "Pending visual comparison"
        for item in results
    }
    manifest["next_step"] = "Review the contact sheet and record whether the specified supporting-character style is consistent in all six images."
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if len(results) == 6 and all(item.get("ok") for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
