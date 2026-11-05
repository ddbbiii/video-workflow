# -*- coding: utf-8 -*-
"""最终重拼(2026-10-20 收尾;v5 复跑):intro(batch-20261020-v5) + 正文 v3 → 最终交付。

v5:音轨未动(intro.wav 同 v4),字幕 r3 不变;仅片头末卡换回分句文字卡重渲。

- clean = intro 视频流 + body v3 视频流(concat copy,正文 v3 零重编码)
          + 重建 narration.wav(intro.wav 变了必须重拼;48k PCM 单声道)
          → AAC 160k 48k mono(口径同 15_assemble 正文 clean)
- BGM 不混(用户未委托;16_mix_bgm 不运行,归用户)
- 校验:音视差 ≤1 帧;总时长 ≈ intro + body;"接下来的 35 分钟"自洽
  (|总时长-2100s| > 30s 即 FAIL 停下报告,不改口播)。

移植自 newton 18_reconcat_and_remix.py(siffre 适配:body 源为 media/body_video.mp4 v3,
去 BGM 重混,加 35 分钟门禁)。
"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import AUDIO_PLAN as AP  # noqa: F401

EP = HERE.parents[2]
RUN = EP / "runs" / "20261018-sbt-b01"
INTRO_BATCH = "batch-20261020-v5"          # 与 14_build_intro.py OUT 一致(v5 片头:末卡回归分句文字卡)
INTRO_VID = RUN / f"intro/{INTRO_BATCH}/clean-intro.mp4"
INTRO_TL = RUN / "intro_timeline.json"
BODY_VID = RUN / "media" / "body_video.mp4"          # 正文 v3(视频流,61944f)
BODY_AUDIO = RUN / "chapters" / "body_narration.wav"
INTRO_AUDIO = RUN / "chapters" / "intro.wav"
CLEAN = EP / "video/final/siffre-beyond-time_clean.mp4"
NARR = EP / "video/final/siffre-beyond-time_narration.wav"
FFMPEG = r"C:/Users/10060/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.2-full_build-shared/bin/ffmpeg.exe"
FFPROBE = FFMPEG.replace("ffmpeg.exe", "ffprobe.exe")
FPS = 30
CLAIM_MINUTES = 35            # 片头口播回填值(锁定稿)
CLAIM_TOL_S = 30              # 收尾任务书红线:±30s 以上不自洽即停


def probe_dur(p):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return float(r.stdout.strip())


def probe(p, entries):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", entries,
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return r.stdout.strip()


def main():
    # ---- 0. 输入体检 ----
    intro_s = json.loads(INTRO_TL.read_text(encoding="utf-8"))["intro_seconds"]
    iv_dur, bv_dur = probe_dur(INTRO_VID), probe_dur(BODY_VID)
    print(f"intro: {iv_dur:.3f}s (audio {intro_s:.3f}s)  body v3: {bv_dur:.3f}s")
    for name, p in (("intro", INTRO_VID), ("body", BODY_VID)):
        info = probe(p, "stream=codec_name,width,height,r_frame_rate,pix_fmt,profile,level")
        print(f"  {name}: {info}")

    # ---- 1. concat intro + body v3(copy 模式,秒级;v3 零重编码)----
    list_file = RUN / "reconcat_final.txt"
    list_file.write_text(f"file '{INTRO_VID.as_posix()}'\nfile '{BODY_VID.as_posix()}'\n",
                         encoding="utf-8")
    concat_v = RUN / "media" / "final_concat_video.mp4"
    r = subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
                        "-c", "copy", "-an", str(concat_v)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("copy concat failed:", (r.stderr or "")[-500:])
        raise SystemExit("concat copy 失败:检查 intro 与 body 编码参数一致性后重试")
    cv_dur = probe_dur(concat_v)
    cv_frames = int(float(probe(concat_v, "stream=nb_frames") or 0) or
                    (cv_dur * FPS))
    print(f"concat video: {cv_dur:.3f}s (~{cv_frames}f)")

    # ---- 2. 重建 narration(intro.wav + body_narration.wav,48k PCM 单声道)----
    narr_list = RUN / "narration_rebuild.txt"
    narr_list.write_text(f"file '{INTRO_AUDIO.as_posix()}'\nfile '{BODY_AUDIO.as_posix()}'\n",
                         encoding="utf-8")
    r = subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(narr_list),
                        "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "1", str(NARR)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("narration rebuild failed: " + (r.stderr or "")[-500:])
    n_dur = probe_dur(NARR)
    print(f"narration.wav rebuilt: {n_dur:.3f}s "
          f"(intro {probe_dur(INTRO_AUDIO):.3f} + body {probe_dur(BODY_AUDIO):.3f})")

    # ---- 3. clean = concat 视频 + narration(AAC 160k 48k mono,口径同 15 号)----
    CLEAN.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([FFMPEG, "-y", "-i", str(concat_v), "-i", str(NARR),
                        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "1",
                        "-movflags", "+faststart", str(CLEAN)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("clean mux failed: " + (r.stderr or "")[-500:])
    clean_dur = probe_dur(CLEAN)
    av_diff = clean_dur - n_dur
    print(f"CLEAN {clean_dur:.3f}s ({CLEAN.stat().st_size // 1024 // 1024}MB) "
          f"av_diff {av_diff * 1000:.1f}ms")

    # ---- 4. 校验 ----
    fails = []
    if abs(av_diff) > 1 / FPS + 0.005:
        fails.append(f"音视差 {av_diff:.3f}s 超 1 帧")
    expect = intro_s + probe_dur(BODY_AUDIO)
    if abs(clean_dur - expect) > 0.05:
        fails.append(f"clean {clean_dur:.3f}s != intro+body音频 {expect:.3f}s")
    claim = CLAIM_MINUTES * 60
    margin = clean_dur - claim
    print(f"35 分钟自洽: total {clean_dur:.1f}s vs claim {claim}s (margin {margin:+.1f}s, "
          f"tol ±{CLAIM_TOL_S}s)")
    if abs(margin) > CLAIM_TOL_S:
        fails.append(f"总时长与片头口播 35 分钟不自洽(margin {margin:+.1f}s > ±30s):"
                     "按红线停下报告,不改口播")
    if fails:
        for f_ in fails:
            print("FAIL:", f_)
        return 1
    print(f"\nOK -> {CLEAN}\n   -> {NARR}")
    print(f"total {clean_dur / 60:.2f}min; BGM 未混(归用户);字幕起点=片头实测 {intro_s:.3f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
