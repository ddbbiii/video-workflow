# -*- coding: utf-8 -*-
"""VAD-boundary subtitles: sentence changes only at real speech onsets."""
import json, subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import ImageFont
from funasr import AutoModel

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws")
RUN = EP / "runs" / "20261106-ulw-b01"
CACHE = Path(r"E:\program\1project\video\shared\runtime\engines\tts\funasr-cache\models")
VAD = next(CACHE.glob("iic--speech_fsmn_vad*")) / "snapshots" / "master"
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


def main():
    tl = json.loads((RUN / "timeline.json").read_text(encoding="utf-8"))
    off = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "default=nw=1:nk=1", str(RUN / "intro" / "intro.mp4")],
                               capture_output=True, text=True).stdout.strip())
    wav16 = RUN / "logs" / "body_16k_subs.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(EP / "audio" / "narration_body.wav"),
                    "-ar", "16000", "-ac", "1", str(wav16)], check=True)
    x, sr = sf.read(str(wav16))
    total = len(x) / sr
    vad = AutoModel(model=str(VAD), disable_update=True)
    res = vad.generate(input=x)
    segs = res[0].get("value", [])
    bounds = [s[0] / 1000 for s in segs]
    print("vad segments", len(bounds), "first", bounds[:3], "last", bounds[-1:])

    sents = []
    for u in tl["utterances"]:
        sents.extend(split_sentences(u["text"]))
    print("sentences", len(sents))
    chars = [len(s) for s in sents]
    cum = np.cumsum(chars) / sum(chars)

    # snap each sentence boundary proportionally to the nearest VAD onset (monotonic)
    chosen = [0]
    bi = 0
    for f in cum[:-1]:
        target = f * total
        best = bi
        for j in range(bi, len(bounds)):
            if bounds[j] <= target + 1.2:
                best = j
            else:
                break
        # pick nearest onset to target, not before previous
        cand = [j for j in range(bi, min(len(bounds), best + 2))]
        j = min(cand, key=lambda k: abs(bounds[k] - target)) if cand else bi
        chosen.append(j); bi = j
    chosen.append(len(bounds))
    print("boundaries", len(chosen))
    cues = []
    for i, s in enumerate(sents):
        a = bounds[chosen[i]] if chosen[i] < len(bounds) else total
        b = bounds[chosen[i + 1]] if chosen[i + 1] < len(bounds) else total
        if b - a < 0.5:
            b = a + 0.5
        if FONT.getlength(s) <= MAX_W:
            txt, fs = s, 54
        else:
            mid = len(s) // 2
            cands = [k for k, ch in enumerate(s) if ch in MID]
            cut = (min(cands, key=lambda k: abs(k - mid)) + 1) if cands else mid
            l1, l2 = s[:cut], s[cut:]
            wmax = max(FONT.getlength(l1), FONT.getlength(l2))
            fs = max(30, min(54, int(54 * MAX_W / max(1.0, wmax))))
            txt = (("{\\fs%d}" % fs) if fs < 54 else "") + l1 + "\\N" + l2
        cues.append((a, b, txt))

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
    lines = ["Dialogue: 0,%s,%s,body,,0,0,0,,%s" % (ts(s + off), ts(e + off), t) for s, e, t in cues]
    (RUN / "subtitles" / "body_funasr.ass").write_text("\ufeff" + head + "\n".join(lines) + "\n", encoding="utf-8")
    print("cues", len(cues))


if __name__ == "__main__":
    main()
