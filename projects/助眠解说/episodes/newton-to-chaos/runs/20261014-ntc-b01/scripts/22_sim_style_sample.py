# -*- coding: utf-8 -*-
"""模拟镜头风格增强样例(用户 2026-10-18 委托,先出样片人工审核)。

目标:弥合"数据可视化语言"与助眠视觉规范("科幻纪录片:体积光/氛围/层次")的割裂。
增强项(全部在渲染器内,不重跑物理):
  1. bloom 辉光(两级高斯,线条变发光体)
  2. 锥形尾迹(线宽/亮度/色温沿轨迹渐变,头亮尾暗,轨迹变彗尾)
  3. 天体多层径向光晕 + 热核亮点
  4. 三层深度星空 + 极淡星云渐变 + 暗角
  5. 2x 超采样渲染再缩小(线条抗锯齿)

实现方式:import 10_render_sims 并猴子补丁 save_frame/render_trails/plot_body,
验证通过后再固化进 10_render_sims.py。
输出:sim_style_sample/{shot}_compare.mp4(左=现状,右=增强)。
运行:voxcpm venv python。
"""
import sys, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
import subprocess

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\newton-to-chaos")
RUN = EP / "runs" / "20261014-ntc-b01"
SIMS_DIR = EP / "image" / "sims"
OUT = RUN / "sim_style_sample"
FFMPEG = r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"
W, H = 1280, 720
SAMPLE_SHOTS = [("ch02-p02-s01", "two_body_ellipse"),
                ("ch04-p14-s01", "double_pendulum_chaotic")]
SAMPLE_DUR = 12.0

sys.path.insert(0, str(RUN / "scripts"))
from importlib import import_module
mod = import_module("10_render_sims")
SIMS = import_module("03_sim_specs").SIMS

# ---------- 预计算氛围层 ----------
rng = np.random.default_rng(20261018)

def _star_layer(n, r_range, a_range):
    from PIL import ImageDraw
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    rs = rng.uniform(r_range[0], r_range[1], n)
    a = rng.uniform(a_range[0], a_range[1], n)
    xs = rng.uniform(0, W, n); ys = rng.uniform(0, H, n)
    for x, y, r, al in zip(xs, ys, rs, a):
        d.ellipse([x - r, y - r, x + r, y + r], fill=int(al))
    return np.asarray(img).astype(np.float32) / 255.0

STARS = [(_star_layer(90, (0.5, 0.9), (18, 45)), np.array([150, 165, 185], np.float32)),
         (_star_layer(38, (0.8, 1.3), (35, 75)), np.array([175, 195, 215], np.float32)),
         (_star_layer(12, (1.2, 2.0), (55, 110)), np.array([200, 220, 240], np.float32))]

def _nebula():
    base = np.zeros((H, W, 3), np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    for cx, cy, rad, col, k in [(W*0.72, H*0.30, 520, (10, 26, 34), 1.0),
                                 (W*0.20, H*0.75, 610, (8, 18, 30), 0.8),
                                 (W*0.45, H*0.50, 800, (6, 14, 24), 0.5)]:
        r2 = ((xx - cx)**2 + (yy - cy)**2) / rad**2
        g = np.exp(-r2) * k
        base += g[..., None] * np.array(col, np.float32)
    return base
NEBULA = _nebula()

_yy, _xx = np.mgrid[0:H, 0:W]
_r = np.sqrt(((_xx - W/2) / (W/2))**2 + ((_yy - H/2) / (H/2))**2)
VIGNETTE = (1.0 - 0.38 * np.clip(_r - 0.35, 0, 1)**1.6)[..., None].astype(np.float32)

def _blur(a, radius):
    return np.asarray(Image.fromarray((a * 255).astype(np.uint8))
                      .filter(ImageFilter.GaussianBlur(radius))).astype(np.float32) / 255.0

# ---------- 替换 save_frame:超采样缩小 + 氛围 + bloom ----------
def enhanced_save_frame(fig):
    fig.canvas.draw()
    buf = np.asarray(fig.canvas.buffer_rgba())[..., :3]
    im = Image.fromarray(buf).resize((W, H), Image.LANCZOS)   # 2x 超采样
    f = np.asarray(im).astype(np.float32)
    f = f * VIGNETTE + NEBULA
    for mask, col in STARS:
        f += mask[..., None] * col
    # bloom 两级:细辉光(半径6,强)+ 宽氛围光(半径22,柔)
    hi = np.clip((f.max(axis=2) - 130) / 125.0, 0, 1)
    for radius, gain, tint in [(6, 95.0, (0.85, 1.0, 1.0)), (22, 38.0, (0.6, 0.85, 1.0))]:
        b = _blur(hi, radius)
        f += b[..., None] * gain * np.array(tint, np.float32)
    return np.clip(f, 0, 255).astype(np.uint8)

# ---------- 替换 render_trails:锥形彗尾 ----------
from matplotlib.collections import LineCollection

def tapered_trails(ax, pos_hist, color, trail_len=120, lw=3.0, alpha_max=0.9):
    arr = np.asarray(pos_hist, dtype=float)
    seqs = [arr[:, b] for b in range(arr.shape[1])] if arr.ndim == 3 else [arr]
    color = np.array(color, float)
    white = np.array([255, 255, 255], float)
    for seg in seqs:
        n = len(seg)
        st = max(0, n - trail_len)
        seg = seg[st:]
        if len(seg) < 2:
            continue
        pts = np.stack([seg[:-1], seg[1:]], axis=1)
        m = len(pts)
        BANDS = 7
        for b in range(BANDS):
            i0 = int(m * b / BANDS); i1 = int(m * (b + 1) / BANDS)
            if i1 - i0 < 1:
                continue
            t = (b + 1) / BANDS                      # 新→旧 0→1 内的"新近度"
            sub = pts[i0:i1]
            mix = 0.45 * t**2                        # 最新段向白偏移(热)
            col = color * (1 - mix) + white * mix
            lc = LineCollection(sub, colors=[(*[c / 255 for c in col],
                                              alpha_max * (0.10 + 0.90 * t**1.4))],
                                linewidths=max(0.5, lw * (0.22 + 0.78 * t)),
                                capstyle="round")
            ax.add_collection(lc)

# ---------- 替换 plot_body:多层光晕 + 热核 ----------
def halo_body(ax, p, color, size=22, halo=True):
    x, y = p[0], p[1]
    if halo:
        for s, a in [(size*5.0, 0.045), (size*3.2, 0.10), (size*2.2, 0.22), (size*1.3, 0.55)]:
            ax.scatter([x], [y], s=s, c=[color], alpha=a, edgecolors="none", zorder=3)
    core = np.array(color, float) * 0.35 + 255 * 0.65
    ax.scatter([x], [y], s=size * 0.62, c=[tuple(core / 255)], edgecolors="none", zorder=4)

mod.save_frame = enhanced_save_frame
mod.render_trails = tapered_trails
mod.plot_body = halo_body
mod.W, mod.H = W * 2, H * 2          # 2x 超采样画布

def encode_compare(shot, frames):
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / f"_{shot}_enh"
    tmp.mkdir(exist_ok=True)
    for i, f in enumerate(frames):
        Image.fromarray(f).save(str(tmp / f"f{i:05d}.png"))
    enh = OUT / f"{shot}_enh.mp4"
    subprocess.run([FFMPEG, "-y", "-framerate", "24", "-i", str(tmp / "f%05d.png"),
                    "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                    "-pix_fmt", "yuv420p", str(enh)], check=True, capture_output=True)
    cur = SIMS_DIR / f"{shot}.mp4"
    cmp4 = OUT / f"{shot}_compare.mp4"
    subprocess.run([FFMPEG, "-y", "-i", str(cur), "-i", str(enh),
                    "-filter_complex",
                    f"[0:v]scale={W}:{H},trim=duration={SAMPLE_DUR},setpts=PTS-STARTPTS[a];"
                    f"[1:v]trim=duration={SAMPLE_DUR},setpts=PTS-STARTPTS[b];"
                    f"[a][b]hstack,format=yuv420p[v]",
                    "-map", "[v]", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                    "-t", str(SAMPLE_DUR), str(cmp4)], check=True, capture_output=True)
    for p in tmp.glob("*.png"):
        p.unlink()
    tmp.rmdir()
    print(f"OK {cmp4.name} ({cmp4.stat().st_size//1024}KB)")

def main():
    for shot, key in SAMPLE_SHOTS:
        spec = dict(SIMS[key])
        spec["duration_s"] = int(SAMPLE_DUR)
        sysname = spec["system"]
        fn = mod.DISPATCH[sysname]
        print(f"render {shot} [{sysname}/{key}] {SAMPLE_DUR}s @2x ...")
        frames = fn(spec, key)
        encode_compare(shot, frames)
    print("-> ", OUT)

if __name__ == "__main__":
    main()
