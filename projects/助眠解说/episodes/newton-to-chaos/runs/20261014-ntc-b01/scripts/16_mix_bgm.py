"""混音：旁白 + 助眠统一BGM（章鱼同款参数）。

- BGM: leberch-sleep-583079.mp3 → 48k 立体声 float32
- 循环: 3秒 overlap 交叉淡出
- 增益: BGM RMS 调到低于旁白 RMS 18 dB
- 首尾淡入淡出: 5秒
- 片头段（intro_data 部分）无 BGM
- 峰值保护 ≤ 0.98
- 输出 mixed.wav (PCM_16) + 与视频合成 watch cut (AAC 256k)
"""
import json, subprocess, shutil
from pathlib import Path
import numpy as np
import soundfile as sf

EP = Path(r"E:/program/1project/video/projects/助眠解说/episodes/newton-to-chaos")
RUN = EP / "runs/20261014-ntc-b01"
SR = 48000
FFMPEG = r"C:/Users/10060/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.2-full_build-shared/bin/ffmpeg.exe"
FFPROBE = r"C:/Users/10060/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.2-full_build-shared/bin/ffprobe.exe"

BGM_SRC = Path(r"E:/program/1project/video/assets/助眠解说/audio/bgm/sleep-unified-v1/leberch-sleep-583079.mp3")
CLEAN_MP4 = EP / "video/final/newton-to-chaos_clean.mp4"
NARR_WAV = EP / "video/final/newton-to-chaos_narration.wav"
INTRO_WAV = RUN / "chapters/intro.wav"
INTRO_TL = RUN / "intro_timeline.json"
BODY_NARR = RUN / "chapters/body_narration.wav"

MIX_WAV = RUN / "audio/mixed.wav"
MUSIC_PCM = RUN / "audio/music_48k_f32.wav"
WATCH_DIR = RUN / "watch"
WATCH_DIR.mkdir(parents=True, exist_ok=True)
WATCH_MP4 = WATCH_DIR / "newton-to-chaos_with_audio.mp4"


def ff(*args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg failed: " + (r.stderr or "")[-600:])


def probe_dur(p):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return float(r.stdout.strip())


# 1. 读取片头时长（确定 BGM 起始偏移）
intro_tl = json.load(open(INTRO_TL, encoding="utf-8"))
intro_seconds = intro_tl["intro_seconds"]
intro_samples = round(intro_seconds * SR)
print(f"intro: {intro_seconds:.3f}s / {intro_samples} samples (no BGM)")

# 2. 读取整段旁白（已是 intro+body 拼接的 narration.wav）
narr, sr_n = sf.read(str(NARR_WAV), dtype="float32", always_2d=True)
assert sr_n == SR, f"narration sr {sr_n} != {SR}"
if narr.shape[1] == 1:
    narr = np.repeat(narr, 2, axis=1)  # 单声道转立体声混音用
print(f"narration total: {narr.shape[0]/SR:.3f}s / {narr.shape[0]} samples / {narr.shape[1]}ch")

body_samples = narr.shape[0] - intro_samples
assert body_samples > 0, f"body_samples={body_samples}"
print(f"body samples: {body_samples} = {body_samples/SR:.3f}s")

# 3. 解码 BGM 为 48k 立体声 float32
print("decoding BGM to 48k f32...")
ff(FFMPEG, "-y", "-i", str(BGM_SRC), "-ar", str(SR), "-ac", "2",
   "-c:a", "pcm_f32le", str(MUSIC_PCM))
music, sr_m = sf.read(str(MUSIC_PCM), dtype="float32", always_2d=True)
assert sr_m == SR
print(f"music: {music.shape[0]/SR:.3f}s / {music.shape}")

# 4. 循环到 body 时长（3 秒 overlap 交叉淡出）
overlap = SR * 3
looped = np.zeros((body_samples, 2), dtype="float32")
cursor = 0
loop_count = 0
while cursor < body_samples:
    n = min(len(music), body_samples - cursor)
    chunk = music[:n].copy()
    if cursor:  # 不是第一段：开头 3s 淡入
        k = min(overlap, n)
        chunk[:k] *= np.linspace(0, 1, k)[:, None]
    if cursor + n < body_samples:  # 不是最后一段：末尾 3s 淡出
        chunk[-overlap:] *= np.linspace(1, 0, overlap)[:, None]
    looped[cursor:cursor + n] += chunk
    cursor += len(music) - overlap
    loop_count += 1
print(f"looped {loop_count} segments, total {looped.shape[0]/SR:.3f}s")

# 5. 增益：BGM RMS 调到低于旁白 RMS 18 dB
# 旁白 RMS 仅取正文段（避免片头静段拉低 RMS）
body_narr_mono = narr[intro_samples:, 0]
voice_rms = float(np.sqrt(np.mean(body_narr_mono ** 2)))
music_rms = float(np.sqrt(np.mean(looped ** 2)))
gain = voice_rms * 10 ** (-10 / 20) / music_rms  # BGM 低于旁白 10 dB（用户 2026-10-14 19:00 进一步上调，原 -14dB 仍偏小）
print(f"voice_rms={voice_rms:.6f}  music_rms={music_rms:.6f}  gain={gain:.4f} (BGM -18dB below voice)")
looped *= gain

# 6. 首尾 5s 淡入淡出
fade = SR * 5
looped[:fade] *= np.linspace(0, 1, fade)[:, None]
looped[-fade:] *= np.linspace(1, 0, min(fade, looped.shape[0]))[:, None]

# 7. 拼到 narration 上：片头段保持纯旁白，正文段叠加 BGM
mixed = narr.copy()
mixed[intro_samples:] += looped

# 8. 峰值保护
peak = float(np.max(np.abs(mixed)))
if peak > 0.98:
    scale = 0.98 / peak
    mixed *= scale
    print(f"peak {peak:.4f} > 0.98, scaled by {scale:.4f}")
else:
    print(f"peak {peak:.4f} <= 0.98, no scaling")

# 9. 输出 mixed.wav (PCM_16)
sf.write(str(MIX_WAV), mixed, SR, subtype="PCM_16")
print(f"wrote mixed.wav: {MIX_WAV}  ({mixed.shape[0]/SR:.3f}s)")

# 10. 合成 watch cut 视频（视频 copy + AAC 256k）
print("muxing watch cut (video copy + aac 256k)...")
ff(FFMPEG, "-y", "-i", str(CLEAN_MP4), "-i", str(MIX_WAV),
   "-map", "0:v", "-map", "1:a",
   "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
   "-movflags", "+faststart", str(WATCH_MP4))

# 11. 验证
vdur = probe_dur(WATCH_MP4)
adur = probe_dur(MIX_WAV)
cdur = probe_dur(CLEAN_MP4)
print(f"watch_mp4={vdur:.3f}s  mixed={adur:.3f}s  clean={cdur:.3f}s  diff_v_a={vdur-adur:.3f}s")

# 12. manifest
manifest = {
    "status": "rendered-awaiting-user-review",
    "rule_source": "rules/助眠解说/background-music.md + manual-post-production.md (user explicitly commissioned mix)",
    "episode": "newton-to-chaos",
    "music": str(BGM_SRC),
    "music_id": "SLEEP-BGM-UNIFIED-001",
    "music_gain": gain,
    "music_rms_below_voice_db": 10,
    "music_crossfade_seconds": 3,
    "music_fade_seconds": 5,
    "intro_music": False,
    "subtitles": False,
    "intro_seconds": intro_seconds,
    "body_seconds": body_samples / SR,
    "total_seconds": mixed.shape[0] / SR,
    "peak": peak,
    "peak_scaled": peak > 0.98,
    "deliverables": {
        "mixed_wav": str(MIX_WAV),
        "watch_cut_mp4": str(WATCH_MP4),
    },
    "preserved_untouched": [
        str(CLEAN_MP4),
        str(NARR_WAV),
    ],
    "durations": {
        "watch_mp4": vdur,
        "mixed_wav": adur,
        "clean_mp4": cdur,
        "diff_v_a": vdur - adur,
    },
}
manifest_path = RUN / "audio/mix_manifest.json"
json.dump(manifest, open(manifest_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"manifest: {manifest_path}")
print("DONE")
