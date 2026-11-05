# -*- coding: utf-8 -*-
"""Char B jacket smoke with Chengwu style lock (IPAdapter style transfer + softer LoRA)."""
from __future__ import annotations
import json, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
CKPT = "animagine-xl-4.0-opt.safetensors"
LORA = "charb-sweater-sdxl-v1.safetensors"
# Softer so base + style adapter dominate look
LORA_SM, LORA_SC = 0.72, 0.68
IPA = "ip-adapter-plus_sdxl_vit-h.safetensors"
CLIPV = "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
STYLE_SRC = Path(r"E:\program\1project\video\xfer\overnight-2026-09-21\K2-half-living-day-out-1-2026092502.png")
COMFY_INPUT = Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input")
OUT = Path(r"E:\\program\\1project\\video\\shared\\work\\scratch\\legacy-numbered\\charb-sweater-smoke")
XFER = Path(r"E:\\program\\1project\\video\\xfer\\overnight-2026-09-22\\smoke\\charb_sweater")
STEPS, CFG = 28, 5.3  # match Chengwu keyframe smoke
IPA_W = 0.35

STYLE_TAGS = (
    "anime style, masterpiece, best quality, soft cel shading, clean lineart, "
    "flat color, soft lighting, consistent 2d anime illustration"
)
NEG = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, "
    "cropped, worst quality, low quality, jpeg artifacts, signature, watermark, blurry, "
    "loli, child, photorealistic, realistic skin texture, pores, glossy plastic skin, "
    "extra people, crowd, multiple girls, deformed face, western comic, 3d render, grey-blue hair, blue hair, teal hair, silver hair, "
    "harsh rim light, oversharpened, oily leather shine"
)
CHAR = (
    f"charb_sweater, 1girl, solo, young adult woman, short black hair, jet black hair, black bob cut, bangs, "
    f"red hair clip, dark brown eyes, pale skin, cream knit sweater, soft sweater, {STYLE_TAGS}, "
    f"hair color is pure black, not grey, not blue, not teal"
)
JOBS = [
    ("V2-SL1-front-half", 2026092151, 896, 1152,
     f"{CHAR}, half body, front view, looking at viewer, plain soft grey background"),
    ("V2-SL2-3q", 2026092152, 896, 1152,
     f"{CHAR}, upper body, three-quarter view, looking at viewer, plain soft grey background"),
    ("V2-SL3-full", 2026092153, 832, 1216,
     f"{CHAR}, full body, standing, looking at viewer, plain soft grey background, simple shoes"),
    ("V2-SL4-profile", 2026092154, 896, 1152,
     f"{CHAR}, upper body, side profile, looking ahead, plain soft grey background"),
]


def get(url, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def post(url, obj, timeout=180):
    data = json.dumps(obj).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def wait_server(n=40):
    for _ in range(n):
        try:
            get(f"{SERVER}/system_stats", 3)
            return
        except Exception:
            time.sleep(2)
    raise SystemExit("Comfy down")


def graph(pos, seed, w, h, tag, style_name):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoraLoader", "inputs": {
            "model": ["1", 0], "clip": ["1", 1],
            "lora_name": LORA, "strength_model": LORA_SM, "strength_clip": LORA_SC,
        }},
        "3": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": IPA}},
        "4": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": CLIPV}},
        "5": {"class_type": "LoadImage", "inputs": {"image": style_name}},
        "6": {"class_type": "IPAdapterAdvanced", "inputs": {
            "model": ["2", 0],
            "ipadapter": ["3", 0],
            "image": ["5", 0],
            "weight": IPA_W,
            "weight_type": "style transfer",
            "combine_embeds": "concat",
            "start_at": 0.0,
            "end_at": 0.70,
            "embeds_scaling": "V only",
            "clip_vision": ["4", 0],
        }},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["2", 1]}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["2", 1]}},
        "9": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "10": {"class_type": "KSampler", "inputs": {
            "model": ["6", 0], "positive": ["7", 0], "negative": ["8", 0],
            "latent_image": ["9", 0], "seed": seed, "steps": STEPS, "cfg": CFG,
            "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": 1.0,
        }},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["1", 2]}},
        "12": {"class_type": "SaveImage", "inputs": {
            "images": ["11", 0], "filename_prefix": f"charb-sweater-smoke/{tag}",
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
    if not STYLE_SRC.is_file():
        # fallback candidates
        cands = list(Path(r"E:\program\1project\video\xfer\overnight-2026-09-21").glob("K2*.png"))
        cands += list(Path(r"E:\program\1project\video\xfer").glob("**/K2-half*.png"))
        if not cands:
            raise SystemExit(f"missing style ref {STYLE_SRC}")
        style = cands[0]
    else:
        style = STYLE_SRC
    COMFY_INPUT.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    XFER.mkdir(parents=True, exist_ok=True)
    style_name = "chengwu-style-lock-ref.png"
    shutil.copy2(style, COMFY_INPUT / style_name)
    print("style_ref", style, flush=True)

    wait_server()
    saved = []
    for tag, seed, w, h, pos in JOBS:
        print("run", tag, flush=True)
        entry = queue_wait(graph(pos, seed, w, h, tag, style_name))
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
        "ipa_weight": IPA_W,
        "ipa_weight_type": "style transfer",
        "style_ref": str(style),
        "cfg": CFG,
        "files": saved,
        "xfer": str(XFER),
    }
    (XFER / "SMOKE-STYLELOCK-SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()


