# -*- coding: utf-8 -*-
"""Build the glacier-style E intro: 2 hook lines + title + transition narration, 4 bgs."""
import json, subprocess, wave, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from subsplit import timed_cues

RUN = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws\runs\20261106-ulw-b01")
EP = RUN.parents[1]
INTRO = RUN / "intro"
INTRO.mkdir(exist_ok=True)
SR = 48000
VO = EP / "audio" / "vo-processed" / "b2cosy3-s90"
D = json.loads((RUN / "durations.json").read_text(encoding="utf-8"))
CM = Path(r"E:\program\1project\video\shared\camera-motion\camera_motion.py")

IDS = ["intro-p01-u01", "intro-p01-u02", "intro-p02-u01", "intro-p02-u02",
       "intro-p03-u01", "intro-trans"]
d = [D[i] for i in IDS]

# timeline
head = 0.30
g1 = 0.45
title_pause = 2.90
gq = 0.35
gt = 0.45
tail = 0.30
t = {}
t["h1"] = head
t["h2"] = t["h1"] + d[0] + g1
t["title"] = t["h2"] + d[1] + 0.35
t["q1"] = t["title"] + title_pause
t["q2"] = t["q1"] + d[2] + gq
t["q3"] = t["q2"] + d[3] + gq
t["tr"] = t["q3"] + d[4] + gt
total = t["tr"] + d[5] + tail

# audio
with wave.open(str(INTRO / "intro.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(np.zeros(int(head * SR), dtype=np.int16).tobytes())
    pos = head
    for i, sid in enumerate(IDS):
        start = t[["h1", "h2", "q1", "q2", "q3", "tr"][i]]
        gap = start - pos
        if gap > 0:
            w.writeframes(np.zeros(int(gap * SR), dtype=np.int16).tobytes())
        with wave.open(str(VO / (sid + ".wav")), "rb") as r:
            w.writeframes(r.readframes(r.getnframes()))
        pos = start + d[i]
    w.writeframes(np.zeros(int((total - pos) * SR), dtype=np.int16).tobytes())

# bg boundaries: 8 equal segments, 4 images cycling
raw_b = [round(total * i / 8, 3) for i in range(9)]
raw_b = sorted(set(x for x in raw_b if x < total)) + [round(total, 3)]
nf = [round(x * 30) for x in raw_b]
shots = []
for i in range(len(nf) - 1):
    dur = (nf[i + 1] - nf[i]) / 30.0
    shots.append({"id": "ib%d" % i, "source": str(INTRO / ("bg%d.png" % (i % 4 + 1))),
                  "duration_s": dur,
                  "start_view": [0.0, 0.0, 1.0, 1.0],
                  "end_view": [0.0238, 0.0238, 0.9524, 0.9524],
                  "curve": {"type": "ramped_linear", "ramp_s": 0.4}})
plan = {"schema_version": 1, "backend": "affine",
        "output": {"width": 1920, "height": 1080, "fps": 30},
        "transition_s": 0, "overview": "intro", "shots": shots}
(RUN / "intro_motion_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
subprocess.run(["python", str(CM), str(RUN / "intro_motion_plan.json"),
                "--out", str(INTRO / "bg_out"), "--resume"], check=True)

# concat bg segments
lst = INTRO / "bg_list.txt"
lst.write_text("\n".join("file '%s'" % (INTRO / "bg_out" / (s["id"] + ".mp4")).as_posix() for s in shots),
               encoding="utf-8")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                "-i", str(lst), "-c", "copy", str(INTRO / "intro_bg.mp4")], check=True)

# ASS
def ts(x):
    h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
    return "%d:%02d:%05.2f" % (h, m, s)

hook_anim = (r"{\an5\pos(960,520)\fad(300,400)\fscx96\fscy96"
             r"\t(0,350,\fscx100\fscy100)\t(350,2050,\fscx110\fscy110)}")
head_ass = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,Ma Shan Zheng,118,&H00F1E9E0,&H00F1E9E0,&H000A1018,&H00000000,0,0,0,0,100,100,0,0,1,6,0,5,0,0,0,1
Style: Title,Ma Shan Zheng,160,&H00F1E9E0,&H00F1E9E0,&H000A1018,&H00000000,0,0,0,0,100,100,0,0,1,7,0,5,0,0,0,1
Style: body,SourceHanSansSC,54,&H00E8F0F5,&H00E8F0F5,&H0012100C,&H00000000,0,0,0,0,100,100,0,0,1,3,0,2,120,120,72,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
lines = [
    "Dialogue: 0,%s,%s,Hook,,0,0,0,,%s我们总说，发现了一条规律。" % (ts(t["h1"]), ts(t["h1"] + d[0] + 0.30), hook_anim),
    "Dialogue: 0,%s,%s,Hook,,0,0,0,,%s很少有人说，证明了它。" % (ts(t["h2"]), ts(t["h2"] + d[1] + 0.45), hook_anim),
    "Dialogue: 0,%s,%s,Title,,0,0,0,,{\\an5\\pos(960,520)\\fad(300,300)}物理定律，真的靠谱吗" % (ts(t["title"]), ts(t["title"] + title_pause - 0.10)),
]
qtext = {
    "q1": "一条规律可以被检验一万次。",
    "q2": "第一万零一次，它仍然可能失效。",
    "q3": "那么，一条无法被证明的规律，真的存在吗？",
    "tr": "我们从比萨斜塔上的两个球开始，一直走到物理学家不得不承认：我们只能发现规律，不能证明规律。",
}
for key, idx in (("q1", 2), ("q2", 3), ("q3", 4), ("tr", 5)):
    for s, e, txt in timed_cues(t[key], d[idx], qtext[key], maxlen=18, max_lines=1):
        lines.append("Dialogue: 0,%s,%s,body,,0,0,0,,%s" % (ts(s), ts(e), txt))
(INTRO / "intro.ass").write_text(head_ass + "\n".join(lines) + "\n", encoding="utf-8")

# compose
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(INTRO / "intro_bg.mp4"),
                "-i", str(INTRO / "intro.wav"), "-vf", "ass=intro.ass:fontsdir=fonts",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-shortest",
                str(INTRO / "intro.mp4")], cwd=str(INTRO), check=True)
print("intro total", round(total, 2), "bg segments", len(shots))
