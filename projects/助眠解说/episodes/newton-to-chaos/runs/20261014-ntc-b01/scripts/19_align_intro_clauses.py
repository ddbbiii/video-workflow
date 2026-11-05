# -*- coding: utf-8 -*-
"""片头子句卡时间轴(intro-node.md §2/§4:句界来自实际语音边界,禁止字符比例)。

流程:intro.wav(48k mono) → 16k wav → FunASR 字级时间戳 →
按 [，。？！；：] 把 5 段片头口播切成子句 → 双指针匹配 ASR 字符流取实测起止 →
段边界吸附 intro_timeline.json → 短卡合并(<4字 或 <1.5s 并入后卡) → intro_cards.json。

运行环境:voxcpm venv(需 funasr/numpy/soundfile)。
用法:python 19_align_intro_clauses.py
"""
import json, re, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
from funasr import AutoModel

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\newton-to-chaos")
RUN = EP / "runs" / "20261014-ntc-b01"
INTRO_WAV = RUN / "chapters" / "intro.wav"
INTRO_TL = RUN / "intro_timeline.json"
UTT = EP / "audio" / "utterances.json"
OUT = RUN / "intro_cards.json"
WORK16K = RUN / "logs" / "intro_16k.wav"
FFMPEG = r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"
H = r"C:\Users\10060\.cache\modelscope\hub\iic"
ASR = H + r"\speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
VAD = H + r"\speech_fsmn_vad_zh-cn-16k-common-pytorch"

# 显示层文本转换:数字转汉字(地磁集先例,"41"→"四十一")
CN_NUM = {"0": "零", "1": "一", "2": "二", "3": "三", "4": "四",
          "5": "五", "6": "六", "7": "七", "8": "八", "9": "九"}
TENS = {2: "十", 3: "百"}


def digits_to_cn(s):
    def repl(m):
        d = m.group(0)
        if len(d) == 1:
            return CN_NUM[d]
        if len(d) == 2:
            return (""
                    + (CN_NUM[d[0]] if d[0] != "1" else "")
                    + "十"
                    + (CN_NUM[d[1]] if d[1] != "0" else ""))
        return "".join(CN_NUM[c] for c in d)  # 3位以上罕见,逐字
    return re.sub(r"\d+", repl, s)


def split_clauses(text):
    """按标点切子句,保留文本(去首尾空白)。"""
    parts = re.split(r"[，。？！；：]", text)
    return [p.strip() for p in parts if p.strip()]


def match_chars(locked, tokens):
    """单指针顺序匹配:锁定稿字符流 vs ASR 字符流(同源 TTS,容忍少量差异)。
    全片单次匹配保证时间单调;返回 每个锁定字符的 (s,e) 或 None。"""
    res = [None] * len(locked)
    j = 0
    n = len(tokens)
    for i, ch in enumerate(locked):
        if ch in "，。？！；：、 ":
            continue
        k = j
        while k < n and tokens[k]["c"] != ch:
            k += 1
        if k < n:
            res[i] = (tokens[k]["s"], tokens[k]["e"])
            j = k + 1
    return res


def main():
    tl = json.loads(INTRO_TL.read_text(encoding="utf-8"))
    utt = json.loads(UTT.read_text(encoding="utf-8"))
    paras = [u for u in utt["utterances"] if u["id"].startswith("intro")]
    assert len(paras) == len(tl["units"]), "intro paragraph count mismatch"

    # 1. 16k mono wav
    WORK16K.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([FFMPEG, "-y", "-i", str(INTRO_WAV), "-ac", "1", "-ar", "16000",
                    str(WORK16K)], check=True, capture_output=True)

    # 2. FunASR 字级时间戳:按段落窗口识别并加窗口偏移。
    #    (整段识别时 VAD 分段的时间戳是段内相对时间,跨段会塌缩)
    model = AutoModel(model=ASR, vad_model=VAD, device="cpu",
                      disable_update=True, log_level="ERROR")
    x, sr = sf.read(str(WORK16K), dtype="float32")
    tokens = []
    for unit in tl["units"]:
        t0 = max(0.0, unit["start_s"] - 0.30)
        t1 = min(len(x) / sr, unit["end_s"] + 0.30)
        res = model.generate(input=x[int(t0 * sr):int(t1 * sr)], batch_size_s=300)
        for r in res:
            t = r.get("text", "")
            ts = r.get("timestamp", []) or []
            ch = list(t.replace(" ", ""))
            n = min(len(ch), len(ts))
            for i in range(n):
                tokens.append({"c": ch[i],
                               "s": ts[i][0] / 1000 + t0,
                               "e": ts[i][1] / 1000 + t0})
    print(f"ASR tokens: {len(tokens)}")

    # 3. 全片单次字符匹配,再按段落切子句区间
    all_locked = "".join(p["text"] for p in paras)
    ch_at = match_chars(list(all_locked), tokens)

    cards = []
    cursor = 0
    for para, unit in zip(paras, tl["units"]):
        p_start, p_end = unit["start_s"], unit["end_s"]
        locked = para["text"]
        clauses = split_clauses(locked)
        idx = cursor
        spans = []
        for cl in clauses:
            L = len(cl)
            spans.append((idx, idx + L))
            idx += L + 1  # 跳过一个标点
        for cl, (a, b) in zip(clauses, spans):
            ts = [ch_at[i] for i in range(a, b) if ch_at[i] is not None]
            if ts:
                s = min(t[0] for t in ts)
                e = max(t[1] for t in ts)
            else:  # 无匹配(如纯数字):段落内兜底,标记 draft 由人工复核
                s, e = p_start, p_end
                print(f"WARN: clause no-match, fallback to para window: {cl}")
            assert s <= e, f"non-monotonic clause time: {cl} {s}>{e}"
            s = max(s, p_start)
            e = min(e, p_end)
            cards.append({"para": para["id"], "text": digits_to_cn(cl),
                          "start_s": round(s, 3), "end_s": round(e, 3)})
        cursor = idx

    # 4. 短卡合并:<4字 或 <1.35s:先并后卡;段尾无处可并则回并前卡
    def too_short(c):
        return len(c["text"]) < 4 or (c["end_s"] - c["start_s"]) < 1.35

    merged = []
    i = 0
    while i < len(cards):
        c = cards[i]
        if too_short(c) and i + 1 < len(cards) and cards[i + 1]["para"] == c["para"]:
            nxt = cards[i + 1]
            cards[i + 1] = {**nxt,
                            "text": c["text"] + "，" + nxt["text"],
                            "start_s": c["start_s"]}
            i += 1
            continue
        merged.append(c)
        i += 1
    j = 1
    while j < len(merged):
        if too_short(merged[j]) and merged[j]["para"] == merged[j - 1]["para"]:
            prev, cur = merged[j - 1], merged[j]
            merged[j - 1] = {**prev, "text": prev["text"] + "，" + cur["text"],
                             "end_s": cur["end_s"]}
            del merged[j]
            continue
        j += 1

    # 5. 卡边界防重叠(不越过下卡开始前 0.04s)
    for a, b in zip(merged, merged[1:]):
        if a["end_s"] > b["start_s"] - 0.04:
            a["end_s"] = round(b["start_s"] - 0.04, 3)

    for k, c in enumerate(merged):
        c["dur"] = round(c["end_s"] - c["start_s"], 3)
        c["idx"] = k
    out = {"source_audio": str(INTRO_WAV), "asr_tokens": len(tokens),
           "aligner": "funasr seaco-paraformer char-level",
           "cards": merged}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    total = merged[-1]["end_s"] - merged[0]["start_s"]
    print(f"cards: {len(merged)}, span {merged[0]['start_s']:.2f}-{merged[-1]['end_s']:.2f}s")
    for c in merged:
        print("  %2d  %5.2f-%5.2f (%4.1fs)  %s" % (c["idx"], c["start_s"], c["end_s"], c["dur"], c["text"]))
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
