# -*- coding: utf-8 -*-
"""Long-paragraph A/B: current recipe vs original-reference-prompt recipe."""
import os, sys, time, json
from pathlib import Path

ROOT = Path(r"E:\program\1project\video")
OUT = ROOT / "work" / "voice-noise-20261106" / "tts-probe3"
OUT.mkdir(parents=True, exist_ok=True)
MD = str(ROOT / "shared/runtime/engines/tts/voxcpm/pretrained_models/VoxCPM2")
REF = str(ROOT / "shared/runtime/engines/tts/refs/b2-warm-male_ref.wav")
REF_TEXT = (ROOT / "shared/runtime/engines/tts/voice-assets/b2-warm-male/ref_text.txt").read_text(encoding="utf-8").strip()
PROMPT = str(ROOT / "shared/runtime/engines/tts/voice-assets/b2-warm-male/refs/light-expression-20261013/prompt.wav")
PROMPT_TEXT = "你脚下的地球，藏着一个看不见的磁场。"
TEXT = ("很远的地方，有一座高山。山脚下或许还有树林，或许还有尚未结冰的溪水。"
        "但在山顶，空气已经足够寒冷。云层贴着山脊缓缓移动，细小的冰晶在云里生长，然后开始落下。")

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

VARIANTS = {
    "cur_s10": dict(reference=REF, prompt=PROMPT, prompt_text=PROMPT_TEXT, steps=10),
    "orig_s20": dict(reference=REF, prompt=REF, prompt_text=REF_TEXT, steps=20),
}
only = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else None

t0 = time.time()
model = VoxCPM.from_pretrained(MD, load_denoiser=False, optimize=False)
print("load_s", round(time.time() - t0, 1), flush=True)
sr = model.tts_model.sample_rate
meta = dict(text=TEXT, sr=sr, results={})

for name, v in VARIANTS.items():
    if only and name not in only:
        continue
    torch.manual_seed(7)
    torch.cuda.synchronize(); t = time.time()
    wav = model.generate(text=TEXT, cfg_value=2.0, inference_timesteps=v["steps"],
                         reference_wav_path=v["reference"], prompt_wav_path=v["prompt"],
                         prompt_text=v["prompt_text"])
    torch.cuda.synchronize(); dt = time.time() - t
    p = OUT / f"{name}.wav"
    sf.write(str(p), wav, sr)
    meta["results"][name] = dict(gen_s=round(dt, 1), audio_s=round(len(wav) / sr, 2))
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print("RESULT", name, meta["results"][name], flush=True)
print("DONE", flush=True)
