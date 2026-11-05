# -*- coding: utf-8 -*-
"""量字幕与配音的全局偏移：每条 cue 起点 vs 最近的语音起始点。"""
import json, wave
from pathlib import Path
import numpy as np

EP = Path(r"E:\program\1project\video\4")
CUES = json.loads((EP / "runs/20261103-gla-b01/subtitles/r2/cues.json").read_text(encoding="utf-8"))["cues"]
WAV = EP / "video/final/glacier-river_narration.wav"

with wave.open(str(WAV), "rb") as w:
    sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
    y = np.frombuffer(w.readframes(n), dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        y = y.reshape(-1, ch).mean(axis=1)

hop = int(sr * 0.02)
m = len(y) // hop
rms = np.sqrt(np.mean(y[: m * hop].reshape(m, hop) ** 2, axis=1))
db = 20 * np.log10(np.maximum(rms, 1e-9))
thr = -40.0
on = (db > thr)
# 语音段起点：连续 >=3 帧静音后转有声
onsets = []
sil = 0
for i, v in enumerate(on):
    if v:
        if sil >= 3 or i == 0:
            onsets.append(i * 0.02)
        sil = 0
    else:
        sil += 1
onsets = np.array(onsets)
print("onsets", len(onsets), "first", onsets[:5])

starts = np.array([c["start_s"] for c in CUES])
deltas = []
for s in starts:
    j = np.argmin(np.abs(onsets - s))
    if abs(onsets[j] - s) < 3.0:
        deltas.append(s - onsets[j])
deltas = np.array(deltas)
print("matched", len(deltas))
for q in (5, 25, 50, 75, 95):
    print(f"p{q}", round(float(np.percentile(deltas, q)), 3))
print("mean", round(float(deltas.mean()), 3))
print("median", round(float(np.median(deltas)), 3))
# 只看前 20 条
print("first10", [round(float(x), 2) for x in deltas[:10]])
