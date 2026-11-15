# -*- coding: utf-8 -*-
"""Build 《脱水超重》 intro v2 (new 3-line hook copy, 15.17 s, 364 frames @ 24 fps)."""
import json
import math
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

EP = Path(r"E:\program\1project\video\projects\悬疑\episodes\20261112-tuoshui")
V = EP / "intro" / "v3"
PL = EP / "intro" / "v2" / "plates"
VO = EP / "audio" / "vo-processed-v2" / "b2s95"
MOTION = V / "motion-bg"
FF = "ffmpeg"
FPS = 24
SR = 48000
W, H = 1920, 1080

T = [8 / 24, 92 / 24, 199 / 24, 289 / 24]          # 0.333, 3.833, 8.292, 12.042
DUR = [3.020, 3.980, 3.260, 2.700]
TOTAL_FRAMES = 361
TOTAL = TOTAL_FRAMES / FPS

HOOKS = [
    ("hook1", "洗衣机的读数，从来不是筒里的重量。"),
    ("hook2", "排水管连通暗处，有东西在和他调成一样重。"),
    ("hook3", "空筒上跳动的数字，是另一个他的重量。"),
]
TITLE_TEXT = "《脱水超重》"
KICKER = "一口气看完"
TITLE_VO = "脱水超重，一口气看完。"

FONT_HOOK = Path(r"E:\program\1project\video\assets\助眠解说\intro\fonts\MaShanZheng-Regular.ttf")
FONT_XC = Path(r"E:\program\1project\video\assets\悬疑\intro\fonts\xiangcui.ttf")

SHOTS = [
    # id, source, start_frame, end_frame, start_view, end_view
    ("hook1_machine", EP / "image" / "final-v2" / "bg_machine2.png", 0, 36,
     [0.02, 0.02, 0.96, 0.96], [0.06, 0.05, 0.88, 0.88]),
    ("hook1_phone", PL / "shot1_phone.png", 36, 92,
     [0.0, 0.0, 1.0, 1.0], [0.035, 0.02, 0.93, 0.93]),
    ("hook2_pipe", EP / "image" / "final-v2" / "bg_pipe2.png", 92, 199,
     [0.0, 0.0, 1.0, 1.0], [0.08, 0.05, 0.84, 0.84]),
    ("hook3_pair", PL / "shot3_pair.png", 199, 289,
     [0.0, 0.0, 1.0, 1.0], [0.025, 0.015, 0.95, 0.95]),
    ("title", EP / "image" / "final-v2" / "bg_gap2.png", 289, 361,
     [0.04, 0.02, 0.92, 0.92], [0.10, 0.07, 0.80, 0.80]),
]


def run(cmd, cwd=None):
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        print("FAIL", " ".join(str(c) for c in cmd)[:600])
        print((r.stdout or "")[-1500:], (r.stderr or "")[-2500:])
        raise SystemExit(1)
    return r


def read_wav(p):
    with wave.open(str(p), "rb") as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    y = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        y = y.reshape(-1, ch).mean(axis=1)
    assert sr == SR, f"{p} sr={sr}"
    return y


def write_stereo(path, L, R):
    n = max(len(L), len(R))
    buf = np.zeros((n, 2), dtype=np.float32)
    buf[: len(L), 0] = L
    buf[: len(R), 1] = R
    peak = float(np.max(np.abs(buf)))
    if peak > 0.98:
        buf *= 0.98 / peak
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(buf, -1, 1) * 32767).astype("<i2").tobytes())


def place(dst, src, at, gain):
    i = int(round(at * SR))
    j = min(len(dst), i + len(src))
    if j > i:
        dst[i:j] += (src[: j - i] * gain).astype(np.float32)


def rms_db(x):
    return float(20 * np.log10(np.sqrt(np.mean(np.asarray(x, dtype=np.float64) ** 2)) + 1e-9))


def bandpass(x, lo, hi, sr=SR, soft=120.0):
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / sr)
    spec = np.fft.rfft(x)
    mask = 1 / (1 + np.exp(-(f - lo) / soft)) * 1 / (1 + np.exp((f - hi) / soft))
    return np.fft.irfft(spec * mask, n).astype(np.float32)


def synth_hum(seconds=12.0, seed=3):
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * SR)) / SR
    def ch(f0, phase):
        base = (0.62 * np.sin(2 * np.pi * f0 * t + phase)
                + 0.26 * np.sin(2 * np.pi * 2 * f0 * t + phase * 1.7)
                + 0.10 * np.sin(2 * np.pi * 3 * f0 * t + phase * 0.4) + 0.06 * np.sin(2 * np.pi * 4 * f0 * t + phase * 0.9))
        am = 1 + 0.07 * np.sin(2 * np.pi * 0.17 * t) + 0.025 * np.sin(2 * np.pi * 0.53 * t + 1.0)
        noise = bandpass(rng.normal(0, 1, len(t)).astype(np.float32), 30, 220, soft=30) * 0.22
        return (base * am + noise).astype(np.float32)
    L, R = ch(49.0, 0.0), ch(49.2, 2.1)
    for y in (L, R):
        g = 10 ** (-37.0 / 20) / (np.sqrt(np.mean(y.astype(np.float64) ** 2)) + 1e-12)
        y *= g
    # fade in / hard stop at 12.0
    f = int(0.45 * SR)
    L[:f] *= np.linspace(0, 1, f) ** 1.5
    R[:f] *= np.linspace(0, 1, f) ** 1.5
    return L, R


def synth_creak(seed=9):
    rng = np.random.default_rng(seed)
    dur = 0.55
    t = np.arange(int(dur * SR)) / SR
    n = len(t)
    # stick-slip envelope: three uneven micro-bursts
    env = np.zeros(n, dtype=np.float32)
    for at, w, a in ((0.03, 0.10, 0.9), (0.16, 0.07, 0.55), (0.28, 0.13, 1.0)):
        env += a * np.exp(-((t - at) ** 2) / (2 * w * w))
    noise = bandpass(rng.normal(0, 1, n).astype(np.float32), 380, 2100, soft=90)
    # resonant sweep 700 -> 460 Hz
    phase = 2 * np.pi * np.cumsum(700 - 240 * (t / dur)) / SR
    tone = 0.35 * np.sin(phase) + 0.15 * np.sin(2 * phase)
    y = (noise * 0.8 + tone) * env
    y *= 10 ** (-31.0 / 20) / (np.sqrt(np.mean(y.astype(np.float64) ** 2)) + 1e-12)
    return y.astype(np.float32)


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


# ---------------------------------------------------------------- 1. motion plan
V.mkdir(parents=True, exist_ok=True)
(V / "fonts").mkdir(exist_ok=True)
for f in (FONT_HOOK, FONT_XC):
    shutil.copy2(f, V / "fonts" / f.name)

plan = {"schema_version": 1, "backend": "affine", "output": {"width": W, "height": H, "fps": FPS},
        "overview": False, "transition_s": 0, "shots": []}
for sid, src, f0, f1, sv, ev in SHOTS:
    plan["shots"].append({
        "id": sid, "source": str(src), "duration_s": (f1 - f0) / FPS,
        "start_view": sv, "end_view": ev,
        "curve": {"type": "ramped_linear", "ramp_s": min(0.8, ((f1 - f0) / FPS) * 0.25)},
    })
(V / "motion_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
shutil.rmtree(MOTION, ignore_errors=True)
run(["python", r"E:\program\1project\video\shared\camera-motion\camera_motion.py", V / "motion_plan.json", "--out", MOTION])

# ---------------------------------------------------------------- 2. concat
lines = [f"file '{(MOTION / (s[0] + '.mp4')).as_posix()}'" for s in SHOTS]
(V / "concat.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", V / "concat.txt", "-c", "copy", V / "bg.mp4"])

# subtitle scrim: transparent above 66% height, up to 72% black at the bottom
yy = np.arange(H, dtype=np.float32) / H
alpha = np.clip((yy - 0.66) / 0.34, 0, 1) ** 1.3 * 0.72
scrim = np.zeros((H, W, 4), dtype=np.uint8)
scrim[:, :, 3] = (alpha[:, None] * 255).astype(np.uint8)
Image.fromarray(scrim, "RGBA").save(V / "scrim.png")

# ---------------------------------------------------------------- 3. ASS
hook_sizes = [measure(FONT_HOOK, t, 100) for _, t in HOOKS]
max_w = max(hook_sizes)
HOOK_SIZE = min(96, int(1728 * 100 / max_w))
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
    end = T[i] + DUR[i] + 0.10
    body.append(f"Dialogue: 0,{ass_time(T[i])},{ass_time(end)},Hook,,0,0,0,,{{\\an5\\pos(960,950)\\fad(140,120)}}{text}")
body.append(f"Dialogue: 0,{ass_time(T[3] + 0.25)},{ass_time(TOTAL)},Kicker,,0,0,0,,{{\\an7\\pos(150,42)\\fad(200,0)}}{KICKER}")
th = r"{\an5\pos(960,470)\blur12\alpha&H90&\fad(20,0)\fscx108\fscy108\t(0,120,\fscx100\fscy100)}"
tt = r"{\an5\pos(960,470)\fad(20,0)\fscx108\fscy108\t(0,120,\fscx100\fscy100)}"
body.append(f"Dialogue: 0,{ass_time(T[3])},{ass_time(TOTAL)},Halo,,0,0,0,,{th}{TITLE_TEXT}")
body.append(f"Dialogue: 1,{ass_time(T[3])},{ass_time(TOTAL)},Title,,0,0,0,,{tt}{TITLE_TEXT}")
(V / "intro.ass").write_text(HEAD + "\n".join(body) + "\n", encoding="utf-8")

# ---------------------------------------------------------------- 4. burn text
run([FF, "-y", "-loglevel", "error", "-i", V / "bg.mp4", "-loop", "1", "-framerate", "24", "-i", V / "scrim.png",
     "-filter_complex", "[0:v][1:v]overlay=0:0:enable='lt(t,12)',ass=intro.ass:fontsdir=fonts",
     "-r", str(FPS), "-frames:v", str(TOTAL_FRAMES), "-c:v", "libx264", "-preset", "medium",
     "-crf", "18", "-pix_fmt", "yuv420p", "-an", V / "text.mp4"], cwd=V)

# ---------------------------------------------------------------- 5. audio
N = int(round(TOTAL * SR))
L = np.zeros(N, dtype=np.float32)
R = np.zeros(N, dtype=np.float32)
for i, key in enumerate(("intro01", "intro02", "intro03", "intro_title")):
    y = read_wav(VO / f"{key}.wav")
    place(L, y, T[i], 0.95)
    place(R, y, T[i], 0.95)

humL, humR = synth_hum(12.0)
hum_end = int(12.0 * SR)
L[:hum_end] += humL[:hum_end]
R[:hum_end] += humR[:hum_end]
# 0.12 s cut so the hum dies right at the title frame
fade = int(0.12 * SR)
L[hum_end - fade:hum_end] *= np.linspace(1, 0, fade)
R[hum_end - fade:hum_end] *= np.linspace(1, 0, fade)

creak = synth_creak()
place(L, creak, 11.45, 1.0)
place(R, creak, 11.47, 1.0)

peak = float(np.max(np.abs(np.concatenate([L, R]))))
g = 0.89 / peak
L *= g
R *= g
write_stereo(V / "mix.wav", L, R)

# ---------------------------------------------------------------- 6. mux
out = EP / "intro" / "脱水超重_片头_v3.mp4"
run([FF, "-y", "-loglevel", "error", "-i", V / "text.mp4", "-i", V / "mix.wav",
     "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out])

meta = {
    "version": "v3",
    "copy": [t for _, t in HOOKS],
    "fps": FPS, "frames": TOTAL_FRAMES, "total": round(TOTAL, 3),
    "hooks": [{"key": k, "text": tx, "start": round(T[i], 4), "end": round(T[i] + DUR[i], 4), "vo": DUR[i]}
              for i, (k, tx) in enumerate(HOOKS)],
    "title": {"text": TITLE_TEXT, "start": round(T[3], 4), "end": round(TOTAL, 4), "size": TITLE_SIZE,
              "width_px": title_w, "width_pct": round(title_w / W * 100, 1)},
    "kicker": {"text": KICKER, "size": KICK_SIZE, "width_px": kick_w, "pos": [150, 42]},
    "hook_font_size": HOOK_SIZE,
    "audio": {"peak": 0.89, "rms_dbfs": round(rms_db(np.concatenate([L, R])), 2),
              "hum_rms_dbfs": -37.0, "creak_rms_dbfs": -31.0, "bgm": None,
              "hum_stop_s": 12.0, "creak_at_s": 11.45},
}
(V / "timeline.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
print("DONE", out)
print("hook_size", HOOK_SIZE, "title_size", TITLE_SIZE, "title_pct", round(title_w / W * 100, 1), "kick", KICK_SIZE)
print("total", TOTAL)


