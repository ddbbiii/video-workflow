from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from threading import Lock
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw

EP = Path(__file__).resolve().parents[1]
REPO = EP.parents[3]
PLAN_PATH = EP / "storyboard" / "SHOT_PLAN.json"
RULES_PATH = REPO / "rules" / "悬疑" / "visual.md"
POLICY_PATH = REPO / "shared" / "image-api" / "channel-policy.json"
GP_PATH = REPO / "projects" / "悬疑" / "visual-tests" / "20261114-pilot-8shots" / "gen_pilot.py"
IMAGE = EP / "image"
RAW, BG, CROPS, ANCHORS, COMPOSITES, QA = [IMAGE / p for p in
    ("stills-raw", "backgrounds", "crops", "anchors", "composites", "qa")]
for folder in (RAW, BG, CROPS, ANCHORS, COMPOSITES, QA):
    folder.mkdir(parents=True, exist_ok=True)

spec = importlib.util.spec_from_file_location("suspense_image_api", GP_PATH)
gp = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = gp
spec.loader.exec_module(gp)
gp.HERE, gp.RAW, gp.CROPS, gp.ANCH = IMAGE, RAW, CROPS, ANCHORS
gp.RULES, gp.POLICY = RULES_PATH, POLICY_PATH

PLAN = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
STYLE_POS, STYLE_NEG, CEL_BOOST = [gp.read_block(k) for k in ("STYLE_POS", "STYLE_NEG", "CEL_BOOST")]
POLICY = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
POLICY_NAME = POLICY["active"]
ROUTE = POLICY["policies"][POLICY_NAME]
CHANNEL_NAMES = ROUTE.get("parallel_channels") or [ROUTE["default_channel"]]
CHANNELS = []
for channel_name in CHANNEL_NAMES:
    channel = dict(POLICY["channels"][channel_name])
    channel["name"] = channel_name
    channel["policy"] = POLICY_NAME
    CHANNELS.append(channel)
MANIFEST_LOCK = Lock()
CHAR_ID = PLAN["character"]["character_id"]
CHAR_ANCHOR = ANCHORS / "linxu-turnsheet-v2.png"
VIEWS = {key: ANCHORS / f"{key}-v2.png" for key in ("front", "side", "back", "face")}


def character_description() -> str:
    return ("one same approximately 30-year-old Chinese male office worker, ordinary lean adult build, "
            "short black hair with a natural side part, narrow dark-brown eyes, straight brows, ordinary nose, "
            "thin lips, tired but healthy face; fixed outfit: charcoal grey commuter jacket over a light grey "
            "shirt, straight black trousers and worn black leather shoes; no tie, glasses, jewelry or bag; "
            "same face, hairstyle, body and clothes in every view")


def make_character_sheet() -> None:
    prompt = (f"{STYLE_POS}, {CEL_BOOST}, one clean 2 by 2 reference sheet of {character_description()}, "
              "top left full-body front view, top right full-body 90-degree side view, bottom left full-body back view, "
              "bottom right front face close-up; same adult male in every panel, same scale and neutral standing pose, "
              "plain uniform muted grey flat background, exactly three hard-edged flat color tones per surface, "
              "uniform shirt fabric and uniform grey backdrop, solid cel-shadow shapes only, no gradients anywhere, "
              "no soft shading, no airbrush, no hatching, no crosshatching, no rim glow, no paper texture, "
              "clear panel separation only by spacing, no captions or text, no props, no scene, "
              f"Avoid: {STYLE_NEG}")
    shot = {"tag": "linxu-turnsheet-v2", "title": "Lin Xu character anchor v2"}
    channel = CHANNELS[0]
    info, channel, attempts, fallback_from = routed_call(channel, prompt, shot, None)
    if not info.get("ok"):
        raise RuntimeError(f"character anchor failed: {info.get('error')}")
    with Image.open(RAW / "linxu-turnsheet-v2.png") as source:
        image = source.convert("RGB")
        w, h = image.size
        expected_size = tuple(int(x) for x in channel["size"].split("x"))
        if (w, h) != expected_size:
            raise RuntimeError(f"turn sheet size mismatch: {image.size}")
        # Inset 4 px from each quadrant to remove possible grid separators.
        boxes = {
            "front": (4, 4, w // 2 - 4, h // 2 - 4),
            "side": (w // 2 + 4, 4, w - 4, h // 2 - 4),
            "back": (4, h // 2 + 4, w // 2 - 4, h - 4),
            "face": (w // 2 + 4, h // 2 + 4, w - 4, h - 4),
        }
        for key, box in boxes.items():
            image.crop(box).save(VIEWS[key])
        image.save(CHAR_ANCHOR)
    prompt_path = ANCHORS / "linxu-turnsheet-v2.prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    anchor_manifest = {"character_id": CHAR_ID, "channel": channel["name"], "policy": channel["policy"],
                       "model": channel["model"], "size": channel["size"], "attempts": attempts,
                       "fallback_from": fallback_from,
                       "file": str(CHAR_ANCHOR.relative_to(EP)).replace("\\", "/"),
                       "sha256": info["sha256"], "prompt_file": str(prompt_path.relative_to(EP)).replace("\\", "/"),
                       "views": {key: str(value.relative_to(EP)).replace("\\", "/") for key, value in VIEWS.items()},
                       "note": "v1 retained for comparison; v2 is the active flatness-corrected anchor."}
    (ANCHORS / "manifest.json").write_text(json.dumps(anchor_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ANCHOR OK {info.get('dims')} {info.get('elapsed_s')}s", flush=True)


def location_text(scene: str) -> tuple[str, str, str]:
    loc = PLAN["locations"][scene]
    return ", ".join(loc["anchors"]), ", ".join(loc["decay"]), ", ".join(loc["life"])


def image_prompt(shot: dict, reference: bool = False) -> str:
    anchors, decay, life = location_text(shot["scene"])
    shot_type = shot["type"]
    cast = shot.get("cast", "none")
    camera = {
        "E": "camera far or medium at the doorway or opposite wall, eye level, 24mm wide-angle, deep focus, "
             "location recedes along a third line, one foreground doorframe or railing occludes an edge",
        "M": "camera medium distance 3 to 4 metres, eye level, 28mm wide-angle, deep focus, person on a side third, "
             "foreground doorway or furniture edge occludes one corner; person height about 0.6 of a visible door",
        "C": "camera close but not macro, 28mm wide-angle with deep focus, evidence prop on a side third and fully visible, "
             "foreground edge frames but does not cover the evidence",
    }[shot_type]
    cel = f", {CEL_BOOST}" if shot_type == "C" or shot.get("cast") in ("linxu", "hand") else ""
    if shot.get("cast") == "none":
        subject = f"no people, {shot['visual']}"
        char_text = ""
    elif shot.get("cast") == "hand" and reference:
        subject = f"only one adult male right hand with a charcoal jacket cuff, no full person, {shot['visual']}"
        char_text = "Use the scene input as the location reference and preserve its layout; render one hand only."
    elif shot.get("cast") == "hand":
        subject = f"empty environment plate, no people, establish the location for a later hand composite: {shot['visual']}"
        char_text = ""
    elif reference:
        subject = shot["visual"]
        char_text = (f"Character reference composite: preserve the adult man shown in the reference strip, "
                     f"{character_description()}; render one person only.")
    else:
        subject = f"empty environment plate, no people, establish the exact location for a later character composite: {shot['visual']}"
        char_text = ""
    layers = (f"foreground: worn doorframe, curtain edge or railing with {decay}; "
              f"middle ground: {life}; background: {anchors}")
    light = ("cold grey-blue ambient light, one controlled small warm practical light as the only warm spot; "
             "lamps are flat shapes with no halo")
    fact_line = f"evidence/fact: {shot['fact']} {shot['evidence']}" if cast == "none" or reference else ""
    parts = [STYLE_POS + cel, camera, char_text, f"subject: {subject}", f"layers: {layers}",
             f"decay: {decay}", f"life trace: {life}", f"light: {light}",
             fact_line,
             "hard constraints: one readable fact only, ordinary Chinese urban setting, no readable text, letters, "
             "numbers, signage, UI, logos, watermark, collage, extra people, duplicate person, monster, gore, "
             "ruined building, collapsed wall, rubble, plant overgrowth, no fake navigation labels or map text"]
    if reference:
        parts.append("Use the left part of the input only as the scene/layout reference and the right strip only as the character identity reference; "
                     "do not reproduce the combined reference layout; output one full-frame 16:9 scene.")
    parts.append("Avoid: " + STYLE_NEG)
    return ", ".join(p for p in parts if p)


def compose_references(bg_path: Path, output: Path) -> Path:
    with Image.open(bg_path) as src:
        bg = src.convert("RGB").resize((1000, 563), Image.Resampling.LANCZOS)
    with Image.open(CHAR_ANCHOR) as src:
        # A three-view strip avoids sending the original panel layout as a scene reference.
        char = src.convert("RGB").resize((640, 360), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (1640, 563), (34, 38, 43))
    canvas.paste(bg, (0, 0))
    canvas.paste(char, (1000, 0))
    canvas.save(output)
    return output


def routed_call(channel: dict, prompt: str, shot: dict, anchor: Path | None) -> tuple[dict, dict, list[dict], str | None]:
    attempt_log = []
    selected = channel
    fallback_from = None
    for route_index in range(len(CHANNELS)):
        for attempt in range(1, 3):
            info = gp.call(selected, prompt, shot, anchor, attempt)
            attempt_log.append({"channel": selected["name"], "attempt": attempt,
                                "http_status": info.get("http_status"), "ok": info.get("ok"),
                                "error": info.get("error")})
            if info.get("ok"):
                return info, selected, attempt_log, fallback_from
            status = info.get("http_status")
            transient = status is None or status in (429, 500, 502, 503, 504)
            depleted = status == 403
            if not transient and not depleted:
                return info, selected, attempt_log, fallback_from
            if depleted:
                break
        if route_index + 1 < len(CHANNELS):
            fallback_from = selected["name"]
            selected = next(c for c in CHANNELS if c["name"] != selected["name"])
        else:
            break
    return info, selected, attempt_log, fallback_from


def generate_one(shot: dict, channel: dict, retry_suffix: str = "") -> dict:
    tag = shot["id"]
    run_tag = tag + retry_suffix
    cast = shot.get("cast", "none")
    bg_path = None
    if cast != "none":
        bg_shot = {"tag": f"BG-{run_tag}", "title": f"unoccupied plate for {tag}"}
        bg_info, channel, bg_attempts, bg_fallback = routed_call(
            channel, image_prompt(shot, reference=False), bg_shot, None)
        if not bg_info.get("ok"):
            return {"id": tag, "pass": False, "stage": "background", "channel": channel["name"],
                    "attempt_log": bg_attempts, "error": bg_info.get("error")}
        bg_path = RAW / Path(bg_info["file"]).name
        bg_path.replace(BG / f"{run_tag}-background.png")
        bg_path = BG / f"{run_tag}-background.png"
    ref = None
    if cast == "linxu":
        ref = compose_references(bg_path, COMPOSITES / f"{run_tag}-scene-character-reference.png")
    elif cast == "hand":
        ref = bg_path
    final_shot = {"tag": run_tag, "title": shot["fact"]}
    final, channel, final_attempts, final_fallback = routed_call(
        channel, image_prompt(shot, reference=cast in ("linxu", "hand")), final_shot, ref)
    if not final.get("ok"):
        return {"id": tag, "pass": False, "stage": "final", "channel": channel["name"],
                "attempt_log": final_attempts, "error": final.get("error")}
    final_path = RAW / Path(final["file"]).name
    with Image.open(final_path) as im:
        expected_size = tuple(int(x) for x in channel["size"].split("x"))
        if im.size != expected_size:
            return {"id": tag, "pass": False, "stage": "size", "dims": list(im.size)}
    metrics = gp.measure(final_path)
    qa = gp.gate({"dims": final["dims"], "metrics": metrics}, channel)
    style_notes = []
    if metrics["mean_sat"] > 85:
        style_notes.append("mean saturation above 85; inspect style in contact sheet")
    if metrics["mean_lum"] < 32:
        style_notes.append("mean luminance below 32; inspect shadow readability")
    record = {"id": tag, "type": shot["type"], "scene_id": shot["scene"],
              "character_ids": [CHAR_ID] if cast == "linxu" else [],
              "cast": cast, "fact": shot["fact"], "channel": channel["name"],
              "policy": channel["policy"], "model": channel["model"], "endpoint": final["endpoint"],
              "fallback_from": final_fallback or (bg_fallback if cast != "none" else None),
              "background_attempts": bg_attempts if cast != "none" else [],
              "final_attempts": final_attempts,
              "request_size": channel["size"], "dims": final["dims"], "sha256": final["sha256"],
              "pass": not qa, "qa": qa, "style_notes": style_notes, "metrics": metrics,
              "background_path": str(bg_path.relative_to(EP)).replace("\\", "/") if bg_path else None,
              "composite_path": str(ref.relative_to(EP)).replace("\\", "/") if ref and cast == "linxu" else None,
              "file": final["file"], "prompt": final["prompt"], "elapsed_s": final.get("elapsed_s"),
              "attempt_tag": run_tag}
    manifest_path = IMAGE / "manifest.json"
    with MANIFEST_LOCK:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        manifest.setdefault("shots", {})[tag] = record
        manifest.update({"run": EP.name, "channels": CHANNEL_NAMES, "channel_policy": POLICY_NAME,
                         "updated_at": datetime.now().isoformat(timespec="seconds"),
                         "style_pos": STYLE_POS, "style_neg": STYLE_NEG, "cel_boost": CEL_BOOST,
                         "ui_policy": "No readable generated UI; compose exact interface elements deterministically in post."})
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def contact_sheet(ids: list[str], name: str) -> Path:
    cols = 3
    cw, ch, label_h = 650, 366, 48
    rows = math.ceil(len(ids) / cols)
    canvas = Image.new("RGB", (cols * cw, rows * (ch + label_h)), (15, 18, 21))
    draw = ImageDraw.Draw(canvas)
    font = gp.font(22)
    manifest_path = IMAGE / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    for i, shot_id in enumerate(ids):
        record = manifest.get("shots", {}).get(shot_id, {})
        path = IMAGE / record["file"] if record.get("file") else RAW / f"{shot_id}.png"
        if not path.exists():
            x, y = (i % cols) * cw, (i // cols) * (ch + label_h)
            draw.text((x + 10, y + 6), f"{shot_id} · NOT GENERATED", fill=(225, 150, 120), font=font)
            continue
        with Image.open(path) as im:
            tile = im.convert("RGB").resize((cw - 12, ch), Image.Resampling.LANCZOS)
        x, y = (i % cols) * cw, (i // cols) * (ch + label_h)
        draw.text((x + 10, y + 6), shot_id, fill=(235, 237, 241), font=font)
        canvas.paste(tile, (x + 6, y + label_h))
    out = QA / f"{name}-contact.png"
    canvas.save(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchor", action="store_true")
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--batch", choices=("1", "2"))
    ap.add_argument("--ids", default="", help="指定镜头 ID，逗号分隔；供分段批次调用")
    ap.add_argument("--attempt-suffix", default="", help="给本次生成文件加唯一后缀，避免覆盖旧尝试")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--rebuild-sheet", default="", help="仅按已有 manifest 重建联系表")
    args = ap.parse_args()
    if args.rebuild_sheet:
        selected_ids = [s["id"] for s in PLAN["shots"]] if args.rebuild_sheet == "all" else [
            x.strip() for x in args.rebuild_sheet.split(",") if x.strip()]
        print(contact_sheet(selected_ids, "full" if args.rebuild_sheet == "all" else "requested"), flush=True)
        return 0
    if args.anchor:
        make_character_sheet()
        return 0
    if not CHAR_ANCHOR.exists():
        raise SystemExit("Character anchor missing; run --anchor first.")
    # Check the configured credential without printing or persisting it.
    for channel in CHANNELS:
        gp.key_for(channel["key_env"])
    shots = PLAN["shots"]
    if args.ids:
        chosen = [x.strip() for x in args.ids.split(",") if x.strip()]
        batch_name = "batch-" + chosen[0].lower() + "-" + chosen[-1].lower()
    elif args.pilot:
        chosen = ["S01", "S03", "S06", "S08", "S13", "S15"]
        batch_name = "pilot6"
    elif args.batch == "1":
        chosen = [s["id"] for s in shots[:24]]
        batch_name = "batch01"
    elif args.batch == "2":
        chosen = [s["id"] for s in shots[24:]]
        batch_name = "batch02"
    else:
        raise SystemExit("Choose --pilot, --batch 1, --batch 2, or --anchor.")
    unknown = set(chosen) - {s["id"] for s in shots}
    if unknown:
        raise SystemExit(f"Unknown shot IDs: {sorted(unknown)}")
    planned = [s for s in shots if s["id"] in chosen]
    current_manifest_path = IMAGE / "manifest.json"
    current_manifest = json.loads(current_manifest_path.read_text(encoding="utf-8")) if current_manifest_path.exists() else {}
    current_records = current_manifest.get("shots", {})
    selected = []
    for shot in planned:
        record = current_records.get(shot["id"], {})
        record_path = IMAGE / record["file"] if record.get("file") else None
        if record.get("pass") and record_path and record_path.exists():
            continue
        selected.append(shot)
    print(f"channels={','.join(CHANNEL_NAMES)} policy={POLICY_NAME} new={len(selected)} "
          f"planned={len(planned)} skipped_pass={len(planned)-len(selected)}", flush=True)
    def run_pair(item: tuple[int, dict]) -> dict:
        index, shot = item
        previous = current_records.get(shot["id"], {})
        channel = next((c for c in CHANNELS if c["name"] == previous.get("channel")),
                       CHANNELS[index % len(CHANNELS)])
        retry_suffix = args.attempt_suffix or ("-retry2" if previous and not previous.get("pass") else "")
        result = generate_one(shot, channel, retry_suffix)
        if retry_suffix:
            previous_summary = {"file": previous.get("file"), "channel": previous.get("channel"),
                                "qa": previous.get("qa"), "metrics": previous.get("metrics")}
            result["previous_attempt"] = previous_summary
            path = IMAGE / "manifest.json"
            with MANIFEST_LOCK:
                manifest = json.loads(path.read_text(encoding="utf-8"))
                manifest["shots"][shot["id"]]["previous_attempt"] = previous_summary
                path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    results = []
    with ThreadPoolExecutor(max_workers=min(2, len(CHANNELS))) as pool:
        for result in pool.map(run_pair, enumerate(selected)):
            results.append(result)
            print(f"{result['id']}: {'PASS' if result.get('pass') else 'FAIL'} "
                  f"channel={result.get('channel', '?')} {result.get('qa', result.get('error', ''))}", flush=True)
    sheet = contact_sheet(chosen, batch_name)
    final_manifest = json.loads(current_manifest_path.read_text(encoding="utf-8")) if current_manifest_path.exists() else {}
    final_records = final_manifest.get("shots", {})
    batch_records = [final_records.get(shot_id, {}) for shot_id in chosen]
    report = {"batch": batch_name, "channels": CHANNEL_NAMES, "policy": POLICY_NAME,
              "count": len(planned), "generated": len(selected),
              "passed": sum(bool(record.get("pass")) for record in batch_records),
              "failed": [{"id": shot_id, "record": final_records.get(shot_id)}
                         for shot_id in chosen if not final_records.get(shot_id, {}).get("pass")],
              "contact_sheet": str(sheet),
              "results": results}
    (QA / f"{batch_name}-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"CONTACT {sheet}", flush=True)
    return 0 if report["passed"] == len(planned) else 1


if __name__ == "__main__":
    raise SystemExit(main())
