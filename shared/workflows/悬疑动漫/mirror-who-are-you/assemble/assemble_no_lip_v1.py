# -*- coding: utf-8 -*-
"""Assemble mirror-who-are-you no-lip v1: still cells + VO."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\program\1project\video\projects\悬疑动漫\mirror-who-are-you")
AUDIO = ROOT / "audio" / "takes-seed123"
CELLS = ROOT / "cells"
OUT = ROOT / "out"
SEG = OUT / "_segs_no_lip_v1"
SCALED = OUT / "_scaled_720x1280"
META = AUDIO / "meta.json"
TIMELINE = OUT / "timeline_no_lip_v1.json"
FINAL = OUT / "mirror_no_lip_v1.mp4"
LOG = OUT / "assemble_no_lip_v1.log"
W, H = 720, 1280
FPS = 24

# shot_id -> cell filename (no path)
MAP = {
    # L01
    "L01_01": "G1_c1.png",
    "L01_02": "G1_c2.png",
    "L01_03": "G1_c5.png",
    "L01_04": "G1_c7.png",
    "L01_05": "G1_c6.png",
    "L01_06": "G1_c9.png",  # 你是谁 雾镜
    "L01_07": "G1_c8.png",  # 程雾
    "L01_08": "G1_c1.png",  # 反讽抿唇
    "L01_09": "G1_c5.png",
    # L02
    "L02_01": "G1_c6.png",
    "L02_02": "G1_c3.png",  # 你是谁
    "L02_03": "G1_c8.png",  # 程雾
    "L02_04": "G1_c5.png",
    "L02_05": "G1_c1.png",
    # L03
    "L03_01": "G2_c1.png",
    "L03_02": "G2_c2.png",
    "L03_03": "G2_c3.png",
    "L03_04": "G1_c9.png",  # 你是谁
    "L03_05": "G1_c3.png",  # 程雾
    "L03_06": "G1_c2.png",  # 环境/镜框
    # L04
    "L04_01": "G1_c7.png",
    "L04_02": "G1_c7.png",  # 低头抿嘴
    "L04_03": "G1_c6.png",
    "L04_04": "G1_c9.png",  # 你是谁
    "L04_05": "G1_c8.png",  # 程雾x3（单轨用 c8；c9 留给前后切变感）
    "L04_06": "G1_c3.png",
    "L04_07": "G3_v2_c7.png",  # 雾字横竖
    # L05 album
    "L05_01": "G2_c4.png",
    "L05_02": "G2_c5.png",
    "L05_03": "G2_c6.png",
    "L05_04": "G2_c7.png",
    "L05_05": "G2_c8.png",
    "L05_06": "G2_c9.png",
    "L05_07": "G3_v2_c1.png",
    # L06
    "L06_01": "G1_c8.png",
    "L06_02": "G1_c9.png",
    "L06_03": "G3_v2_c2.png",
    "L06_04": "G2_c2.png",
    "L06_05": "G3_v2_c3.png",
    "L06_06": "G3_v2_c4.png",
    "L06_07": "G3_v2_c5.png",
    "L06_08": "G3_v2_c6.png",
    "L06_09": "G3_v2_c8.png",
    "L06_10": "G1_c2.png",
    # L07
    "L07_01": "G1_c9.png",  # 你是谁
    "L07_02": "N1_face.png",  # 唇闭静帧收束
}

HIGH_RISK = {
    "L01_06", "L02_02", "L03_04", "L04_04", "L07_01",
    "L01_07", "L02_03", "L03_05", "L04_05",
    "L01_08", "L03_06",
}


def log(msg: str) -> None:
    line = msg.rstrip() + "\n"
    print(line, end="", flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line)


def run(cmd, check=True):
    log("CMD: " + " ".join(str(c) for c in cmd))
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.stdout:
        log(p.stdout[-2000:] if len(p.stdout) > 2000 else p.stdout)
    if p.stderr:
        # ffmpeg stats go to stderr
        err = p.stderr
        if len(err) > 3000:
            err = err[:1500] + "\n...\n" + err[-1500:]
        log(err)
    if check and p.returncode != 0:
        raise RuntimeError(f"cmd failed rc={p.returncode}: {cmd[0]}")
    return p


def ffprobe_duration(path: Path) -> float:
    p = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return float(p.stdout.strip())


def scale_image(src: Path, dst: Path) -> None:
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return
    # scale to fit 720x1280, pad black, lanczos
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,"
        f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black,"
        f"setsar=1"
    )
    run([
        "ffmpeg", "-y", "-i", str(src),
        "-vf", vf,
        "-frames:v", "1",
        str(dst),
    ])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    SEG.mkdir(parents=True, exist_ok=True)
    SCALED.mkdir(parents=True, exist_ok=True)
    if LOG.exists():
        LOG.unlink()

    meta = json.load(open(META, encoding="utf-8"))
    shots = meta["shots"]
    order = sorted(shots.keys())

    missing = [s for s in order if s not in MAP]
    if missing:
        raise SystemExit(f"MAP missing shots: {missing}")
    extra = [s for s in MAP if s not in shots]
    if extra:
        log(f"WARN MAP extras ignored: {extra}")

    # validate high-risk images never G1_c4
    for sid in HIGH_RISK:
        img = MAP[sid]
        if img == "G1_c4.png":
            raise SystemExit(f"HIGH RISK {sid} mapped to G1_c4 — forbidden")
        if sid in ("L01_06", "L02_02", "L03_04", "L04_04", "L07_01") and img not in ("G1_c9.png", "G1_c3.png"):
            raise SystemExit(f"你是谁 {sid} must be G1_c9/c3, got {img}")
        if sid in ("L01_07", "L02_03", "L03_05") and img not in ("G1_c8.png", "G1_c3.png"):
            raise SystemExit(f"程雾 {sid} must be G1_c8/c3, got {img}")
        if sid == "L04_05" and img not in ("G1_c8.png", "G1_c9.png", "G1_c3.png"):
            raise SystemExit(f"L04_05 must be fog cells, got {img}")

    timeline = []
    total_audio = 0.0

    # scale unique images
    needed = sorted(set(MAP[s] for s in order))
    for name in needed:
        src = CELLS / name
        if not src.exists():
            raise SystemExit(f"missing cell: {src}")
        scale_image(src, SCALED / name)

    concat_list = SEG / "concat.txt"
    seg_paths = []

    for i, sid in enumerate(order):
        wav = AUDIO / f"{sid}.wav"
        if not wav.exists():
            raise SystemExit(f"missing wav: {wav}")
        dur = ffprobe_duration(wav)
        img_name = MAP[sid]
        scaled = SCALED / img_name
        seg = SEG / f"{i:03d}_{sid}.mp4"
        text = shots[sid]["text"]

        # stillimage encode; -t from audio duration; aac copy after encode
        # use -shortest with exact -t on video
        run([
            "ffmpeg", "-y",
            "-loop", "1", "-framerate", str(FPS),
            "-i", str(scaled),
            "-i", str(wav),
            "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
            "-r", str(FPS),
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-t", f"{dur:.6f}",
            "-shortest",
            "-movflags", "+faststart",
            str(seg),
        ])
        seg_paths.append(seg)
        total_audio += dur
        timeline.append({
            "shot_id": sid,
            "audio": str(wav),
            "image": str(CELLS / img_name),
            "image_cell": img_name,
            "audio_s": round(dur, 4),
            "meta_audio_s": shots[sid].get("audio_s"),
            "text": text,
            "high_risk": sid in HIGH_RISK,
        })
        log(f"OK {sid} {dur:.3f}s -> {img_name}")

    with open(TIMELINE, "w", encoding="utf-8") as f:
        json.dump({
            "version": "no_lip_v1",
            "desc": "静帧挂 VO；VO=内心独白；禁正脸张嘴对口型；未用 G1_c4 挂高危句",
            "resolution": f"{W}x{H}",
            "fps": FPS,
            "total_audio_s": round(total_audio, 4),
            "shot_count": len(timeline),
            "shots": timeline,
            "high_risk_map": {s: MAP[s] for s in sorted(HIGH_RISK)},
        }, f, ensure_ascii=False, indent=2)

    # concat demuxer
    with open(concat_list, "w", encoding="utf-8") as f:
        for p in seg_paths:
            # ffmpeg concat needs forward slashes or escaped backslashes
            f.write(f"file '{p.as_posix()}'\n")

    tmp_final = OUT / "mirror_no_lip_v1.tmp.mp4"
    run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        "-movflags", "+faststart",
        str(tmp_final),
    ])
    if FINAL.exists():
        FINAL.unlink()
    tmp_final.rename(FINAL)

    # probe final
    p = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration:format=duration,size",
            "-of", "json",
            str(FINAL),
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    info = json.loads(p.stdout)
    log("FINAL_PROBE " + json.dumps(info, ensure_ascii=False))
    log(f"DONE path={FINAL} total_audio_s={total_audio:.3f} timeline={TIMELINE}")
    print("SUCCESS")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"FATAL: {e}")
        raise
