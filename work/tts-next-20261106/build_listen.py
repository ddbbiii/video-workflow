# -*- coding: utf-8 -*-
"""Build the two-model listening set, loudness-matched, plus an HTML page."""
from pathlib import Path
import sys
import numpy as np
import wave
sys.path.insert(0, str(Path(r"E:\program\1project\video\work\voice-noise-20261106")))
from analyze import read_wav
from stretch_cmp import metrics

ROOT = Path(r"E:\program\1project\video")
WORK = ROOT / "work" / "tts-next-20261106"
OUT = WORK / "out" / "listen"
OUT.mkdir(parents=True, exist_ok=True)

CLIPS = [
    ("00_current_L7", ROOT / "work/voice-noise-20261106/ab_long/L7_orig10_finish.wav", None,
     "对照：当前生产链（VoxCPM2 轻语 prompt + 10 步 + atempo + 后期）"),
    ("01_qwen3", WORK / "out/qwen3_15s.wav", None,
     "Qwen3-TTS 1.7B Base：3 秒克隆 + 原速（无变速）"),
    ("02_cosyvoice3", WORK / "out/cosyvoice3_15s.wav", None,
     "CosyVoice3 0.5B：zero-shot 克隆 + speed=1.0（无 atempo）"),
    ("03_cosyvoice3_breath", WORK / "out/cosyvoice3_15s_breath.wav", None,
     "CosyVoice3：[breath] 显式放在三个句号后"),
    ("04_cosyvoice3_slow", WORK / "out/cosyvoice3_slow.wav", None,
     "CosyVoice3：speed=0.78 原生减速（目标语速，无 atempo）"),
]


def write(path, y, sr):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())


def gain_to(y, target_db=-21.0):
    rms = np.sqrt(np.mean(y ** 2)) + 1e-12
    return y * (10 ** (target_db / 20) / rms)


rows = []
for name, src, _, desc in CLIPS:
    y, sr = read_wav(src)
    y = gain_to(y)
    dst = OUT / f"{name}.wav"
    write(dst, y, sr)
    m = metrics(str(dst))
    rows.append((name, dst, desc, sr, m))
    print(f"{name:24s} sr={sr} dur={m['dur']:.2f}s inr={m['inr_mean']:.3f} flux90={m['flux_p90']:.2f}")

html = ["<!doctype html><meta charset='utf-8'><title>助眠 TTS 新方案试听</title>",
        "<style>body{background:#12161c;color:#e8eef6;font:15px/1.65 system-ui,'Microsoft YaHei';max-width:960px;margin:36px auto;padding:0 20px}",
        "h1{font-size:21px;font-weight:600}.lead{color:#9fb0c3;margin-bottom:22px}",
        ".clip{margin:16px 0;padding:14px 18px;background:#1b222c;border-radius:10px;border-left:3px solid #2e3b4a}",
        ".name{font-weight:600;color:#ffd27d}.desc{color:#9fb0c3;margin:3px 0 6px;font-size:13.5px}",
        ".m{color:#6f8095;font-size:12px;margin-bottom:8px}audio{width:100%}</style>",
        "<h1>助眠解说 · 换线试听（Qwen3-TTS vs CosyVoice3）</h1>",
        "<div class='lead'>同一段 70 字、同一参考音（b2-warm-male 16s）、统一到 −21 dBFS RMS。"
        "重点听三处：<b>句号后的换气</b>、<b>“溪水/细小”的字头</b>、<b>整体有没有金属拖尾</b>。<br>"
        "00 是现在成片的声音，01–04 是新模型。</div>"]
for name, p, desc, sr, m in rows:
    html.append(f"<div class='clip'><div class='name'>{name}</div><div class='desc'>{desc}</div>"
                f"<div class='m'>时长 {m['dur']:.2f}s · {sr//1000} kHz · 谐波间噪声 {m['inr_mean']:.3f}（越低越干净）"
                f" · 通量 p90 {m['flux_p90']:.2f}</div>"
                f"<audio controls preload='none' src='{p.name}'></audio></div>")
(OUT / "index.html").write_text("\n".join(html), encoding="utf-8")
print("HTML ->", OUT / "index.html")
