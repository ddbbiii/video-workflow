# -*- coding: utf-8 -*-
import soundfile as sf
from pathlib import Path
from funasr import AutoModel

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws")
RUN = EP / "runs" / "20261106-ulw-b01"
CACHE = Path(r"E:\program\1project\video\shared\runtime\engines\tts\funasr-cache\models")
ASR = next(CACHE.glob("iic--speech_seaco_paraformer*")) / "snapshots" / "master"
VAD = next(CACHE.glob("iic--speech_fsmn_vad*")) / "snapshots" / "master"
x, sr = sf.read(str(RUN / "logs" / "clean16k.wav"))
m = AutoModel(model=str(ASR), vad_model=str(VAD), disable_update=True)
for t0, t1 in [(0, 7), (29, 34)]:
    r = m.generate(input=x[int(t0 * sr):int(t1 * sr)], batch_size_s=300)
    text = r[0].get("text", "").replace(" ", "")
    ts = r[0].get("timestamp", []) or []
    print("==", t0, t1, text)
    print(" ".join("%s%.2f" % (text[i], ts[i][0] / 1000 + t0) for i in range(min(len(text), len(ts)))))
