# -*- coding: utf-8 -*-
"""Add the speed ladder + pause variant to the listening set."""
from pathlib import Path
import sys
import numpy as np
import wave
sys.path.insert(0, str(Path(r"E:\program\1project\video\work\voice-noise-20261106")))
from analyze import read_wav
from stretch_cmp import metrics

WORK = Path(r"E:\program\1project\video\work\tts-next-20261106")
OUT = WORK / "out" / "listen"

CLIPS = [
    ("05_cv_speed095", WORK / "out/cv_s095.wav", "CosyVoice3 speed=0.95（16.1s）"),
    ("06_cv_speed090", WORK / "out/cv_s090.wav", "CosyVoice3 speed=0.90（16.3s）"),
    ("07_cv_speed085", WORK / "out/cv_s085.wav", "CosyVoice3 speed=0.85（18.6s）"),
    ("08_cv_pause", WORK / "out/cv_pause.wav", "CosyVoice3 原速逐句 + 句间 0.55s 停顿（20.7s，3.38 字/秒）"),
]


def write(path, y, sr):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())


def gain_to(y, target_db=-21.0):
    rms = np.sqrt(np.mean(y ** 2)) + 1e-12
    return y * (10 ** (target_db / 20) / rms)


rows = []
for name, src, desc in CLIPS:
    y, sr = read_wav(src)
    y = gain_to(y)
    dst = OUT / f"{name}.wav"
    write(dst, y, sr)
    m = metrics(str(dst))
    rows.append((name, dst, desc, m))
    print(f"{name:20s} {m['dur']:.2f}s inr={m['inr_mean']:.3f} flux90={m['flux_p90']:.2f}")

html = ["<!doctype html><meta charset='utf-8'><title>CosyVoice 减速方案</title>",
        "<style>body{background:#12161c;color:#e8eef6;font:15px/1.65 system-ui,'Microsoft YaHei';max-width:960px;margin:36px auto;padding:0 20px}",
        "h1{font-size:21px;font-weight:600}.lead{color:#9fb0c3;margin-bottom:22px}",
        ".clip{margin:16px 0;padding:14px 18px;background:#1b222c;border-radius:10px;border-left:3px solid #2e3b4a}",
        ".name{font-weight:600;color:#ffd27d}.desc{color:#9fb0c3;margin:3px 0 6px;font-size:13.5px}",
        ".m{color:#6f8095;font-size:12px;margin-bottom:8px}audio{width:100%}</style>",
        "<h1>CosyVoice3 · 把 02 放慢的四种方式</h1>",
        "<div class='lead'>02 的音质保持不变，只改节奏。先听 08（逐句原速 + 句间停顿），再对比 05–07（原生 speed）。"
        "重点听：<b>有没有电音/沙沙</b>、<b>前后鼻音</b>、<b>句间停顿是否自然</b>。</div>"]
for name, p, desc, m in rows:
    html.append(f"<div class='clip'><div class='name'>{name}</div><div class='desc'>{desc}</div>"
                f"<div class='m'>谐波间噪声 {m['inr_mean']:.3f} · 通量 p90 {m['flux_p90']:.2f}</div>"
                f"<audio controls preload='none' src='{p.name}'></audio></div>")
(OUT / "slow.html").write_text("\n".join(html), encoding="utf-8")
print("HTML ->", OUT / "slow.html")
