# -*- coding: utf-8 -*-
"""CosyVoice3 at speed=0.90, per sentence, tight trim + fades + computed gaps
to hit a target overall pace (default 3.8 chars/s). Removes sentence-tail breaths.
"""
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

uji = json.loads((ROOT / "4/audio/utterances.json").read_text(encoding="utf-8"))
TEXT = "".join([u["text"] for u in uji["utterances"] if u["section"] == "ch01"][:6])
SENTS = [s.strip() for s in TEXT.split("。") if s.strip()]

SPEED = float(os.environ.get("CV_SPEED", "0.90"))
TARGET_CPS = float(os.environ.get("CV_CPS", "3.8"))
TRIM_DB = -42.0
HEAD_KEEP, TAIL_KEEP = 0.05, 0.08
FADE = 0.02

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


def trim(y):
    n = int(0.02 * sr)
    m = len(y) // n
    if m == 0:
        return y
    r = np.sqrt(np.mean(y[: m * n].reshape(m, n) ** 2, axis=1))
    act = np.where(r > 10 ** (TRIM_DB / 20))[0]
    if not len(act):
        return y
    a = max(0, int(act[0] * n - HEAD_KEEP * sr))
    b = min(len(y), int((act[-1] + 1) * n + TAIL_KEEP * sr))
    out = y[a:b].copy()
    f = int(FADE * sr)
    if len(out) > 2 * f:
        out[:f] *= np.linspace(0, 1, f)
        out[-f:] *= np.linspace(1, 0, f)
    return out


t0 = time.time()
parts, rows = [], []
for i, s in enumerate(SENTS):
    text = s + "。"
    torch.cuda.synchronize(); st = time.time()
    chunks = [j["tts_speech"].squeeze(0).cpu().numpy()
              for j in model.inference_zero_shot(text, PROMPT_TEXT, str(REF), stream=False, speed=SPEED)]
    wav = np.concatenate(chunks) if chunks else np.zeros(1, dtype=np.float32)
    y = trim(wav)
    parts.append(y)
    rows.append(dict(i=i, text=text, raw_s=round(len(wav) / sr, 2), trimmed_s=round(len(y) / sr, 2),
                     gen_s=round(time.time() - st, 1)))
    print("SENT", json.dumps(rows[-1], ensure_ascii=False), flush=True)

speech_s = sum(len(p) / sr for p in parts)
chars = len(TEXT)
total_target = chars / TARGET_CPS
gap_total = max(0.0, total_target - speech_s)
gaps = len(parts) - 1
gap_s = gap_total / gaps if gaps else 0.0
gap_pcm = np.zeros(int(gap_s * sr), dtype=np.float32)

audio = []
for i, p in enumerate(parts):
    audio.append(p)
    if i < len(parts) - 1:
        audio.append(gap_pcm)
out = np.concatenate(audio)
name = f"cv_380_s{int(SPEED*100)}"
p = OUT / f"{name}.wav"
sf.write(str(p), out, sr)

meta = dict(name=name, speed=SPEED, target_cps=TARGET_CPS, chars=chars, sentences=len(parts),
            speech_s=round(speech_s, 2), gap_s=round(gap_s, 2), audio_s=round(len(out) / sr, 2),
            actual_cps=round(chars / (len(out) / sr), 2), trim_db=TRIM_DB,
            gen_total_s=round(time.time() - t0, 1), sr=sr)
(OUT / f"{name}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
(OUT / f"{name}_sentences.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("RESULT", json.dumps(meta, ensure_ascii=False), flush=True)
