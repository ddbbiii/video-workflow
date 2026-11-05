# -*- coding: utf-8 -*-
"""v4 follow-up: Chengwu+jacket (J1-J3) and Chengwu+hoodie-male (H1-H3).
Same style IPA + dual masked face IPA recipe as sweater v4.
"""
from __future__ import annotations
import json, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
CKPT = "animagine-xl-4.0-opt.safetensors"
CHENGWU = "chengwu-sdxl-v1b.safetensors"
JACKET = "charb-jacket-sdxl-v1b.safetensors"
HOODIE = "charb-hoodie-male-sdxl-v1.safetensors"
HOME = "jiaoli-home-sdxl-v1.safetensors"
IPA_STYLE = "ip-adapter-plus_sdxl_vit-h.safetensors"
IPA_FACE = "ip-adapter-plus-face_sdxl_vit-h.safetensors"
CLIPV = "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"

CW_SM, CW_SC = 0.78, 0.72
SP_SM, SP_SC = 0.72, 0.66  # supporting char
HM_SM, HM_SC = 0.70, 0.62
STYLE_W, STYLE_END = 0.22, 0.55
FACE_W, FACE_END = 0.70, 0.85
STEPS, CFG = 28, 5.3

COMFY_INPUT_CANDIDATES = [
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input"),
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\ComfyUI_windows_portable\ComfyUI\input"),
]
STYLE_CANDIDATES = [
    Path(r"E:\program\1project\video\xfer\refs-for-grok\style-prev-N2.png"),
    Path(r"E:\program\1project\video\xfer\overnight-2026-09-21\K2-half-living-day-out-1-2026092502.png"),
    Path(r"E:\program\1project\video\xfer\home-char-smoke\K2-out.png"),
]
CW_FACE_CANDIDATES = [
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input\chengwu_identity_upperbody_A.png"),
    Path(r"E:\program\1project\video\xfer\refs-for-grok\chengwu-face.png"),
]
JK_FACE_CANDIDATES = [
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input\v4-face-jacket.png"),
    Path(r"E:\program\1project\video\xfer\charb-jacket-smoke-stylelock-v2\V2-SL1-front-half.png"),
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input\soft-init-jacket-02-front-face.png"),
]
HD_FACE_CANDIDATES = [
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input\v4-face-hoodie-male.png"),
    Path(r"E:\program\1project\video\xfer\soft-continue-2026-09-22\smoke\charb_hoodie_male\M1-front-half.png"),
    Path(r"E:\program\1project\video\xfer\soft-continue-2026-09-22\smoke\charb_hoodie_male_consistency\C01-front-half.png"),
]

OUT = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\keyframes-2026-09-23\chengwu-jacket-hoodie-v4")
XFER = Path(r"E:\program\1project\video\xfer\keyframes-2026-09-23\chengwu-jacket-hoodie-v4")

STYLE_TAGS = (
    "anime style, masterpiece, best quality, soft cel shading, clean lineart, "
    "flat color, soft lighting, consistent 2d anime illustration, young adult"
)
CW = (
    "chengwu, 程雾, young adult woman on the LEFT, short grey-blue bob hair above shoulders, "
    "NO ponytail, NO bun, brown eyes, pale cool skin, thin black choker with silver ring, "
    "teal long-sleeve scoop-neck top showing a little collarbone"
)
JK = (
    "charb_jacket, young adult woman on the RIGHT, DIFFERENT face from left, "
    "dark brown or black medium-long hair, no grey-blue hair, no short bob, "
    "dark casual jacket over shirt, NO choker, NO teal clothes, NO cream turtleneck sweater"
)
HD = (
    "charb_hoodie_male, 1boy, young adult man on the RIGHT, DIFFERENT face from left, "
    "short-to-medium dark hair, masculine jaw, oversized hoodie, "
    "NO female, NO choker, NO teal scoop, NO grey-blue bob, NO long straight black hair with red clip"
)
SCENE = (
    "jiaoli_home, indoor home interior, living room, soft home atmosphere, "
    "readable two-person composition, clear left-right separation"
)
NEG_BASE = (
    "loli, child, baby face, chibi, overly cute childish face, identical twins, same face, "
    "matching faces, both short bob, both chokers, both teal clothes, "
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, cropped, "
    "worst quality, low quality, jpeg artifacts, signature, watermark, blurry, "
    "photorealistic, solo, three people, crowd, western comic, 3d render, harsh rim light"
)
NEG_JK = NEG_BASE + ", 1boy, male, hoodie, cream turtleneck"
NEG_HD = NEG_BASE + ", 2girls, both female, feminine man, girl on the right, cream turtleneck, red hair clip"

JOBS = [
    ("jacket", "J1-living-night", 2026092391, 1152, 896,
     f"2girls, two young adult women standing side by side, left and right clearly distinct, "
     f"left: {CW}, right: {JK}, both looking at viewer, "
     f"{SCENE}, night, sofa, floor lamp, city lights through window, {STYLE_TAGS}"),
    ("jacket", "J2-living-day-talk", 2026092392, 1152, 896,
     f"2girls, two young adult women facing slightly toward each other talking, "
     f"left: {CW}, right: {JK}, "
     f"{SCENE}, daytime, soft daylight, window, {STYLE_TAGS}"),
    ("jacket", "J3-window-day", 2026092393, 1152, 896,
     f"2girls, two young adult women by the window, half body, "
     f"left: {CW}, right: {JK}, looking at viewer, "
     f"{SCENE}, daytime, soft daylight, {STYLE_TAGS}"),
    ("hoodie", "H1-living-night", 2026092394, 1152, 896,
     f"1girl 1boy, young adult woman and young adult man standing side by side, clearly distinct, "
     f"left: {CW}, right: {HD}, both looking at viewer, "
     f"{SCENE}, night, sofa, floor lamp, city lights through window, {STYLE_TAGS}"),
    ("hoodie", "H2-sofa-sit", 2026092395, 1152, 896,
     f"1girl 1boy, woman and man sitting on sofa, "
     f"left: {CW}, right: {HD}, "
     f"{SCENE}, night, warm lamp light, {STYLE_TAGS}"),
    ("hoodie", "H3-doorway", 2026092396, 896, 1152,
     f"1girl 1boy, woman and man near doorway, "
     f"front-left: {CW}, behind-right: {HD}, "
     f"{SCENE}, night, hallway to living room, {STYLE_TAGS}"),
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


def graph(pos, neg, seed, w, h, tag, style_img, cw_face, sp_face, support_lora):
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
            "lora_name": support_lora, "strength_model": SP_SM, "strength_clip": SP_SC,
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
        "15": {"class_type": "LoadImage", "inputs": {"image": sp_face}},
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
            "weight": FACE_W,
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
            "weight": FACE_W,
            "weight_type": "linear",
            "combine_embeds": "concat",
            "start_at": 0.0,
            "end_at": FACE_END,
            "embeds_scaling": "V only",
            "attn_mask": ["27", 0],
        }},
        "40": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["4", 1]}},
        "41": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["4", 1]}},
        "42": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "43": {"class_type": "KSampler", "inputs": {
            "model": ["31", 0], "positive": ["40", 0], "negative": ["41", 0],
            "latent_image": ["42", 0],
            "seed": seed, "steps": STEPS, "cfg": CFG,
            "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": 1.0,
        }},
        "44": {"class_type": "VAEDecode", "inputs": {"samples": ["43", 0], "vae": ["1", 2]}},
        "45": {"class_type": "SaveImage", "inputs": {
            "images": ["44", 0], "filename_prefix": f"kf-cw-jh-v4/{tag}",
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
    comfy_input.mkdir(parents=True, exist_ok=True)

    style_src = first_existing(STYLE_CANDIDATES)
    cw_src = first_existing(CW_FACE_CANDIDATES)
    jk_src = first_existing(JK_FACE_CANDIDATES)
    hd_src = first_existing(HD_FACE_CANDIDATES)
    if not style_src or not cw_src or not jk_src or not hd_src:
        raise SystemExit(f"missing refs style={style_src} cw={cw_src} jk={jk_src} hd={hd_src}")

    style_img = stage_into_input(style_src, comfy_input, "v4-style-k2.png")
    cw_face = stage_into_input(cw_src, comfy_input, "v4-face-chengwu.png")
    jk_face = stage_into_input(jk_src, comfy_input, "v4-face-jacket.png")
    hd_face = stage_into_input(hd_src, comfy_input, "v4-face-hoodie-male.png")
    print("style", style_src, "cw", cw_src, "jk", jk_src, "hd", hd_src, flush=True)

    saved = []
    for kind, tag, seed, w, h, pos in JOBS:
        if kind == "jacket":
            support, sp_face, neg = JACKET, jk_face, NEG_JK
        else:
            support, sp_face, neg = HOODIE, hd_face, NEG_HD
        print(f"run {tag} {w}x{h} lora={support}", flush=True)
        hist = queue_wait(graph(pos, neg, seed, w, h, tag, style_img, cw_face, sp_face, support))
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
        "phase": "v4-chengwu-jacket-hoodie",
        "style_ref": str(style_src),
        "cw_face": str(cw_src),
        "jacket_face": str(jk_src),
        "hoodie_face": str(hd_src),
        "recipe": {
            "style_ipa": STYLE_W,
            "face_ipa_masked": FACE_W,
            "loras": {
                "chengwu": [CW_SM, CW_SC],
                "support": [SP_SM, SP_SC],
                "home": [HM_SM, HM_SC],
                "jacket_file": JACKET,
                "hoodie_file": HOODIE,
            },
        },
        "files": saved,
        "xfer": str(XFER),
    }
    (OUT / "last-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    shutil.copy2(OUT / "last-report.json", XFER / "last-report.json")
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
