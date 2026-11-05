"""Chengwu LoRA outfit-swap smoke on ComfyUI 8188."""
import json, time, urllib.request, uuid
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
CKPT = "animagine-xl-4.0-opt.safetensors"
LORA = "chengwu-sdxl-v1-000010.safetensors"
OUT_PREFIX = "chengwu-lora-smoke/outfit"

OUTFITS = [
    ("hoodie", "chengwu, 1girl, short grey-blue bob hair, brown eyes, pale skin, black choker with silver ring, oversized beige hoodie, casual, upper body, three-quarter view, looking at viewer, anime style, masterpiece, best quality"),
    ("school", "chengwu, 1girl, short grey-blue bob hair, brown eyes, pale skin, black choker with silver ring, white shirt, dark navy school blazer, plaid skirt, upper body, looking at viewer, anime style, masterpiece, best quality"),
    ("dress", "chengwu, 1girl, short grey-blue bob hair, brown eyes, pale skin, black choker with silver ring, simple black sleeveless dress, upper body, looking at viewer, anime style, masterpiece, best quality"),
    ("coat", "chengwu, 1girl, short grey-blue bob hair, brown eyes, pale skin, black choker with silver ring, long grey trench coat over turtleneck, upper body, looking at viewer, anime style, masterpiece, best quality"),
]
NEG = "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, jpeg artifacts, signature, watermark, blurry, loli, child, teal shirt, cyan top"


def queue(prompt):
    data = json.dumps({"prompt": prompt, "client_id": str(uuid.uuid4())}).encode()
    req = urllib.request.Request(f"{SERVER}/prompt", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["prompt_id"]


def wait(pid, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        with urllib.request.urlopen(f"{SERVER}/history/{pid}", timeout=30) as r:
            hist = json.loads(r.read())
        if pid in hist:
            return hist[pid]
        time.sleep(2)
    raise TimeoutError(pid)


def graph(pos, seed, w=832, h=1216):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoraLoader", "inputs": {
            "model": ["1", 0], "clip": ["1", 1],
            "lora_name": LORA, "strength_model": 0.85, "strength_clip": 0.75,
        }},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["2", 1]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["2", 1]}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["2", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0],
            "seed": seed, "steps": 28, "cfg": 5.5, "sampler_name": "euler_ancestral",
            "scheduler": "normal", "denoise": 1.0,
        }},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": f"{OUT_PREFIX}-{seed}"}},
    }


def main():
    for _ in range(30):
        try:
            urllib.request.urlopen(f"{SERVER}/system_stats", timeout=3)
            break
        except Exception:
            time.sleep(2)
    else:
        raise SystemExit("ComfyUI not up")

    results = []
    for i, (tag, pos) in enumerate(OUTFITS):
        seed = 53000 + i
        pid = queue(graph(pos, seed))
        print(f"queued {tag} {pid}", flush=True)
        hist = wait(pid)
        for o in hist.get("outputs", {}).values():
            for im in o.get("images", []):
                results.append({"tag": tag, **im})
                print("saved", tag, im, flush=True)
    Path(r"E:\program\1project\video\shared\project-tools\lora\chengwu-v1\smoke\outfit-smoke.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print("DONE", results)


if __name__ == "__main__":
    main()
