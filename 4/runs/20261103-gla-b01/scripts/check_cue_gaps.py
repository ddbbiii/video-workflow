# -*- coding: utf-8 -*-
"""cue 起点到下一段语音起始的间隔分布（只统计起点在静音里的 cue）。"""
import json, wave
from pathlib import Path
import numpy as np

EP = Path(r"E:\program\1project\video\4")
RUN = EP / "runs/20261103-gla-b01"
CUES = json.loads((RUN / "subtitles/r2/cues.json").read_text(encoding="utf-8"))["cues"]
WAV = EP / "video/final/glacier-river_narration.wav"
with wave.open(str(WAV), "rb") as w:
    sr = w.getframerate()
    y = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
hop = int(sr * 0.02)
m = len(y) // hop
db = 20 * np.log10(np.maximum(np.sqrt(np.mean(y[: m * hop].reshape(m, hop) ** 2, axis=1)), 1e-9))

gaps = []
for c in CUES:
    i = int(c["start_s"] / 0.02)
    j = i
    limit = min(m, i + int(1.6 / 0.02))
    while j < limit and db[j] < -40:
        j += 1
    if j > i and j < m:
        gaps.append((j - i) * 0.02)
g = np.array(gaps)
print("quiet-start cues", len(g))
for q in (10, 25, 50, 75, 90):
    print(f"p{q}", round(float(np.percentile(g, q)), 2))
print("mean", round(float(g.mean()), 2), "max", round(float(g.max()), 2))
print("share >=0.4s", round(float((g >= 0.4).mean()), 2), ">=0.8s", round(float((g >= 0.8).mean()), 2))
