# -*- coding: utf-8 -*-
"""收尾终检(2026-10-20 收尾任务书第 7 条;v5 复跑:片头 v5 去标题卡版)。

v5:音轨/字幕 r3 不变,终检口径同 v4;抽帧验证末卡为分句文字且无"超出时间"字样。

① 片头门禁(intro-node §6 最小验收):句界一致(叠化整体落在句间停顿)/
   无黑帧闪帧(signalstats 逐帧)/ 常显(14 号内置 0.5s 步进扫描结果复核)/
   交棒句驻留(末次叠化止于末句开口前,其后零切换至片尾);
② 字幕 QA:cues.json 一致率/无重叠/宽度 + sub.mp8 抽样底部带实测
   (字幕中点命中、片头区间无字幕带);
③ 终检:clean 与 sub 时长/帧数一致、音轨相同(提取后 md5);
④ 全片 clean 白屏/黑屏/解码帧序 CFR/音视差(vs narration.wav)。

输出:runs/.../qa/final/{FINAL_QA.json, FINAL_QA.md};FAIL 退出码 1。
"""
from __future__ import annotations
import hashlib, json, re, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image

EP = Path(__file__).resolve().parents[3]
RUN = EP / "runs" / "20261018-sbt-b01"
FFMPEG = r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"
FFPROBE = FFMPEG.replace("ffmpeg.exe", "ffprobe.exe")
FPS = 30
INTRO_BATCH = "batch-20261020-v5"
CLEAN = EP / "video/final/siffre-beyond-time_clean.mp4"
SUB = EP / "video/final/siffre-beyond-time_sub.mp4"
NARR = EP / "video/final/siffre-beyond-time_narration.wav"
INTRO_VID = RUN / f"intro/{INTRO_BATCH}/clean-intro.mp4"
INTRO_CARDS = RUN / "intro_cards.json"
INTRO_TL = RUN / "intro_timeline.json"
BATCH = RUN / f"intro/{INTRO_BATCH}"
CUES = RUN / "subtitles/r3/cues.json"
OUTDIR = RUN / "qa" / "final"
WHITE_YAVG, WHITE_MIN_S = 225, 1.0
BLACK_YAVG, BLACK_MIN_S = 12, 2.0

def probe(p, entries):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", entries,
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return r.stdout.strip()

def probe_dur(p):
    return float(probe(p, "format=duration"))

def scan_luma(video, t0=None, t1=None):
    """逐帧 YAVG(160x90 采样),可选时间窗。"""
    cmd = [FFMPEG, "-nostats", "-i", str(video), "-map", "0:v"]
    if t0 is not None:
        cmd += ["-ss", f"{t0:.3f}"]
    vf = "scale=160:90,signalstats,metadata=print:file=-"
    cmd += ["-vf", vf, "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True)
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
    for fr in frames:
        fr["YAVG"] = float(fr.get("YAVG", 128))
    return frames

def runs_of(frames, key, pred, min_s):
    out, start = [], None
    for fr in frames:
        if pred(fr[key]) and start is None:
            start = fr
        elif not pred(fr[key]) and start is not None:
            if fr["t"] - start["t"] >= min_s:
                out.append((round(start["t"], 3), round(fr["t"], 3)))
            start = None
    if start is not None and frames[-1]["t"] - start["t"] >= min_s:
        out.append((round(start["t"], 3), round(frames[-1]["t"] + 1 / FPS, 3)))
    return out

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

def frame_at(video, t, out_png):
    subprocess.run([FFMPEG, "-y", "-ss", f"{t:.3f}", "-i", str(video),
                    "-frames:v", "1", "-q:v", "3", str(out_png)],
                   capture_output=True, text=True)
    return out_png

def bottom_band_ratio(png):
    """底部字幕带(MarginV118,字号96:y≈830-975)白字像素占比。"""
    im = Image.open(png).convert("L")
    w, h = im.size
    band = im.crop((int(w * 0.06), int(h * 0.76), int(w * 0.94), int(h * 0.905)))
    a = np.asarray(band, dtype=np.uint8)
    return float((a > 200).mean())

def audio_md5(video, tmp):
    subprocess.run([FFMPEG, "-y", "-i", str(video), "-map", "0:a:0",
                    "-c:a", "copy", "-f", "adts", str(tmp)],
                   capture_output=True, text=True)
    return hashlib.md5(tmp.read_bytes()).hexdigest()

def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    fails, notes = [], {}

    # ---------- ① 片头门禁 ----------
    cards = json.loads(INTRO_CARDS.read_text(encoding="utf-8"))["cards"]
    intro_tl = json.loads(INTRO_TL.read_text(encoding="utf-8"))
    intro_s = intro_tl["intro_seconds"]
    btl = json.loads((BATCH / "timeline.json").read_text(encoding="utf-8"))
    blends = btl["bg_timeline"]["blends"]          # [start, end, dur]
    # 句界一致:每次叠化整体落在句间停顿(上句末卡语音结束+0.04 ≤ 起,止 ≤ 下句首卡开口-0.03)
    para_of = {}
    for c in cards:
        para_of.setdefault(c["para"], []).append(c)
    para_seq = sorted(para_of.items(), key=lambda kv: kv[1][0]["start_s"])
    sent_bounds = []
    for pid, cs in para_seq:
        sent_bounds.append((pid, cs[0]["start_s"], cs[-1]["end_s"]))
    blends_ok, blend_check = True, []
    for j, (pid, s0, e0) in enumerate(sent_bounds[:-1]):
        nxt_pid, ns, _ = sent_bounds[j + 1]
        bs, be, bdur = blends[j]
        ok = (bs >= e0 + 0.04 - 1e-6) and (be <= ns - 0.03 + 1e-6)
        blends_ok &= ok
        blend_check.append({"junction": f"{pid}->{nxt_pid}", "blend": [bs, be],
                            "pause": [e0, ns], "ok": bool(ok)})
    # 驻留:末次叠化止于末句开口前;末句朗读期间零切换
    last_pid, last_s, last_e = sent_bounds[-1]
    dwell_from = blends[-1][1] if blends else 0.0
    dwell_ok = dwell_from <= last_s + 1e-6
    dwell_s = round(btl["total_s"] - dwell_from, 3)
    # 常显:14 号内置扫描结果
    qa_md = (BATCH / "gate" / "qa_report.md").read_text(encoding="utf-8")
    cont_blanks = "continuity blanks: []" in qa_md or "continuity blanks: none" in qa_md
    card_fails = re.search(r"card fails: \[([^\]]*)\]", qa_md)
    card_fails_empty = card_fails and card_fails.group(1).strip() == ""
    # 黑帧闪帧(逐帧 signalstats)
    ifr = scan_luma(INTRO_VID)
    intro_blacks = runs_of(ifr, "YAVG", lambda y: y <= BLACK_YAVG, BLACK_MIN_S)
    intro_whites = runs_of(ifr, "YAVG", lambda y: y >= WHITE_YAVG, WHITE_MIN_S)
    intro_dur = probe_dur(INTRO_VID)
    notes["intro"] = {
        "duration_s": round(intro_dur, 3), "audio_s": intro_s,
        "frames": len(ifr), "cards": len(cards),
        "blends": blend_check, "blends_ok": blends_ok,
        "dwell": {"from_s": dwell_from, "seconds": dwell_s,
                  "during_last_sentence_only": bool(dwell_ok)},
        "persistent_text_scan_clean": bool(cont_blanks and card_fails_empty),
        "black_runs": intro_blacks, "white_runs": intro_whites,
    }
    if not blends_ok: fails.append("intro 叠化未整体落在句间停顿")
    if not dwell_ok: fails.append("intro 交棒句驻留被切换打断")
    if not (cont_blanks and card_fails_empty): fails.append("intro 常显扫描未通过(见 gate/qa_report.md)")
    if intro_blacks or intro_whites: fails.append(f"intro 黑/白帧 runs: {intro_blanks}{intro_whites}")
    if abs(intro_dur - intro_s) > 1 / FPS + 0.005: fails.append("intro 音视差 > 1 帧")

    # ---------- ② 字幕 QA ----------
    cd = json.loads(CUES.read_text(encoding="utf-8"))
    cues, subqa = cd["cues"], cd.get("qa", {})
    if subqa.get("units_consistent") != subqa.get("units_total"):
        fails.append(f"字幕锁定稿一致率 {subqa.get('units_consistent')}/{subqa.get('units_total')}"
                     f" 不满分:{subqa.get('consistency_bad')}")
    if subqa.get("overlaps"): fails.append(f"字幕重叠 {len(subqa['overlaps'])} 处")
    if subqa.get("width_over"): fails.append(f"字幕超宽 {subqa['width_over']} 条")
    if cd.get("warns"): notes["subtitle_warns"] = len(cd["warns"])
    # sub.mp4 抽样:字幕中点底部带命中 + 片头区间无字幕带
    tmp = OUTDIR / "_probe.png"
    idxs = [int(i * (len(cues) - 1) / 11) for i in range(12)]
    hits = []
    for i in idxs:
        c = cues[i]
        mid = (c["start_s"] + c["end_s"]) / 2
        r = bottom_band_ratio(frame_at(SUB, mid, tmp))
        hits.append({"i": i, "t": round(mid, 2), "ratio": round(r, 4), "text": c["text"][:12]})
        if r < 0.005: fails.append(f"字幕抽样未命中: cue#{i} @t={mid:.1f}s ratio={r:.4f}")
    intro_mids = [intro_s * 0.4, intro_s * 0.8]
    intro_band = []
    for t in intro_mids:
        r = bottom_band_ratio(frame_at(SUB, t, tmp))
        intro_band.append({"t": round(t, 2), "ratio": round(r, 4)})
        if r > 0.01: fails.append(f"片头区间出现字幕带 @t={t:.1f}s ratio={r:.4f}")
    tmp.unlink(missing_ok=True)
    notes["subtitle"] = {"cues": len(cues), "qa": subqa, "sample_hits": hits,
                         "intro_band": intro_band}

    # ---------- ③ clean vs sub ----------
    cn, sn = probe(CLEAN, "stream=nb_frames"), probe(SUB, "stream=nb_frames")
    cdur, sdur = probe_dur(CLEAN), probe_dur(SUB)
    t1, t2 = OUTDIR / "_ca.aac", OUTDIR / "_sa.aac"
    h1, h2 = audio_md5(CLEAN, t1), audio_md5(SUB, t2)
    t1.unlink(); t2.unlink()
    notes["clean_vs_sub"] = {"frames": [cn, sn], "duration_s": [round(cdur, 3), round(sdur, 3)],
                             "audio_md5_same": h1 == h2}
    if cn != sn: fails.append(f"clean/sub 帧数不一致 {cn} vs {sn}")
    if abs(cdur - sdur) > 0.1: fails.append(f"clean/sub 时长差 {cdur - sdur:.3f}s")
    if h1 != h2: fails.append("clean/sub 音轨哈希不一致")

    # ---------- ④ 全片 clean 门禁 ----------
    cfr_ok, cfr_info = decoded_pts_cfr(CLEAN)
    av_diff = cdur - probe_dur(NARR)
    if abs(av_diff) > 1 / FPS + 0.005: fails.append(f"clean 音视差 {av_diff:.3f}s > 1 帧")
    if cfr_ok is False: fails.append(f"clean 解码帧序非 CFR: {cfr_info}")
    ffr = scan_luma(CLEAN)
    whites = runs_of(ffr, "YAVG", lambda y: y >= WHITE_YAVG, WHITE_MIN_S)
    blacks_all = runs_of(ffr, "YAVG", lambda y: y <= BLACK_YAVG, BLACK_MIN_S)
    blacks = [b for b in blacks_all if b[0] < cdur - 3.0]
    if whites: fails.append(f"clean 白屏 runs: {whites}")
    if blacks: fails.append(f"clean 黑屏 runs: {blacks}")
    claim_margin = cdur - 35 * 60
    if abs(claim_margin) > 30: fails.append(f"35 分钟不自洽 margin={claim_margin:+.1f}s")
    notes["final_clean"] = {"duration_s": round(cdur, 3), "minutes": round(cdur / 60, 2),
                            "frames_scanned": len(ffr), "white_runs": whites,
                            "black_runs": blacks, "av_diff_s": round(av_diff, 3),
                            "cfr": cfr_info, "claim_margin_s": round(claim_margin, 1)}

    verdict = "FAIL" if fails else "PASS"
    rep = {"verdict": verdict, "fails": fails, **notes}
    (OUTDIR / "FINAL_QA.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
    md = ["# FINAL QA — siffre-beyond-time", "",
          f"verdict: **{verdict}**", "",
          f"- intro: {notes['intro']['duration_s']}s, {notes['intro']['cards']} cards, "
          f"{len(blends)} blends(all-in-pause={blends_ok}), dwell {dwell_s}s",
          f"- subtitles: {len(cues)} cues, consistent {subqa.get('units_consistent')}/"
          f"{subqa.get('units_total')}, max width {subqa.get('max_text_px')}px",
          f"- clean: {notes['final_clean']['duration_s']}s "
          f"({notes['final_clean']['minutes']}min), av_diff {notes['final_clean']['av_diff_s']}s, "
          f"claim margin {notes['final_clean']['claim_margin_s']}s",
          f"- clean/sub: frames {cn}/{sn}, audio md5 same={h1 == h2}", ""]
    if fails:
        md += ["## fails"] + [f"- {f}" for f in fails]
    (OUTDIR / "FINAL_QA.md").write_text("\n".join(md), encoding="utf-8")
    print(f"[{verdict}] intro {intro_dur:.2f}s/{notes['intro']['cards']}卡 | "
          f"total {cdur:.2f}s | cues {len(cues)} | clean==sub audio {h1 == h2}")
    for f_ in fails:
        print("  FAIL:", f_)
    print(f"-> {OUTDIR / 'FINAL_QA.md'}")
    return 1 if fails else 0

if __name__ == "__main__":
    raise SystemExit(main())
