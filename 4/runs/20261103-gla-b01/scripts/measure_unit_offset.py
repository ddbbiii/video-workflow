# -*- coding: utf-8 -*-
"""按单元量：单元内第一句字幕起点 vs 该单元语音实际起点（-45dB）。"""
import json, wave
from pathlib import Path
import numpy as np

EP = Path(r"E:\program\1project\video\4")
RUN = EP / "runs/20261103-gla-b01"
TL = json.loads((RUN / "timeline.json").read_text(encoding="utf-8"))
CUES = json.loads((RUN / "subtitles/r2/cues.json").read_text(encoding="utf-8"))["cues"]
INTRO = json.loads((RUN / "intro_v2/intro_timeline.json").read_text(encoding="utf-8"))["intro_seconds"]
WAV = EP / "video/final/glacier-river_narration.wav"

with wave.open(str(WAV), "rb") as w:
    sr = w.getframerate()
    y = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
hop = int(sr * 0.02)


def onset_in(a, b):
    i0, i1 = int(a * sr), int(b * sr)
    seg = y[i0:i1]
    m = len(seg) // hop
    if m <= 0:
        return None
    rms = np.sqrt(np.mean(seg[: m * hop].reshape(m, hop) ** 2, axis=1))
    db = 20 * np.log10(np.maximum(rms, 1e-9))
    idx = np.where(db > -45)[0]
    return a + idx[0] * 0.02 if len(idx) else None


first_cue = {}
for c in CUES:
    first_cue.setdefault(c["unit"], c)
deltas = []
rows = []
for u in TL["utterances"]:
    c = first_cue.get(u["id"])
    if not c:
        continue
    u0, u1 = u["start_s"], u["end_s"]
    on = onset_in(INTRO + u0, INTRO + u1)
    if on is None:
        continue
    cue_start = c["start_s"]
    d = cue_start - on
    deltas.append(d)
    rows.append((u["id"], round(u0, 2), round(on - INTRO, 2), round(cue_start - INTRO, 2), round(d, 2)))
d = np.array(deltas)
print("units", len(d))
for q in (5, 25, 50, 75, 95):
    print(f"p{q}", round(float(np.percentile(d, q)), 3))
print("mean", round(float(d.mean()), 3))
print("sample")
for r in rows[:12]:
    print(r)
