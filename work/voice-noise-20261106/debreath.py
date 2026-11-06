# -*- coding: utf-8 -*-
"""De-breath: detect synthetic breath segments and either mute or soften them.

Runs BEFORE atempo so WSOLA never stretches noise.
  mute   : -30 dB, 25 ms ramps -> exhale effectively disappears
  soften : -9 dB + 2.5 kHz low-pass + smooth 40 ms envelope -> reads as air, not a puff
"""
from __future__ import annotations
import sys, wave
from pathlib import Path
import numpy as np
from analyze import read_wav
from breath2 import detect


def write(path, y, sr):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())


def rbj_lowpass(y, sr, fc=2500.0, q=0.707):
    w0 = 2 * np.pi * fc / sr
    c, s = np.cos(w0), np.sin(w0)
    alpha = s / (2 * q)
    b = [(1 - c) / 2, 1 - c, (1 - c) / 2]
    a = [1 + alpha, -2 * c, 1 - alpha]
    b = [x / a[0] for x in b]
    a = [1.0, a[1] / a[0], a[2] / a[0]]
    out = np.zeros_like(y)
    x1 = x2 = y1 = y2 = 0.0
    for i, v in enumerate(y):
        o = b[0] * v + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2
        x2, x1 = x1, v
        y2, y1 = y1, o
        out[i] = o
    return out


def apply_events(y, sr, events, mode="mute", ramp_s=0.025):
    out = y.copy()
    ramp = max(1, int(ramp_s * sr))
    for e in events:
        a, b = max(0, int(e["start"] * sr)), min(len(y), int(e["end"] * sr))
        if b - a < 2 * ramp:
            continue
        seg = y[a:b]
        if mode == "soften":
            seg = rbj_lowpass(seg, sr, 2500.0)
        g = 10 ** (-30 / 20) if mode == "mute" else 10 ** (-9 / 20)
        env = np.full(b - a, g)
        env[:ramp] = np.linspace(1, g, ramp)
        env[-ramp:] = np.linspace(g, 1, ramp)
        if mode == "soften":
            # smooth the envelope inside the segment too
            k = max(1, int(0.04 * sr))
            env = np.convolve(env, np.ones(k) / k, mode="same")
        out[a:b] = seg * env
    return out


if __name__ == "__main__":
    src, dst, mode = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "mute")
    y, sr = read_wav(Path(src))
    evs, *_ = detect(y, sr)
    out = apply_events(y, sr, evs, mode)
    write(dst, out, sr)
    print(f"{dst}: mode={mode} events={len(evs)} total={sum(e['dur'] for e in evs):.2f}s")
