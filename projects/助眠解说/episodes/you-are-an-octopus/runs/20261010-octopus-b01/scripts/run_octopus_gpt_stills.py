# -*- coding: utf-8 -*-
"""Octopus stills via gpt-image-2.5-sunburst: 2x2 grids + single for complex closeups."""
from __future__ import annotations
import argparse, base64, json, os, sys, time, urllib.error, urllib.request
from datetime import datetime
from pathlib import Path
from PIL import Image

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\you-are-an-octopus")
SHOT_PLAN = EP / "visual" / "SHOT_PLAN.json"
STILLS = EP / "image" / "stills"
GRIDS = EP / "image" / "grids"
RUN_ROOT = EP / "runs" / "20261010-octopus-b01" / "stills-gpt2x2"
CKPT = EP / "runs" / "20261010-octopus-b01" / "CHECKPOINT.json"
STATUS = EP / "runs" / "20261010-octopus-b01" / "STATUS.md"
MODEL = "gpt-image-2.5-sunburst"
SIZE = "2048x1152"
SIZE_SINGLE = "1536x1024"
BASE_URL = os.environ.get("IMAGE_API_BASE_URL", "https://dklapi.com/v1").rstrip("/")

def load_plan():
    return json.loads(SHOT_PLAN.read_text(encoding="utf-8"))

def have_ids():
    return {p.stem for p in STILLS.glob("*.jpg")} | {p.stem for p in STILLS.glob("*.png")}

def missing_by_mode(mode: str):
    have = have_ids()
    return [s for s in load_plan()["shots"] if s["id"] not in have and s.get("image_mode") == mode]

def build_grid_prompt(shots):
    header = (
        "生成一张严格等分的2x2网格图，总画幅16:9，每格也为横屏16:9。"
        "格子没有间距、装饰边框、文字或编号；不同场景只能在各自格子内，不能跨格。"
        "以下位置和编号只用于指令，不要画到图中。"
    )
    parts = [header]
    for idx, shot in enumerate(shots):
        row, col = divmod(idx, 2)
        body = (shot.get("image_prompt") or "").strip()
        parts.append(f"\n\n第{row + 1}行第{col + 1}列（{shot['id']}）：\n{body}")
    return "".join(parts)

def call_api(prompt, out_response: Path, out_image: Path, size: str):
    key = os.environ.get("IMAGE_RELAY_KEY_1K")
    if not key:
        raise RuntimeError("IMAGE_RELAY_KEY_1K is missing")
    payload = json.dumps(
        {"model": MODEL, "prompt": prompt, "size": size, "n": 1},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + "/images/generations",
        data=payload,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=600) as response:
            raw = response.read(); status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read(); status = exc.code
        out_response.write_bytes(raw)
        raise RuntimeError(f"HTTP {status}: {raw[:500]!r}")
    elapsed = round(time.time() - started, 2)
    out_response.write_bytes(raw)
    data = json.loads(raw.decode("utf-8"))
    item = (data.get("data") or [{}])[0]
    if item.get("b64_json"):
        out_image.write_bytes(base64.b64decode(item["b64_json"]))
    elif item.get("url"):
        with urllib.request.urlopen(item["url"], timeout=600) as image_response:
            out_image.write_bytes(image_response.read())
    else:
        raise RuntimeError("no image URL or b64_json in response")
    with Image.open(out_image) as im:
        im.load(); dims = im.size
    return {"status": status, "elapsed_s": elapsed, "dims": dims, "bytes": out_image.stat().st_size, "size": size}

def split_and_save(grid_path: Path, shots, batch_dir: Path):
    crops_dir = batch_dir / "crops"; crops_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    with Image.open(grid_path) as im:
        width, height = im.size
        rgb = im.convert("RGB")
        for idx, shot in enumerate(shots):
            col, row = idx % 2, idx // 2
            box = (round(col * width / 2), round(row * height / 2),
                   round((col + 1) * width / 2), round((row + 1) * height / 2))
            crop = rgb.crop(box)
            crop_png = crops_dir / f"{shot['id']}.png"
            crop_jpg = STILLS / f"{shot['id']}.jpg"
            crop.save(crop_png)
            crop.save(crop_jpg, quality=95, optimize=True)
            saved.append({"id": shot["id"], "box": box, "size": list(crop.size), "path": str(crop_jpg)})
    return saved

def touch_ckpt(have_n, note):
    d = {}
    if CKPT.exists():
        try: d = json.loads(CKPT.read_text(encoding="utf-8"))
        except Exception: d = {}
    d["stills_count"] = have_n
    d["stills_note"] = note
    d["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    CKPT.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batches", type=int, default=999)
    ap.add_argument("--sleep", type=float, default=2.0)
    ap.add_argument("--mode", choices=["2x2", "single", "all"], default="all")
    args = ap.parse_args()
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    STILLS.mkdir(parents=True, exist_ok=True)
    GRIDS.mkdir(parents=True, exist_ok=True)

    for bi in range(args.batches):
        # Prefer filling 2x2 first (faster), then singles
        do_2x2 = args.mode in ("2x2", "all")
        do_single = args.mode in ("single", "all")
        batch = None; kind = None
        if do_2x2:
            miss = missing_by_mode("2x2_tile")
            if miss:
                batch = miss[:4]; kind = "2x2"
                while len(batch) < 4:
                    batch.append({
                        "id": f"_pad-{len(batch)}",
                        "image_prompt": (
                            "Empty calm teal-blue underwater midwater with soft volumetric light, "
                            "no animal, no text, photorealistic water and distant rock, 16:9."
                        ),
                    })
        if batch is None and do_single:
            miss = missing_by_mode("single")
            if miss:
                batch = [miss[0]]; kind = "single"
        if batch is None:
            # also catch any shots without image_mode or intro listed
            have = have_ids()
            other = [s for s in load_plan()["shots"] if s["id"] not in have]
            if not other:
                print("ALL_DONE stills complete", len(have_ids()), flush=True)
                touch_ckpt(len(have_ids()), "stills complete")
                return 0
            # treat unknown as single
            batch = [other[0]]; kind = "single"

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        lead = batch[0]["id"]
        batch_dir = RUN_ROOT / f"batch-{stamp}-{lead}"
        batch_dir.mkdir(parents=True, exist_ok=False)
        if kind == "2x2":
            prompt = build_grid_prompt(batch)
            size = SIZE
        else:
            prompt = (batch[0].get("image_prompt") or "").strip()
            size = SIZE_SINGLE
        (batch_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
        ids = [s["id"] for s in batch if not str(s["id"]).startswith("_pad")]
        print(f"BATCH {bi+1} kind={kind} ids={ids}", flush=True)
        grid_path = batch_dir / ("grid2x2.png" if kind == "2x2" else "single.png")
        resp_path = batch_dir / "response.json"
        try:
            meta = call_api(prompt, resp_path, grid_path, size)
        except Exception as exc:
            (batch_dir / "error.txt").write_text(repr(exc), encoding="utf-8")
            print("FAIL", ids, type(exc).__name__, exc, flush=True)
            return 1
        print("API_OK", meta, flush=True)
        if kind == "2x2":
            real = [s for s in batch if not str(s["id"]).startswith("_pad")]
            saved = split_and_save(grid_path, real, batch_dir)
            # also keep grid
            dst = GRIDS / f"{lead}_grid2x2.png"
            dst.write_bytes(grid_path.read_bytes())
        else:
            with Image.open(grid_path) as im:
                rgb = im.convert("RGB")
                jpg = STILLS / f"{batch[0]['id']}.jpg"
                rgb.save(jpg, quality=95, optimize=True)
                saved = [{"id": batch[0]["id"], "size": list(rgb.size), "path": str(jpg)}]
        (batch_dir / "manifest.json").write_text(
            json.dumps({"model": MODEL, "kind": kind, "api": meta, "saved": saved}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        have_n = len(list(STILLS.glob("*.jpg")))
        touch_ckpt(have_n, f"last={ids}")
        print("SAVED", ids, "stills", have_n, flush=True)
        time.sleep(args.sleep)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())