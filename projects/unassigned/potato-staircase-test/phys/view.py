#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G1 调试视图：不追求好看，追求“看得见物理”。

画的东西：真实碰撞圆（不是贴图）+ 旋转辐条 + 速度矢量 + 角速度
+ 接触/冲量打点 + 数值 HUD；另导出撞击前后 24 连续帧的条带。
"""
from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .scene import Scene, World

S = 0.5                       # 1080x1920 -> 540x960 调试画布
CW, CH = int(1080 * S), int(1920 * S)
FONT = "C:/Windows/Fonts/msyh.ttc"
FONT_MONO = "C:/Windows/Fonts/consola.ttf"


def set_scale(s: float) -> None:
    """调试视频用 0.5；条带用 1.0（1:1 裁剪，位移才看得出来）。"""
    global S, CW, CH
    S = s
    CW, CH = int(1080 * s), int(1920 * s)

BG = (12, 11, 10)
LINE = (232, 232, 228)
POT = (214, 160, 92)
POT_EDGE = (60, 38, 20)
SPOKE = (255, 236, 196)
VEL = (86, 214, 255)
OMEGA = (255, 120, 200)
HIT = (255, 96, 60)
DIM = (140, 138, 132)


def _f(size: int, mono: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_MONO if mono else FONT, size)


def _pt(p):
    return (p[0] * S, p[1] * S)


def _ellipse(center, r, angle, aspect=0.835):
    cx, cy = center
    ca, sa = math.cos(angle), math.sin(angle)
    out = []
    for k in range(30):
        t = 2 * math.pi * k / 30
        x, y = r * math.cos(t), r * aspect * math.sin(t)
        out.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    return out


def render_frame(w: World, res: dict, k: int) -> Image.Image:
    sc = w.sc
    tr = res["trace"]
    im = Image.new("RGB", (CW, CH), BG)
    d = ImageDraw.Draw(im, "RGBA")

    # 阶梯：连续细线（与参考片一致的画法）
    d.line([_pt(p) for p in w.outline], fill=LINE, width=2, joint="curve")

    t = tr["t"][k]
    # 撞击闪光
    for e in res["impacts"]:
        dt = t - e["t"]
        if -0.02 <= dt <= 0.16:
            c = _pt(e["point"])
            rad = 10 + 90 * max(0.0, dt) / 0.16
            al = int(235 * (1 - max(0.0, dt) / 0.16))
            d.ellipse([c[0] - rad, c[1] - rad, c[0] + rad, c[1] + rad],
                      outline=HIT + (al,), width=2)

    for i, p in enumerate(w.potatoes):
        pos = _pt(tr["pos"][k][i])
        v = tr["vel"][k][i]
        vra = tr["angle"][k][i]
        r = p["r"] * S
        # 真实碰撞圆
        d.ellipse([pos[0] - r, pos[1] - r, pos[0] + r, pos[1] + r],
                  fill=POT + (255,), outline=POT_EDGE + (255,), width=2)
        # 辐条：角度可读
        for off in (0.0, math.pi * 0.5):
            a = vra + off
            d.line([pos, (pos[0] + r * 0.94 * math.cos(a), pos[1] + r * 0.94 * math.sin(a))],
                   fill=SPOKE + (200,), width=2)
        d.ellipse([pos[0] - 2.5, pos[1] - 2.5, pos[0] + 2.5, pos[1] + 2.5], fill=POT_EDGE + (255,))
        # 索引
        d.text((pos[0], pos[1] - r - 9), f"P{i}", font=_f(13), fill=DIM + (255,), anchor="mb")
        # 速度矢量
        sp = math.hypot(*v)
        if sp > 8:
            tip = (pos[0] + v[0] * 0.16, pos[1] + v[1] * 0.16)
            d.line([pos, tip], fill=VEL + (230,), width=2)
            d.ellipse([tip[0] - 3, tip[1] - 3, tip[0] + 3, tip[1] + 3], fill=VEL + (230,))

    # HUD
    y = 10
    d.rectangle([0, 0, CW, 96], fill=(0, 0, 0, 155))
    d.text((10, y), f"[{sc.key}] {sc.label}", font=_f(15), fill=(245, 240, 230))
    y += 20
    d.text((10, y), f"t={t:6.2f}s  slope={sc.slope_deg:.0f}°  lip={sc.lip_h:.0f}px  "
                    f"W={sc.step_w:.0f}  r={sc.radii}", font=_f(12, True), fill=(200, 200, 195))
    y += 16
    parts = []
    for i in range(len(w.potatoes)):
        vx, vy = tr["vel"][k][i]
        parts.append(f"P{i} v={math.hypot(vx, vy):6.1f} w={tr['angvel'][k][i]:6.2f}")
    d.text((10, y), "   ".join(parts), font=_f(11, True), fill=VEL)
    y += 15
    d.text((10, y), f"pen={tr['pen'][k]:+.2f}px  hits={sum(1 for e in res['impacts'] if e['t'] <= t)}"
                    f"  sep>=1px: " + " ".join(
                        f"{(e['sep_dt'] if e['sep_dt'] is not None else -1):.2f}"
                        for e in res["impacts"][:6]),
           font=_f(11, True), fill=(190, 190, 185))

    # 底部结论
    d.rectangle([0, CH - 58, CW, CH], fill=(0, 0, 0, 165))
    ok = res["pass"]
    d.text((10, CH - 50), ("PASS  " if ok else "FAIL  ") + " | ".join(
        f"{'OK' if c['ok'] else 'NG'} {c['name']}" for c in res["checks"]),
        font=_f(10, True), fill=(120, 235, 150) if ok else (255, 130, 110))
    d.text((10, CH - 30), f"max_pen={res['max_penetration']}px  slip={res['slip_mean']}"
                          f"  dur={res['duration']}s", font=_f(10, True), fill=DIM)
    return im


def render_frames(w: World, res: dict, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    n = len(res["trace"]["t"])
    for k in range(n):
        render_frame(w, res, k).save(out_dir / f"f{k:05d}.png")
    return n


def encode_video(frames_dir: Path, out_mp4: Path, fps: int = 60) -> None:
    out_mp4.unlink(missing_ok=True)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-framerate", str(fps), "-i", str(frames_dir / "f%05d.png"),
           "-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq",
           "-pix_fmt", "yuv420p", "-rc", "vbr", "-cq", "21",
           "-movflags", "+faststart", str(out_mp4)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg failed:\n" + r.stderr[-2000:])


def make_strip(w: World, res: dict, ev: dict, out_jpg: Path,
               pre: int = 3, post: int = 27, crop=(560, 420), cols: int = 6) -> Path:
    """撞击前后连续帧条带（默认 31 帧 / 0.5s），1:1 裁剪以看清位移。"""
    prev = S
    set_scale(1.0)
    try:
        return _make_strip(w, res, ev, out_jpg, pre, post, crop, cols)
    finally:
        set_scale(prev)


def _make_strip(w: World, res: dict, ev: dict, out_jpg: Path,
                pre: int, post: int, crop, cols: int) -> Path:
    tr = res["trace"]
    k0 = min(range(len(tr["t"])), key=lambda k: abs(tr["t"][k] - ev["t"]))
    idx = [k for k in range(k0 - pre, k0 + post + 1) if 0 <= k < len(tr["t"])]
    cw, chh = crop
    cx, cy = _pt(ev["point"])
    cy += 120
    left = min(max(0, int(cx - cw / 2)), CW - cw)
    top = min(max(0, int(cy - chh / 2)), CH - chh)
    rows = (len(idx) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cw, rows * chh), (0, 0, 0))
    for j, k in enumerate(idx):
        fr = render_frame(w, res, k).crop((left, top, left + cw, top + chh))
        dd = ImageDraw.Draw(fr, "RGBA")
        dt = tr["t"][k] - ev["t"]
        dd.rectangle([0, 0, cw, 17], fill=(0, 0, 0, 190))
        dd.text((5, 2), f"{j * 1000 // 60:>3}ms  dt={dt * 1000:+.0f}ms", font=_f(12, True),
                fill=(255, 255, 255))
        sheet.paste(fr, ((j % cols) * cw, (j // cols) * chh))
    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_jpg, quality=90)
    return out_jpg


def make_overview(w: World, res: dict, out_jpg: Path, n: int = 12) -> Path:
    """全程每 0.5s 一帧的概览。"""
    tr = res["trace"]
    step = max(1, len(tr["t"]) // n)
    idx = list(range(0, len(tr["t"]), step))[:n]
    cols = 4
    rows = (len(idx) + cols - 1) // cols
    tw, th = CW // 2, CH // 2
    sheet = Image.new("RGB", (cols * tw, rows * th), (0, 0, 0))
    for j, k in enumerate(idx):
        fr = render_frame(w, res, k).resize((tw, th), Image.LANCZOS)
        sheet.paste(fr, ((j % cols) * tw, (j // cols) * th))
    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_jpg, quality=88)
    return out_jpg
