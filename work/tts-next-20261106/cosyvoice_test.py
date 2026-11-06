# -*- coding: utf-8 -*-
"""CosyVoice3 0.5B: ~15 s Chinese clone test + optional [breath] variant."""
import json, os, sys, time
from pathlib import Path

ROOT = Path(r"E:\program\1project\video")
WORK = ROOT / "work" / "tts-next-20261106"
MODEL = WORK / "models" / "Fun-CosyVoice3-0.5B"
CV = WORK / "third_party" / "cosyvoice"
REF = ROOT / "shared/runtime/engines/tts/refs/b2-warm-male_ref.wav"
REF_TEXT = (ROOT / "shared/runtime/engines/tts/voice-assets/b2-warm-male/ref_text.txt").read_text(encoding="utf-8").strip()
OUT = WORK / "out"
OUT.mkdir(parents=True, exist_ok=True)

TEXT = ("很远的地方，有一座高山。山脚下或许还有树林，或许还有尚未结冰的溪水。"
        "但在山顶，空气已经足够寒冷。云层贴着山脊缓缓移动，细小的冰晶在云里生长。")
TEXT_BREATH = ("很远的地方，有一座高山。[breath]山脚下或许还有树林，或许还有尚未结冰的溪水。[breath]"
               "但在山顶，空气已经足够寒冷。[breath]云层贴着山脊缓缓移动，细小的冰晶在云里生长。")

sys.path.insert(0, str(CV))
sys.path.insert(0, str(CV / "third_party" / "Matcha-TTS"))
os.environ["MODELSCOPE_CACHE"] = str(WORK / "modelscope-cache")
os.environ["HF_HOME"] = str(WORK / "hf-cache")

import numpy as np
import soundfile as sf
import torch
from cosyvoice.cli.cosyvoice import AutoModel

t0 = time.time()
model = AutoModel(model_dir=str(MODEL))
sr = model.sample_rate
print("load_s", round(time.time() - t0, 1), "sr", sr, flush=True)

PROMPT_TEXT = "You are a helpful assistant.<|endofprompt|>" + REF_TEXT


def run(text, speed, name, cross=False):
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize(); t = time.time()
    chunks = []
    gen = (model.inference_cross_lingual("You are a helpful assistant.<|endofprompt|>" + text,
                                         str(REF), stream=False, speed=speed)
           if cross else
           model.inference_zero_shot(text, PROMPT_TEXT, str(REF), stream=False, speed=speed))
    for j in gen:
        chunks.append(j["tts_speech"].squeeze(0).cpu().numpy())
    torch.cuda.synchronize(); dt = time.time() - t
    wav = np.concatenate(chunks) if chunks else np.zeros(1, dtype=np.float32)
    p = OUT / f"{name}.wav"
    sf.write(str(p), wav, sr)
    meta = dict(model=str(MODEL), name=name, chars=len(text), speed=speed, cross=cross,
                sr=sr, audio_s=round(len(wav) / sr, 2), gen_s=round(dt, 1),
                rtf=round(dt / max(len(wav) / sr, 1e-6), 2),
                vram_peak_gb=round(torch.cuda.max_memory_allocated() / 1e9, 2))
    (OUT / f"{name}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print("RESULT", json.dumps(meta, ensure_ascii=False), flush=True)
    return meta


if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else None
    if not only or only == "normal":
        run(TEXT, 1.0, "cosyvoice3_15s")
    if not only or only == "breath":
        run(TEXT_BREATH, 1.0, "cosyvoice3_15s_breath", cross=True)
    if not only or only == "slow":
        run(TEXT, 0.78, "cosyvoice3_slow", cross=False)
