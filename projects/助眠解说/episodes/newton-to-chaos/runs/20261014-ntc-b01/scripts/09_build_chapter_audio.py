# -*- coding: utf-8 -*-
"""牛顿到混沌 章节音频拼装 + 时间轴（AUDIO_PLAN.md 第3节留白规范）。
正文 = lead + ch01..ch08。intro 单独走片头流程。
留白：整章头部0.3774s；同段内单元间0.19s；段间0.4245s；章间0.7547s；整集尾部0.7547s（尾部在整片拼装时加）。"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import soundfile as sf

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\newton-to-chaos")
PROC = EP / "audio" / "vo-processed" / "lightexpr-final"
RUN = EP / "runs" / "20261014-ntc-b01"
CHAP = RUN / "chapters"
TIMELINE = RUN / "timeline.json"
SR = 48000
HEAD = 0.3774
UNIT_GAP = 0.19
PARA_GAP = 0.4245
CHAP_GAP = 0.7547

BODY_SECTIONS = ["lead", "ch01", "ch02", "ch03", "ch04", "ch05", "ch06", "ch07", "ch08"]

def silence(s):
    return np.zeros(int(SR * s), dtype=np.int16)

def load_wav16(path):
    y, sr = sf.read(str(path), always_2d=False)
    if y.dtype != np.int16:
        y = (np.clip(y, -1, 1) * 32767).astype(np.int16)
    if y.ndim > 1:
        y = y.mean(axis=1).astype(np.int16)
    if sr != SR:
        import subprocess
        tmp = path.with_suffix(".tmp48k.wav")
        subprocess.run([r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe",
                        "-y","-i",str(path),"-ar",str(SR),"-ac","1","-acodec","pcm_s16le",str(tmp)],
                       capture_output=True)
        y, sr2 = sf.read(str(tmp), always_2d=False)
        tmp.unlink(missing_ok=True)
        y = (np.clip(y, -1, 1) * 32767).astype(np.int16)
    return y

def main():
    CHAP.mkdir(parents=True, exist_ok=True)
    utt = json.loads((EP / "audio" / "utterances.json").read_text(encoding="utf-8"))
    by_id = {u["id"]: u for u in utt["utterances"]}
    para_order = utt["paragraph_order"]
    para_section = {p["id"]: p["section"] for p in [{"id": pid, "section": by_id[list(by_id)[i]]["section"]} for i, pid in enumerate(para_order)]} if False else None
    # build paragraph -> section from utterances
    psec = {}
    for uid, u in by_id.items():
        psec[u["paragraph_id"]] = u["section"]
    # group utterances by paragraph preserving order
    para_utts = {p: [] for p in para_order}
    for u in utt["utterances"]:
        if u["paragraph_id"] in para_utts:
            para_utts[u["paragraph_id"]].append(u)
    # group paragraphs by section
    sec_paras = {s: [] for s in BODY_SECTIONS}
    for p in para_order:
        s = psec.get(p)
        if s in sec_paras:
            sec_paras[s].append(p)

    timeline = {"sample_rate": SR, "head_s": HEAD, "unit_gap_s": UNIT_GAP,
                "para_gap_s": PARA_GAP, "chap_gap_s": CHAP_GAP,
                "sections": {}, "paragraphs": {}, "utterances": []}
    body_abs = 0.0  # absolute body offset (seconds from body start)
    body_pcm = []

    for si, sec in enumerate(BODY_SECTIONS):
        sec_pcm = []
        sec_start = body_abs
        # chapter head
        sec_pcm.append(silence(HEAD)); body_abs += HEAD
        chap_units = []
        for pi, pid in enumerate(sec_paras[sec]):
            us = para_utts[pid]
            # paragraph start
            para_start = body_abs
            for ui, u in enumerate(us):
                if u.get("tts_blocked"):
                    continue
                src = PROC / f"{u['id']}.wav"
                if not src.exists():
                    print(f"MISSING {src}"); continue
                y = load_wav16(src)
                if ui > 0:
                    sec_pcm.append(silence(UNIT_GAP)); body_abs += UNIT_GAP
                u_start = body_abs
                sec_pcm.append(y); body_abs += len(y) / SR
                timeline["utterances"].append({"id": u["id"], "paragraph_id": pid,
                    "section": sec, "start_s": round(u_start, 3),
                    "end_s": round(body_abs, 3),
                    "start_sample": int(u_start * SR), "end_sample": int(body_abs * SR),
                    "seconds": round(len(y) / SR, 3)})
                chap_units.append(u["id"])
            timeline["paragraphs"][pid] = {"section": sec,
                "start_s": round(para_start, 3), "end_s": round(body_abs, 3)}
            # paragraph gap (except last paragraph in chapter)
            if pi < len(sec_paras[sec]) - 1:
                sec_pcm.append(silence(PARA_GAP)); body_abs += PARA_GAP
        chap_pcm = np.concatenate(sec_pcm)
        sf.write(str(CHAP / f"{sec}.wav"), chap_pcm, SR, subtype="PCM_16")
        timeline["sections"][sec] = {"start_s": round(sec_start, 3),
            "end_s": round(body_abs, 3), "seconds": round(body_abs - sec_start, 3),
            "units": chap_units, "wav": str(CHAP / f"{sec}.wav")}
        print(f"{sec}: {body_abs - sec_start:.1f}s ({len(chap_units)} units)")
        # chapter gap (except last)
        if si < len(BODY_SECTIONS) - 1:
            body_pcm.append(silence(CHAP_GAP)); body_abs += CHAP_GAP
        body_pcm.append(chap_pcm)
    # episode tail
    body_pcm.append(silence(CHAP_GAP)); body_abs += CHAP_GAP
    full = np.concatenate(body_pcm) if body_pcm else silence(1)
    sf.write(str(CHAP / "body_narration.wav"), full, SR, subtype="PCM_16")
    timeline["body_seconds"] = round(body_abs, 3)
    timeline["body_samples"] = len(full)
    timeline["body_wav"] = str(CHAP / "body_narration.wav")
    TIMELINE.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"BODY total {body_abs:.1f}s = {body_abs/60:.2f} min")

if __name__ == "__main__":
    main()
