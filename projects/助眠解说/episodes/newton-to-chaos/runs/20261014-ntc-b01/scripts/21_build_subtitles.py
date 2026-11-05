# -*- coding: utf-8 -*-
"""字幕生成 r1(manual-post-production.md:用户明确委托;subtitles.md style_r4)。

真源:显示文本=audio/utterances.json(锁定稿);时间=runs/.../timeline.json 的
204 个正文单元(sample 精确锚点) + 单元内 FunASR 字级时间戳(窗口化加偏移,
整段识别的 VAD 分段时间戳是段内相对时间,会塌缩——见 intro 踩坑)。

粒度:子句级(句界优先,逗号组合),单行宽度用真实字体测量 ≤1718px
(含描边 10px 后 ≤1728 安全区);行末标点去除;短卡(<1.35s 或 <4 字)并邻卡。
片头不加常规字幕(常显艺术字卡已承担)。

输出:runs/.../subtitles/r1/{cues.json, body.srt, body.ass}
运行环境:voxcpm venv(funasr/soundfile/PIL)。
"""
import json, re
from pathlib import Path
import numpy as np
import soundfile as sf
from funasr import AutoModel
from PIL import ImageFont

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\newton-to-chaos")
RUN = EP / "runs" / "20261014-ntc-b01"
TL = RUN / "timeline.json"
UTT = EP / "audio" / "utterances.json"
INTRO_TL = RUN / "intro_timeline.json"
BODY_WAV = RUN / "chapters" / "body_narration.wav"
FONT = Path(r"E:\program\1project\video\assets\助眠解说\subtitles\style-r4\fonts\SourceHanSansSC-Heavy.otf")
OUT = RUN / "subtitles" / "r1"
H = r"C:\Users\10060\.cache\modelscope\hub\iic"
ASR = H + r"\speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
VAD = H + r"\speech_fsmn_vad_zh-cn-16k-common-pytorch"
SR = 48000
SR_ASR = 16000          # FunASR paraformer 只吃 16k;直接喂 48k 会让时间轴错乱
WORK16K = RUN / "logs" / "body_16k.wav"
PAD = 0.30                 # 单元窗口前后余量
MAX_TEXT_PX = 1718         # 1728 安全区 - 10px 描边
MIN_DUR, TAIL_HOLD = 0.7, 0.3

# ---------- 字体测量 ----------
_font = ImageFont.truetype(str(FONT), 96)
def text_px(s):
    return _font.getlength(s)

def split_by_width(clause):
    """超宽子句在标点/空格处或字符间切分为多段,每段 ≤MAX_TEXT_PX。"""
    if text_px(clause) <= MAX_TEXT_PX:
        return [clause]
    parts, cur = [], ""
    for ch in clause:
        if text_px(cur + ch) > MAX_TEXT_PX and cur:
            parts.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        parts.append(cur)
    return parts

# ---------- ASR 窗口化对齐 ----------
def unit_tokens(model, x, u0, u1):
    t0 = max(0.0, u0 - PAD)
    t1 = min(len(x) / SR_ASR, u1 + PAD)
    res = model.generate(input=x[int(t0 * SR_ASR):int(t1 * SR_ASR)], batch_size_s=300)
    toks = []
    for r in res:
        t = r.get("text", "")
        ts = r.get("timestamp", []) or []
        ch = list(t.replace(" ", ""))
        n = min(len(ch), len(ts))
        for i in range(n):
            toks.append({"c": ch[i], "s": ts[i][0] / 1000 + t0, "e": ts[i][1] / 1000 + t0})
    return toks

def match_chars(locked, tokens):
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
    OUT.mkdir(parents=True, exist_ok=True)
    tl = json.loads(TL.read_text(encoding="utf-8"))
    utt = json.loads(UTT.read_text(encoding="utf-8"))
    intro_s = json.loads(INTRO_TL.read_text(encoding="utf-8"))["intro_seconds"]
    units = tl["utterances"]                      # 204,含 start_s/end_s(body 相对)
    text_by_id = {u["id"]: u["text"] for u in utt["utterances"]}

    x, sr = sf.read(str(BODY_WAV), always_2d=False)
    assert sr == SR
    if not WORK16K.exists():
        import subprocess
        subprocess.run([r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe",
                        "-y", "-i", str(BODY_WAV), "-ac", "1", "-ar", "16000",
                        str(WORK16K)], check=True, capture_output=True)
    x16, sr16 = sf.read(str(WORK16K), always_2d=False)
    assert sr16 == SR_ASR
    model = AutoModel(model=ASR, vad_model=VAD, device="cpu",
                      disable_update=True, log_level="ERROR")

    cues, warns = [], []
    for n, u in enumerate(units):
        uid, u0, u1 = u["id"], u["start_s"], u["end_s"]
        locked = text_by_id[uid]
        toks = unit_tokens(model, x16, u0, u1)
        ch_at = match_chars(list(locked), toks)
        span = max(1e-6, u1 - u0)
        # 子句切分(句末标点定界,显示时去行末标点)
        clauses = [(m.group(0), m.start()) for m in re.finditer(r"[^，。？！；]+[，。？！；]?", locked)]
        # 每子句:字符区间 → 实测起止;无匹配则按字符占比在单元内内插
        pieces = []
        n_locked = max(1, len(locked))
        for cl, off in clauses:
            disp = cl.strip("，。？！；：")
            if not disp:
                continue
            ts = [ch_at[i] for i in range(off, off + len(cl)) if i < len(ch_at) and ch_at[i]]
            if ts:
                s = min(t[0] for t in ts); e = max(t[1] for t in ts)
            else:
                warns.append(f"{uid}: no-match clause '{disp[:10]}'")
                s = u0 + span * (off / n_locked)
                e = u0 + span * ((off + len(cl)) / n_locked)
            s = max(s, u0); e = min(e, u1)
            if e <= s:
                e = min(u1, s + 0.3)
            pieces.append({"text": disp, "s": s, "e": e})
        # 超宽子句按字符均分(时间按字符比例在 [s,e] 内分,仅用于切段位置)
        expanded = []
        for p in pieces:
            segs = split_by_width(p["text"])
            if len(segs) == 1:
                expanded.append(p)
            else:
                total = sum(len(g) for g in segs)
                t = p["s"]; span = p["e"] - p["s"]
                acc = 0
                for g in segs:
                    acc += len(g)
                    expanded.append({"text": g, "s": t, "e": p["s"] + span * acc / total})
                    t = p["s"] + span * acc / total
        # 短卡合并(<4 字 或 <1.35s,并后卡;段尾回并前卡;合并结果不得超宽)
        def short(c):
            return len(c["text"]) < 4 or c["e"] - c["s"] < 1.35
        merged = []
        i = 0
        while i < len(expanded):
            c = expanded[i]
            if (i + 1 < len(expanded) and short(c)
                    and text_px(c["text"] + "，" + expanded[i + 1]["text"]) <= MAX_TEXT_PX):
                nxt = expanded[i + 1]
                expanded[i + 1] = {**nxt, "text": c["text"] + "，" + nxt["text"], "s": c["s"]}
                i += 1
                continue
            merged.append(c)
            i += 1
        j = 1
        while j < len(merged):
            if (short(merged[j])
                    and text_px(merged[j - 1]["text"] + "，" + merged[j]["text"]) <= MAX_TEXT_PX):
                prev, cur = merged[j - 1], merged[j]
                merged[j - 1] = {**prev, "text": prev["text"] + "，" + cur["text"], "e": cur["e"]}
                del merged[j]
                continue
            j += 1
        for c in merged:
            if c["e"] <= c["s"]:
                warns.append(f"{uid}: degenerate cue dropped '{c['text'][:10]}'")
                continue
            cues.append({"unit": uid, "text": c["text"],
                         "start_s": round(intro_s + c["s"], 3),
                         "end_s": round(intro_s + c["e"], 3)})
        if (n + 1) % 40 == 0:
            print(f"  units {n+1}/{len(units)}")

    # 全局边界:尾部停留 0.3s,不越过下一条开始前 0.04s;目标最短 0.7s
    for a, b in zip(cues, cues[1:]):
        want = a["end_s"] + TAIL_HOLD
        a["end_s"] = round(min(want, b["start_s"] - 0.04), 3)
        if a["end_s"] - a["start_s"] < MIN_DUR:
            a["end_s"] = round(min(a["start_s"] + MIN_DUR, b["start_s"] - 0.04), 3)
    cues[-1]["end_s"] = round(cues[-1]["end_s"] + TAIL_HOLD, 3)

    # ---- 输出 ----
    (OUT / "cues.json").write_text(json.dumps(
        {"style": "style_r4", "intro_seconds": intro_s, "cues": cues,
         "warns": warns, "source_audio": str(BODY_WAV)},
        ensure_ascii=False, indent=1), encoding="utf-8")

    def srt_t(t):
        h, m = int(t // 3600), int(t % 3600 // 60)
        s, ms = int(t % 60), int(round((t % 1) * 1000))
        if ms == 1000: s, ms = s + 1, 0
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    with (OUT / "body.srt").open("w", encoding="utf-8-sig") as f:
        for i, c in enumerate(cues, 1):
            f.write(f"{i}\n{srt_t(c['start_s'])} --> {srt_t(c['end_s'])}\n{c['text']}\n\n")

    def ass_t(t):
        h, m = int(t // 3600), int(t % 3600 // 60)
        s, cs = int(t % 60), int(round((t % 1) * 100))
        if cs == 100: s, cs = s + 1, 0
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

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

    durs = [c["end_s"] - c["start_s"] for c in cues]
    widths = [text_px(c["text"]) for c in cues]
    print(f"cues: {len(cues)}  span {cues[0]['start_s']:.1f}-{cues[-1]['end_s']:.1f}s")
    print(f"dur: min={min(durs):.2f} max={max(durs):.2f} mean={sum(durs)/len(durs):.2f}")
    print(f"width: max={max(widths):.0f}px (limit {MAX_TEXT_PX})  over={sum(1 for w in widths if w > MAX_TEXT_PX)}")
    print(f"warns: {len(warns)}")
    for w in warns[:8]:
        print("  ", w)
    print(f"-> {OUT}")

if __name__ == "__main__":
    main()
