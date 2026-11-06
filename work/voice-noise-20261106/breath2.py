# -*- coding: utf-8 -*-
"""Breath detection v2: proper per-frame mean removal + windowing, then classify
unvoiced noise runs that sit next to speech.

Outputs candidate events; `crop` mode renders a spectrogram around an event so the
shape can be checked visually.
"""
from __future__ import annotations
import struct, sys, wave, zlib
from pathlib import Path
import numpy as np
from analyze import read_wav

WIN = 0.03
HOP = 0.005


def feats(y, sr):
    n, hop = int(sr * WIN), int(sr * HOP)
    count = max(1, 1 + (len(y) - n) // hop)
    idx = np.arange(n)[None, :] + hop * np.arange(count)[:, None]
    fr = y[idx]
    fr = fr - fr.mean(axis=1, keepdims=True)
    fr = fr * np.hanning(n)[None, :]
    rms = np.sqrt(np.mean(fr ** 2, axis=1)) + 1e-12
    db = 20 * np.log10(rms)
    # normalized autocorrelation peak (pitch strength)
    spec = np.fft.rfft(fr, n=2 * n, axis=1)
    ac = np.fft.irfft(np.abs(spec) ** 2, axis=1)[:, :n]
    ac = ac / (ac[:, :1] + 1e-20)
    lo, hi = int(sr / 400), int(sr / 65)
    per = ac[:, lo:hi].max(axis=1)
    # spectral flatness in 300-4000
    pow_spec = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    freqs = np.fft.rfftfreq(n, 1 / sr)
    band = (freqs >= 300) & (freqs <= 4000)
    s = pow_spec[:, band] + 1e-20
    flat = np.exp(np.mean(np.log(s), axis=1)) / (np.mean(s, axis=1) + 1e-20)
    # zero crossing rate
    zcr = np.mean(np.abs(np.diff(np.signbit(fr), axis=1)), axis=1)
    return db, per, flat, zcr


def runs(mask, max_hole=2):
    out = []
    i = 0
    while i < len(mask):
        if not mask[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(mask) and (mask[j + 1] or (j + 1 + max_hole < len(mask) and mask[j + 1:j + 1 + max_hole].any())):
            j += 1
        out.append((i, j))
        i = j + 1
    return out


def detect(y, sr):
    db, per, flat, zcr = feats(y, sr)
    speech = db > -30
    cand = (db > -58) & (db < -24) & (per < 0.55) & (flat > 0.06)
    evs = []
    for a, b in runs(cand):
        dur = (b - a + 1) * HOP
        if not (0.06 <= dur <= 0.70):
            continue
        # must touch a speech region within 0.25 s on either side
        w = int(0.25 / HOP)
        near = speech[max(0, a - w):a].any() or speech[b + 1:b + 1 + w].any()
        if not near:
            continue
        evs.append(dict(start=round(a * HOP, 3), end=round((b + 1) * HOP, 3), dur=round(dur, 3),
                        db=round(float(db[a:b + 1].mean()), 1), per=round(float(per[a:b + 1].mean()), 2),
                        flat=round(float(flat[a:b + 1].mean()), 2), zcr=round(float(zcr[a:b + 1].mean()), 3)))
    return evs, db, per, flat


def write_png_gray(img, path):
    h, w = img.shape
    raw = b"".join(b"\x00" + img[r].tobytes() for r in range(h))

    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    Path(path).write_bytes(png)


def crop(y, sr, start, dur, out, fmax=6000):
    a, b = int(start * sr), int((start + dur) * sr)
    seg = y[a:b]
    n, hop = 1024, 8
    frames = np.lib.stride_tricks.sliding_window_view(seg, n)[::hop] * np.hanning(n)
    spec = np.abs(np.fft.rfft(frames, axis=1)).T
    freqs = np.fft.rfftfreq(n, 1 / sr)
    spec = 20 * np.log10(spec[freqs <= fmax] + 1e-10)
    lo, hi = np.percentile(spec, 10), np.percentile(spec, 99.9)
    img = (np.clip((spec - lo) / (hi - lo), 0, 1)[::-1] * 255).astype(np.uint8)
    write_png_gray(img, out)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "scan":
        for p in sys.argv[2:]:
            y, sr = read_wav(Path(p))
            evs, db, per, flat = detect(y, sr)
            print(f"\n{p}: {len(evs)} candidates, {sum(e['dur'] for e in evs):.2f}s")
            for e in evs:
                print(f"  {e['start']:7.3f}-{e['end']:7.3f} dur={e['dur']:.2f} db={e['db']:6.1f} per={e['per']:.2f} flat={e['flat']:.2f} zcr={e['zcr']:.3f}")
    elif mode == "crop":
        p, start, dur = sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
        y, sr = read_wav(Path(p))
        out = str(Path(p).with_suffix(f".b{start:g}.png"))
        crop(y, sr, start, dur, out)
        print("crop ->", out)
