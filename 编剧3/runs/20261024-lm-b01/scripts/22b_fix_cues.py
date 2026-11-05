# -*- coding: utf-8 -*-
"""修补 22 号字幕 cues:单元窗夹紧 + 单调排序 + 重叠清理 + 重烧(2026-10-22)。

根因:ASR 窗口 ±0.3s 外溢,个别单元(数字密集)字级匹配咬到相邻单元语音,
产生 start 晚于后继 start 的逆序 cue,尾持逻辑将其压成负时长。
"""
import hashlib, json, re, shutil, subprocess
from pathlib import Path

EP = Path(r"E:\program\1project\video\编剧3")
RUN = EP / "runs" / "20261024-lm-b01"
OUT = RUN / "subtitles" / "r1"
TL = RUN / "timeline.json"
INTRO_S = json.loads((RUN / "intro_timeline.json").read_text(encoding="utf-8"))["intro_seconds"]
FONT = Path(r"E:\program\1project\video\assets\助眠解说\subtitles\style-r4\fonts\SourceHanSansSC-Heavy.otf")
CLEAN = EP / "video" / "final" / "life-manual_with_narration.mp4"
SUB_OUT = EP / "video" / "final" / "life-manual_sub.mp4"
FF = r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"
MIN_DUR, TAIL_HOLD = 0.7, 0.3

doc = json.loads((OUT / "cues.json").read_text(encoding="utf-8"))
tl = json.loads(TL.read_text(encoding="utf-8"))
win = {u["id"]: (INTRO_S + u["start_s"] - 0.05, INTRO_S + u["end_s"] + 0.40)
       for u in tl["utterances"]}

cues = doc["cues"]
fixed = 0
for c in cues:
    lo, hi = win.get(c["unit"], (0, 1e9))
    s, e = c["start_s"], c["end_s"]
    c["start_s"] = round(min(max(s, lo), hi), 3)
    c["end_s"] = round(min(max(e, c["start_s"] + 0.3, lo), hi), 3)
    if abs(c["start_s"] - s) > 0.01 or abs(c["end_s"] - e) > 0.01:
        fixed += 1

cues.sort(key=lambda c: (c["start_s"], c["end_s"]))
# 重叠清理 + 最短时长(保序,不前推 start)
clean = []
for c in cues:
    if clean:
        prev = clean[-1]
        nxt_end_bound = c["start_s"] - 0.04
        prev["end_s"] = round(min(prev["end_s"], nxt_end_bound), 3)
        if prev["end_s"] - prev["start_s"] < MIN_DUR:
            prev["end_s"] = round(min(prev["start_s"] + MIN_DUR, nxt_end_bound), 3)
    clean.append(c)
cues = [c for c in clean if c["end_s"] > c["start_s"] + 0.05]
cues[-1]["end_s"] = round(cues[-1]["end_s"] + TAIL_HOLD, 3)

durs = [c["end_s"] - c["start_s"] for c in cues]
neg = sum(1 for d in durs if d <= 0)
ovl = sum(1 for a, b in zip(cues, cues[1:]) if a["end_s"] > b["start_s"] + 1e-6)
print(f"cues={len(cues)} clamped={fixed} neg={neg} overlaps={ovl} "
      f"dur min={min(durs):.2f} max={max(durs):.2f}")

doc["cues"] = cues
doc["fix_note"] = "22b: unit-window clamp + sort + overlap cleanup after ASR bleed"
(OUT / "cues.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

def srt_t(t):
    h, m = int(t // 3600), int(t % 3600 // 60)
    s, ms = int(t % 60), int(round((t % 1) * 1000))
    if ms == 1000: s, ms = s + 1, 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03f}" if False else f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

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

# 重烧
burn = OUT / "burn"
(burn / "fonts").mkdir(parents=True, exist_ok=True)
shutil.copy(OUT / "body.ass", burn / "subs.ass")
shutil.copy(FONT, burn / "fonts" / FONT.name)
r = subprocess.run([FF, "-y", "-i", str(CLEAN),
                    "-vf", "subtitles=subs.ass:fontsdir=fonts",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                    "-pix_fmt", "yuv420p", "-c:a", "copy",
                    "-movflags", "+faststart", str(SUB_OUT)],
                   capture_output=True, text=True, cwd=str(burn))
if r.returncode != 0:
    raise RuntimeError("burn failed: " + (r.stderr or "")[-800:])
print(f"reburn OK -> {SUB_OUT}")

def amd5(video, tmp):
    subprocess.run([FF, "-y", "-i", str(video), "-map", "0:a:0",
                    "-c:a", "copy", "-f", "adts", str(tmp)], capture_output=True)
    return hashlib.md5(tmp.read_bytes()).hexdigest()
t = burn / "_a.aac"
h1, h2 = amd5(CLEAN, t), amd5(SUB_OUT, t)
t.unlink()
print("audio md5 same:", h1 == h2)
