# -*- coding: utf-8 -*-
"""Check subtitle vs audio at given times using FunASR on the final clean."""
import subprocess
from pathlib import Path
import numpy as np, soundfile as sf
from funasr import AutoModel

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws")
RUN = EP / "runs" / "20261106-ulw-b01"
CACHE = Path(r"E:\program\1project\video\shared\runtime\engines\tts\funasr-cache\models")
ASR_DIR = next(CACHE.glob("iic--speech_seaco_paraformer*")) / "snapshots" / "master"
VAD_DIR = next(CACHE.glob("iic--speech_fsmn_vad*")) / "snapshots" / "master"
CLEAN = EP / "video" / "final" / "unproven-laws_clean.mp4"
wav = RUN / "logs" / "clean16k.wav"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(CLEAN), "-ar", "16000", "-ac", "1", str(wav)], check=True)
x, sr = sf.read(str(wav))
m = AutoModel(model=str(ASR_DIR), vad_model=str(VAD_DIR), disable_update=True)
for label, t0, t1 in [("intro23-27", 23, 27), ("body1500-1503", 1500, 1503), ("body1612-1616", 1612, 1616), ("body25-28", 25, 28)]:
    seg = x[int(t0 * sr):int(t1 * sr)]
    r = m.generate(input=seg, batch_size_s=300)
    print(label, "|", "".join(r[0].get("text", "")))
