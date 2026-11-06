# -*- coding: utf-8 -*-
"""Compare cue starts with audio energy onsets for selected ranges."""
import numpy as np, soundfile as sf
from pathlib import Path

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws")
RUN = EP / "runs" / "20261106-ulw-b01"
x, sr = sf.read(str(RUN / "logs" / "clean16k.wav"))


def sec(t):
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


cues = []
for l in open(RUN / "subtitles" / "body_funasr.ass", encoding="utf-8-sig"):
    if l.startswith("Dialogue:"):
        p = l.split(",", 9)
        cues.append((sec(p[1]), sec(p[2]), p[9].strip()))

for s, e, t in cues:
    if 29 <= s <= 39 or 59 <= s <= 76:
        a = max(0, int((s - 0.6) * sr)); b = min(len(x), int((s + 0.6) * sr))
        seg = x[a:b]
        frame = int(0.02 * sr)
        n = len(seg) // frame
        rms = np.sqrt(np.mean(seg[:n * frame].reshape(n, frame) ** 2, axis=1) + 1e-12)
        db = 20 * np.log10(rms + 1e-12)
        idx = np.where(db > -38)[0]
        onset = a / sr + idx[0] * 0.02 if len(idx) else None
        print("%.2f-%.2f onset=%s off=%s | %s" % (
            s, e, "%.2f" % onset if onset else "NA",
            "%+.2f" % (onset - s) if onset else "NA", t))
