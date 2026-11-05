# -*- coding: utf-8 -*-
"""字幕门禁 v1（模式 A：纯脚本，不调用 LLM）

输入：最终 narration.wav（绝对时间）+ 现有 SRT
输出：fixed.srt / fixed.ass（显式词边界折行）/ qa.md / flagged.json

门禁：
  G2 同步：逐条 cue 起止 vs 整轨 ASR 词时间；全局偏移 vs 逐条误差；5 分钟分箱漂移
  G3 能量：cue 起点前静音 / 终点后拖尾
  G4 断句：坏首尾字、数字+量词跨条、行宽、CPS、时长
自动修复：全局偏移、逐条吸附（|err|<=0.4s）、按 jieba 词边界折行；不改文字。
"""
from __future__ import annotations
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

import jieba
import numpy as np
from funasr import AutoModel
from PIL import Image, ImageFont

EP = Path(r"E:\program\1project\video\4")
RUN = EP / "runs" / "20261103-gla-b01"
SRT_IN = Path(sys.argv[1]) if len(sys.argv) > 1 else RUN / "subtitles/r4/body.srt"
NARR = EP / "video/final/glacier-river_narration.wav"
OUT = RUN / "subtitles/gate1"
W16 = RUN / "logs/narration_16k.wav"
FONT = Path(r"E:\program\1project\video\assets\助眠解说\subtitles\style-r4\fonts\SourceHanSansSC-Heavy.otf")
FFMPEG = r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"
H = r"C:\Users\10060\.cache\modelscope\hub\iic"
ASR = H + r"\speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
SR = 48000
SR_ASR = 16000
WIN = 60.0
OVERLAP = 1.0
MAXW = 1700
FONTSZ = 96
BAD_HEAD = set("的地得了着过吗呢吧啊而却也就还都和与或把被在从向因所将")
BAD_TAIL = set("的地得了着过和与或而却因所把被在从向将又也就还都才便更最不没未")
LEAD_PUNCT = set("，。！？；：、）】》”’")
TAIL_PUNCT = set("（【《“‘")
UNITS = ("年", "月", "日", "天", "小时", "分钟", "秒", "米", "公里", "千米", "厘米", "毫米",
         "度", "摄氏度", "个", "种", "次", "层", "条", "片", "块", "座", "倍", "成", "岁")
PUNCT = "，,。？！;；:：、— "


def read_wav(p):
    with wave.open(str(p), "rb") as w:
        sr, ch = w.getframerate(), w.getnchannels()
        y = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        y = y.reshape(-1, ch).mean(axis=1)
    return y, sr


def parse_srt(p):
    text = p.read_text(encoding="utf-8-sig").replace("\r", "")
    blocks = [b for b in re.split(r"\n\s*\n", text) if b.strip()]
    cues = []
    for b in blocks:
        lines = b.split("\n")
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        a, bb = lines[1].split("-->")

        def sec(t):
            h, m, rest = t.strip().split(":")
            s, ms = rest.split(",")
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

        cues.append({"start_s": round(sec(a), 3), "end_s": round(sec(bb), 3),
                     "text": " ".join(lines[2:]).strip()})
    return cues


def asr_tokens():
    if not W16.exists():
        subprocess.run([FFMPEG, "-y", "-i", str(NARR), "-ac", "1", "-ar", str(SR_ASR), str(W16)],
                       check=True, capture_output=True)
    x, sr = read_wav(W16)
    model = AutoModel(model=ASR, device="cpu", disable_update=True, log_level="ERROR")
    toks = []
    t = 0.0
    dur = len(x) / SR_ASR
    while t < dur:
        t1 = min(dur, t + WIN)
        seg = x[int(t * SR_ASR):int(t1 * SR_ASR)]
        res = model.generate(input=seg, batch_size_s=300)
        for r in res:
            txt = r.get("text", "").replace(" ", "")
            ts = r.get("timestamp", []) or []
            for i in range(min(len(txt), len(ts))):
                toks.append({"c": txt[i], "s": ts[i][0] / 1000 + t,
                             "e": ts[i][1] / 1000 + t})
        print(f"asr {t:.0f}-{t1:.0f}s tokens={len(toks)}", flush=True)
        if t1 >= dur:
            break
        t = t1 - OVERLAP
    # 去重（重叠区重复字）
    toks.sort(key=lambda z: (z["s"], z["c"]))
    out = []
    for z in toks:
        if out and z["c"] == out[-1]["c"] and abs(z["s"] - out[-1]["s"]) < 0.25:
            continue
        out.append(z)
    return out


def dp_pairs(locked, toks):
    A = [c for c in locked if c not in PUNCT]
    B = [t["c"] for t in toks]
    n, m = len(A), len(B)
    if n == 0 or m == 0:
        return {}
    NEG = -10 ** 9
    dp = np.full((n + 1, m + 1), NEG, dtype=np.int32)
    ptr = np.zeros((n + 1, m + 1), dtype=np.int8)
    dp[0, 0] = 0
    for i in range(1, n + 1):
        dp[i, 0] = -2 * i; ptr[i, 0] = 2
    for j in range(1, m + 1):
        dp[0, j] = -2 * j; ptr[0, j] = 3
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            sc = 3 if A[i - 1] == B[j - 1] else -1
            best = dp[i - 1, j - 1] + sc; p = 1
            up = dp[i - 1, j] - 2
            if up > best: best, p = up, 2
            left = dp[i, j - 1] - 2
            if left > best: best, p = left, 3
            dp[i, j] = best; ptr[i, j] = p
    pairs = {}
    i, j = n, m
    while i > 0 or j > 0:
        p = ptr[i, j]
        if i > 0 and j > 0 and p == 1:
            pairs[i - 1] = toks[j - 1]; i -= 1; j -= 1
        elif i > 0 and p == 2:
            i -= 1
        else:
            j -= 1
    return pairs


def envelope(y, sr):
    hop = int(0.02 * sr)
    m = len(y) // hop
    rms = np.sqrt(np.mean(y[: m * hop].reshape(m, hop) ** 2, axis=1))
    db = 20 * np.log10(np.maximum(rms, 1e-9))
    return db, 0.02


def speech_bounds(db, dt, a, b):
    i0, i1 = max(0, int(a / dt)), min(len(db), int(b / dt))
    seg = db[i0:i1]
    idx = np.where(seg > -40)[0]
    if not len(idx):
        return None, None
    return a + idx[0] * dt, a + (idx[-1] + 1) * dt


def width(s, font):
    return font.getlength(s)


def line_break(text, font):
    if width(text, font) <= MAXW:
        return text
    toks = list(jieba.cut(text))
    best, best_score = None, -1
    fallback, fb_score = None, -1
    for i in range(1, len(toks)):
        l, r = "".join(toks[:i]), "".join(toks[i:])
        wl, wr = width(l, font), width(r, font)
        if wl <= MAXW and wr <= MAXW:
            score = min(wl, wr) / max(wl, wr)
            if score > fb_score:
                fallback, fb_score = (l, r), score
            if r[:1] in LEAD_PUNCT or l[-1:] in TAIL_PUNCT:
                continue
            # 优先不在虚词/助词/连接词处折行
            if l[-1:] in BAD_TAIL or r[:1] in BAD_HEAD:
                continue
            if score > best_score:
                best, best_score = (l, r), score
    if best:
        return best[0] + "\\N" + best[1]
    if fallback:
        return fallback[0] + "\\N" + fallback[1]
    return text


def srt_t(t):
    h, m = int(t // 3600), int(t % 3600 // 60)
    s, ms = int(t % 60), int(round((t % 1) * 1000))
    if ms == 1000: s, ms = s + 1, 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def ass_t(t):
    h, m = int(t // 3600), int(t % 3600 // 60)
    s, cs = int(t % 60), int(round((t % 1) * 100))
    if cs == 100: s, cs = s + 1, 0
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype(str(FONT), FONTSZ)
    cues = parse_srt(SRT_IN)
    print("cues", len(cues), flush=True)
    y, sr = read_wav(NARR)
    db, dt = envelope(y, sr)
    tok_cache = OUT / "asr_tokens.json"
    if tok_cache.exists():
        toks = json.loads(tok_cache.read_text(encoding="utf-8"))
    else:
        toks = asr_tokens()
        tok_cache.write_text(json.dumps(toks, ensure_ascii=False), encoding="utf-8")
    print("tokens", len(toks), flush=True)

    for c in cues:
        a, b = c["start_s"], c["end_s"]
        near = [z for z in toks if a - 3.0 <= z["s"] <= b + 3.0]
        pairs = dp_pairs(c["text"], near)
        if pairs:
            first = min(pairs.values(), key=lambda z: z["s"])
            last = max(pairs.values(), key=lambda z: z["e"])
            c["err_start"] = a - first["s"]
            c["err_end"] = b - last["e"]
            c["ws"], c["we"] = first["s"], last["e"]
        else:
            c["err_start"] = c["err_end"] = None
        on, off = speech_bounds(db, dt, a - 1.0, b + 1.0)
        c["lead"] = None if on is None else on - a
        c["tail"] = None if off is None else b - off
        c["dur"] = b - a
        c["cps"] = len(re.sub(f"[{re.escape(PUNCT)}]", "", c["text"])) / max(0.1, c["dur"])
        c["w"] = width(c["text"], font)

    errs = np.array([c["err_start"] for c in cues if c["err_start"] is not None])
    err_e = np.array([c["err_end"] for c in cues if c["err_end"] is not None])
    med = float(np.median(errs)) if len(errs) else 0.0
    iqr = float(np.percentile(errs, 75) - np.percentile(errs, 25)) if len(errs) else 0.0
    p95 = float(np.percentile(np.abs(errs), 95)) if len(errs) else 0.0
    maxe = float(np.max(np.abs(errs))) if len(errs) else 0.0

    # 5 分钟分箱漂移
    bins = {}
    for c in cues:
        if c["err_start"] is None:
            continue
        k = int(c["start_s"] // 300)
        bins.setdefault(k, []).append(c["err_start"])
    binmed = {k: float(np.median(v)) for k, v in bins.items()}
    drift = (max(binmed.values()) - min(binmed.values())) if binmed else 0.0

    global_shift = med if abs(med) > 0.20 and iqr < 0.15 else 0.0   # 正=字幕偏晚，需要减
    corr = -global_shift
    fixed = []
    flags = []
    for c in cues:
        s, e = c["start_s"] + corr, c["end_s"] + corr
        if c["err_start"] is not None and abs(c["err_start"]) <= 0.40:
            s = c["ws"] + 0.03  # 吸附到词边界（绝对时间）
        if c["err_end"] is not None and abs(c["err_end"]) <= 0.40:
            e = c["we"] + 0.12
        if e - s < 0.6:
            e = s + 0.6
        text = c["text"]
        bad = []
        if c["w"] > MAXW * 2: bad.append("too_wide")
        if c["dur"] < 0.7: bad.append("too_short")
        if c["cps"] > 9: bad.append("cps")
        if bad:
            flags.append({"start": c["start_s"], "text": text, "flags": bad})
        fixed.append({"start_s": round(s, 3), "end_s": round(e, 3), "text": text})

    # 数字+量词跨条
    for a, b in zip(fixed, fixed[1:]):
        if re.search(r"[0-9一二三四五六七八九十百千万亿两]$", a["text"]) and b["text"][:1] in "年月日天秒米度个种次层条片块座倍岁":
            flags.append({"start": a["start_s"], "text": a["text"] + " | " + b["text"],
                          "flags": ["number_unit_break"]})

    # 写 SRT
    n_cue_flags = len(flags)
    with (OUT / "fixed.srt").open("w", encoding="utf-8-sig") as f:
        for i, c in enumerate(fixed, 1):
            f.write(f"{i}\n{srt_t(c['start_s'])} --> {srt_t(c['end_s'])}\n{c['text']}\n\n")

    # 写 ASS（显式词边界折行）
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
    with (OUT / "fixed.ass").open("w", encoding="utf-8") as f:
        f.write("\ufeff" + hdr)
        for c in fixed:
            text = line_break(c["text"], font)
            lines = text.split("\\N")
            lb = []
            if len(lines) > 2:
                lb.append("more_than_2_lines")
            for j, ln in enumerate(lines):
                if width(ln, font) > 1718:
                    lb.append("line_too_wide")
                # 单行 cue 的句首/句尾是子句边界，不按“坏首尾字”判；只查 cue 内部折行
                if len(lines) > 1:
                    if j > 0 and ln[:1] in BAD_HEAD:
                        lb.append("line_bad_head")
                    if j < len(lines) - 1 and ln[-1:] in BAD_TAIL:
                        lb.append("line_bad_tail")
            if lb:
                flags.append({"start": c["start_s"], "text": text, "flags": sorted(set(lb))})
            f.write(f"Dialogue: 0,{ass_t(c['start_s'])},{ass_t(c['end_s'])},B,,0,0,0,,{text}\n")

    qa = [
        "# 字幕门禁 v1（模式 A）", "",
        f"- 输入：`{SRT_IN}`", f"- 旁白：`{NARR}`", f"- 条数：{len(cues)}", "",
        "## G2 同步（cue 起点 vs ASR 首字）", "",
        f"- 中位误差：{med:+.3f}s；IQR：{iqr:.3f}s；|误差| P95：{p95:.3f}s；最大：{maxe:.3f}s",
        f"- 全局校正：{'字幕整体前移 ' + format(-global_shift, '+.3f') + 's' if global_shift else '不需要（逐条处理）'}",
        f"- 5 分钟分箱中位：{ {k: round(v,3) for k,v in sorted(binmed.items())} }",
        f"- 分箱漂移：{drift:.3f}s（阈值 0.30s）", "",
        "## G3 能量", "",
        f"- 起点前静音 >0.35s：{sum(1 for c in cues if c['lead'] is not None and c['lead'] > 0.35)} 条",
        f"- 终点后拖尾 >0.50s：{sum(1 for c in cues if c['tail'] is not None and c['tail'] > 0.50)} 条", "",
        "## G4 断句/排版", "",
        f"- cue 级（过短/CPS/超宽/数字量词）：{n_cue_flags} 条",
        f"- 行级（折行后超宽/坏首尾/超 2 行）：{len(flags) - n_cue_flags} 条", "",
        "## 结论", "",
        f"- {'PASS' if not flags and drift <= 0.30 else 'REVIEW'}",
    ]
    (OUT / "qa.md").write_text("\n".join(qa), encoding="utf-8")
    (OUT / "flagged.json").write_text(json.dumps(flags, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(qa))
    print("->", OUT)


if __name__ == "__main__":
    main()
