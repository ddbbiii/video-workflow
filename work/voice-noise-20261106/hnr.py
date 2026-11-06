# -*- coding: utf-8 -*-
"""Voiced-frame HNR + harmonic/noise ratio to judge hoarseness/breathiness."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
from analyze import read_wav


def hnr_frames(y, sr, frame_ms=40, hop_ms=10):
    n = int(sr * frame_ms / 1000)
    hop = int(sr * hop_ms / 1000)
    vals = []
    for i in range(0, len(y) - n, hop):
        fr = y[i:i+n] * np.hanning(n)
        e = np.sqrt(np.mean(fr ** 2))
        if e < 1e-3:
            continue
        ac = np.correlate(fr, fr, mode="full")[n-1:]
        ac /= (ac[0] + 1e-20)
        lo, hi = int(sr / 400), int(sr / 70)  # 70-400 Hz
        if hi >= len(ac):
            continue
        lag = lo + int(np.argmax(ac[lo:hi]))
        r = ac[lag]
        if r <= 0:
            continue
        hnr = 10 * np.log10(r / (1 - r + 1e-12))
        vals.append(hnr)
    return np.array(vals)


for p in sys.argv[1:]:
    y, sr = read_wav(Path(p))
    h = hnr_frames(y, sr)
    print(f"{Path(p).name:26s} n={len(h):5d} HNR p10={np.percentile(h,10):5.1f} p50={np.percentile(h,50):5.1f} p90={np.percentile(h,90):5.1f} mean={h.mean():5.1f} dB")
