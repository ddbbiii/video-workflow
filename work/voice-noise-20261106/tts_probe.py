# -*- coding: utf-8 -*-
"""Probe VoxCPM2 quality knobs on the sleep-line voice (same reference/prompt as production).

Goal: find settings that reduce mechanical breath / metallic artifacts without changing timbre.
Runs on the shared GPU; writes wavs + meta.json to work/voice-noise-20261106/tts-probe/.
"""
import os, sys, time, json
from pathlib import Path

ROOT = Path(r"E:\program\1project\video")
OUT = ROOT / "work" / "voice-noise-20261106" / "tts-probe"
OUT.mkdir(parents=True, exist_ok=True)
MD = str(ROOT / "shared/runtime/engines/tts/voxcpm/pretrained_models/VoxCPM2")
REF = str(ROOT / "shared/runtime/engines/tts/refs/b2-warm-male_ref.wav")
PROMPT = str(ROOT / "shared/runtime/engines/tts/voice-assets/b2-warm-male/refs/light-expression-20261013/prompt.wav")
PROMPT_TEXT = "你脚下的地球，藏着一个看不见的磁场。"
TEXT = "其中一片雪花，旋转着，穿过安静的空气，最后落在山坡上。"

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["MODELSCOPE_CACHE"] = str(ROOT / "shared/runtime/engines/tts/modelscope-cache")
os.environ["HF_HOME"] = str(ROOT / "shared/runtime/engines/tts/hf-cache")
TMP = ROOT / "work/voice-noise-20261106/tmp"
TMP.mkdir(parents=True, exist_ok=True)
os.environ["TMP"] = os.environ["TEMP"] = os.environ["TMPDIR"] = str(TMP)
os.environ["NUMBA_CACHE_DIR"] = str(TMP / "numba")
(TMP / "numba").mkdir(exist_ok=True)

import torch, soundfile as sf
from voxcpm import VoxCPM

VARIANTS = [
    ("s10", dict(inference_timesteps=10)),
    ("s20", dict(inference_timesteps=20)),
    ("s30", dict(inference_timesteps=30)),
    ("s20cfg24", dict(inference_timesteps=20, cfg_value=2.4)),
]

only = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else None
denoise = "--denoise" in sys.argv

t0 = time.time()
model = VoxCPM.from_pretrained(MD, load_denoiser=denoise, optimize=False)
print("load_s", round(time.time() - t0, 1), "denoiser", denoise, flush=True)
sr = model.tts_model.sample_rate

meta_p = OUT / "meta.json"
meta = json.loads(meta_p.read_text(encoding="utf-8")) if meta_p.exists() else {}
meta.update(dict(ref=REF, prompt=PROMPT, prompt_text=PROMPT_TEXT, text=TEXT,
                 cfg_value=2.0, seed=7, denoise=denoise, sr=sr,
                 torch=torch.__version__, load_s=round(time.time() - t0, 1)))
meta.setdefault("results", {})

for name, kw in VARIANTS:
    if only and name not in only:
        continue
    torch.manual_seed(7)
    torch.cuda.synchronize(); t = time.time()
    wav = model.generate(text=TEXT, cfg_value=kw.get("cfg_value", 2.0),
                         inference_timesteps=kw["inference_timesteps"],
                         reference_wav_path=REF, prompt_wav_path=PROMPT,
                         prompt_text=PROMPT_TEXT, denoise=denoise)
    torch.cuda.synchronize(); dt = time.time() - t
    suffix = "d" if denoise else ""
    p = OUT / f"{name}{suffix}.wav"
    sf.write(str(p), wav, sr)
    r = dict(variant=name, **kw, seed=7, gen_s=round(dt, 1), audio_s=round(len(wav) / sr, 2))
    meta["results"][p.stem] = r
    meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print("RESULT", p.stem, json.dumps(r), flush=True)

print("DONE", flush=True)
