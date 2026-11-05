# -*- coding: utf-8 -*-
"""Male hoodie LoRA smoke — NO Chengwu female stylelock; identity-first."""
from __future__ import annotations
import json, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
CKPT = "animagine-xl-4.0-opt.safetensors"
LORA = "charb-hoodie-male-sdxl-v1.safetensors"
LORA_SM, LORA_SC = 0.80, 0.75
OUT = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\charb-hoodie-male-consistency")
XFER = Path(r"E:\program\1project\video\xfer\soft-continue-2026-09-22\smoke\charb_hoodie_male_consistency")
STEPS, CFG = 28, 5.5

POS_BASE = (
    "charb_hoodie_male, 1boy, solo, young adult man, male, masculine face, defined jawline, "
    "short black hair, messy layered short hair, bangs, warm brown eyes, "
    "fair skin with warm undertone, dark navy hoodie with drawstrings, no hair accessories, "
    "soft cel shading, soft lighting, clean soft lineart, masterpiece, best quality, "
    "simple soft grey background"
)
NEG = (
    "1girl, woman, female, feminine face, soft round jaw, lipstick, makeup, hair clip, hairpin, "
    "red hair clip, long eyelashes exaggerated, loli, child, "
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, "
    "cropped, worst quality, low quality, jpeg artifacts, signature, watermark, blurry, "
    "photorealistic, extra people, multiple boys, deformed face, pink hair, grey-blue hair"
)

JOBS = [
    ("C01-front-half", 2026092321, 896, 1152, "half body, front view, looking at viewer, neutral expression"),
    ("C02-3q-smile", 2026092322, 896, 1152, "upper body, three-quarter view, slight smile, looking at viewer"),
    ("C03-profile", 2026092323, 896, 1152, "upper body, strict side profile facing left, only one eye visible, masculine profile"),
    ("C04-overshoulder", 2026092324, 896, 1152, "upper body, looking back over shoulder, three-quarter rear view"),
    ("C05-lookup", 2026092325, 896, 1152, "upper body, slight low angle, looking up, chin raised a little"),
    ("C06-downcast", 2026092326, 896, 1152, "upper body, slight high angle, looking down, eyes lowered"),
    ("C07-hands-pocket", 2026092327, 896, 1152, "half body, both hands in hoodie front pocket, casual stance, front view"),
    ("C08-arms-crossed", 2026092328, 896, 1152, "half body, arms crossed, front view, looking at viewer"),
    ("C09-sitting", 2026092329, 896, 1152, "upper body, sitting pose, leaning forward a little, looking at viewer"),
    ("C10-walking", 2026092330, 832, 1216, "full body, walking toward viewer, natural stride, simple shoes"),
    ("C11-full-stand", 2026092331, 832, 1216, "full body, standing straight, arms relaxed at sides, front three-quarter, simple shoes"),
    ("C12-crouch", 2026092332, 832, 1216, "full body, slight crouch, hands on knees, looking at viewer, simple shoes"),
]


def get(url, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def post(url, obj, timeout=180):
    data = json.dumps(obj).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def wait_server(n=90):
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
            "images": ["7", 0], "filename_prefix": f"charb-hoodie-male-consistency/{tag}",
        }},
    }


def queue_wait(g):
    resp = post(f"{SERVER}/prompt", {"prompt": g, "client_id": str(uuid.uuid4())})
    if resp.get("node_errors"):
        raise SystemExit("node_errors " + json.dumps(resp["node_errors"], ensure_ascii=False))
    pid = resp["prompt_id"]
    print("queued", pid, flush=True)
    t0 = time.time()
    while time.time() - t0 < 700:
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
    for tag, seed, w, h, extra in JOBS:
        pos = f"{POS_BASE}, {extra}"
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
    summary = {
        "ok": True,
        "lora": LORA,
        "lora_strength": [LORA_SM, LORA_SC],
        "no_ipa": True,
        "files": saved,
        "xfer": str(XFER),
    }
    (XFER / "SMOKE-MALE-CONSISTENCY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
