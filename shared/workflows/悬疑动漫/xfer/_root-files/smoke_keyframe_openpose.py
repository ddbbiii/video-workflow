"""Keyframe smoke: Chengwu v1b + jiaoli_home + OpenPose (union CN)."""
import json, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
CKPT = "animagine-xl-4.0-opt.safetensors"
CHAR_LORA = "chengwu-sdxl-v1b.safetensors"
SCENE_LORA = "jiaoli-home-sdxl-v1.safetensors"
CN = "xinsir-controlnet-union-sdxl-1.0.safetensors"
CHAR_SM, CHAR_SC = 0.88, 0.82
SCENE_SM, SCENE_SC = 0.75, 0.68
CN_STRENGTH = 0.55
STEPS, CFG = 28, 5.3
COMFY_INPUT = Path(r"E:\program\1project\video\shared\project-tools\production\comfyui-input")
OUT_DIR = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\home-char-smoke\keyframe-pose")
XFER = Path(r"E:\program\1project\video\xfer\home-char-smoke")
STAGED = Path(r"E:\program\1project\video\xfer\pose-refs")

CHAR = (
    "chengwu, 程雾, 1girl, young adult, short grey-blue bob hair, brown eyes, pale skin, "
    "thin black choker with silver ring, teal long-sleeve scoop-neck top, "
    "anime style, masterpiece, best quality"
)
NEG = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, "
    "cropped, worst quality, low quality, jpeg artifacts, signature, watermark, blurry, "
    "loli, child, photorealistic, extra people, crowd, multiple girls, deformed face"
)

JOBS = [
    ("K1-stand-living-night", "pose-ref-standing.png", 2026092501, 832, 1216,
     f"{CHAR}, full body, standing, looking at viewer, jiaoli_home, indoor home interior, living room, night, sofa, floor lamp, city lights"),
    ("K2-half-living-day", "pose-ref-half.png", 2026092502, 832, 1216,
     f"{CHAR}, half body, three-quarter view, looking at viewer, jiaoli_home, indoor home interior, living room, daytime, sofa, window, soft daylight"),
]


def get(url, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def post(url, obj, timeout=180):
    data = json.dumps(obj).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def wait_server():
    for _ in range(40):
        try:
            get(f"{SERVER}/system_stats", 3)
            return
        except Exception:
            time.sleep(2)
    raise SystemExit("Comfy down")


def graph(pose_name, pos, seed, w, h, tag):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoraLoader", "inputs": {
            "model": ["1", 0], "clip": ["1", 1],
            "lora_name": CHAR_LORA, "strength_model": CHAR_SM, "strength_clip": CHAR_SC,
        }},
        "3": {"class_type": "LoraLoader", "inputs": {
            "model": ["2", 0], "clip": ["2", 1],
            "lora_name": SCENE_LORA, "strength_model": SCENE_SM, "strength_clip": SCENE_SC,
        }},
        "4": {"class_type": "LoadImage", "inputs": {"image": pose_name}},
        "5": {"class_type": "OpenposePreprocessor", "inputs": {
            "image": ["4", 0],
            "detect_hand": "disable",
            "detect_body": "enable",
            "detect_face": "disable",
            "resolution": 512,
            "scale_stick_for_xinsr_cn": "enable",
        }},
        "6": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": CN}},
        "7": {"class_type": "SetUnionControlNetType", "inputs": {
            "control_net": ["6", 0], "type": "openpose",
        }},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["3", 1]}},
        "9": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["3", 1]}},
        "10": {"class_type": "ControlNetApplyAdvanced", "inputs": {
            "positive": ["8", 0], "negative": ["9", 0],
            "control_net": ["7", 0], "image": ["5", 0],
            "strength": CN_STRENGTH, "start_percent": 0.0, "end_percent": 0.85,
            "vae": ["1", 2],
        }},
        "11": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "12": {"class_type": "KSampler", "inputs": {
            "model": ["3", 0],
            "positive": ["10", 0], "negative": ["10", 1],
            "latent_image": ["11", 0],
            "seed": seed, "steps": STEPS, "cfg": CFG,
            "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": 1.0,
        }},
        "13": {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["1", 2]}},
        "14": {"class_type": "SaveImage", "inputs": {
            "images": ["13", 0], "filename_prefix": f"keyframe-pose/{tag}-{seed}",
        }},
        # also save pose map for debug
        "15": {"class_type": "SaveImage", "inputs": {
            "images": ["5", 0], "filename_prefix": f"keyframe-pose/{tag}-pose-{seed}",
        }},
    }


def queue_wait(g):
    resp = post(f"{SERVER}/prompt", {"prompt": g, "client_id": str(uuid.uuid4())})
    if resp.get("node_errors"):
        raise SystemExit("node_errors " + json.dumps(resp["node_errors"]))
    pid = resp["prompt_id"]
    print("queued", pid, flush=True)
    t0 = time.time()
    while time.time() - t0 < 900:
        hist = get(f"{SERVER}/history/{pid}")
        if pid in hist:
            entry = hist[pid]
            st = entry.get("status") or {}
            if st.get("status_str") == "error":
                raise SystemExit("comfy error " + json.dumps(st.get("messages")))
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
        time.sleep(2)
    except Exception:
        pass


def main():
    wait_server()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    XFER.mkdir(parents=True, exist_ok=True)
    for tag, pose_file, seed, w, h, pos in JOBS:
        src = STAGED / pose_file
        if not src.exists():
            raise SystemExit(f"missing pose {src}")
        shutil.copy2(src, COMFY_INPUT / pose_file)
        print("===", tag, "===", flush=True)
        hist = queue_wait(graph(pose_file, pos, seed, w, h, tag))
        outs = []
        for o in hist.get("outputs", {}).values():
            outs.extend(o.get("images", []))
        if not outs:
            raise SystemExit("no images " + tag)
        for i, meta in enumerate(outs):
            suffix = "pose" if "pose" in meta.get("filename", "") else "out"
            # prefer non-pose as main; save all
            dest = OUT_DIR / f"{tag}-{suffix}-{i}-{seed}.png"
            download(meta, dest)
            shutil.copy2(dest, XFER / dest.name)
            print("saved", dest, flush=True)
        try_free()
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
