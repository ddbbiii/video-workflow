# -*- coding: utf-8 -*-
"""Expand Hoodie-Male v2 with HARDER masculinity (higher denoise + body tags).
Fresh dataset for charb-hoodie-male-sdxl-v2. Does NOT queue dual-frame.
Requires ComfyUI on 127.0.0.1:8188. Base ckpt only (no LoRA).
"""
from __future__ import annotations
import json, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
CKPT = "animagine-xl-4.0-opt.safetensors"
COMFY_INPUT = Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input")

# Prefer smoke M1 (current LoRA look) then fall back to v1 seed
SEED_CANDIDATES = [
    Path(r"E:\program\1project\video\xfer\soft-continue-2026-09-22\smoke\charb_hoodie_male\M1-front-half.png"),
    Path(r"E:\program\1project\video\shared\project-tools\lora\charb-hoodie-male-v1\dataset\img\15_charb_hoodie_male\01-seed.png"),
    Path(r"E:\program\1project\video\xfer\overnight-2026-09-21\charB\01-hoodie.png"),
]

OUT_DIR = Path(r"E:\program\1project\video\shared\project-tools\lora\charb-hoodie-male-v2\dataset\img\10_charb_hoodie_male")
XFER = Path(r"E:\program\1project\video\xfer\soft-continue-2026-09-22\expand-hoodie-male-v2-masc")
SCRATCH = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\charb-hoodie-male-v2-expand")
STEPS, CFG = 30, 5.5

# Trigger kept for captions; expand POS uses descriptive male tags (no LoRA loaded)
BASE = (
    "1boy, solo, young adult man, CLEARLY MALE, masculine face, "
    "angular male jaw, squared chin, thicker neck, adam's apple, "
    "short messy jet black hair, layered short hair, NOT bob cut, NOT grey-blue hair, "
    "warm brown eyes, fair skin with warm undertone, "
    "broad shoulders, flat chest, masculine proportions, male body, "
    "oversized dark charcoal navy hoodie with drawstrings, hood down, "
    "soft cel shading, soft lighting, clean soft lineart, "
    "masterpiece, best quality, simple soft grey background"
)
NEG = (
    "1girl, woman, female, chengwu, pretty boy, bishounen, androgynous, trap, futa, "
    "feminine face, soft feminine jaw, soft V-shaped chin, large sparkly girl eyes, "
    "lean slender girl neck, narrow girl shoulders, breasts, cleavage, slim girl waist, "
    "grey-blue hair, short bob cut, bob hair, black choker, teal scoop-neck, "
    "lipstick, makeup, long eyelashes exaggerated, hair clip, hairpin, earrings, "
    "loli, child, chibi, lowres, bad anatomy, bad hands, text, error, "
    "missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, "
    "jpeg artifacts, signature, watermark, blurry, photorealistic, extra people, "
    "multiple boys, deformed face, harsh comic lines, thick ink outlines, western comic, "
    "pink hair, blue hair, long hair"
)

# (stem, denoise, seed, prompt_extra, caption_extra)
# Higher denoise than v1 (0.26-0.35) so masculinity can land.
SEED_REDESIGN = ("01-seed-masc", 0.52, 20260923101,
                 "upper body, front three-quarter, looking at viewer, clearly male",
                 "upper body, front three-quarter, looking at viewer")

JOBS = [
    ("02-front-face", 0.36, 20260923102, "close-up face, front view, looking at viewer, upper body, masculine jaw visible", "close-up face, front view, angular male jaw"),
    ("03-front-half", 0.40, 20260923103, "half body, front view, looking at viewer, standing, broad shoulders visible", "half body, front view, broad shoulders, flat chest"),
    ("04-3q-left", 0.40, 20260923104, "upper body, three-quarter view from left, looking at viewer, male jaw", "three-quarter view from left, angular male jaw"),
    ("05-3q-right", 0.40, 20260923105, "upper body, three-quarter view from right, looking at viewer, male jaw", "three-quarter view from right, angular male jaw"),
    ("06-profile-left", 0.46, 20260923106, "upper body, strict side profile facing left, strong male profile, adam's apple", "strict side profile, thicker neck, adam's apple"),
    ("07-profile-right", 0.46, 20260923107, "upper body, strict side profile facing right, strong male profile", "strict side profile right, angular male jaw"),
    ("08-overshoulder", 0.42, 20260923108, "upper body, looking back over shoulder, three-quarter rear, broad back", "looking back over shoulder, broad shoulders"),
    ("09-lookup", 0.38, 20260923109, "upper body, slight low angle, looking up, thicker neck", "slight look-up, thicker neck"),
    ("10-downcast", 0.38, 20260923110, "upper body, slight high angle, looking down", "slight look-down, masculine face"),
    ("11-hands-pockets", 0.44, 20260923111, "half body, hands in hoodie pocket, casual stance, broad shoulders, front view", "hands in pocket, broad shoulders, flat chest"),
    ("12-arms-crossed", 0.44, 20260923112, "half body, arms crossed, standing, masculine stance, front view", "arms crossed, broad shoulders, male proportions"),
    ("13-hood-down", 0.40, 20260923113, "upper body, hoodie hood down, front view, looking at viewer", "hood down, front view, angular male jaw"),
    ("14-full-standing", 0.50, 20260923114, "full body, standing, full figure visible, front three-quarter, taller male frame, flat chest", "full body, standing, broad shoulders, flat chest, male proportions"),
    ("15-full-walk", 0.50, 20260923115, "full body, walking pose, side three-quarter, masculine gait, flat chest", "full body, walking, male proportions, flat chest"),
    ("16-full-sit", 0.48, 20260923116, "full body, sitting casually, knees visible, broad shoulders, flat chest", "full body, sitting, broad shoulders, flat chest"),
    ("17-3q-smile", 0.40, 20260923117, "upper body, three-quarter view, slight smile, masculine face", "three-quarter, slight smile, angular male jaw"),
    ("18-crouch", 0.48, 20260923118, "full body, slight crouch, athletic male stance, flat chest", "full body, crouch, male proportions"),
    ("19-back-half", 0.44, 20260923119, "half body from behind, short black hair, broad shoulders, hoodie", "back view half body, broad shoulders"),
    ("20-lean-wall", 0.44, 20260923120, "half body, leaning, casual male stance, hands in pocket, flat chest", "half body lean, broad shoulders, flat chest"),
]


def get(url, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def post(url, obj, timeout=180):
    data = json.dumps(obj).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def wait_server(tries=60):
    for _ in range(tries):
        try:
            get(f"{SERVER}/system_stats", 3)
            return
        except Exception:
            time.sleep(2)
    raise SystemExit("Comfy 8188 not up — start ComfyUI first")


def graph(input_name, pos, seed, denoise, tag):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoadImage", "inputs": {"image": input_name}},
        "3": {"class_type": "VAEEncode", "inputs": {"pixels": ["2", 0], "vae": ["1", 2]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["1", 1]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["1", 1]}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["4", 0], "negative": ["5", 0],
            "latent_image": ["3", 0], "seed": seed, "steps": STEPS, "cfg": CFG,
            "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": denoise,
        }},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {
            "images": ["7", 0], "filename_prefix": f"charb-hoodie-male-v2-expand/{tag}",
        }},
    }


def queue_wait(g):
    resp = post(f"{SERVER}/prompt", {"prompt": g, "client_id": str(uuid.uuid4())})
    if resp.get("node_errors"):
        raise SystemExit("node_errors " + json.dumps(resp["node_errors"], ensure_ascii=False))
    pid = resp["prompt_id"]
    print("queued", pid, flush=True)
    t0 = time.time()
    while time.time() - t0 < 600:
        hist = get(f"{SERVER}/history/{pid}")
        if pid in hist:
            entry = hist[pid]
            st = entry.get("status") or {}
            if st.get("status_str") == "error":
                raise SystemExit("comfy error " + json.dumps(st.get("messages"), ensure_ascii=False))
            return entry
        time.sleep(2)
    raise TimeoutError(pid)


def download(meta, dest: Path):
    q = urllib.parse.urlencode({
        "filename": meta["filename"],
        "subfolder": meta.get("subfolder") or "",
        "type": meta.get("type") or "output",
    })
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(f"{SERVER}/view?{q}", timeout=120) as r:
        dest.write_bytes(r.read())


def try_free():
    try:
        post(f"{SERVER}/free", {"unload_models": True, "free_memory": True}, 30)
        time.sleep(1)
    except Exception:
        pass


def write_caption(path: Path, extra: str):
    text = (
        f"charb_hoodie_male, 1boy, solo, young adult man, male, "
        f"angular male jaw, squared chin, thicker neck, adam's apple, "
        f"short messy jet black hair, NOT bob cut, warm brown eyes, "
        f"fair skin with warm undertone, broad shoulders, flat chest, masculine proportions, "
        f"oversized dark charcoal navy hoodie with drawstrings, hood down, "
        f"soft cel shading, soft lighting, clean soft lineart, "
        f"masterpiece, best quality, simple soft grey background, {extra}"
    )
    path.write_text(text + "\n", encoding="utf-8")


def pick_seed() -> Path:
    for p in SEED_CANDIDATES:
        if p.is_file():
            return p
    raise SystemExit("no seed candidate found")


def run_one(input_name, stem, denoise, seed, prompt_extra, cap_extra, results):
    dest = OUT_DIR / f"{stem}.png"
    pos = f"{BASE}, {prompt_extra}"
    print(f"run {stem} denoise={denoise}", flush=True)
    entry = queue_wait(graph(input_name, pos, seed, denoise, stem))
    saved = False
    for node in (entry.get("outputs") or {}).values():
        for im in node.get("images") or []:
            tmp = SCRATCH / f"{stem}-{im['filename']}"
            download(im, tmp)
            shutil.copy2(tmp, dest)
            write_caption(OUT_DIR / f"{stem}.txt", cap_extra)
            shutil.copy2(dest, XFER / dest.name)
            shutil.copy2(OUT_DIR / f"{stem}.txt", XFER / f"{stem}.txt")
            saved = True
            print("saved", dest, flush=True)
            break
        if saved:
            break
    if not saved:
        raise SystemExit(f"no image for {stem}")
    results.append({"stem": stem, "status": "ok", "denoise": denoise})
    try_free()


def main():
    seed_src = pick_seed()
    print("seed_src", seed_src, flush=True)
    COMFY_INPUT.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    XFER.mkdir(parents=True, exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("*"):
        old.unlink()

    wait_server()
    results = []

    # Stage original soft ref → redesign masculine seed
    input_soft = "charb-hoodie-male-v2-softref.png"
    shutil.copy2(seed_src, COMFY_INPUT / input_soft)
    stem, denoise, seed, pextra, cextra = SEED_REDESIGN
    run_one(input_soft, stem, denoise, seed, pextra, cextra, results)

    # Also store as 01-seed.png (training anchor name)
    shutil.copy2(OUT_DIR / f"{stem}.png", OUT_DIR / "01-seed.png")
    shutil.copy2(OUT_DIR / f"{stem}.txt", OUT_DIR / "01-seed.txt")
    shutil.copy2(OUT_DIR / "01-seed.png", XFER / "01-seed.png")
    shutil.copy2(OUT_DIR / "01-seed.txt", XFER / "01-seed.txt")
    results.append({"stem": "01-seed", "status": "alias-of-01-seed-masc"})

    # Expand from redesigned seed
    input_masc = "charb-hoodie-male-v2-01-seed-masc.png"
    shutil.copy2(OUT_DIR / "01-seed.png", COMFY_INPUT / input_masc)
    for stem, denoise, seed, pextra, cextra in JOBS:
        run_one(input_masc, stem, denoise, seed, pextra, cextra, results)

    pngs = sorted(OUT_DIR.glob("*.png"))
    summary = {
        "ok": True,
        "png_count": len(pngs),
        "out_dir": str(OUT_DIR),
        "gender": "male",
        "version": "v2-masc",
        "seed_src": str(seed_src),
        "note": "EYE-CHECK 01-seed-masc before training. Reject if still pretty-boy / Chengwu-like.",
        "results": results,
    }
    (XFER / "EXPAND-MALE-V2.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT_DIR.parent.parent.parent / "EXPAND-MALE-V2.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
