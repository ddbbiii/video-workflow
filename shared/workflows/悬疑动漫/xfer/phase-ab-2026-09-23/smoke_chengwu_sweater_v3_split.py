# -*- coding: utf-8 -*-
"""Chengwu + sweater v3 SPLIT COMPOSITE — high audience recognition.
A) Solo identity locks (one char LoRA + strong face IPA; optional PuLID)
B) Same-frame via left/right solo panels + PIL paste + optional low-denoise unify
NO dual character LoRA on one pass. Images only. API queue only.
"""
from __future__ import annotations
import json, time, urllib.request, urllib.parse, uuid, shutil, traceback
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

SERVER = "http://127.0.0.1:8188"
CKPT = "animagine-xl-4.0-opt.safetensors"
CHENGWU_CANDS = [
    "chengwu-sdxl-v1b.safetensors",
    "chengwu-sdxl-v1b-000012.safetensors",
    "chengwu-sdxl-v1.safetensors",
]
SWEATER_CANDS = [
    "charb-sweater-sdxl-v1b.safetensors",
    "charb-sweater-sdxl-v1b-000012.safetensors",
    "charb-sweater-sdxl-v1.safetensors",
]
HOME_CANDS = [
    "jiaoli-home-sdxl-v1.safetensors",
    "jiaoli-home-sdxl-v1.0.safetensors",
]
IPA_FACE_CANDS = [
    "ip-adapter-plus-face_sdxl_vit-h.safetensors",
    "ip-adapter-plus-face_sdxl_vit-h.pth",
]
CLIPV_CANDS = [
    "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors",
]

# Solo lock strengths — strong identity
CW_SM, CW_SC = 0.85, 0.80
SW_SM, SW_SC = 0.85, 0.80
HM_SOLO_SM, HM_SOLO_SC = 0.50, 0.45
FACE_W_SOLO = 0.88
FACE_END_SOLO = 0.95
PULID_W = 0.90

# Unify pass — home only, soft faces, LOW denoise
HM_UNIFY_SM, HM_UNIFY_SC = 0.55, 0.50
FACE_W_UNIFY = 0.45
FACE_END_UNIFY = 0.70
UNIFY_DENOISE = 0.30

STEPS, CFG = 30, 5.2
SAMPLER, SCHED = "euler_ancestral", "normal"

COMFY_INPUT_CANDIDATES = [
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input"),
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\ComfyUI_windows_portable\ComfyUI\input"),
]
COMFY_OUTPUT_CANDIDATES = [
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\output"),
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\ComfyUI_windows_portable\ComfyUI\output"),
]

CW_FACE_CANDIDATES = [
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input\chengwu_identity_upperbody_A.png"),
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\ComfyUI_windows_portable\ComfyUI\input\chengwu_identity_upperbody_A.png"),
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input\v2-face-chengwu.png"),
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\ComfyUI_windows_portable\ComfyUI\input\v2-face-chengwu.png"),
    Path(r"E:\program\1project\video\xfer\upperbody-A-ref.png"),
    Path(r"E:\program\1project\video\xfer\51-identity-v4.png"),
    Path(r"E:\program\1project\video\xfer\home-char-smoke\K2-half-living-day-out-1-2026092502.png"),
]
SW_FACE_CANDIDATES = [
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input\charb-sweater-01-seed.png"),
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\ComfyUI_windows_portable\ComfyUI\input\charb-sweater-01-seed.png"),
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input\soft-init-sweater-02-front-face.png"),
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\ComfyUI_windows_portable\ComfyUI\input\soft-init-sweater-02-front-face.png"),
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input\v2-face-sweater.png"),
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\ComfyUI_windows_portable\ComfyUI\input\v2-face-sweater.png"),
    Path(r"E:\program\1project\video\xfer\overnight-2026-09-21\charB\02-sweater.png"),
]

OUT = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\keyframes-2026-09-23\chengwu-sweater-v3-split")
XFER = Path(r"E:\program\1project\video\xfer\keyframes-2026-09-23\chengwu-sweater-v3-split")
SOLOS = OUT / "solos"
XFER_SOLOS = XFER / "solos"
SCRATCH_SCRIPT_DIR = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\phase-ab-2026-09-23")
XFER_SCRIPT_DIR = Path(r"E:\program\1project\video\xfer\phase-ab-2026-09-23")

STYLE = (
    "anime style, masterpiece, best quality, soft cel shading, clean lineart, "
    "flat color, soft lighting, highly recognizable character design"
)

# Amplify visual signatures — bob vs long black + red clip
CW_SOLO = (
    "chengwu, 程雾, solo, 1girl, young adult woman, UNIQUE identity lock, "
    "cooler oval face, soft natural chin, pale cool skin, brown eyes, "
    "SHORT grey-blue bob hair cut ABOVE shoulders, chin-length bob, blunt bangs, "
    "NO ponytail, NO hair clip, NO red accessory, NO long hair, "
    "thin black choker with silver ring, teal scoop-neck top OK, clothes flexible, "
    "upper body portrait, looking at viewer"
)
SW_SOLO = (
    "charb_sweater, solo, 1girl, young adult woman, UNIQUE identity lock, "
    "warmer rounder cheeks, slightly sharper jaw, pale warm skin, dark brown eyes, "
    "LONGER jet-black hair past shoulders, shoulder-length or longer pure black hair, "
    "OBVIOUS bright red hair clip on one side, bangs, "
    "NO grey-blue hair, NO short bob, NO choker, NO teal clothes, "
    "cream cable-knit turtleneck sweater, upper body portrait, looking at viewer"
)

CW_HALF = (
    "chengwu, 程雾, young adult woman, cooler oval face, pale cool skin, brown eyes, "
    "SHORT grey-blue bob ABOVE shoulders, chin-length bob, NO ponytail, NO hair clip, "
    "thin black choker with silver ring, teal scoop OK, clothes flexible"
)
SW_HALF = (
    "charb_sweater, young adult woman, warmer rounder face, dark brown eyes, "
    "LONGER jet-black hair past shoulders, OBVIOUS bright red hair clip, "
    "cream cable sweater, NO choker, NO teal, NO grey-blue hair, NO short bob"
)

SCENE = (
    "jiaoli_home, indoor home interior, living room, soft home atmosphere, "
    "readable composition"
)

NEG_SOLO = (
    "2girls, twins, identical face, clone, lowres, bad anatomy, bad hands, text, error, "
    "missing fingers, extra digit, cropped, worst quality, low quality, jpeg artifacts, "
    "signature, watermark, blurry, loli, child, photorealistic, 3d render, boy, male, "
    "western comic, harsh rim light, fused face"
)
NEG_CW = NEG_SOLO + (
    ", ponytail, long hair, red hair clip, cream sweater, jet black hair, "
    "shoulder-length black hair, hair bun, hair clip"
)
NEG_SW = NEG_SOLO + (
    ", grey-blue hair, short bob, chin-length bob, black choker, teal top, "
    "scoop-neck teal, short hair above shoulders only"
)
NEG_JOINT = (
    "identical twins, same face, matching faces, lookalikes, clone sisters, "
    "same hairstyle both, both grey-blue hair, both black hair, both red hair clips, "
    "both chokers, both cream sweaters, both teal tops, fused faces, "
    "chengwu with long black hair, sweater girl with grey-blue bob, "
    "chengwu with red hair clip, sweater girl with black choker, "
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, "
    "cropped, worst quality, low quality, jpeg artifacts, signature, watermark, blurry, "
    "loli, child, photorealistic, 1girl, solo, three people, crowd, boy, male, hoodie, "
    "western comic, 3d render, harsh rim light"
)

# D1–D6 reuse v2 seeds/themes; full canvas then half panels
SCENES = [
    ("D1-living-night", 2026092361, 1152, 896, "night",
     "living room at night, sofa, floor lamp, city lights through window"),
    ("D2-living-day-talk", 2026092362, 1152, 896, "day",
     "living room daytime, two women facing slightly toward each other talking, soft daylight, window"),
    ("D3-sofa-sit", 2026092363, 1152, 896, "night",
     "two women sitting on sofa, night, warm lamp light"),
    ("D4-window-day", 2026092364, 1152, 896, "day",
     "two women by the window, half body, daytime soft daylight"),
    ("D5-doorway", 2026092365, 896, 1152, "night",
     "near doorway, hallway to living room, night"),
    ("D6-living-night-alt", 2026092366, 1152, 896, "night",
     "standing in living room, night, sofa, floor lamp"),
]

SOLO_JOBS_CW = [
    ("S-CW-01-upper", 2026092371, 768, 1152),
    ("S-CW-02-upper", 2026092372, 896, 1152),
]
SOLO_JOBS_SW = [
    ("S-SW-01-upper", 2026092381, 768, 1152),
    ("S-SW-02-upper", 2026092382, 896, 1152),
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
        if p and Path(p).exists():
            return Path(p)
    return None


def pick_from_list(available, candidates, label):
    if not available:
        return candidates[0]
    avail_l = {a.lower(): a for a in available}
    for c in candidates:
        if c.lower() in avail_l:
            return avail_l[c.lower()]
        # suffix / prefix fuzzy
        for a in available:
            al = a.lower()
            cl = c.lower().replace(".safetensors", "").replace(".pth", "")
            if al.startswith(cl) or cl in al:
                return a
    print(f"WARN {label}: none of {candidates} in list; using first candidate name", flush=True)
    return candidates[0]


def stage_into_input(src: Path, comfy_input: Path, name: str) -> str:
    comfy_input.mkdir(parents=True, exist_ok=True)
    dest = comfy_input / name
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)
    return name


def try_free():
    try:
        post(f"{SERVER}/free", {"unload_models": True, "free_memory": True}, 30)
        time.sleep(1.5)
    except Exception:
        pass


def queue_wait(g, timeout=1200):
    resp = post(f"{SERVER}/prompt", {"prompt": g, "client_id": str(uuid.uuid4())})
    if resp.get("node_errors"):
        raise RuntimeError("node_errors " + json.dumps(resp["node_errors"], ensure_ascii=False))
    if resp.get("error"):
        raise RuntimeError("prompt error " + json.dumps(resp["error"], ensure_ascii=False))
    pid = resp["prompt_id"]
    print("queued", pid, flush=True)
    t0 = time.time()
    while time.time() - t0 < timeout:
        hist = get(f"{SERVER}/history/{pid}")
        if pid in hist:
            entry = hist[pid]
            st = entry.get("status") or {}
            if st.get("status_str") == "error":
                raise RuntimeError("comfy error " + json.dumps(st.get("messages"), ensure_ascii=False))
            # drain queue check
            return entry
        # also check queue empty-ish
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


def images_from_hist(hist):
    imgs = []
    for o in hist.get("outputs", {}).values():
        imgs.extend(o.get("images", []))
    return imgs


def mirror(dest: Path, *extra_dirs: Path):
    for d in extra_dirs:
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dest, d / dest.name)


# ---------- graphs ----------

def graph_solo(pos, neg, seed, w, h, tag, lora_name, lora_sm, lora_sc,
               face_name, home_name, ipa_face, clipv, use_pulid=False, pulid_file=None):
    """Single character lock: char LoRA + home + strong face IPA (+ optional PuLID)."""
    g = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoraLoader", "inputs": {
            "model": ["1", 0], "clip": ["1", 1],
            "lora_name": lora_name, "strength_model": lora_sm, "strength_clip": lora_sc,
        }},
        "3": {"class_type": "LoraLoader", "inputs": {
            "model": ["2", 0], "clip": ["2", 1],
            "lora_name": home_name, "strength_model": HM_SOLO_SM, "strength_clip": HM_SOLO_SC,
        }},
        "10": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": ipa_face}},
        "11": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": clipv}},
        "12": {"class_type": "LoadImage", "inputs": {"image": face_name}},
        "40": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["3", 1]}},
        "41": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["3", 1]}},
        "42": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
    }
    model_src = ["3", 0]
    if use_pulid and pulid_file:
        g["50"] = {"class_type": "PulidModelLoader", "inputs": {"pulid_file": pulid_file}}
        g["51"] = {"class_type": "PulidInsightFaceLoader", "inputs": {"provider": "CUDA"}}
        g["52"] = {"class_type": "PulidEvaClipLoader", "inputs": {}}
        g["53"] = {"class_type": "ApplyPulid", "inputs": {
            "model": model_src,
            "pulid": ["50", 0],
            "eva_clip": ["52", 0],
            "face_analysis": ["51", 0],
            "image": ["12", 0],
            "method": "fidelity",
            "weight": PULID_W,
            "start_at": 0.0,
            "end_at": 1.0,
        }}
        model_src = ["53", 0]

    g["30"] = {"class_type": "IPAdapterAdvanced", "inputs": {
        "model": model_src,
        "ipadapter": ["10", 0],
        "image": ["12", 0],
        "clip_vision": ["11", 0],
        "weight": FACE_W_SOLO,
        "weight_type": "linear",
        "combine_embeds": "concat",
        "start_at": 0.0,
        "end_at": FACE_END_SOLO,
        "embeds_scaling": "V only",
    }}
    g["43"] = {"class_type": "KSampler", "inputs": {
        "model": ["30", 0], "positive": ["40", 0], "negative": ["41", 0],
        "latent_image": ["42", 0],
        "seed": seed, "steps": STEPS, "cfg": CFG,
        "sampler_name": SAMPLER, "scheduler": SCHED, "denoise": 1.0,
    }}
    g["44"] = {"class_type": "VAEDecode", "inputs": {"samples": ["43", 0], "vae": ["1", 2]}}
    g["45"] = {"class_type": "SaveImage", "inputs": {
        "images": ["44", 0], "filename_prefix": f"kf-cw-sw-v3/solos/{tag}",
    }}
    return g


def graph_panel(pos, neg, seed, w, h, tag, lora_name, lora_sm, lora_sc,
                face_name, home_name, ipa_face, clipv):
    """Half-canvas panel for one character in scene."""
    return graph_solo(pos, neg, seed, w, h, tag, lora_name, lora_sm, lora_sc,
                      face_name, home_name, ipa_face, clipv, use_pulid=False)


def graph_unify(pos, neg, seed, w, h, tag, composite_name, cw_face, sw_face,
                home_name, ipa_face, clipv, denoise=UNIFY_DENOISE):
    """Light img2img unify: ONLY home LoRA + soft dual face IPA with L/R masks."""
    half = w // 2
    right_w = w - half
    g = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoraLoader", "inputs": {
            "model": ["1", 0], "clip": ["1", 1],
            "lora_name": home_name, "strength_model": HM_UNIFY_SM, "strength_clip": HM_UNIFY_SC,
        }},
        "10": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": ipa_face}},
        "11": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": clipv}},
        "12": {"class_type": "LoadImage", "inputs": {"image": cw_face}},
        "13": {"class_type": "LoadImage", "inputs": {"image": sw_face}},
        "14": {"class_type": "LoadImage", "inputs": {"image": composite_name}},
        # left mask
        "20": {"class_type": "SolidMask", "inputs": {"value": 0.0, "width": w, "height": h}},
        "21": {"class_type": "SolidMask", "inputs": {"value": 1.0, "width": half, "height": h}},
        "22": {"class_type": "MaskComposite", "inputs": {
            "destination": ["20", 0], "source": ["21", 0], "x": 0, "y": 0, "operation": "add",
        }},
        "23": {"class_type": "FeatherMask", "inputs": {
            "mask": ["22", 0], "left": 0, "top": 0, "right": 64, "bottom": 0,
        }},
        # right mask
        "24": {"class_type": "SolidMask", "inputs": {"value": 0.0, "width": w, "height": h}},
        "25": {"class_type": "SolidMask", "inputs": {"value": 1.0, "width": right_w, "height": h}},
        "26": {"class_type": "MaskComposite", "inputs": {
            "destination": ["24", 0], "source": ["25", 0], "x": half, "y": 0, "operation": "add",
        }},
        "27": {"class_type": "FeatherMask", "inputs": {
            "mask": ["26", 0], "left": 64, "top": 0, "right": 0, "bottom": 0,
        }},
        "30": {"class_type": "IPAdapterAdvanced", "inputs": {
            "model": ["2", 0],
            "ipadapter": ["10", 0],
            "image": ["12", 0],
            "clip_vision": ["11", 0],
            "weight": FACE_W_UNIFY,
            "weight_type": "linear",
            "combine_embeds": "concat",
            "start_at": 0.0,
            "end_at": FACE_END_UNIFY,
            "embeds_scaling": "V only",
            "attn_mask": ["23", 0],
        }},
        "31": {"class_type": "IPAdapterAdvanced", "inputs": {
            "model": ["30", 0],
            "ipadapter": ["10", 0],
            "image": ["13", 0],
            "clip_vision": ["11", 0],
            "weight": FACE_W_UNIFY,
            "weight_type": "linear",
            "combine_embeds": "concat",
            "start_at": 0.0,
            "end_at": FACE_END_UNIFY,
            "embeds_scaling": "V only",
            "attn_mask": ["27", 0],
        }},
        # ConditioningSetMask left/right on positive prompts
        "40": {"class_type": "CLIPTextEncode", "inputs": {
            "text": f"left side: {CW_HALF}, {SCENE}, {STYLE}",
            "clip": ["2", 1],
        }},
        "41": {"class_type": "CLIPTextEncode", "inputs": {
            "text": f"right side: {SW_HALF}, {SCENE}, {STYLE}",
            "clip": ["2", 1],
        }},
        "42": {"class_type": "ConditioningSetMask", "inputs": {
            "conditioning": ["40", 0], "mask": ["23", 0],
            "set_cond_area": "default", "strength": 1.0,
        }},
        "43": {"class_type": "ConditioningSetMask", "inputs": {
            "conditioning": ["41", 0], "mask": ["27", 0],
            "set_cond_area": "default", "strength": 1.0,
        }},
        "44": {"class_type": "ConditioningCombine", "inputs": {
            "conditioning_1": ["42", 0], "conditioning_2": ["43", 0],
        }},
        "45": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["2", 1]}},
        # also mix in joint scene prompt lightly
        "46": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["2", 1]}},
        "47": {"class_type": "ConditioningCombine", "inputs": {
            "conditioning_1": ["44", 0], "conditioning_2": ["46", 0],
        }},
        "50": {"class_type": "VAEEncode", "inputs": {"pixels": ["14", 0], "vae": ["1", 2]}},
        "51": {"class_type": "KSampler", "inputs": {
            "model": ["31", 0], "positive": ["47", 0], "negative": ["45", 0],
            "latent_image": ["50", 0],
            "seed": seed, "steps": 20, "cfg": 4.5,
            "sampler_name": SAMPLER, "scheduler": SCHED, "denoise": denoise,
        }},
        "52": {"class_type": "VAEDecode", "inputs": {"samples": ["51", 0], "vae": ["1", 2]}},
        "53": {"class_type": "SaveImage", "inputs": {
            "images": ["52", 0], "filename_prefix": f"kf-cw-sw-v3/unify/{tag}",
        }},
    }
    return g


def pil_side_by_side(left_path: Path, right_path: Path, out_path: Path, full_w: int, full_h: int):
    if Image is None:
        raise RuntimeError("PIL not available")
    left = Image.open(left_path).convert("RGB")
    right = Image.open(right_path).convert("RGB")
    half = full_w // 2
    right_w = full_w - half
    left = left.resize((half, full_h), Image.Resampling.LANCZOS)
    right = right.resize((right_w, full_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (full_w, full_h))
    canvas.paste(left, (0, 0))
    canvas.paste(right, (half, 0))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, "PNG")
    return out_path


def probe_object_info():
    info = get(f"{SERVER}/object_info", 120)
    return info


def resolve_assets(info):
    loras = []
    try:
        loras = info["LoraLoader"]["input"]["required"]["lora_name"][0]
    except Exception:
        pass
    ipas = []
    try:
        ipas = info["IPAdapterModelLoader"]["input"]["required"]["ipadapter_file"][0]
    except Exception:
        pass
    clipvs = []
    try:
        clipvs = info["CLIPVisionLoader"]["input"]["required"]["clip_name"][0]
    except Exception:
        pass
    pulids = []
    has_pulid = "PulidModelLoader" in info and "ApplyPulid" in info
    if has_pulid:
        try:
            pulids = info["PulidModelLoader"]["input"]["required"]["pulid_file"][0]
        except Exception:
            pass

    cw = pick_from_list(loras, CHENGWU_CANDS, "chengwu")
    sw = pick_from_list(loras, SWEATER_CANDS, "sweater")
    hm = pick_from_list(loras, HOME_CANDS, "home")
    ipa = pick_from_list(ipas, IPA_FACE_CANDS, "ipa_face")
    clipv = pick_from_list(clipvs, CLIPV_CANDS, "clipv")
    pulid = None
    if has_pulid and pulids:
        pulid = next((p for p in pulids if "pulid" in p.lower()), pulids[0])

    # ConditioningSetMask availability
    has_csm = "ConditioningSetMask" in info and "ConditioningCombine" in info
    return {
        "chengwu": cw, "sweater": sw, "home": hm,
        "ipa_face": ipa, "clipv": clipv, "pulid": pulid,
        "has_pulid": bool(pulid), "has_csm": has_csm,
        "has_ipa": "IPAdapterAdvanced" in info,
    }


def run_one(g, dest: Path):
    hist = queue_wait(g)
    imgs = images_from_hist(hist)
    if not imgs:
        raise RuntimeError(f"no images for {dest.name}")
    download(imgs[0], dest)
    return dest


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    XFER.mkdir(parents=True, exist_ok=True)
    SOLOS.mkdir(parents=True, exist_ok=True)
    XFER_SOLOS.mkdir(parents=True, exist_ok=True)
    SCRATCH_SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    XFER_SCRIPT_DIR.mkdir(parents=True, exist_ok=True)

    # copy this script into shared/work/scratch/legacy-root/xfer if we can locate ourselves
    try:
        me = Path(__file__).resolve()
        shutil.copy2(me, SCRATCH_SCRIPT_DIR / me.name)
        shutil.copy2(me, XFER_SCRIPT_DIR / me.name)
    except Exception as e:
        print("script self-copy skip:", e, flush=True)

    wait_server()
    info = probe_object_info()
    assets = resolve_assets(info)
    print("assets", json.dumps(assets, ensure_ascii=False), flush=True)
    if not assets["has_ipa"]:
        raise SystemExit("IPAdapterAdvanced missing")

    comfy_input = first_existing(COMFY_INPUT_CANDIDATES) or COMFY_INPUT_CANDIDATES[0]
    comfy_input.mkdir(parents=True, exist_ok=True)

    cw_src = first_existing(CW_FACE_CANDIDATES)
    sw_src = first_existing(SW_FACE_CANDIDATES)
    if not cw_src or not sw_src:
        raise SystemExit(f"missing face refs cw={cw_src} sw={sw_src}")
    cw_face = stage_into_input(cw_src, comfy_input, "v3-face-chengwu.png")
    sw_face = stage_into_input(sw_src, comfy_input, "v3-face-sweater.png")
    print("cw_face", cw_src, "->", cw_face, flush=True)
    print("sw_face", sw_src, "->", sw_face, flush=True)

    saved_solos = []
    saved_same = []
    errors = []
    use_pulid = assets["has_pulid"]

    # ----- A) SOLO LOCKS -----
    print("=== A SOLO LOCKS ===", flush=True)
    for tag, seed, w, h in SOLO_JOBS_CW:
        try:
            print(f"solo CW {tag} {w}x{h} pulid={use_pulid}", flush=True)
            pos = f"{CW_SOLO}, {SCENE}, {STYLE}"
            g = graph_solo(
                pos, NEG_CW, seed, w, h, tag,
                assets["chengwu"], CW_SM, CW_SC,
                cw_face, assets["home"], assets["ipa_face"], assets["clipv"],
                use_pulid=use_pulid, pulid_file=assets["pulid"],
            )
            dest = SOLOS / f"{tag}.png"
            try:
                run_one(g, dest)
            except Exception as e:
                if use_pulid:
                    print("PuLID failed, retry IPA-only:", e, flush=True)
                    use_pulid = False
                    g = graph_solo(
                        pos, NEG_CW, seed, w, h, tag,
                        assets["chengwu"], CW_SM, CW_SC,
                        cw_face, assets["home"], assets["ipa_face"], assets["clipv"],
                        use_pulid=False,
                    )
                    run_one(g, dest)
                else:
                    raise
            mirror(dest, XFER_SOLOS)
            saved_solos.append(str(dest))
            print("saved", dest, flush=True)
        except Exception as e:
            errors.append(f"{tag}: {e}")
            print("ERR", tag, e, flush=True)
            traceback.print_exc()
        try_free()

    for tag, seed, w, h in SOLO_JOBS_SW:
        try:
            print(f"solo SW {tag} {w}x{h} pulid={use_pulid}", flush=True)
            pos = f"{SW_SOLO}, {SCENE}, {STYLE}"
            g = graph_solo(
                pos, NEG_SW, seed, w, h, tag,
                assets["sweater"], SW_SM, SW_SC,
                sw_face, assets["home"], assets["ipa_face"], assets["clipv"],
                use_pulid=use_pulid, pulid_file=assets["pulid"],
            )
            dest = SOLOS / f"{tag}.png"
            try:
                run_one(g, dest)
            except Exception as e:
                if use_pulid:
                    print("PuLID failed, retry IPA-only:", e, flush=True)
                    use_pulid = False
                    g = graph_solo(
                        pos, NEG_SW, seed, w, h, tag,
                        assets["sweater"], SW_SM, SW_SC,
                        sw_face, assets["home"], assets["ipa_face"], assets["clipv"],
                        use_pulid=False,
                    )
                    run_one(g, dest)
                else:
                    raise
            mirror(dest, XFER_SOLOS)
            saved_solos.append(str(dest))
            print("saved", dest, flush=True)
        except Exception as e:
            errors.append(f"{tag}: {e}")
            print("ERR", tag, e, flush=True)
            traceback.print_exc()
        try_free()

    # ----- B) SAME-FRAME SPLIT COMPOSITE -----
    print("=== B SAME-FRAME SPLIT ===", flush=True)
    if Image is None:
        errors.append("PIL missing — cannot composite")
        print("FATAL: PIL missing", flush=True)
    else:
        for tag, seed, full_w, full_h, tod, scene_extra in SCENES:
            try:
                half_w = full_w // 2
                right_w = full_w - half_w
                print(f"scene {tag} panels {half_w}x{full_h} + {right_w}x{full_h}", flush=True)

                # Left Chengwu panel
                pos_l = (
                    f"solo, 1girl, {CW_HALF}, standing on LEFT half of frame, "
                    f"{SCENE}, {scene_extra}, {tod}, {STYLE}, "
                    f"empty space on right, character framed left-center"
                )
                g_l = graph_panel(
                    pos_l, NEG_CW, seed, half_w, full_h, f"{tag}-L",
                    assets["chengwu"], CW_SM, CW_SC,
                    cw_face, assets["home"], assets["ipa_face"], assets["clipv"],
                )
                left_path = OUT / f"{tag}-L.png"
                run_one(g_l, left_path)
                mirror(left_path, XFER)
                try_free()

                # Right Sweater panel
                pos_r = (
                    f"solo, 1girl, {SW_HALF}, standing on RIGHT half of frame, "
                    f"{SCENE}, {scene_extra}, {tod}, {STYLE}, "
                    f"empty space on left, character framed right-center"
                )
                g_r = graph_panel(
                    pos_r, NEG_SW, seed + 17, right_w, full_h, f"{tag}-R",
                    assets["sweater"], SW_SM, SW_SC,
                    sw_face, assets["home"], assets["ipa_face"], assets["clipv"],
                )
                right_path = OUT / f"{tag}-R.png"
                run_one(g_r, right_path)
                mirror(right_path, XFER)
                try_free()

                # PIL paste
                raw = OUT / f"{tag}-raw-composite.png"
                pil_side_by_side(left_path, right_path, raw, full_w, full_h)
                mirror(raw, XFER)
                print("composited", raw, flush=True)

                # Optional unify
                final = OUT / f"{tag}.png"
                if assets["has_csm"]:
                    comp_name = stage_into_input(raw, comfy_input, f"v3-comp-{tag}.png")
                    joint_pos = (
                        f"2girls, two different women side by side, clearly distinct faces and hair, "
                        f"left: {CW_HALF}, right: {SW_HALF}, "
                        f"{SCENE}, {scene_extra}, {tod}, {STYLE}"
                    )
                    g_u = graph_unify(
                        joint_pos, NEG_JOINT, seed + 99, full_w, full_h, tag,
                        comp_name, cw_face, sw_face,
                        assets["home"], assets["ipa_face"], assets["clipv"],
                        denoise=UNIFY_DENOISE,
                    )
                    try:
                        run_one(g_u, final)
                    except Exception as e:
                        print("unify failed, keep raw composite:", e, flush=True)
                        shutil.copy2(raw, final)
                        errors.append(f"{tag}-unify: {e}")
                else:
                    print("no ConditioningSetMask — skip unify, use raw", flush=True)
                    shutil.copy2(raw, final)

                mirror(final, XFER)
                saved_same.append(str(final))
                print("saved same-frame", final, flush=True)
            except Exception as e:
                errors.append(f"{tag}: {e}")
                print("ERR", tag, e, flush=True)
                traceback.print_exc()
            try_free()

    # queue drained?
    queue_empty = False
    try:
        q = get(f"{SERVER}/queue", 10)
        running = q.get("queue_running") or []
        pending = q.get("queue_pending") or []
        queue_empty = len(running) == 0 and len(pending) == 0
    except Exception as e:
        errors.append(f"queue-check: {e}")

    report = {
        "ok": len(saved_solos) >= 4 and len(saved_same) >= 4 and not errors,
        "phase": "B-v3-split-composite",
        "recipe": {
            "method": "solo-lock then L/R panel split + PIL paste + optional low-denoise unify",
            "no_dual_char_lora_on_one_pass": True,
            "solo_loras": {
                "chengwu": [CW_SM, CW_SC],
                "sweater": [SW_SM, SW_SC],
                "home_solo": [HM_SOLO_SM, HM_SOLO_SC],
            },
            "face_weight_solo": FACE_W_SOLO,
            "unify": {
                "home_only": [HM_UNIFY_SM, HM_UNIFY_SC],
                "face_weight": FACE_W_UNIFY,
                "denoise": UNIFY_DENOISE,
                "conditioning_set_mask": assets.get("has_csm"),
            },
            "pulid_used": use_pulid and assets.get("has_pulid"),
            "assets": assets,
            "cw_face": str(cw_src),
            "sw_face": str(sw_src),
            "signatures": {
                "chengwu": "short grey-blue bob ABOVE shoulders, no ponytail, no clip, thin black choker",
                "sweater": "LONGER jet-black hair shoulder+, OBVIOUS bright red clip, cream sweater, no choker",
            },
        },
        "solos": saved_solos,
        "same_frame": saved_same,
        "errors": errors,
        "queue_empty": queue_empty,
        "out": str(OUT),
        "xfer": str(XFER),
        "success_criteria": {
            "solos_each_ge_2": len([s for s in saved_solos if "S-CW" in s]) >= 2
                and len([s for s in saved_solos if "S-SW" in s]) >= 2,
            "same_frame_ge_4": len(saved_same) >= 4,
        },
    }
    (OUT / "last-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    shutil.copy2(OUT / "last-report.json", XFER / "last-report.json")
    print(json.dumps(report, ensure_ascii=False), flush=True)
    if not report["success_criteria"]["solos_each_ge_2"] or not report["success_criteria"]["same_frame_ge_4"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
