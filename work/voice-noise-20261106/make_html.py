# -*- coding: utf-8 -*-
"""Regenerate the A/B HTML page from the clips in ab/ with measured metrics."""
from __future__ import annotations
from pathlib import Path
import numpy as np
from analyze import read_wav

AB = Path(r"E:\program\1project\video\work\voice-noise-20261106\ab")
DESC = {
    "01_prod_atempo_s10": ("当前生产版", "轻语 prompt + 10 步 + atempo。就是冰川/编剧3 成片里的声音。"),
    "02_s20_atempo": ("20 步", "只把推理步数从 10 提到 20，其余不变。"),
    "03_s30_atempo": ("30 步", "步数 30，其余不变。"),
    "04_p1_refprompt_atempo": ("原版参考音 prompt", "改用 2026-10-02 批准的原始 16s 参考音当 prompt，20 步。"),
    "05_p2_denprompt_atempo": ("轻语 prompt 先降噪", "对轻语 prompt 做频谱降噪后再克隆，20 步。"),
    "06_s20_rubberband": ("rubberband 变速", "20 步，变速器换成 rubberband（替代 atempo）。"),
    "07_s20_atempo_finish": ("20 步 + 后期链", "高通 55Hz + 去齿音 + 气息门（−38 dB 以下压 18 dB）。"),
    "08_p1_atempo_finish": ("原版 prompt + 后期链", "原版参考音 prompt，20 步，加同一条后期链。"),
    "09_prod_denoise_finish": ("现有成片只做后期", "不重新生成，只对当前生产版做频谱降噪 + 后期链。验证能否救回已交付的声音。"),
}
ORDER = list(DESC)


def metrics(p):
    y, sr = read_wav(p)
    rms = 20 * np.log10(np.sqrt(np.mean(y ** 2)) + 1e-12)
    # inter-harmonic noise proxy: energy above 6k + spectral flatness
    n = 4096
    seg = y[len(y)//2: len(y)//2 + 2*sr]
    if len(seg) < n:
        seg = np.pad(seg, (0, n - len(seg)))
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
    fr = np.fft.rfftfreq(len(seg), 1/sr)
    hf = 100 * spec[fr >= 6000].sum() / (spec.sum() + 1e-20)
    flat = float(np.exp(np.mean(np.log(spec + 1e-30))) / (np.mean(spec) + 1e-30))
    return len(y)/sr, rms, hf, flat


rows = []
for name in ORDER:
    p = AB / f"{name}.wav"
    if not p.exists():
        continue
    dur, rms, hf, flat = metrics(p)
    rows.append((name, p, DESC[name], dur, rms, hf, flat))

html = ["<!doctype html><meta charset='utf-8'><title>助眠声线 A/B</title>",
        "<style>body{background:#12161c;color:#e8eef6;font:15px/1.65 system-ui,'Microsoft YaHei';max-width:960px;margin:36px auto;padding:0 20px}",
        "h1{font-size:21px;font-weight:600;margin-bottom:6px}.lead{color:#9fb0c3;margin-bottom:26px}",
        ".clip{margin:20px 0;padding:14px 18px;background:#1b222c;border-radius:10px;border-left:3px solid #2e3b4a}",
        ".name{font-weight:600;color:#ffd27d}.desc{color:#9fb0c3;margin:3px 0 8px;font-size:13.5px}",
        ".m{color:#6f8095;font-size:12px;margin-bottom:8px}audio{width:100%}</style>",
        "<h1>助眠解说 · 同一句声线对比</h1>",
        "<div class='lead'>文本：其中一片雪花，旋转着，穿过安静的空气，最后落在山坡上。<br>"
        "全部按生产口径裁剪、变速、统一到约 −21 dBFS RMS。戴耳机听换气、齿音、金属感，选一个最不“机器”的。</div>"]
for name, p, (title, desc), dur, rms, hf, flat in rows:
    html.append(
        f"<div class='clip'><div class='name'>{name[:2]} · {title}</div>"
        f"<div class='desc'>{desc}</div>"
        f"<div class='m'>时长 {dur:.2f}s · RMS {rms:.1f} dBFS · 6k+ 能量 {hf:.2f}% · 频谱平坦度 {flat:.5f}</div>"
        f"<audio controls preload='none' src='{p.name}'></audio></div>")
html.append("<p style='color:#6f8095;font-size:12.5px'>注：指标只作参考，最终以听感为准。"
            "“6k+ 能量”越低越不刺；“频谱平坦度”越高越像噪声。</p>")
(AB / "index.html").write_text("\n".join(html), encoding="utf-8")
print("HTML ->", AB / "index.html", f"({len(rows)} clips)")
