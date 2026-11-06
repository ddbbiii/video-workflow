# -*- coding: utf-8 -*-
"""Batch scan all VO wavs: level, noise floor, HF ratio, flatness; rank outliers."""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
from analyze import read_wav

ROOT = Path(r"E:\program\1project\video\4\audio")


def metrics(path: Path):
    y, sr = read_wav(path)
    if y.size == 0:
        return None
    n = max(1, int(sr * 0.02))
    m = len(y) // n
    r = np.sqrt(np.mean(y[: m * n].reshape(m, n) ** 2, axis=1)) if m else np.array([0.0])
    rdb = 20 * np.log10(np.maximum(r, 1e-12))
    peak = float(np.abs(y).max())
    clip = int(np.sum(np.abs(y) >= 0.999))
    zero_frac = float(np.mean(y == 0.0))
    # HF ratio via 2nd difference energy proxy + FFT on a middle 2s window
    mid = y[len(y)//2: len(y)//2 + 2*sr]
    if len(mid) < 4096:
        mid = np.pad(mid, (0, 4096 - len(mid)))
    spec = np.abs(np.fft.rfft(mid * np.hanning(len(mid)))) ** 2
    fr = np.fft.rfftfreq(len(mid), 1 / sr)
    tot = spec.sum() + 1e-20
    hf = float(spec[(fr >= 6000)].sum() / tot)
    flat = float(np.exp(np.mean(np.log(spec + 1e-30))) / (np.mean(spec) + 1e-30))
    return {
        "file": path.name, "dur": round(len(y)/sr, 2), "peak_db": round(20*np.log10(max(peak,1e-12)), 2),
        "rms_db": round(20*np.log10(max(np.sqrt(np.mean(y**2)),1e-12)), 2),
        "p5_db": round(float(np.percentile(rdb, 5)), 1),
        "p50_db": round(float(np.percentile(rdb, 50)), 1),
        "clip": clip, "zero_frac": round(zero_frac, 4),
        "hf6k": round(hf, 6), "flat": round(flat, 6),
    }


def main():
    rows = []
    for d in ("vo-raw/lightexpr-seed7", "vo-processed/lightexpr-seed7"):
        for p in sorted((ROOT / d).glob("*.wav")):
            mm = metrics(p)
            if mm:
                mm["set"] = d.split("/")[0]
                rows.append(mm)
    out = ROOT.parent / "runs" / "20261103-gla-b01" / "logs" / "vo_noise_scan.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"scanned {len(rows)} -> {out}")
    for key in ("flat", "hf6k", "peak_db"):
        s = sorted(rows, key=lambda r: r[key], reverse=True)[:12]
        print(f"\n-- top {key} --")
        for r in s:
            print(f"  {r['set']:12s} {r['file']:22s} flat={r['flat']:.5f} hf6k={r['hf6k']:.4f} peak={r['peak_db']:.1f} p5={r['p5_db']} clip={r['clip']} zero={r['zero_frac']}")


if __name__ == "__main__":
    main()
