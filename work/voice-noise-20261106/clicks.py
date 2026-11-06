# -*- coding: utf-8 -*-
"""Find clicks / hum / bursts in a PCM wav; print timestamps + save spectrogram png."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
from analyze import read_wav, db

SR_TARGET = 48000


def spectrogram(y, sr, out_png, fmax=12000, max_sec=60):
    """Dependency-free spectrogram PNG via numpy + zlib (grayscale)."""
    import struct, zlib
    y = y[: int(max_sec * sr)]
    n = 1024
    hop = 256
    if len(y) < n:
        y = np.pad(y, (0, n - len(y)))
    frames = np.lib.stride_tricks.sliding_window_view(y, n)[::hop] * np.hanning(n)
    spec = np.abs(np.fft.rfft(frames, axis=1)).T
    freqs = np.fft.rfftfreq(n, 1 / sr)
    spec = spec[freqs <= fmax]
    spec = 20 * np.log10(spec + 1e-9)
    lo, hi = np.percentile(spec, 5), np.percentile(spec, 99.9)
    img = np.clip((spec - lo) / (hi - lo), 0, 1)
    img = (img[::-1] * 255).astype(np.uint8)
    h, w = img.shape
    # grayscale PNG, filter type 0 per row
    raw = b"".join(b"\x00" + img[r].tobytes() for r in range(h))

    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6))
    png += chunk(b"IEND", b"")
    Path(out_png).write_bytes(png)
    print(f"spectrogram -> {out_png} ({w}x{h})")


def main(path):
    y, sr = read_wav(Path(path))
    dur = len(y) / sr
    print(f"\n== {path} sr={sr} dur={dur:.2f}s")
    # hum
    n = 1 << 16
    seg = y[: int(30 * sr)]
    if len(seg) < n:
        seg = np.pad(seg, (0, n - len(seg)))
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
    freqs = np.fft.rfftfreq(len(seg), 1 / sr)
    tot = spec.sum() + 1e-20
    for f in (50, 60, 100, 120, 150, 180):
        m = (freqs > f - 1.5) & (freqs < f + 1.5)
        print(f"   hum {f}Hz: {100*spec[m].sum()/tot:.4f}%  ({10*np.log10(spec[m].sum()/tot+1e-20):.1f} dBc)")
    # impulses: 1ms frames, compare peak |diff| to local 99th pct
    d = np.abs(np.diff(y))
    win = int(sr * 0.001)
    m = len(d) // win * win
    pk = d[:m].reshape(-1, win).max(axis=1)
    thr = np.percentile(pk, 99.9)
    idx = np.where(pk > max(thr * 1.8, 0.02))[0]
    print(f"   impulse thr={thr:.4f} hits={len(idx)}")
    # merge nearby hits
    times = idx * win / sr
    groups = []
    for t in times:
        if groups and t - groups[-1][-1] < 0.05:
            groups[-1].append(t)
        else:
            groups.append([t])
    for g in groups[:20]:
        t = g[0]
        i = int(t * sr)
        print(f"     click @ {t:.3f}s peakdiff={d[max(0,i-10):i+10].max():.4f} rms={db(np.sqrt(np.mean(y[max(0,i-sr//50):i+sr//50]**2))):.1f}dBFS")
    # HF bursts
    hop = int(sr * 0.02)
    mm = len(y) // hop * hop
    fr = y[:mm].reshape(-1, hop)
    hf = np.abs(np.diff(fr, axis=1)).mean(axis=1)
    hf_thr = np.percentile(hf, 99.5)
    hits = np.where(hf > hf_thr * 2.0)[0] * hop / sr
    print(f"   hf bursts={len(hits)} first={[round(float(x),2) for x in hits[:10]]}")
    spectrogram(y, sr, str(Path(path).with_suffix(".spec.png")))


if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
