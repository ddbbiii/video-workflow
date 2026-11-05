# -*- coding: utf-8 -*-
"""单元唯一 cue：起点/终点 vs 语音实际首末（-45dB）。"""
import json, wave
from pathlib import Path
import numpy as np

EP = Path(r"E:\program\1project\video\4")
RUN = EP / "runs" / "20261103-gla-b01"
TL = json.loads((RUN / "timeline.json").read_text(encoding="utf-8"))
CUES = json.loads((RUN / "subtitles/r2/cues.json").read_text(encoding="utf-8"))["cues"]
INTRO = json.loads((RUN / "intro_v2/intro_timeline.json").read_text(encoding="utf-8"))["intro_seconds"]
WAV = EP / "video/final/glacier-river_narration.wav"
with wave.open(str(WAV), "rb") as w:
    sr = w.getframerate()
    y = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
hop = int(sr * 0.02)


def bounds(a, b):
    seg = y[int(a * sr):int(b * sr)]
    m = len(seg) // hop
    if m <= 0:
        return None, None
    rms = np.sqrt(np.mean(seg[: m * hop].reshape(m, hop) ** 2, axis=1))
    db = 20 * np.log10(np.maximum(rms, 1e-9))
    idx = np.where(db > -45)[0]
    if not len(idx):
        return None, None
    return a + idx[0] * 0.02, a + (idx[-1] + 1) * 0.02


by_unit = {}
for c in CUES:
    by_unit.setdefault(c["unit"], []).append(c)
ds, de = [], []
for u in TL["utterances"]:
    cs = by_unit.get(u["id"], [])
    if len(cs) != 1:
        continue
    on, off = bounds(INTRO + u["start_s"], INTRO + u["end_s"])
    if on is None:
        continue
    c = cs[0]
    ds.append(c["start_s"] - on)
    de.append(c["end_s"] - off)
for name, arr in (("start", ds), ("end", de)):
    a = np.array(arr)
    print(name, "n", len(a),
          "p5", round(float(np.percentile(a, 5)), 2),
          "p50", round(float(np.percentile(a, 50)), 2),
          "p95", round(float(np.percentile(a, 95)), 2),
          "mean", round(float(a.mean()), 2))
print("sample end", [round(x, 2) for x in de[:12]])
