# -*- coding: utf-8 -*-
"""10 秒片头字幕节奏样片（新字体 BaoCanMou HuiTing）。

节奏（用户指定）：
  1) 第一句缓缓淡入；
  2) 第二句出现，第一句保留并向上移；
  3) 第三句出现，前两句向上移；
  4) 整体淡出。
背景用正文已验收的 c1-s01 运镜片段（同一批静帧），首尾轻微淡入淡出。
"""
from __future__ import annotations
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

EP = Path(r"E:\program\1project\video\4")
FONT_PATH = EP / "assets" / "fonts" / "BaoCanMouHuiTing-Regular.ttf"
BG = EP / "runs" / "20261103-gla-b01" / "media" / "affine" / "c1-s01.mp4"
RUN = EP / "runs" / "20261104-fontsample-b01"
FRAMES = RUN / "frames"
OUT = EP / "video" / "samples" / "glacier_intro_font_10s.mp4"
FFMPEG = r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"

W, H, FPS, DUR = 1920, 1080, 30, 10.0
FS = 144
TRACKING = 8
STROKE_R = 5
WARM = (246, 241, 233, 255)
DARK = (10, 16, 24, 235)

LINES = ["在地球最寒冷的地方", "有一条流淌了几千年的河", "它的河水，是冰。"]
# 每行中心 y：单行 540；两句 462/618；三句 384/540/696
POS = {
    "l1": [(0.0, 540), (3.1, 540), (4.1, 432), (5.5, 432), (6.5, 324)],
    "l2": [(0.0, 648), (5.5, 648), (6.5, 540)],
    "l3": [(0.0, 756)],
}
# alpha 关键帧 (t, a)
ALPHA = {
    "l1": [(0.0, 0.0), (0.8, 0.0), (1.9, 1.0), (8.3, 1.0), (9.5, 0.0)],
    "l2": [(0.0, 0.0), (3.1, 0.0), (4.2, 1.0), (8.3, 1.0), (9.5, 0.0)],
    "l3": [(0.0, 0.0), (5.5, 0.0), (6.6, 1.0), (8.3, 1.0), (9.5, 0.0)],
}


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def interp(keys, t, ease=False):
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            k = (t - t0) / max(1e-6, t1 - t0)
            if ease:
                k = smooth(k)
            return v0 + (v1 - v0) * k
    return keys[-1][1]


def make_layer(text):
    font = ImageFont.truetype(str(FONT_PATH), FS)
    widths = [font.getlength(ch) for ch in text]
    total = sum(widths) + TRACKING * (len(text) - 1)
    pad = STROKE_R + 12
    lw, lh = int(total) + pad * 2, FS + pad * 2
    img = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    baseline = lh / 2 + FS * 0.36
    # 两遍：先给整行描边，再统一填字，避免下一字的描边压到上一字的笔画
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
    cx, cy = W / 2, H / 2
    r = np.sqrt(((xx - cx) / (W * 0.62)) ** 2 + ((yy - cy) / (H * 0.62)) ** 2)
    mask = np.clip(1.0 - 0.32 * r ** 2, 0.55, 1.0)
    return mask[..., None]


def main():
    FRAMES.mkdir(parents=True, exist_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    layers = {k: make_layer(t) for k, t in zip(("l1", "l2", "l3"), LINES)}
    print({k: v.size for k, v in layers.items()})

    cap = cv2.VideoCapture(str(BG))
    cap.set(cv2.CAP_PROP_FPS, FPS)
    frames = []
    while len(frames) < int(DUR * FPS):
        ok, fr = cap.read()
        if not ok:
            break
        frames.append(fr)
    cap.release()
    while len(frames) < int(DUR * FPS):
        frames.append(frames[-1].copy())
    print("bg frames", len(frames))

    vig = vignette()
    for i in range(int(DUR * FPS)):
        t = i / FPS
        fr = frames[i].astype(np.float32)
        fade = min(1.0, t / 0.6) * (1.0 if t < 9.3 else max(0.0, (10.0 - t) / 0.7))
        fr = fr * 0.86 * fade
        fr = np.clip(fr * vig, 0, 255).astype(np.uint8)
        base = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)).convert("RGBA")

        for key, img in layers.items():
            a = interp(ALPHA[key], t, ease=False)
            if a <= 0.002:
                continue
            arr = np.array(img)
            arr[:, :, 3] = (arr[:, :, 3] * a).astype(np.uint8)
            layer = Image.fromarray(arr)
            cy = interp(POS[key], t, ease=True)
            x = (W - layer.width) // 2
            y = int(round(cy - layer.height / 2))
            base.alpha_composite(layer, (x, y))

        out = cv2.cvtColor(np.array(base.convert("RGB")), cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(FRAMES / f"f{i:04d}.png"), out)

    cmd = [FFMPEG, "-y", "-framerate", str(FPS), "-i", str(FRAMES / "f%04d.png"),
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", str(OUT)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[-800:])
    print("OK", OUT, OUT.stat().st_size // 1024 // 1024, "MB")


if __name__ == "__main__":
    main()
