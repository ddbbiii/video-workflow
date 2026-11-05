# -*- coding: utf-8 -*-
"""统计 cue 起点处是否已经在说话；并列出“起点静音超过 0.3s”的 cue。"""
import json, wave
from pathlib import Path
import numpy as np

EP = Path(r"E:\program\1project\video\4")
RUN = EP / "runs/20261103-gla-b01"
CUES = json.loads((RUN / "subtitles/r2/cues.json").read_text(encoding="utf-8"))["cues"]
WAV = EP / "video/final/glacier-river_narration.wav"
with wave.open(str(WAV), "rb") as w:
    sr = w.getframerate()
    y = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
hop = int(sr * 0.02)
m = len(y) // hop
db = 20 * np.log10(np.maximum(np.sqrt(np.mean(y[: m * hop].reshape(m, hop) ** 2, axis=1)), 1e-9))

early = []
for c in CUES:
    i = int(c["start_s"] / 0.02)
    lo, hi = max(0, i - 15), min(m, i + 15)
    seg = db[lo:hi]
    # 起点前 0.3s 是否静音、起点后 0.3s 是否仍静音
    pre = db[max(0, i - 15):i]
    post = db[i:min(m, i + 15)]
    if (len(post) and np.all(post < -42)) or (len(pre) and np.mean(pre < -42) > 0.8):
        early.append((c["text"][:12], c["start_s"], round(float(np.mean(post)) if len(post) else 0, 1)))
print("cues", len(CUES), "quiet_at_start", len(early), f"{len(early)/len(CUES)*100:.1f}%")
for e in early[:15]:
    print(e)
