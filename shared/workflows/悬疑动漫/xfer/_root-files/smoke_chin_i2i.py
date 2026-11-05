"""Mild img2img chin soften on existing Chengwu face refs for LoRA supplement."""
import json, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
CKPT = "animagine-xl-4.0-opt.safetensors"
CHAR_LORA = "chengwu-sdxl-v1-000010.safetensors"
# Lower LoRA so prompt can soften jaw without full identity rewrite
CHAR_SM, CHAR_SC = 0.72, 0.65
STEPS, CFG, DENOISE = 28, 5.0, 0.38
IN_DIR = Path(r"E:\program\1project\video\xfer\chin-soft-in")
OUT_DIR = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\home-char-smoke\chin-soft-out")
XFER = Path(r"E:\program\1project\video\xfer\home-char-smoke")
COMFY_INPUT = Path(r"E:\program\1project\video\shared\project-tools\production\comfyui-input")

POS = (
    "chengwu, 程雾, 1girl, young adult, short grey-blue bob hair, brown eyes, pale skin, "
    "soft jawline, slightly rounded chin, gentle oval face, soft U-shaped jaw, "
    "thin black choker with silver ring, teal long-sleeve scoop-neck top, "
    "anime style, masterpiece, best quality, same character, subtle change only"
)
NEG = (
    "sharp chin, pointed chin, V-shaped face, angular jaw, fox face, overly pointed jaw, "
    "lowres, bad anatomy, blurry, watermark, loli, child, different person, face drift"
)

JOBS = [
    ("01-style-lock.png", "soft-01-style", 2026092301),
    ("08-face-front.png", "soft-08-front", 2026092302),
    ("14-face-choker.png", "soft-14-choker", 2026092303),
    ("09-half-3q.png", "soft-09-half", 2026092304),
]


def get(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def post(url, obj, timeout=120):
    data = json.dumps(obj).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def wait_server():
    for _ in range(40):
        try:
            get(f"{SERVER}/system_stats", 3)
            return
        except Exception:
            time.sleep(2)
    raise SystemExit("Comfy down")


def graph(img_name, seed, tag):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoraLoader", "inputs": {
            "model": ["1", 0], "clip": ["1", 1],
            "lora_name": CHAR_LORA, "strength_model": CHAR_SM, "strength_clip": CHAR_SC,
        }},
        "3": {"class_type": "LoadImage", "inputs": {"image": img_name}},
        "4": {"class_type": "VAEEncode", "inputs": {"pixels": ["3", 0], "vae": ["1", 2]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": POS, "clip": ["2", 1]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["2", 1]}},
        "7": {"class_type": "KSampler", "inputs": {
            "model": ["2", 0], "positive": ["5", 0], "negative": ["6", 0], "latent_image": ["4", 0],
            "seed": seed, "steps": STEPS, "cfg": CFG, "sampler_name": "euler_ancestral",
            "scheduler": "normal", "denoise": DENOISE,
        }},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["1", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {
            "images": ["8", 0], "filename_prefix": f"chin-soft/{tag}-{seed}",
        }},
    }


def queue_wait(g):
    resp = post(f"{SERVER}/prompt", {"prompt": g, "client_id": str(uuid.uuid4())})
    if resp.get("node_errors"):
        raise SystemExit(str(resp["node_errors"]))
    pid = resp["prompt_id"]
    print("queued", pid, flush=True)
    t0 = time.time()
    while time.time() - t0 < 600:
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


def main():
    wait_server()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    XFER.mkdir(parents=True, exist_ok=True)
    for src_name, tag, seed in JOBS:
        src = IN_DIR / src_name
        if not src.exists():
            raise SystemExit(f"missing {src}")
        dst_in = COMFY_INPUT / src_name
        shutil.copy2(src, dst_in)
        print("===", tag, "===", flush=True)
        hist = queue_wait(graph(src_name, seed, tag))
        imgs = []
        for o in hist.get("outputs", {}).values():
            imgs.extend(o.get("images", []))
        if not imgs:
            raise SystemExit("no img " + tag)
        dest = OUT_DIR / f"{tag}.png"
        download(imgs[0], dest)
        shutil.copy2(dest, XFER / dest.name)
        print("saved", dest, flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
