# -*- coding: utf-8 -*-
"""Voice-noise probe: read PCM wav via stdlib wave, report level/spectrum/noise floor."""
from __future__ import annotations
import sys, wave
from pathlib import Path
import numpy as np


def read_wav(path: Path):
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        nch = w.getnchannels()
        sw = w.getsampwidth()
        n = w.getnframes()
        raw = w.readframes(n)
    if sw == 2:
        y = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    elif sw == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        v = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
        v = np.where(v & 0x800000, v - 0x1000000, v)
        y = v.astype(np.float64) / 8388608.0
    elif sw == 4:
        y = np.frombuffer(raw, dtype="<i4").astype(np.float64) / 2147483648.0
    else:
        raise ValueError(f"unsupported sampwidth {sw}")
    if nch > 1:
        y = y.reshape(-1, nch).mean(axis=1)
    return y, sr


def db(x):
    return 20 * np.log10(max(float(x), 1e-12))


def frame_rms(y, sr, ms=20):
    n = max(1, int(sr * ms / 1000))
    m = len(y) // n
    if m == 0:
        return np.array([np.sqrt(np.mean(y ** 2))])
    return np.sqrt(np.mean(y[: m * n].reshape(m, n) ** 2, axis=1))


def band_energy(y, sr):
    # Welch-free: average periodogram over 4096 frames
    n = 4096
    if len(y) < n:
        y = np.pad(y, (0, n - len(y)))
    hop = n // 2
    win = np.hanning(n)
    frames = np.lib.stride_tricks.sliding_window_view(y, n)[::hop] * win
    spec = np.abs(np.fft.rfft(frames, axis=1)) ** 2
    psd = spec.mean(axis=0)
    freqs = np.fft.rfftfreq(n, 1 / sr)
    total = psd.sum() + 1e-20
    bands = [(0, 80), (80, 300), (300, 1000), (1000, 3000), (3000, 6000), (6000, 8000), (8000, 12000), (12000, 16000), (16000, 24000)]
    out = {}
    for lo, hi in bands:
        if hi > sr / 2:
            continue
        m = (freqs >= lo) & (freqs < hi)
        out[f"{lo//1000 if lo>=1000 else lo}-{hi//1000 if hi>=1000 else hi}k" if hi >= 1000 else f"{lo}-{hi}"] = round(100 * psd[m].sum() / total, 2)
    # spectral flatness
    flat = float(np.exp(np.mean(np.log(psd + 1e-30))) / (np.mean(psd) + 1e-30))
    # centroid
    cen = float((freqs * psd).sum() / (psd.sum() + 1e-30))
    return out, flat, cen


def analyze(path: Path, label=None):
    y, sr = read_wav(path)
    dur = len(y) / sr
    r = frame_rms(y, sr)
    rdb = 20 * np.log10(np.maximum(r, 1e-12))
    active = rdb > (rdb.max() - 45)
    # noise floor estimate: 10th percentile of frames that are below speech median
    floor = np.percentile(rdb, 5)
    speech = np.percentile(rdb[active], 50) if active.any() else np.nan
    bands, flat, cen = band_energy(y, sr)
    clip = int(np.sum(np.abs(y) >= 0.999))
    dc = float(np.mean(y))
    # zero crossing rate
    zcr = float(np.mean(np.abs(np.diff(np.signbit(y).astype(np.int8)))))
    print(f"\n== {label or path.name}")
    print(f"   path={path}")
    print(f"   sr={sr} dur={dur:.2f}s peak={db(np.abs(y).max()):.2f}dBFS rms={db(np.sqrt(np.mean(y**2))):.2f}dBFS")
    print(f"   frame p95={np.percentile(rdb,95):.1f} p50={np.percentile(rdb,50):.1f} p5={floor:.1f} floor_gap={speech-floor:.1f}dB")
    print(f"   clip={clip} dc={dc:+.2e} zcr={zcr:.4f} flatness={flat:.5f} centroid={cen:.0f}Hz")
    print(f"   bands%={bands}")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        analyze(Path(p))
