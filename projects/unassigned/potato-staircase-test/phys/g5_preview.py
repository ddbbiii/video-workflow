#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G5 预演（只出数值）：把 G1 配方扩到 10 个土豆，看被动接力能走多远。

结论会写进 G1_REPORT.md：主要用来回答“纯物理能不能撑满 10 级”。
"""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from phys.scene import VARIANTS          # noqa: E402
from phys.sim import simulate            # noqa: E402

base = next(v for v in VARIANTS if v.key == "D")


def run(n=10, w=200.0, frac=0.985, push=180.0, step_h=150.0):
    radii = tuple(24.0 + i * (62.5 - 24.0) / (n - 1) for i in range(n))
    sc = replace(base, n_potato=n, radii=radii, step_w=w, step_h=step_h,
                 x0=90.0, y0=380.0, rail_x=90.0 + (n + 1) * w + 240.0,
                 receiver_frac=frac, push_v=push)
    r = simulate(sc, t_max=95.0)
    return sc, r


def main():
    out = {}
    for w, frac in [(200.0, 0.985), (200.0, 0.97), (175.0, 0.985)]:
        sc, r = run(w=w, frac=frac)
        links = sum(1 for p in r["relay_pairs"] if p["hit"])
        out[f"W{w}_frac{frac}"] = {
            "w": w, "frac": frac, "n_potato": sc.n_potato,
            "radii": [round(x, 1) for x in sc.radii],
            "links": links, "hits": r["n_impacts"], "duration": r["duration"],
            "pass": r["pass"],
            "land_seq": {i: sorted(set(v)) for i, v in r["land_seq"].items()},
            "recv_peak": [round(e["post"][1], 1) for e in r["impacts"]],
            "fails": [c["name"] for c in r["checks"] if not c["ok"]],
        }
        print(f"W={w} frac={frac}: {links}/9 links, hits={r['n_impacts']}, "
              f"dur={r['duration']:.1f}s, pass={r['pass']}")
        print(f"   seq={out[f'W{w}_frac{frac}']['land_seq']}")
        print(f"   recv_peak={out[f'W{w}_frac{frac}']['recv_peak']}")
    (BASE / "g1" / "g5_preview.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
