# -*- coding: utf-8 -*-
"""Compare old vs refined cue starts against speech onsets (energy-based, independent of ASR)."""
import numpy as np, soundfile as sf
from pathlib import Path

RUN = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws\runs\20261106-ulw-b01")


def sec(t):
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def load(p):
    out = []
    for l in Path(p).read_text(encoding="utf-8-sig").splitlines():
        if l.startswith("Dialogue:"):
            q = l.split(",", 9)
            out.append((sec(q[1]), sec(q[2]), q[9].strip()))
    return out


x, sr = sf.read(str(RUN / "logs" / "body_16k_subs.wav"))
frame = int(0.01 * sr)
n = len(x) // frame
rms = np.sqrt(np.mean(x[:n * frame].reshape(n, frame) ** 2, axis=1) + 1e-12)
db = 20 * np.log10(rms + 1e-12)
off = 30.03
for name, path in [("old", RUN / "subtitles" / "body_old.ass"), ("refined", RUN / "subtitles" / "body_refined.ass")]:
    cues = load(path)
    diffs = []
    for s, e, t in cues:
        s0 = s - off
        i0 = int(max(0, s0 - 0.25) / 0.01); i1 = int(min(n, s0 + 0.6) / 0.01)
        if i0 >= i1:
            continue
        seg = db[i0:i1]
        if seg[0] > -38:  # speech already running: not a clean onset
            continue
        idx = np.where(seg > -38)[0]
        if len(idx):
            onset = (i0 + idx[0]) * 0.01
            diffs.append((onset - s0) * 1000)
    a = np.abs(np.array(diffs))
    print(name, "n", len(a), "median_abs_ms", round(float(np.median(a)), 1),
          "p90_ms", round(float(np.percentile(a, 90)), 1), "within150ms", round(float((a <= 150).mean()), 3))
