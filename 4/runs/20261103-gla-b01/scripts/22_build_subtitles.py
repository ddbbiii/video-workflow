# -*- coding: utf-8 -*-
"""字幕生成 r1(subtitles.md style_r4;收尾任务书 2026-10-20 明确委托)。

移植自 newton runs/20261014-ntc-b01/scripts/21_build_subtitles.py,适配点:
- 真源不变:显示文本=audio/utterances.json(锁定稿原字词);时间=runs/.../
  timeline.json 的 218 个正文单元(sample 精确锚点) + 单元内 FunASR 字级时间戳
  (16k 单声道 + 窗口化加偏移,整段识别的 VAD 分段时间戳会塌缩)。
- 绝对起点=片头实测时长(intro_timeline.json intro_seconds;字幕只覆盖正文,
  片头文字即艺术字卡,不叠字幕)。
- 烧录:video/final/glacier-river_sub.mp4(视频 veryfast crf19 重编码、
  -c:a copy);字幕目录作 cwd + 滤镜内相对路径(fontsdir=fonts,避 Windows
  盘符/中文转义坑);烧录后提取音轨哈希与 clean 母片核验。
- QA:锁定稿一致率(逐单元去标点比对)、无重叠、宽度实测 ≤1718px、
  无匹配内插告警清单(cues.json.warnds)。

输出:runs/.../subtitles/r1/{cues.json, body.srt, body.ass, burn/, glacier-river_sub.mp4}
运行环境:voxcpm venv(funasr/soundfile/PIL)。
"""
import hashlib, json, re, shutil, subprocess
from pathlib import Path
import numpy as np
import soundfile as sf
from funasr import AutoModel
from PIL import ImageFont

EP = Path(r"E:\program\1project\video\4")
RUN = EP / "runs" / "20261103-gla-b01"
TL = RUN / "timeline.json"
UTT = EP / "audio" / "utterances.json"
INTRO_TL = RUN / "intro_timeline.json"
BODY_WAV = RUN / "chapters" / "body_narration.wav"
CLEAN = EP / "video" / "final" / "glacier-river_with_narration.mp4"  # mariana clean 无音轨,烧录用带旁白版
SUB_OUT = EP / "video" / "final" / "glacier-river_sub.mp4"
FONT_ASSET = Path(r"E:\program\1project\video\assets\助眠解说\subtitles\style-r4\fonts\SourceHanSansSC-Heavy.otf")
OUT = RUN / "subtitles" / "r1"
H = r"C:\Users\10060\.cache\modelscope\hub\iic"
ASR = H + r"\speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
VAD = H + r"\speech_fsmn_vad_zh-cn-16k-common-pytorch"
FFMPEG = r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"
SR = 48000
SR_ASR = 16000          # FunASR paraformer 只吃 16k
WORK16K = RUN / "logs" / "body_16k.wav"
PAD = 0.30                 # 单元窗口前后余量
MAX_TEXT_PX = 1718         # 1728 安全区 - 10px 描边
MIN_DUR, TAIL_HOLD = 0.7, 0.3
BURN_CRF, BURN_PRESET = "19", "veryfast"   # 口径同 15_assemble 正文

# ---------- 字体测量 ----------
_font = ImageFont.truetype(str(FONT_ASSET), 96)
def text_px(s):
    return _font.getlength(s)

def split_by_width(clause):
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
        if ch in "，,。？！;；:：、 ":
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
    units = tl["utterances"]                      # 218,含 start_s/end_s(body 相对)
    text_by_id = {u["id"]: u["text"] for u in utt["utterances"]}

    x, sr = sf.read(str(BODY_WAV), always_2d=False)
    assert sr == SR
    if not WORK16K.exists():
        subprocess.run([FFMPEG, "-y", "-i", str(BODY_WAV), "-ac", "1", "-ar", "16000",
                        str(WORK16K)], check=True, capture_output=True)
    x16, sr16 = sf.read(str(WORK16K), always_2d=False)
    assert sr16 == SR_ASR
    model = AutoModel(model=ASR, vad_model=VAD, device="cpu",
                      disable_update=True, log_level="ERROR")

    cues, warns = [], []
    unit_cues = {}          # uid -> [cue texts](锁定稿一致率用)
    for n, u in enumerate(units):
        uid, u0, u1 = u["id"], u["start_s"], u["end_s"]
        locked = text_by_id[uid]
        toks = unit_tokens(model, x16, u0, u1)
        ch_at = match_chars(list(locked), toks)
        span = max(1e-6, u1 - u0)
        clauses = [(m.group(0), m.start()) for m in re.finditer(r"[^，,。？！;；]+[，,。？！;；]?", locked)]
        pieces = []
        n_locked = max(1, len(locked))
        for cl, off in clauses:
            disp = cl.strip("，,。？！;；:：")
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
        expanded = []
        for p in pieces:
            segs = split_by_width(p["text"])
            if len(segs) == 1:
                expanded.append(p)
            else:
                total = sum(len(g) for g in segs)
                t = p["s"]; cspan = p["e"] - p["s"]
                acc = 0
                for g in segs:
                    acc += len(g)
                    expanded.append({"text": g, "s": t, "e": p["s"] + cspan * acc / total})
                    t = p["s"] + cspan * acc / total
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
            unit_cues.setdefault(uid, []).append(c["text"])
        if (n + 1) % 40 == 0:
            print(f"  units {n+1}/{len(units)}")

    for a, b in zip(cues, cues[1:]):
        want = a["end_s"] + TAIL_HOLD
        a["end_s"] = round(min(want, b["start_s"] - 0.04), 3)
        if a["end_s"] - a["start_s"] < MIN_DUR:
            a["end_s"] = round(min(a["start_s"] + MIN_DUR, b["start_s"] - 0.04), 3)
    cues[-1]["end_s"] = round(cues[-1]["end_s"] + TAIL_HOLD, 3)

    # ---- QA:锁定稿一致率(逐单元,去标点/合并逗号后须逐字相等)----
    PUNCT = "，,。？！;；:：、— "
    consist_bad = []
    for u in units:
        locked = re.sub(f"[{re.escape(PUNCT)}]", "", text_by_id[u["id"]])
        shown = re.sub(f"[{re.escape(PUNCT)}]", "", "".join(unit_cues.get(u["id"], [])))
        if locked != shown:
            consist_bad.append(u["id"])
    n_units_ok = len(units) - len(consist_bad)
    # 无重叠 / 宽度
    overlaps = [(i, cues[i]["end_s"], cues[i + 1]["start_s"])
                for i in range(len(cues) - 1) if cues[i]["end_s"] > cues[i + 1]["start_s"] + 1e-6]
    widths = [text_px(c["text"]) for c in cues]
    width_over = sum(1 for w in widths if w > MAX_TEXT_PX)

    (OUT / "cues.json").write_text(json.dumps(
        {"style": "style_r4", "intro_seconds": intro_s, "cues": cues,
         "warns": warns, "source_audio": str(BODY_WAV),
         "qa": {"units_total": len(units), "units_consistent": n_units_ok,
                "consistency_bad": consist_bad, "overlaps": overlaps,
                "max_text_px": round(max(widths), 1), "limit_px": MAX_TEXT_PX,
                "width_over": width_over}},
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
    print(f"cues: {len(cues)}  span {cues[0]['start_s']:.1f}-{cues[-1]['end_s']:.1f}s (intro offset {intro_s:.3f}s)")
    print(f"dur: min={min(durs):.2f} max={max(durs):.2f} mean={sum(durs)/len(durs):.2f}")
    print(f"width: max={max(widths):.0f}px (limit {MAX_TEXT_PX})  over={width_over}")
    print(f"consistency: {n_units_ok}/{len(units)} units exact  bad={consist_bad[:5]}")
    print(f"overlaps: {len(overlaps)}  warns: {len(warns)}")
    for w in warns[:8]:
        print("  ", w)
    print(f"-> {OUT}")

    # ---- 烧录 ----
    burn = OUT / "burn"
    burn.mkdir(exist_ok=True)
    (burn / "fonts").mkdir(exist_ok=True)
    shutil.copy(OUT / "body.ass", burn / "subs.ass")
    shutil.copy(FONT_ASSET, burn / "fonts" / FONT_ASSET.name)
    r = subprocess.run([FFMPEG, "-y", "-i", str(CLEAN),
                        "-vf", "subtitles=subs.ass:fontsdir=fonts",
                        "-c:v", "libx264", "-preset", BURN_PRESET, "-crf", BURN_CRF,
                        "-pix_fmt", "yuv420p", "-c:a", "copy",
                        "-movflags", "+faststart", str(SUB_OUT)],
                       capture_output=True, text=True, cwd=str(burn))
    if r.returncode != 0:
        raise RuntimeError("burn failed: " + (r.stderr or "")[-800:])
    print(f"burn OK -> {SUB_OUT} ({SUB_OUT.stat().st_size // 1024 // 1024}MB)")

    # ---- 音轨哈希核验(sub vs clean,提取音轨后比较)----
    def audio_md5(video, tmp):
        subprocess.run([FFMPEG, "-y", "-i", str(video), "-map", "0:a:0",
                        "-c:a", "copy", "-f", "adts", str(tmp)],
                       capture_output=True, text=True)
        return hashlib.md5(tmp.read_bytes()).hexdigest()
    t1, t2 = burn / "_a1.aac", burn / "_a2.aac"
    h1, h2 = audio_md5(CLEAN, t1), audio_md5(SUB_OUT, t2)
    t1.unlink(); t2.unlink()
    same = h1 == h2
    print(f"audio track md5 clean={h1[:12]} sub={h2[:12]} same={same}")
    if not same:
        raise RuntimeError("烧录后音轨与 clean 不一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
