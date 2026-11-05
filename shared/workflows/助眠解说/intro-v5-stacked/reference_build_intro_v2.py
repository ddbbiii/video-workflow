# -*- coding: utf-8 -*-
"""片头 v5（参考实现）：三句堆叠手写体（BaoCanMou HuiTing），配音版。

逻辑（2026-11-04 用户定稿）：
  1) 第一句缓缓淡入；
  2) 第二句出现，第一句保留并上移；
  3) 第三句出现，前两句一起上移；
  4) 整体淡出。
字号 144，字距 8，描边 5；三行最终 324/540/756。
配音沿用 b2-warm-male light-expression（seed 7 / atempo 0.774224）。

【单集移植：只改下面 7 行 CONFIG】
  EP      单集根目录
  RUN     runs/<run-id>
  RAW     三条原始 TTS wav 目录（文件名 intro2-l1/l2/l3.wav）
  PROC    trim+atempo 后的 wav 目录
  OUTD    本批片头产物目录
  BG      背景运镜 mp4（正文已验收）
  FONT    共享字体（assets/助眠解说/intro/fonts/...）
三句文案在 LINES；时序偏移在 render() 里的 SHIFT（默认 1.0s）。
"""
from __future__ import annotations
import json
import subprocess
import wave
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

EP = Path(r"E:\program\1project\video\4")
RUN = EP / "runs" / "20261103-gla-b01"
RAW = EP / "audio" / "vo-raw-v2" / "lightexpr-seed7"
PROC = EP / "audio" / "vo-processed-v2" / "lightexpr-seed7"
OUTD = RUN / "intro_v2"
BG = RUN / "media" / "affine" / "c1-s13.mp4"
FONT_PATH = Path(r"E:\program\1project\video\assets\助眠解说\intro\fonts\BaoCanMouHuiTing-Regular.ttf")
FFMPEG = r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"

ATEMPO = 0.774224
HEAD, GAP1, GAP2, TAIL = 0.60, 0.55, 0.60, 1.60
SR = 48000
TRIM_RMS_DB, TRIM_FRAME_MS, KEEP_HEAD, KEEP_TAIL = -45.0, 20, 0.10, 0.15

W, H, FPS = 1920, 1080, 30
FS, TRACKING, STROKE_R = 144, 8, 5
WARM, DARK = (246, 241, 233, 255), (10, 16, 24, 235)
LINES = ["在地球最寒冷的地方", "有一条流淌了几千年的河", "它的河水，是冰。"]
IDS = ["intro2-l1", "intro2-l2", "intro2-l3"]
FINAL_Y = [324, 540, 756]
STATE2_Y = [432, 648]


def read_wav16(p):
    with wave.open(str(p), "rb") as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        raw = w.readframes(n)
    y = np.frombuffer(raw, dtype="<i2")
    if ch > 1:
        y = y.reshape(-1, ch).mean(axis=1).astype(np.int16)
    return y, sr


def write_wav16(p, y, sr=SR):
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(np.asarray(y, dtype="<i2").tobytes())


def trim(y, sr):
    if y.ndim > 1:
        y = y.mean(axis=1)
    frame = max(1, int(sr * TRIM_FRAME_MS / 1000))
    thr = 10 ** (TRIM_RMS_DB / 20.0)
    n = len(y) // frame
    if n == 0:
        return y
    frames = y[: n * frame].reshape(n, frame)
    rms = np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1))
    act = np.where(rms > thr)[0]
    if len(act) == 0:
        return y
    a = max(0, int(act[0] * frame - KEEP_HEAD * sr))
    b = min(len(y), int((act[-1] + 1) * frame + KEEP_TAIL * sr))
    return y[a:b]


def process():
    PROC.mkdir(parents=True, exist_ok=True)
    for sid in IDS:
        src, dst = RAW / f"{sid}.wav", PROC / f"{sid}.wav"
        y, sr = read_wav16(src)
        y = trim(np.asarray(y), sr)
        tmp = PROC / f"{sid}.trim.wav"
        write_wav16(tmp, y, sr)
        r = subprocess.run([FFMPEG, "-y", "-i", str(tmp), "-filter:a", f"atempo={ATEMPO}",
                            "-acodec", "pcm_s16le", str(dst)], capture_output=True, text=True)
        tmp.unlink(missing_ok=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr[-500:])
        n_info = len(read_wav16(dst)[0])
        print(sid, round(n_info / SR, 3), "s")


def load16(p):
    y, sr = read_wav16(p)
    if y.dtype != np.int16:
        y = (np.clip(y, -1, 1) * 32767).astype(np.int16)
    return y


def build_audio():
    OUTD.mkdir(parents=True, exist_ok=True)
    pcm = [np.zeros(int(SR * HEAD), dtype=np.int16)]
    t = HEAD
    units = []
    for i, sid in enumerate(IDS):
        if i > 0:
            gap = GAP1 if i == 1 else GAP2
            pcm.append(np.zeros(int(SR * gap), dtype=np.int16))
            t += gap
        y = load16(PROC / f"{sid}.wav")
        s = t
        pcm.append(y)
        t += len(y) / SR
        units.append({"id": sid, "text": LINES[i], "start_s": round(s, 3),
                      "end_s": round(t, 3), "seconds": round(len(y) / SR, 3)})
    pcm.append(np.zeros(int(SR * TAIL), dtype=np.int16))
    t += TAIL
    full = np.concatenate(pcm)
    write_wav16(OUTD / "intro.wav", full)
    meta = {"intro_seconds": round(t, 3), "intro_samples": len(full), "sample_rate": SR,
            "head_s": HEAD, "tail_s": TAIL, "units": units,
            "voice": "b2-warm-male light-expression seed7 atempo 0.774224"}
    (OUTD / "intro_timeline.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                             encoding="utf-8")
    print("intro", round(t, 3), "s")
    return meta


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def interp(keys, t):
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            return v0 + (v1 - v0) * smooth((t - t0) / max(1e-6, t1 - t0))
    return keys[-1][1]


def alpha_in(t, t0, t1):
    if t <= t0:
        return 0.0
    if t >= t1:
        return 1.0
    return (t - t0) / (t1 - t0)


def make_layer(text):
    font = ImageFont.truetype(str(FONT_PATH), FS)
    widths = [font.getlength(ch) for ch in text]
    total = sum(widths) + TRACKING * (len(text) - 1)
    pad = STROKE_R + 14
    lw, lh = int(total) + pad * 2, FS + pad * 2
    img = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    baseline = lh / 2 + FS * 0.36
    for pass_i in (0, 1):
        x = pad
        for ch, w in zip(text, widths):
            if pass_i == 0:
                for dx in range(-STROKE_R, STROKE_R + 1):
                    for dy in range(-STROKE_R, STROKE_R + 1):
                        if dx * dx + dy * dy <= STROKE_R * STROKE_R:
                            d.text((x + dx, baseline + dy), ch, font=font, fill=DARK, anchor="ls")
            else:
                d.text((x, baseline), ch, font=font, fill=WARM, anchor="ls")
            x += w + TRACKING
    return img


def vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    return np.clip(1.0 - 0.30 * r ** 2, 0.58, 1.0)[..., None]


def render(meta):
    layers = {i: make_layer(t) for i, t in enumerate(LINES)}
    total = meta["intro_seconds"]
    n = round(total * FPS)
    u = meta["units"]
    s2, s3 = u[1]["start_s"], u[2]["start_s"]
    # 每句：语音前 0.45s 起淡入；上一句语音结束后进入换行/上移
    # 2026-11-04 用户反馈"字幕偏早"，所有文字关键帧整体后移 1.5s（音频不动）
    SHIFT = 1.5
    a1 = (u[0]["start_s"] - 0.55 + SHIFT, u[0]["start_s"] + 0.55 + SHIFT)
    a2 = (s2 - 0.45 + SHIFT, s2 + 0.55 + SHIFT)
    a3 = (s3 - 0.45 + SHIFT, s3 + 0.55 + SHIFT)
    mv1 = (s2 - 0.50 + SHIFT, s2 - 0.50 + 0.90 + SHIFT)   # l1 540 -> 432
    mv2 = (s3 - 0.50 + SHIFT, s3 - 0.50 + 0.90 + SHIFT)   # l1 432->324, l2 648->540
    fade_out = (total - 0.95, total - 0.05)

    def pos(i, t):
        if i == 0:
            y = interp([(0, 540), (mv1[0], 540), (mv1[1], 432),
                        (mv2[0], 432), (mv2[1], 324)], t)
            return y
        if i == 1:
            return interp([(0, STATE2_Y[1]), (mv2[0], STATE2_Y[1]), (mv2[1], 540)], t)
        return FINAL_Y[2]

    cap = cv2.VideoCapture(str(BG))
    frames = []
    while len(frames) < n:
        ok, fr = cap.read()
        if not ok:
            break
        frames.append(fr)
    cap.release()
    while len(frames) < n:
        frames.append(frames[-1].copy())
    print("bg frames", len(frames), "total", total)

    vig = vignette()
    for k in range(n):
        t = k / FPS
        fr = frames[k].astype(np.float32) * 0.86
        bg_fade = min(1.0, t / 0.6) * (1.0 if t < total - 0.9 else max(0.0, (total - t) / 0.9))
        fr = np.clip(fr * bg_fade * vig, 0, 255).astype(np.uint8)
        base = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)).convert("RGBA")
        for i in range(3):
            if i == 0:
                a = alpha_in(t, a1[0], a1[1])
            elif i == 1:
                a = alpha_in(t, a2[0], a2[1])
            else:
                a = alpha_in(t, a3[0], a3[1])
            if t > fade_out[0]:
                a *= max(0.0, 1.0 - (t - fade_out[0]) / (fade_out[1] - fade_out[0]))
            if a <= 0.002:
                continue
            arr = np.array(layers[i])
            arr[:, :, 3] = (arr[:, :, 3] * a).astype(np.uint8)
            layer = Image.fromarray(arr)
            x = (W - layer.width) // 2
            y = int(round(pos(i, t) - layer.height / 2))
            base.alpha_composite(layer, (x, y))
        out = cv2.cvtColor(np.array(base.convert("RGB")), cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(OUTD / "frames" / f"f{k:04d}.png"), out)

    cmd = [FFMPEG, "-y", "-framerate", str(FPS), "-i", str(OUTD / "frames" / "f%04d.png"),
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", str(OUTD / "clean-intro.mp4")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:])
    print("OK", OUTD / "clean-intro.mp4")


def main():
    (OUTD / "frames").mkdir(parents=True, exist_ok=True)
    process()
    meta = build_audio()
    render(meta)


if __name__ == "__main__":
    main()
