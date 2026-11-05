"""Dual LoRA smoke: Chengwu ep10 + jiaoli_home on ComfyUI 8188. Serial, no browser."""
import json, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
CKPT = "animagine-xl-4.0-opt.safetensors"
CHAR_LORA = "chengwu-sdxl-v1-000010.safetensors"
SCENE_LORA = "jiaoli-home-sdxl-v1.safetensors"
CHAR_SM, CHAR_SC = 0.88, 0.82
SCENE_SM, SCENE_SC = 0.78, 0.70
STEPS, CFG = 28, 5.3
OUT_DIR = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\home-char-smoke")
XFER = Path(r"E:\program\1project\video\xfer\home-char-smoke")
PREFIX = "home-char-smoke"

CHAR = (
    "chengwu, 程雾, 1girl, young adult, short grey-blue bob hair, brown eyes, pale skin, "
    "thin black choker with silver ring, teal long-sleeve scoop-neck top, anime style, "
    "masterpiece, best quality"
)
NEG = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, "
    "cropped, worst quality, low quality, jpeg artifacts, signature, watermark, blurry, "
    "loli, child, photorealistic, extra people, crowd, multiple girls, deformed face"
)
SHOTS = [
    ("A-living-night-3q", 2026092001, 832, 1216,
     f"{CHAR}, upper body, three-quarter view, looking at viewer, jiaoli_home, indoor home interior, living room, night, sofa, floor lamp, city lights through window, cozy atmosphere"),
    ("B-living-day-half", 2026092002, 832, 1216,
     f"{CHAR}, half body, standing, looking at viewer, jiaoli_home, indoor home interior, living room, daytime, sofa, window, soft daylight"),
    ("C-sitting-reading", 2026092003, 832, 1216,
     f"{CHAR}, sitting, reading a book, looking down slightly, jiaoli_home, indoor home interior, bedroom or living room, soft indoor light, cozy home"),
    ("D-living-night-alt", 2026092004, 896, 1152,
     f"{CHAR}, upper body, side three-quarter, slight smile, looking at viewer, jiaoli_home, indoor home interior, living room, night, warm lamp light, city night window"),
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
    raise SystemExit("ComfyUI not up on 8188")


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
    pid = post(f"{SERVER}/prompt", {"prompt": g, "client_id": str(uuid.uuid4())})["prompt_id"]
    print(f"queued {pid}", flush=True)
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
    url = f"{SERVER}/view?{q}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as r:
        dest.write_bytes(r.read())
    return dest


def try_free():
    try:
        post(f"{SERVER}/free", {"unload_models": True, "free_memory": True}, 30)
        time.sleep(2)
    except Exception:
        pass


def main():
    wait_server()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    XFER.mkdir(parents=True, exist_ok=True)
    results = []
    for tag, seed, w, h, pos in SHOTS:
        print(f"=== {tag} seed={seed} {w}x{h} ===", flush=True)
        hist = queue_wait(graph(pos, seed, w, h, tag))
        imgs = []
        for o in hist.get("outputs", {}).values():
            imgs.extend(o.get("images", []))
        if not imgs:
            raise SystemExit(f"no images for {tag}")
        dest = OUT_DIR / f"home-char-{tag}-{seed}.png"
        download(imgs[0], dest)
        xfer = XFER / dest.name
        shutil.copy2(dest, xfer)
        print("saved", dest, "->", xfer, flush=True)
        results.append({"tag": tag, "seed": seed, "path": str(dest), "xfer": str(xfer), "meta": imgs[0]})
        try_free()
    report = {
        "ok": True,
        "char_lora": CHAR_LORA, "scene_lora": SCENE_LORA,
        "strengths": {"char": [CHAR_SM, CHAR_SC], "scene": [SCENE_SM, SCENE_SC]},
        "ckpt": CKPT, "steps": STEPS, "cfg": CFG,
        "results": results,
    }
    (OUT_DIR / "last-smoke.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    shutil.copy2(OUT_DIR / "last-smoke.json", XFER / "last-smoke.json")
    print("DONE", json.dumps(results, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
