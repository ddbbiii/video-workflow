# -*- coding: utf-8 -*-
"""Sentence-aware FunASR subtitle builder: cues end only at sentence/clause boundaries."""
import json, subprocess
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
END = "。！？"
MID = "，；：、"
FONT = ImageFont.truetype(str(EP.parents[3] / "assets" / "助眠解说" / "subtitles" / "style-r4" / "fonts" / "SourceHanSansSC-Heavy.otf"), 54)
MAX_W = 1500.0


def ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return "%d:%02d:%05.2f" % (h, m, s)


def intro_dur():
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(RUN / "intro" / "intro.mp4")],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def split_sentences(text):
    out, cur = [], ""
    for ch in text:
        cur += ch
        if ch in END:
            out.append(cur); cur = ""
    if cur:
        out.append(cur)
    return out


def sentence_segments(text):
    """Return [(segment_text, start_index, end_index, font_size)]; complete sentences only."""
    segs = []
    pos = 0
    for sent in split_sentences(text):
        w = FONT.getlength(sent)
        if w <= MAX_W:
            segs.append((sent, pos, pos + len(sent), 54))
        else:
            # split once at the punctuation nearest the visual midpoint
            mid = len(sent) // 2
            cands = [i for i, ch in enumerate(sent) if ch in MID]
            cut = min(cands, key=lambda i: abs(i - mid)) + 1 if cands else mid
            l1, l2 = sent[:cut], sent[cut:]
            wmax = max(FONT.getlength(l1), FONT.getlength(l2))
            fs = min(54, int(54 * MAX_W / max(1.0, wmax)))
            fs = max(30, fs)
            segs.append((l1 + "\\N" + l2, pos, pos + len(sent), fs))
        pos += len(sent)
    return segs


def main():
    tl = json.loads((RUN / "timeline.json").read_text(encoding="utf-8"))
    off = intro_dur()
    wav16 = RUN / "logs" / "body_16k_subs.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(EP / "audio" / "narration_body.wav"),
                    "-ar", "16000", "-ac", "1", str(wav16)], check=True)
    x, sr = sf.read(str(wav16))
    model = AutoModel(model=str(ASR), vad_model=str(VAD), disable_update=True)

    cues = []
    PAD = 0.30
    for n, u in enumerate(tl["utterances"], 1):
        text = u["text"]
        t0 = max(0.0, u["start"] - PAD)
        t1 = min(len(x) / sr, u["end"] + PAD)
        r = model.generate(input=x[int(t0 * sr):int(t1 * sr)], batch_size_s=300)
        toks = []
        for rr in r:
            s = rr.get("text", "").replace(" ", "")
            tms = rr.get("timestamp", []) or []
            for i in range(min(len(s), len(tms))):
                toks.append((s[i], tms[i][0] / 1000 + t0, tms[i][1] / 1000 + t0))
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
            times = [(u["start"], u["end"])] * len(lplain)
        else:
            for i in range(known[0]):
                times[i] = times[known[0]]
            for i in range(known[-1] + 1, len(times)):
                times[i] = times[known[-1]]
            for a, b in zip(known, known[1:]):
                for m in range(a + 1, b):
                    f = (m - a) / (b - a)
                    times[m] = (times[a][0] + (times[b][0] - times[a][0]) * f,
                                times[a][1] + (times[b][1] - times[a][1]) * f)
        idx2plain = {}
        k = 0
        for i, ch in enumerate(text):
            if ch not in PUNCT and not ch.isspace():
                idx2plain[i] = k; k += 1
        for seg, a, b, fs in sentence_segments(text):
            pi = [idx2plain[i] for i in range(a, b) if i in idx2plain]
            if not pi:
                continue
            s0 = times[pi[0]][0]; e0 = times[pi[-1]][1]
            s0 = max(u["start"] - 0.15, s0 - 0.05)
            e0 = min(u["end"] + 0.35, e0 + 0.25)
            if e0 - s0 < 0.8:
                e0 = s0 + 0.8
            txt = (("{\\fs%d}" % fs) if fs < 54 else "") + seg
            cues.append((s0, e0, txt))
        if n % 40 == 0:
            print("aligned", n, "/", len(tl["utterances"]), flush=True)

    cues.sort(key=lambda c: c[0])
    fixed = []
    for i, (s, e, t) in enumerate(cues):
        if i + 1 < len(cues) and e > cues[i + 1][0] - 0.02:
            e = max(s + 0.5, cues[i + 1][0] - 0.02)
        fixed.append((s, e, t))

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
    lines = ["Dialogue: 0,%s,%s,body,,0,0,0,,%s" % (ts(s + off), ts(e + off), t)
             for s, e, t in fixed]
    (RUN / "subtitles" / "body_funasr.ass").write_text("\ufeff" + head + "\n".join(lines) + "\n", encoding="utf-8")
    print("cues", len(fixed), "maxw", round(max(FONT.getlength(t) for _, _, t in fixed), 1),
          "maxdur", round(max(e - s for s, e, _ in fixed), 2))


if __name__ == "__main__":
    main()
