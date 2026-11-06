# -*- coding: utf-8 -*-
"""Qwen3-TTS 1.7B Base: ~15 s Chinese clone test with the existing b2 reference."""
import json, os, time
from pathlib import Path

ROOT = Path(r"E:\program\1project\video")
WORK = ROOT / "work" / "tts-next-20261106"
MODEL = WORK / "models" / "Qwen3-TTS-1.7B-Base"
REF = ROOT / "shared/runtime/engines/tts/refs/b2-warm-male_ref.wav"
REF_TEXT = (ROOT / "shared/runtime/engines/tts/voice-assets/b2-warm-male/ref_text.txt").read_text(encoding="utf-8").strip()
OUT = WORK / "out"
OUT.mkdir(parents=True, exist_ok=True)

TEXT = ("很远的地方，有一座高山。山脚下或许还有树林，或许还有尚未结冰的溪水。"
        "但在山顶，空气已经足够寒冷。云层贴着山脊缓缓移动，细小的冰晶在云里生长。")

os.environ["HF_HOME"] = str(WORK / "hf-cache")
os.environ["MODELSCOPE_CACHE"] = str(WORK / "modelscope-cache")
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import torch, soundfile as sf
from qwen_tts import Qwen3TTSModel

torch.manual_seed(7)
t0 = time.time()
model = Qwen3TTSModel.from_pretrained(
    str(MODEL), device_map="cuda:0", dtype=torch.bfloat16, attn_implementation="sdpa"
)
print("load_s", round(time.time() - t0, 1), flush=True)

prompt = model.create_voice_clone_prompt(ref_audio=str(REF), ref_text=REF_TEXT)

torch.cuda.reset_peak_memory_stats()
torch.cuda.synchronize(); t = time.time()
wavs, sr = model.generate_voice_clone(
    text=TEXT, language="Chinese", voice_clone_prompt=prompt, non_streaming_mode=True
)
torch.cuda.synchronize(); dt = time.time() - t
wav = wavs[0]
out = OUT / "qwen3_15s.wav"
sf.write(str(out), wav, sr)
meta = dict(model=str(MODEL), ref=str(REF), text=TEXT, chars=len(TEXT), sr=sr,
            audio_s=round(len(wav) / sr, 2), gen_s=round(dt, 1),
            rtf=round(dt / (len(wav) / sr), 2),
            vram_peak_gb=round(torch.cuda.max_memory_allocated() / 1e9, 2))
(OUT / "qwen3_15s.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
print("RESULT", json.dumps(meta, ensure_ascii=False), flush=True)
