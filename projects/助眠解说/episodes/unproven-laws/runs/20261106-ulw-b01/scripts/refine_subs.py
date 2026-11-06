# -*- coding: utf-8 -*-
"""Refine subtitle cue boundaries against ASR; writes sidecar ASS/SRT only (no video)."""
import re, subprocess, json
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import ImageFont
from funasr import AutoModel

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws")
RUN = EP / "runs" / "20261106-ulw-b01"
CACHE = Path(r"E:\program\1project\video\shared\runtime\engines\tts\funasr-cache\models")
ASR = next(CACHE.glob("iic--speech_seaco_paraformer*")) / "snapshots" / "master"
VAD = next(CACHE.glob("iic--speech_fsmn_vad*")) / "snapshots" / "master"
PUNCT = "，。？！；：、"
FONT = ImageFont.truetype(str(EP.parents[3] / "assets" / "助眠解说" / "subtitles" / "style-r4" / "fonts" / "SourceHanSansSC-Heavy.otf"), 54)
MAX_W = 1500.0


def ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return "%d:%02d:%05.2f" % (h, m, s)


def srt_ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = int(t % 60); ms = int(round((t % 1) * 1000))
    if ms == 1000:
        s += 1; ms = 0
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


def sec(t):
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def plain(s):
    return re.sub(r"\{\\[^}]*\}", "", s).replace("\\N", "")


def find_time(tokens, target, first=True):
    ap = "".join(c for c, _, _ in tokens)
    n = len(target)
    for L in (n, max(2, n - 1), 2):
        tgt = target[:L] if first else target[-L:]
        idx = ap.find(tgt) if first else ap.rfind(tgt)
        if idx >= 0:
            j = idx if first else idx + L - 1
            return tokens[j][1] if first else tokens[j][2]
    return None


def main():
    wav16 = RUN / "logs" / "body_16k_subs.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(EP / "audio" / "narration_body.wav"),
                    "-ar", "16000", "-ac", "1", str(wav16)], check=True)
    x, sr = sf.read(str(wav16))
    dur = len(x) / sr
    off = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "default=nw=1:nk=1", str(RUN / "intro" / "intro.mp4")],
                               capture_output=True, text=True).stdout.strip())
    model = AutoModel(model=str(ASR), vad_model=str(VAD), disable_update=True)

    cues = []
    for l in (RUN / "subtitles" / "body.ass").read_text(encoding="utf-8-sig").splitlines():
        if l.startswith("Dialogue:"):
            p = l.split(",", 9)
            cues.append([sec(p[1]) - off, sec(p[2]) - off, p[9].strip()])

    shifts = []
    for i, (s, e, txt) in enumerate(cues):
        tgt = plain(txt)
        # start
        a = max(0, s - 1.5); b = min(dur, s + 1.0)
        r = model.generate(input=x[int(a * sr):int(b * sr)], batch_size_s=300)
        toks = []
        for rr in r:
            t = rr.get("text", "").replace(" ", "")
            tms = rr.get("timestamp", []) or []
            for k in range(min(len(t), len(tms))):
                toks.append((t[k], tms[k][0] / 1000 + a, tms[k][1] / 1000 + a))
        ns = find_time(toks, tgt[:4], True)
        # end
        a2 = max(0, e - 1.5); b2 = min(dur, e + 0.8)
        r2 = model.generate(input=x[int(a2 * sr):int(b2 * sr)], batch_size_s=300)
        toks2 = []
        for rr in r2:
            t = rr.get("text", "").replace(" ", "")
            tms = rr.get("timestamp", []) or []
            for k in range(min(len(t), len(tms))):
                toks2.append((t[k], tms[k][0] / 1000 + a2, tms[k][1] / 1000 + a2))
        ne = find_time(toks2, tgt[-4:], False)
        if ns is not None:
            shifts.append(ns - s); s = ns - 0.05
        if ne is not None:
            ne = ne + 0.20
            if ne > s + 0.6:
                e = ne
        cues[i] = [max(0, s), min(dur, e), txt]

    # monotonic + min duration
    cues.sort(key=lambda c: c[0])
    for i, (s, e, t) in enumerate(cues):
        if i and s < cues[i - 1][1] + 0.02:
            s = cues[i - 1][1] + 0.02
        if e < s + 0.7:
            e = s + 0.7
        cues[i] = [s, e, t]

    # snap boundaries to real silence onsets
    frame = int(0.02 * sr); n = len(x) // frame
    rms = np.sqrt(np.mean(x[:n * frame].reshape(n, frame) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-12); quiet = db < -40
    sil, run = [], 0
    for i, q in enumerate(quiet):
        if q:
            run += 1
        else:
            if run >= 3:
                sil.append((i - run) * frame / sr)
            run = 0
    for i in range(len(cues) - 1):
        b = cues[i + 1][0]
        cand = [z for z in sil if b - 0.25 <= z <= b + 0.45]
        if cand:
            nb = cand[0] + 0.02
            cues[i][1] = nb; cues[i + 1][0] = nb

    # write ASS + SRT
    head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: body,SourceHanSansSC,54,&H00E8F0F5,&H00E8F0F5,&H0012100C,&H00000000,0,0,0,0,100,100,0,0,1,3,0,2,110,110,72,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ass = head + "\n".join("Dialogue: 0,%s,%s,body,,0,0,0,,%s" % (ts(s + off), ts(e + off), t)
                            for s, e, t in cues) + "\n"
    (RUN / "subtitles" / "body_refined.ass").write_text("\ufeff" + ass, encoding="utf-8")
    srt = []
    for i, (s, e, t) in enumerate(cues, 1):
        srt.append("%d\n%s --> %s\n%s\n" % (i, srt_ts(s + off), srt_ts(e + off), plain(t).replace("\\N", "\n")))
    (RUN / "subtitles" / "body_refined.srt").write_text("\n".join(srt), encoding="utf-8")

    print("cues", len(cues), "start_shift median", round(float(np.median(shifts)), 3),
          "p90", round(float(np.percentile(np.abs(shifts), 90)), 3),
          "max", round(float(np.max(np.abs(shifts))), 3))
    for s, e, t in cues:
        if 38 <= s + off <= 48:
            print(round(s + off, 2), round(e + off, 2), plain(t)[:30])


if __name__ == "__main__":
    main()
