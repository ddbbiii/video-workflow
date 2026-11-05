# -*- coding: utf-8 -*-
"""Newton-to-chaos stills via gpt-image-2.5-sunburst (approved remote API).

Modes:
  --single <shot_id>...   independent 16:9-ish generation (1536x1024, crop to 16:9 later)
  --tile                  2x2 grid batch (4 shots per call), crop per cell (batch mode only)
Only shots with image_prompt (P/V classes) are eligible. Logs each response;
stills land in image/stills/<id>.jpg + .png.
"""
from __future__ import annotations
import argparse, base64, json, os, sys, time, urllib.error, urllib.request
from datetime import datetime
from pathlib import Path
from PIL import Image

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\newton-to-chaos")
SHOT_PLAN = EP / "visual" / "SHOT_PLAN.json"
STILLS = EP / "image" / "stills"
GRIDS = EP / "image" / "grids"
RUN = EP / "runs" / "20261014-ntc-b01"
MODEL = "gpt-image-2.5-sunburst"
SIZE_GRID = "2048x1152"
SIZE_SINGLE = "1536x1024"
BASE_URL = os.environ.get("IMAGE_API_BASE_URL", "https://dklapi.com/v1").rstrip("/")

def load_plan():
    return json.loads(SHOT_PLAN.read_text(encoding="utf-8"))

def shot_by_id(plan):
    return {s["id"]: s for s in plan["shots"]}

def have_ids():
    return {p.stem for p in STILLS.glob("*.jpg")} | {p.stem for p in STILLS.glob("*.png")}

def call_api(prompt, out_response, out_image, size):
    key = os.environ.get("IMAGE_RELAY_KEY_1K")
    if not key:
        raise RuntimeError("IMAGE_RELAY_KEY_1K is missing")
    payload = json.dumps({"model": MODEL, "prompt": prompt, "size": size, "n": 1},
                         ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE_URL + "/images/generations", data=payload,
                                 headers={"Authorization": "Bearer " + key,
                                          "Content-Type": "application/json"}, method="POST")
    started = time.time()
    backoffs = [20, 40, 90, 180]
    for attempt, delay in enumerate([0] + backoffs):
        if delay:
            time.sleep(delay)
        try:
            with urllib.request.urlopen(req, timeout=600) as response:
                raw = response.read(); status = response.status
            break
        except urllib.error.HTTPError as exc:
            raw = exc.read(); status = exc.code
            is_rate = status in (408, 429, 502, 503, 504) or b"rate_limit" in raw or b"overloaded" in raw
            if is_rate and attempt < len(backoffs):
                continue
            out_response.write_bytes(raw)
            raise RuntimeError(f"HTTP {status}: {raw[:500]!r}")
        except urllib.error.URLError as exc:
            if attempt < len(backoffs):
                continue
            raise RuntimeError(f"URLError: {exc}")
    elapsed = round(time.time() - started, 2)
    out_response.write_bytes(raw)
    data = json.loads(raw.decode("utf-8"))
    item = (data.get("data") or [{}])[0]
    if item.get("b64_json"):
        out_image.write_bytes(base64.b64decode(item["b64_json"]))
    elif item.get("url"):
        with urllib.request.urlopen(item["url"], timeout=600) as r:
            out_image.write_bytes(r.read())
    else:
        raise RuntimeError("no image URL or b64_json in response")
    with Image.open(out_image) as im:
        im.load(); dims = im.size
    return {"status": status, "elapsed_s": elapsed, "dims": dims,
            "bytes": out_image.stat().st_size, "size": size}

def gen_single(shot, batch_dir):
    out_img = batch_dir / f"{shot['id']}.png"
    out_resp = batch_dir / f"{shot['id']}.json"
    info = call_api(shot["image_prompt"], out_resp, out_img, SIZE_SINGLE)
    jpg = STILLS / f"{shot['id']}.jpg"
    with Image.open(out_img) as im:
        im.convert("RGB").save(jpg, quality=95, optimize=True)
    return {"id": shot["id"], "mode": "single", **info, "jpg": str(jpg)}

def build_grid_prompt(shots):
    header = ("生成一张严格等分的2x2网格图，总画幅16:9，每格也为横屏16:9。"
              "格子没有间距、装饰边框、文字或编号；不同场景只能在各自格子内，不能跨格。"
              "以下位置和编号只用于指令，不要画到图中。")
    parts = [header]
    for idx, shot in enumerate(shots):
        row, col = divmod(idx, 2)
        parts.append(f"\n\n第{row + 1}行第{col + 1}列（{shot['id']}）：\n{shot['image_prompt']}")
    return "".join(parts)

def gen_grid(shots, batch_dir):
    prompt = build_grid_prompt(shots)
    grid_png = batch_dir / f"grid_{shots[0]['id']}.png"
    out_resp = batch_dir / f"grid_{shots[0]['id']}.json"
    info = call_api(prompt, out_resp, grid_png, SIZE_GRID)
    crops_dir = batch_dir / "crops"; crops_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    with Image.open(grid_png) as im:
        width, height = im.size
        rgb = im.convert("RGB")
        for idx, shot in enumerate(shots):
            col, row = idx % 2, idx // 2
            box = (round(col * width / 2), round(row * height / 2),
                   round((col + 1) * width / 2), round((row + 1) * height / 2))
            crop = rgb.crop(box)
            (crops_dir / f"{shot['id']}.png").write_bytes(b"")  # touch dir
            crop.save(crops_dir / f"{shot['id']}.png")
            jpg = STILLS / f"{shot['id']}.jpg"
            crop.save(jpg, quality=95, optimize=True)
            saved.append({"id": shot["id"], "box": box, "size": list(crop.size), "jpg": str(jpg)})
    return {"id": f"grid:{shots[0]['id']}+{len(shots)}", "mode": "grid", **info, "saved": saved}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--single", nargs="+", default=[])
    ap.add_argument("--tile", nargs="*", default=None,
                    help="tile mode: given ids (or --tile-auto N to pick next N pending tile shots)")
    ap.add_argument("--tile-auto", type=int, default=0)
    args = ap.parse_args()

    plan = load_plan(); by_id = shot_by_id(plan)
    have = have_ids()
    STILLS.mkdir(parents=True, exist_ok=True); GRIDS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    batch_dir = GRIDS / f"batch-{stamp}"; batch_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = batch_dir / "manifest.json"
    manifest = {"batch": str(batch_dir), "items": [], "fails": []}

    jobs = []
    if args.single:
        for sid in args.single:
            if sid in have:
                print(f"skip existing {sid}"); continue
            shot = by_id.get(sid)
            if not shot or not shot.get("image_prompt"):
                print(f"no image_prompt for {sid}"); continue
            jobs.append(("single", shot))
    if args.tile or args.tile_auto:
        if args.tile:
            ids = [i for i in args.tile if i not in have]
        else:
            pend = [s for s in plan["shots"]
                    if s.get("image_mode") == "2x2_tile" and s.get("image_prompt")
                    and s["id"] not in have]
            ids = [s["id"] for s in pend[: args.tile_auto]]
        for i in range(0, len(ids), 4):
            group = [by_id[i] for i in ids[i : i + 4] if i in by_id]
            if group:
                jobs.append(("grid", group))

    for kind, payload in jobs:
        try:
            if kind == "single":
                r = gen_single(payload, batch_dir)
                print("OK", json.dumps(r, ensure_ascii=False))
                manifest["items"].append(r)
            else:
                r = gen_grid(payload, batch_dir)
                print("OK", r["id"], r.get("dims"))
                manifest["items"].append(r)
        except Exception as e:
            err = f"{kind}:{[p['id'] if isinstance(p, dict) else p for p in ([payload] if kind=='single' else payload)]}: {e}"
            print("FAIL", err)
            manifest["fails"].append(err)
            time.sleep(3)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"BATCH DONE items={len(manifest['items'])} fails={len(manifest['fails'])}")
    return 0 if not manifest["fails"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
