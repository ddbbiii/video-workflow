# -*- coding: utf-8 -*-
"""Hoodie-Male v2 HARD masculine seed redesign pack.
A) Pure txt2img (Animagine only, NO LoRA, NO soft-M1 img2img base) — escape face family.
B) High-denoise img2img from M1 at 0.68 / 0.75 as alternate candidates (clearly labeled).
Does NOT wipe soft 21-png dataset. Does NOT expand. Does NOT train. Does NOT dual-frame.
Requires ComfyUI on 127.0.0.1:8188.
"""
from __future__ import annotations
import json, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
CKPT = "animagine-xl-4.0-opt.safetensors"
COMFY_INPUT = Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input")

M1_CANDIDATES = [
    Path(r"E:\program\1project\video\xfer\soft-continue-2026-09-22\smoke\charb_hoodie_male\M1-front-half.png"),
    Path(r"E:\program\1project\video\xfer\soft-continue-2026-09-22\v2-retrain\review\M1-source.png"),
    Path(r"E:\program\1project\video\shared\project-tools\lora\charb-hoodie-male-v2\dataset\img\10_charb_hoodie_male\01-seed-masc.png"),
]

# Primary outputs (Desktop — CopyToBox friendly)
OUT_HARD = Path(r"E:\program\1project\video\xfer\soft-continue-2026-09-22\v2-retrain\seed-redesign-hard")
REVIEW = Path(r"E:\program\1project\video\xfer\soft-continue-2026-09-22\v2-retrain\review\seed-redesign-hard")
# Staging under project (do NOT touch 10_charb_hoodie_male soft set)
STAGING = Path(r"E:\program\1project\video\shared\project-tools\lora\charb-hoodie-male-v2\seed-candidates")
SCRATCH = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\charb-hoodie-male-v2-seed-hard")
XFER = Path(r"E:\program\1project\video\xfer\soft-continue-2026-09-22\seed-redesign-hard-xfer")

STEPS, CFG = 30, 6.0
W, H = 896, 1152  # portrait

POS = (
    "1boy, solo, young adult man, CLEARLY MALE, adult male, masculine bone structure, "
    "strong angular male jaw, squared chin, wide jaw, firm chin, "
    "thicker muscular neck, visible adam's apple, "
    "narrower male eyes, smaller eyes than girl, less sparkly eyes, sharp male gaze, "
    "broader shoulders, wide clavicle, flat chest, male torso, masculine proportions, "
    "short messy jet black hair, layered short hair, spiky bangs, NOT bob, NOT long hair, "
    "warm brown eyes, fair skin with warm undertone, "
    "oversized dark charcoal navy hoodie with drawstrings, hood down, "
    "upper body, front three-quarter, looking at viewer, "
    "soft cel shading, soft lighting, clean soft lineart, "
    "masterpiece, best quality, simple soft grey background"
)
NEG = (
    "1girl, woman, female, chengwu, pretty boy, bishounen, androgynous, trap, futa, otoko no ko, "
    "feminine face, soft feminine jaw, soft V-shaped chin, pointed delicate chin, "
    "large sparkly girl eyes, big doe eyes, long eyelashes exaggerated, "
    "lean slender girl neck, thin neck, narrow girl shoulders, breasts, cleavage, slim girl waist, "
    "grey-blue hair, short bob cut, bob hair, black choker, teal scoop-neck, "
    "lipstick, makeup, hair clip, hairpin, earrings, "
    "loli, child, chibi, teenager boy cute, shota, "
    "lowres, bad anatomy, bad hands, text, error, "
    "missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, "
    "jpeg artifacts, signature, watermark, blurry, photorealistic, extra people, "
    "multiple boys, deformed face, harsh comic lines, thick ink outlines, western comic, "
    "pink hair, blue hair, long hair, twin tails"
)

# A) Pure txt2img — 8 candidates, varied seeds (NO img2img from soft M1)
TXT2IMG_JOBS = [
    ("T01-txt2img-s101", 20260923101),
    ("T02-txt2img-s102", 20260923102),
    ("T03-txt2img-s103", 20260923103),
    ("T04-txt2img-s104", 20260923104),
    ("T05-txt2img-s105", 20260923105),
    ("T06-txt2img-s106", 20260923106),
    ("T07-txt2img-s107", 20260923107),
    ("T08-txt2img-s108", 20260923108),
]

# B) High-denoise img2img from M1 — alternate candidates, labeled
# denoise 0.68 x 3 seeds, denoise 0.75 x 3 seeds
I2I_JOBS = [
    ("I01-i2i-d068-s201", 0.68, 20260923201),
    ("I02-i2i-d068-s202", 0.68, 20260923202),
    ("I03-i2i-d068-s203", 0.68, 20260923203),
    ("I04-i2i-d075-s301", 0.75, 20260923301),
    ("I05-i2i-d075-s302", 0.75, 20260923302),
    ("I06-i2i-d075-s303", 0.75, 20260923303),
]


def get(url, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def post(url, obj, timeout=180):
    data = json.dumps(obj).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def wait_server(tries=60):
    for _ in range(tries):
        try:
            get(f"{SERVER}/system_stats", 3)
            return
        except Exception:
            time.sleep(2)
    raise SystemExit("Comfy 8188 not up — start ComfyUI first")


def graph_txt2img(pos, seed, w, h, tag):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["1", 1]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["1", 1]}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["3", 0], "negative": ["4", 0],
            "latent_image": ["5", 0], "seed": seed, "steps": STEPS, "cfg": CFG,
            "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": 1.0,
        }},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {
            "images": ["7", 0], "filename_prefix": f"charb-hoodie-male-v2-seed-hard/{tag}",
        }},
    }


def graph_img2img(input_name, pos, seed, denoise, tag):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoadImage", "inputs": {"image": input_name}},
        "3": {"class_type": "VAEEncode", "inputs": {"pixels": ["2", 0], "vae": ["1", 2]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["1", 1]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["1", 1]}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["4", 0], "negative": ["5", 0],
            "latent_image": ["3", 0], "seed": seed, "steps": STEPS, "cfg": CFG,
            "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": denoise,
        }},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {
            "images": ["7", 0], "filename_prefix": f"charb-hoodie-male-v2-seed-hard/{tag}",
        }},
    }


def queue_wait(g):
    resp = post(f"{SERVER}/prompt", {"prompt": g, "client_id": str(uuid.uuid4())})
    if resp.get("node_errors"):
        raise SystemExit("node_errors " + json.dumps(resp["node_errors"], ensure_ascii=False))
    pid = resp["prompt_id"]
    print("queued", pid, flush=True)
    t0 = time.time()
    while time.time() - t0 < 600:
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


def pick_m1() -> Path:
    for p in M1_CANDIDATES:
        if p.is_file():
            return p
    raise SystemExit("no M1 source found for high-denoise i2i")


def mirror_all(dest: Path):
    """Copy dest png into mirror roots (skip same-path; OUT_HARD already has file)."""
    dest_r = dest.resolve()
    for root in (OUT_HARD, STAGING, XFER, REVIEW):
        root.mkdir(parents=True, exist_ok=True)
        target = (root / dest.name).resolve()
        if target == dest_r:
            continue
        # retry briefly if AV locks the fresh write
        last = None
        for _ in range(8):
            try:
                shutil.copy2(dest, target)
                last = None
                break
            except PermissionError as e:
                last = e
                time.sleep(0.4)
        if last is not None:
            raise last


def save_from_entry(entry, stem: str, kind: str, meta: dict, results: list):
    saved = False
    for node in (entry.get("outputs") or {}).values():
        for im in node.get("images") or []:
            tmp = SCRATCH / f"{stem}-{im['filename']}"
            download(im, tmp)
            dest = OUT_HARD / f"{stem}.png"
            OUT_HARD.mkdir(parents=True, exist_ok=True)
            shutil.copy2(tmp, dest)
            mirror_all(dest)
            note = {
                "stem": stem,
                "kind": kind,
                **meta,
                "path_desktop": str(OUT_HARD / f"{stem}.png"),
                "path_staging": str(STAGING / f"{stem}.png"),
                "path_review": str(REVIEW / f"{stem}.png"),
            }
            (OUT_HARD / f"{stem}.json").write_text(
                json.dumps(note, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            for root in (STAGING, XFER, REVIEW):
                shutil.copy2(OUT_HARD / f"{stem}.json", root / f"{stem}.json")
            results.append(note)
            print("saved", dest, kind, meta, flush=True)
            saved = True
            break
        if saved:
            break
    if not saved:
        raise SystemExit(f"no image for {stem}")
    try_free()


def main():
    for d in (OUT_HARD, STAGING, XFER, REVIEW, SCRATCH, COMFY_INPUT):
        d.mkdir(parents=True, exist_ok=True)

    # Clear ONLY redesign-hard / seed-candidates / review subfolder — NEVER the soft 21-png dataset
    soft_dataset = Path(r"E:\program\1project\video\shared\project-tools\lora\charb-hoodie-male-v2\dataset\img\10_charb_hoodie_male")
    assert soft_dataset.is_dir(), "soft dataset missing — abort (safety)"
    soft_pngs_before = sorted(p.name for p in soft_dataset.glob("*.png"))

    for root in (OUT_HARD, STAGING, XFER, REVIEW):
        for old in root.glob("*"):
            if old.is_file():
                old.unlink()

    wait_server()
    results = []

    # --- A) Pure txt2img ---
    print("=== A) TXT2IMG batch (Animagine only, no LoRA, no soft-M1) ===", flush=True)
    for stem, seed in TXT2IMG_JOBS:
        print(f"run {stem} seed={seed} {W}x{H}", flush=True)
        entry = queue_wait(graph_txt2img(POS, seed, W, H, stem))
        save_from_entry(entry, stem, "txt2img", {"seed": seed, "w": W, "h": H, "denoise": 1.0}, results)

    # --- B) High-denoise img2img from M1 ---
    m1 = pick_m1()
    print("=== B) HIGH-DENOISE img2img from M1 ===", m1, flush=True)
    input_name = "charb-hoodie-male-v2-m1-softref-hardseed.png"
    shutil.copy2(m1, COMFY_INPUT / input_name)
    # also keep M1 copy in review for eye-check side-by-side
    shutil.copy2(m1, REVIEW / "M1-source-ref.png")
    shutil.copy2(m1, OUT_HARD / "M1-source-ref.png")

    for stem, denoise, seed in I2I_JOBS:
        print(f"run {stem} denoise={denoise} seed={seed}", flush=True)
        entry = queue_wait(graph_img2img(input_name, POS, seed, denoise, stem))
        save_from_entry(
            entry, stem, "img2img-high-denoise",
            {"seed": seed, "denoise": denoise, "src": str(m1)},
            results,
        )

    soft_pngs_after = sorted(p.name for p in soft_dataset.glob("*.png"))
    if soft_pngs_before != soft_pngs_after:
        raise SystemExit("SAFETY FAIL: soft 21-png dataset changed — abort")

    summary = {
        "ok": True,
        "version": "seed-redesign-hard-v2",
        "ckpt": CKPT,
        "no_lora": True,
        "txt2img_count": len(TXT2IMG_JOBS),
        "i2i_count": len(I2I_JOBS),
        "size": [W, H],
        "m1_src": str(m1),
        "out_hard": str(OUT_HARD),
        "staging": str(STAGING),
        "review_desktop": str(REVIEW),
        "xfer": str(XFER),
        "soft_dataset_untouched": True,
        "soft_png_count": len(soft_pngs_after),
        "note": (
            "EYE-CHECK: pick TOP 1-2 CLEARLY more male / farther from Chengwu soft face. "
            "If ALL still soft, Animagine txt2img alone may be limited — consider pose ControlNet + different male ref."
        ),
        "results": results,
    }
    for root in (OUT_HARD, STAGING, XFER, REVIEW):
        (root / "SEED-REDESIGN-HARD.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
