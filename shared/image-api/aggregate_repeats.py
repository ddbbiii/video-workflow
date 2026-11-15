# -*- coding: utf-8 -*-
"""Aggregate the repeat samples: per-panel mean / spread and new2-vs-dklnew win rate.

Reads report.json (first pass, 3 channels) + report-repeats.json (samples 2-4,
dkl-new and new2) and writes REPORT-repeats.md plus a grouped bar chart.
"""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RUN = Path(r"E:\program\1project\video\shared\image-api\runs\20261112-114824-dkl3way-2x2")
CH = ["dkl-old", "dkl-new", "new2"]
NAME = {"dkl-old": "DKL 旧 key 0.16", "dkl-new": "DKL 新 key 0.015", "new2": "new2 0.018"}


def font(size: int):
    for path in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\arial.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def collect() -> dict:
    """samples[(prompt, channel)][panel] -> list of delivery lap_var."""
    samples: dict[tuple[str, str], dict[int, list[float]]] = {}
    grid_lap: dict[tuple[str, str], list[float]] = {}

    first = json.loads((RUN / "report.json").read_text(encoding="utf-8"))
    for r in first.get("results", []):
        if not r.get("ok"):
            continue
        key = (r["prompt"], r["channel"])
        grid_lap.setdefault(key, []).append(r["metrics"]["lap_var"])
        for cell in r.get("cells") or []:
            samples.setdefault(key, {}).setdefault(cell["panel"], []).append(
                cell["delivery_lap_var_1080p"])

    repeats = json.loads((RUN / "report-repeats.json").read_text(encoding="utf-8"))
    for r in repeats.get("results", []):
        if not r.get("ok") or not r.get("cells"):
            continue
        key = (r["prompt"], r["channel"])
        for cell in r["cells"]:
            samples.setdefault(key, {}).setdefault(cell["panel"], []).append(
                cell["delivery_lap_var_1080p"])
        grid_lap.setdefault(key, []).append(float("nan"))
    return {"cells": samples, "grid": grid_lap}


def grid_metrics() -> dict:
    """Full-image metrics for every sample, recomputed from the PNGs."""
    out: dict[tuple[str, str], list[dict]] = {}
    paths = []
    first = json.loads((RUN / "report.json").read_text(encoding="utf-8"))
    for r in first.get("results", []):
        if r.get("ok"):
            paths.append(((r["prompt"], r["channel"]), RUN / "raw" / f"{r['channel']}-{r['prompt']}.png"))
    repeats = json.loads((RUN / "report-repeats.json").read_text(encoding="utf-8"))
    for r in repeats.get("results", []):
        if r.get("ok"):
            paths.append(((r["prompt"], r["channel"]),
                          RUN / "raw" / f"{r['channel']}-{r['prompt']}-s{r['sample']}.png"))
    from compare_dkl_new_three import metrics  # noqa: PLC0415
    for key, path in paths:
        if not path.exists():
            continue
        m = metrics(path)
        out.setdefault(key, []).append(m)
    return out


def chart(prompt: str, data: dict[tuple[str, str], dict[int, list[float]]]) -> Path:
    """Grouped bars: mean per panel, error whiskers as min-max."""
    panels = [1, 2, 3, 4]
    chans = ["dkl-old", "dkl-new", "new2"]
    colors = {"dkl-old": (232, 208, 160), "dkl-new": (120, 200, 240), "new2": (150, 230, 160)}
    width, height = 900, 460
    left, right, top, bottom = 70, 20, 50, 60
    plot_h = height - top - bottom
    plot_w = width - left - right
    canvas = Image.new("RGB", (width, height), (18, 18, 22))
    draw = ImageDraw.Draw(canvas)
    means = {c: [st.mean(data[(prompt, c)][p]) for p in panels] for c in chans}
    peak = max(max(v) for v in means.values()) * 1.15
    draw.text((12, 12), f"{prompt} · 每格交付锐度（4 个样本均值，须线=min–max）",
              fill=(235, 235, 235), font=font(18))
    for i in range(5):
        y = top + plot_h - plot_h * i / 4
        draw.line([(left, y), (width - right, y)], fill=(50, 50, 58))
        draw.text((18, y - 8), f"{peak * i / 4:.0f}", fill=(150, 150, 160), font=font(13))
    group_w = plot_w / len(panels)
    bar_w = group_w / (len(chans) + 1)
    for pi, panel in enumerate(panels):
        gx = left + pi * group_w
        for ci, ch in enumerate(chans):
            values = data[(prompt, ch)][panel]
            mean = st.mean(values)
            x0 = gx + bar_w * (ci + 0.5)
            y0 = top + plot_h - plot_h * mean / peak
            x1 = x0 + bar_w * 0.8
            draw.rectangle([x0, y0, x1, top + plot_h], fill=colors[ch])
            lo, hi = min(values), max(values)
            draw.line([(x0 + bar_w * 0.4, top + plot_h - plot_h * lo / peak),
                       (x0 + bar_w * 0.4, top + plot_h - plot_h * hi / peak)],
                      fill=(220, 220, 220), width=1)
            draw.text((x0 + 2, y0 - 16), f"{mean:.0f}", fill=(230, 230, 230), font=font(12))
        draw.text((gx + group_w / 2 - 18, height - 40), f"第 {panel} 格", fill=(200, 200, 205),
                  font=font(14))
    for ci, ch in enumerate(chans):
        draw.rectangle([left + ci * 190, height - 24, left + ci * 190 + 12, height - 12],
                       fill=colors[ch])
        draw.text((left + ci * 190 + 18, height - 28), NAME[ch], fill=(210, 210, 215), font=font(13))
    out = RUN / "compare" / f"stats-{prompt}.png"
    canvas.save(out)
    return out


def main() -> int:
    cells = collect()["cells"]
    grid = grid_metrics()
    lines = ["# 重抽汇总：new2 vs DKL 新 key（每格 4 个样本）", ""]
    lines.append("- 样本：首轮 1 次 + 2026-11-12 12:0x 重抽 3 次；dkl-old 只参与首轮，"
                 "作为质量上限参照。")
    lines.append("- 指标：每格缩到 1920×1080 后的拉普拉斯方差（越高细节越多）。")
    lines.append("")

    for prompt in ("G-grid", "S-grid"):
        lines.append(f"## {prompt}")
        lines.append("")
        lines.append("| 格 | dkl-old（1 样本） | dkl-new 均值±极差 | new2 均值±极差 | 胜负 |")
        lines.append("|---|---|---|---|---|")
        wins = {"dkl-new": 0, "new2": 0}
        for panel in (1, 2, 3, 4):
            old_vals = cells[(prompt, "dkl-old")][panel]
            new_vals = cells[(prompt, "dkl-new")][panel]
            n2_vals = cells[(prompt, "new2")][panel]
            winner = "new2" if st.mean(n2_vals) > st.mean(new_vals) else "dkl-new"
            wins[winner] += 1
            lines.append(
                f"| p{panel} | {st.mean(old_vals):.1f} | "
                f"{st.mean(new_vals):.1f} ±{(max(new_vals) - min(new_vals)):.1f} | "
                f"{st.mean(n2_vals):.1f} ±{(max(n2_vals) - min(n2_vals)):.1f} | {winner} |")
        lines.append("")
        lines.append(f"- 格级胜负：new2 **{wins['new2']} : {wins['dkl-new']}** dkl-new")
        g_new = [m["lap_var"] for m in grid.get((prompt, "dkl-new"), [])]
        g_n2 = [m["lap_var"] for m in grid.get((prompt, "new2"), [])]
        g_old = [m["lap_var"] for m in grid.get((prompt, "dkl-old"), [])]
        lines.append(f"- 整图锐度：dkl-old {st.mean(g_old):.0f} | "
                     f"dkl-new {st.mean(g_new):.0f}（{min(g_new):.0f}–{max(g_new):.0f}） | "
                     f"new2 {st.mean(g_n2):.0f}（{min(g_n2):.0f}–{max(g_n2):.0f}）")
        lines.append(f"- 整图比值 new2 / dkl-new = **{st.mean(g_n2) / st.mean(g_new):.2f}×**")
        lines.append("")
        shot = chart(prompt, cells)
        lines.append(f"![{prompt}]({shot.name})")
        lines.append("")

    (RUN / "REPORT-repeats.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
