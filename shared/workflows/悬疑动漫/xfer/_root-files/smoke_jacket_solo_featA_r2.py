# -*- coding: utf-8 -*-
"""Jacket girl Plan A solo r2: face-crop IPA + weaker face weight so prompt can force long hair.
r1 failed: V2-SL1 full half-body IPA locked short grey bob into all 4 frames.
"""
from __future__ import annotations
import json, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
CKPT = "animagine-xl-4.0-opt.safetensors"
JACKET = "charb-jacket-sdxl-v1b.safetensors"
HOME = "jiaoli-home-sdxl-v1.safetensors"
IPA_STYLE = "ip-adapter-plus_sdxl_vit-h.safetensors"
IPA_FACE = "ip-adapter-plus-face_sdxl_vit-h.safetensors"
CLIPV = "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"

JK_SM, JK_SC = 0.76, 0.66
HM_SM, HM_SC = 0.50, 0.42
STYLE_W, STYLE_END = 0.16, 0.45
FACE_W, FACE_END = 0.55, 0.78  # lowered so Plan A hair can override V2-SL1 bob
STEPS, CFG = 28, 5.3

COMFY_INPUT_CANDIDATES = [
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input"),
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\ComfyUI_windows_portable\ComfyUI\input"),
]
STYLE_CANDIDATES = [
    Path(r"E:\program\1project\video\xfer\refs-for-grok\style-prev-N2.png"),
    Path(r"E:\program\1project\video\xfer\overnight-2026-09-21\K2-half-living-day-out-1-2026092502.png"),
]
JK_FACE_CANDIDATES = [
    Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input\v4-face-jacket-V2-SL1-facecrop.png"),
    Path(r"E:\program\1project\video\xfer\keyframes-2026-09-29\jacket-solo-featA\v4-face-jacket-V2-SL1-facecrop.png"),
]

OUT = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\jacket-solo-featA")
XFER = Path(r"E:\program\1project\video\xfer\keyframes-2026-09-29\jacket-solo-featA")

STYLE_TAGS = (
    "anime style, masterpiece, best quality, soft cel shading, clean lineart, "
    "flat color, soft lighting, consistent 2d anime illustration, "
    "clear readable face and hair, young adult woman"
)

HAIR = (
    "(shoulder-length hair:1.4), (hair past shoulders:1.35), (medium-long hair:1.3), "
    "(dark brown hair:1.25), (black-brown hair:1.15), (side parted hair:1.2), "
    "(soft wavy hair:1.2), (thin bangs:1.15), (side bangs:1.1), "
    "NOT short bob, NOT chin-length bob, NOT grey hair, NOT blue-grey hair, NOT ash blue hair"
)

JK = (
    f"charb_jacket, 1girl, solo, young adult woman, {HAIR}, "
    "slightly mature oval face, clearer jawline, slightly longer midface, "
    "youthful adult NOT babyface, warm brown amber eyes, "
    "small silver stud earrings, NO choker, NO collar necklace, "
    "dark casual jacket over inner shirt"
)

SCENE_BASE = "jiaoli_home, indoor home interior, soft home atmosphere"
SCENE_CLEAN = "clean indoor interior, soft ambient light, minimal background clutter"

NEG = (
    "short bob, chin-length hair, hair above shoulders, grey-blue bob, ash blue hair, "
    "blue-grey hair, charcoal grey bob, cool grey hair, pink hair streak, red hair clip, "
    "white hair clip, black choker, thin black choker, collar choker, "
    "teal scoop-neck, cyan-green top, identical twin face, same face as chengwu, "
    "baby face, loli, child, chibi, overly cute childish face, hard masculine jaw, "
    "cream turtleneck sweater, foggy face, blurry face, scanlines, misty, heavy fog, "
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, cropped, "
    "worst quality, low quality, jpeg artifacts, signature, watermark, blurry, "
    "photorealistic, 2girls, multiple girls, boy, male, crowd, western comic, 3d render"
)

JOBS = [
    ("r2-A1-front-half", 2026092951, 896, 1152,
     f"1girl, solo, front view half body portrait looking at viewer, "
     f"{JK}, {SCENE_CLEAN}, soft frontal light, {STYLE_TAGS}"),
    ("r2-A2-3q-half", 2026092952, 896, 1152,
     f"1girl, solo, three-quarter view half body, head turned slightly, looking at viewer, "
     f"{JK}, {SCENE_CLEAN}, soft side light, {STYLE_TAGS}"),
    ("r2-A3-window-stand", 2026092953, 896, 1152,
     f"1girl, solo, standing by window, half body to knee-up, looking at viewer, "
     f"{JK}, {SCENE_BASE}, daytime soft daylight through window, {STYLE_TAGS}"),
    ("r2-A4-sofa-sit", 2026092954, 1152, 896,
     f"1girl, solo, sitting on sofa, half body portrait, looking at viewer, "
     f"{JK}, {SCENE_BASE}, night warm lamp light, living room sofa, {STYLE_TAGS}"),
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


def graph(pos, seed, w, h, tag, style_img, jk_face):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoraLoader", "inputs": {
            "model": ["1", 0], "clip": ["1", 1],
            "lora_name": JACKET, "strength_model": JK_SM, "strength_clip": JK_SC,
        }},
        "3": {"class_type": "LoraLoader", "inputs": {
            "model": ["2", 0], "clip": ["2", 1],
            "lora_name": HOME, "strength_model": HM_SM, "strength_clip": HM_SC,
        }},
        "10": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": IPA_STYLE}},
        "11": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": IPA_FACE}},
        "12": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": CLIPV}},
        "13": {"class_type": "LoadImage", "inputs": {"image": style_img}},
        "14": {"class_type": "LoadImage", "inputs": {"image": jk_face}},
        "16": {"class_type": "IPAdapterAdvanced", "inputs": {
            "model": ["3", 0], "ipadapter": ["10", 0], "image": ["13", 0],
            "clip_vision": ["12", 0], "weight": STYLE_W, "weight_type": "style transfer",
            "combine_embeds": "concat", "start_at": 0.0, "end_at": STYLE_END,
            "embeds_scaling": "V only",
        }},
        "30": {"class_type": "IPAdapterAdvanced", "inputs": {
            "model": ["16", 0], "ipadapter": ["11", 0], "image": ["14", 0],
            "clip_vision": ["12", 0], "weight": FACE_W, "weight_type": "linear",
            "combine_embeds": "concat", "start_at": 0.0, "end_at": FACE_END,
            "embeds_scaling": "V only",
        }},
        "40": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["3", 1]}},
        "41": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["3", 1]}},
        "42": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "43": {"class_type": "KSampler", "inputs": {
            "model": ["30", 0], "positive": ["40", 0], "negative": ["41", 0],
            "latent_image": ["42", 0], "seed": seed, "steps": STEPS, "cfg": CFG,
            "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": 1.0,
        }},
        "44": {"class_type": "VAEDecode", "inputs": {"samples": ["43", 0], "vae": ["1", 2]}},
        "45": {"class_type": "SaveImage", "inputs": {
            "images": ["44", 0], "filename_prefix": f"kf-jk-solo-featA/{tag}",
        }},
    }


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
    jk_src = first_existing(JK_FACE_CANDIDATES)
    if not style_src or not jk_src:
        raise SystemExit(f"missing refs style={style_src} jk={jk_src}")

    style_img = stage_into_input(style_src, comfy_input, "v4-style-k2.png")
    jk_face = stage_into_input(jk_src, comfy_input, "v4-face-jacket-V2-SL1-facecrop.png")
    print("style", style_src, "jk_facecrop", jk_src, flush=True)
    print("weights", {
        "jacket": [JK_SM, JK_SC], "home": [HM_SM, HM_SC],
        "style_ipa": STYLE_W, "face_ipa": FACE_W, "steps": STEPS, "cfg": CFG,
    }, flush=True)

    results = []
    for tag, seed, w, h, pos in JOBS:
        print(f"run {tag} {w}x{h} seed={seed}", flush=True)
        hist = queue_wait(graph(pos, seed, w, h, tag, style_img, jk_face))
        imgs = []
        for o in hist.get("outputs", {}).values():
            imgs.extend(o.get("images", []))
        if not imgs:
            raise SystemExit(f"no images {tag}")
        dest = OUT / f"{tag}.png"
        download(imgs[0], dest)
        shutil.copy2(dest, XFER / dest.name)
        print("saved", dest, "bytes", dest.stat().st_size, flush=True)
        results.append({
            "file": dest.name, "path": str(dest), "xfer": str(XFER / dest.name),
            "seed": seed, "size": [w, h], "tag": tag,
        })
        try_free()

    report = {
        "ok": True,
        "phase": "jacket-solo-featA-r2",
        "date": "2026-09-29",
        "plan": "A",
        "r1_fail": "full V2-SL1 half IPA@0.70 locked short grey bob into all 4",
        "r2_fix": "facecrop IPA + face_w=0.55 + weighted long dark hair prompts",
        "jacket_face_lock": str(jk_src),
        "jacket_face_staged": "v4-face-jacket-V2-SL1-facecrop.png",
        "style_ref": str(style_src),
        "weights": {
            "ckpt": CKPT,
            "lora_jacket": [JK_SM, JK_SC],
            "lora_home": [HM_SM, HM_SC],
            "style_ipa": STYLE_W,
            "face_ipa": FACE_W,
            "steps": STEPS,
            "cfg": CFG,
            "sampler": "euler_ancestral",
        },
        "jobs": results,
        "out": str(OUT),
        "xfer": str(XFER),
    }
    (OUT / "REPORT-r2.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    shutil.copy2(OUT / "REPORT-r2.json", XFER / "REPORT-r2.json")
    # merge summary REPORT.json pointing at r2 as primary candidates
    summary = {
        "ok": True,
        "phase": "jacket-solo-featA",
        "date": "2026-09-29",
        "plan": "A",
        "primary_round": "r2",
        "r1_note": "A1-A4 FAILED Plan A hair (short grey bob locked by full V2-SL1 IPA)",
        "r2_note": "facecrop + face_ipa 0.55; visual triage required",
        "weights_r2": report["weights"],
        "candidates_r2": results,
        "r1_files": [
            "A1-front-half.png", "A2-3q-half.png", "A3-window-stand.png", "A4-sofa-sit.png"
        ],
        "out": str(OUT),
        "xfer": str(XFER),
        "featA_checklist": [
            "hair past shoulders / not short bob",
            "dark brown/black not grey-blue",
            "thin or side bangs",
            "small silver stud earrings",
            "slightly mature oval face",
            "no choker / no teal",
        ],
    }
    (OUT / "REPORT.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    shutil.copy2(OUT / "REPORT.json", XFER / "REPORT.json")
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
