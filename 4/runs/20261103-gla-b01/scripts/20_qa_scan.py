# -*- coding: utf-8 -*-
"""全片 QA 扫描门禁(源于 newton 467s 白屏事故,2026-10-17)。

检查项:
1. 白屏:连续 YAVG≥225 且 ≥1.0s 的区间(纯色空页)→ FAIL
2. 黑屏:连续 YAVG≤12 且 ≥2.0s 的区间 → FAIL(结尾淡出黑 ≤3s 豁免)
3. 时长与帧率记录;可选音轨时长差 ≤1 帧
4. 解码帧序 CFR/单调性校验

用法:python 20_qa_scan.py [video.mp4] [audio.wav]
默认 video=watch/glacier-river_with_audio.mp4, audio=video/final/…narration.wav
输出:logs/qa_scan/QA_SCAN_<name>.json + 控制台摘要;FAIL 时退出码 1。
移植自 newton 20_qa_scan.py。本集附加关注项(人工复核,脚本不判):
c4 全片最暗段收束是否稳、c6-s09 是否全片唯一最亮帧、焰/光缓变无闪烁。
"""
import json, re, subprocess, sys
from pathlib import Path

EP = Path(r"E:\program\1project\video\4")
RUN = EP / "runs" / "20261103-gla-b01"
FFMPEG = r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"
FFPROBE = FFMPEG.replace("ffmpeg.exe", "ffprobe.exe")
WHITE_YAVG, WHITE_MIN_S = 225, 1.0
BLACK_YAVG, BLACK_MIN_S = 12, 2.0


def probe(p, entries):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", entries,
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return r.stdout.strip()


def probe_dur(p):
    return float(probe(p, "format=duration"))


def luma_runs(video):
    """2fps 采样 YAVG,返回 (frames, 白屏区间, 黑屏区间)。"""
    r = subprocess.run([FFMPEG, "-nostats", "-i", str(video), "-map", "0:v",
                        "-vf", "fps=2,scale=160:90,signalstats,metadata=print:file=-",
                        "-f", "null", "-"], capture_output=True, text=True)
    frames, cur = [], {}
    for line in r.stdout.splitlines():
        line = line.strip()
        m = re.match(r"frame:\d+\s+pts:\d+\s+pts_time:([\d.]+)", line)
        if m:
            if cur:
                frames.append(cur)
            cur = {"t": float(m.group(1))}
        else:
            kv = line.split("=", 1)
            if len(kv) == 2:
                cur[kv[0].strip().replace("lavfi.signalstats.", "")] = kv[1].strip()
    if cur:
        frames.append(cur)

    def runs_of(pred, min_s):
        out, start = [], None
        for f in frames:
            y = float(f.get("YAVG", 128))
            if pred(y) and start is None:
                start = f["t"]
            elif not pred(y) and start is not None:
                if f["t"] - start >= min_s:
                    out.append((round(start, 2), round(f["t"], 2)))
                start = None
        if start is not None and frames[-1]["t"] - start >= min_s:
            out.append((round(start, 2), round(frames[-1]["t"], 2)))
        return out

    return frames, runs_of(lambda y: y >= WHITE_YAVG, WHITE_MIN_S), \
        runs_of(lambda y: y <= BLACK_YAVG, BLACK_MIN_S)


def decoded_pts_cfr(video, n=300):
    """解码帧序(展示顺序)CFR/单调性校验。
    注意:不能用 packet=pts_time —— 那是 B 帧存储顺序(dts 交织),天然非单调,会误报。"""
    r = subprocess.run([FFMPEG, "-i", str(video), "-vf", "showinfo",
                        "-frames:v", str(n), "-f", "null", "-"],
                       capture_output=True, text=True)
    pts = [float(m) for m in re.findall(r"pts_time:([\d.]+)", r.stderr)]
    if len(pts) < 10:
        return None, "showinfo parse failed"
    deltas = [(b - a) * 1000 for a, b in zip(pts, pts[1:])]
    mono = all(d > 0 for d in deltas)
    uniform = all(abs(d - 33.333) < 2.0 for d in deltas)
    return (mono and uniform), dict(min=round(min(deltas), 2), max=round(max(deltas), 2),
                                    n=len(deltas), monotonic=mono, uniform30fps=uniform)


def main():
    video = Path(sys.argv[1]) if len(sys.argv) > 1 else RUN / "watch/glacier-river_with_audio.mp4"
    audio = Path(sys.argv[2]) if len(sys.argv) > 2 else EP / "video/final/glacier-river_narration.wav"
    frames, whites, blacks = luma_runs(video)
    vdur = probe_dur(video)
    # 结尾淡出产生的黑屏豁免:起点在最后 3s 内
    blacks = [b for b in blacks if b[0] < vdur - 3.0]
    rep = {
        "video": str(video), "duration_s": vdur,
        "fps_samples": len(frames), "scan_fps": 2,
        "white_runs": whites, "black_runs": blacks,
        "audio": str(audio) if audio.exists() else None,
        "audio_duration_s": probe_dur(audio) if audio.exists() else None,
    }
    if audio.exists():
        rep["av_diff_s"] = round(vdur - rep["audio_duration_s"], 3)
    cfr_ok, cfr_info = decoded_pts_cfr(video)
    rep["decoded_pts_cfr"] = cfr_info
    fails = []
    if whites:
        fails.append(f"white runs: {whites}")
    if blacks:
        fails.append(f"black runs: {blacks}")
    if audio.exists() and abs(rep.get("av_diff_s", 0)) > 1 / 30 + 0.005:
        fails.append(f"av diff {rep['av_diff_s']}s > 1 frame")
    if cfr_ok is False:
        fails.append(f"decoded pts not CFR/monotonic: {cfr_info}")
    rep["verdict"] = "FAIL" if fails else "PASS"
    rep["fails"] = fails

    outdir = RUN / "logs" / "qa_scan"
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"QA_SCAN_{video.stem}.json"
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[{rep['verdict']}] {video.name} {vdur:.3f}s  "
          f"white_runs={len(whites)} black_runs={len(blacks)}"
          + (f"  av_diff={rep['av_diff_s']}s" if audio.exists() else ""))
    for f in fails:
        print("  FAIL:", f)
    for a, b in whites[:10]:
        print(f"  white: {a}-{b} ({b-a:.1f}s)")
    print(f"-> {out}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
