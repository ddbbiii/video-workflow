#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
土豆阶梯接力 · 代码变速测试
10 个土豆 / 1080x1920 / 60fps / 代码 time-warp 0.75x / 2.5D 景深
"""
from __future__ import annotations

import argparse
import bisect
import math
import random
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE = Path(__file__).resolve().parent
ASSETS = BASE / "assets"
AUDIO = BASE / "audio"
OUT = BASE / "out"
QA = BASE / "qa"
for p in (ASSETS, AUDIO, OUT, QA):
    p.mkdir(parents=True, exist_ok=True)

W, H = 1080, 1920
FPS = 60
STEPS = 10
STEP_W = 90
STEP_H = 125
X0 = 100.0
Y0 = 440.0
TRAVEL = 5.2
DELAY = 0.8
SLOW_OUT = 0.65
SLOW_SCALE = 0.75
FINAL_HOLD = 3.2

FONT_TITLE = "C:/Windows/Fonts/simsun.ttc"
FONT_UI = "C:/Windows/Fonts/msyh.ttc"

POTATO = ASSETS / "potato.png"
BG = ASSETS / "bg.png"
SHADOW = ASSETS / "shadow.png"
GLOW = ASSETS / "glow.png"


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def smoothstep(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


# ---------------------------------------------------------------------------
# layout
# ---------------------------------------------------------------------------

RADII = [22.0 + i * 4.5 for i in range(STEPS)]          # 22..62.5
REST = []
for i in range(STEPS):
    x = X0 + i * STEP_W + STEP_W * 0.55
    y = Y0 + i * STEP_H - RADII[i]
    REST.append((x, y))

STAIR = []
for i in range(STEPS):
    x = X0 + i * STEP_W
    y = Y0 + i * STEP_H
    STAIR.append(((x, y), (x + STEP_W, y)))
    if i < STEPS - 1:
        STAIR.append(((x + STEP_W, y), (x + STEP_W, y + STEP_H)))


def catmull(points, u):
    n = len(points) - 1
    if n <= 0:
        return points[0]
    u = clamp(u, 0.0, 1.0)
    seg = min(int(u * n), n - 1)
    t = u * n - seg
    p0 = points[max(0, seg - 1)]
    p1 = points[seg]
    p2 = points[seg + 1]
    p3 = points[min(n, seg + 2)]
    out = []
    for k in range(2):
        v = 0.5 * (
            2 * p1[k]
            + (-p0[k] + p2[k]) * t
            + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t * t
            + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t * t * t
        )
        out.append(v)
    return tuple(out)


def build_paths():
    paths = []
    for i in range(STEPS - 1):
        start = REST[i]
        target = REST[i + 1]
        edge1 = (X0 + (i + 1) * STEP_W, Y0 + i * STEP_H)
        edge2 = (edge1[0], Y0 + (i + 1) * STEP_H)
        dx, dy = target[0] - edge2[0], target[1] - edge2[1]
        ln = math.hypot(dx, dy) or 1.0
        contact = (target[0] - (RADII[i] + RADII[i + 1]) * 1.02, target[1])
        paths.append([start, edge1, edge2, contact])
    return paths


PATHS = build_paths()

SEGMENTS = []
s = DELAY
for i in range(STEPS - 1):
    SEGMENTS.append((s, s + TRAVEL, i))
    s += TRAVEL
SOURCE_END = s + FINAL_HOLD


def path_position(points, u):
    """start -> tread edge (roll) -> drop -> next tread (roll)."""
    u = clamp(u, 0.0, 1.0)
    if u < 0.42:
        a, b, t = points[0], points[1], u / 0.42
    elif u < 0.68:
        a, b, t = points[1], points[2], (u - 0.42) / 0.26
    else:
        a, b, t = points[2], points[3], (u - 0.68) / 0.32
    t = smoothstep(t)
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def potato_position(i, src_t):
    if i >= len(SEGMENTS):
        return REST[i]
    start, end, _ = SEGMENTS[i]
    if src_t <= start:
        return REST[i]
    if src_t >= end:
        return PATHS[i][-1]
    u = (src_t - start) / TRAVEL
    return path_position(PATHS[i], u)


# ---------------------------------------------------------------------------
# timeline (code-controlled speed)
# ---------------------------------------------------------------------------

def build_timeline():
    """Returns output segments: (out_start, out_end, speed, src_start), impacts."""
    segs = []
    impacts = []
    o = 0.0
    src = 0.0
    for i, (start, end, _) in enumerate(SEGMENTS):
        dur = end - src
        segs.append((o, o + dur, 1.0, src))
        o += dur
        src = end
        impacts.append((o, i))
        segs.append((o, o + SLOW_OUT, SLOW_SCALE, src))
        o += SLOW_OUT
        src += SLOW_OUT * SLOW_SCALE
    segs.append((o, o + (SOURCE_END - src), 1.0, src))
    out_end = o + (SOURCE_END - src)
    return segs, impacts, out_end


TIMELINE, IMPACTS, OUT_END = build_timeline()
OUT_STARTS = [x[0] for x in TIMELINE]


def src_time(t_out):
    if t_out <= 0:
        return 0.0
    if t_out >= OUT_END:
        return SOURCE_END
    idx = bisect.bisect_right(OUT_STARTS, t_out) - 1
    o0, o1, speed, s0 = TIMELINE[idx]
    return s0 + (t_out - o0) * speed


def focus_index(src_t):
    for i, (start, end, _) in enumerate(SEGMENTS):
        if src_t < end:
            return i
    return STEPS - 1


# ===========================================================================
# Track-constrained physics override
# Every potato is a circle constrained to one staircase surface; adjacent
# bodies exchange 1D impulses. No hand-authored per-potato path.
# ===========================================================================

TW, TH = 110.0, 130.0
TX0, TY0 = 100.0, 420.0
DWELL = 4.0
V0 = 190.0
TRACK_G = 900.0
TRACK_DAMP = 0.8
TRACK_E = 0.2

_surface = []
for _i in range(STEPS):
    _x = TX0 + _i * TW
    _y = TY0 + _i * TH
    for _k in range(0, 111, 2):
        _surface.append((_x + TW * _k / 110.0, _y))
    if _i < STEPS - 1:
        for _k in range(0, 131, 2):
            _surface.append((_x + TW, _y + TH * _k / 130.0))

_sm = [_surface[0]]
for _i in range(1, len(_surface) - 1):
    _a, _b, _c = _surface[_i - 1], _surface[_i], _surface[_i + 1]
    _sm.append(((_a[0] + 2 * _b[0] + _c[0]) / 4, (_a[1] + 2 * _b[1] + _c[1]) / 4))
_sm.append(_surface[-1])
_surface = _sm

_cum = [0.0]
for _i in range(1, len(_surface)):
    _cum.append(_cum[-1] + math.dist(_surface[_i - 1], _surface[_i]))
_PATH_LEN = _cum[-1]


def _track_sample(s):
    s = clamp(s, 0.0, _PATH_LEN)
    i = min(bisect.bisect_right(_cum, s) - 1, len(_surface) - 2)
    t = (s - _cum[i]) / max(1e-9, _cum[i + 1] - _cum[i])
    p = (_surface[i][0] + (_surface[i + 1][0] - _surface[i][0]) * t,
         _surface[i][1] + (_surface[i + 1][1] - _surface[i][1]) * t)
    dx = _surface[i + 1][0] - _surface[i][0]
    dy = _surface[i + 1][1] - _surface[i][1]
    ln = math.hypot(dx, dy) or 1.0
    return p, (dx / ln, dy / ln)


def _s_at(x, y):
    best, bd = 0.0, 1e18
    for i in range(len(_surface)):
        d = (_surface[i][0] - x) ** 2 + (_surface[i][1] - y) ** 2
        if d < bd:
            bd, best = d, _cum[i]
    return best


def _center_from_s(i, s):
    p, tan = _track_sample(s)
    if abs(tan[1]) > abs(tan[0]):
        return (p[0] + RADII[i], p[1])      # falling beside a riser
    return (p[0], p[1] - RADII[i])          # resting on a tread


# rest positions along the track: right edge of each tread
_REST_S = []
for _i in range(STEPS):
    _x = TX0 + _i * TW + TW - RADII[_i] - 3
    _y = TY0 + _i * TH
    _REST_S.append(_s_at(_x, _y))
_REST_S[0] = _s_at(TX0 + 22, TY0)

_S = list(_REST_S)
_V = [0.0] * STEPS
_M = [r * r for r in RADII]
_HOLD = [1e9] * STEPS
_HOLD[0] = 0.0
_V[0] = V0
_PENDING = [0.0] * STEPS
_COOLDOWN = [0.0] * STEPS
_ANGLE = [0.0] * STEPS

_CHAIN = []          # (source time, target potato index)
_IMPACT_CENTERS = []
_FRAMES = []         # per 60fps: (S tuple, angle tuple)

_SIM_DT = 1 / 240
_MAX_STEPS = int(80 / _SIM_DT)
_t = 0.0
for _step in range(_MAX_STEPS):
    _t = _step * _SIM_DT
    for _i in range(STEPS):
        _COOLDOWN[_i] = max(0.0, _COOLDOWN[_i] - _SIM_DT)
        if _HOLD[_i] > 0:
            _HOLD[_i] -= _SIM_DT
            _V[_i] = 0.0
            if _HOLD[_i] <= 0:
                _V[_i] = max(_PENDING[_i], 175.0)
            continue
        _p, _tan = _track_sample(_S[_i])
        _V[_i] += TRACK_G * _tan[1] * _SIM_DT
        _V[_i] *= math.exp(-TRACK_DAMP * _SIM_DT)
        _d = _V[_i] * _SIM_DT
        _S[_i] += _d
        _ANGLE[_i] += _d / RADII[_i]

    for _i in range(STEPS - 1):
        if _COOLDOWN[_i] > 0:
            continue
        _gap = RADII[_i] + RADII[_i + 1]
        if _S[_i + 1] - _S[_i] < _gap:
            _rel = _V[_i] - _V[_i + 1]
            if _rel > 0:
                _j = -(1 + TRACK_E) * _rel / (1 / _M[_i] + 1 / _M[_i + 1])
                _V[_i] += _j / _M[_i]
                _V[_i + 1] -= _j / _M[_i + 1]
                _COOLDOWN[_i] = DWELL + 2.5
                if _HOLD[_i + 1] > 0:
                    _CHAIN.append((_t, _i + 1))
                    _IMPACT_CENTERS.append(_center_from_s(_i + 1, _S[_i + 1]))
                    _PENDING[_i + 1] = max(0.0, _V[_i + 1])
                    _HOLD[_i + 1] = DWELL
                    _V[_i + 1] = 0.0
                    _V[_i] = 0.0
                    _S[_i] = _S[_i + 1] - _gap - 1.0
            _overlap = _gap - (_S[_i + 1] - _S[_i])
            if _overlap > 0:
                _S[_i] -= _overlap * 0.5
                _S[_i + 1] += _overlap * 0.5

    if _step % 4 == 0:
        _FRAMES.append((tuple(_S), tuple(_ANGLE)))
    if len(_CHAIN) >= STEPS - 1 and _t > _CHAIN[-1][0] + 3.2:
        break

# The chain should always produce nine impacts; fall back to the simulated
# sequence if a collision was missed.
if len(_CHAIN) < STEPS - 1:
    print("WARNING: only", len(_CHAIN), "chain impacts")

SOURCE_END = len(_FRAMES) / FPS
REST = [_center_from_s(i, _REST_S[i]) for i in range(STEPS)]

# impacts are (source time, target index)
SEGMENTS = []
_prev = 0.0
for _k, (_ti, _idx) in enumerate(_CHAIN):
    SEGMENTS.append((_prev, _ti, _idx))
    _prev = _ti
if not SEGMENTS:
    SEGMENTS = [(0.0, SOURCE_END, STEPS - 1)]

PATHS = []
for _k, (_ti, _idx) in enumerate(_CHAIN):
    PATHS.append([_IMPACT_CENTERS[_k]])


def _state_at(src_t):
    idx = int(clamp(src_t * FPS, 0, len(_FRAMES) - 1))
    return _FRAMES[idx]


def potato_position(i, src_t):
    s, _ = _state_at(src_t)
    return _center_from_s(i, s[i])


def potato_angle(i, src_t):
    _, a = _state_at(src_t)
    return a[i]


def focus_index(src_t):
    idx = 0
    for k, (ti, target) in enumerate(_CHAIN):
        if src_t >= ti:
            idx = target
    return idx


def build_timeline_from_impacts():
    segs = []
    impacts = []
    o = 0.0
    src = 0.0
    for k, (ti, target) in enumerate(_CHAIN):
        dur = ti - src
        segs.append((o, o + dur, 1.0, src))
        o += dur
        src = ti
        impacts.append((o, target))
        segs.append((o, o + SLOW_OUT, SLOW_SCALE, src))
        o += SLOW_OUT
        src += SLOW_OUT * SLOW_SCALE
    segs.append((o, o + (SOURCE_END - src), 1.0, src))
    out_end = o + (SOURCE_END - src)
    return segs, impacts, out_end


TIMELINE, IMPACTS, OUT_END = build_timeline_from_impacts()
OUT_STARTS = [x[0] for x in TIMELINE]


def src_time(t_out):
    if t_out <= 0:
        return 0.0
    if t_out >= OUT_END:
        return SOURCE_END
    idx = bisect.bisect_right(OUT_STARTS, t_out) - 1
    o0, o1, speed, s0 = TIMELINE[idx]
    return s0 + (t_out - o0) * speed


# ---------------------------------------------------------------------------
# assets
# ---------------------------------------------------------------------------

def make_bg():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    y = (yy / (H - 1))[..., None]
    top = np.array([3, 3, 3], dtype=np.float32)
    bot = np.array([10, 8, 7], dtype=np.float32)
    img = top[None, None, :] * (1 - y) + bot[None, None, :] * y

    d = np.sqrt((xx - W * 0.52) ** 2 + (yy - H * 0.55) ** 2)
    warm = np.exp(-(d / 700.0) ** 2)[..., None] * np.array([18, 11, 6], dtype=np.float32)
    img = img + warm

    vn = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    vig = 1.0 - 0.55 * np.clip(vn - 0.15, 0, 1) ** 1.3
    img = img * vig[..., None]

    rng = np.random.default_rng(7)
    img = img + rng.normal(0, 1.8, (H, W, 1))
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").save(BG)


def make_soft():
    n = 512
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    nx = (xx - n / 2) / (n / 2)
    ny = (yy - n / 2) / (n / 2)
    a = np.exp(-((nx / 0.95) ** 2 + (ny / 0.26) ** 2) * 2.4)
    sh = np.zeros((n, n, 4), dtype=np.uint8)
    sh[..., 3] = (np.clip(a, 0, 1) * 170).astype(np.uint8)
    Image.fromarray(sh, "RGBA").save(SHADOW)

    g = np.exp(-((nx ** 2 + ny ** 2) / 0.50) * 2.2)
    gl = np.zeros((n, n, 4), dtype=np.uint8)
    gl[..., 0], gl[..., 1], gl[..., 2] = 255, 175, 90
    gl[..., 3] = (np.clip(g, 0, 1) * 80).astype(np.uint8)
    Image.fromarray(gl, "RGBA").save(GLOW)


def make_blur_bases():
    src = Image.open(POTATO).convert("RGBA")
    base = 640
    h = int(round(src.height * base / src.width))
    src = src.resize((base, h), Image.Resampling.LANCZOS)
    out = {}
    for lvl in range(13):
        if lvl == 0:
            out[lvl] = src
        else:
            out[lvl] = src.filter(ImageFilter.GaussianBlur(lvl))
    return out


# ---------------------------------------------------------------------------
# text
# ---------------------------------------------------------------------------

class TextCache:
    def __init__(self):
        self.cache = {}
        self.fonts = {
            "title": ImageFont.truetype(FONT_TITLE, 66),
            "end": ImageFont.truetype(FONT_TITLE, 54),
            "sub": ImageFont.truetype(FONT_UI, 24),
        }

    def get(self, text, key="title", fill=(255, 255, 255, 255), stroke=0, spacing=16):
        ck = (text, key, fill, stroke, spacing)
        if ck in self.cache:
            return self.cache[ck]
        font = self.fonts[key]
        lines = text.split("\n")
        widths, heights = [], []
        for line in lines:
            b = font.getbbox(line, stroke_width=stroke)
            widths.append(b[2] - b[0])
            heights.append(b[3] - b[1])
        w = max(widths) + stroke * 2 + 8
        h = sum(heights) + spacing * (len(lines) - 1) + stroke * 2 + 8
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        y = 4
        for line, lw, lh in zip(lines, widths, heights):
            b = font.getbbox(line, stroke_width=stroke)
            d.text(((w - lw) // 2 - b[0], y - b[1]), line, font=font, fill=fill,
                   stroke_width=stroke, stroke_fill=(0, 0, 0, 200))
            y += lh + spacing
        self.cache[ck] = img
        return img


# ---------------------------------------------------------------------------
# audio
# ---------------------------------------------------------------------------

SR = 48000


def highpass(x, n=12):
    if len(x) <= n:
        return x
    return x - np.convolve(x, np.ones(n) / n, mode="same")


def kick(dur=0.4):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    f = 48 + 145 * np.exp(-tt * 22)
    phase = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(phase) * np.exp(-tt * 9)
    click = highpass(np.random.default_rng(1).normal(0, 1, n)) * np.exp(-tt * 80) * 0.2
    return np.tanh((body + click) * 1.5)


def hat(dur=0.09):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    return highpass(np.random.default_rng(2).normal(0, 1, n), 4) * np.exp(-tt * 75) * 0.35


def snare(dur=0.25):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    nz = highpass(np.random.default_rng(3).normal(0, 1, n), 6)
    tone = np.sin(2 * np.pi * 190 * tt) * np.exp(-tt * 26) * 0.4
    return np.tanh((nz * np.exp(-tt * 20) * 0.6 + tone) * 1.3)


def bass(freq, dur):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    sig = (0.65 * np.sin(2 * np.pi * freq * tt) +
           0.22 * np.sin(2 * np.pi * freq * 2 * tt) +
           0.10 * np.sin(2 * np.pi * freq * 3 * tt))
    return sig * np.minimum(tt / 0.008, 1) * np.exp(-tt * 7)


def pluck(freq, dur=0.22):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    sig = np.sin(2 * np.pi * freq * tt) + 0.35 * np.sin(2 * np.pi * freq * 2 * tt)
    return sig * np.exp(-tt * 15) * 0.6


def potato_hit(scale=1.0, seed=0):
    """Low thud + cartoon boing + squash noise, slowed by `scale`."""
    dur = 0.55 / scale
    n = int(dur * SR)
    tt = np.arange(n) / SR
    rng = np.random.default_rng(seed + 10)

    # low body
    f0 = 95.0 * scale
    f = f0 * 0.55 + f0 * 0.45 * np.exp(-tt * 18)
    phase = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(phase) * np.exp(-tt * 11)

    # cartoon boing
    fb = (210 * scale) * (0.55 + 0.45 * np.exp(-tt * 4.5))
    vib = 1.0 + 0.035 * np.sin(2 * np.pi * 24 * tt)
    phase2 = 2 * np.pi * np.cumsum(fb * vib) / SR
    boing = np.sin(phase2) * np.exp(-tt * 5.5) * 0.55

    # squash noise
    nz = highpass(rng.normal(0, 1, n), 8) * np.exp(-tt * 35) * 0.5
    sig = np.tanh((body + boing + nz) * 1.4)
    return sig


def synth_audio(impacts, out_end, wav_path):
    n = int(out_end * SR)
    music = np.zeros(n, dtype=np.float32)
    drums = np.zeros(n, dtype=np.float32)
    sfx = np.zeros(n, dtype=np.float32)

    def add(buf, sig, start, gain=1.0):
        i = int(start * SR)
        if i < 0 or i >= n:
            return
        j = min(n, i + len(sig))
        buf[i:j] += sig[:j - i] * gain

    beat = 60.0 / 120.0
    roots = [110.0, 87.31, 130.81, 98.0]
    arp = [440.0, 523.25, 659.25, 783.99, 659.25, 523.25]

    # simple bed from 0 to end
    k = 0
    while k * beat < out_end - 0.1:
        bt = k * beat
        add(drums, kick(), bt, 0.85)
        if k % 4 in (1, 3):
            add(drums, snare(), bt, 0.42)
        add(drums, hat(), bt + beat / 2, 0.30)
        add(drums, hat(), bt, 0.13)
        add(music, bass(roots[(k // 4) % 4], beat * 0.95), bt, 0.52)
        for j in range(4):
            add(music, pluck(arp[(k * 4 + j) % len(arp)]), bt + j * beat / 4, 0.16)
        k += 1

    # impact sfx at output impact times, slowed where the video is slowed
    for idx, (t_imp, _) in enumerate(impacts):
        add(sfx, potato_hit(scale=SLOW_SCALE, seed=idx), t_imp, 1.0)

    # soft duck music around impacts
    duck = np.ones(n, dtype=np.float32)
    for t_imp, _ in impacts:
        i = int(t_imp * SR)
        m = int(0.35 * SR)
        a = max(0, i - int(0.05 * SR))
        b = min(n, i + m)
        if b > a:
            env = np.linspace(1.0, 0.65, b - a)
            duck[a:b] = np.minimum(duck[a:b], env)

    mix = drums * 0.8 + music * 0.62 * duck + sfx * 1.0
    mix = np.tanh(mix * 1.15)
    fi = int(0.06 * SR)
    mix[:fi] *= np.linspace(0, 1, fi)
    fo = int(0.3 * SR)
    mix[-fo:] *= np.linspace(1, 0, fo)
    peak = float(np.max(np.abs(mix))) or 1.0
    mix = mix / peak * 0.9

    delay = int(0.004 * SR)
    left = mix
    right = np.concatenate([np.zeros(delay, dtype=np.float32), mix[:-delay]]) * 0.97
    stereo = np.stack([left, right], axis=1)
    pcm = np.clip(stereo * 32767, -32768, 32767).astype(np.int16)
    with wave.open(str(wav_path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"audio: {wav_path}  {out_end:.2f}s")


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def screen(wx, wy, cx, cy, zoom):
    return (wx - cx) * zoom + W / 2, (wy - cy) * zoom + H / 2


def render():
    bg = Image.open(BG).convert("RGB")
    potato = Image.open(POTATO).convert("RGBA")
    aspect = potato.height / potato.width
    shadow = Image.open(SHADOW).convert("RGBA")
    glow = Image.open(GLOW).convert("RGBA")
    blur_bases = make_blur_bases()
    tc = TextCache()

    sprite_cache = {}
    n_frames = int(round(OUT_END * FPS))
    silent = OUT / "silent.mp4"
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-", "-an",
        "-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq",
        "-rc", "vbr", "-cq", "17", "-b:v", "0", "-maxrate", "30M", "-bufsize", "60M",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(silent),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    # stateful camera
    cam_cx, cam_cy, cam_zoom = W / 2, H / 2, 1.0
    last_imp = -10.0
    imp_idx = 0
    particles = []
    spawned = set()

    save_idx = {int(1.0 * FPS), int(5.0 * FPS), int(10.0 * FPS),
                int(18.0 * FPS), int(26.0 * FPS), max(0, n_frames - 90)}
    for f in QA.glob("frame_*.jpg"):
        f.unlink()

    try:
        for fi in range(n_frames):
            t_out = fi / FPS
            s = src_time(t_out)
            foc = focus_index(s)

            # impacts passed
            while imp_idx < len(IMPACTS) and IMPACTS[imp_idx][0] <= t_out:
                last_imp = IMPACTS[imp_idx][0]
                imp_idx += 1

            # spawn dust in source time
            for idx, (t_imp, i) in enumerate(IMPACTS):
                if idx in spawned or s < SEGMENTS[idx][1]:
                    continue
                spawned.add(idx)
                cx0, cy0 = PATHS[idx][-1]
                prng = random.Random(700 + idx)
                for _ in range(18):
                    ang = prng.uniform(math.pi * 1.05, math.pi * 1.95)
                    sp = prng.uniform(40, 220)
                    particles.append({
                        "birth": SEGMENTS[idx][1],
                        "x": cx0, "y": cy0,
                        "vx": math.cos(ang) * sp,
                        "vy": math.sin(ang) * sp - prng.uniform(20, 100),
                        "size": prng.uniform(2, 6),
                        "life": prng.uniform(0.35, 0.8),
                        "color": prng.choice([(255, 230, 190), (231, 180, 120), (255, 250, 235)]),
                    })

            # target camera
            first_impact = IMPACTS[0][0]
            if t_out < first_impact:
                tz = 1.0
                tcx, tcy = W / 2, H / 2
            else:
                tz = 1.95 + 0.35 * (t_out - first_impact) / max(1.0, OUT_END - first_impact)
                tcx, tcy = potato_position(foc, s)
                tcy -= 80
                if s > SEGMENTS[-1][1]:
                    tz = 2.35
                    tcx, tcy = REST[-1]
                    tcy -= 60
            # smooth
            cam_zoom += (tz - cam_zoom) * 0.10
            cam_cx += (tcx - cam_cx) * 0.12
            cam_cy += (tcy - cam_cy) * 0.12

            punch = 0.16 * math.exp(-max(0.0, t_out - last_imp) / 0.28)
            zoom = cam_zoom + punch
            shake = 9.0 * math.exp(-max(0.0, t_out - last_imp) / 0.18)
            rng = random.Random(1000 + fi)
            ox = rng.uniform(-shake, shake)
            oy = rng.uniform(-shake, shake)

            frame = bg.copy()
            draw = ImageDraw.Draw(frame, "RGBA")

            # stairs (same smoothed surface the bodies follow)
            path_px = []
            for _p in _surface:
                _sx, _sy = screen(_p[0], _p[1], cam_cx, cam_cy, zoom)
                path_px.append((_sx + ox, _sy + oy))
            wdt = max(2, int(round(3.2 * zoom)))
            draw.line(path_px, fill=(255, 255, 255, 235), width=wdt, joint="curve")

            # potatoes (far to near)
            for i in range(STEPS):
                px, py = potato_position(i, s)
                sx, sy = screen(px, py, cam_cx, cam_cy, zoom)
                sx += ox
                sy += oy
                rr = RADII[i] * zoom
                if rr < 2:
                    continue
                depth = abs(i - foc)
                close = clamp((cam_zoom - 1.02) / 0.9, 0, 1)
                lvl = int(round(min(12.0, depth * 3.0 * close)))
                blurred = blur_bases[lvl]
                sw = max(2, int(2 * rr))
                sh = max(2, int(2 * rr * aspect))
                bw = max(1, (sw // 8) * 8)
                bh = max(1, (sh // 8) * 8)
                ck = (lvl, bw, bh)
                sp = sprite_cache.get(ck)
                if sp is None:
                    sp = blurred.resize((bw, bh), Image.Resampling.LANCZOS)
                    sprite_cache[ck] = sp
                    if len(sprite_cache) > 160:
                        sprite_cache.pop(next(iter(sprite_cache)))

                # rolling rotation on the sharp/active body
                if depth == 0:
                    ang = math.degrees(potato_angle(i, s))
                    if abs(ang) > 0.5:
                        sp = sp.rotate(-ang, expand=True, resample=Image.Resampling.BICUBIC)

                # shadow
                shw = int(sp.width * 0.95)
                shh = max(8, int(sp.height * 0.14))
                ssp = sprite_cache.get(("sh", shw // 8, shh // 8))
                if ssp is None:
                    ssp = shadow.resize((max(1, shw), max(1, shh)), Image.Resampling.LANCZOS)
                    sprite_cache[("sh", shw // 8, shh // 8)] = ssp
                frame.paste(ssp, (int(sx - ssp.width / 2), int(sy + rr - ssp.height * 0.45)), ssp)

                # glow for active
                if depth == 0:
                    gw = int(sp.width * 1.45)
                    gh = int(sp.height * 1.45)
                    gsp = sprite_cache.get(("gl", gw // 16, gh // 16))
                    if gsp is None:
                        gsp = glow.resize((max(1, gw), max(1, gh)), Image.Resampling.LANCZOS)
                        sprite_cache[("gl", gw // 16, gh // 16)] = gsp
                    frame.paste(gsp, (int(sx - gsp.width / 2), int(sy + rr - gsp.height / 2)), gsp)

                bx = int(sx - sp.width / 2)
                by = int(sy + rr - sp.height)
                frame.paste(sp, (bx, by), sp)

            # impact ring + dust
            for idx, (t_imp, i) in enumerate(IMPACTS):
                age = s - SEGMENTS[idx][1]
                if 0.0 <= age < 0.34:
                    cx0, cy0 = PATHS[idx][-1]
                    sx0, sy0 = screen(cx0, cy0, cam_cx, cam_cy, zoom)
                    rr = (18 + age * 330) * zoom
                    aa = int(170 * (1 - age / 0.34))
                    draw.ellipse([sx0 - rr, sy0 - rr * 0.55, sx0 + rr, sy0 + rr * 0.55],
                                 outline=(255, 220, 170, aa), width=max(2, int(3 * zoom)))
            for p in particles:
                age = s - p["birth"]
                if age < 0 or age > p["life"]:
                    continue
                wxp = p["x"] + p["vx"] * age
                wyp = p["y"] + p["vy"] * age + 0.5 * 1500 * age * age
                sx0, sy0 = screen(wxp, wyp, cam_cx, cam_cy, zoom)
                rr = max(1.0, p["size"] * zoom * (1.0 - age / p["life"]))
                aa = int(220 * (1 - age / p["life"]))
                draw.ellipse([sx0 - rr, sy0 - rr, sx0 + rr, sy0 + rr],
                             fill=(p["color"][0], p["color"][1], p["color"][2], aa))

            # title fade
            if t_out < 3.4:
                alpha = 255 if t_out < 2.8 else int(255 * max(0.0, 1 - (t_out - 2.8) / 0.6))
                alpha = (alpha // 32) * 32
                if alpha > 0:
                    title = tc.get("土豆跌落\n每次都会更大", "title", (255, 255, 255, alpha), 0, 18)
                    frame.paste(title, ((W - title.width) // 2, 92), title)

            # end card
            if s > SEGMENTS[-1][1] + 1.2:
                a = clamp((s - (SEGMENTS[-1][1] + 1.2)) / 0.8, 0, 1)
                frame = Image.blend(frame, Image.new("RGB", (W, H), (0, 0, 0)), 0.45 * a)

            if fi in save_idx:
                frame.save(QA / f"frame_{fi:05d}.jpg", quality=92)
            proc.stdin.write(frame.tobytes())
            if fi % 120 == 0:
                print(f"  render {fi}/{n_frames}  t={t_out:5.2f}s  src={s:5.2f}s  foc={foc}  zoom={zoom:.2f}", flush=True)

    finally:
        if proc.stdin:
            proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "ignore") if proc.stderr else ""
        rc = proc.wait()
        if rc != 0:
            print("ffmpeg failed:\n", err[-3000:])
            raise RuntimeError("ffmpeg failed")

    print(f"silent: {silent}  {OUT_END:.2f}s")
    return silent


def mux(silent, wav, final):
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(silent), "-i", str(wav),
        "-c:v", "copy",
        "-af", "loudnorm=I=-14:TP=-2.0:LRA=11,alimiter=level=0:limit=0.65",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-shortest", "-movflags", "+faststart", str(final),
    ]
    subprocess.run(cmd, check=True)
    print(f"final: {final}")


def contact_sheet():
    frames = sorted(QA.glob("frame_*.jpg"))
    if not frames:
        return
    thumbs = []
    for f in frames[:8]:
        im = Image.open(f).convert("RGB")
        im.thumbnail((360, 640), Image.Resampling.LANCZOS)
        thumbs.append((f.name, im))
    cols = 4
    rows = math.ceil(len(thumbs) / cols)
    cw, ch = 380, 690
    sheet = Image.new("RGB", (cols * cw, rows * ch), (12, 12, 12))
    d = ImageDraw.Draw(sheet)
    for i, (name, im) in enumerate(thumbs):
        x = (i % cols) * cw + 10
        y = (i // cols) * ch + 10
        sheet.paste(im, (x + (360 - im.width) // 2, y))
        d.text((x + 8, y + 650), name, fill=(220, 220, 220))
    sheet.save(QA / "contact_sheet.jpg", quality=90)
    print("contact sheet:", QA / "contact_sheet.jpg")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=0)
    ap.add_argument("--skip-assets", action="store_true")
    args = ap.parse_args()

    if not args.skip_assets or not BG.exists():
        make_bg()
    if not args.skip_assets or not SHADOW.exists():
        make_soft()

    print(f"steps={STEPS} source={SOURCE_END:.2f}s output={OUT_END:.2f}s")
    silent = render()
    wav = AUDIO / "mix.wav"
    synth_audio(IMPACTS, OUT_END, wav)
    final = OUT / "potato_staircase_test.mp4"
    mux(silent, wav, final)
    contact_sheet()
    print("done.")


if __name__ == "__main__":
    main()
