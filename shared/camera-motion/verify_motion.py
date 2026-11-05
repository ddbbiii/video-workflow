"""Verify encoded camera motion against rendered trajectory metadata.

Usage: python verify_motion.py <run-directory> [--out qa.json]
The checker is deliberately conservative: failed or low-texture ECC samples are
reported as indeterminate rather than being treated as a pass.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np


def gray(frame: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0


def ecc(a: np.ndarray, b: np.ndarray, affine: bool = True):
    mode = cv2.MOTION_AFFINE if affine else cv2.MOTION_TRANSLATION
    matrix = np.eye(2, 3, dtype=np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 80, 1e-6)
    try:
        score, matrix = cv2.findTransformECC(a, b, matrix, mode, criteria, None, 3)
        return float(score), matrix
    except cv2.error:
        return None, None


def probe(path: Path):
    command = ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]
    try:
        data = json.loads(subprocess.check_output(command, text=True))
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        return {"probe_ok": False, "error": str(exc)}
    stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    return {"probe_ok": bool(stream), "width": stream.get("width"), "height": stream.get("height"),
            "fps": stream.get("avg_frame_rate"), "frames": int(stream["nb_frames"]) if stream.get("nb_frames", "N/A") not in ("N/A", None) else None,
            "duration_s": float(stream["duration"]) if stream.get("duration") else float(data.get("format", {}).get("duration", 0)),
            "codec": stream.get("codec_name"), "pix_fmt": stream.get("pix_fmt")}


def actual_motion(video: Path, trajectory: Path):
    meta = json.loads(trajectory.read_text(encoding="utf-8"))
    planned = np.asarray(meta.get("inverse_sample_matrices", []), dtype=np.float64)
    cap = cv2.VideoCapture(str(video))
    decoded_count = 0
    def pairs():
        nonlocal decoded_count, x0, y0
        previous = None
        try:
            while True:
                ok, image = cap.read()
                if not ok:
                    return
                h, w = image.shape[:2]
                y0, y1 = int(h * .18), int(h * .82)
                x0, x1 = int(w * .18), int(w * .82)
                crop = gray(image[y0:y1, x0:x1])
                current = (crop, float(np.std(crop)))
                decoded_count += 1
                if previous is not None:
                    yield previous, current
                previous = current
        finally:
            cap.release()
    x0 = y0 = 0
    samples = []
    for i, ((a, ta), (b, tb)) in enumerate(pairs()):
        if min(ta, tb) < 0.015:
            samples.append({"frame": i, "status": "indeterminate", "reason": "low_texture", "texture_std": min(ta, tb)})
            continue
        score, measured = ecc(a, b, affine=True)
        if measured is None:
            samples.append({"frame": i, "status": "indeterminate", "reason": "ecc_failed", "texture_std": min(ta, tb)})
            continue
        # ECC matrix maps the crop from frame i to i+1. Compare translation and scale
        # with the relative transform from adjacent planned inverse matrices.
        observed = measured.astype(float)
        expected = None
        if i + 1 < len(planned):
            p0 = np.vstack([planned[i], [0, 0, 1]])
            p1 = np.vstack([planned[i + 1], [0, 0, 1]])
            expected = np.linalg.inv(p1) @ p0
        entry = {"frame": i, "status": "measured", "ecc": float(score),
                 "dx_px": float(observed[0, 2]), "dy_px": float(observed[1, 2]),
                 "scale_x": float(observed[0, 0]), "scale_y": float(observed[1, 1]),
                 "texture_std": min(ta, tb)}
        if expected is not None:
            local_center = np.array([a.shape[1] / 2, a.shape[0] / 2, 1.0])
            global_center = local_center + [x0, y0, 0]
            expected_step = (expected @ global_center)[:2] - global_center[:2]
            observed_step = observed @ local_center - local_center[:2]
            entry.update(expected_dx_px=float(expected_step[0]), expected_dy_px=float(expected_step[1]),
                         residual_dx_px=float(observed_step[0] - expected_step[0]),
                         residual_dy_px=float(observed_step[1] - expected_step[1]))
        samples.append(entry)
    measured = [s for s in samples if s["status"] == "measured" and "residual_dx_px" in s]
    if measured:
        residual = np.array([[s["residual_dx_px"], s["residual_dy_px"]] for s in measured])
        rms = float(np.sqrt(np.mean(residual ** 2)))
        ecc_min = float(min(s["ecc"] for s in measured))
    else:
        rms, ecc_min = None, None
    reasons = []
    if len(measured) != len(samples) or not measured:
        reasons.append('registration_failed_or_low_texture')
    if ecc_min is not None and ecc_min < .98:
        reasons.append('low_registration_correlation')
    if rms is not None and rms > .08:
        reasons.append('motion_residual_above_threshold')
    if decoded_count != len(planned):
        reasons.append('trajectory_frame_count_mismatch')
    return {"decoded_frames": decoded_count, "sample_count": len(samples),
            "measured_count": len(measured), "indeterminate_count": len(samples) - len(measured),
            "residual_rms_px": rms, "ecc_min": ecc_min,
            "samples": samples, "indeterminate_reasons": reasons, "status": "pass" if len(measured) == len(samples) and measured and rms is not None and rms <= 0.08 and ecc_min >= 0.98 and decoded_count == len(planned) else "indeterminate"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    results = []
    for trajectory in sorted(args.run_dir.glob("*-trajectory.json")):
        shot = trajectory.name[:-len("-trajectory.json")]
        video = args.run_dir / f"{shot}.mp4"
        if not video.exists():
            results.append({"id": shot, "status": "indeterminate", "reason": "video_missing"})
            continue
        media = probe(video)
        motion = actual_motion(video, trajectory)
        decode_ok = media.get("probe_ok") and motion["decoded_frames"] == media.get("frames")
        results.append({"id": shot, "video": str(video), "media": media, "decode_ok": decode_ok, "motion": motion,
                        "status": "pass" if decode_ok and motion["status"] == "pass" else "indeterminate"})
    report = {"method": "Decoded-frame ECC affine registration against adjacent trajectory matrices; central 64% ROI; low-texture and ECC failures are indeterminate.",
              "run_dir": str(args.run_dir.resolve()), "shots": results,
              "limits": ["ECC measures dominant texture motion and can be biased by compression or repeated texture.", "Numeric pass does not replace human playback review."]}
    output = args.out or (args.run_dir / "qa.json")
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "shots": len(results), "statuses": [r["status"] for r in results]}, indent=2))


if __name__ == "__main__":
    main()
