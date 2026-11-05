#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""参数扫描：push × receiver_frac，输出最精简的一行结论。"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from phys.scene import Scene, VARIANTS          # noqa: E402
from phys.sim import simulate                   # noqa: E402


def line(sc: Scene, res: dict) -> str:
    hits = res["impacts"]
    nx = [round(e["normal"][0], 2) for e in hits[:3]]
    seqs = {i: sorted(set(v)) for i, v in res["land_seq"].items()}
    return (f"push={sc.push_v:5.0f} frac={sc.receiver_frac:.2f} | "
            f"hits={res['n_impacts']} n={res['pass']} "
            f"J={[round(e['peak_impulse']) for e in hits[:3]]} "
            f"nx={nx} post={[p for e in hits[:2] for p in e['post']]} "
            f"dur={res['duration']:5.2f} pen={res['max_penetration']:+.2f} "
            f"seq={seqs} skip={len(res['cross_step'])} "
            f"NG={[c['name'] for c in res['checks'] if not c['ok']]}")


def main():
    keys = sys.argv[1].upper() if len(sys.argv) > 1 else "D"
    pushes = [80, 100, 120, 150, 180]
    fracs = [0.75, 0.82, 0.88]
    for sc in VARIANTS:
        if sc.key not in keys:
            continue
        print(f"--- {sc.key} {sc.label}  W={sc.step_w} H={sc.step_h} r={sc.radii} lip={sc.lip_h}")
        for f in (fracs if sc.lip_h <= 0 else [sc.receiver_frac]):
            for p in pushes:
                s2 = replace(sc, push_v=float(p), receiver_frac=f)
                r = simulate(s2, t_max=14.0)
                print("   " + line(s2, r))


if __name__ == "__main__":
    main()
