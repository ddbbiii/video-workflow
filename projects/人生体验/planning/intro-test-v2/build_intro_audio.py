# -*- coding: utf-8 -*-
"""Build the 7.2 s intro audio: SFX bed + hits + narration.

Reads VO from planning/intro-test-v2/vo-final/ and writes:
  intro_mix.wav   full mix (48 kHz stereo)
  vo_only.wav     narration only, for the title-VO gate

No external SFX library; all beds/hits are synthesized so there is no licensing
question and no reuse of the reference track.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly

SR = 48000
DUR = 8.43
N = int(SR * DUR)
T = np.arange(N, dtype=np.float32) / SR
RNG = np.random.default_rng(20261110)

ROOT = Path(r"E:\program\1project\video")
VO = ROOT / "projects" / "人生体验" / "planning" / "intro-test-v2" / "vo-b2-full"
OUT = ROOT / "projects" / "人生体验" / "planning" / "intro-test-v2"


def lp(x: np.ndarray, fc: float, order: int = 2) -> np.ndarray:
    sos = butter(order, fc / (SR / 2), btype="low", output="sos")
    return sosfilt(sos, x).astype(np.float32)


def hp(x: np.ndarray, fc: float, order: int = 2) -> np.ndarray:
    sos = butter(order, fc / (SR / 2), btype="high", output="sos")
    return sosfilt(sos, x).astype(np.float32)


def bp(x: np.ndarray, lo: float, hi: float) -> np.ndarray:
    sos = butter(2, [lo / (SR / 2), hi / (SR / 2)], btype="band", output="sos")
    return sosfilt(sos, x).astype(np.float32)


def env_ad(n: int, attack: float, decay: float) -> np.ndarray:
    t = np.arange(n, dtype=np.float32) / SR
    return (np.minimum(1.0, t / max(attack, 1e-4)) * np.exp(-t / max(decay, 1e-4))).astype(np.float32)


def place(buf: np.ndarray, sig: np.ndarray, at: float, gain: float = 1.0, pan: float = 0.0) -> None:
    i = int(round(at * SR))
    if i >= len(buf):
        return
    n = min(len(sig), len(buf) - i)
    if n <= 0:
        return
    pan = max(-1.0, min(1.0, pan))
    l = math.cos((pan + 1) * math.pi / 4)
    r = math.sin((pan + 1) * math.pi / 4)
    buf[i:i + n, 0] += sig[:n] * gain * l
    buf[i:i + n, 1] += sig[:n] * gain * r


def impact(size: float = 1.0, f0: float = 52.0) -> np.ndarray:
    dur = 1.1
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    f = f0 * np.exp(-t * 1.6)
    sub = np.sin(2 * np.pi * f * t) * np.exp(-t * 5.5)
    crack = bp(RNG.standard_normal(n).astype(np.float32), 800, 3800) * np.exp(-t * 30)
    metal = (np.sin(2 * np.pi * 880 * t) + 0.55 * np.sin(2 * np.pi * 1320 * t)) * np.exp(-t * 4.5)
    return (sub + 0.12 * crack + 0.14 * metal) * size


def riser(dur: float, f_start: float = 120.0, f_end: float = 900.0) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    ramp = (t / dur) ** 2
    noise = bp(RNG.standard_normal(n).astype(np.float32), 500, 3200) * ramp * 0.022
    sweep = np.sin(2 * np.pi * (f_start * t + (f_end - f_start) * t * t / (2 * dur))) * ramp * 0.050
    return (noise + sweep).astype(np.float32)


def read_vo(path: Path) -> np.ndarray:
    x, sr = sf.read(str(path), dtype="float32", always_2d=False)
    if x.ndim > 1:
        x = x.mean(axis=1)
    if sr != SR:
        x = resample_poly(x, SR, sr).astype(np.float32)
    # trim low-level head/tail
    win = int(0.02 * SR)
    frames = [np.max(np.abs(x[i:i + win])) for i in range(0, len(x) - win + 1, win)]
    thr = 10 ** (-45 / 20)
    idx = [i for i, v in enumerate(frames) if v > thr]
    if idx:
        a = max(0, idx[0] * win - int(0.03 * SR))
        b = min(len(x), idx[-1] * win + win + int(0.05 * SR))
        x = x[a:b]
    x = x - np.mean(x)
    rms = float(np.sqrt(np.mean(x ** 2)) + 1e-9)
    x = x * (0.28 / rms)
    fade = int(0.012 * SR)
    x[:fade] *= np.linspace(0, 1, fade)
    x[-fade:] *= np.linspace(1, 0, fade)
    return x.astype(np.float32)


def main() -> int:
    bed = np.zeros((N, 2), dtype=np.float32)
    hits = np.zeros((N, 2), dtype=np.float32)
    voice = np.zeros((N, 2), dtype=np.float32)

    # ---- room tone / wind ----
    wind = lp(RNG.standard_normal(N).astype(np.float32), 320)
    wind = wind / (np.max(np.abs(wind)) + 1e-9)
    wind *= 0.012 * (0.75 + 0.25 * np.sin(2 * np.pi * 0.13 * T))
    bed[:, 0] += wind
    bed[:, 1] += np.roll(wind, 137)
    # 开场 36 Hz 低频，避免 0–0.5 s 太静
    sub0 = 0.022 * np.sin(2 * np.pi * 36 * T) * np.clip(T / 0.25, 0, 1)
    bed[:, 0] += sub0
    bed[:, 1] += sub0

    # ---- prelude: ticks, flips, riser, impact ----
    place(hits, impact(0.35, 44), 0.0, 0.32)
    place(bed, riser(0.35, 80, 260), 0.02, 0.45)
    for k in range(int(1.8 * 12)):
        n = int(0.035 * SR)
        tt = np.arange(n, dtype=np.float32) / SR
        tick = np.sin(2 * np.pi * 2100 * tt) * np.exp(-tt * 120)
        place(bed, tick, k / 12, 0.03, pan=(-0.5 if k % 2 else 0.5))
    for k in range(8):
        at = 0.18 + k * 0.22
        n = int(0.14 * SR)
        flip = bp(RNG.standard_normal(n).astype(np.float32), 1100, 5200) * env_ad(n, 0.004, 0.05)
        place(bed, flip, at, 0.05, pan=(-0.7 if k % 2 else 0.7))
    place(bed, riser(1.0, 110, 820), 0.70, 0.30)
    place(hits, impact(0.8, 54), 1.70, 0.40)

    # ---- main drone ----
    drone_env = np.clip((T - 1.7) / 0.5, 0, 1) * np.clip((DUR - T) / 0.5, 0, 1)
    drone = (0.040 * np.sin(2 * np.pi * 42 * T)
             + 0.024 * np.sin(2 * np.pi * 84 * T)
             + 0.018 * lp(RNG.standard_normal(N).astype(np.float32), 110))
    drone *= drone_env
    bed[:, 0] += drone
    bed[:, 1] += drone

    # ---- main riser into the hook ----
    place(bed, riser(0.95, 85, 320), 2.35, 0.55)

    # ---- three impact hits ----
    for at, size, f0 in ((3.60, 0.55, 58), (4.00, 0.62, 52), (4.40, 0.75, 46)):
        place(hits, impact(size, f0), at, 0.60)
        # static crack around the hit
        n = int(0.10 * SR)
        st = bp(RNG.standard_normal(n).astype(np.float32), 2000, 6000) * env_ad(n, 0.002, 0.035)
        place(hits, st, at - 0.02, 0.04, pan=0.3)

    # ---- tape stop / settle at 4.45–4.80 ----
    n = int(0.35 * SR)
    tt = np.arange(n, dtype=np.float32) / SR
    stop = np.sin(2 * np.pi * (200 * np.exp(-tt * 5.5)) * tt) * np.exp(-tt * 4)
    place(hits, stop, 4.45, 0.12)

    # ---- heartbeat after settle ----
    for at in (4.85, 5.70, 6.55, 7.40, 8.25):
        n = int(0.22 * SR)
        tt = np.arange(n, dtype=np.float32) / SR
        thump = np.sin(2 * np.pi * 52 * tt) * np.exp(-tt * 12)
        place(bed, thump, at, 0.07)

    # ---- final soft boom at the end of chapter card ----
    place(hits, impact(0.55, 44), 8.0, 0.35)

    # ---- narration ----
    vo_specs = [
        ("line1-world.wav", 0.30),
        ("line2-empty.wav", 3.30),
        ("line3-level.wav", 6.10),
    ]
    for name, at in vo_specs:
        x = read_vo(VO / name)
        place(voice, x, at, 1.0, pan=0.0)

    # simple plate-ish reverb on voice
    rev = np.zeros_like(voice)
    for delay, gain in ((0.07, 0.12), (0.13, 0.07), (0.21, 0.04)):
        d = int(delay * SR)
        rev[d:, 0] += voice[:-d, 0] * gain
        rev[d:, 1] += voice[:-d, 1] * gain
    rev = lp(rev[:, 0], 5000)[:, None] * np.array([[0.9, 0.9]])
    voice = voice + rev.astype(np.float32)

    # ---- sidechain duck bed/hits under narration ----
    env = np.abs(voice).max(axis=1)
    k = int(0.05 * SR)
    env = np.convolve(env, np.ones(k, dtype=np.float32) / k, mode="same")
    env = np.clip(env / 0.08, 0, 1)[:, None]
    bed *= (1.0 - 0.55 * env) * 0.38
    hits *= (1.0 - 0.35 * env) * 0.90

    bed = np.stack([lp(bed[:, 0], 12000), lp(bed[:, 1], 12000)], axis=1)
    hits = np.stack([lp(hits[:, 0], 12000), lp(hits[:, 1], 12000)], axis=1)
    voice = np.stack([lp(voice[:, 0], 14000), lp(voice[:, 1], 14000)], axis=1)

    mix = voice + bed + hits
    mix = np.tanh(mix * 1.15) / np.tanh(1.15)
    mix *= 0.95 / max(float(np.max(np.abs(mix))), 1e-9)

    sf.write(str(OUT / "intro_mix.wav"), mix, SR, subtype="PCM_16")
    sf.write(str(OUT / "vo_only.wav"), voice, SR, subtype="PCM_16")
    print("wrote", OUT / "intro_mix.wav", "peak", round(float(np.max(np.abs(mix))), 3))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
