# -*- coding: utf-8 -*-
"""Test whether slowing the PROMPT makes the model speak slower (so less atempo is needed)."""
import os, subprocess, sys, time, json
from pathlib import Path

ROOT = Path(r"E:\program\1project\video")
WORK = ROOT / "work/voice-noise-20261106"
OUT = WORK / "tts-probe5"
OUT.mkdir(parents=True, exist_ok=True)
MD = str(ROOT / "shared/runtime/engines/tts/voxcpm/pretrained_models/VoxCPM2")
REF = str(ROOT / "shared/runtime/engines/tts/refs/b2-warm-male_ref.wav")
PROMPT = str(ROOT / "shared/runtime/engines/tts/voice-assets/b2-warm-male/refs/light-expression-20261013/prompt.wav")
PROMPT_TEXT = "你脚下的地球，藏着一个看不见的磁场。"
TEXT = ("很远的地方，有一座高山。山脚下或许还有树林，或许还有尚未结冰的溪水。"
        "但在山顶，空气已经足够寒冷。云层贴着山脊缓缓移动，细小的冰晶在云里生长，然后开始落下。")

SLOW = OUT / "prompt_slow82.wav"
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", PROMPT,
                "-filter:a", "rubberband=tempo=0.82:pitch=1:formant=preserved",
                "-acodec", "pcm_s16le", str(SLOW)], check=True)

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["MODELSCOPE_CACHE"] = str(ROOT / "shared/runtime/engines/tts/modelscope-cache")
os.environ["HF_HOME"] = str(ROOT / "shared/runtime/engines/tts/hf-cache")
TMP = WORK / "tmp"
TMP.mkdir(parents=True, exist_ok=True)
os.environ["TMP"] = os.environ["TEMP"] = os.environ["TMPDIR"] = str(TMP)
os.environ["NUMBA_CACHE_DIR"] = str(TMP / "numba")
(TMP / "numba").mkdir(exist_ok=True)

import torch, soundfile as sf
from voxcpm import VoxCPM

model = VoxCPM.from_pretrained(MD, load_denoiser=False, optimize=False)
sr = model.tts_model.sample_rate
torch.manual_seed(7)
torch.cuda.synchronize(); t = time.time()
wav = model.generate(text=TEXT, cfg_value=2.0, inference_timesteps=10,
                     reference_wav_path=REF, prompt_wav_path=str(SLOW), prompt_text=PROMPT_TEXT)
torch.cuda.synchronize(); dt = time.time() - t
p = OUT / "slowprompt_s10.wav"
sf.write(str(p), wav, sr)
meta = dict(prompt=str(SLOW), gen_s=round(dt, 1), audio_s=round(len(wav) / sr, 2))
(OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
print("RESULT", meta, flush=True)
