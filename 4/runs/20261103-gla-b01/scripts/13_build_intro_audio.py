# -*- coding: utf-8 -*-
"""构建片头音轨：HEAD 0.3774 + intro p01..p05（段间0.4245）。
输出 chapters/intro.wav + intro_timeline.json。"""
import json, numpy as np, soundfile as sf
from pathlib import Path
EP = Path(r"E:\program\1project\video\4")
PROC = EP / "audio" / "vo-processed" / "lightexpr-seed7"
RUN = EP / "runs" / "20261103-gla-b01"
SR = 48000; HEAD = 0.3774; PARA_GAP = 0.4245

def sil(s): return np.zeros(int(SR*s), dtype=np.int16)

def load(p):
    y, sr = sf.read(str(p), always_2d=False)
    if y.dtype != np.int16: y = (np.clip(y, -1, 1) * 32767).astype(np.int16)
    if y.ndim > 1: y = y.mean(axis=1).astype(np.int16)
    return y

units = [f"intro-p0{i}-u01" for i in range(1, 6)]   # 预览版片头=5 个呼吸段(慢钩型,5 句)
pcm = [sil(HEAD)]; t = HEAD; tl = []
for i, u in enumerate(units):
    if i > 0:
        pcm.append(sil(PARA_GAP)); t += PARA_GAP
    y = load(PROC / f"{u}.wav"); s = t
    pcm.append(y); t += len(y) / SR
    tl.append({"id": u, "start_s": round(s,3), "end_s": round(t,3), "seconds": round(len(y)/SR,3)})
full = np.concatenate(pcm)
sf.write(str(RUN / "chapters" / "intro.wav"), full, SR, subtype="PCM_16")
intro_s = round(t, 3)
json.dump({"intro_seconds": intro_s, "intro_samples": len(full), "sample_rate": SR,
           "units": tl, "head_s": HEAD, "para_gap_s": PARA_GAP},
          open(RUN / "intro_timeline.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"intro {intro_s}s = {intro_s/60:.2f}min")
