# -*- coding: utf-8 -*-
"""Build de-breath variants (mute / soften) and measure."""
import sys
from pathlib import Path
from analyze import read_wav
from build_ab import trim, write, stretch, gain_to
from finish import finish
from debreath import apply_events
from breath2 import detect
from stretch_cmp import metrics

WORK = Path(r"E:\program\1project\video\work\voice-noise-20261106")
OUT = WORK / "ab_long"
CASES = [
    ("L11_orig10_mute", "tts-probe4/orig_s10_seed7.wav", "mute"),
    ("L12_orig10_soft", "tts-probe4/orig_s10_seed7.wav", "soften"),
    ("L13_cur_mute", "tts-probe3/cur_s10.wav", "mute"),
]

for name, src, mode in CASES:
    y, sr = read_wav(WORK / src)
    y = trim(y, sr)
    evs, *_ = detect(y, sr)
    total = sum(e["dur"] for e in evs)
    print(f"{name}: {len(evs)} events, {total:.2f}s")
    y = apply_events(y, sr, evs, mode)
    p = OUT / f"_{name}_trim.wav"
    write(p, y, sr)
    y, sr = stretch(p, OUT / f"_{name}_stretch.wav", "atempo")
    p.unlink(missing_ok=True)
    y = gain_to(y, -21.0)
    dst = OUT / f"{name}.wav"
    write(dst, y, sr)
    finish(dst, dst)
    y, sr = read_wav(dst)
    y = gain_to(y, -21.0)
    write(dst, y, sr)
    print(name, round(len(y) / sr, 2), metrics(str(dst)))
