"""Compare Chengwu v1b vs v1-ep10 — same prompts, focus chin naturalness. No scene LoRA."""
import json, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
CKPT = "animagine-xl-4.0-opt.safetensors"
LORAS = [
    ("v1", "chengwu-sdxl-v1-000010.safetensors"),
    ("v1b", "chengwu-sdxl-v1b.safetensors"),
]
SM, SC = 0.88, 0.82
STEPS, CFG = 28, 5.3
OUT_DIR = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\home-char-smoke\v1b-compare")
XFER = Path(r"E:\program\1project\video\xfer\home-char-smoke")
PREFIX = "chengwu-v1b-cmp"

# Neutral prompts — do NOT push soft/sharp chin; let LoRA speak
POS_A = (
    "chengwu, 程雾, 1girl, young adult, short grey-blue bob hair, brown eyes, pale skin, "
    "thin black choker with silver ring, teal long-sleeve scoop-neck top, "
    "anime style, masterpiece, best quality, upper body, three-quarter view, looking at viewer, "
    "simple light background"
)
POS_B = (
    "chengwu, 程雾, 1girl, young adult, short grey-blue bob hair, brown eyes, pale skin, "
    "thin black choker with silver ring, teal long-sleeve scoop-neck top, "
    "anime style, masterpiece, best quality, face close-up, front view, looking at viewer, "
    "simple light background"
)
NEG = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, cropped, worst quality, "
    "low quality, jpeg artifacts, signature, watermark, blurry, loli, child, photorealistic, "
    "extra people, deformed face"
)
SHOTS = [
    ("A-3q", 2026092401, 832, 1216, POS_A),
    ("B-front", 2026092402, 832, 1216, POS_B),
]


def get(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def post(url, obj, timeout=120):
    data = json.dumps(obj).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def wait_server(n=60):
    for _ in range(n):
        try:
            get(f"{SERVER}/system_stats", 3)
            return
        except Exception:
            time.sleep(2)
    raise SystemExit("ComfyUI not up")


def graph(lora, pos, seed, w, h, tag):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoraLoader", "inputs": {
            "model": ["1", 0], "clip": ["1", 1],
            "lora_name": lora, "strength_model": SM, "strength_clip": SC,
        }},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["2", 1]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["2", 1]}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["2", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0],
            "seed": seed, "steps": STEPS, "cfg": CFG, "sampler_name": "euler_ancestral",
            "scheduler": "normal", "denoise": 1.0,
        }},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {
            "images": ["7", 0], "filename_prefix": f"{PREFIX}/{tag}-{seed}",
        }},
    }


def queue_wait(g):
    resp = post(f"{SERVER}/prompt", {"prompt": g, "client_id": str(uuid.uuid4())})
    if resp.get("node_errors"):
        raise SystemExit(str(resp["node_errors"]))
    pid = resp["prompt_id"]
    print("queued", pid, flush=True)
    t0 = time.time()
    while time.time() - t0 < 900:
        hist = get(f"{SERVER}/history/{pid}")
        if pid in hist:
            return hist[pid]
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


def main():
    wait_server()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    XFER.mkdir(parents=True, exist_ok=True)
    results = []
    for ver, lora in LORAS:
        for tag, seed, w, h, pos in SHOTS:
            name = f"{ver}-{tag}"
            print("===", name, lora, "===", flush=True)
            hist = queue_wait(graph(lora, pos, seed, w, h, name))
            imgs = []
            for o in hist.get("outputs", {}).values():
                imgs.extend(o.get("images", []))
            if not imgs:
                raise SystemExit("no img " + name)
            dest = OUT_DIR / f"{name}-{seed}.png"
            download(imgs[0], dest)
            shutil.copy2(dest, XFER / dest.name)
            print("saved", dest, flush=True)
            results.append(str(dest))
            try_free()
    print("DONE", results, flush=True)


if __name__ == "__main__":
    main()
