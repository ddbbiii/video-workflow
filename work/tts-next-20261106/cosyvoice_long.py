# -*- coding: utf-8 -*-
"""CosyVoice3 speed=0.90 on a longer real passage: check stability and tail artifacts."""
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

import json as _json
utt = _json.loads((ROOT / "4/audio/utterances.json").read_text(encoding="utf-8"))
ch01 = [u for u in utt["utterances"] if u["section"] == "ch01"][:6]
TEXT = "".join(u["text"] for u in ch01)
print("chars", len(TEXT), flush=True)

sys.path.insert(0, str(CV))
sys.path.insert(0, str(CV / "third_party" / "Matcha-TTS"))
os.environ["MODELSCOPE_CACHE"] = str(WORK / "modelscope-cache")
os.environ["HF_HOME"] = str(WORK / "hf-cache")

import numpy as np
import soundfile as sf
import torch
from cosyvoice.cli.cosyvoice import AutoModel

model = AutoModel(model_dir=str(MODEL))
sr = model.sample_rate
PROMPT_TEXT = "You are a helpful assistant.<|endofprompt|>" + REF_TEXT

torch.cuda.reset_peak_memory_stats()
torch.cuda.synchronize(); t0 = time.time()
chunks = []
for j in model.inference_zero_shot(TEXT, PROMPT_TEXT, str(REF), stream=False, speed=0.90):
    chunks.append(j["tts_speech"].squeeze(0).cpu().numpy())
torch.cuda.synchronize(); dt = time.time() - t0
wav = np.concatenate(chunks) if chunks else np.zeros(1, dtype=np.float32)
p = OUT / "cv_090_long.wav"
sf.write(str(p), wav, sr)
meta = dict(text_chars=len(TEXT), sr=sr, audio_s=round(len(wav) / sr, 2), gen_s=round(dt, 1),
            rtf=round(dt / (len(wav) / sr), 2), vram_peak_gb=round(torch.cuda.max_memory_allocated() / 1e9, 2),
            chars_per_s=round(len(TEXT) / (len(wav) / sr), 2))
(OUT / "cv_090_long.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
print("RESULT", json.dumps(meta, ensure_ascii=False), flush=True)
