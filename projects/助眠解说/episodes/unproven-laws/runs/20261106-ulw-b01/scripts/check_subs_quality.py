# -*- coding: utf-8 -*-
"""Spot-check subtitle cues against audio with FunASR."""
import re
from pathlib import Path
import soundfile as sf
from funasr import AutoModel

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws")
RUN = EP / "runs" / "20261106-ulw-b01"
CACHE = Path(r"E:\program\1project\video\shared\runtime\engines\tts\funasr-cache\models")
ASR = next(CACHE.glob("iic--speech_seaco_paraformer*")) / "snapshots" / "master"
VAD = next(CACHE.glob("iic--speech_fsmn_vad*")) / "snapshots" / "master"
x, sr = sf.read(str(RUN / "logs" / "clean16k.wav"))
m = AutoModel(model=str(ASR), vad_model=str(VAD), disable_update=True)


def sec(t):
    h, mi, s = t.split(":")
    return int(h) * 3600 + int(mi) * 60 + float(s)


cues = []
for l in open(RUN / "subtitles" / "body_funasr.ass", encoding="utf-8-sig"):
    if l.startswith("Dialogue:"):
        p = l.split(",", 9)
        cues.append((sec(p[1]), sec(p[2]), p[9].strip()))
print("cues", len(cues))
bad = []
for i in range(0, len(cues), max(1, len(cues) // 20)):
    s, e, text = cues[i]
    a, b = max(0, s - 0.15), min(len(x) / sr, e + 0.15)
    r = m.generate(input=x[int(a * sr):int(b * sr)], batch_size_s=300)
    asr = re.sub(r"[^\u4e00-\u9fff]", "", "".join(r[0].get("text", "")))
    tgt = re.sub(r"[^\u4e00-\u9fff]", "", text)
    hit = sum(1 for ch in tgt if ch in asr)
    ratio = hit / max(1, len(tgt))
    flag = "" if ratio >= 0.6 else " <<<"
    print("%.2f %.2f %s | %s | %.2f%s" % (s, e, text[:18], asr[:24], ratio, flag))
    if ratio < 0.6:
        bad.append((s, text, asr))
print("bad", len(bad))
