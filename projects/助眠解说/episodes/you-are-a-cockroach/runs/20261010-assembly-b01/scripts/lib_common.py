# -*- coding: utf-8 -*-
"""Shared helpers for cockroach assembly-b01."""
from __future__ import annotations
import json, os, time, subprocess, tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\you-are-a-cockroach")
RUN = EP / "runs" / "20261010-assembly-b01"
FFMPEG = Path(r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe")
FFPROBE = FFMPEG.with_name("ffprobe.exe")
PYTHON = Path(r"E:\program\language\python\Python-3.11.0\python.exe")
CAMERA_MOTION = Path(r"E:\program\1project\video\shared\camera-motion\camera_motion.py")
BGM = Path(r"E:\program\1project\video\assets\助眠解说\audio\bgm\sleep-unified-v1\leberch-sleep-583079.mp3")
FONT_DIR = Path(r"E:\program\1project\video\assets\助眠解说\subtitles\style-r4\fonts")
FONT_FILE = FONT_DIR / "SourceHanSansSC-Heavy.otf"
VO_DIR = EP / "audio" / "vo-processed" / "atempo07304"
I2V_LANCZOS = EP / "runs" / "20261009-i2v-batch-b01" / "lanczos"
I2V_MANIFEST = EP / "runs" / "20261009-i2v-batch-b01" / "i2v_manifest.json"
AFFINE_OLD = EP / "runs" / "20261009-affine-b01"
STILLS = EP / "image" / "stills"

SR = 48000
FPS = 30
GAP_INTRA = 0.20
GAP_INTER_PARA = 0.45
GAP_INTER_CHAPTER = 0.80
INTRO_HEAD = 0.40
INTRO_BETWEEN = 0.45
INTRO_TAIL = 0.80
BGM_GAIN = 1.30
TZ = timezone(timedelta(hours=8))

BODY_SECTIONS = ["bridge", "ch01", "ch02", "ch03", "ch04", "ch05", "ch06", "ch07", "ch08", "outro"]


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def atomic_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def update_checkpoint(*, stage, completed, running, next_action, blocked=""):
    atomic_json(RUN / "CHECKPOINT.json", {
        "stage": stage,
        "completed": completed,
        "running": running,
        "next_action": next_action,
        "blocked": blocked,
        "updated_at": now_iso(),
    })


def log_stage(name: str, text: str) -> Path:
    p = RUN / "logs" / f"{name}.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(f"[{now_iso()}] {text}\n")
    return p


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def vo_rel_path(uid: str) -> str:
    # uid like ch01-p01-u01 -> ch01/ch01-p01-u01.wav
    section = uid.split("-")[0]
    return f"{section}/{uid}.wav"


def ffprobe_duration(path: Path) -> float:
    r = subprocess.run(
        [str(FFPROBE), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())


def run_cmd(cmd, log_path: Path, cwd=None) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"\n$ {' '.join(map(str, cmd))}\n")
        f.flush()
        p = subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT)
        f.write(f"exit={p.returncode}\n")
    return p.returncode
