# -*- coding: utf-8 -*-
"""Breath detector + attenuator for TTS narration.

A breath is a noise-like, unvoiced segment (80-600 ms) that sits next to a pause:
  * frame flatness (0.3-4 kHz) above threshold   -> noise, not tone
  * frame periodicity (autocorr peak) low        -> unvoiced
  * frame level above the local noise floor but below the speech peak
  * run length >= 100 ms and <= 800 ms
  * not touching a voiced frame except at the very edge (breaths abut pauses)

Usage:
  python breath.py scan <wav> [...]
  python breath.py apply <wav> <out.wav> [--db -20]
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
from analyze import read_wav

WIN = 0.02   # 20 ms
HOP = 0.01   # 10 ms
FLAT_TH = 0.18
PER_TH = 0.45
MIN_DB = -62.0
MAX_DB = -26.0
MIN_LEN = 0.10
MAX_LEN = 0.80


def frames(y, sr):
    n, hop = int(sr * WIN), int(sr * HOP)
    count = max(1, 1 + (len(y) - n) // hop)
    out = np.lib.stride_tricks.sliding_window_view(y, n)[::hop][:count] * np.hanning(n)
    return out, n, hop


def frame_features(fr, sr):
    rms = np.sqrt(np.mean(fr ** 2, axis=1)) + 1e-12
    db = 20 * np.log10(rms)
    spec = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    freqs = np.fft.rfftfreq(fr.shape[1], 1 / sr)
    band = (freqs >= 300) & (freqs <= 4000)
    s = spec[:, band] + 1e-20
    flat = np.exp(np.mean(np.log(s), axis=1)) / (np.mean(s, axis=1) + 1e-20)
    # periodicity: normalized autocorr peak in 70-400 Hz
    ac = np.fft.irfft(np.abs(np.fft.rfft(fr, axis=1)) ** 2, axis=1)
    ac = ac / (ac[:, :1] + 1e-20)
    lo, hi = int(sr / 400), int(sr / 70)
    per = ac[:, lo:hi].max(axis=1) if hi <= ac.shape[1] else np.zeros(len(fr))
    return db, flat, per


def detect(y, sr):
    fr, n, hop = frames(y, sr)
    db, flat, per = frame_features(fr, sr)
    cand = (db > MIN_DB) & (db < MAX_DB) & (flat > FLAT_TH) & (per < PER_TH)
    # merge runs, allow 1-frame holes
    runs = []
    i = 0
    while i < len(cand):
        if not cand[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(cand) and (cand[j + 1] or (j + 2 < len(cand) and cand[j + 2])):
            j += 1
        runs.append((i, j))
        i = j + 1
    events = []
    speech_db = np.percentile(db[db > -35], 90) if (db > -35).any() else -20
    for a, b in runs:
        dur = (b - a + 1) * HOP
        if not (MIN_LEN <= dur <= MAX_LEN):
            continue
        pad = 3
        left_voiced = per[max(0, a - pad):a].max() > PER_TH if a > 0 else False
        right_voiced = per[b + 1:b + 1 + pad].max() > PER_TH if b + 1 < len(per) else False
        ctx = np.concatenate([db[max(0, a - 10):a], db[b + 1:b + 11]])
        ctx_db = float(ctx.max()) if len(ctx) else -120
        if ctx_db > -22:   # inside a loud phrase, not a breath
            continue
        events.append(dict(start=max(0.0, a * HOP - 0.03), end=min(len(y) / sr, (b + 1) * HOP + 0.03),
                           dur=round(dur, 3), db=round(float(db[a:b + 1].mean()), 1),
                           flat=round(float(flat[a:b + 1].mean()), 3),
                           per=round(float(per[a:b + 1].mean()), 3),
                           ctx=round(ctx_db, 1), left_voiced=bool(left_voiced), right_voiced=bool(right_voiced)))
    return events


def attenuate(y, sr, events, db_gain=-20.0):
    g = np.ones(len(y))
    ramp = int(0.015 * sr)
    gv = 10 ** (db_gain / 20)
    for e in events:
        a, b = int(e["start"] * sr), int(e["end"] * sr)
        a, b = max(0, a), min(len(y), b)
        if b - a < ramp * 2:
            continue
        env = np.full(b - a, gv)
        env[:ramp] = np.linspace(1, gv, ramp)
        env[-ramp:] = np.linspace(gv, 1, ramp)
        g[a:b] = env
    return y * g


def main():
    mode = sys.argv[1]
    if mode == "scan":
        for p in sys.argv[2:]:
            y, sr = read_wav(Path(p))
            ev = detect(y, sr)
            print(f"\n{p}: {len(ev)} events, total {sum(e['dur'] for e in ev):.2f}s")
            for e in ev:
                print(f"   {e['start']:7.3f}-{e['end']:7.3f} dur={e['dur']:.2f} db={e['db']:6.1f} flat={e['flat']:.2f} per={e['per']:.2f} ctx={e['ctx']:5.1f} L={int(e['left_voiced'])} R={int(e['right_voiced'])}")
    elif mode == "apply":
        src, dst = sys.argv[2], sys.argv[3]
        db_gain = -20.0
        if "--db" in sys.argv:
            db_gain = float(sys.argv[sys.argv.index("--db") + 1])
        y, sr = read_wav(Path(src))
        ev = detect(y, sr)
        out = attenuate(y, sr, ev, db_gain)
        import wave
        out16 = np.clip(out, -1, 1)
        with wave.open(str(dst), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
            w.writeframes((out16 * 32767).astype("<i2").tobytes())
        print(f"{dst}: {len(ev)} breaths attenuated {db_gain} dB ({sum(e['dur'] for e in ev):.2f}s)")


if __name__ == "__main__":
    main()
