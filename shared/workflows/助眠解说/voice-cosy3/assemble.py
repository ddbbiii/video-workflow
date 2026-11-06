# -*- coding: utf-8 -*-
"""Assemble processed CosyVoice units into chapter audio + timeline (system Python).

Gap policy: per section, gaps are solved so that section duration = chars / target_cps
(clamped to min/max). No atempo anywhere. Output timeline matches the existing
`09_build_chapter_audio.py` schema so shots/subtitles keep reading one truth.
"""
from __future__ import annotations

import argparse
import json
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DEFAULT_PROFILE = HERE.parents[2] / "runtime" / "engines" / "tts" / "voice-assets" / "b2-warm-male-cosy3" / "profile.json"
BODY_SECTIONS = ["ch01", "ch02", "ch03", "ch04", "ch05", "ch06",
                 "ch07", "ch08", "ch09", "ch10", "ch11", "ch12", "epilogue"]


def read_pcm16(path: Path):
    with wave.open(str(path), "rb") as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    if sw != 2:
        raise SystemExit(f"[wav] expected PCM16: {path}")
    y = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        y = y.reshape(-1, ch).mean(axis=1)
    return y, sr


def write_pcm16(path: Path, y: np.ndarray, sr: int):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())


def silence(s: float, sr: int) -> np.ndarray:
    return np.zeros(int(round(s * sr)), dtype=np.float32)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--profile", default=str(DEFAULT_PROFILE))
    ap.add_argument("--tag", default="")
    ap.add_argument("--sections", default="", help="comma list; default = all sections except intro")
    args = ap.parse_args()

    prof = json.loads(Path(args.profile).read_text(encoding="utf-8"))
    sr = int(prof["sample_rate"])
    ep = Path(args.episode).resolve()
    tag = args.tag or prof["tag"]
    proc_dir = ep / "audio" / "vo-processed" / tag
    run_dir = ep / "runs" / args.run_id
    chap_dir = run_dir / "chapters"
    chap_dir.mkdir(parents=True, exist_ok=True)

    doc = json.loads((ep / "audio" / "utterances.json").read_text(encoding="utf-8"))
    by_id = {u["id"]: u for u in doc["utterances"]}
    sections = [s.strip() for s in args.sections.split(",") if s.strip()]
    if not sections:
        seen = []
        for u in doc["utterances"]:
            s = u["section"]
            if s != "intro" and s not in seen:
                seen.append(s)
        sections = seen
    else:
        sections = [s for s in sections if any(u["section"] == s for u in doc["utterances"])]
    if not sections:
        raise SystemExit("[sections] nothing to assemble")

    # paragraph order inside each section, preserving document order
    sec_paras: dict[str, list[str]] = {s: [] for s in sections}
    para_units: dict[str, list[str]] = {}
    for u in doc["utterances"]:
        p = u["paragraph_id"]
        if u["section"] not in sec_paras:
            continue
        if p not in para_units:
            para_units[p] = []
            sec_paras[u["section"]].append(p)
        if not u.get("tts_blocked"):
            para_units[p].append(u["id"])

    head_s = float(prof["chapter_head_s"])
    chap_gap_s = float(prof["chapter_gap_s"])
    min_gap, max_gap = float(prof["min_gap_s"]), float(prof["max_gap_s"])
    cps = float(prof["target_chars_per_second"])

    timeline = {"sample_rate": sr, "head_s": head_s, "unit_gap_s": None, "para_gap_s": None,
                "chap_gap_s": chap_gap_s, "sections": {}, "paragraphs": {}, "utterances": [],
                "audio_plan": {"voice_id": prof["voice_id"], "engine": prof["engine"], "speed": prof["speed"],
                               "target_cps": cps, "trim_rms_db": prof["trim_rms_db"], "no_atempo": True,
                               "profile": str(Path(args.profile).resolve())}}
    body = []
    body_abs = 0.0
    gaps_all = []
    report = []
    first_sec = True
    for sec in sections:
        if not first_sec:
            g = silence(chap_gap_s, sr)
            body.append(g); body_abs += len(g) / sr
        first_sec = False
        sec_start = body_abs
        sec_pcm = [silence(head_s, sr)]
        body_abs += head_s
        units = [uid for p in sec_paras[sec] for uid in para_units[p]]
        if not units:
            continue
        chars = sum(len(by_id[uid]["text"]) for uid in units)
        wavs = []
        for uid in units:
            p = proc_dir / f"{uid}.wav"
            if not p.exists():
                raise SystemExit(f"[missing] {p}")
            y, sr2 = read_pcm16(p)
            if sr2 != sr:
                raise SystemExit(f"[sr] {p} is {sr2}, expected {sr}")
            wavs.append(y)
        speech_s = sum(len(y) / sr for y in wavs)
        target_s = chars / cps
        gaps_total = target_s - head_s - speech_s
        gap = gaps_total / max(1, len(units) - 1) if len(units) > 1 else 0.0
        gap_unclamped = gap
        gap = float(min(max_gap, max(min_gap, gap)))

        chap_units = []
        for i, (uid, y) in enumerate(zip(units, wavs)):
            if i > 0:
                sec_pcm.append(silence(gap, sr)); body_abs += gap
            u_start = body_abs
            sec_pcm.append(y); body_abs += len(y) / sr
            timeline["utterances"].append({"id": uid, "paragraph_id": by_id[uid]["paragraph_id"],
                                           "section": sec, "start_s": round(u_start, 3),
                                           "end_s": round(body_abs, 3),
                                           "start_sample": int(round(u_start * sr)),
                                           "end_sample": int(round(body_abs * sr)),
                                           "seconds": round(len(y) / sr, 3)})
            chap_units.append(uid)
        # paragraph spans
        for p in sec_paras[sec]:
            ids = para_units[p]
            if ids:
                us = [x for x in timeline["utterances"] if x["id"] in ids]
                if us:
                    timeline["paragraphs"][p] = {"section": sec, "start_s": us[0]["start_s"],
                                                 "end_s": us[-1]["end_s"]}
        chap = np.concatenate(sec_pcm)
        write_pcm16(chap_dir / f"{sec}.wav", chap, sr)
        timeline["sections"][sec] = {"start_s": round(sec_start, 3), "end_s": round(body_abs, 3),
                                     "seconds": round(body_abs - sec_start, 3),
                                     "units": chap_units, "wav": str(chap_dir / f"{sec}.wav"),
                                     "chars": chars, "speech_s": round(speech_s, 2),
                                     "gap_s": round(gap, 3), "gap_unclamped_s": round(gap_unclamped, 3),
                                     "clamped": abs(gap - gap_unclamped) > 1e-6}
        body.append(chap)
        gaps_all.append(gap)
        sec_s = body_abs - sec_start
        report.append((sec, chars, round(speech_s, 2), round(sec_s, 2), round(gap, 3),
                       round(chars / sec_s, 2), abs(gap - gap_unclamped) > 1e-6))
        print(f"[assemble] {sec}: chars={chars} speech={speech_s:.1f}s sec={sec_s:.1f}s gap={gap:.2f}s", flush=True)

    full = np.concatenate(body) if body else silence(1.0, sr)
    body_path = chap_dir / "body_narration.wav"
    write_pcm16(body_path, full, sr)
    timeline["body_seconds"] = round(len(full) / sr, 3)
    timeline["body_samples"] = len(full)
    timeline["body_wav"] = str(body_path)
    timeline["unit_gap_s"] = round(float(np.mean(gaps_all)), 4) if gaps_all else 0.0
    timeline["para_gap_s"] = timeline["unit_gap_s"]
    (run_dir / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=1), encoding="utf-8")

    total_chars = sum(r[1] for r in report)
    lines = ["# 配音装配报告", "",
             f"- voice: `{prof['voice_id']}` / {prof['engine']} / speed={prof['speed']}",
             f"- 目标节奏: {cps} 字/秒；实测: {total_chars / (len(full)/sr):.2f} 字/秒",
             f"- 正文时长: {len(full)/sr:.2f}s = {len(full)/sr/60:.2f} min",
             f"- 裁剪: {prof['trim_rms_db']} dB / {prof['trim_frame_ms']} ms 帧，前留 {prof['trim_keep_head_s']}s、后留 {prof['trim_keep_tail_s']}s，淡入淡出 {prof['fade_s']}s",
             f"- 无 atempo；模型原生 {prof['speed']} + 句间留白", "",
             "| 章 | 字数 | 语音 | 章时长 | 句间 | 实测字/秒 | 夹限 |", "|---|---|---|---|---|---|---|"]
    for r in report:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {'是' if r[6] else ''} |")
    (run_dir / "REPORT_audio.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[done] body={len(full)/sr:.2f}s cps={total_chars/(len(full)/sr):.2f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
