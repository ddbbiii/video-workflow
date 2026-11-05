"""Overnight runner until ~04:00 Asia/Shanghai: keyframes then H3. Locked defaults."""
import json, time, urllib.request, urllib.parse, uuid, shutil, traceback
from pathlib import Path
from datetime import datetime

TZ_NOTE = "Asia/Shanghai"
DEADLINE_HOUR = 4  # stop starting new heavy jobs after 04:00
OUT = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\overnight-2026-09-21")
XFER = Path(r"E:\program\1project\video\xfer\overnight-2026-09-21")
COMFY_IN = Path(r"E:\program\1project\video\shared\project-tools\production\comfyui-input")
POSE_DIR = Path(r"E:\program\1project\video\xfer\pose-refs")
H3_IN = Path(r"E:\program\1project\video\shared\runtime\comfy\installs\h3-runtime\input")
STATUS = OUT / "STATUS.md"
RESULTS = OUT / "OVERNIGHT-RESULTS.md"

CKPT = "animagine-xl-4.0-opt.safetensors"
CHAR = "chengwu-sdxl-v1b.safetensors"
SCENE = "jiaoli-home-sdxl-v1.safetensors"
CN = "xinsir-controlnet-union-sdxl-1.0.safetensors"
CHAR_BASE = (
    "chengwu, 程雾, 1girl, young adult, short grey-blue bob hair, brown eyes, pale skin, "
    "thin black choker with silver ring, teal long-sleeve scoop-neck top, anime style, masterpiece, best quality"
)
NEG = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, "
    "cropped, worst quality, low quality, jpeg artifacts, signature, watermark, blurry, "
    "loli, child, photorealistic, extra people, crowd, multiple girls, deformed face"
)

JOBS = [
    ("N1-phone-night", "pose-ref-half.png", 2026092801, 832, 1216, "half",
     f"{CHAR_BASE}, half body, looking at smartphone, slight concern, jiaoli_home, living room, night, sofa, floor lamp, city lights"),
    ("N2-doorway", "pose-ref-standing.png", 2026092802, 832, 1216, "full",
     f"{CHAR_BASE}, full body, standing near doorway, looking back, jiaoli_home, home entry, soft indoor light"),
    ("N3-sit-talk", "pose-ref-half.png", 2026092803, 832, 1216, "half",
     f"{CHAR_BASE}, sitting, talking gesture, slight smile, jiaoli_home, living room, daytime, sofa, window"),
    ("N4-window", "pose-ref-standing.png", 2026092804, 832, 1216, "full",
     f"{CHAR_BASE}, full body, standing by window, looking outside, jiaoli_home, living room, night, city lights"),
]


def log(msg):
    OUT.mkdir(parents=True, exist_ok=True)
    XFER.mkdir(parents=True, exist_ok=True)
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(STATUS, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def past_deadline():
    return datetime.now().hour >= DEADLINE_HOUR and datetime.now().hour < 10


def get(host, path, timeout=60):
    with urllib.request.urlopen(f"http://{host}{path}", timeout=timeout) as r:
        return json.loads(r.read())


def post(host, path, obj, timeout=180):
    data = json.dumps(obj).encode()
    req = urllib.request.Request(
        f"http://{host}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def wait(host, n=40):
    for _ in range(n):
        try:
            get(host, "/system_stats", 3)
            return True
        except Exception:
            time.sleep(2)
    return False


def queue_wait(host, g, label, timeout=3600):
    resp = post(host, "/prompt", {"prompt": g, "client_id": str(uuid.uuid4())})
    if resp.get("node_errors"):
        raise RuntimeError(f"node_errors {label}: {resp['node_errors']}")
    pid = resp["prompt_id"]
    log(f"queued {label} {pid} on {host}")
    t0 = time.time()
    while time.time() - t0 < timeout:
        hist = get(host, f"/history/{pid}", 120)
        if pid in hist:
            st = hist[pid].get("status") or {}
            if st.get("status_str") == "error":
                raise RuntimeError(f"error {label}: {st.get('messages')}")
            return hist[pid]
        time.sleep(5)
    raise TimeoutError(label)


def download(host, meta, dest: Path):
    q = urllib.parse.urlencode({
        "filename": meta["filename"],
        "subfolder": meta.get("subfolder") or "",
        "type": meta.get("type") or "output",
    })
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(f"http://{host}/view?{q}", timeout=180) as r:
        dest.write_bytes(r.read())


def free(host):
    try:
        post(host, "/free", {"unload_models": True, "free_memory": True}, 30)
        time.sleep(2)
    except Exception:
        pass


def keyframe_graph(pose_name, pos, seed, w, h, tag):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoraLoader", "inputs": {
            "model": ["1", 0], "clip": ["1", 1],
            "lora_name": CHAR, "strength_model": 0.88, "strength_clip": 0.82,
        }},
        "3": {"class_type": "LoraLoader", "inputs": {
            "model": ["2", 0], "clip": ["2", 1],
            "lora_name": SCENE, "strength_model": 0.75, "strength_clip": 0.68,
        }},
        "4": {"class_type": "LoadImage", "inputs": {"image": pose_name}},
        "5": {"class_type": "OpenposePreprocessor", "inputs": {
            "image": ["4", 0], "detect_hand": "disable", "detect_body": "enable",
            "detect_face": "disable", "resolution": 512, "scale_stick_for_xinsr_cn": "enable",
        }},
        "6": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": CN}},
        "7": {"class_type": "SetUnionControlNetType", "inputs": {"control_net": ["6", 0], "type": "openpose"}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["3", 1]}},
        "9": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["3", 1]}},
        "10": {"class_type": "ControlNetApplyAdvanced", "inputs": {
            "positive": ["8", 0], "negative": ["9", 0], "control_net": ["7", 0],
            "image": ["5", 0], "strength": 0.55, "start_percent": 0.0, "end_percent": 0.85,
            "vae": ["1", 2],
        }},
        "11": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "12": {"class_type": "KSampler", "inputs": {
            "model": ["3", 0], "positive": ["10", 0], "negative": ["10", 1],
            "latent_image": ["11", 0], "seed": seed, "steps": 28, "cfg": 5.3,
            "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": 1.0,
        }},
        "13": {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["1", 2]}},
        "14": {"class_type": "SaveImage", "inputs": {
            "images": ["13", 0], "filename_prefix": f"overnight/{tag}",
        }},
    }


def h3_graph(img_name, prompt, seed, w, h, tag):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {
            "unet_name": "minimax_h3_fl2va_pruned_int8_convrot.safetensors", "weight_dtype": "default",
        }},
        "1b": {"class_type": "EasyCache", "inputs": {
            "model": ["1", 0], "reuse_threshold": 0.2, "start_percent": 0.15, "end_percent": 0.95, "verbose": False,
        }},
        "2": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "type": "minimax", "device": "default",
        }},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_fp16.safetensors"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"}},
        "5": {"class_type": "LoadImage", "inputs": {"image": img_name}},
        "6": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {
            "clip": ["2", 0], "vae": ["3", 0], "prompt": prompt,
            "width": w, "height": h, "length": 124, "first_frame": ["5", 0],
        }},
        "7": {"class_type": "BasicGuider", "inputs": {"model": ["1b", 0], "conditioning": ["6", 0]}},
        "8": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
        "9": {"class_type": "BasicScheduler", "inputs": {
            "model": ["1b", 0], "scheduler": "simple", "steps": 20, "denoise": 1.0,
        }},
        "10": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "11": {"class_type": "SamplerCustomAdvanced", "inputs": {
            "noise": ["10", 0], "guider": ["7", 0], "sampler": ["8", 0],
            "sigmas": ["9", 0], "latent_image": ["6", 1],
        }},
        "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["3", 0]}},
        "13": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["11", 0], "vae": ["4", 0]}},
        "14": {"class_type": "CreateVideo", "inputs": {"images": ["12", 0], "fps": 24.0, "audio": ["13", 0]}},
        "15": {"class_type": "SaveVideo", "inputs": {
            "video": ["14", 0], "filename_prefix": f"overnight-h3/{tag}", "format": "auto", "codec": "auto",
        }},
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    XFER.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(f"# Overnight results {datetime.now().isoformat()}\n\n", encoding="utf-8")
    log("START overnight runner")
    if not wait("127.0.0.1:8188"):
        log("FAIL 8188 not up")
        return
    keyframes = []
    for tag, pose, seed, w, h, kind, pos in JOBS:
        if past_deadline():
            log("deadline reached before more keyframes")
            break
        src = POSE_DIR / pose
        if not src.exists():
            log(f"skip missing pose {src}")
            continue
        shutil.copy2(src, COMFY_IN / pose)
        try:
            hist = queue_wait("127.0.0.1:8188", keyframe_graph(pose, pos, seed, w, h, tag), tag)
            imgs = []
            for o in hist.get("outputs", {}).values():
                imgs.extend(o.get("images", []))
            if not imgs:
                raise RuntimeError("no images")
            dest = OUT / f"{tag}.png"
            download("127.0.0.1:8188", imgs[0], dest)
            shutil.copy2(dest, XFER / dest.name)
            keyframes.append((tag, dest, kind))
            with open(RESULTS, "a", encoding="utf-8") as f:
                f.write(f"- KEYFRAME {tag}: {dest}\n")
            log(f"OK keyframe {tag}")
            free("127.0.0.1:8188")
        except Exception as e:
            log(f"FAIL keyframe {tag}: {e}\n{traceback.format_exc()}")
    log(f"keyframes done count={len(keyframes)}")
    # Hand off note: parent/H3 start separately if needed — try H3 if already up
    if past_deadline():
        log("skip H3 due to deadline")
        return
    if not wait("127.0.0.1:8189", 5):
        log("H3 8189 not up — write NEED_H3 flag")
        (OUT / "NEED_H3").write_text("start h3 then re-run h3 portion\n", encoding="utf-8")
        return
    for tag, path, kind in keyframes:
        if past_deadline():
            log("deadline during H3")
            break
        w, h = (576, 864) if kind == "full" else (480, 864)
        name = f"h3-{tag}.png"
        H3_IN.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, H3_IN / name)
        prompt = (
            f"anime style, same young woman, subtle breathing and natural micro-motion, "
            f"gentle camera, keep face and teal outfit stable, home interior, no morphing, no extra people. "
            f"Audio: quiet room tone, no speech, no music."
        )
        try:
            queue_wait("127.0.0.1:8189", h3_graph(name, prompt, 2026092900 + hash(tag) % 1000, w, h, tag), f"H3-{tag}", 3600)
            out_root = Path(r"E:\program\1project\video\shared\runtime\comfy\installs\h3-runtime\output\overnight-h3")
            found = sorted(out_root.glob(f"{tag}*"), key=lambda p: p.stat().st_mtime, reverse=True) if out_root.exists() else []
            if not found:
                found = sorted(Path(r"E:\program\1project\video\shared\runtime\comfy\installs\h3-runtime\output").rglob(f"*{tag}*"), key=lambda p: p.stat().st_mtime, reverse=True)[:3]
            for f in found[:2]:
                shutil.copy2(f, OUT / f.name)
                shutil.copy2(f, XFER / f.name)
                with open(RESULTS, "a", encoding="utf-8") as rf:
                    rf.write(f"- H3 {tag}: {f}\n")
            log(f"OK H3 {tag}")
            free("127.0.0.1:8189")
        except Exception as e:
            log(f"FAIL H3 {tag}: {e}")
    log("DONE overnight runner")


if __name__ == "__main__":
    main()
