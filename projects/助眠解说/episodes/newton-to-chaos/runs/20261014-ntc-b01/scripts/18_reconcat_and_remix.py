# -*- coding: utf-8 -*-
"""最小化重拼：新片头 + 旧 body_padded → clean.mp4（concat copy，秒级）。
然后重混音（narration 不变，BGM 参数不变 -10dB）→ 新 watch cut。
用户 2026-10-14 19:05 改片头艺术字（每段一组），19:15 重渲片头完成。
"""
import subprocess, json
from pathlib import Path

EP = Path(r"E:/program/1project/video/projects/助眠解说/episodes/newton-to-chaos")
RUN = EP / "runs/20261014-ntc-b01"
INTRO_VID = RUN / "intro/batch-20261018-short/clean-intro.mp4"
BODY_PADDED = RUN / "chapters/body_video_padded.mp4"
CLEAN = EP / "video/final/newton-to-chaos_clean.mp4"
FFMPEG = r"C:/Users/10060/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.2-full_build-shared/bin/ffmpeg.exe"
FFPROBE = r"C:/Users/10060/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.2-full_build-shared/bin/ffprobe.exe"

def probe_dur(p):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return float(r.stdout.strip())

# 1. concat intro + body_padded → clean（concat demuxer, copy 模式）
print(f"intro: {probe_dur(INTRO_VID):.3f}s  body_padded: {probe_dur(BODY_PADDED):.3f}s")
list_file = RUN / "reconcat_list.txt"
list_file.write_text(f"file '{INTRO_VID.as_posix()}'\nfile '{BODY_PADDED.as_posix()}'\n", encoding="utf-8")
CLEAN.parent.mkdir(parents=True, exist_ok=True)
if CLEAN.exists():
    CLEAN.unlink()
# 先尝试 copy 模式（秒级），失败则重编码
r = subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
                    "-c", "copy", "-movflags", "+faststart", str(CLEAN)],
                   capture_output=True, text=True)
if r.returncode != 0:
    print("copy concat failed, falling back to re-encode...")
    r = subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(CLEAN)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("concat re-encode failed: " + (r.stderr or "")[-500:])
clean_dur = probe_dur(CLEAN)
print(f"clean.mp4: {clean_dur:.3f}s ({CLEAN.stat().st_size//1024//1024}MB)")

# 1b. 重建 narration(片头音频变更时必须;intro.wav + body_narration.wav)
INTRO_AUDIO = RUN / "chapters/intro.wav"
BODY_AUDIO = RUN / "chapters/body_narration.wav"
narr = EP / "video/final/newton-to-chaos_narration.wav"
if INTRO_AUDIO.exists() and BODY_AUDIO.exists():
    narr_list = RUN / "narration_rebuild.txt"
    narr_list.write_text(f"file '{INTRO_AUDIO.as_posix()}'\nfile '{BODY_AUDIO.as_posix()}'\n", encoding="utf-8")
    r = subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(narr_list),
                        "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "1", str(narr)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("narration rebuild failed: " + (r.stderr or "")[-500:])
    print(f"narration.wav rebuilt: {probe_dur(narr):.3f}s "
          f"(intro {probe_dur(INTRO_AUDIO):.3f} + body {probe_dur(BODY_AUDIO):.3f})")

# 2. 重混音（narration 不变，BGM -10dB 参数不变）→ 新 mixed.wav + watch cut
print("\n=== re-mix BGM (-10dB) ===")
r = subprocess.run(["E:/program/1project/video/shared/runtime/engines/tts/voxcpm/.venv/Scripts/python.exe",
                    str(RUN / "scripts/16_mix_bgm.py")],
                   capture_output=True, text=True, cwd=str(EP))
print(r.stdout[-800:] if r.stdout else "")
if r.returncode != 0:
    print("STDERR:", (r.stderr or "")[-500:])
    raise RuntimeError("mix failed")

# 3. 验证
mix_wav = RUN / "audio/mixed.wav"
watch = RUN / "watch/newton-to-chaos_with_audio.mp4"
print(f"\n=== final ===")
print(f"clean: {probe_dur(CLEAN):.3f}s  narration: {probe_dur(narr):.3f}s  diff: {probe_dur(CLEAN)-probe_dur(narr):.3f}s")
print(f"mixed: {probe_dur(mix_wav):.3f}s  watch: {probe_dur(watch):.3f}s  diff: {probe_dur(watch)-probe_dur(mix_wav):.3f}s")
print("DONE")
