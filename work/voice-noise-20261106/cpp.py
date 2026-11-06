# -*- coding: utf-8 -*-
"""Cepstral Peak Prominence (CPP) proxy: higher = clearer voice, lower = breathier.

Uses 40 ms Hann frames, real cepstrum, quefrency 1/400..1/60 s, prominence over the
local cepstral trend (dB). Frames below -40 dBFS are skipped.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
from analyze import read_wav


def cpp(path):
    y, sr = read_wav(Path(path))
    n, hop = int(sr * 0.04), int(sr * 0.02)
    vals = []
    for i in range(0, len(y) - n, hop):
        fr = y[i:i+n]
        if np.sqrt(np.mean(fr ** 2)) < 0.01:
            continue
        fr = (fr - fr.mean()) * np.hanning(n)
        spec = np.abs(np.fft.rfft(fr)) + 1e-12
        cep = np.fft.irfft(np.log(spec), n)
        qlo, qhi = int(sr / 400), int(sr / 60)
        seg = cep[qlo:qhi]
        if len(seg) < 5:
            continue
        k = int(np.argmax(seg))
        # local trend: fit a line over the search band
        x = np.arange(len(seg))
        coef = np.polyfit(x, seg, 1)
        trend = np.polyval(coef, k)
        vals.append((seg[k] - trend) * 20 / np.log(10))  # dB
    v = np.array(vals)
    return dict(n=len(v), cpp_med=round(float(np.median(v)), 2), cpp_mean=round(float(v.mean()), 2),
                cpp_p25=round(float(np.percentile(v, 25)), 2), cpp_p75=round(float(np.percentile(v, 75)), 2))


for p in sys.argv[1:]:
    print(f"{Path(p).name:28s} {cpp(p)}")
