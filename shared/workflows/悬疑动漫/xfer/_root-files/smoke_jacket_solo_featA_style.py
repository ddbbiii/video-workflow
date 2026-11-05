# -*- coding: utf-8 -*-
"""Jacket Plan A solo r4: stack style-suspense-rainnight LoRA on r3 recipe.
r1: full V2-SL1 IPA@0.70 -> short grey bob FAIL
r2: facecrop@0.55 still bob FAIL
r3: facecrop@0.35 jacket 0.72/0.50 cfg6.5 — hair ok, style generic
r4: + style LoRA 0.65/0.55, trigger sks_suspense_rainnight; Style IPA OFF; Face IPA 0.40
"""
from __future__ import annotations
import json, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
CKPT = "animagine-xl-4.0-opt.safetensors"
JACKET = "charb-jacket-sdxl-v1b.safetensors"
HOME = "jiaoli-home-sdxl-v1.safetensors"
STYLE = "style-suspense-rainnight-sdxl-v1.safetensors"
IPA_FACE = "ip-adapter-plus-face_sdxl_vit-h.safetensors"
CLIPV = "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"

# r4 weights (recipe jacket-solo + style stack)
JK_SM, JK_SC = 0.72, 0.50
HM_SM, HM_SC = 0.40, 0.35
ST_SM, ST_SC = 0.65, 0.55
# Style IPA OFF — style LoRA carries grade; avoid dual-style fight
USE_STYLE_IPA = False
STYLE_IPA_W, STYLE_IPA_END = 0.0, 0.40
FACE_W, FACE_END = 0.40, 0.70
STEPS, CFG = 30, 6.5

COMFY_INPUT = Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input")
JK_FACE = Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input\v4-face-jacket-V2-SL1-facecrop.png")
OUT = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\jacket-solo-featA-style")
XFER = Path(r"E:\program\1project\video\xfer\jacket-solo-featA-style")
LOG = OUT / "run.log"

STYLE_TAGS = (
    "sks_suspense_rainnight, dark semi-realistic anime, cool cyan-black grade, "
    "soft volumetric light, film still, masterpiece, best quality, "
    "clear readable face and hair"
)

HAIR = (
    "(long hair:1.5), (very long hair:1.35), (hair past shoulders:1.45), "
    "(shoulder-length hair:1.4), (medium long hair:1.3), "
    "(dark brown hair:1.35), (black hair:1.2), (brown hair:1.15), "
    "(side part:1.25), (wavy hair:1.25), (soft waves:1.2), "
    "(bangs:1.2), (thin bangs:1.15), (sidelocks:1.1)"
)

JK = (
    f"charb_jacket, 1girl, solo, young adult woman, {HAIR}, "
    "slightly mature oval face, defined jawline, longer midface, "
    "warm amber brown eyes, small silver stud earrings, "
    "(dark grey casual jacket:1.3), (black jacket:1.2), jacket over white inner shirt, "
    "NO choker, NO short hair, NO bob cut, NO grey-blue hair"
)

NEG = (
    "short hair, short bob, bob cut, chin-length hair, hair above shoulders, "
    "grey-blue hair, ash blue hair, blue-grey hair, cool grey hair, "
    "black choker, choker, teal top, cyan top, baby face, loli, child, "
    "white jacket, cream turtleneck, red hairclip, pink hair streak, "
    "identical twins, foggy face, scanlines, blurry, lowres, bad anatomy, "
    "2girls, male, photorealistic, 3d render, watermark, "
    "bright cheerful daylight, colorful pop anime, pure cel flat 2d candy color"
)

JOBS = [
    ("r4-A1-front-half", 2026092971, 896, 1152,
     f"1girl, solo, front view half body portrait looking at viewer, {JK}, "
     f"clean indoor, soft cool frontal light, cool cyan-black grade, {STYLE_TAGS}"),
    ("r4-A2-3q-half", 2026092972, 896, 1152,
     f"1girl, solo, three-quarter view half body looking at viewer, {JK}, "
     f"clean indoor, soft cool side light, cool cyan-black grade, {STYLE_TAGS}"),
    ("r4-A3-window-stand", 2026092973, 896, 1152,
     f"1girl, solo, standing by window, half body knee-up looking at viewer, {JK}, "
     f"jiaoli_home, cool window light, soft volumetric light, {STYLE_TAGS}"),
    ("r4-A4-sofa-sit", 2026092974, 1152, 896,
     f"1girl, solo, sitting on sofa half body looking at viewer, {JK}, "
     f"jiaoli_home, night cool lamp, living room, cool cyan-black grade, {STYLE_TAGS}"),
]


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    try:
        OUT.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def get(url, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def post(url, obj, timeout=180):
    data = json.dumps(obj).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def stage(src: Path, name: str) -> str:
    COMFY_INPUT.mkdir(parents=True, exist_ok=True)
    dest = COMFY_INPUT / name
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)
    return name


def graph(pos, seed, w, h, tag, jk_face):
    # Chain: ckpt -> jacket -> home -> style LoRA -> Face IPA -> sample
    g = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoraLoader", "inputs": {
            "model": ["1", 0], "clip": ["1", 1],
            "lora_name": JACKET, "strength_model": JK_SM, "strength_clip": JK_SC,
        }},
        "3": {"class_type": "LoraLoader", "inputs": {
            "model": ["2", 0], "clip": ["2", 1],
            "lora_name": HOME, "strength_model": HM_SM, "strength_clip": HM_SC,
        }},
        "4": {"class_type": "LoraLoader", "inputs": {
            "model": ["3", 0], "clip": ["3", 1],
            "lora_name": STYLE, "strength_model": ST_SM, "strength_clip": ST_SC,
        }},
        "11": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": IPA_FACE}},
        "12": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": CLIPV}},
        "14": {"class_type": "LoadImage", "inputs": {"image": jk_face}},
        "30": {"class_type": "IPAdapterAdvanced", "inputs": {
            "model": ["4", 0], "ipadapter": ["11", 0], "image": ["14", 0],
            "clip_vision": ["12", 0], "weight": FACE_W, "weight_type": "linear",
            "combine_embeds": "concat", "start_at": 0.0, "end_at": FACE_END,
            "embeds_scaling": "V only",
        }},
        "40": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["4", 1]}},
        "41": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["4", 1]}},
        "42": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "43": {"class_type": "KSampler", "inputs": {
            "model": ["30", 0], "positive": ["40", 0], "negative": ["41", 0],
            "latent_image": ["42", 0], "seed": seed, "steps": STEPS, "cfg": CFG,
            "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": 1.0,
        }},
        "44": {"class_type": "VAEDecode", "inputs": {"samples": ["43", 0], "vae": ["1", 2]}},
        "45": {"class_type": "SaveImage", "inputs": {
            "images": ["44", 0], "filename_prefix": f"kf-jk-solo-featA-style/{tag}",
        }},
    }
    return g


def queue_wait(g):
    resp = post(f"{SERVER}/prompt", {"prompt": g, "client_id": str(uuid.uuid4())})
    if resp.get("node_errors"):
        raise SystemExit("node_errors " + json.dumps(resp["node_errors"], ensure_ascii=False))
    pid = resp["prompt_id"]
    log(f"queued {pid}")
    t0 = time.time()
    while time.time() - t0 < 1200:
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
    if LOG.exists():
        LOG.write_text("", encoding="utf-8")
    log("r4 start jacket-solo-featA-style")

    for _ in range(60):
        try:
            get(f"{SERVER}/system_stats", 3)
            break
        except Exception:
            time.sleep(2)
    else:
        raise SystemExit("Comfy down")

    if not JK_FACE.exists():
        raise SystemExit(f"missing face ref {JK_FACE}")

    jk_face = stage(JK_FACE, "v4-face-jacket-V2-SL1-facecrop.png")
    weights = {
        "lora_style": [ST_SM, ST_SC],
        "lora_jacket": [JK_SM, JK_SC],
        "lora_home": [HM_SM, HM_SC],
        "style_ipa": STYLE_IPA_W if USE_STYLE_IPA else 0.0,
        "face_ipa": FACE_W,
        "face_ipa_end": FACE_END,
        "steps": STEPS,
        "cfg": CFG,
        "sampler": "euler_ancestral",
        "trigger": "sks_suspense_rainnight",
        "face_ref": "v4-face-jacket-V2-SL1-facecrop.png",
        "style_lora_file": STYLE,
    }
    log(f"weights {json.dumps(weights)}")

    results = []
    for tag, seed, w, h, pos in JOBS:
        log(f"run {tag} seed={seed} {w}x{h}")
        hist = queue_wait(graph(pos, seed, w, h, tag, jk_face))
        imgs = []
        for o in hist.get("outputs", {}).values():
            imgs.extend(o.get("images", []))
        if not imgs:
            raise SystemExit(f"no images {tag}")
        dest = OUT / f"{tag}.png"
        download(imgs[0], dest)
        shutil.copy2(dest, XFER / dest.name)
        log(f"saved {dest} size={dest.stat().st_size}")
        results.append({
            "file": dest.name,
            "path": str(dest),
            "xfer": str(XFER / dest.name),
            "seed": seed,
            "size": [w, h],
            "tag": tag,
            "pose": tag.split("-", 2)[-1] if "-" in tag else tag,
        })
        try_free()

    summary = {
        "ok": True,
        "phase": "jacket-solo-featA-style",
        "date": "2026-09-29",
        "plan": "A",
        "round": "r4",
        "history": {
            "r1": "FAIL hair — full V2-SL1 IPA@0.70 locked short grey bob",
            "r2": "FAIL hair — facecrop@0.55 still chin/neck bob",
            "r3": "facecrop@0.35 jacket 0.72/0.50 cfg6.5 — hair ok, style generic anime",
            "r4": "stack style LoRA 0.65/0.55 + trigger; Style IPA OFF; Face IPA facecrop@0.40",
        },
        "weights": weights,
        "candidates": results,
        "out": str(OUT),
        "xfer": str(XFER),
        "featA_checklist": {
            "hair_past_shoulders_not_bob": "PENDING_VISUAL",
            "dark_brown_black_not_greyblue": "PENDING_VISUAL",
            "thin_or_side_bangs": "PENDING_VISUAL",
            "small_silver_stud_earrings": "PENDING_VISUAL",
            "slightly_mature_oval_face": "PENDING_VISUAL",
            "no_choker_dark_jacket": "PENDING_VISUAL",
        },
        "style_vs_r3": "PENDING_VISUAL — expect cooler cyan-black semi-realistic vs r3 generic soft cel",
        "recommended_anchor": "PENDING_VISUAL — prefer r4-A1 or r4-A2 if hair+face pass",
        "notes": [
            "Style IPA disabled to avoid fighting style LoRA",
            "Indoor makeup OK; style grade from LoRA+trigger, not forced rain night set",
            "Do not delete r3 outputs; this is a new directory",
            "GPU lock owned by main agent — do not release here",
        ],
    }
    report = OUT / "REPORT.json"
    report.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    shutil.copy2(report, XFER / "REPORT.json")
    log(f"REPORT written {report}")
    log("DONE r4")
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
