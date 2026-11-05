# -*- coding: utf-8 -*-
"""字幕重对齐 v4：逐单元 DP 字符对齐（替代 22 号脚本的贪心单指针），
再按子句切卡，最后加一个全局偏移（默认 +0.5s）。

背景：用户反馈"有的地方早、有的地方晚"；全局平移无法同时修好，
根因是贪心匹配在 ASR 漏字/多字时会跳时间。DP 对齐能把每个锁定字
落到最可能的 ASR 字时间上，子句边界随之稳定。

【单集移植：只改 EP / RUN / OUT 三行 CONFIG】
  EP   单集根目录；RUN  runs/<run-id>；OUT 字幕批次目录
  片头时长从 RUN/intro_v2/intro_timeline.json 读；正文字幕时间以 body_narration.wav 为准
用法：python reference_realign_subtitles.py [全局偏移秒，默认 0.5]
"""
from __future__ import annotations
import json
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from funasr import AutoModel

EP = Path(r"E:\program\1project\video\4")
RUN = EP / "runs" / "20261103-gla-b01"
TL = json.loads((RUN / "timeline.json").read_text(encoding="utf-8"))
UTT = json.loads((EP / "audio/utterances.json").read_text(encoding="utf-8"))
INTRO_TL = RUN / "intro_v2/intro_timeline.json"
BODY = RUN / "chapters/body_narration.wav"
W16 = RUN / "logs/body_16k.wav"
OUT = RUN / "subtitles/r4"
FONT = Path(r"E:\program\1project\video\assets\助眠解说\subtitles\style-r4\fonts\SourceHanSansSC-Heavy.otf")
H = r"C:\Users\10060\.cache\modelscope\hub\iic"
ASR = H + r"\speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
VAD = H + r"\speech_fsmn_vad_zh-cn-16k-common-pytorch"
FFMPEG = r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"
SR = 48000
SR_ASR = 16000
PAD = 0.25
GLOBAL = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
PUNCT = "，,。？！;；:：、— "
MAXW = 1718


def read_wav(p):
    with wave.open(str(p), "rb") as w:
        sr, ch = w.getframerate(), w.getnchannels()
        y = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        y = y.reshape(-1, ch).mean(axis=1)
    return y, sr


def unit_tokens(model, x, u0, u1):
    t0 = max(0.0, u0 - PAD)
    t1 = min(len(x) / SR_ASR, u1 + PAD)
    res = model.generate(input=x[int(t0 * SR_ASR):int(t1 * SR_ASR)], batch_size_s=300)
    toks = []
    for r in res:
        text = r.get("text", "")
        ts = r.get("timestamp", []) or []
        ch = list(text.replace(" ", ""))
        for i in range(min(len(ch), len(ts))):
            toks.append({"c": ch[i], "s": ts[i][0] / 1000 + t0, "e": ts[i][1] / 1000 + t0})
    return toks


def dp_align(locked, toks):
    """锁定字符（不含标点）与 ASR 字符的全局对齐；返回每个锁定字符的 (s,e) 或 None。"""
    A = [c for c in locked if c not in PUNCT]
    B = [t["c"] for t in toks]
    n, m = len(A), len(B)
    NEG = -10 ** 9
    dp = np.full((n + 1, m + 1), NEG, dtype=np.int32)
    ptr = np.zeros((n + 1, m + 1), dtype=np.int8)  # 1=diag 2=up 3=left
    dp[0, 0] = 0
    for i in range(1, n + 1):
        dp[i, 0] = -2 * i
        ptr[i, 0] = 2
    for j in range(1, m + 1):
        dp[0, j] = -2 * j
        ptr[0, j] = 3
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            sc = 3 if A[i - 1] == B[j - 1] else -1
            best = dp[i - 1, j - 1] + sc
            p = 1
            up = dp[i - 1, j] - 2
            if up > best:
                best, p = up, 2
            left = dp[i, j - 1] - 2
            if left > best:
                best, p = left, 3
            dp[i, j] = best
            ptr[i, j] = p
    pairs = {}
    i, j = n, m
    while i > 0 or j > 0:
        p = ptr[i, j]
        if i > 0 and j > 0 and p == 1:
            pairs[i - 1] = toks[j - 1]
            i -= 1
            j -= 1
        elif i > 0 and p == 2:
            i -= 1
        else:
            j -= 1
    return A, pairs


def fill_times(locked, pairs):
    A = [c for c in locked if c not in PUNCT]
    n = len(A)
    times = [None] * n
    for i in range(n):
        if i in pairs:
            times[i] = (pairs[i]["s"], pairs[i]["e"])
    known = [i for i in range(n) if times[i]]
    if not known:
        return A, times
    for i in range(n):
        if times[i]:
            continue
        prev = max([k for k in known if k < i], default=None)
        nxt = min([k for k in known if k > i], default=None)
        if prev is not None and nxt is not None:
            a, b = times[prev], times[nxt]
            r = (i - prev) / (nxt - prev)
            times[i] = (a[0] + (b[0] - a[0]) * r, a[1] + (b[1] - a[1]) * r)
        elif prev is not None:
            a = times[prev]
            times[i] = (a[1], a[1] + 0.08)
        elif nxt is not None:
            b = times[nxt]
            times[i] = (b[0] - 0.08, b[0])
    return A, times


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    intro = json.loads(INTRO_TL.read_text(encoding="utf-8"))["intro_seconds"]
    if not W16.exists():
        subprocess.run([FFMPEG, "-y", "-i", str(BODY), "-ac", "1", "-ar", "16000", str(W16)],
                       check=True, capture_output=True)
    x, sr = read_wav(W16)
    assert sr == SR_ASR
    model = AutoModel(model=ASR, vad_model=VAD, device="cpu", disable_update=True, log_level="ERROR")
    text_by_id = {u["id"]: u["text"] for u in UTT["utterances"]}

    cues = []
    for k, u in enumerate(TL["utterances"]):
        uid, u0, u1 = u["id"], u["start_s"], u["end_s"]
        locked = text_by_id[uid]
        toks = unit_tokens(model, x, u0, u1)
        A, pairs = dp_align(locked, toks)
        A, times = fill_times(locked, pairs)
        # 子句 -> 时间（A 下标 = 去掉标点后的序号）
        chars = []
        idx = 0
        for ch in locked:
            if ch in PUNCT:
                chars.append(None)
            else:
                chars.append(times[idx] if idx < len(times) else None)
                idx += 1
        pieces = []
        for m in re.finditer(r"[^，,。？！;；]+[，,。？！;；]?", locked):
            cl = m.group(0)
            disp = cl.strip(PUNCT)
            if not disp:
                continue
            ts = [chars[i] for i in range(m.start(), m.end()) if chars[i]]
            if not ts:
                continue
            s = min(t[0] for t in ts)
            e = max(t[1] for t in ts)
            pieces.append({"text": disp, "s": s, "e": e})
        if not pieces:
            continue
        # 极短卡并入下一句
        merged = []
        i = 0
        while i < len(pieces):
            c = pieces[i]
            if i + 1 < len(pieces) and (len(c["text"]) < 4 or c["e"] - c["s"] < 0.7):
                nxt = pieces[i + 1]
                pieces[i + 1] = {"text": c["text"] + nxt["text"], "s": c["s"], "e": nxt["e"]}
                i += 1
                continue
            merged.append(c)
            i += 1
        for c in merged:
            abs_s = intro + c["s"] + GLOBAL
            abs_e = intro + c["e"] + GLOBAL + 0.12
            cues.append({"unit": uid, "text": c["text"], "start_s": round(abs_s, 3),
                         "end_s": round(abs_e, 3)})
        if (k + 1) % 40 == 0:
            print("units", k + 1, flush=True)

    cues.sort(key=lambda c: c["start_s"])
    for a, b in zip(cues, cues[1:]):
        if a["end_s"] > b["start_s"] - 0.04:
            a["end_s"] = round(b["start_s"] - 0.04, 3)
    cues = [c for c in cues if c["end_s"] > c["start_s"] + 0.2]
    doc = {"intro_seconds": intro, "global_shift_s": GLOBAL, "aligner": "DP char align",
           "cues": cues}
    (OUT / "cues.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    def srt_t(t):
        h, m = int(t // 3600), int(t % 3600 // 60)
        s, ms = int(t % 60), int(round((t % 1) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def ass_t(t):
        h, m = int(t // 3600), int(t % 3600 // 60)
        s, cs = int(t % 60), int(round((t % 1) * 100))
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    with (OUT / "body.srt").open("w", encoding="utf-8-sig") as f:
        for i, c in enumerate(cues, 1):
            f.write(f"{i}\n{srt_t(c['start_s'])} --> {srt_t(c['end_s'])}\n{c['text']}\n\n")
    hdr = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n"
        "WrapStyle: 2\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
        "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding\n"
        "Style: B,Source Han Sans SC Heavy,96,&H00FFFFFF,&H000000FF,&H00000000,"
        "&H80000000,0,0,0,0,100,100,0,0,1,5,2,2,96,96,118,1\n\n[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    with (OUT / "body.ass").open("w", encoding="utf-8") as f:
        f.write("\ufeff" + hdr)
        for c in cues:
            f.write(f"Dialogue: 0,{ass_t(c['start_s'])},{ass_t(c['end_s'])},B,,0,0,0,,{c['text']}\n")
    burn = OUT / "burn"
    (burn / "fonts").mkdir(parents=True, exist_ok=True)
    shutil.copy(OUT / "body.ass", burn / "subs.ass")
    shutil.copy(FONT, burn / "fonts" / FONT.name)
    print("cues", len(cues), "first", cues[0]["start_s"], "last", cues[-1]["end_s"])
    print("global", GLOBAL, "->", OUT)


if __name__ == "__main__":
    main()
