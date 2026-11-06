# -*- coding: utf-8 -*-
"""Print char-level ASR times for selected windows to compare with ASS cues."""
import subprocess
from pathlib import Path
import soundfile as sf
from funasr import AutoModel

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws")
RUN = EP / "runs" / "20261106-ulw-b01"
CACHE = Path(r"E:\program\1project\video\shared\runtime\engines\tts\funasr-cache\models")
ASR_DIR = next(CACHE.glob("iic--speech_seaco_paraformer*")) / "snapshots" / "master"
VAD_DIR = next(CACHE.glob("iic--speech_fsmn_vad*")) / "snapshots" / "master"
wav = RUN / "logs" / "clean16k.wav"
x, sr = sf.read(str(wav))
m = AutoModel(model=str(ASR_DIR), vad_model=str(VAD_DIR), disable_update=True)
for label, t0, t1 in [("body", 1499, 1504), ("intro", 20, 30), ("body2", 1612, 1616)]:
    seg = x[int(t0 * sr):int(t1 * sr)]
    r = m.generate(input=seg, batch_size_s=300)
    text = r[0].get("text", "").replace(" ", "")
    ts = r[0].get("timestamp", []) or []
    print("==", label, text)
    out = []
    for i, ch in enumerate(text):
        if i < len(ts):
            out.append("%s %.2f-%.2f" % (ch, ts[i][0] / 1000 + t0, ts[i][1] / 1000 + t0))
    print(" | ".join(out))
