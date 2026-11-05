# -*- coding: utf-8 -*-
"""Expand Char B jacket seed via ComfyUI 8188 img2img (no character LoRA yet)."""
from __future__ import annotations
import json, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
CKPT = "animagine-xl-4.0-opt.safetensors"
COMFY_INPUT = Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input")
SEED_SRC = Path(r"E:\program\1project\video\shared\project-tools\lora\charb-jacket-v1\dataset\img\10_charb_jacket\01-seed.png")
OUT_DIR = Path(r"E:\program\1project\video\shared\project-tools\lora\charb-jacket-v1\dataset\img\10_charb_jacket")
XFER = Path(r"E:\program\1project\video\xfer\charb-jacket-prep\expand")
SCRATCH = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\charb-jacket-expand")
STEPS, CFG = 28, 5.5
W, H = 896, 1152

BASE = (
    "1girl, solo, young adult woman, short hair, black hair, bob cut, bangs, red hair clip, "
    "dark eyes, pale skin, black oversized jacket, white t-shirt, anime style, "
    "masterpiece, best quality, simple grey background"
)
NEG = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, "
    "cropped, worst quality, low quality, jpeg artifacts, signature, watermark, blurry, "
    "loli, child, photorealistic, extra people, multiple girls, deformed face, "
    "different hair color, blonde, long hair"
)

# (filename_stem, denoise, seed, prompt_extra, caption_extra)
JOBS = [
    ("02-front-face", 0.42, 2026092102, "close-up face, front view, looking at viewer, upper body",
     "close-up face, front view, looking at viewer, upper body"),
    ("03-front-half", 0.45, 2026092103, "half body, front view, looking at viewer, standing",
     "half body, front view, looking at viewer"),
    ("04-3q-left", 0.48, 2026092104, "upper body, three-quarter view from left, looking at viewer",
     "upper body, three-quarter view from left"),
    ("05-3q-right", 0.48, 2026092105, "upper body, three-quarter view from right, looking at viewer",
     "upper body, three-quarter view from right"),
    ("06-profile-left", 0.50, 2026092106, "upper body, strict side profile facing left",
     "upper body, strict side profile"),
    ("07-overshoulder", 0.50, 2026092107, "upper body, looking back over shoulder, three-quarter rear",
     "looking back over shoulder"),
    ("08-lookup", 0.45, 2026092108, "upper body, slight low angle, looking up, chin raised a little",
     "slight look-up, low angle"),
    ("09-downcast", 0.45, 2026092109, "upper body, slight high angle, looking down, eyes lowered",
     "slight look-down, high angle"),
    ("10-hands-pockets", 0.52, 2026092110, "half body, hands in jacket pockets, casual stance, front view",
     "hands in jacket pockets, half body"),
    ("11-jacket-closed", 0.48, 2026092111, "upper body, jacket more closed, front view, looking at viewer",
     "jacket more closed, front view"),
    ("12-full-standing", 0.55, 2026092112, "full body, standing, full figure visible, front three-quarter view",
     "full body, standing"),
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
    for i in range(tries):
        try:
            get(f"{SERVER}/system_stats", 3)
            print("comfy_up", flush=True)
            return
        except Exception:
            time.sleep(2)
    raise SystemExit("Comfy 8188 not up")


def graph(input_name: str, pos: str, seed: int, denoise: float, tag: str):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoadImage", "inputs": {"image": input_name}},
        "3": {"class_type": "VAEEncode", "inputs": {"pixels": ["2", 0], "vae": ["1", 2]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["1", 1]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["1", 1]}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0],
            "positive": ["4", 0], "negative": ["5", 0],
            "latent_image": ["3", 0],
            "seed": seed, "steps": STEPS, "cfg": CFG,
            "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": denoise,
        }},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {
            "images": ["7", 0], "filename_prefix": f"charb-jacket-expand/{tag}",
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
    text = f"charb_jacket, {BASE}, {extra}"
    path.write_text(text + "\n", encoding="utf-8")


def main():
    if not SEED_SRC.is_file():
        raise SystemExit(f"missing seed {SEED_SRC}")
    COMFY_INPUT.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    XFER.mkdir(parents=True, exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)

    # Ensure seed caption exists
    seed_txt = OUT_DIR / "01-seed.txt"
    if not seed_txt.is_file():
        write_caption(seed_txt, "upper body, three-quarter view, looking at viewer")

    input_name = "charb-jacket-01-seed.png"
    shutil.copy2(SEED_SRC, COMFY_INPUT / input_name)

    wait_server()
    results = []
    for stem, denoise, seed, prompt_extra, cap_extra in JOBS:
        dest = OUT_DIR / f"{stem}.png"
        if dest.is_file() and dest.stat().st_size > 1000:
            print("skip_existing", dest.name, flush=True)
            results.append({"stem": stem, "status": "skip"})
            continue
        pos = f"{BASE}, {prompt_extra}"
        print(f"run {stem} denoise={denoise}", flush=True)
        entry = queue_wait(graph(input_name, pos, seed, denoise, stem))
        outs = entry.get("outputs") or {}
        saved = False
        for node in outs.values():
            for im in node.get("images") or []:
                if "charb-jacket-expand" not in (im.get("subfolder") or "") and "charb" not in im.get("filename", ""):
                    # still accept SaveImage from our prefix via filename
                    pass
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
            raise SystemExit(f"no image for {stem}: {json.dumps(outs)[:500]}")
        results.append({"stem": stem, "status": "ok", "path": str(dest)})
        try_free()

    pngs = sorted(OUT_DIR.glob("*.png"))
    summary = {
        "ok": True,
        "png_count": len(pngs),
        "out_dir": str(OUT_DIR),
        "xfer": str(XFER),
        "results": results,
    }
    (OUT_DIR.parent.parent.parent / "EXPAND-RUN.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (XFER / "EXPAND-RUN.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()

