# -*- coding: utf-8 -*-
"""拼接：93 个镜头 → body_silent → 加旁白 → 拼片头 → clean.mp4。

产物：
  body_silent.mp4   正文无声母片（1920x1080 / 30 fps）
  body_clean.mp4    正文＋旁白（AAC 192k）
  clean.mp4         片头＋正文＋完整旁白（交付母版，无字幕）
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

EP = Path(__file__).resolve().parents[3]
RUN = EP / "runs" / "20261112-cas-b01"
CLIPS = RUN / "body_clips"
INTRO = RUN / "intro" / "batch-20261113-cas-e05-20char" / "intro_silent.mp4"
BODY_WAV = RUN / "chapters" / "body_narration.wav"
NARR = RUN / "narration.wav"
FPS = 30


def run(cmd: list[str]) -> None:
    print(" ".join(str(c) for c in cmd[:6]), "...")
    res = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stderr[-1500:])
        raise SystemExit(f"ffmpeg failed: {res.returncode}")


def dur(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout
    return float(out.strip())


def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                          "-show_entries", "stream=width,height,r_frame_rate,pix_fmt",
                          "-of", "json", str(path)], capture_output=True, text=True).stdout
    s = json.loads(out)["streams"][0]
    return {"w": s["width"], "h": s["height"], "fps": s["r_frame_rate"], "pix": s["pix_fmt"]}


def main() -> None:
    plan = json.loads((RUN / "motion_plan.json").read_text(encoding="utf-8"))
    ids = [s["id"] for s in plan["shots"]]
    missing = [i for i in ids if not (CLIPS / f"{i}.mp4").exists()]
    if missing:
        raise SystemExit(f"missing clips: {missing}")

    lst = RUN / "logs" / "clips.txt"
    lst.write_text("\n".join(f"file '{(CLIPS / (i + '.mp4')).as_posix()}'" for i in ids),
                   encoding="utf-8")

    body_silent = RUN / "body_silent.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
         "-c", "copy", body_silent])

    frames = int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                                 "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0",
                                 str(body_silent)], capture_output=True, text=True).stdout.strip())
    expect = sum(round(s["duration_s"] * FPS) for s in plan["shots"])
    print(f"body frames={frames} expect={expect} drift={frames - expect}")
    print(f"body video={dur(body_silent):.2f}s audio={dur(BODY_WAV):.2f}s")

    body_clean = RUN / "body_clean.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-i", body_silent, "-i", BODY_WAV,
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-shortest", "-movflags", "+faststart", body_clean])

    print("intro", probe(INTRO), f"{dur(INTRO):.2f}s")
    print("body ", probe(body_clean), f"{dur(body_clean):.2f}s")

    full_silent = RUN / "full_silent.mp4"
    lst2 = RUN / "logs" / "full.txt"
    lst2.write_text(f"file '{INTRO.as_posix()}'\nfile '{body_silent.as_posix()}'\n", encoding="utf-8")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst2,
         "-c", "copy", full_silent])

    clean = RUN / "clean.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-i", full_silent, "-i", NARR,
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-shortest", "-movflags", "+faststart", clean])

    print(f"clean video={dur(full_silent):.2f}s audio={dur(NARR):.2f}s -> {clean}")
    if abs(dur(full_silent) - dur(NARR)) > 0.5:
        print("WARN: video/audio drift > 0.5 s")


if __name__ == "__main__":
    main()
