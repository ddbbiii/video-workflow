# -*- coding: utf-8 -*-
"""Objective comparison of time-stretch artifacts: inter-harmonic noise ratio (INR),
spectral flux, and frame-level crest. Lower INR / flux = cleaner (less metallic)."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
from analyze import read_wav


def f0_frame(fr, sr, lo=70, hi=350):
    fr = fr - fr.mean()
    ac = np.correlate(fr, fr, mode="full")[len(fr) - 1:]
    if ac[0] <= 0:
        return None
    ac = ac / ac[0]
    a, b = int(sr / hi), int(sr / lo)
    seg = ac[a:b]
    if len(seg) == 0:
        return None
    lag = a + int(np.argmax(seg))
    if ac[lag] < 0.25:
        return None
    return sr / lag, float(ac[lag])


def metrics(path):
    y, sr = read_wav(Path(path))
    n, hop = int(sr * 0.04), int(sr * 0.02)
    inrs, fluxes = [], []
    prev = None
    for i in range(0, len(y) - n, hop):
        fr = y[i:i+n]
        if np.sqrt(np.mean(fr ** 2)) < 0.01:
            prev = None
            continue
        r = f0_frame(fr, sr)
        if r is None:
            prev = None
            continue
        f0, rho = r
        spec = np.abs(np.fft.rfft(fr * np.hanning(n))) ** 2
        freqs = np.fft.rfftfreq(n, 1/sr)
        # harmonic mask: +/- 1.5 bins around k*f0
        mask = np.zeros(len(spec), bool)
        k = 1
        while k * f0 < sr / 2:
            mask |= np.abs(freqs - k * f0) <= 1.5 * sr / n
            k += 1
        if mask.sum() == 0 or spec.sum() <= 0:
            continue
        inrs.append(float(spec[~mask].sum() / spec.sum()))
        if prev is not None:
            fluxes.append(float(np.mean(np.abs(spec - prev)) / (np.mean(spec) + 1e-20)))
        prev = spec
    inrs = np.array(inrs); fluxes = np.array(fluxes)
    return dict(dur=round(len(y)/sr, 2), frames=len(inrs),
                inr_med=round(float(np.median(inrs)), 3), inr_mean=round(float(inrs.mean()), 3),
                inr_p90=round(float(np.percentile(inrs, 90)), 3),
                flux_med=round(float(np.median(fluxes)), 3), flux_p90=round(float(np.percentile(fluxes, 90)), 3))


def main():
    for p in sys.argv[1:]:
        m = metrics(p)
        print(f"{Path(p).name:26s} {m}")


if __name__ == "__main__":
    main()
