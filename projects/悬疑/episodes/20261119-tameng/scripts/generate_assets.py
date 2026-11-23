from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[3]
PLAN_PATH = EP / "storyboard" / "SHOT_PLAN-body-v2.json"
CONCEPT = ROOT / "projects" / "悬疑" / "visual-tests" / "20261119-creature-directions" / "07-dreadful-face-mouths.png"
HELPER_PATH = ROOT / "projects" / "悬疑" / "visual-tests" / "20261114-pilot-8shots" / "gen_pilot.py"

spec = importlib.util.spec_from_file_location("image_api", HELPER_PATH)
api = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = api
spec.loader.exec_module(api)
api.HERE = EP
api.RAW = EP / "image" / "raw" / "full-v1"
api.CROPS = EP / "image" / "crops"
api.ANCH = EP / "image" / "anchors"
api.TIMEOUT_S = 900
for folder in (api.RAW, api.CROPS, api.ANCH, EP / "image" / "pilot", EP / "image" / "final"):
    folder.mkdir(parents=True, exist_ok=True)

POLICY = json.loads((ROOT / "shared" / "image-api" / "channel-policy.json").read_text(encoding="utf-8"))
ROUTE_NAME = POLICY["active"]
CHANNELS = {}
for name in POLICY["policies"][ROUTE_NAME]["parallel_channels"]:
    CHANNELS[name] = dict(POLICY["channels"][name], name=name, policy=ROUTE_NAME)
POS, NEG, CEL = [api.read_block(key) for key in ("STYLE_POS", "STYLE_NEG", "CEL_BOOST")]
CHANNEL_LOCKS = {name: threading.Lock() for name in CHANNELS}

CHARACTERS = {
    "mother": {
        "id": "tameng-mother", "name": "母亲", "tier": "A",
        "desc": "one Chinese woman aged 42, adult medium build, shoulder-length straight black hair with a center part, long oval face, slightly tired dark eyes, straight brows, muted dark-red cardigan over a charcoal round-neck shirt, black straight trousers, plain dark house slippers, no jewelry, no glasses",
        "prompt": "Create one 2x2 character identity sheet with four equal panels and no borders. Top-left: full-body front view. Top-right: exact 90-degree side full-body view. Bottom-left: full-body back view. Bottom-right: close front face portrait. The exact same adult Chinese woman appears in every panel, identical face, hair, body, clothing and proportions. Neutral standing pose, plain cool-grey background. No text, numbers, labels, watermark or interface.",
        "anchor": "mother-2x2.png",
    },
    "husband": {
        "id": "tameng-husband", "name": "老陈", "tier": "B",
        "desc": "one Chinese man aged 44, average adult build, short straight black hair, broad oval face, calm dark eyes, medium brows, faint under-eye lines, dark navy casual jacket over a dark grey shirt, black trousers, no glasses, no jewelry",
        "prompt": "One full-body three-quarter front identity reference of the same Chinese man, neutral upright pose, plain cool-grey background, one person only, no text, no panels, no labels, no watermark.",
        "anchor": "husband-front-ref.png",
    },
    "officer1": {
        "id": "tameng-officer1", "name": "老周警员", "tier": "B",
        "desc": "one Chinese male police officer aged 50, sturdy broad-shouldered build, very short salt-and-pepper crew cut with visible grey at both temples, broad square lower face, heavy straight brows, deep-set dark eyes, distinct from the 44-year-old husband; plain dark navy Chinese police uniform with no readable insignia or text, black duty belt, black shoes",
        "prompt": "One full-body three-quarter front identity reference, neutral standing pose, plain cool-grey background, one person only. Design a face visibly distinct from the younger husband: broad heavier face, short salt-and-pepper crew cut, grey temples. No visible badges, no readable text, no panels, no watermark.",
        "anchor": "officer1-face-ref.png",
    },
    "creature": {
        "id": "tameng-creature", "name": "地下室爬行者", "tier": "A visual continuity asset",
        "desc": "a low crawling human-shaped entity, adult-sized but compressed close to the ground, soaked dark clothing swollen and adhering to its back, wet black hair and sludge, limbs bent at unnatural angles; its face has several uneven mouths in different sizes, and every extra mouth exists only on the face; ordinary eyes partly hidden by wet hair; no extra mouths on neck, arms, torso or elsewhere",
        "prompt": "An anatomy and continuity reference for one crawling entity in a worn Chinese apartment basement stairwell. Medium-wide 3/4 side view, its body low to the wet floor. The face alone has several uneven mouths of different sizes; no extra mouths anywhere beyond the face. Wet dark hair, black mud, swollen old clothing, wrong joint angles. The image is an anatomy reference only; do not copy reference image lighting, rendering style, color, background or composition. Use the established restrained cel-shaded story style. No blood, no exposed organs, no frontal hero portrait, no readable text.",
        "anchor": "creature-body.png",
        "reference": CONCEPT,
    },
}


def save_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def prompt_for(visual: str, cast: list[str], creature: bool = False) -> str:
    parts = [POS]
    if cast or creature:
        parts.append(CEL)
    if "mother" in cast:
        parts.append(CHARACTERS["mother"]["desc"] + "; preserve identity from attached character reference, same face, hair and clothing")
    if "husband" in cast:
        parts.append(CHARACTERS["husband"]["desc"] + "; preserve identity from attached character reference")
    if "officer1" in cast:
        parts.append(CHARACTERS["officer1"]["desc"] + "; preserve identity from attached character reference; sleeve tears only after the creature pulls it")
    if "creature" in cast or creature:
        parts.append(CHARACTERS["creature"]["desc"])
        parts.append("The story-required crawling entity is an intentional subject despite the generic negative-list term; medium or wide framing only, no jump-scare composition. Extra mouths only on the face.")
    parts += [
        "Camera: 24-28mm wide-angle, deep focus, off-center on a left or right third, ordinary observer viewpoint.",
        "Foreground: a door frame, table edge, stair rail, window frame or other concrete obstruction presses one edge; middle ground shows the action; background establishes the room, stair or entry.",
        visual,
        "Lighting: cold grey-blue night light and at most one restrained warm practical light. Worn, lived-in Chinese urban surfaces; use story-driven water stains, chipped paint, scuffed tile, old furniture or used household objects where visible. Preserve clean 2D cel rendering, not pristine physical condition.",
        "No readable text, numbers, labels, captions, watermark, logo, UI, gore, exposed organs, extra people or invented story events.",
        "Avoid: " + NEG,
    ]
    return "\n".join(parts)


def shot_prompt(row: dict) -> str:
    cast = row["cast"]
    return prompt_for(row["visual"], cast, "creature" in cast)


def choose_anchor(cast: list[str]) -> Path | None:
    for key in ("mother", "husband", "officer1", "creature"):
        if key in cast:
            anchor = {"mother": "mother-front.png"}.get(key, CHARACTERS[key]["anchor"])
            path = api.ANCH / anchor
            return path if path.exists() else None
    return None


def run_request(tag: str, prompt: str, channel_name: str, reference: Path | None = None,
                retries: int = 2, size_kind: str = "M") -> dict:
    primary = channel_name
    order = [primary, next(n for n in CHANNELS if n != primary)]
    attempts: list[dict] = []
    for route_idx, route_name in enumerate(order):
        if route_idx and not attempts:
            continue
        for attempt in range(1, retries + 1):
            row = {"tag": tag, "shot_type": size_kind, "character_ids": [], "evidence": ""}
            with CHANNEL_LOCKS[route_name]:
                info = api.call(CHANNELS[route_name], prompt, row, reference, attempt)
            if info.get("ok"):
                path = EP / info["file"]
                info["metrics"] = api.measure(path)
                info["qa"] = api.gate(info, CHANNELS[route_name])
            info["route_index"] = route_idx
            attempts.append(info)
            print(f"{tag} {route_name} a{attempt}: {'OK' if info.get('ok') else 'FAIL'} {info.get('elapsed_s', '-')}s {info.get('dims', '')} {info.get('qa', info.get('error', ''))}", flush=True)
            if info.get("ok") and not info.get("qa"):
                break
        passed = next((a for a in reversed(attempts) if a.get("ok") and not a.get("qa")), None)
        if passed:
            passed["fallback_from"] = primary if route_name != primary else ""
            passed["all_attempts"] = [{k: v for k, v in a.items() if k != "all_attempts"} for a in attempts]
            return passed
        if route_name == primary:
            continue
    result = attempts[-1] if attempts else {"ok": False, "error": "no attempts"}
    result["fallback_from"] = ""
    result["all_attempts"] = attempts
    return result


def generate_character(key: str, channel: str, attempt_ref: Path | None = None) -> dict:
    char = CHARACTERS[key]
    prompt = "\n".join([POS, CEL, char["prompt"], char["desc"], "Avoid: " + NEG])
    tag = "anchor-officer1-v2" if key == "officer1" else "anchor-" + key
    request = run_request(tag, prompt, channel, attempt_ref, size_kind="C")
    if not request.get("ok"):
        return request
    source = EP / request["file"]
    dest = api.ANCH / char["anchor"]
    if key == "mother":
        with Image.open(source) as im:
            im = im.convert("RGB")
            w, h = im.size
            gap = max(3, round(min(w / 2, h / 2) * 0.006))
            boxes = {
                "front": (gap, gap, w // 2 - gap, h // 2 - gap),
                "side": (w // 2 + gap, gap, w - gap, h // 2 - gap),
                "back": (gap, h // 2 + gap, w // 2 - gap, h - gap),
                "face": (w // 2 + gap, h // 2 + gap, w - gap, h - gap),
            }
            for name, box in boxes.items():
                im.crop(box).save(api.ANCH / f"mother-{name}.png")
            im.save(dest)
    else:
        shutil.copyfile(source, dest)
    request["anchor_file"] = str(dest.relative_to(EP))
    request["anchor_sha256"] = hashlib.sha256(dest.read_bytes()).hexdigest()
    save_json(EP / "logs" / ("anchor-officer1-v2.json" if key == "officer1" else f"anchor-{key}.json"), request)
    return request


def anchors() -> int:
    # Round-robin requests honor the active image channel policy.
    order = [("mother", "new2", None), ("husband", "dkl-b", None),
             ("officer1", "new2", None), ("creature", "dkl-b", CONCEPT)]
    results = []
    for key, channel, reference in order:
        result = generate_character(key, channel, reference)
        results.append({"character": key, "result": result})
        if not result.get("ok"):
            save_json(EP / "logs" / "anchor-generation.json", results)
            return 1
    save_json(EP / "logs" / "anchor-generation.json", results)
    print("ANCHORS_COMPLETE", flush=True)
    return 0


def sample_rows() -> list[dict]:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    lookup = {row["id"]: row for row in plan["shots"]}
    return [plan["shots"][i] for i in (0, 1, 2, 4, 12, 18)]


def sample() -> int:
    results = []
    for row in sample_rows():
        anchor = choose_anchor(row["cast"])
        reference = anchor
        if "creature" in row["cast"]:
            reference = api.ANCH / CHARACTERS["creature"]["anchor"]
        info = run_request(row["id"], shot_prompt(row), "dkl-b", reference,
                           size_kind=row["shot_type"])
        results.append({"shot": row["id"], "result": info})
        if info.get("ok"):
            source = EP / info["file"]
            shutil.copyfile(source, EP / "image" / "pilot" / f"{row['id']}.png")
        else:
            save_json(EP / "logs" / "style-samples.json", results)
            return 1
    save_json(EP / "logs" / "style-samples.json", results)
    print("SIX_STYLE_SAMPLES_COMPLETE", flush=True)
    return 0


def batch() -> int:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    existing = {int(p.stem[1:]) for p in (EP / "image" / "final").glob("S*.png") if p.stem[1:].isdigit()}
    todo = [s for s in plan["shots"] if int(s["id"][1:]) not in existing]
    queue = []
    for idx, row in enumerate(todo):
        queue.append((row, "new2" if idx % 2 == 0 else "dkl-b"))
    results = []

    def work(item):
        row, channel = item
        reference = choose_anchor(row["cast"])
        info = run_request(row["id"], shot_prompt(row), channel, reference, size_kind=row["shot_type"])
        if info.get("ok"):
            raw = EP / info["file"]
            shutil.copyfile(raw, EP / "image" / "final" / f"{row['id']}.png")
        return {"shot": row["id"], "assigned": channel, "result": info}

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(work, item) for item in queue]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            save_json(EP / "logs" / "image-batch-progress.json", results)
            print("BATCH", result["shot"], "DONE" if result["result"].get("ok") else "FAILED", flush=True)
    save_json(EP / "logs" / "image-batch.json", sorted(results, key=lambda x: x["shot"]))
    complete = all((EP / "image" / "final" / f"{s['id']}.png").exists() for s in plan["shots"])
    print("BATCH_COMPLETE" if complete else "BATCH_INCOMPLETE", flush=True)
    return 0 if complete else 1


def main() -> int:
    mode = sys.argv[1]
    if mode == "anchors":
        return anchors()
    if mode == "sample":
        return sample()
    if mode == "batch":
        return batch()
    if mode == "regen-officer":
        result = generate_character("officer1", "new2")
        save_json(EP / "logs" / "anchor-officer1-v2.json", result)
        return 0 if result.get("ok") else 1
    raise SystemExit("usage: generate_assets.py anchors|regen-officer|sample|batch")


if __name__ == "__main__":
    raise SystemExit(main())
