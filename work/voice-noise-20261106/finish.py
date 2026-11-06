# -*- coding: utf-8 -*-
"""Finishing chain for sleep-line narration: HPF -> de-ess -> breath gate -> RMS match.

Breath gate: frames quieter than GATE_DB (relative to speech) get pulled down by GATE_GAIN,
with smooth attack/release, so faint synthetic inhales disappear but sentence tails survive.
"""
from __future__ import annotations
import subprocess, sys, wave
from pathlib import Path
import numpy as np
from analyze import read_wav

FF = "ffmpeg"
GATE_DB = -38.0
GATE_GAIN_DB = -18.0
ATTACK = 0.02
RELEASE = 0.08


def write(path, y, sr):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())


def ff_filter(src, dst, afilter):
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
                    "-filter:a", afilter, "-acodec", "pcm_s16le", str(dst)], check=True)


def breath_gate(y, sr, gate_db=GATE_DB, gain_db=GATE_GAIN_DB, attack=ATTACK, release=RELEASE):
    hop = int(0.005 * sr)
    m = len(y) // hop
    frames = y[: m * hop].reshape(m, hop)
    rms = np.sqrt(np.mean(frames ** 2, axis=1)) + 1e-12
    db = 20 * np.log10(rms)
    g = np.ones(m)
    g[db < gate_db] = 10 ** (gain_db / 20)
    # smooth (attack when closing, release when opening)
    for i in range(1, m):
        a = attack if g[i] < g[i - 1] else release
        k = min(1.0, (0.005 / a))
        g[i] = g[i - 1] + (g[i] - g[i - 1]) * k
    gain = np.repeat(g, hop)
    out = y.copy()
    out[:len(gain)] *= gain
    return out


def finish(src, dst, gate=True, attack=ATTACK, release=RELEASE, gain_db=GATE_GAIN_DB, gate_db=GATE_DB):
    tmp1 = Path(str(dst) + ".hp.wav")
    ff_filter(src, tmp1, "highpass=f=55,deesser=i=0.35:m=0.5:f=0.5")
    y, sr = read_wav(tmp1)
    if gate:
        y = breath_gate(y, sr, gate_db=gate_db, gain_db=gain_db)
    write(dst, y, sr)
    tmp1.unlink(missing_ok=True)
    print("finished", dst, f"{len(y)/sr:.2f}s gate={gate}")


if __name__ == "__main__":
    for pair in sys.argv[1:]:
        src, dst = pair.split("=", 1)
        finish(src, dst)
