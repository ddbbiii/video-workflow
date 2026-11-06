# -*- coding: utf-8 -*-
"""CosyVoice3: find the slowest speed that keeps clip 02's clean timbre,
plus a pause-based pacing variant (same speed, longer gaps)."""
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
SENTENCES = ["很远的地方，有一座高山。",
             "山脚下或许还有树林，或许还有尚未结冰的溪水。",
             "但在山顶，空气已经足够寒冷。",
             "云层贴着山脊缓缓移动，细小的冰晶在云里生长。"]

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


def gen(text, speed):
    chunks = []
    for j in model.inference_zero_shot(text, PROMPT_TEXT, str(REF), stream=False, speed=speed):
        chunks.append(j["tts_speech"].squeeze(0).cpu().numpy())
    return np.concatenate(chunks) if chunks else np.zeros(1, dtype=np.float32)


def save(name, wav, extra):
    p = OUT / f"{name}.wav"
    sf.write(str(p), wav, sr)
    meta = dict(name=name, sr=sr, audio_s=round(len(wav) / sr, 2), chars=len(TEXT), **extra)
    (OUT / f"{name}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print("RESULT", json.dumps(meta, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    tasks = sys.argv[1].split(",") if len(sys.argv) > 1 else ["s095", "s090", "s085", "pause"]
    for t in tasks:
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize(); st = time.time()
        if t.startswith("s"):
            speed = int(t[1:]) / 100.0
            wav = gen(TEXT, speed)
            dt = time.time() - st
            save(f"cv_{t}", wav, dict(mode="speed", speed=speed, gen_s=round(dt, 1),
                                      rtf=round(dt / (len(wav) / sr), 2),
                                      vram_peak_gb=round(torch.cuda.max_memory_allocated() / 1e9, 2)))
        elif t == "pause":
            parts = []
            for i, s in enumerate(SENTENCES):
                parts.append(gen(s, 1.0))
                if i < len(SENTENCES) - 1:
                    parts.append(np.zeros(int(0.55 * sr), dtype=np.float32))
            wav = np.concatenate(parts)
            dt = time.time() - st
            save("cv_pause", wav, dict(mode="pause", speed=1.0, gap_s=0.55, gen_s=round(dt, 1),
                                       rtf=round(dt / (len(wav) / sr), 2),
                                       vram_peak_gb=round(torch.cuda.max_memory_allocated() / 1e9, 2)))
