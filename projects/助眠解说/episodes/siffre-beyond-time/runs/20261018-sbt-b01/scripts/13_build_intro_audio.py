# -*- coding: utf-8 -*-
"""构建片头音轨:HEAD 0.3774 + intro p01..pNN(段间0.4245)。
输出 chapters/intro.wav + intro_timeline.json。

siffre 片头为慢钩型(≤45s),intro 段落数以 utterances.json 为准(NARRATION_MASTER
v1 片头含 6 段,末段含【正文实测分钟数】占位,回填并重配该段后才齐)。占位段
(tts_blocked)自动跳过。移植自 newton 13_build_intro_audio.py。
"""
import json, sys
import numpy as np
import soundfile as sf
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import AUDIO_PLAN as AP

EP = HERE.parents[2]
PROC = EP / "audio" / "vo-processed" / (AP.VOICE_TAG or "TODO_AUDIO_PLAN")
RUN = EP / "runs" / "20261018-sbt-b01"
SR = AP.SR; HEAD = AP.HEAD_S; PARA_GAP = AP.PARA_GAP_S

def sil(s): return np.zeros(int(SR*s), dtype=np.int16)

def load(p):
    y, sr = sf.read(str(p), always_2d=False)
    if y.dtype != np.int16: y = (np.clip(y, -1, 1) * 32767).astype(np.int16)
    if y.ndim > 1: y = y.mean(axis=1).astype(np.int16)
    return y

def main():
    AP.require_audio_plan("VOICE_TAG")
    utt = json.loads((EP / "audio" / "utterances.json").read_text(encoding="utf-8"))
    # intro 全部段落,按文档顺序;跳过 tts_blocked(分钟数占位段)
    units = [u["id"] for u in utt["utterances"]
             if u["section"] == "intro" and not u.get("tts_blocked")]
    if not units:
        raise SystemExit("intro 无可配语音单元:先完成片头占位段回填与TTS。")
    pcm = [sil(HEAD)]; t = HEAD; tl = []
    for i, u in enumerate(units):
        wav = PROC / f"{u}.wav"
        if not wav.exists():
            raise SystemExit(f"缺少片头语音 {wav}(占位段回填后需重配该段)")
        if i > 0:
            pcm.append(sil(PARA_GAP)); t += PARA_GAP
        y = load(wav); s = t
        pcm.append(y); t += len(y) / SR
        tl.append({"id": u, "start_s": round(s,3), "end_s": round(t,3), "seconds": round(len(y)/SR,3)})
    full = np.concatenate(pcm)
    (RUN / "chapters").mkdir(parents=True, exist_ok=True)
    sf.write(str(RUN / "chapters" / "intro.wav"), full, SR, subtype="PCM_16")
    intro_s = round(t, 3)
    json.dump({"intro_seconds": intro_s, "intro_samples": len(full), "sample_rate": SR,
               "units": tl, "head_s": HEAD, "para_gap_s": PARA_GAP},
              open(RUN / "intro_timeline.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"intro {intro_s}s = {intro_s/60:.2f}min ({len(units)} units)")

if __name__ == "__main__":
    main()
