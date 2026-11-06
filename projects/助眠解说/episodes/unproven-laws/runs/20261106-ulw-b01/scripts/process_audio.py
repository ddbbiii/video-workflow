# -*- coding: utf-8 -*-
"""Trim VO, slow to 0.774224, resample 48k mono, and record durations."""
import json, subprocess, wave
from pathlib import Path
import numpy as np

RUN = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws\runs\20261106-ulw-b01")
EP = RUN.parents[1]
RAW = EP / "audio" / "vo-raw" / "lightexpr-seed7"
PROC = EP / "audio" / "vo-proc"
TMP = EP / "audio" / "vo-trim"
ATEMPO = 0.774224
TRIM_RMS_DB = -45.0
FRAME_MS = 20
KEEP_HEAD = 0.10
KEEP_TAIL = 0.15

for d in (PROC, TMP):
    d.mkdir(parents=True, exist_ok=True)


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate(); n = w.getnframes(); ch = w.getnchannels(); sw = w.getsampwidth()
        data = w.readframes(n)
    if sw != 2:
        raise SystemExit("expect 16-bit wav: %s" % path)
    a = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        a = a.reshape(-1, ch).mean(axis=1)
    return a, sr


def write_wav(path, a, sr):
    a16 = np.clip(a, -1, 1)
    a16 = (a16 * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(a16.tobytes())


def trim(a, sr):
    fl = max(1, int(sr * FRAME_MS / 1000))
    n = len(a) // fl
    if n == 0:
        return a
    rms = np.sqrt(np.mean(a[: n * fl].reshape(n, fl) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-12)
    idx = np.where(db > TRIM_RMS_DB)[0]
    if len(idx) == 0:
        return a
    start = max(0, int(idx[0] * fl - KEEP_HEAD * sr))
    end = min(len(a), int((idx[-1] + 1) * fl + KEEP_TAIL * sr))
    return a[start:end]


dur = {}
files = sorted(RAW.glob("*.wav"))
for i, p in enumerate(files, 1):
    out = PROC / p.name
    if out.exists():
        with wave.open(str(out), "rb") as w:
            dur[p.stem] = round(w.getnframes() / w.getframerate(), 3)
        continue
    a, sr = read_wav(p)
    a = trim(a, sr)
    tmp = TMP / p.name
    write_wav(tmp, a, sr)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp),
           "-af", "atempo=%s,aresample=48000" % ATEMPO,
           "-ac", "1", "-c:a", "pcm_s16le", str(out)]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        print("FAIL", p.name, r.stderr[:300]); continue
    with wave.open(str(out), "rb") as w:
        dur[p.stem] = round(w.getnframes() / w.getframerate(), 3)
    if i % 20 == 0:
        print("done", i, "/", len(files), flush=True)

(RUN / "durations.json").write_text(json.dumps(dur, ensure_ascii=False, indent=1), encoding="utf-8")
print("processed", len(dur), "total_s", round(sum(dur.values()), 1))
