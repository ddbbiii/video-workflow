# -*- coding: utf-8 -*-
"""Graininess of breath segments: envelope modulation energy in 15-70 Hz.

WSOLA time-stretch turns a smooth noise exhale into a periodic grain train; the
artifact shows up as excess 15-70 Hz modulation of the segment envelope.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
from analyze import read_wav
from breath2 import detect


def modulation_index(y, sr, a, b):
    seg = y[int(a * sr):int(b * sr)]
    if len(seg) < int(0.05 * sr):
        return None
    hop = int(0.002 * sr)
    m = len(seg) // hop
    if m < 8:
        return None
    env = np.sqrt(np.mean(seg[: m * hop].reshape(m, hop) ** 2, axis=1))
    env = env - env.mean()
    if np.std(env) < 1e-6:
        return None
    spec = np.abs(np.fft.rfft(env * np.hanning(len(env)))) ** 2
    freqs = np.fft.rfftfreq(len(env), hop / sr)
    band = (freqs >= 15) & (freqs <= 70)
    return float(spec[band].sum() / (spec.sum() + 1e-20))


for p in sys.argv[1:]:
    y, sr = read_wav(Path(p))
    evs, *_ = detect(y, sr)
    vals = [v for e in evs if (v := modulation_index(y, sr, e["start"], e["end"])) is not None]
    if not vals:
        print(f"{Path(p).name:28s} no breath segments")
        continue
    v = np.array(vals)
    print(f"{Path(p).name:28s} n={len(v):2d} mod15-70 med={np.median(v):.3f} mean={v.mean():.3f} p75={np.percentile(v,75):.3f}")
