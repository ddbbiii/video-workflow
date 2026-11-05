# -*- coding: utf-8 -*-
"""过渡旁白 ASR：给 hook 模块提供字级时间戳（venv python 跑，含 funasr）。"""
import json
import subprocess
import sys
import wave
from pathlib import Path

from funasr import AutoModel
import numpy as np

IN = Path(sys.argv[1])
OUT = Path(sys.argv[2])
W16 = IN.with_suffix(".16k.wav")
FF = r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"
H = r"C:\Users\10060\.cache\modelscope\hub\iic"
ASR = H + r"\speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"

subprocess.run([FF, "-y", "-i", str(IN), "-ac", "1", "-ar", "16000", str(W16)],
               check=True, capture_output=True)
with wave.open(str(W16), "rb") as w:
    x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
model = AutoModel(model=ASR, device="cpu", disable_update=True, log_level="ERROR")
res = model.generate(input=x, batch_size_s=300)
toks = []
for r in res:
    txt = r.get("text", "").replace(" ", "")
    ts = r.get("timestamp", []) or []
    for i in range(min(len(txt), len(ts))):
        toks.append({"c": txt[i], "s": ts[i][0] / 1000, "e": ts[i][1] / 1000})
OUT.write_text(json.dumps(toks, ensure_ascii=False), encoding="utf-8")
print("tokens", len(toks), "->", OUT)
