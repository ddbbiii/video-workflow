# -*- coding: utf-8 -*-
"""对比 sub.mp4 音轨与 narration.wav 的时移（包络互相关，±2s）。"""
import wave
from pathlib import Path
import numpy as np

EP = Path(r"E:\program\1project\video\4")
A = EP / "video/final/glacier-river_narration.wav"
B = EP / "runs/20261103-gla-b01/qa/sub_audio.wav"


def env(p, n=6000, hop_s=0.01):
    with wave.open(str(p), "rb") as w:
        sr = w.getframerate()
        y = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    hop = int(sr * hop_s)
    m = min(n, len(y) // hop)
    e = np.sqrt(np.mean(y[: m * hop].reshape(m, hop) ** 2, axis=1))
    return e, hop_s


ea, dt = env(A)
eb, _ = env(B)
ea = ea - ea.mean()
eb = eb - eb.mean()
# 找 lag: B[t+lag] 与 A[t] 对齐；lag>0 表示 B 晚
best_lag, best = 0, -1e9
for lag in range(-200, 201):  # ±2s
    if lag >= 0:
        x, y = ea[: len(ea) - lag], eb[lag:]
    else:
        x, y = ea[-lag:], eb[: len(eb) + lag]
    n = min(len(x), len(y))
    c = float(np.dot(x[:n], y[:n]) / n)
    if c > best:
        best, best_lag = c, lag
print("best lag_s", round(best_lag * dt, 3), "corr", round(best, 6))
