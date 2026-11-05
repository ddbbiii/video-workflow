# -*- coding: utf-8 -*-
"""Chengwu home longform: H3 ~5s serial chain + overlap xfade to ~30-60s."""
from __future__ import annotations
import json, time, uuid, shutil, subprocess, traceback
from pathlib import Path
from datetime import datetime
from urllib import request as urlreq

HOST = "127.0.0.1:8189"
SEG_LEN = 124
FPS = 24.0
STEPS = 20
OVERLAP_S = 0.75
W, H = 576, 864
BASE_SEED = 2026092110

OUT = Path(r"E:\program\1project\video\shared\work\scratch\legacy-numbered\longform-2026-09-21")
XFER = Path(r"E:\program\1project\video\xfer\longform-2026-09-21")
H3_IN = Path(r"E:\program\1project\video\shared\runtime\comfy\installs\h3-runtime\input")
H3_OUT = Path(r"E:\program\1project\video\shared\runtime\comfy\installs\h3-runtime\output\longform-chengwu")
KEY_DIR = Path(r"E:\program\1project\video\xfer\overnight-2026-09-21")
STATUS = OUT / "STATUS.md"
MANIFEST = OUT / "MANIFEST.json"
FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"

BEATS = [
    {"id": "L01-phone", "kind": "keyframe", "key": "N1-phone-night.png", "prompt": "anime style, same young woman with short grey-blue bob and teal scoop-neck top, half-to-full body on sofa at night, looking at smartphone with slight concern, subtle breathing, tiny hand adjust on phone, soft lamp light, city lights in window, gentle static camera, no morphing, no extra people. Audio: quiet room tone, phone soft tap, no speech, no music."},
    {"id": "L02-stand", "kind": "chain", "prompt": "anime style, same young woman, she lowers the phone and slowly stands up from sofa, natural weight shift, teal outfit stable, face stable, home living room night, soft continuous motion, gentle camera tilt up slightly, no morphing, no extra people. Audio: quiet room tone, soft fabric rustle, no speech, no music."},
    {"id": "L03-door", "kind": "keyframe", "key": "N2-doorway.png", "prompt": "anime style, same young woman full body near doorway, looking back over shoulder, subtle turn of head then soft step toward living room, teal outfit stable, home entry soft indoor light, gentle camera, no morphing, no extra people. Audio: quiet room tone, soft footsteps, no speech, no music."},
    {"id": "L04-walk", "kind": "chain", "prompt": "anime style, same young woman walking slowly into living room, natural gait, hair soft bounce, teal outfit stable, face identity locked, night home interior, gentle tracking camera following her, no morphing, no extra people. Audio: quiet room tone, soft footsteps, no speech, no music."},
    {"id": "L05-sit", "kind": "keyframe", "key": "N3-sit-talk.png", "prompt": "anime style, same young woman sitting on sofa soft light, talking gesture, slight smile, hand motion natural, teal outfit stable, home living room, gentle camera, no morphing, no extra people. Audio: quiet room tone, soft clothing rustle, no speech, no music."},
    {"id": "L06-settle", "kind": "chain", "prompt": "anime style, same young woman settles back on sofa, smile softens, looks toward window, subtle breathing and blink, teal outfit stable, warm home light, very gentle camera push-in, no morphing, no extra people. Audio: quiet room tone, distant city hush, no speech, no music."},
    {"id": "L07-window", "kind": "keyframe", "key": "N4-window.png", "prompt": "anime style, same young woman full body standing by window at night looking outside, city lights, soft hair move, teal outfit stable, calm contemplative mood, gentle static camera, no morphing, no extra people. Audio: quiet room tone, soft city ambience, no speech, no music."},
    {"id": "L08-linger", "kind": "chain", "prompt": "anime style, same young woman lingering by window, subtle breathing, slight head tilt, city light flicker soft, teal outfit and face stable, peaceful ending hold, very gentle camera, no morphing, no extra people. Audio: quiet room tone fading soft, no speech, no music."},
]

def log(msg: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    XFER.mkdir(parents=True, exist_ok=True)
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(STATUS, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def http_json(method: str, path: str, obj=None, timeout=300):
    data = None if obj is None else json.dumps(obj).encode()
    req = urlreq.Request(f"http://{HOST}{path}", data=data, headers={"Content-Type": "application/json"} if obj is not None else {}, method=method)
    with urlreq.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def wait_up(n=60) -> bool:
    for _ in range(n):
        try:
            http_json("GET", "/system_stats", timeout=3)
            return True
        except Exception:
            time.sleep(2)
    return False

def free_hard():
    try:
        http_json("POST", "/free", {"unload_models": True, "free_memory": True}, timeout=60)
    except Exception as e:
        log(f"free warn: {e}")
    time.sleep(6)

def wait_idle(label: str, timeout=7200):
    t0 = time.time()
    while True:
        q = http_json("GET", "/queue", timeout=30)
        if not q.get("queue_running") and not q.get("queue_pending"):
            return
        if time.time() - t0 > timeout:
            raise TimeoutError(label)
        time.sleep(5)

def wait_prompt(pid: str, timeout=3600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            hist = http_json("GET", f"/history/{pid}", timeout=60)
            if pid in hist:
                return hist[pid]
        except Exception:
            pass
        time.sleep(4)
    raise TimeoutError(pid)

def h3_graph(img_name: str, prompt: str, seed: int, tag: str):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "minimax_h3_fl2va_pruned_int8_convrot.safetensors", "weight_dtype": "default"}},
        "1b": {"class_type": "EasyCache", "inputs": {"model": ["1", 0], "reuse_threshold": 0.3, "start_percent": 0.2, "end_percent": 0.9, "verbose": False}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "type": "minimax", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_fp16.safetensors"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"}},
        "5": {"class_type": "LoadImage", "inputs": {"image": img_name}},
        "6": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {"clip": ["2", 0], "vae": ["3", 0], "prompt": prompt, "width": W, "height": H, "length": SEG_LEN, "first_frame": ["5", 0]}},
        "7": {"class_type": "BasicGuider", "inputs": {"model": ["1b", 0], "conditioning": ["6", 0]}},
        "8": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
        "9": {"class_type": "BasicScheduler", "inputs": {"model": ["1b", 0], "scheduler": "simple", "steps": STEPS, "denoise": 1.0}},
        "10": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "11": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["10", 0], "guider": ["7", 0], "sampler": ["8", 0], "sigmas": ["9", 0], "latent_image": ["6", 1]}},
        "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["3", 0]}},
        "13": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["11", 0], "vae": ["4", 0]}},
        "14": {"class_type": "CreateVideo", "inputs": {"images": ["12", 0], "fps": FPS, "audio": ["13", 0]}},
        "15": {"class_type": "SaveVideo", "inputs": {"video": ["14", 0], "filename_prefix": f"longform-chengwu/{tag}", "format": "auto", "codec": "auto"}},
    }

def find_video(tag: str):
    if H3_OUT.exists():
        cands = sorted(H3_OUT.glob(f"{tag}*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if cands:
            return cands[0]
    root = Path(r"E:\program\1project\video\shared\runtime\comfy\installs\h3-runtime\output")
    for c in sorted(root.rglob(f"*{tag}*"), key=lambda p: p.stat().st_mtime, reverse=True):
        if c.suffix.lower() in {".mp4", ".webm", ".mkv"}:
            return c
    return None

def extract_last_frame(mp4: Path, tag: str) -> str:
    name = f"chain-last-{tag}.jpg"
    out = H3_IN / name
    H3_IN.mkdir(parents=True, exist_ok=True)
    subprocess.run([FFMPEG, "-y", "-sseof", "-0.12", "-i", str(mp4), "-frames:v", "1", "-q:v", "2", str(out)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not out.exists():
        raise FileNotFoundError(out)
    return name

def duration(path: Path) -> float:
    out = subprocess.check_output([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], text=True).strip()
    return float(out)

def xfade_concat(paths, out_path: Path, overlap: float) -> Path:
    if len(paths) == 1:
        shutil.copy2(paths[0], out_path)
        return out_path
    durs = [duration(p) for p in paths]
    inputs = []
    for p in paths:
        inputs.extend(["-i", str(p)])
    vfilters = []
    cur = "[0:v]"
    offset = 0.0
    for i in range(1, len(paths)):
        offset += durs[i - 1] - overlap
        out_label = f"[v{i}]" if i < len(paths) - 1 else "[vout]"
        vfilters.append(f"{cur}[{i}:v]xfade=transition=fade:duration={overlap}:offset={max(offset, 0):.3f}{out_label}")
        cur = out_label
    afilters = []
    cur_a = "[0:a]"
    for i in range(1, len(paths)):
        out_label = f"[a{i}]" if i < len(paths) - 1 else "[aout]"
        afilters.append(f"{cur_a}[{i}:a]acrossfade=d={overlap}:c1=tri:c2=tri{out_label}")
        cur_a = out_label
    fc = ";".join(vfilters + afilters)
    cmd = [FFMPEG, "-y", *inputs, "-filter_complex", fc, "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", str(out_path)]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        log("acrossfade failed; retry video-only xfade")
        fc = ";".join(vfilters)
        cmd = [FFMPEG, "-y", *inputs, "-filter_complex", fc, "-map", "[vout]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(out_path)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return out_path

def stage(p: Path):
    shutil.copy2(p, OUT / p.name)
    shutil.copy2(p, XFER / p.name)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    XFER.mkdir(parents=True, exist_ok=True)
    H3_IN.mkdir(parents=True, exist_ok=True)
    H3_OUT.mkdir(parents=True, exist_ok=True)
    STATUS.write_text("", encoding="utf-8")
    log(f"START longform n={len(BEATS)} {W}x{H} overlap={OVERLAP_S}s")
    if not wait_up():
        log("FAIL 8189 not up")
        return 2
    manifest = {"started": datetime.now().isoformat(), "beats": [], "settings": {"w": W, "h": H, "seg_len": SEG_LEN, "steps": STEPS, "overlap_s": OVERLAP_S, "easycache": True}}
    videos = []
    last_frame_name = None
    for i, beat in enumerate(BEATS):
        tag = beat["id"]
        existing = OUT / f"{tag}.mp4"
        if existing.exists() and existing.stat().st_size > 10000:
            log(f"skip existing {tag}")
            videos.append(existing)
            last_frame_name = extract_last_frame(existing, tag)
            manifest["beats"].append({"id": tag, "skipped": True, "path": str(existing)})
            continue
        if beat["kind"] == "keyframe":
            src = KEY_DIR / beat["key"]
            if not src.exists():
                log(f"FAIL missing key {src}")
                return 3
            img_name = f"anchor-{tag}.png"
            shutil.copy2(src, H3_IN / img_name)
        else:
            if not last_frame_name:
                log(f"FAIL no chain frame for {tag}")
                return 4
            img_name = last_frame_name
        wait_idle(f"before-{tag}")
        free_hard()
        wait_idle(f"after-free-{tag}")
        seed = BASE_SEED + i
        log(f"queue {tag} kind={beat['kind']} img={img_name} seed={seed}")
        try:
            resp = http_json("POST", "/prompt", {"prompt": h3_graph(img_name, beat["prompt"], seed, tag), "client_id": str(uuid.uuid4())}, timeout=180)
            if resp.get("node_errors"):
                log(f"node_errors {resp['node_errors']}")
                return 5
            hist = wait_prompt(resp["prompt_id"])
            free_hard()
            v = find_video(tag)
            if not v:
                log(f"FAIL no video for {tag}")
                return 6
            dest = OUT / f"{tag}.mp4"
            shutil.copy2(v, dest)
            stage(dest)
            videos.append(dest)
            last_frame_name = extract_last_frame(dest, tag)
            d = duration(dest)
            log(f"OK {tag} {d:.2f}s -> {dest.name}")
            manifest["beats"].append({"id": tag, "kind": beat["kind"], "path": str(dest), "duration": d, "seed": seed, "first_image": img_name})
            MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            log(f"FAIL {tag}: {e}\n{traceback.format_exc()}")
            MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
            return 7
    final = OUT / "chengwu-home-longform-xfade.mp4"
    log(f"xfade concat {len(videos)} clips overlap={OVERLAP_S}")
    xfade_concat(videos, final, OVERLAP_S)
    stage(final)
    d = duration(final)
    manifest["final"] = {"path": str(final), "duration": d, "parts": [str(v) for v in videos]}
    manifest["finished"] = datetime.now().isoformat()
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (XFER / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"DONE final {d:.2f}s -> {final}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
