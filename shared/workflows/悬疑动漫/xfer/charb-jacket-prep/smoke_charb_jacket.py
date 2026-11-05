# -*- coding: utf-8 -*-
"""Smoke定妆: charb-jacket-sdxl-v1 alone (no scene LoRA)."""
from __future__ import annotations
import json, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
CKPT = "animagine-xl-4.0-opt.safetensors"
LORA = "charb-jacket-sdxl-v1.safetensors"
LORA_SM, LORA_SC = 0.90, 0.85
STEPS, CFG = 28, 5.5
OUT = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\charb-jacket-smoke")
XFER = Path(r"E:\program\1project\video\xfer\charb-jacket-smoke")
NEG = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, "
    "cropped, worst quality, low quality, jpeg artifacts, signature, watermark, blurry, "
    "loli, child, photorealistic, extra people, multiple girls, deformed face, long hair, blonde"
)
CHAR = (
    "charb_jacket, 1girl, solo, young adult woman, short hair, black hair, bob cut, bangs, "
    "red hair clip, dark eyes, pale skin, black oversized jacket, white t-shirt, anime style, "
    "masterpiece, best quality"
)
JOBS = [
    ("S1-front-half", 2026092131, 896, 1152,
     f"{CHAR}, half body, front view, looking at viewer, simple grey background"),
    ("S2-3q", 2026092132, 896, 1152,
     f"{CHAR}, upper body, three-quarter view, looking at viewer, simple grey background"),
    ("S3-full", 2026092133, 832, 1216,
     f"{CHAR}, full body, standing, looking at viewer, simple indoor lighting, plain background"),
    ("S4-profile", 2026092134, 896, 1152,
     f"{CHAR}, upper body, side profile, looking ahead, simple grey background"),
]


def get(url, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def post(url, obj, timeout=180):
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
    raise SystemExit("Comfy down")


def graph(pos, seed, w, h, tag):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoraLoader", "inputs": {
            "model": ["1", 0], "clip": ["1", 1],
            "lora_name": LORA, "strength_model": LORA_SM, "strength_clip": LORA_SC,
        }},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["2", 1]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["2", 1]}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["2", 0], "positive": ["3", 0], "negative": ["4", 0],
            "latent_image": ["5", 0], "seed": seed, "steps": STEPS, "cfg": CFG,
            "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": 1.0,
        }},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {
            "images": ["7", 0], "filename_prefix": f"charb-jacket-smoke/{tag}",
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


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    XFER.mkdir(parents=True, exist_ok=True)
    wait_server()
    saved = []
    for tag, seed, w, h, pos in JOBS:
        print("run", tag, flush=True)
        entry = queue_wait(graph(pos, seed, w, h, tag))
        for node in (entry.get("outputs") or {}).values():
            for im in node.get("images") or []:
                dest = OUT / f"{tag}.png"
                download(im, dest)
                shutil.copy2(dest, XFER / dest.name)
                saved.append(str(dest))
                print("saved", dest, flush=True)
                break
        try_free()
    summary = {"ok": True, "lora": LORA, "strength": [LORA_SM, LORA_SC], "files": saved, "xfer": str(XFER)}
    (XFER / "SMOKE-SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
