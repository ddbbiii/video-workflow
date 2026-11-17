from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
import shutil
import time
import urllib.error
import urllib.request
import uuid
import winreg
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
EXPR_DIR = OUT / "expressions"
V8 = ROOT / "assets" / "人生体验" / "characters" / "catman-20261113" / "reference-v8"
FACE_PHOTO = ROOT / "assets" / "人生体验" / "characters" / "catman-20261113" / "reference-v8" / "ref-face.png"
D_FACE = ROOT / "assets" / "人生体验" / "characters" / "catman-20261113" / "character-reference" / "face-style-D.png"
BASE = os.environ.get("IMAGE_API_BASE_URL_XXC", "https://xxcapi.com/v1").rstrip("/")
MODEL = "AZ-gpt-image-2"
SIZE = "1536x1024"
UA = "OpenAI/Python 1.60.0"

TURN_PROMPT = (
    "The uploaded reference board has five labeled panels. Use panels A, B and C ONLY for the already "
    "approved body turn views and their exact view directions/body proportions. Use panel D ONLY for the "
    "selected D graphic-flat anime rendering language. Use panel E ONLY for the exact real-cat coat colors "
    "and tabby marking map. Create a genuinely newly redrawn three-view turnaround, not a pasted or "
    "assembled copy: exactly three equal vertical panels, left-to-right FRONT, pure LEFT-FACING SIDE, BACK. "
    "Full body in every panel, identical scale and stance, feet visible. Same compact upright human body of "
    "about 3 to 3.2 head-heights, extremely short neck, narrow shoulders, grey hoodie, black trousers, rounded "
    "cat-paw hands, bare cat-paw feet, no shoes, no tail. D style: bold clean dark grey-blue outer contour, "
    "broad flat color regions, a few crisp controlled shadow shapes; no photographic fur, no soft photo shading. "
    "Identity is critical: same broad round orange-and-cream Scottish Fold head, same folded ears, same eye "
    "spacing and size, same pink nose and short muzzle. Preserve the coat map from panel E exactly in every "
    "view: pale cream-orange base, same cream blaze and forehead M, same orange cheek bands in the same places, "
    "same cream muzzle and chest bib. Do not change hue, saturation, stripe count, stripe direction, stripe "
    "width, marking positions or white/cream areas. In side view, render a plausible left-facing profile of this "
    "same cat; in back view show the same orange/cream coat and folded ears from behind. Plain white background. "
    "No text, labels, panel borders, collage look, extra characters, extra limbs, human fingers, socks, shoes, "
    "or altered markings."
)

NEW_EXPRESSIONS = [
    ("joyful-laugh", "Joyful laugh: eyes curve into happy crescents but retain the same eye placement; mouth opens in a clear cheerful laugh with a small visible dark mouth interior, no teeth, no tongue, no changed muzzle."),
    ("sad-tears", "Sad with tears: upper eyelids lift slightly, pupils look down, two small clean tear shapes sit below the eyes, mouth corners turn down clearly; do not alter face outline or markings."),
    ("surprised", "Surprised: eyes open wider without changing their size or spacing, pupils centered, mouth opens into a small round shape; no giant eyes and no face deformation."),
    ("fear-panic", "Fear/panic: eyelids raised, pupils slightly contracted, gaze fixed forward, mouth open in a tense small gasp; dramatic but controlled, no screaming distortion."),
    ("intense-anger", "Intense anger: eyelids lower strongly, pupils fixed in a sharp direct gaze, mouth opens in a firm angry call with visible dark mouth interior but no teeth; keep head and muzzle geometry unchanged."),
    ("disgust", "Disgust: one eyelid lowers more than the other, gaze shifts sideways, mouth tightens with a slight asymmetric curl; clearly displeased but do not warp cheeks or nose."),
    ("deep-grief", "Deep grief: eyelids press closed, two bold but simple tear streams on the cream cheek areas, mouth opens in a sorrowful cry; preserve all fur colors and stripe marks beneath/around tears."),
    ("exhausted", "Exhaustion: eyelids nearly closed, pupils low, mouth slightly open as if breathing out, expression visibly drained; no change to cheek silhouette, fur colors or tabby map."),
]

IDENTITY_LOCK = (
    "Edit the supplied D-style face image directly. Preserve its exact face outline, head proportions, folded ears, "
    "eye placement and spacing, nose, muzzle, whiskers, cream/orange colors, forehead blaze/M, and every stripe's "
    "count, location, direction, width and color. Preserve the D graphic-flat line weight, crop, white background "
    "and composition. Change only eyelids, gaze/pupils, mouth expression, and the specifically requested emotion "
    "marks such as tears. Do not redesign, slim, enlarge eyes, move markings, recolor fur, add extra stripes, "
    "photorealize, or add objects/text."
)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def get_key() -> str:
    value = os.environ.get("IMAGE_API_KEY_XXC", "").strip()
    if value:
        return value
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, "IMAGE_API_KEY_XXC")[0]


def ref_board() -> Path:
    path = OUT / "turnaround-reference-board.png"
    sources = [
        ("A - APPROVED FRONT VIEW", V8 / "turnaround-v8-front.png"),
        ("B - APPROVED LEFT PROFILE", V8 / "turnaround-v8-side.png"),
        ("C - APPROVED BACK VIEW", V8 / "turnaround-v8-back.png"),
        ("D - SELECTED GRAPHIC-FLAT STYLE", D_FACE),
        ("E - ORIGINAL COAT COLOR / MARK MAP", FACE_PHOTO),
    ]
    cell_w, cell_h, title_h = 400, 700, 58
    canvas = Image.new("RGB", (cell_w * len(sources), cell_h + title_h), "white")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for index, (label, source) in enumerate(sources):
        with Image.open(source) as image:
            image = image.convert("RGB")
            image.thumbnail((cell_w - 24, cell_h - 24))
            x = index * cell_w + (cell_w - image.width) // 2
            y = title_h + (cell_h - image.height) // 2
            canvas.paste(image, (x, y))
        draw.text((index * cell_w + 10, 16), label, fill="#17232a", font=font)
    canvas.save(path)
    return path


def multipart(fields: dict[str, str], image_path: Path) -> tuple[bytes, str]:
    boundary = "----codex" + uuid.uuid4().hex
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    ctype = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    chunks.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{image_path.name}\"\r\n"
        f"Content-Type: {ctype}\r\n\r\n".encode()
    )
    chunks.extend((image_path.read_bytes(), b"\r\n", f"--{boundary}--\r\n".encode()))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def call_edit(image_path: Path, prompt: str, out_path: Path) -> dict:
    body, ctype = multipart({"model": MODEL, "prompt": prompt, "size": SIZE, "n": "1"}, image_path)
    request = urllib.request.Request(
        f"{BASE}/images/edits", data=body, method="POST",
        headers={"Authorization": f"Bearer {get_key()}", "Content-Type": ctype,
                 "Accept": "application/json", "User-Agent": UA},
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=900) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as error:
        status, raw = error.code, error.read()
    result: dict = {"status": status, "elapsed_s": round(time.time() - started, 1), "prompt": prompt}
    if status != 200:
        result.update({"ok": False, "error": raw[:500].decode("utf-8", "replace")})
        return result
    item = (json.loads(raw.decode("utf-8")).get("data") or [{}])[0]
    if item.get("b64_json"):
        out_path.write_bytes(base64.b64decode(item["b64_json"]))
        result["delivery"] = "b64_json"
    elif item.get("url"):
        download = urllib.request.Request(item["url"], headers={"User-Agent": UA})
        with urllib.request.urlopen(download, timeout=300) as response:
            out_path.write_bytes(response.read())
        result["delivery"] = "url"
    else:
        result.update({"ok": False, "error": "No b64_json or url"})
        return result
    with Image.open(out_path) as image:
        image.load()
        result.update({"ok": True, "file": str(out_path.resolve()), "dimensions": list(image.size),
                       "bytes": out_path.stat().st_size, "sha256": sha(out_path)})
    return result


def copy_first_16() -> list[dict]:
    src_m = json.loads((OLD_V9 / "manifest.json").read_text(encoding="utf-8"))
    results = []
    for item in src_m["expressions"]["results"]:
        dest = EXPR_DIR / ("neutral.png" if item["expression"] == "neutral" else f"{item['expression']}.png")
        source = Path(item["file"])
        shutil.copy2(source, dest)
        with Image.open(dest) as image:
            dims = list(image.size)
        results.append({"expression": item["expression"], "source": str(source.resolve()), "file": str(dest.resolve()),
                        "dimensions": dims, "bytes": dest.stat().st_size, "sha256": sha(dest), "ok": True,
                        "copied_unchanged": True})
    return results


def compose_sheet(results: list[dict]) -> Path:
    labels = [item["expression"] for item in results]
    columns = 5
    rows = 5
    thumb_w, thumb_h, label_h, gap = 340, 227, 38, 18
    canvas = Image.new("RGB", (columns * thumb_w + (columns + 1) * gap,
                                rows * (thumb_h + label_h) + (rows + 1) * gap), "white")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for index, item in enumerate(results):
        x = gap + (index % columns) * (thumb_w + gap)
        y = gap + (index // columns) * (thumb_h + label_h + gap)
        with Image.open(item["file"]) as image:
            image = image.convert("RGB")
            image.thumbnail((thumb_w, thumb_h))
            canvas.paste(image, (x + (thumb_w - image.width) // 2, y + (thumb_h - image.height) // 2))
        draw.text((x + 4, y + thumb_h + 9), f"{index + 1:02d} {labels[index]}", fill="#17232a", font=font)
    path = OUT / "expressions-24-contact.jpg"
    canvas.save(path, quality=88)
    return path


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    EXPR_DIR.mkdir(parents=True, exist_ok=True)
    board = ref_board()
    key = get_key()
    errors: list[str] = []
    turn_path = OUT / "turnaround-d-redrawn.png"
    turn_result = call_edit(board, TURN_PROMPT, turn_path)
    print(json.dumps({"kind": "turnaround", "ok": turn_result.get("ok"), "file": turn_result.get("file"),
                      "dimensions": turn_result.get("dimensions")}, ensure_ascii=False), flush=True)
    if not turn_result.get("ok"):
        errors.append(str(turn_result.get("error")))

    expression_results = copy_first_16()
    for name, detail in NEW_EXPRESSIONS:
        prompt = IDENTITY_LOCK + " Expression: " + detail
        path = EXPR_DIR / f"{name}.png"
        result = call_edit(D_FACE, prompt, path)
        result["expression"] = name
        expression_results.append(result)
        print(json.dumps({"kind": "expression", "expression": name, "ok": result.get("ok"),
                          "dimensions": result.get("dimensions")}, ensure_ascii=False), flush=True)
        if not result.get("ok"):
            errors.append(f"{name}: {result.get('error')}")
            break
    if len(expression_results) == 24:
        contact = compose_sheet(expression_results)
    else:
        contact = None
    manifest = {
        "purpose": "Redrawn D-style three-view candidate plus 24-expression comparison sheet",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "channel": "new2",
        "model": MODEL,
        "endpoint": f"{BASE}/images/edits",
        "requested_dimensions": SIZE,
        "reference_board": str(board.resolve()),
        "turnaround": {
            "reference_sources": {
                "approved_v8_front": str((V8 / "turnaround-v8-front.png").resolve()),
                "approved_v8_side": str((V8 / "turnaround-v8-side.png").resolve()),
                "approved_v8_back": str((V8 / "turnaround-v8-back.png").resolve()),
                "D_style_face": str(D_FACE.resolve()),
                "original_face_identity": str(FACE_PHOTO.resolve()),
            },
            "prompt": TURN_PROMPT,
            "result": turn_result,
            "acceptance": "Pending strict visual review of coat hue, stripe count/placement, and face geometry. This is a redraw candidate; do not promote without user approval.",
        },
        "expressions": {
            "base": str(D_FACE.resolve()),
            "count": len(expression_results),
            "existing_16_copied_without_modification": True,
            "new_variants": NEW_EXPRESSIONS,
            "identity_lock_prompt": IDENTITY_LOCK,
            "results": expression_results,
            "contact_sheet": str(contact.resolve()) if contact else None,
            "acceptance": "Pending low-resolution contact-sheet review; raw expression images are not resized.",
        },
        "errors": errors,
        "next_step": "User reviews the D-style redraw and expanded emotional range; do not change production references until approval.",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if turn_result.get("ok") and len(expression_results) == 24 and not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
