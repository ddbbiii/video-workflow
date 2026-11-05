# -*- coding: utf-8 -*-
"""r2: 程雾短发/青绿稳住，仍弱提示，禁止 v4b 硬分离。补 H2/H3/H6 + 两张新构图。"""
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

# r2: 抬程雾稳住短发，卫衣男略抬；左脸 IPA 略高
CW_SM, CW_SC = 0.84, 0.78
HD_SM, HD_SC = 0.76, 0.70
HM_SM, HM_SC = 0.68, 0.58
STYLE_W, STYLE_END = 0.18, 0.50
FACE_L, FACE_R = 0.78, 0.68
FACE_END = 0.85
STEPS, CFG = 28, 5.3

COMFY_INPUT_CANDIDATES = [
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input"),
]
STYLE_CANDIDATES = [
    Path(r"E:\program\1project\video\xfer\refs-for-grok\style-prev-N2.png"),
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input\v4-style-k2.png"),
]
CW_FACE_CANDIDATES = [
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input\chengwu_identity_upperbody_A.png"),
]
HD_FACE_CANDIDATES = [
    Path(r"E:\program\1project\video\xfer\soft-continue-2026-09-22\smoke\charb_hoodie_male\M1-front-half.png"),
]

OUT = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\chengwu-hoodie-male-v1-sameframe")
XFER = Path(r"E:\program\1project\video\xfer\keyframes-2026-09-28\chengwu-hoodie-male-v1")

STYLE_TAGS = (
    "anime style, masterpiece, best quality, soft cel shading, clean lineart, "
    "flat color, soft lighting, consistent 2d anime illustration, young adult, "
    "sharp facial details, clear eyes, no scanlines, no fog"
)
CW = (
    "chengwu, 程雾, young woman on the LEFT, SHORT grey-blue bob hair ABOVE shoulders, "
    "chin-length bob, NO long hair, NO ponytail, brown eyes, pale cool skin, "
    "thin black choker with silver ring, teal long-sleeve scoop-neck top, NOT wearing hoodie"
)
HD = (
    "charb_hoodie_male, young man on the RIGHT, messy short black hair, "
    "light brown eyes, oversized dark charcoal hoodie with drawstrings, "
    "NO grey-blue hair, NO choker, NO teal clothes"
)
SCENE = (
    "jiaoli_home, indoor home interior, living room, soft home atmosphere, "
    "readable two-person composition, clear left-right separation, shared room"
)
NEG = (
    "identical twins, same face, matching faces, long hair on left, long straight hair, "
    "ponytail, both short bob, both grey-blue hair, both teal clothes, both chokers, "
    "both hoodies, clothing swap, woman wearing hoodie, man with short grey-blue bob, "
    "man with choker, man in teal top, split screen, diptych, panel border, "
    "loli, child, baby face, chibi, lowres, bad anatomy, bad hands, text, error, "
    "missing fingers, extra digit, cropped, worst quality, low quality, jpeg artifacts, "
    "signature, watermark, blurry, foggy face, scanlines, grey haze, "
    "photorealistic, solo, three people, crowd, western comic, 3d render, harsh rim light"
)

JOBS = [
    ("R2-H2-living-day", 2026092812, 1152, 896,
     f"1girl 1boy, young woman and young man standing side by side talking, "
     f"left: {CW}, right: {HD}, "
     f"{SCENE}, daytime, soft daylight, window, sofa, {STYLE_TAGS}"),
    ("R2-H3-sofa", 2026092813, 1152, 896,
     f"1girl 1boy, young woman and young man sitting on sofa side by side, "
     f"left: {CW}, right: {HD}, half body, "
     f"{SCENE}, night, warm floor lamp, {STYLE_TAGS}"),
    ("R2-H6-living-night", 2026092816, 1152, 896,
     f"1girl 1boy, two people standing together in one living room, "
     f"left: {CW}, right: {HD}, looking at viewer, "
     f"{SCENE}, night, sofa, floor lamp, city lights through window, {STYLE_TAGS}"),
    ("R2-H7-window-close", 2026092817, 1152, 896,
     f"1girl 1boy, young woman and young man by the window, half body close, "
     f"left: {CW}, right: {HD}, looking at viewer, "
     f"{SCENE}, daytime, soft daylight, curtains, {STYLE_TAGS}"),
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
    half = w // 2
    right_w = w - half
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
            "mask": ["22", 0], "left": 0, "top": 0, "right": 48, "bottom": 0,
        }},
        "24": {"class_type": "SolidMask", "inputs": {"value": 0.0, "width": w, "height": h}},
        "25": {"class_type": "SolidMask", "inputs": {"value": 1.0, "width": right_w, "height": h}},
        "26": {"class_type": "MaskComposite", "inputs": {
            "destination": ["24", 0], "source": ["25", 0], "x": half, "y": 0, "operation": "add",
        }},
        "27": {"class_type": "FeatherMask", "inputs": {
            "mask": ["26", 0], "left": 48, "top": 0, "right": 0, "bottom": 0,
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
            "images": ["44", 0], "filename_prefix": f"kf-cw-hd-v1-r2/{tag}",
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

    style_img = stage_into_input(style_src, comfy_input, "v4-style-k2.png")
    cw_face = stage_into_input(cw_src, comfy_input, "v4-face-chengwu.png")
    hd_face = stage_into_input(hd_src, comfy_input, "v1-face-hoodie-male-M1.png")
    print("r2 style", style_src, "cw", cw_src, "hd", hd_src, flush=True)
    print("weights cw", CW_SM, CW_SC, "hd", HD_SM, HD_SC, "faceL/R", FACE_L, FACE_R, flush=True)

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
        "phase": "chengwu-hoodie-male-v1-weak-r2",
        "hoodie_lora": HOODIE,
        "chengwu_lora": CHENGWU,
        "recipe": {
            "style_ipa": STYLE_W,
            "face_ipa_L_R": [FACE_L, FACE_R],
            "loras": {"chengwu": [CW_SM, CW_SC], "hoodie_male_v1": [HD_SM, HD_SC], "home": [HM_SM, HM_SC]},
        },
        "files": saved,
    }
    (OUT / "last-report-r2.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    shutil.copy2(OUT / "last-report-r2.json", XFER / "last-report-r2.json")
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
