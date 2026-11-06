# -*- coding: utf-8 -*-
"""Pre-stretch low-level gate: attenuate breath-like quiet frames BEFORE atempo,
so WSOLA never stretches noise (which is what makes the exhale sound granular).

Usage: python pregate.py <src.wav> <dst.wav> [gate_db] [gain_db]
"""
from __future__ import annotations
import sys, wave
from pathlib import Path
import numpy as np
from analyze import read_wav


def write(path, y, sr):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())


def smooth_gate(db, hop_s, gate_db, gain_db, attack=0.03, release=0.10):
    g = np.ones(len(db))
    g[db < gate_db] = 10 ** (gain_db / 20)
    # 2-pass smoothing for a soft floor
    for i in range(1, len(g)):
        a = attack if g[i] < g[i - 1] else release
        k = min(1.0, hop_s / a)
        g[i] = g[i - 1] + (g[i] - g[i - 1]) * k
    return g


def apply(y, sr, gate_db=-34.0, gain_db=-12.0, hop_s=0.005):
    hop = int(sr * hop_s)
    m = len(y) // hop
    frames = y[: m * hop].reshape(m, hop)
    rms = np.sqrt(np.mean(frames ** 2, axis=1)) + 1e-12
    db = 20 * np.log10(rms)
    g = smooth_gate(db, hop_s, gate_db, gain_db)
    out = y.copy()
    out[: m * hop] *= np.repeat(g, hop)
    return out


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    gate_db = float(sys.argv[3]) if len(sys.argv) > 3 else -34.0
    gain_db = float(sys.argv[4]) if len(sys.argv) > 4 else -12.0
    y, sr = read_wav(Path(src))
    out = apply(y, sr, gate_db, gain_db)
    write(dst, out, sr)
    print(f"{dst}: gate {gate_db} dB / {gain_db} dB")
