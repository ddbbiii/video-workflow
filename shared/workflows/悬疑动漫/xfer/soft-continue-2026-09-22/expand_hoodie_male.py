# -*- coding: utf-8 -*-
"""Expand Char B HOODIE MALE seed via img2img. Correct gender: 1boy only."""
from __future__ import annotations
import json, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
CKPT = "animagine-xl-4.0-opt.safetensors"
COMFY_INPUT = Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input")
SEED_SRC = Path(r"E:\program\1project\video\xfer\overnight-2026-09-21\charB\01-hoodie.png")
OUT_DIR = Path(r"E:\program\1project\video\shared\project-tools\lora\charb-hoodie-male-v1\dataset\img\15_charb_hoodie_male")
XFER = Path(r"E:\program\1project\video\xfer\soft-continue-2026-09-22\expand-hoodie-male-v2")
SCRATCH = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\charb-hoodie-male-expand")
STEPS, CFG = 28, 5.5
W, H = 896, 1152

BASE = (
    "1boy, solo, young adult man, male, masculine face, defined jawline, slightly angular chin, "
    "short black hair, jet black hair, messy layered short hair, bangs, warm brown eyes, "
    "fair skin with warm undertone, same skin tone as reference, lean neck, "
    "dark navy hoodie, casual hoodie with drawstrings, no hair accessories, "
    "soft cel shading, soft lighting, clean soft lineart, "
    "masterpiece, best quality, simple soft grey background"
)
NEG = (
    "1girl, woman, female, feminine face, soft feminine jaw, lipstick, makeup, long eyelashes exaggerated, "
    "hair clip, hairpin, red hair clip, earrings, loli, child, "
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, "
    "cropped, worst quality, low quality, jpeg artifacts, signature, watermark, blurry, "
    "photorealistic, extra people, multiple boys, deformed face, "
    "harsh comic lines, thick ink outlines, western comic, pink hair, grey-blue hair, blue hair"
)

JOBS = [
    ("02-front-face", 0.26, 2026092261, "close-up face, front view, looking at viewer, upper body", "close-up face, front view"),
    ("03-front-half", 0.28, 2026092262, "half body, front view, looking at viewer, standing", "half body, front view"),
    ("04-3q-left", 0.30, 2026092263, "upper body, three-quarter view from left, looking at viewer", "three-quarter view from left"),
    ("05-3q-right", 0.30, 2026092264, "upper body, three-quarter view from right, looking at viewer", "three-quarter view from right"),
    ("06-profile-left", 0.32, 2026092265, "upper body, strict side profile facing left, masculine profile", "strict side profile"),
    ("07-overshoulder", 0.32, 2026092266, "upper body, looking back over shoulder, three-quarter rear", "looking back over shoulder"),
    ("08-lookup", 0.28, 2026092267, "upper body, slight low angle, looking up", "slight look-up"),
    ("09-downcast", 0.28, 2026092268, "upper body, slight high angle, looking down", "slight look-down"),
    ("10-hands-pockets", 0.34, 2026092269, "half body, hands in hoodie pocket, casual stance, front view", "hands in pocket"),
    ("11-hood-down", 0.30, 2026092270, "upper body, hoodie hood down, front view, looking at viewer", "hood down, front view"),
    ("12-full-standing", 0.35, 2026092271, "full body, standing, full figure visible, front three-quarter view", "full body, standing"),
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
    raise SystemExit("Comfy 8188 not up")


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
            "images": ["7", 0], "filename_prefix": f"charb-hoodie-male-expand/{tag}",
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
    text = f"charb_hoodie_male, {BASE}, {extra}"
    path.write_text(text + "\n", encoding="utf-8")


def main():
    if not SEED_SRC.is_file():
        raise SystemExit(f"missing seed {SEED_SRC}")
    COMFY_INPUT.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # wipe previous high-denoise expands (keep folder)
    for old in OUT_DIR.glob('*'):
        old.unlink()
    XFER.mkdir(parents=True, exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    # seed into dataset
    seed_png = OUT_DIR / "01-seed.png"
    shutil.copy2(SEED_SRC, seed_png)
    write_caption(OUT_DIR / "01-seed.txt", "upper body, front three-quarter, looking at viewer, young adult man")
    shutil.copy2(seed_png, XFER / seed_png.name)
    shutil.copy2(OUT_DIR / "01-seed.txt", XFER / "01-seed.txt")
    # extra seed copies to weight true identity higher than expands
    for i in (2, 3):
        shutil.copy2(seed_png, OUT_DIR / f"01-seed-r{i}.png")
        write_caption(OUT_DIR / f"01-seed-r{i}.txt", "upper body, front three-quarter, looking at viewer, young adult man, preserve original face and skin tone")
    input_name = "charb-hoodie-male-01-seed.png"
    shutil.copy2(SEED_SRC, COMFY_INPUT / input_name)
    wait_server()
    results = [{"stem": "01-seed", "status": "seed"}]
    for stem, denoise, seed, prompt_extra, cap_extra in JOBS:
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
        results.append({"stem": stem, "status": "ok"})
        try_free()
    pngs = sorted(OUT_DIR.glob("*.png"))
    summary = {"ok": True, "png_count": len(pngs), "out_dir": str(OUT_DIR), "gender": "male", "results": results}
    (XFER / "EXPAND-MALE.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
