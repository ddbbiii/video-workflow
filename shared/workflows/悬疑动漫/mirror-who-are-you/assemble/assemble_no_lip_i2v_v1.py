# -*- coding: utf-8 -*-
"""Assemble mirror-who-are-you no_lip_i2v_v1: i2v clips + VO (CPU only, no GPU)."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\program\1project\video\projects\悬疑动漫\mirror-who-are-you")
AUDIO = ROOT / "audio" / "takes-seed123"
CELLS = ROOT / "cells"
OUT = ROOT / "out"
I2V = ROOT / "i2v" / "no_lip_v1"
MANIFEST = I2V / "manifest.json"
TL_STILL = OUT / "timeline_no_lip_v1.json"
SEG = OUT / "_segs_no_lip_i2v_v1"
FINAL = OUT / "mirror_no_lip_i2v_v1.mp4"
TIMELINE = OUT / "timeline_no_lip_i2v_v1.json"
NOTES = OUT / "NOTES_no_lip_i2v_v1.md"
LOG = OUT / "assemble_no_lip_i2v_v1.log"
W, H = 1080, 1920  # match i2v clips
FPS = 24

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


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    SEG.mkdir(parents=True, exist_ok=True)
    if LOG.exists():
        LOG.unlink()

    # Refuse if somehow asked to touch GPU — soft check only
    lock = Path(r"E:\program\1project\video\shared\work\cache\gpu.lock")
    log(f"gpu.lock exists={lock.exists()} (CPU assemble; will not acquire)")

    manifest = json.load(open(MANIFEST, encoding="utf-8"))
    shot_map = manifest["shot_map"]
    still_tl = json.load(open(TL_STILL, encoding="utf-8"))
    shots = still_tl["shots"]
    order = [s["shot_id"] for s in shots]
    still_by_id = {s["shot_id"]: s for s in shots}

    missing = [s for s in order if s not in shot_map]
    if missing:
        raise SystemExit(f"shot_map missing: {missing}")

    for sid in order:
        clip = Path(shot_map[sid]["clip"])
        if not clip.exists():
            raise SystemExit(f"missing clip for {sid}: {clip}")
        # never G1_c4
        cell = shot_map[sid].get("cell", "")
        if cell == "G1_c4" or "G1_c4" in clip.name:
            raise SystemExit(f"FORBIDDEN G1_c4 used for {sid}")

    timeline = []
    total_audio = 0.0
    seg_paths = []
    loop_shots = []
    trim_shots = []

    for i, sid in enumerate(order):
        wav = AUDIO / f"{sid}.wav"
        if not wav.exists():
            raise SystemExit(f"missing wav: {wav}")
        dur = ffprobe_duration(wav)
        info = shot_map[sid]
        clip = Path(info["clip"])
        cell = info["cell"]
        clip_dur = ffprobe_duration(clip)
        need_loop = clip_dur + 0.05 < dur
        if need_loop:
            loop_shots.append(sid)
        elif clip_dur > dur + 0.05:
            trim_shots.append(sid)

        seg = SEG / f"{i:03d}_{sid}.mp4"
        # scale/pad to WxH, loop if needed, attach VO, hard cut to audio dur
        vf = (
            f"scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black,"
            f"setsar=1,fps={FPS}"
        )
        cmd = ["ffmpeg", "-y"]
        if need_loop:
            cmd += ["-stream_loop", "-1"]
        cmd += [
            "-i", str(clip),
            "-i", str(wav),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
            "-r", str(FPS),
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-t", f"{dur:.6f}",
            "-shortest",
            "-movflags", "+faststart",
            "-map", "0:v:0", "-map", "1:a:0",
            str(seg),
        ]
        run(cmd)
        # verify seg duration roughly matches
        seg_dur = ffprobe_duration(seg)
        if abs(seg_dur - dur) > 0.15:
            log(f"WARN {sid} seg_dur={seg_dur:.3f} vs audio={dur:.3f}")

        still = still_by_id[sid]
        timeline.append({
            "shot_id": sid,
            "audio": str(wav),
            "clip": str(clip),
            "cell": cell,
            "image_cell": f"{cell}.png",
            "audio_s": round(dur, 4),
            "clip_s": round(clip_dur, 4),
            "mode": "loop" if need_loop else ("trim" if clip_dur > dur + 0.05 else "fit"),
            "text": still.get("text"),
            "high_risk": sid in HIGH_RISK,
        })
        seg_paths.append(seg)
        total_audio += dur
        log(f"OK {sid} audio={dur:.3f}s clip={clip_dur:.3f}s mode={timeline[-1]['mode']} -> {cell}")

    # write timeline
    with open(TIMELINE, "w", encoding="utf-8") as f:
        json.dump({
            "version": "no_lip_i2v_v1",
            "desc": "i2v clips 嵌回 + VO 内心独白；少动嘴 locked-off；禁正脸张嘴；未用 G1_c4",
            "resolution": f"{W}x{H}",
            "fps": FPS,
            "total_audio_s": round(total_audio, 4),
            "shot_count": len(timeline),
            "loop_shots": loop_shots,
            "trim_count": len(trim_shots),
            "manifest": str(MANIFEST),
            "clips_dir": str(I2V / "clips"),
            "shots": timeline,
            "high_risk_map": {
                s: shot_map[s]["cell"] for s in sorted(HIGH_RISK) if s in shot_map
            },
        }, f, ensure_ascii=False, indent=2)

    concat_list = SEG / "concat.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for p in seg_paths:
            f.write(f"file '{p.as_posix()}'\n")

    tmp_final = OUT / "mirror_no_lip_i2v_v1.tmp.mp4"
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

    p = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration,size:stream=codec_type,width,height,duration",
            "-of", "json",
            str(FINAL),
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    info = json.loads(p.stdout)
    log("FINAL_PROBE " + json.dumps(info, ensure_ascii=False))

    notes = f"""# mirror_no_lip_i2v_v1 assemble NOTES

- **CPU only** — no gpu.lock, no Comfy, no i2v re-run
- Source clips: `{I2V / 'clips'}`
- Manifest shot_map: 46/46 covered
- VO: `audio/takes-seed123`
- Output: `{FINAL}`
- Resolution: {W}x{H} (match i2v clips)
- Duration target ~177.92s (timeline still); assembled audio_s={total_audio:.3f}
- Loop shots (clip shorter than VO): {', '.join(loop_shots) if loop_shots else '(none)'}
- Trim shots: {len(trim_shots)}
- Hard rules: locked-off micro; ban speaking/open mouth; no MuseTalk; G1_c4 unused
- Timeline: `{TIMELINE}`
"""
    NOTES.write_text(notes, encoding="utf-8")
    log(f"DONE path={FINAL} total_audio_s={total_audio:.3f} timeline={TIMELINE} notes={NOTES}")
    print("SUCCESS")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"FATAL: {e}")
        raise
