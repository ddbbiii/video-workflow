# -*- coding: utf-8 -*-
"""Regenerate the long A/B page from existing clips with measured metrics."""
from __future__ import annotations
from pathlib import Path
from stretch_cmp import metrics

AB = Path(r"E:\program\1project\video\work\voice-noise-20261106\ab_long")
DESC = {
    "L1_current": "当前配方：轻语 prompt + 10 步 + atempo（对照基准）",
    "L2_current_finish": "当前音色不动，只加后期链（高通 55 / 去齿音 / 气息门）",
    "L3_orig20": "原版参考音 prompt + 20 步",
    "L4_orig20_finish": "原版 prompt + 20 步 + 后期链",
    "L5_orig20_rubberband": "原版 prompt + 20 步 + rubberband（已知更差，可跳过）",
    "L6_orig10": "原版 prompt + 仍用 10 步（零额外算力）",
    "L7_orig10_finish": "原版 prompt + 10 步 + 后期链（零额外算力 + CPU 收尾）",
    "L15_orig10_slowgate": "原版 prompt + 10 步 + 慢速轻压门（80 ms 攻击 / −10 dB）",
    "L16_orig10_hp_deess": "原版 prompt + 10 步 + 只做高通/去齿音，不压门",
}
ORDER = list(DESC)
rows = []
for name in ORDER:
    p = AB / f"{name}.wav"
    if p.exists():
        rows.append((name, p, DESC[name], metrics(str(p))))

html = ["<!doctype html><meta charset='utf-8'><title>助眠声线长段 A/B</title>",
        "<style>body{background:#12161c;color:#e8eef6;font:15px/1.65 system-ui,'Microsoft YaHei';max-width:960px;margin:36px auto;padding:0 20px}",
        "h1{font-size:21px;font-weight:600}.lead{color:#9fb0c3;margin-bottom:24px}",
        ".clip{margin:18px 0;padding:14px 18px;background:#1b222c;border-radius:10px;border-left:3px solid #2e3b4a}",
        ".name{font-weight:600;color:#ffd27d}.desc{color:#9fb0c3;margin:3px 0 6px;font-size:13.5px}",
        ".m{color:#6f8095;font-size:12px;margin-bottom:8px}audio{width:100%}</style>",
        "<h1>助眠解说 · 整段对比（77 字 / 4 句）</h1>",
        "<div class='lead'>文本：很远的地方，有一座高山。山脚下或许还有树林，或许还有尚未结冰的溪水。但在山顶，空气已经足够寒冷。"
        "云层贴着山脊缓缓移动，细小的冰晶在云里生长，然后开始落下。<br>"
        "重点听句末换气，以及“溪水 / 细小的冰晶”这类气声词。L6/L7 是不增加算力的方案。</div>"]
for name, p, desc, m in rows:
    html.append(f"<div class='clip'><div class='name'>{name}</div><div class='desc'>{desc}</div>"
                f"<div class='m'>时长 {m['dur']:.2f}s · 谐波间噪声 {m['inr_mean']:.3f}（越低越干净）"
                f" · 频谱通量 p90 {m['flux_p90']:.2f}</div>"
                f"<audio controls preload='none' src='{p.name}'></audio></div>")
(AB / "index.html").write_text("\n".join(html), encoding="utf-8")
print("HTML ->", AB / "index.html", len(rows), "clips")
