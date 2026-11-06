# -*- coding: utf-8 -*-
"""Per-sentence FunASR alignment for subtitles (avoids utterance-level drift)."""
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


def split_sentences(text):
    out, cur = [], ""
    for ch in text:
        cur += ch
        if ch in END:
            out.append(cur); cur = ""
    if cur:
        out.append(cur)
    return out


def plain(s):
    return "".join(ch for ch in s if ch not in PUNCT and not ch.isspace())


def silence_starts(path):
    y, sr0 = sf.read(str(path))
    if y.ndim > 1:
        y = y.mean(axis=1)
    frame = int(0.02 * sr0)
    n = len(y) // frame
    rms = np.sqrt(np.mean(y[:n * frame].reshape(n, frame) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-12)
    quiet = db < -40
    out, run = [], 0
    for i, q in enumerate(quiet):
        if q:
            run += 1
        else:
            if run >= 3:
                out.append(((i - run) * frame) / sr0)
            run = 0
    return out


def snap(cues, sil):
    for i in range(len(cues) - 1):
        b = cues[i + 1][0]
        cand = [s for s in sil if b - 0.10 <= s <= b + 0.60]
        if cand:
            nb = cand[0] + 0.02
            cues[i] = (cues[i][0], nb, cues[i][2])
            cues[i + 1] = (nb, cues[i + 1][1], cues[i + 1][2])
    for i in range(len(cues) - 1):
        cues[i] = (cues[i][0], max(cues[i][0] + 0.5, cues[i + 1][0]), cues[i][2])
    return cues


def main():
    tl = json.loads((RUN / "timeline.json").read_text(encoding="utf-8"))
    off = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(RUN / "intro" / "intro.mp4")],
                         capture_output=True, text=True)
    off = float(off.stdout.strip())
    wav16 = RUN / "logs" / "body_16k_subs.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(EP / "audio" / "narration_body.wav"),
                    "-ar", "16000", "-ac", "1", str(wav16)], check=True)
    x, sr = sf.read(str(wav16))
    model = AutoModel(model=str(ASR), vad_model=str(VAD), disable_update=True)

    cues = []
    for n, u in enumerate(tl["utterances"], 1):
        sents = split_sentences(u["text"])
        total = sum(len(s) for s in sents)
        cursor = 0
        for sent in sents:
            frac = cursor / max(1, total)
            p = u["start"] + frac * (u["end"] - u["start"])
            dur = len(sent) / 3.8
            a = max(0.0, p - 0.8); b = min(len(x) / sr, p + dur + 0.8)
            r = model.generate(input=x[int(a * sr):int(b * sr)], batch_size_s=300)
            toks = []
            for rr in r:
                t = rr.get("text", "").replace(" ", "")
                tms = rr.get("timestamp", []) or []
                for i in range(min(len(t), len(tms))):
                    toks.append((t[i], tms[i][0] / 1000 + a, tms[i][1] / 1000 + a))
            lp = plain(sent)
            ap = "".join(c for c, _, _ in toks)
            times = [None] * len(lp)
            for tag, i1, i2, j1, j2 in SequenceMatcher(None, lp, ap).get_opcodes():
                if tag == "equal":
                    for k in range(i2 - i1):
                        times[i1 + k] = (toks[j1 + k][1], toks[j1 + k][2])
            known = [i for i, v in enumerate(times) if v]
            if known:
                for i in range(known[0]):
                    times[i] = times[known[0]]
                for i in range(known[-1] + 1, len(times)):
                    times[i] = times[known[-1]]
                for p1, p2 in zip(known, known[1:]):
                    for m in range(p1 + 1, p2):
                        f = (m - p1) / (p2 - p1)
                        times[m] = (times[p1][0] + (times[p2][0] - times[p1][0]) * f,
                                    times[p1][1] + (times[p2][1] - times[p1][1]) * f)
                s0, e0 = times[0][0] - 0.05, times[-1][1] + 0.25
            else:
                s0, e0 = p, p + dur
            s0 = max(0.0, s0) + 0.25; e0 = min(len(x) / sr, e0) + 0.25
            if e0 - s0 < 0.8:
                e0 = s0 + 0.8
            # wrap/scale long sentences
            if FONT.getlength(sent) <= MAX_W:
                txt, fs = sent, 54
            else:
                mid = len(sent) // 2
                cands = [i for i, ch in enumerate(sent) if ch in MID]
                cut = (min(cands, key=lambda i: abs(i - mid)) + 1) if cands else mid
                l1, l2 = sent[:cut], sent[cut:]
                wmax = max(FONT.getlength(l1), FONT.getlength(l2))
                fs = max(30, min(54, int(54 * MAX_W / max(1.0, wmax))))
                txt = (("{\\fs%d}" % fs) if fs < 54 else "") + l1 + "\\N" + l2
            cues.append((s0, e0, txt))
            cursor += len(sent)
        if n % 40 == 0:
            print("sent", n, "/", len(tl["utterances"]), flush=True)

    cues.sort(key=lambda c: c[0])
    cues = snap(cues, silence_starts(EP / "audio" / "narration_body.wav"))
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
    lines = ["Dialogue: 0,%s,%s,body,,0,0,0,,%s" % (ts(s + off), ts(e + off), t) for s, e, t in fixed]
    (RUN / "subtitles" / "body_funasr.ass").write_text("\ufeff" + head + "\n".join(lines) + "\n", encoding="utf-8")
    print("cues", len(fixed))


if __name__ == "__main__":
    main()
