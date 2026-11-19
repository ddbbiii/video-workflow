from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[3]
GENERATOR = ROOT / "projects/悬疑/visual-tests/20261114-pilot-8shots/gen_pilot.py"
spec = importlib.util.spec_from_file_location("suspense_image_api", GENERATOR)
api = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = api
spec.loader.exec_module(api)
api.HERE = EP
api.RAW = EP / "image/raw"
api.CROPS = EP / "image/crops"
api.ANCH = EP / "image/references"
api.RULES = ROOT / "rules/悬疑/visual.md"

for folder in (api.RAW, api.CROPS, api.ANCH, EP / "image/anchors", EP / "image/backgrounds", EP / "image/final", EP / "logs"):
    folder.mkdir(parents=True, exist_ok=True)

POLICY = json.loads((ROOT / "shared/image-api/channel-policy.json").read_text(encoding="utf-8"))
ROUTE = POLICY["policies"][POLICY["active"]]
CHANNELS = [dict(POLICY["channels"][name], name=name, policy=POLICY["active"]) for name in ROUTE["parallel_channels"]]
# The active episode already recorded repeated HTTP 502 responses from new2, so this run drains only to dkl-b.
UNAVAILABLE = {"new2"}
AVAILABLE = [channel for channel in CHANNELS if channel["name"] not in UNAVAILABLE]
LOCKS = {channel["name"]: threading.Lock() for channel in AVAILABLE}
MANIFEST_PATH = EP / "image/manifest.json"
OVERRIDES_PATH = EP / "image/qa-overrides.json"
MANIFEST_LOCK = threading.Lock()
PLAN = json.loads((EP / "storyboard/SHOT_PLAN-v1.json").read_text(encoding="utf-8"))
POS, NEG, CEL = [api.read_block(name) for name in ("STYLE_POS", "STYLE_NEG", "CEL_BOOST")]
CHARACTER_PROMPTS = {
    "zhouning": "one Chinese woman aged 28, lean average adult build, straight shoulder-length black hair with a center part, long oval face, narrow dark eyes, straight brows, muted dark-red home cardigan over charcoal knit top, black trousers, plain black cloth shoes, no jewelry, no glasses, no distinctive marks",
    "chenyi": "one Chinese woman aged 29, average adult build, black hair tied in a low ponytail with a few side-parted wisps, round face, dark eyes, gently curved brow tails, ivory knit sweater, dark-green home trousers, light-grey slippers, no jewelry, no glasses, no distinctive marks",
}

def load_manifest():
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {}

def save_manifest(tag, record):
    with MANIFEST_LOCK:
        manifest = load_manifest()
        manifest[tag] = record
        MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

def save_call_log(tag, info, channel, attempt):
    info.update(model=channel["model"], base_url=channel["base_url"], request_id=info.get("request_id", "not-returned-by-relay"))
    path = EP / "logs" / f"{tag}-{channel['name']}-a{attempt}-meta.json"
    path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

def apply_visual_override(tag, info):
    if not OVERRIDES_PATH.exists():
        return False
    override = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8")).get(tag)
    if not override or info.get("qa") != override.get("failed_gate"):
        return False
    if hashlib.sha256((EP / info["file"]).read_bytes()).hexdigest() != override.get("sha256"):
        raise RuntimeError(f"{tag}: QA override hash does not match the inspected candidate")
    info["qa_override"] = {"reason": override["decision"], "approved_at": override["approved_at"], "basis": override["basis"], "original_gate": info["qa"]}
    info["qa"] = []
    info["ok"] = True
    save_manifest(tag, info)
    return True

def generate(tag, prompt, reference=None, index=0):
    prior = load_manifest().get(tag)
    if prior and prior.get("ok") and prior.get("file") and (EP / prior["file"]).exists():
        return EP / prior["file"]
    channel = AVAILABLE[index % len(AVAILABLE)]
    attempts = []
    cached = EP / "image/raw" / f"{tag}.png"
    if cached.exists():
        with Image.open(cached) as image:
            info = {"ok": True, "file": str(cached.relative_to(EP)), "dims": list(image.size), "channel": channel["name"]}
        info["metrics"] = api.measure(cached)
        info["qa"] = api.gate(info, channel)
        if not info["qa"]:
            save_manifest(tag, info)
            return cached
        if apply_visual_override(tag, info):
            return cached
    for attempt in range(1, 3):
        with LOCKS[channel["name"]]:
            info = api.call(channel, prompt, {"tag": tag}, reference, attempt)
        if info.get("ok"):
            raw = EP / info["file"]
            info["metrics"] = api.measure(raw)
            info["qa"] = api.gate(info, channel)
            if not info["qa"]:
                target = EP / "image/raw" / f"{tag}.png"
                if raw != target:
                    shutil.copyfile(raw, target)
                info["file"] = str(target.relative_to(EP))
                info["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
                info["attempt_log"] = attempts + [{k: info.get(k) for k in ("attempt", "http_status", "elapsed_s", "dims", "qa")}]
                info.update({"ok": True, "channel_policy": POLICY["active"], "disabled_channel": "new2 (repeated HTTP 502 in active episode)"})
                save_call_log(tag, info, channel, attempt)
                save_manifest(tag, info)
                print(tag, "OK", channel["name"], info.get("dims"), info.get("elapsed_s"), flush=True)
                return target
        attempts.append({k: info.get(k) for k in ("attempt", "http_status", "elapsed_s", "error", "dims", "qa")})
        save_call_log(tag, info, channel, attempt)
        print(tag, "FAIL", channel["name"], info.get("http_status"), info.get("error", info.get("qa")), flush=True)
        if info.get("http_status") in (401, 403):
            break
    save_manifest(tag, {"ok": False, "channel": channel["name"], "attempt_log": attempts})
    raise RuntimeError(f"{tag} exhausted retries; inspect {MANIFEST_PATH}")

def anchor_prompt(name, four_view):
    desc = CHARACTER_PROMPTS[name]
    layout = (
        "2x2 character turnaround sheet, four equal panels, one identical character in every panel, same scale and outfit. "
        "Top-left full body front standing, top-right full body exact 90-degree side standing, bottom-left full body back, "
        "bottom-right front-facing head-and-shoulders portrait, neutral pose, plain cool grey background, no frame lines. "
        if four_view else "Single full-body three-quarter front character reference, neutral standing pose, plain cool grey background. "
    )
    return "\n".join((POS, CEL, layout + "Character: " + desc + ". Flat grey background and exact same design throughout. No text, labels, numbers, border, UI or watermark.", "Avoid: " + NEG))

def make_anchors():
    main = generate("anchor-zhouning", anchor_prompt("zhouning", True), index=0)
    anchor_dir = EP / "image/anchors"
    target = anchor_dir / "zhouning-three-view.png"
    shutil.copyfile(main, target)
    with Image.open(target) as sheet:
        w, h = sheet.size
        for name, box in {
            "front": (4, 4, w // 2 - 4, h // 2 - 4),
            "side": (w // 2 + 4, 4, w - 4, h // 2 - 4),
            "back": (4, h // 2 + 4, w // 2 - 4, h - 4),
            "face": (w // 2 + 4, h // 2 + 4, w - 4, h - 4),
        }.items():
            sheet.crop(box).save(anchor_dir / f"zhouning-{name}.png")
    chen = generate("anchor-chenyi", anchor_prompt("chenyi", False), index=0)
    turnaround = anchor_dir / "chenyi-turnaround-generated.png"
    shutil.copyfile(chen, turnaround)
    with Image.open(turnaround) as sheet:
        w, h = sheet.size
        sheet.crop((0, 0, w // 3, h)).save(anchor_dir / "chenyi-front.png")
    contact([target, anchor_dir / "chenyi-front.png"], EP / "qa/character-anchors.jpg", 2)

def contact(paths, output, cols=4):
    width, height, label_h = 640, 360, 30
    canvas = Image.new("RGB", (cols * width, ((len(paths) + cols - 1) // cols) * (height + label_h)), (20, 23, 27))
    draw = ImageDraw.Draw(canvas)
    for i, path in enumerate(paths):
        im = Image.open(path).convert("RGB")
        im = ImageOps.fit(im, (width, height), method=Image.Resampling.LANCZOS)
        x, y = (i % cols) * width, (i // cols) * (height + label_h)
        draw.text((x + 8, y + 7), path.stem, fill=(240, 240, 240))
        canvas.paste(im, (x, y + label_h))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, quality=92)

def scene_plate(scene_id, index):
    out = EP / "image/backgrounds" / f"{scene_id}.png"
    if out.exists():
        return out
    prompt = "\n".join((POS, "Empty environment master, no people, no faces, no figures or reflections. " + PLAN["scenes"][scene_id], "Keep 16:9 deep-focus composition, readable wear and ordinary household use. No text, letters, numbers, signs, labels, UI, logos or watermarks.", "Avoid: " + NEG))
    image = generate("plate-" + scene_id, prompt, index=index)
    shutil.copyfile(image, out)
    return out

def make_reference(shot, plate):
    names = ["zhouning" if x.startswith("zhouning-") else "chenyi" for x in shot["character_ids"]]
    refs = []
    for name in dict.fromkeys(names):
        if name == "zhouning":
            refs.extend([EP / "image/anchors/zhouning-front.png", EP / "image/anchors/zhouning-face.png"])
        elif name == "chenyi":
            refs.append(EP / "image/anchors/chenyi-front.png")
    canvas = Image.new("RGB", (2560, 1440), (92, 94, 98))
    base = ImageOps.contain(Image.open(plate).convert("RGB"), (1920, 1080))
    canvas.paste(base, ((1920 - base.width) // 2, (1080 - base.height) // 2))
    cell_h = 1440 // max(1, len(refs))
    for i, ref in enumerate(refs):
        im = ImageOps.contain(Image.open(ref).convert("RGB"), (640, cell_h))
        canvas.paste(im, (1920 + (640 - im.width) // 2, i * cell_h + (cell_h - im.height) // 2))
    out = EP / "image/references" / f"{shot['id']}.png"
    canvas.save(out)
    return out

def render_shot(shot, index):
    target = EP / "image/final" / f"{shot['id']}.png"
    prior = load_manifest().get(shot["id"])
    if prior and prior.get("ok") and target.exists():
        return target
    plate = scene_plate(shot["scene_id"], index)
    has_char = bool(shot["character_ids"])
    reference = make_reference(shot, plate) if has_char else plate
    prefix = ""
    if has_char:
        prefix = (
            "LEFT large region is the environment master; RIGHT reference strip is identity-only. Output ONE complete "
            "single image of the described scene; do not copy the strip, panels, or reference poses. Keep exact face, hair, "
            "body and outfit from the references. "
        )
    else:
        prefix = "Use the attached empty environment master for exact location and prop continuity. Output one complete scene. "
    prompt_parts = [POS]
    if shot["shot_type"] == "C" or has_char:
        prompt_parts.append(CEL)
    prompt_parts.extend((prefix, shot["visual"], "Keep the same worn set and camera-readable evidence. No readable text, letters, numbers, symbols, platform logos, UI, subtitles or watermark.", "Avoid: " + NEG))
    prompt = "\n".join(prompt_parts)
    image = generate(shot["id"], prompt, reference, index)
    shutil.copyfile(image, target)
    record = load_manifest()[shot["id"]]
    record.update({k: shot[k] for k in ("fact", "character_ids", "evidence_id", "scene_id", "cast", "shot_type")})
    record["file"] = str(target.relative_to(EP))
    save_manifest(shot["id"], record)
    return target

def repair_shot(shot_id):
    shot = next(s for s in PLAN["shots"] if s["id"] == shot_id)
    target = EP / "image/final" / f"{shot_id}.png"
    rejected = EP / "image/rejected" / f"{shot_id}-r1.png"
    rejected.parent.mkdir(parents=True, exist_ok=True)
    old_hash = hashlib.sha256(target.read_bytes()).hexdigest()
    shutil.copyfile(target, rejected)
    old_record = load_manifest().get(shot_id, {})
    save_manifest(shot_id + "-r1", {**old_record, "file": str(rejected.relative_to(EP)), "rejected_for": "identity drift: left actor rendered male instead of Chen Yi"})
    plate = scene_plate(shot["scene_id"], 0)
    reference = make_reference(shot, plate)
    identity = (
        "Exactly two adult Chinese women, and no men. Identity mapping in the attached reference strip: its top full-body "
        "view and middle face view are the SAME Zhou Ning, a woman with shoulder-length center-parted black hair, long oval "
        "face, dark-red cardigan and charcoal knit top; its bottom full-body view is Chen Yi, a woman with a low black ponytail, "
        "round face, ivory knit sweater and dark-green trousers. In the output, Chen Yi sits on the LEFT in ivory and Zhou Ning "
        "sits on the RIGHT in dark red. Do not swap outfits, gender, faces or hairstyles; do not invent a third person. "
    )
    prompt = "\n".join((POS, CEL,
        "LEFT large region is the exact empty living-room master; RIGHT identity strip has Zhou Ning in the top two cells and Chen Yi in the bottom cell. Output one full-frame scene, no reference strip or panels. " + identity,
        shot["visual"],
        "Keep exact face, hair, body and outfit from the matching references. No readable text, letters, numbers, symbols, platform logos, UI, subtitles or watermark.",
        "Avoid: " + NEG))
    image = generate(shot_id + "-r2", prompt, reference, 0)
    new_hash = hashlib.sha256(image.read_bytes()).hexdigest()
    shutil.copyfile(image, target)
    record = load_manifest()[shot_id + "-r2"]
    record.update({k: shot[k] for k in ("fact", "character_ids", "evidence_id", "scene_id", "cast", "shot_type")})
    record.update({"file": str(target.relative_to(EP)), "revision": "r2", "revision_of": shot_id, "replaced_sha256": old_hash})
    save_manifest(shot_id, record)
    log_path = EP / "image/revision-log.json"
    log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else {}
    log[shot_id] = {"rejected_file": str(rejected.relative_to(EP)), "rejected_sha256": old_hash,
                    "accepted_file": str(target.relative_to(EP)), "accepted_sha256": new_hash,
                    "reason": "r1 rendered Chen Yi as male; r2 prompt maps each female identity and outfit explicitly"}
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    selected = [EP / "image/final" / f"{sid}.png" for sid in ("S01", "S02A", "S02B")]
    contact(selected, EP / "qa/contact-pilot-revised.jpg", 3)
    return target

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "anchors"
    if mode == "anchors":
        make_anchors()
        return
    if mode.startswith("repair-"):
        repair_shot(mode.removeprefix("repair-"))
        print("REPAIRED", mode.removeprefix("repair-"), flush=True)
        return
    if mode == "backgrounds":
        for i, sid in enumerate(PLAN["scenes"]):
            scene_plate(sid, i)
        return
    if mode == "pilot":
        picked = []
        for shot in PLAN["shots"]:
            if "zhouning-20261118-xinwen" in shot["character_ids"]:
                picked.append(shot)
            if len(picked) == 3:
                break
    elif mode == "all":
        picked = PLAN["shots"]
    elif mode == "range":
        start, end = int(sys.argv[2]), int(sys.argv[3])
        picked = PLAN["shots"][start:end]
    else:
        ids = set(mode.split(","))
        picked = [s for s in PLAN["shots"] if s["id"] in ids]
    paths = []
    for i, shot in enumerate(picked):
        paths.append(render_shot(shot, i))
    if paths:
        contact(paths, EP / "qa" / f"contact-{picked[0]['id']}-{picked[-1]['id']}.jpg", 3)
    print("BATCH COMPLETE", len(paths), flush=True)

if __name__ == "__main__":
    main()
