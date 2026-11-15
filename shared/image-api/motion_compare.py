# -*- coding: utf-8 -*-
"""Render a slow push-in (1.00 -> 1.09x over 6 s) on the OLD and NEW cells and put them
side by side, so the softness is judged the way the final video will show it.

Pipeline mirrors delivery: cell 1016x568 -> 1920x1080 (Lanczos) -> push-in crop -> 1280x720.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RUN = Path(__file__).resolve().parent / "runs" / "20261109-063916-grid2x2-ab"
CELLS = RUN / "cells"
OUT = RUN / "motion"
TMP = RUN / "motion" / "_frames"
FONT = r"C:\Windows\Fonts\msyh.ttc"
PANELS = [1, 3, 4]
FPS = 24
SECONDS = 6
ZOOM = 1.09
W, H = 1280, 720
LABEL_H = 34


def smooth(t: float) -> float:
    return t * t * (3 - 2 * t)


def base_frames(tag: str, panel: int) -> Image.Image:
    image = Image.open(CELLS / f"{tag}-p{panel}.png").convert("RGB")
    return image.resize((1920, 1080), Image.LANCZOS)


def render(tag: str, panel: int, base: Image.Image) -> list[Path]:
    frame_dir = TMP / f"{tag}-p{panel}"
    if frame_dir.exists():
        shutil.rmtree(frame_dir)
    frame_dir.mkdir(parents=True)
    paths = []
    total = FPS * SECONDS
    for index in range(total):
        progress = smooth(index / (total - 1))
        zoom = 1 + (ZOOM - 1) * progress
        crop_w, crop_h = 1920 / zoom, 1080 / zoom
        left = (1920 - crop_w) / 2
        top = (1080 - crop_h) / 2
        box = (round(left), round(top), round(left + crop_w), round(top + crop_h))
        frame = base.crop(box).resize((W, H), Image.LANCZOS)
        path = frame_dir / f"{index:04d}.png"
        frame.save(path)
        paths.append(path)
    return paths


def encode(frames: list[Path], out: Path) -> None:
    pattern = str(frames[0].parent / "%04d.png")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", pattern,
         "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)],
        check=True)


def side_by_side(panel: int, old_frames: list[Path], new_frames: list[Path]) -> Path:
    combined_dir = TMP / f"sbs-p{panel}"
    if combined_dir.exists():
        shutil.rmtree(combined_dir)
    combined_dir.mkdir(parents=True)
    font = ImageFont.truetype(FONT, 21)
    for index, (old_path, new_path) in enumerate(zip(old_frames, new_frames)):
        canvas = Image.new("RGB", (W * 2 + 6, H + LABEL_H), (12, 12, 14))
        canvas.paste(Image.open(old_path), (0, LABEL_H))
        canvas.paste(Image.open(new_path), (W + 6, LABEL_H))
        draw = ImageDraw.Draw(canvas)
        draw.text((10, 8), "OLD · dklapi · 0.16/张", fill=(240, 200, 120), font=font)
        draw.text((W + 16, 8), "NEW · mxwell · 0.02/张", fill=(120, 210, 240), font=font)
        canvas.save(combined_dir / f"{index:04d}.png")
    out = OUT / f"pushin-p{panel}.mp4"
    frame_paths = sorted(combined_dir.glob("*.png"))
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i",
         str(combined_dir / "%04d.png"), "-c:v", "libx264", "-crf", "18",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)],
        check=True)
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for panel in PANELS:
        print(f"panel {panel}: rendering frames", flush=True)
        old_base, new_base = base_frames("old", panel), base_frames("new", panel)
        old_frames = render("old", panel, old_base)
        new_frames = render("new", panel, new_base)
        out = side_by_side(panel, old_frames, new_frames)
        print(f"panel {panel}: {out}", flush=True)
    shutil.rmtree(TMP)
    return 0


if __name__ == "__main__":
    sys.exit(main())
