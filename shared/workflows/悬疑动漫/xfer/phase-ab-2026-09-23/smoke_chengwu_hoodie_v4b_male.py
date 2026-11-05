# -*- coding: utf-8 -*-
"""v4b: Chengwu + hoodie male — hard gender/identity separation.
Fixes: face collapse toward Chengwu + feminine body.
Asymmetric LoRA + face IPA; stronger 1boy body prompts.
"""
from __future__ import annotations
import json, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
CKPT = "animagine-xl-4.0-opt.safetensors"
CHENGWU = "chengwu-sdxl-v1b.safetensors"
HOODIE = "charb-hoodie-male-sdxl-v1.safetensors"
HOME = "jiaoli-home-sdxl-v1.safetensors"
IPA_STYLE = "ip-adapter-plus_sdxl_vit-h.safetensors"
IPA_FACE = "ip-adapter-plus-face_sdxl_vit-h.safetensors"
CLIPV = "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"

# Asymmetric: lower Chengwu bleed, raise male
CW_SM, CW_SC = 0.58, 0.52
HD_SM, HD_SC = 0.88, 0.82
HM_SM, HM_SC = 0.55, 0.48
STYLE_W, STYLE_END = 0.14, 0.45
FACE_L, FACE_R = 0.55, 0.85
FACE_END = 0.90
STEPS, CFG = 30, 5.0

COMFY_INPUT_CANDIDATES = [
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input"),
]
STYLE_CANDIDATES = [
    Path(r"E:\program\1project\video\xfer\refs-for-grok\style-prev-N2.png"),
]
CW_FACE_CANDIDATES = [
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input\chengwu_identity_upperbody_A.png"),
]
HD_FACE_CANDIDATES = [
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input\v4b-face-hoodie-male.png"),
    Path(r"E:\program\1project\video\xfer\soft-continue-2026-09-22\smoke\charb_hoodie_male\M1-front-half.png"),
    Path(r"E:\program\1project\video\xfer\soft-continue-2026-09-22\smoke\charb_hoodie_male\M3-full.png"),
]

OUT = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\keyframes-2026-09-23\chengwu-hoodie-v4b-male")
XFER = Path(r"E:\program\1project\video\xfer\keyframes-2026-09-23\chengwu-hoodie-v4b-male")

STYLE_TAGS = (
    "anime style, masterpiece, best quality, soft cel shading, clean lineart, "
    "flat color, soft lighting, consistent 2d anime illustration"
)
CW = (
    "chengwu, 程雾, 1girl, young adult WOMAN on the LEFT, short grey-blue bob hair ABOVE shoulders, "
    "NO ponytail, brown eyes, pale cool skin, thin black choker with silver ring, "
    "teal long-sleeve scoop-neck top, feminine slim build, shorter than the man"
)
HD = (
    "charb_hoodie_male, 1boy, young adult MAN on the RIGHT, CLEARLY MALE, "
    "DIFFERENT face from the woman, messy short black hair, dark brown eyes, "
    "angular male jaw, broader shoulders, flat chest, masculine proportions, taller than the woman, "
    "oversized dark charcoal hoodie with drawstrings, male body, NO breasts, NO feminine waist, "
    "NO grey-blue hair, NO short bob, NO choker, NO teal clothes"
)
SCENE = (
    "jiaoli_home, indoor home interior, living room, soft home atmosphere, "
    "clear left-right separation, woman left man right"
)
NEG = (
    "identical twins, same face, matching faces, both female, 2girls, girl on the right, "
    "feminine man, soft pretty boy identical to left, cute girl face on man, "
    "feminine body, slim girl waist on man, breasts on right, small breasts, "
    "grey-blue hair on right, short bob on right, choker on right, teal clothes on right, "
    "clothing swap, woman wearing hoodie, man without hoodie, "
    "loli, child, chibi, lowres, bad anatomy, bad hands, text, error, "
    "missing fingers, extra digit, cropped, worst quality, low quality, jpeg artifacts, "
    "signature, watermark, blurry, photorealistic, solo, three people, crowd, "
    "western comic, 3d render, futa, trap, crossdressing"
)

JOBS = [
    ("H1b-living-night", 2026092401, 1152, 896,
     f"1girl 1boy, young adult woman and young adult man standing side by side, "
     f"man is taller and broader, left: {CW}, right: {HD}, both looking at viewer, "
     f"{SCENE}, night, sofa, floor lamp, city lights through window, {STYLE_TAGS}"),
    ("H2b-sofa-sit", 2026092402, 1152, 896,
     f"1girl 1boy, woman and man sitting on sofa, man broader shoulders, "
     f"left: {CW}, right: {HD}, "
     f"{SCENE}, night, warm lamp light, {STYLE_TAGS}"),
    ("H3b-standing-half", 2026092403, 1152, 896,
     f"1girl 1boy, two people standing half body side by side, clear gender difference, "
     f"left: {CW}, right: {HD}, man taller, "
     f"{SCENE}, daytime, soft daylight, window, {STYLE_TAGS}"),
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


def first_existing(paths):
    for p in paths:
        if p.exists():
            return p
    return None


def stage_into_input(src: Path, comfy_input: Path, name: str) -> str:
    comfy_input.mkdir(parents=True, exist_ok=True)
    dest = comfy_input / name
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)
    return name


def graph(pos, seed, w, h, tag, style_img, cw_face, hd_face):
    # tighter split: left 45% / right 55% to reduce center face bleed onto male
    half = int(w * 0.45)
    right_w = w - half
    feather = 24
    g = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoraLoader", "inputs": {
            "model": ["1", 0], "clip": ["1", 1],
            "lora_name": CHENGWU, "strength_model": CW_SM, "strength_clip": CW_SC,
        }},
        "3": {"class_type": "LoraLoader", "inputs": {
            "model": ["2", 0], "clip": ["2", 1],
            "lora_name": HOODIE, "strength_model": HD_SM, "strength_clip": HD_SC,
        }},
        "4": {"class_type": "LoraLoader", "inputs": {
            "model": ["3", 0], "clip": ["3", 1],
            "lora_name": HOME, "strength_model": HM_SM, "strength_clip": HM_SC,
        }},
        "10": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": IPA_STYLE}},
        "11": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": IPA_FACE}},
        "12": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": CLIPV}},
        "13": {"class_type": "LoadImage", "inputs": {"image": style_img}},
        "14": {"class_type": "LoadImage", "inputs": {"image": cw_face}},
        "15": {"class_type": "LoadImage", "inputs": {"image": hd_face}},
        "16": {"class_type": "IPAdapterAdvanced", "inputs": {
            "model": ["4", 0],
            "ipadapter": ["10", 0],
            "image": ["13", 0],
            "clip_vision": ["12", 0],
            "weight": STYLE_W,
            "weight_type": "style transfer",
            "combine_embeds": "concat",
            "start_at": 0.0,
            "end_at": STYLE_END,
            "embeds_scaling": "V only",
        }},
        "20": {"class_type": "SolidMask", "inputs": {"value": 0.0, "width": w, "height": h}},
        "21": {"class_type": "SolidMask", "inputs": {"value": 1.0, "width": half, "height": h}},
        "22": {"class_type": "MaskComposite", "inputs": {
            "destination": ["20", 0], "source": ["21", 0], "x": 0, "y": 0, "operation": "add",
        }},
        "23": {"class_type": "FeatherMask", "inputs": {
            "mask": ["22", 0], "left": 0, "top": 0, "right": feather, "bottom": 0,
        }},
        "24": {"class_type": "SolidMask", "inputs": {"value": 0.0, "width": w, "height": h}},
        "25": {"class_type": "SolidMask", "inputs": {"value": 1.0, "width": right_w, "height": h}},
        "26": {"class_type": "MaskComposite", "inputs": {
            "destination": ["24", 0], "source": ["25", 0], "x": half, "y": 0, "operation": "add",
        }},
        "27": {"class_type": "FeatherMask", "inputs": {
            "mask": ["26", 0], "left": feather, "top": 0, "right": 0, "bottom": 0,
        }},
        "30": {"class_type": "IPAdapterAdvanced", "inputs": {
            "model": ["16", 0],
            "ipadapter": ["11", 0],
            "image": ["14", 0],
            "clip_vision": ["12", 0],
            "weight": FACE_L,
            "weight_type": "linear",
            "combine_embeds": "concat",
            "start_at": 0.0,
            "end_at": FACE_END,
            "embeds_scaling": "V only",
            "attn_mask": ["23", 0],
        }},
        "31": {"class_type": "IPAdapterAdvanced", "inputs": {
            "model": ["30", 0],
            "ipadapter": ["11", 0],
            "image": ["15", 0],
            "clip_vision": ["12", 0],
            "weight": FACE_R,
            "weight_type": "linear",
            "combine_embeds": "concat",
            "start_at": 0.0,
            "end_at": FACE_END,
            "embeds_scaling": "V only",
            "attn_mask": ["27", 0],
        }},
        "40": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["4", 1]}},
        "41": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["4", 1]}},
        "42": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "43": {"class_type": "KSampler", "inputs": {
            "model": ["31", 0], "positive": ["40", 0], "negative": ["41", 0],
            "latent_image": ["42", 0],
            "seed": seed, "steps": STEPS, "cfg": CFG,
            "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": 1.0,
        }},
        "44": {"class_type": "VAEDecode", "inputs": {"samples": ["43", 0], "vae": ["1", 2]}},
        "45": {"class_type": "SaveImage", "inputs": {
            "images": ["44", 0], "filename_prefix": f"kf-cw-hd-v4b/{tag}",
        }},
    }
    return g


def queue_wait(g):
    resp = post(f"{SERVER}/prompt", {"prompt": g, "client_id": str(uuid.uuid4())})
    if resp.get("node_errors"):
        raise SystemExit("node_errors " + json.dumps(resp["node_errors"], ensure_ascii=False))
    pid = resp["prompt_id"]
    print("queued", pid, flush=True)
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
    wait_server()
    comfy_input = first_existing(COMFY_INPUT_CANDIDATES) or COMFY_INPUT_CANDIDATES[0]
    style_src = first_existing(STYLE_CANDIDATES)
    cw_src = first_existing(CW_FACE_CANDIDATES)
    hd_src = first_existing(HD_FACE_CANDIDATES)
    if not style_src or not cw_src or not hd_src:
        raise SystemExit(f"missing refs style={style_src} cw={cw_src} hd={hd_src}")

    # Prefer M1 portrait as male face lock
    m1 = Path(r"E:\program\1project\video\xfer\soft-continue-2026-09-22\smoke\charb_hoodie_male\M1-front-half.png")
    if m1.exists():
        hd_src = m1

    style_img = stage_into_input(style_src, comfy_input, "v4-style-k2.png")
    cw_face = stage_into_input(cw_src, comfy_input, "v4-face-chengwu.png")
    hd_face = stage_into_input(hd_src, comfy_input, "v4b-face-hoodie-male.png")
    print("style", style_src, "cw", cw_src, "hd", hd_src, flush=True)
    print("weights cw", CW_SM, "hd", HD_SM, "faceL", FACE_L, "faceR", FACE_R, "style", STYLE_W, flush=True)

    saved = []
    for tag, seed, w, h, pos in JOBS:
        print(f"run {tag} {w}x{h}", flush=True)
        hist = queue_wait(graph(pos, seed, w, h, tag, style_img, cw_face, hd_face))
        imgs = []
        for o in hist.get("outputs", {}).values():
            imgs.extend(o.get("images", []))
        if not imgs:
            raise SystemExit(f"no images {tag}")
        dest = OUT / f"{tag}.png"
        download(imgs[0], dest)
        shutil.copy2(dest, XFER / dest.name)
        print("saved", dest, flush=True)
        saved.append(str(dest))
        try_free()

    report = {
        "ok": True,
        "phase": "v4b-hoodie-male-hard-sep",
        "fix": "face-collapse-to-chengwu + feminine-body",
        "hoodie_face": str(hd_src),
        "recipe": {
            "style_ipa": STYLE_W,
            "face_ipa_L": FACE_L,
            "face_ipa_R": FACE_R,
            "loras": {"chengwu": [CW_SM, CW_SC], "hoodie_male": [HD_SM, HD_SC], "home": [HM_SM, HM_SC]},
            "mask_split": "45/55 feather24",
        },
        "files": saved,
        "xfer": str(XFER),
    }
    (OUT / "last-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    shutil.copy2(OUT / "last-report.json", XFER / "last-report.json")
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
