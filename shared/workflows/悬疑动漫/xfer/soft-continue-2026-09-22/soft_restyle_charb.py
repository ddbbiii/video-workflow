# -*- coding: utf-8 -*-
"""Restyle Char B training sets toward Chengwu soft-cel via img2img + IPAdapter style transfer."""
from __future__ import annotations
import json, time, urllib.request, urllib.parse, uuid, shutil, sys
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
CKPT = "animagine-xl-4.0-opt.safetensors"
IPA = "ip-adapter-plus_sdxl_vit-h.safetensors"
CLIPV = "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
STYLE_SRC = Path(r"E:\program\1project\video\xfer\home-char-smoke\K2-half-living-day-out-1-2026092502.png")
COMFY_INPUT = Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input")
STEPS, CFG = 28, 5.3
IPA_W, IPA_END = 0.40, 0.60
DENOISE = 0.38

SOFT = (
    "soft cel shading, soft lighting, gentle flat color, clean soft lineart, "
    "delicate anime illustration, muted soft palette, not harsh comic ink, "
    "not western comic, not thick manga screentone"
)
NEG = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, "
    "cropped, worst quality, low quality, jpeg artifacts, signature, watermark, blurry, "
    "loli, child, photorealistic, extra people, multiple girls, deformed face, "
    "harsh comic lines, thick ink outlines, western comic, screentone, glossy plastic skin, "
    "grey-blue hair, blue hair, teal hair, pink hair, purple hair, silver hair, "
    "pink rim light on hair, magenta hair highlight"
)

OUTFITS = {
    "sweater": {
        "trigger": "charb_sweater",
        "src_dir": Path(r"E:\program\1project\video\shared\project-tools\lora\charb-sweater-v1\dataset\img\10_charb_sweater"),
        "out_dir": Path(r"E:\program\1project\video\shared\project-tools\lora\charb-sweater-v1b\dataset\img\10_charb_sweater"),
        "seed": Path(r"E:\program\1project\video\xfer\overnight-2026-09-21\charB\02-sweater.png"),
        "desc": "young adult woman, jet black hair, short black hair with low ponytail, bangs, single red hair clip, dark brown eyes, pale skin, cream turtleneck cable-knit sweater",
        "xfer": Path(r"E:\program\1project\video\xfer\soft-continue-2026-09-22\expand-sweater"),
    },
    "jacket": {
        "trigger": "charb_jacket",
        "src_dir": Path(r"E:\program\1project\video\shared\project-tools\lora\charb-jacket-v1\dataset\img\10_charb_jacket"),
        "out_dir": Path(r"E:\program\1project\video\shared\project-tools\lora\charb-jacket-v1b\dataset\img\10_charb_jacket"),
        "seed": Path(r"E:\program\1project\video\xfer\overnight-2026-09-21\charB\04-jacket.png"),
        "desc": "young adult woman, jet black hair, short black bob cut, bangs, single red hair clip, dark brown eyes, pale skin, black motorcycle jacket with asymmetric lapels zipper rivets, white t-shirt",
        "xfer": Path(r"E:\program\1project\video\xfer\soft-continue-2026-09-22\expand-jacket"),
    },
    "hoodie": {
        "trigger": "charb_hoodie",
        "src_dir": Path(r"E:\program\1project\video\shared\project-tools\lora\charb-hoodie-v1\dataset\img\10_charb_hoodie"),
        "out_dir": Path(r"E:\program\1project\video\shared\project-tools\lora\charb-hoodie-v1b\dataset\img\10_charb_hoodie"),
        "seed": Path(r"E:\program\1project\video\xfer\overnight-2026-09-21\charB\01-hoodie.png"),
        "desc": "young adult woman, jet black hair, short black hair, bangs, two red hair clips, dark brown eyes, pale skin, grey hoodie with drawstrings kangaroo pocket",
        "xfer": Path(r"E:\program\1project\video\xfer\soft-continue-2026-09-22\expand-hoodie"),
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


def try_free():
    try:
        post(f"{SERVER}/free", {"unload_models": True, "free_memory": True}, 30)
        time.sleep(1)
    except Exception:
        pass


def download(meta, dest: Path):
    q = urllib.parse.urlencode({
        "filename": meta["filename"],
        "subfolder": meta.get("subfolder") or "",
        "type": meta.get("type") or "output",
    })
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(f"{SERVER}/view?{q}", timeout=120) as r:
        dest.write_bytes(r.read())


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


def graph(init_name, style_name, pos, seed, tag):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoadImage", "inputs": {"image": init_name}},
        "3": {"class_type": "VAEEncode", "inputs": {"pixels": ["2", 0], "vae": ["1", 2]}},
        "4": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": IPA}},
        "5": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": CLIPV}},
        "6": {"class_type": "LoadImage", "inputs": {"image": style_name}},
        "7": {"class_type": "IPAdapterAdvanced", "inputs": {
            "model": ["1", 0],
            "ipadapter": ["4", 0],
            "image": ["6", 0],
            "weight": IPA_W,
            "weight_type": "style transfer",
            "combine_embeds": "concat",
            "start_at": 0.0,
            "end_at": IPA_END,
            "embeds_scaling": "V only",
            "clip_vision": ["5", 0],
        }},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["1", 1]}},
        "9": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["1", 1]}},
        "10": {"class_type": "KSampler", "inputs": {
            "model": ["7", 0], "positive": ["8", 0], "negative": ["9", 0],
            "latent_image": ["3", 0], "seed": seed, "steps": STEPS, "cfg": CFG,
            "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": DENOISE,
        }},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["1", 2]}},
        "12": {"class_type": "SaveImage", "inputs": {
            "images": ["11", 0], "filename_prefix": f"charb-soft-restyle/{tag}",
        }},
    }


def caption(cfg, stem: str) -> str:
    return (
        f"{cfg['trigger']}, 1girl, solo, {cfg['desc']}, {SOFT}, "
        f"anime style, masterpiece, best quality, simple soft grey background, "
        f"hair color is pure jet black, {stem.replace('-', ' ')}"
    )


def sources_for(cfg):
    srcs = []
    if cfg["seed"].is_file():
        srcs.append(("01-seed", cfg["seed"]))
    if cfg["src_dir"].is_dir():
        for p in sorted(cfg["src_dir"].glob("*.png")):
            stem = p.stem
            if stem.startswith("01-seed"):
                continue
            srcs.append((stem, p))
    seen = set()
    out = []
    for stem, p in srcs:
        if stem in seen:
            continue
        seen.add(stem)
        out.append((stem, p))
    return out


def run_outfit(name: str):
    cfg = OUTFITS[name]
    cfg["out_dir"].mkdir(parents=True, exist_ok=True)
    cfg["xfer"].mkdir(parents=True, exist_ok=True)
    for npz in cfg["out_dir"].glob("*.npz"):
        npz.unlink()
    if not STYLE_SRC.is_file():
        raise SystemExit(f"missing style {STYLE_SRC}")
    COMFY_INPUT.mkdir(parents=True, exist_ok=True)
    style_name = "chengwu-style-lock-ref.png"
    shutil.copy2(STYLE_SRC, COMFY_INPUT / style_name)
    wait_server()
    results = []
    for i, (stem, src) in enumerate(sources_for(cfg)):
        dest = cfg["out_dir"] / f"{stem}.png"
        init_name = f"soft-init-{name}-{stem}.png"
        shutil.copy2(src, COMFY_INPUT / init_name)
        pos = f"1girl, solo, {cfg['desc']}, {SOFT}, masterpiece, best quality, simple soft grey background"
        seed = 2026092300 + i
        print(f"[{name}] restyle {stem} from {src.name}", flush=True)
        entry = queue_wait(graph(init_name, style_name, pos, seed, f"{name}-{stem}"))
        saved = False
        for node in (entry.get("outputs") or {}).values():
            for im in node.get("images") or []:
                download(im, dest)
                txt = cfg["out_dir"] / f"{stem}.txt"
                txt.write_text(caption(cfg, stem) + "\n", encoding="utf-8")
                shutil.copy2(dest, cfg["xfer"] / dest.name)
                shutil.copy2(txt, cfg["xfer"] / txt.name)
                saved = True
                print("saved", dest, flush=True)
                break
            if saved:
                break
        if not saved:
            raise SystemExit(f"no image for {name}/{stem}")
        results.append({"stem": stem, "src": str(src), "dest": str(dest)})
        try_free()
    pngs = list(cfg["out_dir"].glob("*.png"))
    summary = {
        "ok": True,
        "outfit": name,
        "png_count": len(pngs),
        "out_dir": str(cfg["out_dir"]),
        "ipa_weight": IPA_W,
        "denoise": DENOISE,
        "results": results,
    }
    (cfg["xfer"] / "EXPAND-SOFT.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return summary


def main():
    names = sys.argv[1:] or ["sweater", "jacket", "hoodie"]
    for n in names:
        if n not in OUTFITS:
            raise SystemExit(f"unknown outfit {n}")
        run_outfit(n)
    print("ALL_EXPAND_DONE", flush=True)


if __name__ == "__main__":
    main()
