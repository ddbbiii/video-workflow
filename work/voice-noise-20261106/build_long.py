# -*- coding: utf-8 -*-
"""Build the long-paragraph A/B page (current recipe vs original-prompt recipe)."""
from __future__ import annotations
import shutil
from pathlib import Path
import numpy as np
from analyze import read_wav
from build_ab import trim, write, stretch, gain_to
from finish import finish
from stretch_cmp import metrics

WORK = Path(r"E:\program\1project\video\work\voice-noise-20261106")
SRC = WORK / "tts-probe3"
OUT = WORK / "ab_long"
OUT.mkdir(parents=True, exist_ok=True)

VARIANTS = [
    ("L1_current", "cur_s10", "atempo", False, "当前配方（轻语 prompt + 10 步 + atempo）"),
    ("L2_current_finish", "cur_s10", "atempo", True, "当前配方 + 后期链"),
    ("L3_orig20", "orig_s20", "atempo", False, "原版参考音 prompt + 20 步 + atempo"),
    ("L4_orig20_finish", "orig_s20", "atempo", True, "原版 prompt + 20 步 + 后期链"),
    ("L5_orig20_rubberband", "orig_s20", "rubberband", True, "原版 prompt + 20 步 + rubberband + 后期链"),
]

rows = []
for name, srcname, mode, do_finish, desc in VARIANTS:
    y, sr = read_wav(SRC / f"{srcname}.wav")
    y = trim(y, sr)
    tmp = OUT / f"_{name}_trim.wav"
    write(tmp, y, sr)
    y, sr = stretch(tmp, OUT / f"_{name}_stretch.wav", mode)
    tmp.unlink(missing_ok=True)
    y = gain_to(y, -21.0)
    dst = OUT / f"{name}.wav"
    write(dst, y, sr)
    if do_finish:
        finish(dst, dst)
        y, sr = read_wav(dst)
        y = gain_to(y, -21.0)
        write(dst, y, sr)
    rows.append((name, dst, desc, len(y) / sr, metrics(dst)))
    print(f"{name:24s} {len(y)/sr:5.2f}s  {rows[-1][4]}")

html = ["<!doctype html><meta charset='utf-8'><title>助眠声线长段 A/B</title>",
        "<style>body{background:#12161c;color:#e8eef6;font:15px/1.65 system-ui,'Microsoft YaHei';max-width:960px;margin:36px auto;padding:0 20px}",
        "h1{font-size:21px;font-weight:600}.lead{color:#9fb0c3;margin-bottom:24px}",
        ".clip{margin:20px 0;padding:14px 18px;background:#1b222c;border-radius:10px;border-left:3px solid #2e3b4a}",
        ".name{font-weight:600;color:#ffd27d}.desc{color:#9fb0c3;margin:3px 0 8px;font-size:13.5px}audio{width:100%}</style>",
        "<h1>助眠解说 · 整段对比（77 字 / 4 句）</h1>",
        "<div class='lead'>文本：很远的地方，有一座高山。山脚下或许还有树林，或许还有尚未结冰的溪水。但在山顶，空气已经足够寒冷。"
        "云层贴着山脊缓缓移动，细小的冰晶在云里生长，然后开始落下。<br>"
        "重点听句末换气和“溪水/细小的冰晶”这类气声词。</div>"]
for name, p, desc, dur, m in rows:
    html.append(f"<div class='clip'><div class='name'>{name[:2]} · {desc}</div>"
                f"<div class='desc'>时长 {dur:.2f}s · 谐波间噪声 {m['inr_mean']:.3f}（越低越干净）"
                f" · 频谱通量 p90 {m['flux_p90']:.2f}</div>"
                f"<audio controls preload='none' src='{p.name}'></audio></div>")
(OUT / "index.html").write_text("\n".join(html), encoding="utf-8")
print("HTML ->", OUT / "index.html")
