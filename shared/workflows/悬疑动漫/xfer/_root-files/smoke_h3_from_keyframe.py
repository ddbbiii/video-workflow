"""H3 I2V smoke from approved keyframes — EasyCache, ~5s, first_frame. Port 8189."""
import json, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

HOST = "127.0.0.1:8189"
H3_INPUT = Path(r"E:\program\1project\video\shared\runtime\comfy\installs\h3-runtime\input")
OUT_DIR = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\home-char-smoke\h3-motion")
XFER = Path(r"E:\program\1project\video\xfer\home-char-smoke")
SRC = {
    "K1": Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\home-char-smoke\keyframe-pose\K1-stand-living-night-out-1-2026092501.png"),
    "K2": Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\home-char-smoke\keyframe-pose\K2-half-living-day-out-1-2026092502.png"),
}
# Portrait ~same MP as 864x480 draft default
WIDTH, HEIGHT, LENGTH, STEPS = 480, 864, 124, 20
SEED_BASE = 2026092601

PROMPTS = {
    "K1": (
        "anime style, the same young woman standing in a cozy night living room, "
        "subtle natural breathing, slight hair movement, soft blink, very gentle camera push-in, "
        "city lights outside the window, warm lamp light, keep face and outfit stable, "
        "no morphing, no extra people. Audio: quiet room tone, soft distant city hum, no speech, no music."
    ),
    "K2": (
        "anime style, the same young woman half-body in a bright daytime living room, "
        "subtle breathing, slight head turn toward camera, soft blink, gentle hair sway, "
        "soft daylight from window, keep identity and teal outfit stable, "
        "no morphing, no extra people. Audio: quiet indoor ambience, no speech, no music."
    ),
}


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
    raise SystemExit("H3 8189 down")


def build(img_name, prompt, seed, tag):
    model_ref = ["1", 0]
    g = {
        "1": {"class_type": "UNETLoader", "inputs": {
            "unet_name": "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
            "weight_dtype": "default",
        }},
        "1b": {"class_type": "EasyCache", "inputs": {
            "model": ["1", 0],
            "reuse_threshold": 0.2,
            "start_percent": 0.15,
            "end_percent": 0.95,
            "verbose": False,
        }},
        "2": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
            "type": "minimax",
            "device": "default",
        }},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_fp16.safetensors"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"}},
        "5": {"class_type": "LoadImage", "inputs": {"image": img_name}},
        "6": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {
            "clip": ["2", 0],
            "vae": ["3", 0],
            "prompt": prompt,
            "width": WIDTH,
            "height": HEIGHT,
            "length": LENGTH,
            "first_frame": ["5", 0],
        }},
        "7": {"class_type": "BasicGuider", "inputs": {"model": ["1b", 0], "conditioning": ["6", 0]}},
        "8": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
        "9": {"class_type": "BasicScheduler", "inputs": {
            "model": ["1b", 0], "scheduler": "simple", "steps": STEPS, "denoise": 1.0,
        }},
        "10": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
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
            "video": ["14", 0],
            "filename_prefix": f"chengwu-h3/{tag}",
            "format": "auto",
            "codec": "auto",
        }},
    }
    return g


def queue_wait(g, label, timeout=3600):
    resp = post("/prompt", {"prompt": g, "client_id": str(uuid.uuid4())})
    if resp.get("node_errors"):
        raise SystemExit(f"node_errors {label}: {resp['node_errors']}")
    pid = resp["prompt_id"]
    print(f"queued {label} {pid}", flush=True)
    t0 = time.time()
    while time.time() - t0 < timeout:
        hist = get(f"/history/{pid}", 120)
        if pid in hist:
            entry = hist[pid]
            st = entry.get("status") or {}
            if st.get("status_str") == "error":
                raise SystemExit(f"error {label}: {st.get('messages')}")
            return entry
        # progress heartbeat
        if int(time.time() - t0) % 60 < 3:
            print(f"... still running {label} {int(time.time()-t0)}s", flush=True)
        time.sleep(5)
    raise TimeoutError(label)


def main():
    wait_up()
    H3_INPUT.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    XFER.mkdir(parents=True, exist_ok=True)
    jobs = ["K1", "K2"]  # serial
    for i, key in enumerate(jobs):
        src = SRC[key]
        if not src.exists():
            raise SystemExit(f"missing {src}")
        name = f"h3-first-{key}.png"
        shutil.copy2(src, H3_INPUT / name)
        tag = f"{key}-easycache-480x864-124f"
        seed = SEED_BASE + i
        print(f"=== {tag} ===", flush=True)
        entry = queue_wait(build(name, PROMPTS[key], seed, tag), tag)
        # collect videos from outputs
        videos = []
        for o in (entry.get("outputs") or {}).values():
            for v in o.get("videos") or o.get("gifs") or []:
                videos.append(v)
            for im in o.get("images") or []:
                videos.append(im)  # fallback
        print("outputs keys", list((entry.get("outputs") or {}).keys()), flush=True)
        print("video metas", videos, flush=True)
        # also scan output dir for newest
        out_root = Path(r"E:\program\1project\video\shared\runtime\comfy\installs\h3-runtime\output")
        found = sorted(out_root.rglob(f"*{key}*"), key=lambda p: p.stat().st_mtime, reverse=True)
        for f in found[:5]:
            dest = OUT_DIR / f.name
            shutil.copy2(f, dest)
            shutil.copy2(f, XFER / f.name)
            print("copied", f, "->", dest, flush=True)
        try:
            post("/free", {"unload_models": True, "free_memory": True})
            time.sleep(3)
        except Exception:
            pass
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
