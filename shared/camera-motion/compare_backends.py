"""Run matched affine/blender configs, verify motion, build side-by-side videos and QA report.

Usage (from repo root or this directory):
  python compare_backends.py --run-dir <new-dir> [--pairs land_same,port_same,...] [--blender EXE]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
TESTDATA = ROOT / "testdata"
CONFIGS = TESTDATA / "configs"
PY = sys.executable


def is_complete(out: Path) -> bool:
    man = out / "manifest.json"
    if not man.exists():
        return False
    try:
        data = json.loads(man.read_text(encoding="utf-8"))
    except Exception:
        return False
    return data.get("status") == "complete"


def run(cmd, log_path: Path | None = None):
    print("+", " ".join(map(str, cmd)), flush=True)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if log_path:
        log_path.write_text((proc.stdout or "") + "\n" + (proc.stderr or ""), encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {cmd}\n{proc.stdout}\n{proc.stderr}")
    return proc


def side_by_side(affine_mp4: Path, blender_mp4: Path, dest: Path, label_a="affine", label_b="blender"):
    font = Path(r"C:/Windows/Fonts/arial.ttf")
    if font.is_file():
        filter_complex = (
            f"[0:v]scale=-1:540,drawtext=fontfile='{font.as_posix()}':text='{label_a}':x=12:y=12:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.5[a];"
            f"[1:v]scale=-1:540,drawtext=fontfile='{font.as_posix()}':text='{label_b}':x=12:y=12:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.5[b];"
            f"[a][b]hstack=inputs=2[v]"
        )
    else:
        filter_complex = "[0:v]scale=-1:540[a];[1:v]scale=-1:540[b];[a][b]hstack=inputs=2[v]"
    cmd = [
        "ffmpeg", "-v", "error", "-y",
        "-i", str(affine_mp4), "-i", str(blender_mp4),
        "-filter_complex", filter_complex,
        "-map", "[v]", "-an",
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(dest),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError:
        cmd[cmd.index("-filter_complex") + 1] = "[0:v]scale=-1:540[a];[1:v]scale=-1:540[b];[a][b]hstack=inputs=2[v]"
        subprocess.run(cmd, check=True, capture_output=True)


def matched_frame_pixel_difference(affine_mp4: Path, blender_mp4: Path, max_frames: int = 30):
    ca = cv2.VideoCapture(str(affine_mp4))
    cb = cv2.VideoCapture(str(blender_mp4))
    diffs = []
    for _ in range(max_frames):
        oa, fa = ca.read()
        ob, fb = cb.read()
        if not (oa and ob):
            break
        if fa.shape != fb.shape:
            fb = cv2.resize(fb, (fa.shape[1], fa.shape[0]))
        diffs.append(float(np.mean(np.abs(fa.astype(np.float32) - fb.astype(np.float32)))))
    ca.release()
    cb.release()
    if not diffs:
        return None
    return {"mean_abs_rgb": float(np.mean(diffs)), "max_abs_rgb": float(np.max(diffs)), "frames": len(diffs)}


def copy_plan_resolving_sources(source: Path, destination: Path):
    plan = json.loads(source.read_text(encoding="utf-8"))
    for shot in plan["shots"]:
        shot["source"] = str((source.parent / shot["source"]).resolve())
    for key in ("blender_exe", "gpu_lock"):
        if plan.get(key):
            plan[key] = str((source.parent / plan[key]).resolve())
    destination.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return destination


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--pairs", default="matrix_land_same,matrix_port_same,matrix_materials_land")
    parser.add_argument("--blender", type=Path, default=None)
    parser.add_argument("--skip-render", action="store_true")
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    blender = args.blender or os.environ.get("CAMERA_MOTION_BLENDER")
    report = {"run_dir": str(run_dir), "pairs": [], "recommendation": None}

    for base in [p.strip() for p in args.pairs.split(",") if p.strip()]:
        aff_cfg = CONFIGS / f"{base}_affine.json"
        bli_cfg = CONFIGS / f"{base}_blender.json"
        if not aff_cfg.exists() or not bli_cfg.exists():
            report["pairs"].append({"base": base, "status": "missing_config"})
            continue
        aff_cfg = copy_plan_resolving_sources(aff_cfg, run_dir / aff_cfg.name)
        bli_cfg = copy_plan_resolving_sources(bli_cfg, run_dir / bli_cfg.name)
        aff_out = run_dir / f"{base}_affine"
        bli_out = run_dir / f"{base}_blender"
        pair_info = {"base": base, "affine_out": str(aff_out), "blender_out": str(bli_out)}
        t0 = time.perf_counter()
        if not args.skip_render:
            if is_complete(aff_out):
                pair_info["affine_render_s"] = 0.0
                pair_info["affine_cache"] = True
            else:
                run([PY, str(ROOT / "camera_motion.py"), str(aff_cfg), "--out", str(aff_out)], run_dir / f"{base}_affine_render.log")
                pair_info["affine_render_s"] = time.perf_counter() - t0
            t1 = time.perf_counter()
            if is_complete(bli_out):
                pair_info["blender_render_s"] = 0.0
                pair_info["blender_cache"] = True
            else:
                cmd = [PY, str(ROOT / "camera_motion.py"), str(bli_cfg), "--out", str(bli_out)]
                if blender:
                    cmd += ["--blender", str(blender)]
                run(cmd, run_dir / f"{base}_blender_render.log")
                pair_info["blender_render_s"] = time.perf_counter() - t1
        for label, out in (("affine", aff_out), ("blender", bli_out)):
            qa_path = out / "qa.json"
            run([PY, str(ROOT / "verify_motion.py"), str(out), "--out", str(qa_path)])
            pair_info[f"{label}_qa"] = json.loads(qa_path.read_text(encoding="utf-8"))
        compare_dir = run_dir / f"{base}_compare"
        compare_dir.mkdir(exist_ok=True)
        shots = []
        for traj in sorted(aff_out.glob("*-trajectory.json")):
            shot = traj.name[:-len("-trajectory.json")]
            a = aff_out / f"{shot}.mp4"
            b = bli_out / f"{shot}.mp4"
            if a.exists() and b.exists():
                dest = compare_dir / f"{shot}_sbs.mp4"
                if not dest.exists():
                    side_by_side(a, b, dest)
                difference = matched_frame_pixel_difference(a, b)
                shots.append({"id": shot, "sbs": str(dest.resolve()), "matched_frame_pixel_difference": difference})
        pair_info["shots"] = shots
        report["pairs"].append(pair_info)

    slowdowns = []
    for p in report["pairs"]:
        if p.get("affine_render_s") and p.get("blender_render_s") and p["affine_render_s"] > 0:
            slowdowns.append(p["blender_render_s"] / max(p["affine_render_s"], 1e-6))
    if slowdowns and min(slowdowns) > 5:
        report["recommendation"] = "Keep affine as default; Blender optional (large slowdown)."
    else:
        report["recommendation"] = "Review side-by-side videos before changing default; numeric QA alone is insufficient."
    out_json = run_dir / "QA_REPORT.json"
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"output": str(out_json), "recommendation": report["recommendation"]}, indent=2))


if __name__ == "__main__":
    main()
