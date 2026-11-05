#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D 几何上的小网格搜索：接收者位置 / 推力 / 滚动阻力。"""
from __future__ import annotations

import itertools
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from phys.scene import VARIANTS          # noqa: E402
from phys.sim import simulate            # noqa: E402

base = next(v for v in VARIANTS if v.key == "D")

rows = []
for frac, push, rr in itertools.product(
        [0.82, 0.86, 0.90], [130, 165, 200], [0.0, 20.0, 40.0]):
    sc = replace(base, push_v=float(push), receiver_frac=frac, roll_resist=rr)
    r = simulate(sc, t_max=14.0)
    fails = [c["name"] for c in r["checks"] if not c["ok"]]
    rows.append((len(fails), rr, frac, push, r))

rows.sort(key=lambda t: (t[0], t[4]["duration"]))
for nf, rr, frac, push, r in rows:
    hits = r["impacts"]
    recv = [round(e["post"][1], 1) for e in hits[:3]]
    print(f"fails={nf} rr={rr:4.0f} frac={frac} push={push} hits={r['n_impacts']} "
          f"dur={r['duration']:5.2f} recv={recv} seq={{{', '.join(f'{k}:{sorted(set(v))}' for k, v in r['land_seq'].items())}}} "
          f"{[c['name'] for c in r['checks'] if not c['ok']]}")
