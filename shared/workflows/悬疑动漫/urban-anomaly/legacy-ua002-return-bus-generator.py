"""Create UA002 return-bus intro review candidates only.

No UA002 episode picture or narration asset is modified.  Each candidate is a
self-contained title-card audition with the same local narrator profile and
two-line title treatment.
"""

from __future__ import annotations

import hashlib
import json
import random
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import numpy as np
import requests
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel


ROOT = Path(r"E:\program\1project\video")
OUT = ROOT / "production/series/urban-anomaly-archives/brand/intro/candidates/UA002-return-bus-intro-v1"
COMFY = "http://127.0.0.1:8188"
# Comfy Desktop is configured to use this shared output root; do not assume
# the older portable-install output folder.
COMFY_OUT = Path(r"E:\program\1project\video\shared\runtime\comfy\models\output")
MODEL = Path(r"E:\AI\Qwen3-TTS\models\Qwen3-TTS-12Hz-1.7B-CustomVoice")
FONT_BRUSH = r"C\:/Windows/Fonts/simkai.ttf"
FONT_SANS = r"C\:/Windows/Fonts/msyh.ttc"
SEED = 72917002
VOICE = (
    "成年女性都市悬疑旁白。保持已批准 Serena 的自然、克制、偏低沉音色；"
    "语速略紧，带一点即时紧张感，但不喊叫、不耳语、不播音腔、不卖萌。"
    "吐字清楚，最后一个关键词落点明确。"
)
STYLE = (
    "mature dark urban suspense illustration, cinematic anime realism, rainy night, "
    "cold cyan and deep charcoal palette, thin clean ink lines, restrained contrast, "
    "wet pavement reflections, no chibi, no text, no watermark"
)
CANDIDATES = [
    ("A-no-route", "暴雨后的零点十七分，\n她上了一辆没有线路号的返程车。", "暴雨后的零点十七分|她上了一辆没有线路号的返程车"),
    ("B-no-terminal", "这辆车没有终点，\n车上每个人都说自己在回家。", "这辆车没有终点|车上每个人都说自己在回家"),
    ("C-knows-home", "公交系统里没有这条线路，\n它却知道每个人要回哪里。", "公交系统里没有这条线路|它却知道每个人要回哪里"),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def duration(path: Path) -> float:
    info = sf.info(str(path))
    return round(info.frames / info.samplerate, 3)


def run(*args: str) -> None:
    subprocess.run(list(args), check=True)


def comfy_prompt(seed: int) -> dict:
    prompt = (
        "wide empty city bus stop in heavy rain at night, an old dark green city bus with no route number "
        "arriving at the curb, its interior lights glowing cold white, bus windows fogged, a lone adult woman "
        "under an umbrella seen from behind, large central negative space for typography. " + STYLE
    )
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "z_image_turbo_bf16.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "lumina2", "device": "default"}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": prompt}},
        "4": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["3", 0]}},
        "5": {"class_type": "EmptySD3LatentImage", "inputs": {"width": 1024, "height": 576, "batch_size": 1}},
        "6": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3}},
        "7": {"class_type": "KSampler", "inputs": {"model": ["6", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0], "seed": seed, "steps": 8, "cfg": 1, "sampler_name": "res_multistep", "scheduler": "simple", "denoise": 1}},
        "8": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["8", 0]}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": "UA002/intro/return-bus"}},
    }


def generate_background(destination: Path) -> dict[str, object]:
    client_id = str(uuid.uuid4())
    started = time.perf_counter()
    response = requests.post(f"{COMFY}/prompt", json={"prompt": comfy_prompt(SEED), "client_id": client_id}, timeout=30)
    response.raise_for_status()
    prompt_id = response.json()["prompt_id"]
    for _ in range(720):
        item = requests.get(f"{COMFY}/history/{prompt_id}", timeout=20).json().get(prompt_id)
        if item:
            if item.get("status", {}).get("status_str") == "error":
                raise RuntimeError(item)
            images = item.get("outputs", {}).get("10", {}).get("images", [])
            if images:
                image = images[0]
                src = COMFY_OUT / image.get("subfolder", "") / image["filename"]
                shutil.copy2(src, destination)
                return {"prompt_id": prompt_id, "elapsed_seconds": round(time.perf_counter() - started, 3)}
        time.sleep(1)
    raise TimeoutError("ComfyUI intro background timed out")


def esc(text: str) -> str:
    return text.replace("'", r"\'").replace(":", r"\:")


def render_card(background: Path, wav: Path, output: Path, top: str, bottom: str) -> None:
    visual = (
        "[0:v]scale=1344:756,crop=1280:720:x='32+4*sin(1.4*t)':y=18,"
        "eq=contrast=1.07:brightness=-0.025:saturation=0.78,"
        "drawbox=x=110:y=208:w=1060:h=276:color=0x010305@0.36:t=fill,"
        f"drawtext=fontfile='{FONT_SANS}':text='都市异常档案 · UA-002':x=(w-text_w)/2:y=164:fontsize=24:fontcolor=0xB8CBD0@0.94,"
        f"drawtext=fontfile='{FONT_BRUSH}':text='{esc(top)}':x=(w-text_w)/2:y=244:fontsize=65:fontcolor=0xE7ECEB:borderw=4:bordercolor=0x070B0E@0.96:shadowx=3:shadowy=4:shadowcolor=black@0.9,"
        f"drawtext=fontfile='{FONT_BRUSH}':text='{esc(bottom)}':x=(w-text_w)/2:y=336:fontsize=68:fontcolor=0xC9363F:borderw=5:bordercolor=0x210407@0.96:shadowx=4:shadowy=5:shadowcolor=black@0.92,"
        "drawbox=x=(w-400)/2:y=440:w=400:h=3:color=0xC9363F@0.88:t=fill,format=yuv420p[v]"
    )
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-framerate", "24", "-i", str(background), "-i", str(wav),
        "-filter_complex", f"{visual};[1:a]volume=1.0,aresample=48000[a]", "-map", "[v]", "-map", "[a]", "-shortest", "-r", "24",
        "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output))


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable")
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    background = OUT / "UA002-return-bus-rain-background-v1.png"
    background_result = {"reused": True} if background.exists() else generate_background(background)
    random.seed(SEED); np.random.seed(SEED % (2**32)); torch.manual_seed(SEED); torch.cuda.manual_seed_all(SEED)
    model = Qwen3TTSModel.from_pretrained(str(MODEL), device_map="cuda:0", dtype=torch.bfloat16, attn_implementation="sdpa")
    results = []
    for index, (ident, narration, display) in enumerate(CANDIDATES, 1):
        top, bottom = display.split("|")
        raw = OUT / f"UA002-return-bus-intro-{ident}-raw.wav"
        wav = OUT / f"UA002-return-bus-intro-{ident}-48k.wav"
        video = OUT / f"UA002-return-bus-intro-{ident}.mp4"
        take_started = time.perf_counter()
        audio, sample_rate = model.generate_custom_voice(text=narration, language="Chinese", speaker="Serena", instruct=VOICE, do_sample=False)
        sf.write(str(raw), audio[0], sample_rate, subtype="PCM_16")
        run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw), "-af", "highpass=f=55,loudnorm=I=-18:TP=-3:LRA=7,aresample=48000", "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(wav))
        render_card(background, wav, video, top, bottom)
        results.append({"id": ident, "narration": narration, "display": [top, bottom], "wav": str(wav), "video": str(video), "duration_seconds": duration(wav), "elapsed_seconds": round(time.perf_counter() - take_started, 3), "sha256": {"wav": sha256(wav), "video": sha256(video)}})
    del model; torch.cuda.empty_cache()
    manifest = {"status": "review_required", "episode": "UA002", "title": "零点十七分的返程车", "voice_profile": {"model": str(MODEL), "speaker": "Serena", "instruction": VOICE, "decode": "deterministic do_sample=false", "seed": SEED}, "background": {"path": str(background), **background_result, "sha256": sha256(background)}, "candidates": results, "total_elapsed_seconds": round(time.perf_counter() - started, 3)}
    (OUT / "UA002-return-bus-intro-candidates-v1-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
