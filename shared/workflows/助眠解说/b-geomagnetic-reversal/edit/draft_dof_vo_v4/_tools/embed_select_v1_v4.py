#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Embed select_v1 i2v (12 shots) into draft_dof_vo_v4. CPU ffmpeg only; no GPU / no gpu.lock.

- ch1: copy from draft_dof_vo_v3 (b2-warm-male already)
- ch2-6: baseline shots from draft_dof_vo_v2; 12 select shots replace VIDEO with
  looped i2v, keep baseline VO audio + duration
- xfade 0.4s shot / 0.5s chapter; loudnorm I=-16 TP=-1.5 LRA=11
- canvas 1188x2112 @ 30fps
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal")  # 2026-10-08 迁移：原 legacy-source\zhumian\b-geomagnetic-reversal，现为单集目录
V2 = ROOT / "archive" / "edit" / "draft_dof_vo_v2"
V3 = ROOT / "archive" / "edit" / "draft_dof_vo_v3"
OUT = ROOT / "audio" / "draft_dof_vo_v4"  # inventory/chapters/logs 在这里；shots 和整片在 archive
OUTA = ROOT / "archive" / "edit" / "draft_dof_vo_v4"
SHOTS = OUTA / "shots"
CHAP = OUT / "chapters"
LOGS = OUT / "logs"
WORK = OUT / "work"
I2V_CLIPS = ROOT / "archive" / "i2v" / "select_v1" / "clips"

W, H, FPS = 1188, 2112, 30
XFADE = 0.40
CHAP_XFADE = 0.50
LOUD_I, LOUD_TP, LOUD_LRA = -16.0, -1.5, 11.0

CH26_BY_CHAP = {
    "ch2": [f"ch2-c{i:02d}" for i in range(1, 11)],
    "ch3": [f"ch3-c{i:02d}" for i in range(1, 10)],
    "ch4": [f"ch4-c{i:02d}" for i in range(1, 10)],
    "ch5": [f"ch5-c{i:02d}" for i in range(1, 10)],
    "ch6": [f"ch6-c{i:02d}" for i in range(1, 10)],
}

# ordered as in SHOT_LIST.md / task brief
SELECT_SHOTS = [
    "ch3-c08",
    "ch4-c06",
    "ch4-c08",
    "ch6-c02",
    "ch6-c03",
    "ch2-c09",
    "ch5-c06",
    "ch2-c06",
    "ch5-c02",
    "ch6-c07",
    "ch6-c05",
    "ch5-c05",
]

CH1_ORDER = [
    "ch1-c01", "ch1-c02", "ch1-c03", "ch1-c04", "ch1-c05",
    "ch1-c06a", "ch1-c06b", "ch1-c07", "ch1-c08",
    "ch1-c09a", "ch1-c09b", "ch1-c10", "ch1-c11", "ch1-c12",
    "ch1-c13", "ch1-c14", "ch1-c15",
]


def log(msg: str) -> None:
    print(msg, flush=True)


def run(cmd, check=True):
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        raise RuntimeError(
            f"fail {p.returncode}: {' '.join(map(str, cmd))}\n{(p.stderr or '')[-2500:]}"
        )
    return p


def dur(path: Path) -> float:
    p = run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ])
    return float(p.stdout.strip())


def vf_fit() -> str:
    return (
        f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
        f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={FPS},format=yuv420p"
    )


def measure_loudnorm(path: Path) -> dict:
    p = run([
        "ffmpeg", "-hide_banner", "-i", str(path),
        "-af", f"loudnorm=I={LOUD_I}:TP={LOUD_TP}:LRA={LOUD_LRA}:print_format=json",
        "-f", "null", "-",
    ], check=False)
    text = (p.stderr or "") + (p.stdout or "")
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", text, re.S)
    if not m:
        raise RuntimeError(f"loudnorm measure fail {path}\n{text[-1500:]}")
    return json.loads(m.group(0))


def apply_loudnorm(src: Path, dst: Path, measured: dict | None = None) -> dict:
    if measured is None:
        measured = measure_loudnorm(src)
    filt = (
        f"loudnorm=I={LOUD_I}:TP={LOUD_TP}:LRA={LOUD_LRA}:"
        f"measured_I={measured['input_i']}:"
        f"measured_LRA={measured['input_lra']}:"
        f"measured_TP={measured['input_tp']}:"
        f"measured_thresh={measured['input_thresh']}:"
        f"offset={measured['target_offset']}:"
        f"linear=true:print_format=summary"
    )
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(src),
        "-af", filt,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-movflags", "+faststart",
        str(dst),
    ])
    return measured


def xfade_pair(a: Path, b: Path, out: Path, fade: float):
    da = dur(a)
    offset = max(0.05, da - fade)
    fc = (
        f"[0:v][1:v]xfade=transition=fade:duration={fade:.3f}:offset={offset:.3f}[v];"
        f"[0:a][1:a]acrossfade=d={fade:.3f}:c1=tri:c2=tri[a]"
    )
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(a), "-i", str(b),
        "-filter_complex", fc,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-movflags", "+faststart",
        str(out),
    ])


def xfade_sequence(paths: list[Path], out: Path, fade: float, work: Path) -> float:
    work.mkdir(parents=True, exist_ok=True)
    if len(paths) == 1:
        run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(paths[0]),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
            "-movflags", "+faststart", str(out),
        ])
        return dur(out)
    cur = paths[0]
    tmp_prev = None
    for i, nxt in enumerate(paths[1:], 1):
        tmp = work / f"xf_{i:03d}.mp4"
        log(f"  xfade {i}/{len(paths)-1}: {cur.name} + {nxt.name}")
        xfade_pair(cur, nxt, tmp, fade)
        if tmp_prev and tmp_prev.exists() and tmp_prev != paths[0]:
            try:
                tmp_prev.unlink()
            except OSError:
                pass
        cur = tmp
        tmp_prev = tmp
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(cur), "-c", "copy", "-movflags", "+faststart", str(out),
    ])
    if cur.exists() and cur.parent == work:
        try:
            cur.unlink()
        except OSError:
            pass
    return dur(out)


def find_i2v_clip(shot: str) -> Path:
    """Match clips like ch6-c02_s7_1080x1920.mp4 or ch3-c08_s42_1080x1920.mp4."""
    matches = sorted(I2V_CLIPS.glob(f"{shot}_*_1080x1920.mp4"))
    if not matches:
        matches = sorted(I2V_CLIPS.glob(f"{shot}_*.mp4"))
    if not matches:
        raise FileNotFoundError(f"no i2v clip for {shot} under {I2V_CLIPS}")
    if len(matches) > 1:
        log(f"  WARN multiple i2v for {shot}, using {matches[0].name}")
    return matches[0]


def copy_file(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def ffmpeg_copy(src: Path, dst: Path):
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(src), "-c", "copy", "-movflags", "+faststart", str(dst),
    ])


def make_select_shot(shot: str, baseline: Path, i2v: Path, out: Path, vo_dur: float):
    """Loop i2v video to vo_dur; keep baseline audio; fit canvas."""
    # -stream_loop -1 on video; -t vo_dur on output; audio from baseline (-map 1:a)
    # Also trim/pad audio via -t so A/V match.
    vf = vf_fit()
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-stream_loop", "-1", "-i", str(i2v),
        "-i", str(baseline),
        "-filter_complex", f"[0:v]{vf}[v]",
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-t", f"{vo_dur:.3f}",
        "-movflags", "+faststart",
        str(out),
    ])


def main() -> int:
    now = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S CST")
    for d in (OUT, SHOTS, CHAP, LOGS, WORK, OUT / "_tools"):
        d.mkdir(parents=True, exist_ok=True)

    select_set = set(SELECT_SHOTS)
    rows: list[dict] = []
    select_rows: list[dict] = []

    # ---- ch1: copy from v3, do not rebuild ----
    log("=== ch1 copy from v3 ===")
    ch1_src = V3 / "chapters" / "ch1_dof_vo_v3.mp4"
    ch1_dst = CHAP / "ch1_dof_vo_v4.mp4"
    if not ch1_src.exists():
        raise FileNotFoundError(ch1_src)
    ffmpeg_copy(ch1_src, ch1_dst)
    ch1_dur = dur(ch1_dst)
    log(f"  ch1 chapter={ch1_dur:.3f}s")

    for sid in CH1_ORDER:
        src = V3 / "shots" / f"{sid}.mp4"
        dst = SHOTS / f"{sid}.mp4"
        if src.exists():
            copy_file(src, dst)
            d = dur(dst)
            rows.append({
                "shot": sid,
                "chapter": "ch1",
                "out": str(dst),
                "out_dur": round(d, 3),
                "source": str(src),
                "treatment": "copy_v3_shot",
                "note": "ch1 unchanged from draft_dof_vo_v3",
            })
        else:
            log(f"  WARN missing v3 shot {sid}")

    # ---- ch2-6 shots ----
    log("=== ch2-6 shots (copy or select_v1 i2v loop) ===")
    chap_shot_paths: dict[str, list[Path]] = {}
    for chap, shot_ids in CH26_BY_CHAP.items():
        paths: list[Path] = []
        for shot in shot_ids:
            baseline = V2 / "shots" / f"{shot}.mp4"
            if not baseline.exists():
                raise FileNotFoundError(baseline)
            out = SHOTS / f"{shot}.mp4"
            vo_dur = dur(baseline)

            if shot in select_set:
                i2v = find_i2v_clip(shot)
                i2v_d = dur(i2v)
                log(f"  SELECT {shot}: i2v={i2v.name} ({i2v_d:.2f}s) -> loop to vo={vo_dur:.2f}s")
                make_select_shot(shot, baseline, i2v, out, vo_dur)
                out_d = dur(out)
                row = {
                    "shot": shot,
                    "chapter": chap,
                    "out": str(out),
                    "out_dur": round(out_d, 3),
                    "baseline": str(baseline),
                    "baseline_dur": round(vo_dur, 3),
                    "i2v": str(i2v),
                    "i2v_dur": round(i2v_d, 3),
                    "treatment": "select_v1_i2v_loop",
                    "note": "video looped from select_v1; audio+duration from v2 shot",
                }
                rows.append(row)
                select_rows.append(row)
            else:
                ffmpeg_copy(baseline, out)
                out_d = dur(out)
                rows.append({
                    "shot": shot,
                    "chapter": chap,
                    "out": str(out),
                    "out_dur": round(out_d, 3),
                    "source": str(baseline),
                    "treatment": "copy_v2_shot",
                    "note": "",
                })
            paths.append(out)
        chap_shot_paths[chap] = paths

    missing = select_set - {r["shot"] for r in select_rows}
    if missing:
        raise RuntimeError(f"select shots not built: {sorted(missing)}")
    if len(select_rows) != 12:
        raise RuntimeError(f"expected 12 select shots, got {len(select_rows)}")

    # ---- chapter xfade+loudnorm for ch2-6 ----
    chapter_meta: list[tuple[str, Path, float]] = [("ch1", ch1_dst, ch1_dur)]
    loud_meta: dict = {}

    for chap in ["ch2", "ch3", "ch4", "ch5", "ch6"]:
        log(f"=== chapter {chap} xfade+loudnorm ===")
        raw = CHAP / f"{chap}_dof_vo_v4.raw.mp4"
        outp = CHAP / f"{chap}_dof_vo_v4.mp4"
        d = xfade_sequence(chap_shot_paths[chap], raw, XFADE, WORK / chap)
        log(f"  {chap} raw={d:.2f}s loudnorm...")
        m = apply_loudnorm(raw, outp)
        loud_meta[chap] = m
        try:
            raw.unlink()
        except OSError:
            pass
        cd = dur(outp)
        log(f"  {chap} final={cd:.2f}s")
        chapter_meta.append((chap, outp, cd))

    # ---- full film ----
    log("=== full film ===")
    chap_paths = [p for _, p, _ in chapter_meta]
    full_raw = OUTA / "ch1-6_dof_vo_v4.raw.mp4"
    full_out = OUTA / "ch1-6_dof_vo_v4.mp4"
    dfull = xfade_sequence(chap_paths, full_raw, CHAP_XFADE, WORK / "full")
    log(f"  full raw={dfull:.2f}s loudnorm...")
    mfull = apply_loudnorm(full_raw, full_out)
    loud_meta["full"] = mfull
    try:
        full_raw.unlink()
    except OSError:
        pass
    full_dur = dur(full_out)
    log(f"  full final={full_dur:.2f}s")

    inv = {
        "root": str(ROOT),
        "from_v2": str(V2),
        "from_v3": str(V3),
        "i2v_select": str(I2V_CLIPS),
        "target": f"{W}x{H}@{FPS}",
        "xfade_shot_sec": XFADE,
        "xfade_chapter_sec": CHAP_XFADE,
        "loudnorm": {"I": LOUD_I, "TP": LOUD_TP, "LRA": LOUD_LRA},
        "loudnorm_measured": loud_meta,
        "select_count": len(select_rows),
        "select_shots": select_rows,
        "chapters": {c: {"path": str(p), "dur": round(d, 3)} for c, p, d in chapter_meta},
        "full": {"path": str(full_out), "dur": round(full_dur, 3)},
        "shots": rows,
        "built_at": now,
        "gpu_lock_touched": False,
    }
    (OUT / "inventory.json").write_text(
        json.dumps(inv, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# EMBED_NOTES · draft_dof_vo_v4",
        "",
        f"- 时间：{now}",
        "- 口径：CPU ffmpeg；**不占 GPU / 不写 gpu.lock**",
        "- ch1：复用 `draft_dof_vo_v3/chapters/ch1_dof_vo_v3.mp4`（b2-warm-male），未重做",
        "- ch2–6 基线：`draft_dof_vo_v2/shots/`；其中 **12** 镜画面换 select_v1 i2v 循环，口播/时长不变",
        f"- 画幅：{W}×{H} @ {FPS}fps；镜间 xfade {XFADE}s；章间 {CHAP_XFADE}s；loudnorm I={LOUD_I}",
        "",
        "## 输出",
        f"- 全片：`{full_out}` · **{full_dur:.1f}s**",
    ]
    for c, p, d in chapter_meta:
        lines.append(f"- {c}：`{p}` · {d:.1f}s")
    lines.append("")
    lines.append("## select_v1 替换（12/12）")
    lines.append("| 镜 | i2v | i2v秒 | VO秒 | out秒 | treatment |")
    lines.append("|---|---|---:|---:|---:|---|")
    for r in select_rows:
        lines.append(
            f"| {r['shot']} | `{Path(r['i2v']).name}` | {r['i2v_dur']:.2f} | "
            f"{r['baseline_dur']:.2f} | {r['out_dur']:.2f} | `{r['treatment']}` |"
        )
    lines.append("")
    lines.append("## 约束核对")
    lines.append("- gpu.lock：未读写")
    lines.append("- 仅写本工程 `edit/draft_dof_vo_v4/`")
    lines.append("")
    (OUT / "EMBED_NOTES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    log(f"DONE {full_out} {full_dur:.1f}s select={len(select_rows)}/12")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
