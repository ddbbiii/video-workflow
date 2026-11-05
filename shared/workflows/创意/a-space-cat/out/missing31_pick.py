# -*- coding: utf-8 -*-
"""Inventory + heuristic auto-pick for a-space-cat missing31 firstframes."""
from __future__ import annotations
import json, statistics
from pathlib import Path
from PIL import Image, ImageStat
import numpy as np

RAW = Path(r"E:\program\1project\video\shared\runtime\engines\stills-runtime\out\a-space-cat\a-space-cat_missing31_v6")
SHARED = Path(r"E:\program\1project\video\shared\runtime\engines\stills-runtime\stills_comfy_output\stills\a-space-cat")
FF = Path(r"E:\program\1project\video\projects\创意\episodes\a-space-cat\image\firstframes")
OUT = Path(r"E:\program\1project\video\projects\创意\episodes\a-space-cat\qa")
MISSING = [1,5,6,7,11,12,15,16,17,18,20,22,23,24,26,27,28,32,33,35,36,37,39,40,43,44,46,48,49,50,51]
PROTECTED = {2,3,4,8,9,10,13,14,19,21,25,29,30,31,34,38,41,42,45,47}
TARGET = (1080, 1920)

def shot_tag(n: int) -> str:
    return f"s{n:02d}"

def ff_name(n: int) -> str:
    return f"shot{n:02d}.png"

def load_rgb(p: Path) -> Image.Image:
    return Image.open(p).convert("RGB")

def edge_margin_score(img: Image.Image) -> dict:
    """Higher = safer composition (subject not hugging edges).
    Uses luminance mass centroid + edge-band energy.
    """
    arr = np.asarray(img, dtype=np.float32)
    h, w = arr.shape[:2]
    # luminance
    lum = 0.2126 * arr[:,:,0] + 0.7152 * arr[:,:,1] + 0.0722 * arr[:,:,2]
    # subject mask: away from very dark bg + some contrast
    thr = max(30.0, float(np.percentile(lum, 35)))
    mask = lum >= thr
    if mask.sum() < 100:
        mask = lum >= np.percentile(lum, 20)
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return {"margin_min": 0.0, "cx": 0.5, "cy": 0.5, "edge_hug": 1.0, "score": 0.0}
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    left = x0 / w
    right = (w - 1 - x1) / w
    top = y0 / h
    bot = (h - 1 - y1) / h
    margin_min = min(left, right, top, bot)
    cx = float(xs.mean()) / w
    cy = float(ys.mean()) / h
    # edge band occupancy (bad if lots of subject in outer 3%)
    bw = max(2, int(0.03 * w)); bh = max(2, int(0.03 * h))
    edge = np.zeros_like(mask)
    edge[:bh,:] = True; edge[-bh:,:] = True; edge[:,:bw] = True; edge[:,-bw:] = True
    edge_hug = float((mask & edge).sum()) / max(1, float(mask.sum()))
    # prefer centroid near center, good margins, low edge hug
    center_pen = ((cx - 0.5)**2 + (cy - 0.5)**2) ** 0.5
    score = (margin_min * 2.0) + (1.0 - min(1.0, edge_hug * 8.0)) + (1.0 - min(1.0, center_pen * 2.5))
    return {
        "margin_min": round(margin_min, 4),
        "cx": round(cx, 4),
        "cy": round(cy, 4),
        "edge_hug": round(edge_hug, 4),
        "bbox": [x0, y0, x1, y1],
        "score": round(score, 4),
    }

def silver_score(img: Image.Image) -> dict:
    """Prefer silver/gray fur look: low saturation, mid-high value in subject area."""
    arr = np.asarray(img, dtype=np.float32)
    h, w = arr.shape[:2]
    # center crop 50% for subject-ish
    y0, y1 = h//4, 3*h//4
    x0, x1 = w//4, 3*w//4
    c = arr[y0:y1, x0:x1]
    r, g, b = c[:,:,0], c[:,:,1], c[:,:,2]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    sat = np.where(mx > 1e-6, (mx - mn) / mx, 0.0)
    val = mx / 255.0
    # silver-ish mask: sat low, val mid-high
    silverish = (sat < 0.25) & (val > 0.35) & (val < 0.95)
    ratio = float(silverish.mean())
    mean_sat = float(sat.mean())
    mean_val = float(val.mean())
    # also penalize strong warm/brown dominance (orange cat)
    warm = ((r > g + 15) & (r > b + 15) & (sat > 0.2)).mean()
    score = ratio * 2.0 + (1.0 - min(1.0, mean_sat * 2.5)) + (1.0 - float(warm) * 3.0) * 0.5
    return {
        "silver_ratio": round(ratio, 4),
        "mean_sat": round(mean_sat, 4),
        "mean_val": round(mean_val, 4),
        "warm_ratio": round(float(warm), 4),
        "score": round(float(score), 4),
    }

def detail_score(path: Path, img: Image.Image) -> dict:
    arr = np.asarray(img.convert("L"), dtype=np.float32)
    # laplacian-ish via simple gradient energy
    gx = np.abs(np.diff(arr, axis=1)).mean()
    gy = np.abs(np.diff(arr, axis=0)).mean()
    energy = float(gx + gy)
    size = path.stat().st_size
    # prefer reasonably detailed / larger files but not extreme
    score = min(energy / 20.0, 2.0) + min(size / 1_500_000.0, 1.5)
    return {"grad_energy": round(energy, 3), "bytes": size, "score": round(score, 4)}

def analyze(path: Path) -> dict:
    img = load_rgb(path)
    w, h = img.size
    comp = edge_margin_score(img)
    sil = silver_score(img)
    det = detail_score(path, img)
    total = comp["score"] * 1.4 + sil["score"] * 1.2 + det["score"] * 0.6
    return {
        "path": str(path),
        "size": [w, h],
        "bytes": det["bytes"],
        "composition": comp,
        "silver": sil,
        "detail": det,
        "total_score": round(total, 4),
    }

def pick_rule(c1: dict, c2: dict) -> tuple[str, str]:
    """Return (pick, reason). Prefer composition margin, then silver, then total."""
    # hard prefer better margin if delta meaningful
    m1 = c1["composition"]["margin_min"]
    m2 = c2["composition"]["margin_min"]
    e1 = c1["composition"]["edge_hug"]
    e2 = c2["composition"]["edge_hug"]
    if (m1 - m2) > 0.02 or (e2 - e1) > 0.01:
        if m1 > m2 or e1 < e2:
            return "c1", f"safer composition (margin {m1:.3f}>{m2:.3f} or edge_hug {e1:.3f}<{e2:.3f})"
    if (m2 - m1) > 0.02 or (e1 - e2) > 0.01:
        if m2 > m1 or e2 < e1:
            return "c2", f"safer composition (margin {m2:.3f}>{m1:.3f} or edge_hug {e2:.3f}<{e1:.3f})"
    s1 = c1["silver"]["score"]
    s2 = c2["silver"]["score"]
    if abs(s1 - s2) > 0.15:
        pick = "c1" if s1 > s2 else "c2"
        return pick, f"better silver/gray look (sil_score {max(s1,s2):.3f}>{min(s1,s2):.3f})"
    t1 = c1["total_score"]; t2 = c2["total_score"]
    if t1 >= t2:
        return "c1", f"higher total heuristic ({t1:.3f}>={t2:.3f})"
    return "c2", f"higher total heuristic ({t2:.3f}>{t1:.3f})"

def main():
    inventory = []
    picks = {
        "project": "a-space-cat",
        "batch": "missing31_v6",
        "created": "2026-10-02",
        "timezone": "Asia/Shanghai",
        "target_size": list(TARGET),
        "method_note": "Heuristic auto-pick (composition margin / edge-hug, silver-gray look, detail). Visual QA not fully available to agent; needs 视频号规划 visual accept.",
        "rules": [
            "1. Prefer candidate with larger subject margin / lower edge-hug (avoid edge-hugging; leave crop margin).",
            "2. Else prefer higher silver/gray fur score (low sat, mid-high value; penalize warm/orange).",
            "3. Else higher total = composition*1.4 + silver*1.2 + detail*0.6.",
            "4. Tie-break: c1.",
            "5. Never overwrite protected existing firstframes.",
        ],
        "protected_existing": sorted(PROTECTED),
        "missing_shots": MISSING,
        "shots": {},
    }
    for n in MISSING:
        tag = shot_tag(n)
        raw_dir = RAW / tag
        c1p = raw_dir / f"{tag}_c1.png"
        c2p = raw_dir / f"{tag}_c2.png"
        shared_c1 = SHARED / f"{tag}_c1_00001_.png"
        shared_c2 = SHARED / f"{tag}_c2_00001_.png"
        assert c1p.exists() and c2p.exists(), (c1p, c2p)
        a1 = analyze(c1p)
        a2 = analyze(c2p)
        pick, reason = pick_rule(a1, a2)
        chosen = a1 if pick == "c1" else a2
        entry = {
            "shot": n,
            "tag": tag,
            "c1": a1,
            "c2": a2,
            "pick": pick,
            "reason": reason,
            "picked_path": chosen["path"],
            "shared_c1": str(shared_c1) if shared_c1.exists() else None,
            "shared_c2": str(shared_c2) if shared_c2.exists() else None,
            "ff_target": str(FF / ff_name(n)),
            "ff_exists_before": (FF / ff_name(n)).exists(),
            "protected": n in PROTECTED,
        }
        assert not entry["protected"], n
        assert not entry["ff_exists_before"], n
        picks["shots"][f"{n:02d}"] = entry
        inventory.append({
            "shot": n,
            "c1": str(c1p),
            "c2": str(c2p),
            "c1_bytes": a1["bytes"],
            "c2_bytes": a2["bytes"],
            "c1_size": a1["size"],
            "c2_size": a2["size"],
            "pick": pick,
            "reason": reason,
        })
        print(f"shot{n:02d}: pick={pick}  c1={a1['total_score']:.3f} c2={a2['total_score']:.3f}  | {reason}")

    inv_path = OUT / "missing31_candidates_inventory.json"
    picks_path = OUT / "missing31_picks.json"
    inv_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    picks_path.write_text(json.dumps(picks, ensure_ascii=False, indent=2), encoding="utf-8")
    print("WROTE", inv_path)
    print("WROTE", picks_path)
    print("PICKS", sum(1 for s in picks['shots'].values() if s['pick']=='c1'), "c1 /",
          sum(1 for s in picks['shots'].values() if s['pick']=='c2'), "c2")

if __name__ == "__main__":
    main()
