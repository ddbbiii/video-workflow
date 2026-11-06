# -*- coding: utf-8 -*-
"""Spot-check CosyVoice3 output with Whisper (5 units)."""
import json, sys
from pathlib import Path
import whisper

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws")
D = EP / "audio" / "vo-processed" / "b2cosy3-s90"
job = json.loads((EP / "audio" / "jobs" / "all.json").read_text(encoding="utf-8"))
texts = {s["id"]: s["text"] for s in job["shots"]}
ids = ["ch01-p01-u01", "ch02-p10-u01", "ch05-p07-u01", "ch07-p16-u01", "epilogue-p13-u01"]
m = whisper.load_model("base")
for i in ids:
    p = D / (i + ".wav")
    if not p.exists():
        print("MISSING", i); continue
    r = m.transcribe(str(p), language="zh", fp16=False)
    print("ID", i)
    print("SRC", texts.get(i, "?"))
    print("ASR", r["text"].strip())
