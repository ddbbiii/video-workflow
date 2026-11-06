# -*- coding: utf-8 -*-
"""Re-align intro transition subtitles to intro.wav with FunASR + pause snapping."""
import re
import subprocess
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import soundfile as sf
from funasr import AutoModel

RUN = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws\runs\20261106-ulw-b01")
INTRO = RUN / "intro"
CACHE = Path(r"E:\program\1project\video\shared\runtime\engines\tts\funasr-cache\models")
ASR = next(CACHE.glob("iic--speech_seaco_paraformer*")) / "snapshots" / "master"
VAD = next(CACHE.glob("iic--speech_fsmn_vad*")) / "snapshots" / "master"
PUNCT = "，。？！；：、"


def ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return "%d:%02d:%05.2f" % (h, m, s)


def sec(t):
    h, mi, s = t.split(":")
    return int(h) * 3600 + int(mi) * 60 + float(s)


wav = RUN / "logs" / "intro16k.wav"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(INTRO / "intro.wav"),
                "-ar", "16000", "-ac", "1", str(wav)], check=True)
x, sr = sf.read(str(wav))
model = AutoModel(model=str(ASR), vad_model=str(VAD), disable_update=True)

lines = (INTRO / "intro.ass").read_text(encoding="utf-8-sig").splitlines()
head, body, keep = [], [], []
in_events = False
for l in lines:
    if l.startswith("[Events]"):
        in_events = True
        head.append(l); continue
    if not in_events:
        head.append(l); continue
    if l.startswith("Format:"):
        head.append(l); continue
    if l.startswith("Dialogue:"):
        p = l.split(",", 9)
        if p[3] in ("Hook", "Title"):
            keep.append(l)
        else:
            body.append((sec(p[1]), sec(p[2]), p[9].strip()))
print("body cues", len(body))

new = []
for s, e, text in body:
    a = max(0.0, s - 0.4); b = min(len(x) / sr, e + 0.4)
    r = model.generate(input=x[int(a * sr):int(b * sr)], batch_size_s=300)
    toks = []
    for rr in r:
        t = rr.get("text", "").replace(" ", "")
        tms = rr.get("timestamp", []) or []
        for i in range(min(len(t), len(tms))):
            toks.append((t[i], tms[i][0] / 1000 + a, tms[i][1] / 1000 + a))
    locked = [(i, ch) for i, ch in enumerate(text) if ch not in PUNCT and not ch.isspace()]
    lplain = "".join(ch for _, ch in locked)
    aplain = "".join(c for c, _, _ in toks)
    times = [None] * len(lplain)
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, lplain, aplain).get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                times[i1 + k] = (toks[j1 + k][1], toks[j1 + k][2])
    known = [i for i, v in enumerate(times) if v]
    if not known:
        new.append((s, e, text)); continue
    for i in range(known[0]):
        times[i] = times[known[0]]
    for i in range(known[-1] + 1, len(times)):
        times[i] = times[known[-1]]
    for p1, p2 in zip(known, known[1:]):
        for m in range(p1 + 1, p2):
            f = (m - p1) / (p2 - p1)
            times[m] = (times[p1][0] + (times[p2][0] - times[p1][0]) * f,
                        times[p1][1] + (times[p2][1] - times[p1][1]) * f)
    new.append((max(0.0, times[0][0]), min(len(x) / sr, times[-1][1] + 0.10), text))

# merge into longer lines (<=80% width, <=6s) before snapping
from PIL import ImageFont
FONT = ImageFont.truetype(r"E:/program/1project/video/assets/助眠解说/subtitles/style-r4/fonts/SourceHanSansSC-Heavy.otf", 54)
merged = []
for s, e, t in new:
    if merged:
        txt = merged[-1][2] + t
        if (FONT.getlength(txt) <= 1500 and e - merged[-1][0] <= 5.8
                and s - merged[-1][1] <= 0.45):
            merged[-1] = (merged[-1][0], e, txt)
            continue
    merged.append((s, e, t))
new = merged

# snap boundaries to silences
x2, sr2 = x, sr
frame = int(0.02 * sr2); n = len(x2) // frame
rms = np.sqrt(np.mean(x2[:n * frame].reshape(n, frame) ** 2, axis=1) + 1e-12)
db = 20 * np.log10(rms + 1e-12); quiet = db < -40
sil, run = [], 0
for i, q in enumerate(quiet):
    if q:
        run += 1
    else:
        if run >= 3:
            sil.append(((i - run) * frame) / sr2)
        run = 0
for i in range(len(new) - 1):
    b = new[i + 1][0]
    cand = [s for s in sil if b - 0.05 <= s <= b + 0.75]
    if cand:
        nb = cand[0] + 0.02
        new[i] = (new[i][0], nb, new[i][2])
        new[i + 1] = (nb, new[i + 1][1], new[i + 1][2])
for i in range(len(new) - 1):
    if new[i][1] > new[i + 1][0]:
        new[i] = (new[i][0], new[i + 1][0], new[i][2])

for i in range(len(new) - 1):
    new[i] = (new[i][0], max(new[i][0] + 0.5, new[i + 1][0]), new[i][2])
if new:
    new[-1] = (new[-1][0], max(new[-1][1], new[-1][0] + 0.8), new[-1][2])

out = head + keep + ["Dialogue: 0,%s,%s,body,,0,0,0,,%s" % (ts(s), ts(e), t) for s, e, t in new]
(INTRO / "intro.ass").write_text("\ufeff" + "\n".join(out) + "\n", encoding="utf-8")

subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(INTRO / "intro_bg.mp4"),
                "-i", str(INTRO / "intro.wav"), "-vf", "ass=intro.ass:fontsdir=fonts",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-shortest",
                str(INTRO / "intro.mp4")], cwd=str(INTRO), check=True)
print("intro rebuilt")
