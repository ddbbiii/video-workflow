# -*- coding: utf-8 -*-
"""把 cue 起点吸附到最近的语音起始点，统计需要移动多少（只诊断，不写文件）。"""
import json, wave
from pathlib import Path
import numpy as np

EP = Path(r"E:\program\1project\video\4")
RUN = EP / "runs" / "20261103-gla-b01"
CUES = json.loads((RUN / "subtitles/r2/cues.json").read_text(encoding="utf-8"))["cues"]
WAV = EP / "video/final/glacier-river_narration.wav"
with wave.open(str(WAV), "rb") as w:
    sr = w.getframerate()
    y = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
hop = int(sr * 0.02)
m = len(y) // hop
db = 20 * np.log10(np.maximum(np.sqrt(np.mean(y[: m * hop].reshape(m, hop) ** 2, axis=1)), 1e-9))
on = db > -40
onsets = np.array([i * 0.02 for i in range(1, len(on)) if on[i] and not on[i - 1]])

shifts = []
for c in CUES:
    s = c["start_s"]
    cand = onsets[(onsets > s - 0.15) & (onsets < s + 0.55)]
    if len(cand):
        shifts.append((min(cand, key=lambda x: abs(x - s)) - s, c["text"][:14], s))
sh = np.array([x[0] for x in shifts])
print("cues", len(CUES), "matched", len(sh))
for q in (5, 25, 50, 75, 95):
    print(f"p{q}", round(float(np.percentile(sh, q)), 2))
print("mean", round(float(sh.mean()), 2))
top = sorted(shifts, key=lambda x: -abs(x[0]))[:10]
for t in top:
    print(round(t[0], 2), round(t[2], 2), t[1])
