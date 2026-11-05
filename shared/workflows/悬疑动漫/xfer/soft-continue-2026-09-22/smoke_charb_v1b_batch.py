# -*- coding: utf-8 -*-
"""Char B stylelock-v1b retest: lower IPA identity bleed, lock jet-black hair, strict profile."""
from __future__ import annotations
import json, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
CKPT = "animagine-xl-4.0-opt.safetensors"
IPA = "ip-adapter-plus_sdxl_vit-h.safetensors"
CLIPV = "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
STYLE_SRC = Path(r"E:\program\1project\video\xfer\overnight-2026-09-21\K2-half-living-day-out-1-2026092502.png")
COMFY_INPUT = Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input")
STEPS, CFG = 28, 5.3
# v3: lower stylelock identity bleed vs v2's 0.35 / end_at 0.70
IPA_W = 0.20
IPA_END = 0.55
LORA_SM, LORA_SC = 0.75, 0.70

STYLE_TAGS = (
    "anime style, masterpiece, best quality, soft cel shading, clean lineart, "
    "flat color, soft lighting, consistent 2d anime illustration"
)
NEG_BASE = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, "
    "cropped, worst quality, low quality, jpeg artifacts, signature, watermark, blurry, "
    "loli, child, photorealistic, realistic skin texture, pores, glossy plastic skin, "
    "extra people, crowd, multiple girls, deformed face, western comic, 3d render, "
    "grey-blue hair, blue hair, teal hair, silver hair, purple hair, pink hair, magenta hair, "
    "lavender hair, ash blonde hair, colored hair highlight, pink rim light on hair, "
    "harsh rim light, oversharpened, oily leather shine, three-quarter face when profile requested"
)

OUTFITS = {
    "sweater": {
        "lora": "charb-sweater-sdxl-v1b.safetensors",
        "trigger": "charb_sweater",
        "char": (
            f"charb_sweater, 1girl, solo, young adult woman, jet black hair, pure black hair, "
            f"short black hair with low ponytail, bangs, single red hair clip on one side, "
            f"dark brown eyes, pale skin, cream turtleneck cable-knit sweater, soft knit texture, "
            f"{STYLE_TAGS}, hair color is pure jet black only"
        ),
        "neg_extra": "double hair clips, pink hair, grey hair, blue-tinted hair, oversized balloon sweater",
        "prefix": "charb-sweater-stylelock-v1b",
        "out": Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\charb-sweater-smoke-stylelock-v1b"),
        "xfer": Path(r"E:\program\1project\video\xfer\soft-continue-2026-09-22\smoke\charb_sweater_v1b"),
        "seeds": (20260922101, 20260922102, 20260922103, 20260922104),
    },
    "jacket": {
        "lora": "charb-jacket-sdxl-v1b.safetensors",
        "trigger": "charb_jacket",
        "char": (
            f"charb_jacket, 1girl, solo, young adult woman, jet black hair, pure black hair, "
            f"short black bob cut, bangs, single red hair clip, dark brown eyes, pale skin, "
            f"black motorcycle jacket with asymmetric lapels, visible zipper, metal rivets, "
            f"no ribbed hem, white t-shirt underneath, {STYLE_TAGS}, hair color is pure jet black only"
        ),
        "neg_extra": "pink hair, grey-blue hair, flight jacket, bomber jacket, ribbed cuffs, sports jacket",
        "prefix": "charb-jacket-stylelock-v1b",
        "out": Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\charb-jacket-smoke-stylelock-v1b"),
        "xfer": Path(r"E:\program\1project\video\xfer\soft-continue-2026-09-22\smoke\charb_jacket_v1b"),
        "seeds": (20260922111, 20260922112, 20260922113, 20260922114),
    },
    "hoodie": {
        "lora": "charb-hoodie-sdxl-v1b.safetensors",
        "trigger": "charb_hoodie",
        "char": (
            f"charb_hoodie, 1girl, solo, young adult woman, jet black hair, pure black hair, "
            f"short black hair, neat short bob, bangs, two red hair clips, dark brown eyes, pale skin, "
            f"grey hoodie with drawstrings, kangaroo pocket, {STYLE_TAGS}, "
            f"hair color is pure jet black only, youthful adult face"
        ),
        "neg_extra": "pink hair, purple hair, long hair, mature face, white drawstrings only if mismatched",
        "prefix": "charb-hoodie-stylelock-v1b",
        "out": Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\charb-hoodie-smoke-stylelock-v1b"),
        "xfer": Path(r"E:\program\1project\video\xfer\soft-continue-2026-09-22\smoke\charb_hoodie_v1b"),
        "seeds": (20260922121, 20260922122, 20260922123, 20260922124),
    },
}


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


def jobs_for(cfg):
    char = cfg["char"]
    s1, s2, s3, s4 = cfg["seeds"]
    return [
        ("V1B-SL1-front-half", s1, 896, 1152,
         f"{char}, half body, front view, looking at viewer, plain soft grey background"),
        ("V1B-SL2-3q", s2, 896, 1152,
         f"{char}, upper body, three-quarter view, looking at viewer, plain soft grey background"),
        ("V1B-SL3-full", s3, 832, 1216,
         f"{char}, full body, standing, looking at viewer, plain soft grey background, simple shoes"),
        ("V1B-SL4-profile", s4, 896, 1152,
         f"{char}, upper body, strict side profile, only one eye visible, ear fully visible, "
         f"looking left, face turned 90 degrees, no three-quarter face, plain soft grey background"),
    ]


def graph(cfg, pos, seed, w, h, tag, style_name, neg):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoraLoader", "inputs": {
            "model": ["1", 0], "clip": ["1", 1],
            "lora_name": cfg["lora"], "strength_model": LORA_SM, "strength_clip": LORA_SC,
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
            "end_at": IPA_END,
            "embeds_scaling": "V only",
            "clip_vision": ["4", 0],
        }},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["2", 1]}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["2", 1]}},
        "9": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "10": {"class_type": "KSampler", "inputs": {
            "model": ["6", 0], "positive": ["7", 0], "negative": ["8", 0],
            "latent_image": ["9", 0], "seed": seed, "steps": STEPS, "cfg": CFG,
            "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": 1.0,
        }},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["1", 2]}},
        "12": {"class_type": "SaveImage", "inputs": {
            "images": ["11", 0], "filename_prefix": f"{cfg['prefix']}/{tag}",
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


def resolve_style():
    if STYLE_SRC.is_file():
        return STYLE_SRC
    cands = list(Path(r"E:\program\1project\video\xfer\overnight-2026-09-21").glob("K2*.png"))
    cands += list(Path(r"E:\program\1project\video\xfer").glob("**/K2-half*.png"))
    if not cands:
        raise SystemExit(f"missing style ref {STYLE_SRC}")
    return cands[0]


def run_outfit(name, cfg, style_name, style_path):
    cfg["out"].mkdir(parents=True, exist_ok=True)
    cfg["xfer"].mkdir(parents=True, exist_ok=True)
    neg = NEG_BASE + ", " + cfg["neg_extra"]
    saved = []
    for tag, seed, w, h, pos in jobs_for(cfg):
        print(f"[{name}] run {tag}", flush=True)
        entry = queue_wait(graph(cfg, pos, seed, w, h, tag, style_name, neg))
        for node in (entry.get("outputs") or {}).values():
            for im in node.get("images") or []:
                dest = cfg["out"] / f"{tag}.png"
                download(im, dest)
                shutil.copy2(dest, cfg["xfer"] / dest.name)
                saved.append(str(dest))
                print("saved", dest, flush=True)
                break
        try_free()
    summary = {
        "ok": True,
        "version": "stylelock-v1b",
        "outfit": name,
        "lora": cfg["lora"],
        "lora_strength": [LORA_SM, LORA_SC],
        "ipa_weight": IPA_W,
        "ipa_end_at": IPA_END,
        "ipa_weight_type": "style transfer",
        "style_ref": str(style_path),
        "cfg": CFG,
        "files": saved,
        "xfer": str(cfg["xfer"]),
        "notes": "lower IPA + shorter end_at; jet-black hair lock; strict one-eye profile",
    }
    (cfg["xfer"] / "SMOKE-V1B-SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return summary


def main():
    # order: sweater first (best candidate), then jacket, hoodie
    order = ["sweater", "jacket", "hoodie"]
    import sys
    if len(sys.argv) > 1:
        order = [a for a in sys.argv[1:] if a in OUTFITS]
        if not order:
            raise SystemExit("usage: smoke_charb_stylelock_v3_batch.py [sweater jacket hoodie]")
    style = resolve_style()
    COMFY_INPUT.mkdir(parents=True, exist_ok=True)
    style_name = "chengwu-style-lock-ref.png"
    shutil.copy2(style, COMFY_INPUT / style_name)
    print("style_ref", style, flush=True)
    wait_server()
    root = Path(r"E:\program\1project\video\xfer\soft-continue-2026-09-22")
    root.mkdir(parents=True, exist_ok=True)
    results = []
    for name in order:
        results.append(run_outfit(name, OUTFITS[name], style_name, style))
    batch = {"ok": True, "version": "stylelock-v1b", "order": order, "results": results}
    (root / "BATCH-SUMMARY.json").write_text(
        json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("BATCH DONE", flush=True)


if __name__ == "__main__":
    main()
