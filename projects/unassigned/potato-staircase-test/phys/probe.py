#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速数值探针：只跑仿真、打印指标，不渲染。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from phys.scene import Scene, VARIANTS, DIAGNOSTICS   # noqa: E402
from phys.sim import simulate                          # noqa: E402


def summarize(res: dict) -> str:
    sc = res["scene"]
    L = []
    L.append(f"[{sc['key']}] {sc['label']}  slope={sc['slope_deg']}° lip={sc['lip_h']}"
             f"  W={sc['step_w']} H={sc['step_h']} r={sc['radii']}")
    L.append("  rest drift : " + ", ".join(
        f"P{d['idx']}={d['drift']:.2f}px/{d['dangle']:+.3f}rad" for d in res["idle_drift"]))
    L.append(f"  duration   : {res['duration']}s   impacts={res['n_impacts']}")
    for e in res["impacts"]:
        L.append(f"    hit t={e['t']:6.3f}  P{e['a']}-P{e['b']}  J={e['peak_impulse']:7.1f}"
                 f"  relv={e['rel_v']:6.1f}  pre={e['pre']} post={e['post']}"
                 f"  sep={e['sep_dt']}  pen={e['max_pen']}")
    L.append("    landings : " + ", ".join(
        f"P{e['a']}@t{e['t']}tre{e['tread']}" for e in res["landings"][:16]))
    L.append(f"  max pen    : {res['max_penetration']}px @t={res['max_penetration_at']}")
    L.append(f"  slip mean/max: {res['slip_mean']} / {res['slip_max']}  (n={res['slip_samples']})")
    L.append(f"  checks     : " + " | ".join(
        f"{'OK ' if c['ok'] else 'NG '}{c['name']}={c['v']}" for c in res["checks"]))
    L.append(f"  PASS       : {res['pass']}   chain_ok={res['chain_ok']}"
             f"  cross_step={res['cross_step']}")
    return "\n".join(L)


def main():
    args = [a.upper() for a in sys.argv[1:]]
    diag = "DIAG" in args
    keys = [a for a in args if a != "DIAG"]
    if diag:
        for sc in DIAGNOSTICS:
            if keys and sc.key not in keys:
                continue
            r = simulate(sc)
            print(f"[{sc.key}] {sc.label}: drift="
                  + ", ".join(f"P{d['idx']}={d['drift']:.1f}px" for d in r["idle_drift"])
                  + f"  impacts={r['n_impacts']}")
        return
    for sc in VARIANTS:
        if keys and sc.key not in keys:
            continue
        print(summarize(simulate(sc)))
        print()


if __name__ == "__main__":
    main()
