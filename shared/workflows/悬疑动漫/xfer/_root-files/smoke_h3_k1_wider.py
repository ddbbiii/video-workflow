"""Re-render K1 H3 with aspect closer to keyframe (~2:3), not ultra-narrow 480x864."""
import json, time, urllib.request, uuid, shutil
from pathlib import Path

HOST = "127.0.0.1:8189"
H3_INPUT = Path(r"E:\program\1project\video\shared\runtime\comfy\installs\h3-runtime\input")
OUT_DIR = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\home-char-smoke\h3-motion")
XFER = Path(r"E:\program\1project\video\xfer\home-char-smoke")
SRC = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\home-char-smoke\keyframe-pose\K1-stand-living-night-out-1-2026092501.png")
# Match keyframe ~832x1216 (2:3): use 576x864 (also 2:3), step-32 friendly
WIDTH, HEIGHT, LENGTH, STEPS, SEED = 576, 864, 124, 20, 2026092701
TAG = "K1-easycache-576x864-124f-v2"
PROMPT = (
    "anime style, the same young woman standing in a cozy night living room, "
    "subtle natural breathing, slight hair movement, soft blink, very gentle camera push-in, "
    "city lights outside the window, warm lamp light, keep face and outfit stable, "
    "natural body proportions, no morphing, no extra people. "
    "Audio: quiet room tone, soft distant city hum, no speech, no music."
)


def get(path, timeout=60):
    with urllib.request.urlopen(f"http://{HOST}{path}", timeout=timeout) as r:
        return json.loads(r.read())


def post(path, obj, timeout=180):
    data = json.dumps(obj).encode()
    req = urllib.request.Request(
        f"http://{HOST}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def wait_up():
    for _ in range(40):
        try:
            get("/system_stats", 5)
            return
        except Exception:
            time.sleep(2)
    raise SystemExit("H3 down")


def build(img_name):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {
            "unet_name": "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
            "weight_dtype": "default",
        }},
        "1b": {"class_type": "EasyCache", "inputs": {
            "model": ["1", 0], "reuse_threshold": 0.2,
            "start_percent": 0.15, "end_percent": 0.95, "verbose": False,
        }},
        "2": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
            "type": "minimax", "device": "default",
        }},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_fp16.safetensors"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"}},
        "5": {"class_type": "LoadImage", "inputs": {"image": img_name}},
        "6": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {
            "clip": ["2", 0], "vae": ["3", 0], "prompt": PROMPT,
            "width": WIDTH, "height": HEIGHT, "length": LENGTH,
            "first_frame": ["5", 0],
        }},
        "7": {"class_type": "BasicGuider", "inputs": {"model": ["1b", 0], "conditioning": ["6", 0]}},
        "8": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
        "9": {"class_type": "BasicScheduler", "inputs": {
            "model": ["1b", 0], "scheduler": "simple", "steps": STEPS, "denoise": 1.0,
        }},
        "10": {"class_type": "RandomNoise", "inputs": {"noise_seed": SEED}},
        "11": {"class_type": "SamplerCustomAdvanced", "inputs": {
            "noise": ["10", 0], "guider": ["7", 0], "sampler": ["8", 0],
            "sigmas": ["9", 0], "latent_image": ["6", 1],
        }},
        "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["3", 0]}},
        "13": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["11", 0], "vae": ["4", 0]}},
        "14": {"class_type": "CreateVideo", "inputs": {
            "images": ["12", 0], "fps": 24.0, "audio": ["13", 0],
        }},
        "15": {"class_type": "SaveVideo", "inputs": {
            "video": ["14", 0], "filename_prefix": f"chengwu-h3/{TAG}",
            "format": "auto", "codec": "auto",
        }},
    }


def main():
    wait_up()
    H3_INPUT.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    XFER.mkdir(parents=True, exist_ok=True)
    name = "h3-first-K1.png"
    shutil.copy2(SRC, H3_INPUT / name)
    print(f"=== {TAG} {WIDTH}x{HEIGHT} ===", flush=True)
    resp = post("/prompt", {"prompt": build(name), "client_id": str(uuid.uuid4())})
    if resp.get("node_errors"):
        raise SystemExit(resp["node_errors"])
    pid = resp["prompt_id"]
    print("queued", pid, flush=True)
    t0 = time.time()
    while time.time() - t0 < 3600:
        hist = get(f"/history/{pid}", 120)
        if pid in hist:
            st = (hist[pid].get("status") or {})
            if st.get("status_str") == "error":
                raise SystemExit(st.get("messages"))
            break
        if int(time.time() - t0) % 60 < 5:
            print(f"... {int(time.time()-t0)}s", flush=True)
        time.sleep(5)
    else:
        raise TimeoutError(pid)
    out_root = Path(r"E:\program\1project\video\shared\runtime\comfy\installs\h3-runtime\output\chengwu-h3")
    found = sorted(out_root.glob(f"{TAG}*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not found:
        found = sorted(out_root.glob("*K1*576*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in found[:2]:
        shutil.copy2(f, OUT_DIR / f.name)
        shutil.copy2(f, XFER / f.name)
        print("copied", f, flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
