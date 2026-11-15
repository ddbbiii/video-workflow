# -*- coding: utf-8 -*-
"""《废弃工单》V5 片头：3 句钩子 + 标题卡 + 红字「一口气看完」，12–16 s。

时间轴按 intro VO 实测重排；标题窗 = 标题口播 + 0.42 s（≤ 0.5 s 门限）。
钩子 Ma Shan Zheng 96 / 骨白；标题 香萃，按 85% 宽实测；红字 3/4 标题字号。
无 BGM、无冲击音效；标题起首 2 帧闪白 88%。
"""
import json
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

EP = Path(r"E:\program\1project\video\projects\悬疑\episodes\20261112-feigongdan")
V = EP / "intro" / "v1"
VO = EP / "audio" / "vo-processed" / "b2s95"
STILLS = EP / "image" / "stills-raw"
MOTION = V / "motion-bg"
FF = "ffmpeg"
FPS = 24
SR = 48000
W, H = 1920, 1080

HOOKS = [
    ("u0001", "本该作废的工单，又被派了出来。"),
    ("u0002", "上面没有报修人，只有一个老楼地址。"),
    ("u0003", "没人知道，那里面等着什么。"),
]
TITLE_TEXT = "《废弃工单》"
KICKER = "一口气看完"
TITLE_VO = "intro_title"

FONT_HOOK = Path(r"E:\program\1project\video\assets\助眠解说\intro\fonts\MaShanZheng-Regular.ttf")
FONT_XC = Path(r"E:\program\1project\video\assets\悬疑\intro\fonts\xiangcui.ttf")

# 片头图不复用正文第一镜：箱体 / 箱扣 / 404 门 / 熄灯走廊 / 湿痕
SHOTS = [
    ("hook1a_box", STILLS / "S05.png", [0.02, 0.02, 0.96, 0.96], [0.07, 0.06, 0.86, 0.86]),
    ("hook1b_latch", STILLS / "S06.png", [0.0, 0.0, 1.0, 1.0], [0.08, 0.06, 0.84, 0.84]),
    ("hook2_door", STILLS / "S38.png", [0.03, 0.02, 0.94, 0.94], [0.09, 0.06, 0.82, 0.82]),
    ("hook3_dark", STILLS / "S22.png", [0.0, 0.0, 1.0, 1.0], [0.06, 0.05, 0.88, 0.88]),
    ("title_trail", STILLS / "S34.png", [0.04, 0.02, 0.92, 0.92], [0.10, 0.07, 0.80, 0.80]),
]


def run(cmd, cwd=None):
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode:
        print("FAIL", " ".join(str(c) for c in cmd)[:600])
        print((r.stdout or "")[-1500:], (r.stderr or "")[-2500:])
        raise SystemExit(1)
    return r


def wav_dur(p):
    with wave.open(str(p), "rb") as w:
        return w.getnframes() / w.getframerate()


def read_wav(p):
    with wave.open(str(p), "rb") as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    y = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        y = y.reshape(-1, ch).mean(axis=1)
    if sr != SR:
        raise SystemExit(f"{p} sr={sr}")
    return y


def ass_time(t):
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def measure(font_path, text, size):
    f = ImageFont.truetype(str(font_path), size)
    d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    b = d.textbbox((0, 0), text, font=f)
    return b[2] - b[0]


def main():
    missing = [k for k in ("u0001", "u0002", "u0003", "intro_title") if not (VO / f"{k}.wav").exists()]
    if missing:
        raise SystemExit(f"missing VO: {missing}")
    missing_img = [s[0] for s in SHOTS if not s[1].exists()]
    if missing_img:
        raise SystemExit(f"missing stills: {missing_img}")

    V.mkdir(parents=True, exist_ok=True)
    (V / "fonts").mkdir(exist_ok=True)
    for f in (FONT_HOOK, FONT_XC):
        shutil.copy2(f, V / "fonts" / f.name)

    d = {k: wav_dur(VO / f"{k}.wav") for k in ("u0001", "u0002", "u0003", "intro_title")}
    t = [0.35]
    for i in range(2):
        t.append(t[-1] + d[HOOKS[i][0]] + (0.50 if i == 0 else 0.45))
    t_title = t[2] + d["u0003"] + 0.50
    total = t_title + d["intro_title"] + 0.32
    frames = int(round(total * FPS))
    total = frames / FPS
    if not (12.0 <= total <= 16.0):
        print(f"[warn] total {total:.2f}s 超出 12–16 s")

    # 镜序与帧界：前两钩共用 2 张，钩 3 与标题各 1 张；切换点按 VO 边界
    f_t = [int(round(x * FPS)) for x in t] + [int(round(t_title * FPS))]
    bounds = [0, f_t[0], f_t[1], f_t[2], f_t[3], frames]
    plan = {"schema_version": 1, "backend": "affine",
            "output": {"width": W, "height": H, "fps": FPS},
            "overview": False, "transition_s": 0, "shots": []}
    for i, (sid, src, sv, ev) in enumerate(SHOTS):
        f0, f1 = bounds[i], bounds[i + 1]
        if f1 <= f0:
            f1 = f0 + 2
        plan["shots"].append({
            "id": sid, "source": str(src), "duration_s": (f1 - f0) / FPS,
            "start_view": sv, "end_view": ev,
            "curve": {"type": "ramped_linear", "ramp_s": min(0.8, (f1 - f0) / FPS * 0.25)},
        })
    (V / "motion_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.rmtree(MOTION, ignore_errors=True)
    run([sys.executable, r"E:\program\1project\video\shared\camera-motion\camera_motion.py",
         V / "motion_plan.json", "--out", MOTION])

    lines = [f"file '{(MOTION / (s[0] + '.mp4')).as_posix()}'" for s in SHOTS]
    (V / "concat.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", V / "concat.txt",
         "-c", "copy", V / "bg.mp4"])

    hook_w = max(measure(FONT_HOOK, tx, 100) for _, tx in HOOKS)
    HOOK_SIZE = min(96, int(1728 * 100 / hook_w))
    title_L = measure(FONT_XC, TITLE_TEXT, 100)
    TITLE_SIZE = min(300, int(1632 * 100 / title_L))
    KICK_SIZE = int(round(TITLE_SIZE * 0.75))
    title_w = measure(FONT_XC, TITLE_TEXT, TITLE_SIZE)
    kick_w = measure(FONT_XC, KICKER, KICK_SIZE)

    HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,Ma Shan Zheng,{hs},&H00D7E3E9,&H00D7E3E9,&H00100C0A,&H80000000,0,0,0,0,100,100,4,0,1,4,2,5,0,0,0,1
Style: Kicker,XIANGCUIJIXUESONG,{ks},&H00241ACC,&H00241ACC,&H00100808,&H90000000,0,0,0,0,100,100,8,0,1,3,2,7,0,0,0,1
Style: Halo,XIANGCUIJIXUESONG,{ts},&H00000000,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
Style: Title,XIANGCUIJIXUESONG,{ts},&H00E6EFF2,&H00E6EFF2,&H000B0F12,&H00000000,0,0,0,0,100,100,2,0,1,3,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""".format(hs=HOOK_SIZE, ks=KICK_SIZE, ts=TITLE_SIZE)

    body = []
    for i, (key, text) in enumerate(HOOKS):
        st = t[i]
        en = min(t[i] + d[key] + 0.30, (t[i + 1] if i < 2 else t_title) - 0.05)
        body.append(f"Dialogue: 0,{ass_time(st)},{ass_time(en)},Hook,,0,0,0,,{{\\an5\\pos(960,520)\\fad(140,120)}}{text}")
    body.append(f"Dialogue: 0,{ass_time(t_title + 0.25)},{ass_time(total)},Kicker,,0,0,0,,{{\\an7\\pos(150,42)\\fad(200,0)}}{KICKER}")
    th = r"{\an5\pos(960,470)\blur12\alpha&H90&\fad(20,0)\fscx108\fscy108\t(0,120,\fscx100\fscy100)}"
    tt = r"{\an5\pos(960,470)\fad(20,0)\fscx108\fscy108\t(0,120,\fscx100\fscy100)}"
    body.append(f"Dialogue: 0,{ass_time(t_title)},{ass_time(total)},Halo,,0,0,0,,{th}{TITLE_TEXT}")
    body.append(f"Dialogue: 1,{ass_time(t_title)},{ass_time(total)},Title,,0,0,0,,{tt}{TITLE_TEXT}")
    (V / "intro.ass").write_text(HEAD + "\n".join(body) + "\n", encoding="utf-8")

    # 2 帧闪白：drawbox t=fill，整幅；0.084 s 后消失
    flash_end = t_title + 2.0 / FPS
    vf = (f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.88:t=fill:enable='between(t,{t_title:.4f},{flash_end:.4f})',"
          f"ass=intro.ass:fontsdir=fonts")
    run([FF, "-y", "-loglevel", "error", "-i", V / "bg.mp4", "-vf", vf,
         "-r", str(FPS), "-frames:v", str(frames), "-c:v", "libx264", "-preset", "medium",
         "-crf", "18", "-pix_fmt", "yuv420p", "-an", V / "text.mp4"], cwd=V)

    N = int(round(total * SR))
    mix = np.zeros(N, dtype=np.float32)
    for key, at in (("u0001", t[0]), ("u0002", t[1]), ("u0003", t[2]), ("intro_title", t_title)):
        y = read_wav(VO / f"{key}.wav")
        i = int(round(at * SR))
        j = min(N, i + len(y))
        mix[i:j] += (y[: j - i] * 0.95).astype(np.float32)
    peak = float(np.max(np.abs(mix)))
    if peak > 0.89:
        mix *= 0.89 / peak
    with wave.open(str(V / "mix.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())

    out = EP / "intro" / "废弃工单_片头_v1.mp4"
    run([FF, "-y", "-loglevel", "error", "-i", V / "text.mp4", "-i", V / "mix.wav",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out])

    meta = {"version": "v1", "fps": FPS, "frames": frames, "total": round(total, 3),
            "hooks": [{"key": k, "text": tx, "start": round(t[i], 4), "vo": round(d[k], 4)}
                      for i, (k, tx) in enumerate(HOOKS)],
            "title": {"text": TITLE_TEXT, "start": round(t_title, 4), "size": TITLE_SIZE,
                      "width_px": title_w, "width_pct": round(title_w / W * 100, 1),
                      "vo": round(d["intro_title"], 4), "tail": round(total - t_title - d["intro_title"], 4)},
            "kicker": {"text": KICKER, "size": KICK_SIZE, "width_px": kick_w},
            "hook_size": HOOK_SIZE, "flash_frames": 2, "bgm": None}
    (V / "timeline.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print("DONE", out)
    print("total", round(total, 3), "title_at", round(t_title, 3), "title_size", TITLE_SIZE,
          "pct", round(title_w / W * 100, 1))


if __name__ == "__main__":
    main()




