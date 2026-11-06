# -*- coding: utf-8 -*-
"""Measure discontinuities at every utterance join in the assembled body narration."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from analyze import read_wav

ROOT = Path(r"E:\program\1project\video")
TL = ROOT / "4/runs/20261103-gla-b01/timeline.json"
WAV = ROOT / "4/runs/20261103-gla-b01/chapters/body_narration.wav"

tl = json.loads(TL.read_text(encoding="utf-8"))
y, sr = read_wav(WAV)
print(f"wav {len(y)/sr:.3f}s sr={sr} timeline body {tl['body_seconds']}s")

rows = []
for u in tl["utterances"]:
    a, b = u["start_sample"], u["end_sample"]
    pre = y[max(0, a - 200):a]           # 4ms before
    post = y[b:b + 200]                  # 4ms after
    head = y[a:a + int(0.02 * sr)]
    tail = y[max(0, b - int(0.02 * sr)):b]
    rows.append(dict(
        id=u["id"],
        start_edge=float(abs(y[a]) if a < len(y) else 0),
        end_edge=float(abs(y[b - 1]) if b - 1 < len(y) else 0),
        head_peak=float(np.abs(head).max()) if len(head) else 0,
        tail_peak=float(np.abs(tail).max()) if len(tail) else 0,
        gap_before=float(np.abs(y[max(0, a - int(0.01 * sr)):a]).max()) if a > 0 else 0,
        gap_after=float(np.abs(y[b:b + int(0.01 * sr)]).max()) if b < len(y) else 0,
    ))

import statistics as st
for k in ("start_edge", "end_edge", "head_peak", "tail_peak", "gap_before", "gap_after"):
    vals = [r[k] for r in rows]
    print(f"{k:12s} max={max(vals):.4f} p99={np.percentile(vals,99):.4f} p50={st.median(vals):.4f}")

print("\n-- top 15 by start_edge --")
for r in sorted(rows, key=lambda r: r["start_edge"], reverse=True)[:15]:
    print(f"  {r['id']:18s} start_edge={r['start_edge']:.4f} head_peak={r['head_peak']:.4f} gap_before={r['gap_before']:.4f}")

print("\n-- top 15 by end_edge --")
for r in sorted(rows, key=lambda r: r["end_edge"], reverse=True)[:15]:
    print(f"  {r['id']:18s} end_edge={r['end_edge']:.4f} tail_peak={r['tail_peak']:.4f} gap_after={r['gap_after']:.4f}")

# click score: |y[a] - y[a-1]| vs local 99th pct of |diff|
d = np.abs(np.diff(y))
print("\n-- top 15 join clicks (diff at boundary / local p99.9) --")
scores = []
for u in tl["utterances"]:
    for idx, side in ((u["start_sample"], "start"), (u["end_sample"] - 1, "end")):
        if idx <= 0 or idx >= len(y):
            continue
        local = d[max(0, idx - int(0.5 * sr)): idx + int(0.5 * sr)]
        base = np.percentile(local, 99.9) if len(local) else 0
        scores.append((float(d[idx - 1] / (base + 1e-9)), u["id"], side, float(d[idx - 1])))
for s, uid, side, dv in sorted(scores, reverse=True)[:15]:
    print(f"  {uid:18s} {side:5s} ratio={s:6.1f} diff={dv:.4f}")
