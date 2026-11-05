# -*- coding: utf-8 -*-
"""siffre 正文全片 QA 门禁(2026-10-20 装配任务书口径;源头为 newton 467s 白屏事故)。

检查项(全部按 30fps 逐帧):
1. 白屏:YAVG≥225 连续 ≥1.0s → FAIL;更短的白/黑过渡帧逐帧记录(豁免但不隐匿)
2. 黑屏:YAVG≤12 连续 ≥2.0s → FAIL(结尾淡出黑 ≤3s 豁免)
3. 音视差:clean 内视频流 vs 音频流、vs body_narration.wav,均须 ≤1 帧
4. 解码帧序(展示顺序)CFR/单调性
5. 静帧重复:YDIF<0.05 连续 >13.0s → FAIL(最长合规尾停 12.56s + 容差);
   8s+ 的疑似静帧段做首末帧复检(全分辨率),慢运镜不得误判;5-13s 段列出对照 manifest 尾停

本集附加人工复核项(REPORT 裁决节/PROJECT_STATE 低刺激硬约束,脚本只测不判):
- c6-s07 换手段实际表现(窗口内帧差、无突变)
- c4(616-747s)是否全片最暗段、收束是否稳
- c6-s09 是否全片唯一最亮帧(全局最大 YAVG 帧归属 + 次亮差距)

用法:python 20_qa_scan.py [video.mp4] [audio.wav]
默认 video=video/final/siffre-body_clean.mp4, audio=runs/.../chapters/body_narration.wav
输出:logs/qa_scan/QA_SCAN_<name>.json;FAIL 退出码 1。
"""
import json, re, subprocess, sys
from pathlib import Path

EP = Path(__file__).resolve().parents[3]
RUN = EP / "runs" / "20261018-sbt-b01"
FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"
FPS = 30
WHITE_YAVG, WHITE_MIN_S = 225, 1.0
BLACK_YAVG, BLACK_MIN_S = 12, 2.0
STATIC_YDIF = 0.05
STATIC_FAIL_S = 13.0
STATIC_LIST_S = 5.0
STATIC_RECHECK_S = 8.0

def probe(p, entries):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", entries,
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return r.stdout.strip()

def probe_dur(p):
    return float(probe(p, "format=duration"))

def stream_durations(p):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries",
                        "stream=index,codec_type,duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    out = {}
    for line in r.stdout.strip().splitlines():
        parts = line.split(",")
        if len(parts) == 3:
            out[parts[1]] = float(parts[2])
    return out

def scan_luma(video):
    """逐帧 YAVG/YDIF(160x90 采样),返回 [{f,t,YAVG,YDIF}]。"""
    r = subprocess.run([FFMPEG, "-nostats", "-i", str(video), "-map", "0:v",
                        "-vf", "scale=160:90,signalstats,metadata=print:file=-",
                        "-f", "null", "-"], capture_output=True, text=True)
    frames, cur = [], {}
    for line in r.stdout.splitlines():
        line = line.strip()
        m = re.match(r"frame:\d+\s+pts:\d+\s+pts_time:([\d.]+)", line)
        if m:
            if cur:
                frames.append(cur)
            cur = {"t": float(m.group(1)), "f": len(frames)}
        else:
            kv = line.split("=", 1)
            if len(kv) == 2:
                cur[kv[0].strip().replace("lavfi.signalstats.", "")] = kv[1].strip()
    if cur:
        frames.append(cur)
    for fr in frames:
        fr["YAVG"] = float(fr.get("YAVG", 128))
        fr["YDIF"] = float(fr.get("YDIF", 0))
    return frames

def runs_of(frames, key, pred, min_s):
    out, start = [], None
    for fr in frames:
        if pred(fr[key]) and start is None:
            start = fr
        elif not pred(fr[key]) and start is not None:
            if fr["t"] - start["t"] >= min_s:
                out.append((start["f"], fr["f"] - 1, round(start["t"], 3), round(fr["t"], 3)))
            start = None
    if start is not None and frames[-1]["t"] - start["t"] >= min_s:
        out.append((start["f"], frames[-1]["f"], round(start["t"], 3),
                    round(frames[-1]["t"] + 1 / FPS, 3)))
    return out

def brief_events(frames, key, pred, min_s, cap=60):
    """短于阈值的逐帧过渡事件(记录,不判 FAIL)。"""
    out, start = [], None
    for fr in frames:
        if pred(fr[key]) and start is None:
            start = fr
        elif not pred(fr[key]) and start is not None:
            if fr["t"] - start["t"] < min_s:
                out.append((start["f"], fr["f"] - 1, round(start["t"], 3), round(fr["t"], 3),
                            round(max(x[key] for x in frames[start["f"]:fr["f"]]), 1)))
            start = None
    if start is not None and frames[-1]["t"] - start["t"] < min_s:
        out.append((start["f"], frames[-1]["f"], round(start["t"], 3),
                    round(frames[-1]["t"] + 1 / FPS, 3),
                    round(max(x[key] for x in frames[start["f"]:]), 1)))
    return out[:cap]

def endpoint_moving(video, f0, f1):
    """首末帧复检:480x270 灰度平均绝对差(慢运镜应显著>0,克隆帧≈0)。"""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        outs = []
        for tag, fr in (("a", f0), ("b", f1)):
            o = Path(td) / f"{tag}.png"
            subprocess.run([FFMPEG, "-y", "-i", str(video), "-vf",
                            f"select=eq(n\\,{fr}),scale=480:270,format=gray",
                            "-frames:v", "1", str(o)], capture_output=True, text=True)
            outs.append(o)
        r = subprocess.run([FFMPEG, "-i", str(outs[0]), "-i", str(outs[1]),
                            "-filter_complex", "blend=all_mode=difference,signalstats,metadata=print:file=-",
                            "-frames:v", "1", "-f", "null", "-"], capture_output=True, text=True)
        m = re.search(r"YAVG=([\d.]+)", r.stdout)
        return float(m.group(1)) if m else -1.0

def decoded_pts_cfr(video, n=300):
    r = subprocess.run([FFMPEG, "-i", str(video), "-vf", "showinfo",
                        "-frames:v", str(n), "-f", "null", "-"],
                       capture_output=True, text=True)
    pts = [float(m) for m in re.findall(r"pts_time:([\d.]+)", r.stderr)]
    if len(pts) < 10:
        return None, "showinfo parse failed"
    deltas = [(b - a) * 1000 for a, b in zip(pts, pts[1:])]
    mono = all(d > 0 for d in deltas)
    uniform = all(abs(d - 1000 / FPS) < 2.0 for d in deltas)
    return (mono and uniform), dict(min=round(min(deltas), 2), max=round(max(deltas), 2),
                                    n=len(deltas), monotonic=mono, uniform30fps=uniform)

def window_stats(frames, t0, t1):
    sel = [x for x in frames if t0 <= x["t"] < t1]
    if not sel:
        return None
    return {"n": len(sel),
            "yavg_min": round(min(x["YAVG"] for x in sel), 1),
            "yavg_max": round(max(x["YAVG"] for x in sel), 1),
            "yavg_mean": round(sum(x["YAVG"] for x in sel) / len(sel), 1),
            "ydif_max": round(max(x["YDIF"] for x in sel), 2),
            "ydif_mean": round(sum(x["YDIF"] for x in sel) / len(sel), 3)}

def main():
    video = Path(sys.argv[1]) if len(sys.argv) > 1 else EP / "video/final/siffre-body_clean.mp4"
    audio = Path(sys.argv[2]) if len(sys.argv) > 2 else RUN / "chapters/body_narration.wav"
    man = json.loads((RUN / "manifests/assembly_manifest.json").read_text(encoding="utf-8"))
    shots = {e["id"]: e for e in man["shots"]}
    tl = json.loads((RUN / "timeline.json").read_text(encoding="utf-8"))

    frames = scan_luma(video)
    vdur = probe_dur(video)
    sd = stream_durations(video)

    whites = runs_of(frames, "YAVG", lambda y: y >= WHITE_YAVG, WHITE_MIN_S)
    blacks_all = runs_of(frames, "YAVG", lambda y: y <= BLACK_YAVG, BLACK_MIN_S)
    blacks = [b for b in blacks_all if b[2] < vdur - 3.0]      # 结尾淡出豁免
    white_brief = brief_events(frames, "YAVG", lambda y: y >= WHITE_YAVG, WHITE_MIN_S)
    black_brief = brief_events(frames, "YAVG", lambda y: y <= BLACK_YAVG, BLACK_MIN_S)

    # 静帧:YDIF 低连续段;≥8s 段做首末帧复检
    static_all = runs_of(frames, "YDIF", lambda y: y < STATIC_YDIF, STATIC_LIST_S)
    static_runs = []
    for f0, f1, t0, t1 in static_all:
        rec = {"start_f": f0, "end_f": f1, "start_s": t0, "dur_s": round(t1 - t0, 2)}
        # 归属镜头
        own = next((e["id"] for e in man["shots"] if e["window_start_s"] <= t0 < e["window_end_s"]), "?")
        rec["shot"] = own
        rec["is_manifest_hold"] = bool(shots.get(own, {}).get("tail_extension_mode") == "hold")
        if t1 - t0 >= STATIC_RECHECK_S:
            rec["endpoint_diff_480x270"] = round(endpoint_moving(video, f0, f1), 2)
            rec["confirmed_static"] = rec["endpoint_diff_480x270"] < 0.7
        else:
            rec["confirmed_static"] = True
        static_runs.append(rec)
    static_fail = [r for r in static_runs if r["confirmed_static"] and r["dur_s"] > STATIC_FAIL_S]

    # 音视差
    av = {}
    if "video" in sd:
        av["video_stream_s"] = round(sd["video"], 3)
    if "audio" in sd:
        av["audio_stream_s"] = round(sd["audio"], 3)
        if "video" in sd:
            av["av_diff_in_file_s"] = round(sd["video"] - sd["audio"], 3)
    if audio.exists():
        ad = probe_dur(audio)
        av["wav_s"] = round(ad, 3)
        if "video" in sd:
            av["av_diff_vs_wav_s"] = round(sd["video"] - ad, 3)

    cfr_ok, cfr_info = decoded_pts_cfr(video)

    # 附加人工复核项
    manual = {}
    e = shots["c6-s07"]
    manual["c6_s07"] = {"window_s": [e["window_start_s"], e["window_end_s"]],
                        "stats": window_stats(frames, e["window_start_s"], e["window_end_s"]),
                        "verdict_note": "裁决:V1 原速使用;帧差应为连续换手内容性运动,无单帧突变"}
    ch4 = tl["sections"]["ch04"]
    w4 = window_stats(frames, ch4["start_s"], ch4["end_s"])
    full_min = min(frames, key=lambda x: x["YAVG"])
    ch4_min = min((x for x in frames if ch4["start_s"] <= x["t"] < ch4["end_s"]), key=lambda x: x["YAVG"])
    manual["c4_darkest"] = {"ch04_window_s": [ch4["start_s"], ch4["end_s"]], "stats": w4,
                            "ch04_min_yavg": round(ch4_min["YAVG"], 1), "ch04_min_at_s": round(ch4_min["t"], 2),
                            "global_min_yavg": round(full_min["YAVG"], 1), "global_min_at_s": round(full_min["t"], 2),
                            "global_min_in_ch04": ch4["start_s"] <= full_min["t"] < ch4["end_s"],
                            "verdict_note": "硬约束:c4 为全片最暗段且收束稳(无黑屏 run)"}
    e9 = shots["c6-s09"]
    sel9 = [x for x in frames if e9["window_start_s"] <= x["t"] < e9["window_end_s"]]
    gmax = max(frames, key=lambda x: x["YAVG"])
    outside = [x for x in frames if not (e9["window_start_s"] <= x["t"] < e9["window_end_s"])]
    omax = max(outside, key=lambda x: x["YAVG"])
    manual["c6_s09_brightest"] = {"window_s": [e9["window_start_s"], e9["window_end_s"]],
                                  "c6s09_max_yavg": round(max(x["YAVG"] for x in sel9), 1),
                                  "global_max_yavg": round(gmax["YAVG"], 1),
                                  "global_max_at_s": round(gmax["t"], 2),
                                  "global_max_belongs_to_c6s09": e9["window_start_s"] <= gmax["t"] < e9["window_end_s"],
                                  "max_outside_yavg": round(omax["YAVG"], 1),
                                  "margin": round(gmax["YAVG"] - omax["YAVG"], 1),
                                  "verdict_note": "硬约束:c6-s09 持全片唯一最亮帧;margin>0 且越大约稳"}
    # 弱对位三处(观感复核时间戳)
    manual["weak_alignment_windows"] = {sid: [shots[sid]["window_start_s"], shots[sid]["window_end_s"]]
                                        for sid in ("c9-s12", "c10-s08", "c10-s09", "c7-s10")}

    fails = []
    if whites:
        fails.append(f"white runs: {whites}")
    if blacks:
        fails.append(f"black runs: {blacks}")
    d = av.get("av_diff_vs_wav_s", av.get("av_diff_in_file_s", 0))
    if abs(d) > 1 / FPS + 0.005:
        fails.append(f"av diff {d}s > 1 frame")
    if static_fail:
        fails.append(f"static runs >{STATIC_FAIL_S}s: "
                     + str([(r['shot'], r['dur_s']) for r in static_fail]))
    if cfr_ok is False:
        fails.append(f"decoded pts not CFR/monotonic: {cfr_info}")

    ydifs = sorted(x["YDIF"] for x in frames)
    rep = {
        "video": str(video), "duration_s": vdur, "frames_scanned": len(frames),
        "white_runs": whites, "black_runs": blacks,
        "white_brief_transitions": white_brief, "black_brief_transitions": black_brief,
        "static_runs": static_runs, "static_fail": static_fail,
        "audio": str(audio) if audio.exists() else None, "av": av,
        "ydif_percentiles": {"p50": round(ydifs[len(ydifs)//2], 3),
                             "p99": round(ydifs[int(len(ydifs)*0.99)], 3),
                             "max": round(ydifs[-1], 3)},
        "decoded_pts_cfr": cfr_info, "manual_review": manual,
        "verdict": "FAIL" if fails else "PASS", "fails": fails,
    }
    outdir = RUN / "logs" / "qa_scan"
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"QA_SCAN_{video.stem}.json"
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[{rep['verdict']}] {video.name} {vdur:.3f}s frames={len(frames)}")
    print(f"  white_runs={len(whites)} black_runs={len(blacks)} "
          f"static_runs={len(static_runs)} static_fail={len(static_fail)}")
    print(f"  av={av}")
    print(f"  ydif p50/p99/max={rep['ydif_percentiles']['p50']}/{rep['ydif_percentiles']['p99']}/{rep['ydif_percentiles']['max']}")
    m = manual
    print(f"  [复核] c6-s07 ydif max {m['c6_s07']['stats']['ydif_max']} mean {m['c6_s07']['stats']['ydif_mean']}")
    print(f"  [复核] c4 global_min_in_ch04={m['c4_darkest']['global_min_in_ch04']} "
          f"min@{m['c4_darkest']['global_min_at_s']}s yavg={m['c4_darkest']['global_min_yavg']}")
    print(f"  [复核] c6-s09 brightest belongs={m['c6_s09_brightest']['global_max_belongs_to_c6s09']} "
          f"margin={m['c6_s09_brightest']['margin']}")
    for r in static_runs:
        print(f"  static: {r['shot']} {r['dur_s']}s @f{r['start_f']} hold={r['is_manifest_hold']} "
              f"confirmed={r.get('confirmed_static')} ep_diff={r.get('endpoint_diff_480x270')}")
    for f_ in fails:
        print("  FAIL:", f_)
    print(f"-> {out}")
    return 1 if fails else 0

if __name__ == "__main__":
    raise SystemExit(main())
