#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G1 驱动：跑全部变体，导出调试视频 / 连续帧条带 / 数值日志 / 报告。

用法：
    python -m phys.g1                 # 全跑
    python -m phys.g1 --only D        # 只跑一个
    python -m phys.g1 --no-video      # 只出数值
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from phys.scene import Scene, VARIANTS, DIAGNOSTICS     # noqa: E402
from phys.sim import simulate                            # noqa: E402
from phys.view import (World, render_frames, encode_video,   # noqa: E402
                       make_strip, make_overview)

OUT = BASE / "g1"


def slim(res: dict) -> dict:
    """去掉 trace 再落盘（trace 太大）。"""
    return {k: v for k, v in res.items() if k != "trace"}


def run(sc: Scene, video: bool = True) -> dict:
    t0 = time.time()
    d = OUT / sc.key
    d.mkdir(parents=True, exist_ok=True)
    res = simulate(sc)
    (d / "log.json").write_text(json.dumps(slim(res), ensure_ascii=False, indent=2),
                                encoding="utf-8")
    w = World(sc)     # 只为渲染几何
    if video:
        fdir = d / "frames"
        if fdir.exists():
            shutil.rmtree(fdir)
        n = render_frames(w, res, fdir)
        encode_video(fdir, d / "debug.mp4")
        shutil.rmtree(fdir)
        for j, ev in enumerate(res["impacts"][:4]):
            make_strip(w, res, ev, d / f"strip_{j + 1:02d}.jpg")
        make_overview(w, res, d / "overview.jpg")
        print(f"  {sc.key}: {n} frames, {time.time() - t0:.1f}s")
    return res


def table_row(sc: Scene, res: dict) -> str:
    drift = max(d["drift"] for d in res["idle_drift"])
    hits = res["impacts"]
    recv = [round(e["post"][1], 1) for e in hits[:3]]
    sep = ["-" if e["sep_dt"] is None else f"{e['sep_dt']:.2f}" for e in hits[:3]]
    verdict = "通过" if res["pass"] else "未通过"
    return (f"| {sc.key} | {sc.label} | {sc.slope_deg:.0f}°/{sc.lip_h:.0f}px | "
            f"{drift:.2f}px | {len(hits)} | {recv} | {sep} | "
            f"{res['max_penetration']:+.2f}px | {res['slip_mean']} | "
            f"{len(res['cross_step'])} | {res['duration']:.1f}s | {verdict} |")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--diag", action="store_true")
    a = ap.parse_args()
    keys = [k.upper() for k in a.only.split(",") if k]

    results = {}
    for sc in VARIANTS:
        if keys and sc.key not in keys:
            continue
        print(f"[{sc.key}] {sc.label}  W={sc.step_w} H={sc.step_h} r={sc.radii} "
              f"slope={sc.slope_deg}° lip={sc.lip_h}")
        results[sc.key] = run(sc, video=not a.no_video)

    if a.diag or not keys:
        for sc in DIAGNOSTICS:
            r = simulate(sc)
            results[sc.key] = r
            (OUT / f"{sc.key}_diag.json").write_text(
                json.dumps(slim(r), ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[{sc.key}] {sc.label}: drift="
                  + ", ".join(f"P{d['idx']}={d['drift']:.1f}px" for d in r["idle_drift"]))

    (OUT / "summary.json").write_text(
        json.dumps({k: slim(v) for k, v in results.items()}, ensure_ascii=False, indent=2),
        encoding="utf-8")


if __name__ == "__main__":
    main()
