"""Read-only QA for one RealBasicVSR run (or any existing VSR asset).

Status rules (three-state, never a final pass):
  fail            any hard check failed (streams/size/fps/frames/duration/pix_fmt/codec/audio/decode)
  needs_review    hard checks passed but temporal or tile-seam warnings fired
  pending_review  hard checks passed, no warnings; still needs a human to view the
                  contact sheets AND play the full clip before visual_qa may become "passed"
Laplacian variance is edge energy only; it does not prove real detail recovery.

Usage:
  python qa_single_vsr.py --run-dir <run dir with manifest.json> [--compare-vsr old.mp4]
  python qa_single_vsr.py --input src.mp4 --vsr vsr.mp4 [--baseline lanczos.mp4] --report-dir NEW_DIR
Exit: 0 pending_review/needs_review | 5 fail | 2 usage error | 1 crash
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path

import cv2
import numpy as np

FFMPEG_FALLBACK_DIR = Path(r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages"
                           r"\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe"
                           r"\ffmpeg-8.1.2-full_build-shared\bin")
SCALE = 4
DURATION_TOL = 0.1
SEAM_BAND = 2          # +- px around a boundary (delivery pixels)
SEAM_EXCLUDE = 8       # exclusion zone around boundaries for the reference median
SEAM_ABS = 1.25        # vsr boundary gradient / non-boundary median
SEAM_REL = 1.25        # (vsr score) / (reference score at same position)
CELL = (640, 360)


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def tool(name):
    return shutil.which(name) or str(FFMPEG_FALLBACK_DIR / f"{name}.exe")


def ffprobe(path):
    raw = subprocess.run([tool("ffprobe"), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    if raw.returncode != 0:
        return {"error": raw.stderr.strip()[:300]}
    data = json.loads(raw.stdout)
    streams = data.get("streams", [])
    v = [s for s in streams if s.get("codec_type") == "video"]
    a = [s for s in streams if s.get("codec_type") == "audio"]
    info = {"video_streams": len(v), "audio_streams": len(a),
            "format_duration": float(data.get("format", {}).get("duration", 0) or 0)}
    if v:
        s = v[0]
        info.update(width=s.get("width"), height=s.get("height"), codec=s.get("codec_name"), pix_fmt=s.get("pix_fmt"),
                    r_frame_rate=s.get("r_frame_rate"), nb_frames=int(s["nb_frames"]) if str(s.get("nb_frames", "")).isdigit() else None,
                    video_duration=float(s.get("duration", 0) or 0))
    if a:
        info["audio"] = [{"codec": x.get("codec_name"), "channels": x.get("channels"), "sample_rate": x.get("sample_rate"),
                          "duration": float(x.get("duration", 0) or 0)} for x in a]
    return info


def full_decode(path):
    p = subprocess.run([tool("ffmpeg"), "-v", "error", "-i", str(path), "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {"returncode": p.returncode, "stderr": p.stderr.strip()[:500], "ok": p.returncode == 0 and not p.stderr.strip()}


def boundaries_from_history(history, in_w, in_h):
    xs, ys = set(), set()
    for h in history or []:
        tw, th = h["w"], h["h"]
        for s in h["layout"]["xs"]:
            if s > 0:
                xs.add(s)
            if s + tw < in_w:
                xs.add(s + tw)
        for s in h["layout"]["ys"]:
            if s > 0:
                ys.add(s)
            if s + th < in_h:
                ys.add(s + th)
    return sorted(xs), sorted(ys)


class Stream:
    """Decode a video once, collecting metrics, seam profiles and contact frames."""

    def __init__(self, label, path, target, resize=False):
        self.label, self.path, self.target, self.resize = label, str(path), target, resize

    def run(self, keep_idx):
        cap = cv2.VideoCapture(self.path)
        lap, temporal, luma = [], [], []
        col_sum = row_sum = None
        prev = None
        kept = {}
        n = 0
        while True:
            ok, f = cap.read()
            if not ok:
                break
            if self.resize or (f.shape[1], f.shape[0]) != self.target:
                f = cv2.resize(f, self.target, interpolation=cv2.INTER_LANCZOS4)
            gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
            g = gray.astype(np.float32)
            lap.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
            luma.append(float(g.mean()))
            col = np.abs(np.diff(g, axis=1)).mean(axis=0)
            row = np.abs(np.diff(g, axis=0)).mean(axis=1)
            col_sum = col if col_sum is None else col_sum + col
            row_sum = row if row_sum is None else row_sum + row
            small = cv2.resize(gray, (320, 180), interpolation=cv2.INTER_AREA)
            if prev is not None:
                temporal.append(float(np.mean(cv2.absdiff(small, prev))))
            prev = small
            if n in keep_idx:
                kept[n] = f.copy()
            n += 1
        cap.release()
        self.frames = n
        self.kept = kept
        self.col = col_sum / max(1, n) if col_sum is not None else None
        self.row = row_sum / max(1, n) if row_sum is not None else None
        lap_a = np.array(lap) if lap else np.zeros(1)
        luma_a = np.array(luma) if luma else np.zeros(1)
        self.metrics = {
            "frames_decoded": n,
            "laplacian_median": float(np.median(lap_a)), "laplacian_mean": float(np.mean(lap_a)),
            "laplacian_p95": float(np.percentile(lap_a, 95)),
            "laplacian_frame_cv": float(np.std(lap_a) / max(1e-6, np.median(lap_a))),
            "laplacian_max_adjacent_change_pct": float(np.max(np.abs(np.diff(lap_a)) / np.maximum(1e-6, lap_a[:-1])) * 100) if n > 1 else 0.0,
            "temporal_delta_median": float(np.median(temporal)) if temporal else 0.0,
            "temporal_delta_p95": float(np.percentile(temporal, 95)) if temporal else 0.0,
            "max_adjacent_mean_luma_change": float(np.max(np.abs(np.diff(luma_a)))) if n > 1 else 0.0,
        }
        return self


def seam_scores(profile, positions, length):
    if profile is None or not positions:
        return []
    mask = np.ones(len(profile), bool)
    mask[:4] = mask[-4:] = False
    for p in positions:
        c = int(round(p))
        mask[max(0, c - SEAM_EXCLUDE):c + SEAM_EXCLUDE + 1] = False
    ref = float(np.median(profile[mask])) if mask.any() else float(np.median(profile))
    out = []
    for p in positions:
        c = int(round(p))
        band = profile[max(0, c - 1 - SEAM_BAND):min(len(profile), c + SEAM_BAND)]
        out.append(float(band.mean() / max(1e-6, ref)))
    return out


def seam_report(vsr, ref, in_w, in_h, out_w, out_h, history):
    bx, by = boundaries_from_history(history, in_w, in_h)
    px = [b * out_w / in_w for b in bx]
    py = [b * out_h / in_h for b in by]
    sv_x, sv_y = seam_scores(vsr.col, px, out_w), seam_scores(vsr.row, py, out_h)
    sr_x, sr_y = seam_scores(ref.col, px, out_w), seam_scores(ref.row, py, out_h)
    items, suspects = [], []
    for axis, inp, pos, sv, sr in (("x", bx, px, sv_x, sr_x), ("y", by, py, sv_y, sr_y)):
        for b, p, a, r in zip(inp, pos, sv, sr):
            rel = a / max(1e-6, r)
            item = {"axis": axis, "input_px": b, "delivery_px": round(p, 1), "vsr_score": round(a, 3),
                    "reference_score": round(r, 3), "relative": round(rel, 3)}
            items.append(item)
            if a > SEAM_ABS and rel > SEAM_REL:
                suspects.append(item)
    return {
        "method": "mean |gradient| across each tile boundary band (+-%d delivery px, averaged over all frames and the "
                  "full line) divided by the median of non-boundary lines; compared with the same score on the "
                  "reference (Lanczos baseline) at identical positions. Warning signal only." % SEAM_BAND,
        "reference": ref.label, "thresholds": {"abs": SEAM_ABS, "relative": SEAM_REL},
        "boundaries": items,
        "max_vsr_score": round(max([i["vsr_score"] for i in items], default=0.0), 3),
        "max_relative": round(max([i["relative"] for i in items], default=0.0), 3),
        "suspected": suspects,
    }


def label(img, text):
    out = img.copy()
    cv2.rectangle(out, (0, 0), (out.shape[1], 30), (0, 0, 0), -1)
    cv2.putText(out, text, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    return out


def contact_sheets(streams, keep, out_dir, crop_center, suffix):
    rows, crop_rows = [], []
    names = ["first", "mid", "last"]
    cw, ch = 384, 216
    cx, cy = crop_center
    for name, idx in zip(names, keep):
        cells, crops = [], []
        for s in streams:
            f = s.kept.get(idx)
            if f is None:
                f = np.zeros((s.target[1], s.target[0], 3), np.uint8)
            cells.append(label(cv2.resize(f, CELL, interpolation=cv2.INTER_AREA), f"{s.label} | {name} f{idx}"))
            x0 = int(min(max(0, cx - cw // 2), f.shape[1] - cw))
            y0 = int(min(max(0, cy - ch // 2), f.shape[0] - ch))
            crop = cv2.resize(f[y0:y0 + ch, x0:x0 + cw], (cw * 2, ch * 2), interpolation=cv2.INTER_NEAREST)
            crops.append(label(crop, f"{s.label} | {name} f{idx} | 1:1 crop x{x0} y{y0} (2x nearest)"))
        rows.append(np.hstack(cells))
        crop_rows.append(np.hstack(crops))
    p1 = out_dir / f"contact-first-mid-last{suffix}.png"
    p2 = out_dir / f"contact-seam-crops{suffix}.png"
    for path, img in ((p1, np.vstack(rows)), (p2, np.vstack(crop_rows))):
        # cv2.imwrite silently fails on non-ASCII Windows paths; encode in memory and write via Python
        ok, buf = cv2.imencode(".png", img)
        if not ok:
            raise RuntimeError(f"cannot encode contact sheet {path}")
        path.write_bytes(buf.tobytes())
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"contact sheet not written: {path}")
    return [str(p1), str(p2)]


def atomic_json(path, data):
    tmp = Path(str(path) + ".tmp")
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    for attempt in range(10):
        try:
            tmp.write_text(payload, encoding="utf-8")
            os.replace(tmp, path)
            return
        except PermissionError:
            time.sleep(0.2 * (attempt + 1))
    raise RuntimeError(f"cannot write {path}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", help="run directory produced by run_vsr_streaming.py (reads manifest.json)")
    ap.add_argument("--input", help="source video (read-only mode)")
    ap.add_argument("--vsr", help="VSR delivery video (read-only mode)")
    ap.add_argument("--raw", help="optional raw VSR video (read-only mode)")
    ap.add_argument("--baseline", help="optional Lanczos baseline (read-only mode)")
    ap.add_argument("--report-dir", help="NEW directory for report/contact sheets (read-only mode)")
    ap.add_argument("--output-size", default="1920x1080")
    ap.add_argument("--drop-audio", action="store_true", help="read-only mode: audio was dropped on purpose")
    ap.add_argument("--tile-size", default="640x352", help="read-only mode: tile WxH used (for seam positions)")
    ap.add_argument("--overlap", type=int, default=32)
    ap.add_argument("--compare-vsr", help="extra video (e.g. previously accepted VSR) for metrics/contact sheet")
    args = ap.parse_args(argv)

    manifest_path = None
    if args.run_dir:
        run_dir = Path(args.run_dir).resolve()
        manifest_path = run_dir / "manifest.json"
        if not manifest_path.is_file():
            print(f"[qa] no manifest.json in {run_dir}", file=sys.stderr)
            return 2
        man = json.loads(manifest_path.read_text(encoding="utf-8"))
        cfg = man["config"]
        src, vsr_path, raw_path = Path(cfg["input"]), Path(cfg["outputs"]["delivery"]), Path(cfg["outputs"]["raw"])
        baseline = Path(cfg["baseline"]["path"]) if cfg.get("baseline") else None
        out_w, out_h = cfg["output_size"]
        exp_frames, exp_dur = cfg["expected_frames"], cfg["expected_duration_s"]
        audio_policy = cfg["audio_policy"]
        history = man.get("tile_history")
        report_dir = run_dir
        run_status = man.get("status")
    else:
        if not (args.input and args.vsr and args.report_dir):
            print("[qa] read-only mode needs --input, --vsr and --report-dir", file=sys.stderr)
            return 2
        src, vsr_path = Path(args.input), Path(args.vsr)
        raw_path = Path(args.raw) if args.raw else None
        baseline = Path(args.baseline) if args.baseline else None
        out_w, out_h = [int(v) for v in args.output_size.lower().split("x")]
        report_dir = Path(args.report_dir).resolve()
        if report_dir.exists():
            print(f"[qa] report dir exists, refusing: {report_dir}", file=sys.stderr)
            return 2
        sp = ffprobe(src)
        fps = Fraction(sp["r_frame_rate"])
        exp_frames = sp["nb_frames"]
        exp_dur = exp_frames / float(fps)
        audio_policy = "none" if not sp["audio_streams"] else ("drop" if args.drop_audio else "preserve")
        tw, th = [int(v) for v in args.tile_size.lower().split("x")]
        from run_vsr_streaming import tile_layout  # same layout code as the runner
        history = [{"w": tw, "h": th, "layout": tile_layout(sp["width"], sp["height"], tw, th, args.overlap)}]
        run_status = "n/a (read-only)"
        report_dir.mkdir(parents=True)

    hard, warnings = [], []
    src_probe = ffprobe(src)
    in_w, in_h = src_probe["width"], src_probe["height"]
    src_fps = Fraction(src_probe["r_frame_rate"])
    if run_status not in ("completed", "n/a (read-only)"):
        hard.append(f"run status is {run_status!r}, not completed")
    if not vsr_path.is_file():
        hard.append(f"delivery file missing: {vsr_path}")
        out = {"qa_status": "fail", "hard_failures": hard, "time": now_iso()}
        atomic_json(report_dir / "quality-qa.json", out)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 5

    dp = ffprobe(vsr_path)
    checks = {}
    checks["video_streams_is_1"] = dp.get("video_streams") == 1
    checks["resolution_matches"] = (dp.get("width"), dp.get("height")) == (out_w, out_h)
    checks["fps_matches_input"] = dp.get("r_frame_rate") is not None and Fraction(dp["r_frame_rate"]) == src_fps
    checks["codec_h264"] = dp.get("codec") == "h264"
    checks["pix_fmt_yuv420p"] = dp.get("pix_fmt") == "yuv420p"
    if audio_policy == "preserve":
        checks["audio_present"] = dp.get("audio_streams", 0) >= 1
        a_dur = dp["audio"][0]["duration"] if dp.get("audio") else 0.0
        checks["audio_video_duration_delta_s"] = round(abs(a_dur - dp.get("video_duration", 0.0)), 4)
        checks["audio_duration_matches"] = checks["audio_video_duration_delta_s"] < DURATION_TOL
    else:
        checks["audio_absent_as_expected"] = dp.get("audio_streams", 0) == 0
    checks["format_duration_delta_s"] = round(abs(dp.get("format_duration", 0.0) - exp_dur), 4)
    checks["format_duration_matches"] = checks["format_duration_delta_s"] < DURATION_TOL
    checks["video_duration_delta_s"] = round(abs(dp.get("video_duration", 0.0) - exp_dur), 4)
    checks["video_duration_matches"] = checks["video_duration_delta_s"] < DURATION_TOL
    dec = full_decode(vsr_path)
    checks["delivery_full_decode_ok"] = dec["ok"]
    raw_info = None
    if raw_path is not None:
        if raw_path.is_file():
            raw_dec = full_decode(raw_path)
            raw_probe = ffprobe(raw_path)
            raw_info = {"path": str(raw_path), "probe": raw_probe, "decode": raw_dec}
            checks["raw_full_decode_ok"] = raw_dec["ok"]
            checks["raw_resolution_x4"] = (raw_probe.get("width"), raw_probe.get("height")) == (in_w * SCALE, in_h * SCALE)
        else:
            checks["raw_full_decode_ok"] = False

    n = max(1, exp_frames)
    keep = [0, n // 2, n - 1]
    target = (out_w, out_h)
    vsr_s = Stream("new VSR", vsr_path, target).run(set(keep))
    src_s = Stream("input Lanczos-on-the-fly", src, target, resize=True).run(set(keep))
    base_s = Stream("Lanczos baseline", baseline, target).run(set(keep)) if baseline and baseline.is_file() else None
    cmp_s = Stream("previous VSR", args.compare_vsr, target).run(set(keep)) if args.compare_vsr else None
    src_frames_total = src_s.frames
    checks["delivery_frames_decoded"] = vsr_s.frames
    checks["frame_count_matches"] = vsr_s.frames == exp_frames and (dp.get("nb_frames") in (None, exp_frames))
    if raw_info is not None:
        cap = cv2.VideoCapture(str(raw_path))
        raw_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        checks["raw_frame_count_matches"] = raw_frames == exp_frames

    for k, v in checks.items():
        if isinstance(v, bool) and not v:
            hard.append(k)

    ref = base_s or src_s
    temporal_limit = max(8.0, ref.metrics["temporal_delta_p95"] * 2.5)
    flags = {
        "temporal_warning": vsr_s.metrics["temporal_delta_p95"] > temporal_limit,
        "luma_jump_warning": vsr_s.metrics["max_adjacent_mean_luma_change"] > max(3.0, ref.metrics["max_adjacent_mean_luma_change"] * 2.5),
        "sharpness_flicker_warning": vsr_s.metrics["laplacian_frame_cv"] > max(0.10, ref.metrics["laplacian_frame_cv"] * 2.5),
    }
    seams = seam_report(vsr_s, ref, in_w, in_h, out_w, out_h, history)
    flags["seam_warning"] = bool(seams["suspected"])
    for k, v in flags.items():
        if v:
            warnings.append(k)

    xs = [b["delivery_px"] for b in seams["boundaries"] if b["axis"] == "x"]
    ys = [b["delivery_px"] for b in seams["boundaries"] if b["axis"] == "y"]
    cx = min(xs, key=lambda v: abs(v - out_w / 2)) if xs else out_w / 2
    cy = min(ys, key=lambda v: abs(v - out_h / 2)) if ys else out_h / 2
    suffix = ""
    if (report_dir / "quality-qa.json").exists():
        suffix = "-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    sheet_streams = [s for s in (src_s, base_s, vsr_s, cmp_s) if s is not None]
    sheets = contact_sheets(sheet_streams, keep, report_dir, (cx, cy), suffix)

    status = "fail" if hard else ("needs_review" if warnings else "pending_review")
    src_lap = src_s.metrics["laplacian_median"]
    metrics = {"input_lanczos": src_s.metrics, "new_vsr": vsr_s.metrics}
    if base_s:
        metrics["lanczos_baseline"] = base_s.metrics
    if cmp_s:
        metrics["previous_vsr"] = cmp_s.metrics
    ratios = {k: round(v["laplacian_median"] / max(1e-6, src_lap), 3) for k, v in metrics.items()}
    report = {
        "time": now_iso(), "qa_status": status, "visual_qa": "pending_review",
        "visual_qa_rule": "only a human may set visual_qa=passed after viewing the contact sheets AND full playback",
        "hard_failures": hard, "warnings": warnings, "checks": checks, "warning_flags": flags,
        "temporal_limit_p95": temporal_limit, "seams": seams,
        "expected": {"frames": exp_frames, "duration_s": exp_dur, "size": [out_w, out_h],
                     "fps": f"{src_fps.numerator}/{src_fps.denominator}", "audio_policy": audio_policy,
                     "input_frames_total": src_frames_total},
        "files": {"input": str(src), "delivery": str(vsr_path), "raw": raw_info, "baseline": str(baseline) if baseline else None,
                  "compare_vsr": args.compare_vsr},
        "delivery_probe": dp, "input_probe": src_probe, "delivery_decode": dec,
        "metrics": metrics, "laplacian_median_ratio_vs_input": ratios,
        "contact_sheets": sheets,
        "recommended_delivery": (str(baseline) if baseline and baseline.is_file() else "none: report failure")
        if status == "fail" else f"VSR candidate ({status}); keep Lanczos baseline as fallback until human review",
        "notes": ["Laplacian variance = edge energy, NOT proof of genuine detail recovery.",
                  "Temporal/seam numbers are warning signals only; flicker, deformation and seams need playback.",
                  "QA is read-only on all inputs."],
    }
    name = "quality-qa.json" if not suffix else f"quality-qa{suffix}.json"
    atomic_json(report_dir / name, report)
    if manifest_path is not None:
        man = json.loads(manifest_path.read_text(encoding="utf-8"))
        man.update(qa_status=status, visual_qa="pending_review", qa_report=str(report_dir / name),
                   contact_sheets=sheets, qa_hard_failures=hard, qa_warnings=warnings, updated=now_iso())
        atomic_json(manifest_path, man)
    print(json.dumps({"qa_status": status, "hard_failures": hard, "warnings": warnings,
                      "report": str(report_dir / name), "contact_sheets": sheets}, ensure_ascii=False, indent=2))
    return 5 if status == "fail" else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:
        import traceback
        traceback.print_exc()
        sys.exit(1)
