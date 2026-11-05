# -*- coding: utf-8 -*-
"""Phase A: male hoodie FULL-BODY proportion fix.
No Chengwu female stylelock. No IPA. Same identity recipe as liked male smoke,
but full-body at ~2:3 (768x1152 primary; also 576x864) + stronger body prompts.
"""
from __future__ import annotations
import json, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
CKPT = "animagine-xl-4.0-opt.safetensors"
LORA = "charb-hoodie-male-sdxl-v1.safetensors"
LORA_SM, LORA_SC = 0.80, 0.75
OUT = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\charb-hoodie-male-fullbody-fix")
XFER = Path(r"E:\program\1project\video\xfer\soft-continue-2026-09-22\smoke\charb_hoodie_male_fullbody_fix")
BEST = Path(r"E:\program\1project\video\xfer\keyframes-2026-09-23\male-fullbody-fix-best")
STEPS, CFG = 28, 5.5

# ~2:3 like Chengwu K1 skinny fix direction; wider than ultra-narrow.
# 768x1152 = exact 2:3, SDXL-friendly; 576x864 kept as explicit contract size.
W_MAIN, H_MAIN = 768, 1152
W_ALT, H_ALT = 576, 864

BODY_POS = (
    "natural male body proportions, athletic but natural build, balanced silhouette, "
    "thicker thighs, fuller calves, solid lower body matching oversized hoodie volume, "
    "coordinated full body, proper leg thickness, masculine legs, not skinny"
)
POS_BASE = (
    "charb_hoodie_male, 1boy, solo, young adult man, male, masculine face, defined jawline, "
    "short black hair, messy layered short hair, bangs, warm brown eyes, "
    "fair skin with warm undertone, dark navy oversized hoodie with drawstrings, "
    "dark slim-but-not-skinny pants, simple dark shoes, no hair accessories, "
    f"{BODY_POS}, "
    "soft cel shading, soft lighting, clean soft lineart, masterpiece, best quality, "
    "simple soft grey background"
)
NEG = (
    "1girl, woman, female, feminine face, soft round jaw, lipstick, makeup, hair clip, hairpin, "
    "red hair clip, long eyelashes exaggerated, loli, child, "
    "skinny legs, thin lower body, needle legs, stick legs, stilts, chicken legs, "
    "disproportionate, tiny legs, spindly legs, top-heavy awkward silhouette, "
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, "
    "cropped, worst quality, low quality, jpeg artifacts, signature, watermark, blurry, "
    "photorealistic, extra people, multiple boys, deformed face, pink hair, grey-blue hair"
)

# 6 full-body poses: walk (user #5), stand, crouch, walk-side, pocket-full, lean
JOBS = [
    ("F01-walk-768", 2026092330, W_MAIN, H_MAIN,
     "full body, walking toward viewer, natural stride, one hand in pocket, simple shoes"),
    ("F02-stand-768", 2026092331, W_MAIN, H_MAIN,
     "full body, standing straight, arms relaxed at sides, front three-quarter, simple shoes"),
    ("F03-crouch-768", 2026092332, W_MAIN, H_MAIN,
     "full body, slight crouch, hands on knees, looking at viewer, simple shoes"),
    ("F04-walk-side-768", 2026092340, W_MAIN, H_MAIN,
     "full body, walking to the side, profile-ish stride, natural gait, simple shoes"),
    ("F05-pocket-full-768", 2026092341, W_MAIN, H_MAIN,
     "full body, standing, both hands in hoodie front pocket, casual stance, front view, simple shoes"),
    ("F06-walk-576", 2026092342, W_ALT, H_ALT,
     "full body, walking toward viewer, natural stride, simple shoes"),
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
            "images": ["7", 0], "filename_prefix": f"charb-hoodie-male-fullbody-fix/{tag}",
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
    BEST.mkdir(parents=True, exist_ok=True)
    wait_server()
    saved = []
    for tag, seed, w, h, extra in JOBS:
        pos = f"{POS_BASE}, {extra}"
        print("run", tag, w, h, flush=True)
        entry = queue_wait(graph(pos, seed, w, h, tag))
        for node in (entry.get("outputs") or {}).values():
            for im in node.get("images") or []:
                dest = OUT / f"{tag}.png"
                download(im, dest)
                shutil.copy2(dest, XFER / dest.name)
                # stage likely review picks
                if tag.startswith(("F01-", "F02-", "F03-", "F05-")):
                    shutil.copy2(dest, BEST / dest.name)
                saved.append(str(dest))
                print("saved", dest, flush=True)
                break
        try_free()
    summary = {
        "ok": True,
        "phase": "A-fullbody-fix",
        "lora": LORA,
        "lora_strength": [LORA_SM, LORA_SC],
        "no_ipa": True,
        "no_chengwu_stylelock": True,
        "sizes": {"main": f"{W_MAIN}x{H_MAIN}", "alt": f"{W_ALT}x{H_ALT}"},
        "steps": STEPS, "cfg": CFG,
        "files": saved,
        "xfer": str(XFER),
        "best": str(BEST),
        "recipe_delta": "832x1216 -> 768x1152 (~2:3) + body proportion pos/neg; one 576x864 walk",
    }
    (XFER / "SMOKE-MALE-FULLBODY-FIX.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (BEST / "SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
