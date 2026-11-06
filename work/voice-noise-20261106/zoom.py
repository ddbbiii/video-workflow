# -*- coding: utf-8 -*-
"""High-res spectrogram crop for visual inspection (PNG, no deps)."""
from __future__ import annotations
import struct, sys, zlib
from pathlib import Path
import numpy as np
from analyze import read_wav


def write_png_gray(img, path):
    h, w = img.shape
    raw = b"".join(b"\x00" + img[r].tobytes() for r in range(h))

    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    Path(path).write_bytes(png)


def main(path, start, dur, fmax=6000, out=None):
    y, sr = read_wav(Path(path))
    a, b = int(start * sr), int((start + dur) * sr)
    y = y[a:b]
    n = 2048
    hop = 16  # ~0.33ms -> high time resolution
    frames = np.lib.stride_tricks.sliding_window_view(y, n)[::hop] * np.hanning(n)
    spec = np.abs(np.fft.rfft(frames, axis=1)).T
    freqs = np.fft.rfftfreq(n, 1 / sr)
    spec = spec[freqs <= fmax]
    spec = 20 * np.log10(spec + 1e-10)
    lo, hi = np.percentile(spec, 10), np.percentile(spec, 99.9)
    img = np.clip((spec - lo) / (hi - lo), 0, 1)
    img = (img[::-1] * 255).astype(np.uint8)
    out = out or str(Path(path).with_suffix(f".crop{start:g}.png"))
    write_png_gray(img, out)
    print(f"{out} {img.shape[1]}x{img.shape[0]} ({dur}s, 0-{fmax}Hz)")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]) if len(sys.argv) > 4 else 6000)
