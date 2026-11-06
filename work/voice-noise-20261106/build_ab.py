# -*- coding: utf-8 -*-
"""Build the A/B listening set for the sleep-line voice experiments.

All clips use the same sentence, the production trim rule, and the same final gain,
so only the voice/stretch differ. Also writes an HTML player page.
"""
from __future__ import annotations
import subprocess, wave
from pathlib import Path
import numpy as np
from analyze import read_wav

ROOT = Path(r"E:\program\1project\video")
WORK = ROOT / "work/voice-noise-20261106"
OUT = WORK / "ab"
OUT.mkdir(parents=True, exist_ok=True)
FF = "ffmpeg"


def trim(y, sr, rms_db=-45.0, frame_ms=20, head=0.10, tail=0.15):
    frame = max(1, int(sr * frame_ms / 1000))
    n = len(y) // frame
    if n == 0:
        return y
    r = np.sqrt(np.mean(y[: n * frame].reshape(n, frame) ** 2, axis=1))
    act = np.where(r > 10 ** (rms_db / 20.0))[0]
    if not len(act):
        return y
    a = max(0, int(act[0] * frame - head * sr))
    b = min(len(y), int((act[-1] + 1) * frame + tail * sr))
    return y[a:b]


def write(path, y, sr):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())


def stretch(src, dst, mode):
    if mode == "atempo":
        f = "atempo=0.774224"
    else:
        f = ("rubberband=tempo=0.774224:pitch=1:formant=preserved:"
             "transients=smooth:detector=compound:window=standard")
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
                    "-filter:a", f, "-acodec", "pcm_s16le", str(dst)], check=True)
    y, sr = read_wav(dst)
    return y, sr


def gain_to(y, target_db=-21.0):
    rms = np.sqrt(np.mean(y ** 2)) + 1e-12
    return y * (10 ** (target_db / 20) / rms)


CLIPS = [
    ("01_prod_atempo_s10", ROOT / "4/audio/vo-processed/lightexpr-seed7/ch01-p03-u01.wav", None,
     "当前生产版：轻语 prompt + 10 步 + atempo（就是视频里的声音）"),
    ("02_s20_atempo", WORK / "tts-probe/s20.wav", "atempo",
     "同一句、20 步，仍用轻语 prompt + atempo"),
    ("03_s30_atempo", WORK / "tts-probe/s30.wav", "atempo",
     "同一句、30 步，仍用轻语 prompt + atempo"),
    ("04_p1_refprompt_atempo", WORK / "tts-probe2/p1_refprompt.wav", "atempo",
     "原版参考音当 prompt（不用轻语 prompt）+ 20 步 + atempo"),
    ("05_p2_denprompt_atempo", WORK / "tts-probe2/p2_denprompt.wav", "atempo",
     "轻语 prompt 先做频谱降噪 + 20 步 + atempo"),
    ("06_s20_rubberband", WORK / "tts-probe/s20.wav", "rubberband",
     "20 步 + rubberband 变速（替代 atempo）"),
]


def main():
    rows = []
    for name, src, mode, desc in CLIPS:
        y, sr = read_wav(src)
        if mode:
            y = trim(y, sr)
            tmp = OUT / f"_{name}_trim.wav"
            write(tmp, y, sr)
            y, sr = stretch(tmp, OUT / f"_{name}_stretch.wav", mode)
            tmp.unlink(missing_ok=True)
        y = gain_to(y, -21.0)
        dst = OUT / f"{name}.wav"
        write(dst, y, sr)
        rows.append((name, dst, desc, round(len(y) / sr, 2)))
        print(f"{name:26s} {len(y)/sr:5.2f}s  {dst}")

    html = ["<!doctype html><meta charset='utf-8'><title>助眠声线 A/B</title>",
            "<style>body{background:#12161c;color:#e8eef6;font:15px/1.6 system-ui;max-width:900px;margin:40px auto;padding:0 20px}",
            "h1{font-size:20px;font-weight:600}.clip{margin:26px 0;padding:16px 18px;background:#1b222c;border-radius:10px}",
            ".name{font-weight:600;color:#ffd27d}.desc{color:#9fb0c3;margin:4px 0 10px}audio{width:100%}</style>",
            "<h1>助眠解说 · 同一句声线对比</h1>",
            "<p style='color:#9fb0c3'>文本：其中一片雪花，旋转着，穿过安静的空气，最后落在山坡上。<br>全部按生产口径裁剪、变速、统一 RMS −21 dBFS。建议戴耳机，听换气、齿音、金属感。</p>"]
    for name, dst, desc, dur in rows:
        html.append(f"<div class='clip'><div class='name'>{name}</div><div class='desc'>{desc}（{dur}s）</div>"
                    f"<audio controls preload='none' src='{dst.name}'></audio></div>")
    (OUT / "index.html").write_text("\n".join(html), encoding="utf-8")
    print("HTML ->", OUT / "index.html")


if __name__ == "__main__":
    main()
