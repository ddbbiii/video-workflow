"""分析当前混音的各层 dB（RMS dBFS 与峰值）。"""
import numpy as np
import soundfile as sf
from pathlib import Path

EP = Path(r"E:/program/1project/video/projects/助眠解说/episodes/newton-to-chaos")
RUN = EP / "runs/20261014-ntc-b01"
SR = 48000

NARR = EP / "video/final/newton-to-chaos_narration.wav"           # 纯旁白（intro+body）
MIXED = RUN / "audio/mixed.wav"                                    # 旁白+BGM
MUSIC_PCM = RUN / "audio/music_48k_f32.wav"                        # BGM 原始 48k
INTRO_TL_PATH = RUN / "intro_timeline.json"

import json
intro_s = json.load(open(INTRO_TL_PATH, encoding="utf-8"))["intro_seconds"]
intro_samples = round(intro_s * SR)
print(f"intro_seconds={intro_s:.3f}  intro_samples={intro_samples}")
print(f"body_seconds={(0):.3f}")  # placeholder, calc below


def stats(arr, label):
    """arr: float32 mono or (N,2)"""
    if arr.ndim == 2:
        mono = arr.mean(axis=1)
    else:
        mono = arr
    rms = float(np.sqrt(np.mean(mono ** 2)))
    peak = float(np.max(np.abs(mono)))
    rms_db = 20 * np.log10(rms) if rms > 0 else -np.inf
    peak_db = 20 * np.log10(peak) if peak > 0 else -np.inf
    print(f"{label:30s}  rms={rms:.6f}  rms_dBFS={rms_db:+.2f}  peak={peak:.4f}  peak_dBFS={peak_db:+.2f}")
    return rms, peak, rms_db, peak_db


# 1. 旁白
narr, _ = sf.read(str(NARR), dtype="float32", always_2d=True)
narr_mono = narr.mean(axis=1) if narr.ndim == 2 else narr
body_narr = narr_mono[intro_samples:]
stats(narr_mono, "narration full")
stats(narr_mono[:intro_samples], "narration intro-only")
stats(body_narr, "narration body-only (voice ref)")

# 2. BGM 原始
music, _ = sf.read(str(MUSIC_PCM), dtype="float32", always_2d=True)
stats(music, "BGM raw (full track 352s)")

# 3. mixed
mixed, _ = sf.read(str(MIXED), dtype="float32", always_2d=True)
mixed_mono = mixed.mean(axis=1) if mixed.ndim == 2 else mixed
stats(mixed_mono, "mixed full (voice+bgm)")
stats(mixed_mono[:intro_samples], "mixed intro (voice only, no bgm)")
stats(mixed_mono[intro_samples:], "mixed body (voice+bgm)")

# 4. 反推 BGM 实际音量
# mixed_body = voice_body + bgm_body_loop_gain
# bgm_actual = mixed_body - voice_body  (逐样本相减，理论上得到 BGM 实际混入信号)
voice_body = body_narr
mixed_body = mixed_mono[intro_samples:]
# 长度对齐
n = min(len(voice_body), len(mixed_body))
bgm_actual = mixed_body[:n] - voice_body[:n]
stats(bgm_actual, "BGM as-mixed (mixed_body - voice_body)")

# 5. 差值
print()
print("--- 差值（BGM 低于旁白多少 dB） ---")
v_rms = float(np.sqrt(np.mean(body_narr ** 2)))
b_rms = float(np.sqrt(np.mean(bgm_actual ** 2)))
print(f"voice body RMS dBFS  = {20*np.log10(v_rms):+.2f}")
print(f"bgm   body RMS dBFS  = {20*np.log10(b_rms):+.2f}")
print(f"difference (voice - bgm) = {20*np.log10(v_rms) - 20*np.log10(b_rms):+.2f} dB")
