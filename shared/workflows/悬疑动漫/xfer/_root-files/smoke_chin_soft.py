"""Mild chin soften: same dual LoRA, soft jaw prompts, not a redesign."""
import json, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
CKPT = "animagine-xl-4.0-opt.safetensors"
CHAR_LORA = "chengwu-sdxl-v1-000010.safetensors"
SCENE_LORA = "jiaoli-home-sdxl-v1.safetensors"
# Keep close to prior smoke; slight bump char so face stays locked while jaw softens via prompt
CHAR_SM, CHAR_SC = 0.88, 0.80
SCENE_SM, SCENE_SC = 0.78, 0.70
STEPS, CFG = 28, 5.3
OUT_DIR = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\home-char-smoke")
XFER = Path(r"E:\program\1project\video\xfer\home-char-smoke")
PREFIX = "home-char-chin"

FACE = (
    "soft jawline, slightly rounded chin, oval face, gentle facial contours, "
    "not a sharp V-chin"
)
NEG = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, "
    "cropped, worst quality, low quality, jpeg artifacts, signature, watermark, blurry, "
    "loli, child, photorealistic, extra people, crowd, multiple girls, deformed face, "
    "sharp chin, pointed chin, V-shaped face, angular jaw, overly pointed jaw, fox face"
)

SHOTS = [
    ("C1-default-hair", 2026092201, 832, 1216,
     "chengwu, 程雾, 1girl, young adult, short grey-blue bob hair, brown eyes, pale skin, "
     f"{FACE}, thin black choker with silver ring, teal long-sleeve scoop-neck top, "
     "anime style, masterpiece, best quality, upper body, three-quarter view, looking at viewer, "
     "jiaoli_home, indoor home interior, living room, night, sofa, floor lamp, city lights"),
    ("C2-long-black", 2026092202, 832, 1216,
     "chengwu, 程雾, 1girl, young adult, long straight black hair, bangs, brown eyes, pale skin, "
     f"{FACE}, thin black choker with silver ring, teal long-sleeve scoop-neck top, "
     "anime style, masterpiece, best quality, upper body, looking at viewer, "
     "jiaoli_home, indoor home interior, living room, night, sofa, floor lamp, city lights"),
    ("C3-short-red", 2026092203, 832, 1216,
     "chengwu, 程雾, 1girl, young adult, short messy wine-red hair, brown eyes, pale skin, "
     f"{FACE}, thin black choker with silver ring, teal long-sleeve scoop-neck top, "
     "anime style, masterpiece, best quality, upper body, looking at viewer, "
     "jiaoli_home, indoor home interior, living room, night, sofa, floor lamp, city lights"),
]


def get(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def post(url, obj, timeout=120):
    data = json.dumps(obj).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def wait_server(n=30):
    for _ in range(n):
        try:
            get(f"{SERVER}/system_stats", 3)
            return
        except Exception:
            time.sleep(2)
    raise SystemExit("ComfyUI not up")


def graph(pos, seed, w, h, tag):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoraLoader", "inputs": {
            "model": ["1", 0], "clip": ["1", 1],
            "lora_name": CHAR_LORA, "strength_model": CHAR_SM, "strength_clip": CHAR_SC,
        }},
        "3": {"class_type": "LoraLoader", "inputs": {
            "model": ["2", 0], "clip": ["2", 1],
            "lora_name": SCENE_LORA, "strength_model": SCENE_SM, "strength_clip": SCENE_SC,
        }},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["3", 1]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["3", 1]}},
        "6": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "7": {"class_type": "KSampler", "inputs": {
            "model": ["3", 0], "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0],
            "seed": seed, "steps": STEPS, "cfg": CFG, "sampler_name": "euler_ancestral",
            "scheduler": "normal", "denoise": 1.0,
        }},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["1", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {
            "images": ["8", 0], "filename_prefix": f"{PREFIX}/{tag}-{seed}",
        }},
    }


def queue_wait(g, timeout=900):
    resp = post(f"{SERVER}/prompt", {"prompt": g, "client_id": str(uuid.uuid4())})
    if resp.get("node_errors"):
        raise SystemExit(str(resp["node_errors"]))
    pid = resp["prompt_id"]
    print("queued", pid, flush=True)
    t0 = time.time()
    while time.time() - t0 < timeout:
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
    for tag, seed, w, h, pos in SHOTS:
        print("===", tag, "===", flush=True)
        hist = queue_wait(graph(pos, seed, w, h, tag))
        imgs = []
        for o in hist.get("outputs", {}).values():
            imgs.extend(o.get("images", []))
        if not imgs:
            raise SystemExit("no image " + tag)
        dest = OUT_DIR / f"chin-{tag}-{seed}.png"
        download(imgs[0], dest)
        shutil.copy2(dest, XFER / dest.name)
        print("saved", dest, flush=True)
        try_free()
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
