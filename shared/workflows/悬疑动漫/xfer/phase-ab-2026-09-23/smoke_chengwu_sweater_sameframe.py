# -*- coding: utf-8 -*-
"""Phase B: Chengwu + sweater woman same-frame 定妆 keyframes.
Locked: chengwu-sdxl-v1b + charb-sweater-sdxl-v1b + jiaoli-home-sdxl-v1.
Light IPA style (~0.22) from Chengwu K2 for soft-cel toward Chengwu look on sweater char.
NO male hoodie. NO training. Images only. OpenPose optional (single standing ref, soft).
"""
from __future__ import annotations
import json, time, urllib.request, urllib.parse, uuid, shutil, os
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
CKPT = "animagine-xl-4.0-opt.safetensors"
CHENGWU = "chengwu-sdxl-v1b.safetensors"
SWEATER = "charb-sweater-sdxl-v1b.safetensors"
HOME = "jiaoli-home-sdxl-v1.safetensors"
CN = "xinsir-controlnet-union-sdxl-1.0.safetensors"
IPA = "ip-adapter-plus_sdxl_vit-h.safetensors"
CLIPV = "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"

CW_SM, CW_SC = 0.86, 0.80
SW_SM, SW_SC = 0.78, 0.72
HM_SM, HM_SC = 0.72, 0.65
IPA_W, IPA_END = 0.22, 0.55
CN_STRENGTH = 0.40  # soft — two-person composition; single pose ref is only a guide
STEPS, CFG = 28, 5.3

COMFY_INPUT_CANDIDATES = [
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input"),
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\ComfyUI_windows_portable\ComfyUI\input"),
    Path(r"E:\program\1project\video\shared\project-tools\production\comfyui-input"),
]
STYLE_CANDIDATES = [
    Path(r"E:\program\1project\video\xfer\overnight-2026-09-21\K2-half-living-day-out-1-2026092502.png"),
    Path(r"E:\program\1project\video\xfer\home-char-smoke\K2-out.png"),
    Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\home-char-smoke\keyframe-pose\K2-half-living-day-out.png"),
]
POSE_CANDIDATES = [
    Path(r"E:\program\1project\video\xfer\pose-refs\pose-ref-standing.png"),
    Path(r"E:\program\1project\video\xfer\home-char-smoke\pose-ref-standing.png"),
    Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\home-char-smoke\pose-ref-standing.png"),
]

OUT = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\keyframes-2026-09-23\chengwu-sweater")
XFER = Path(r"E:\program\1project\video\xfer\keyframes-2026-09-23\chengwu-sweater")
BEST = Path(r"E:\program\1project\video\xfer\keyframes-2026-09-23\chengwu-sweater-best")

STYLE_TAGS = (
    "anime style, masterpiece, best quality, soft cel shading, clean lineart, "
    "flat color, soft lighting, consistent 2d anime illustration"
)
CW = (
    "chengwu, 程雾, young adult woman, short grey-blue bob hair, brown eyes, pale skin, "
    "thin black choker with silver ring, teal long-sleeve scoop-neck top"
)
SW = (
    "charb_sweater, young adult woman, jet black hair, pure black hair, "
    "short black hair with low ponytail, bangs, single red hair clip on one side, "
    "dark brown eyes, pale skin, cream turtleneck cable-knit sweater"
)
SCENE = (
    "jiaoli_home, indoor home interior, living room, soft home atmosphere, "
    "sofa, floor lamp, subtle horror-casual home vibe, readable two-person composition"
)
NEG = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, "
    "cropped, worst quality, low quality, jpeg artifacts, signature, watermark, blurry, "
    "loli, child, photorealistic, realistic skin texture, pores, "
    "1girl, solo, fused faces, identical twins, same hair color both, "
    "extra limbs, three people, crowd, deformed face, western comic, 3d render, "
    "boy, male, man, hoodie, grey-blue hair on sweater girl, black hair on chengwu, "
    "harsh rim light, oversharpened"
)

# (tag, seed, w, h, use_cn, use_ipa, prompt_extra)
JOBS = [
    ("N1-living-night-stand", 2026092301, 1152, 896, False, True,
     f"2girls, two women standing side by side in living room at night, "
     f"left: {CW}, right: {SW}, both looking at viewer, "
     f"{SCENE}, night, city lights through window, {STYLE_TAGS}"),
    ("N2-living-day-talk", 2026092302, 1152, 896, False, True,
     f"2girls, two women facing each other talking casually, "
     f"left: {CW}, right: {SW}, mid-conversation gestures, "
     f"{SCENE}, daytime, soft daylight, window, {STYLE_TAGS}"),
    ("N3-sofa-sit", 2026092303, 1152, 896, False, True,
     f"2girls, two women sitting on sofa together, "
     f"left: {CW}, right: {SW}, relaxed home vibe, "
     f"{SCENE}, night, warm lamp light, {STYLE_TAGS}"),
    ("N4-doorway-stand", 2026092304, 896, 1152, False, True,
     f"2girls, two women standing near doorway into living room, "
     f"front: {CW}, slightly behind: {SW}, "
     f"{SCENE}, night, hallway to living room, {STYLE_TAGS}"),
    ("N5-window-day", 2026092305, 1152, 896, False, True,
     f"2girls, two women by the window, half body, "
     f"left: {CW}, right: {SW}, looking at viewer, "
     f"{SCENE}, daytime, soft daylight, {STYLE_TAGS}"),
    ("N6-living-night-cn", 2026092306, 1152, 896, True, True,
     f"2girls, two women standing in living room, readable spacing, "
     f"left: {CW}, right: {SW}, "
     f"{SCENE}, night, sofa, floor lamp, city lights, {STYLE_TAGS}"),
    ("N7-sofa-alt", 2026092307, 1152, 896, False, False,
     f"2girls, two women sitting on sofa, calm expressions, "
     f"left: {CW}, right: {SW}, "
     f"{SCENE}, night, warm lamp, {STYLE_TAGS}"),
    ("N8-living-day-cn", 2026092308, 896, 1152, True, True,
     f"2girls, two women standing three-quarter view, "
     f"left: {CW}, right: {SW}, looking at viewer, "
     f"{SCENE}, daytime, soft daylight, {STYLE_TAGS}"),
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


def graph(pos, seed, w, h, tag, style_name=None, pose_name=None, use_cn=False, use_ipa=False):
    g = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoraLoader", "inputs": {
            "model": ["1", 0], "clip": ["1", 1],
            "lora_name": CHENGWU, "strength_model": CW_SM, "strength_clip": CW_SC,
        }},
        "3": {"class_type": "LoraLoader", "inputs": {
            "model": ["2", 0], "clip": ["2", 1],
            "lora_name": SWEATER, "strength_model": SW_SM, "strength_clip": SW_SC,
        }},
        "4": {"class_type": "LoraLoader", "inputs": {
            "model": ["3", 0], "clip": ["3", 1],
            "lora_name": HOME, "strength_model": HM_SM, "strength_clip": HM_SC,
        }},
    }
    model_src = ["4", 0]
    clip_src = ["4", 1]
    nid = 5

    if use_ipa and style_name:
        g[str(nid)] = {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": IPA}}
        ipa_id = nid; nid += 1
        g[str(nid)] = {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": CLIPV}}
        clipv_id = nid; nid += 1
        g[str(nid)] = {"class_type": "LoadImage", "inputs": {"image": style_name}}
        style_id = nid; nid += 1
        g[str(nid)] = {"class_type": "IPAdapterAdvanced", "inputs": {
            "model": model_src,
            "ipadapter": [str(ipa_id), 0],
            "image": [str(style_id), 0],
            "clip_vision": [str(clipv_id), 0],
            "weight": IPA_W,
            "weight_type": "style transfer",
            "combine_embeds": "concat",
            "start_at": 0.0,
            "end_at": IPA_END,
            "embeds_scaling": "V only",
        }}
        model_src = [str(nid), 0]
        nid += 1

    g[str(nid)] = {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": clip_src}}
    pos_id = nid; nid += 1
    g[str(nid)] = {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": clip_src}}
    neg_id = nid; nid += 1
    pos_src = [str(pos_id), 0]
    neg_src = [str(neg_id), 0]

    if use_cn and pose_name:
        g[str(nid)] = {"class_type": "LoadImage", "inputs": {"image": pose_name}}
        pose_img = nid; nid += 1
        g[str(nid)] = {"class_type": "OpenposePreprocessor", "inputs": {
            "image": [str(pose_img), 0],
            "detect_hand": "enable",
            "detect_body": "enable",
            "detect_face": "disable",
            "resolution": 512,
            "scale_stick_for_xinsr_cn": "enable",
        }}
        pose_map = nid; nid += 1
        g[str(nid)] = {"class_type": "ControlNetLoader", "inputs": {"control_net_name": CN}}
        cn_load = nid; nid += 1
        g[str(nid)] = {"class_type": "SetUnionControlNetType", "inputs": {
            "control_net": [str(cn_load), 0], "type": "openpose",
        }}
        cn_typed = nid; nid += 1
        g[str(nid)] = {"class_type": "ControlNetApplyAdvanced", "inputs": {
            "positive": pos_src, "negative": neg_src,
            "control_net": [str(cn_typed), 0], "image": [str(pose_map), 0],
            "strength": CN_STRENGTH, "start_percent": 0.0, "end_percent": 0.75,
            "vae": ["1", 2],
        }}
        pos_src = [str(nid), 0]
        neg_src = [str(nid), 1]
        nid += 1

    g[str(nid)] = {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}}
    lat = nid; nid += 1
    g[str(nid)] = {"class_type": "KSampler", "inputs": {
        "model": model_src, "positive": pos_src, "negative": neg_src,
        "latent_image": [str(lat), 0],
        "seed": seed, "steps": STEPS, "cfg": CFG,
        "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": 1.0,
    }}
    samp = nid; nid += 1
    g[str(nid)] = {"class_type": "VAEDecode", "inputs": {"samples": [str(samp), 0], "vae": ["1", 2]}}
    dec = nid; nid += 1
    g[str(nid)] = {"class_type": "SaveImage", "inputs": {
        "images": [str(dec), 0], "filename_prefix": f"kf-chengwu-sweater/{tag}",
    }}
    return g


def queue_wait(g):
    resp = post(f"{SERVER}/prompt", {"prompt": g, "client_id": str(uuid.uuid4())})
    if resp.get("node_errors"):
        raise SystemExit("node_errors " + json.dumps(resp["node_errors"], ensure_ascii=False))
    pid = resp["prompt_id"]
    print("queued", pid, flush=True)
    t0 = time.time()
    while time.time() - t0 < 900:
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

    comfy_input = first_existing(COMFY_INPUT_CANDIDATES)
    if comfy_input is None:
        comfy_input = COMFY_INPUT_CANDIDATES[0]
        comfy_input.mkdir(parents=True, exist_ok=True)

    style_src = first_existing(STYLE_CANDIDATES)
    pose_src = first_existing(POSE_CANDIDATES)
    style_name = stage_into_input(style_src, comfy_input, "kf-style-k2.png") if style_src else None
    pose_name = stage_into_input(pose_src, comfy_input, "kf-pose-standing.png") if pose_src else None
    print("style", style_src, "pose", pose_src, "input", comfy_input, flush=True)

    saved = []
    for tag, seed, w, h, use_cn, use_ipa, pos in JOBS:
        use_cn_eff = use_cn and bool(pose_name)
        use_ipa_eff = use_ipa and bool(style_name)
        print("run", tag, w, h, "cn", use_cn_eff, "ipa", use_ipa_eff, flush=True)
        try:
            entry = queue_wait(graph(
                pos, seed, w, h, tag,
                style_name=style_name, pose_name=pose_name,
                use_cn=use_cn_eff, use_ipa=use_ipa_eff,
            ))
        except SystemExit as e:
            # fallback: drop CN then IPA if node missing
            msg = str(e)
            print("retry softer graph after:", msg, flush=True)
            try_free()
            entry = queue_wait(graph(
                pos, seed, w, h, tag,
                style_name=style_name, pose_name=None,
                use_cn=False, use_ipa=False,
            ))
        for node in (entry.get("outputs") or {}).values():
            for im in node.get("images") or []:
                dest = OUT / f"{tag}.png"
                download(im, dest)
                shutil.copy2(dest, XFER / dest.name)
                if tag in ("N1-living-night-stand", "N2-living-day-talk", "N3-sofa-sit", "N5-window-day"):
                    shutil.copy2(dest, BEST / dest.name)
                saved.append(str(dest))
                print("saved", dest, flush=True)
                break
        try_free()

    summary = {
        "ok": True,
        "phase": "B-chengwu-sweater-sameframe",
        "loras": {
            "chengwu": [CHENGWU, CW_SM, CW_SC],
            "sweater": [SWEATER, SW_SM, SW_SC],
            "home": [HOME, HM_SM, HM_SC],
        },
        "ipa": {"weight": IPA_W, "end_at": IPA_END, "style": str(style_src)},
        "openpose": {"strength": CN_STRENGTH, "pose": str(pose_src)},
        "steps": STEPS, "cfg": CFG,
        "files": saved,
        "xfer": str(XFER),
        "best": str(BEST),
        "note": "Images only; no H3. Dual-char prompt; soft IPA stylelock; soft optional OpenPose.",
    }
    (XFER / "SMOKE-CHENGWU-SWEATER-KF.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (BEST / "SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
