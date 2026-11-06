# -*- coding: utf-8 -*-
"""Surgical tail fixes around the '下' exhale, for listening selection."""
from pathlib import Path
import numpy as np
from analyze import read_wav
from build_ab import write

WORK = Path(r"E:\program\1project\video\work\voice-noise-20261106")
SRC = WORK / "ab_long/L7_orig10_finish.wav"
OUT = WORK / "tail_test"
OUT.mkdir(parents=True, exist_ok=True)

y, sr = read_wav(SRC)
a = int(18.60 * sr)
seg = y[a:].copy()
n = len(seg)
write(OUT / "T1_original.wav", seg, sr)

# T2 tail fade: 350 ms from 20.24 s
fade_start = int((20.24 - 18.60) * sr)
t2 = seg.copy()
fade_len = n - fade_start
if fade_len > 0:
    t2[fade_start:] *= np.linspace(1, 0, fade_len) ** 1.5
write(OUT / "T2_fade.wav", t2, sr)

# T3 harmonic-preserving suppression after 20.22 s (only low-periodicity frames)
win, hop = int(0.03 * sr), int(0.005 * sr)
t3 = seg.copy()
g = np.ones(n)
start = int((20.22 - 18.60) * sr)
for i in range(start, n - win, hop):
    fr = seg[i:i + win]
    fr = fr - fr.mean()
    ac = np.correlate(fr, fr, "full")[win - 1:]
    ac /= ac[0] + 1e-20
    lo, hi = int(sr / 400), int(sr / 70)
    per = ac[lo:hi].max()
    if per < 0.5:
        g[i:i + hop] = 10 ** (-10 / 20)
k = int(0.02 * sr)
g = np.convolve(g, np.ones(k) / k, mode="same")
t3 *= g
write(OUT / "T3_suppress.wav", t3, sr)

# T4 hard cut of the suspect 20.25-20.42 s burst
t4 = seg.copy()
c0, c1 = int((20.25 - 18.60) * sr), int((20.42 - 18.60) * sr)
ramp = int(0.02 * sr)
env = np.ones(c1 - c0) * 10 ** (-30 / 20)
env[:ramp] = np.linspace(1, 10 ** (-30 / 20), ramp)
env[-ramp:] = np.linspace(10 ** (-30 / 20), 1, ramp)
t4[c0:c1] *= env
write(OUT / "T4_cut.wav", t4, sr)

for p in sorted(OUT.glob("T*.wav")):
    yy, ss = read_wav(p)
    print(p.name, round(len(yy) / ss, 2), "s")
