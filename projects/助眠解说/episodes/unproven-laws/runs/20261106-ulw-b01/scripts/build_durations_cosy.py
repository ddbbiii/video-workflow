# -*- coding: utf-8 -*-
"""Durations from CosyVoice3 processed wavs."""
import json, wave
from pathlib import Path

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws")
RUN = EP / "runs" / "20261106-ulw-b01"
D = EP / "audio" / "vo-processed" / "b2cosy3-s90"
out = {}
for p in D.glob("*.wav"):
    with wave.open(str(p), "rb") as w:
        out[p.stem] = round(w.getnframes() / w.getframerate(), 3)
(RUN / "durations.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("durations", len(out), "total_s", round(sum(out.values()), 1))
