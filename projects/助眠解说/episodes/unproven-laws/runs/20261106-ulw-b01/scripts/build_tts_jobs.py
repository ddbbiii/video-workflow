# -*- coding: utf-8 -*-
"""Parse NARRATION_MASTER.md into TTS job(s) for unproven-laws.
Section keys: intro, bridge, ch01..ch07, epilogue. Utterance ids: <sec>-pNN-uNN.
"""
import json, re
from pathlib import Path

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws")
SRC = EP / "story" / "NARRATION_MASTER.md"
OUT = EP / "audio" / "jobs"
RAW = EP / "audio" / "vo-raw" / "lightexpr-seed7"

SECTIONS = {
    "片头": "intro", "故事由来": "bridge",
    "第一章": "ch01", "第二章": "ch02", "第三章": "ch03", "第四章": "ch04",
    "第五章": "ch05", "第六章": "ch06", "第七章": "ch07",
    "尾声": "epilogue",
}

REF = r"E:/program/1project/video/shared/runtime/engines/tts/refs/b2-warm-male_ref.wav"
PROMPT_WAV = r"E:/program/1project/video/shared/runtime/engines/tts/voice-assets/b2-warm-male/refs/light-expression-20261013/prompt.wav"
PROMPT_TEXT = "你脚下的地球，藏着一个看不见的磁场。"
MODEL = r"E:\program\1project\video\shared\runtime\engines\tts\voxcpm\pretrained_models\VoxCPM2"


def parse():
    text = SRC.read_text(encoding="utf-8")
    blocks = re.split(r"^## ", text, flags=re.M)[1:]
    secs = []
    for b in blocks:
        title, _, body = b.partition("\n")
        title = title.strip()
        key = next((k for m, k in SECTIONS.items() if title.startswith(m)), None)
        if not key:
            raise SystemExit("unknown section: " + title)
        paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        secs.append((key, title, paras))
    return secs


def chunks(para, limit=80):
    sents = [s for s in re.split(r"(?<=[。？！])", para) if s.strip()]
    out, cur = [], ""
    for s in sents:
        if cur and len(cur) + len(s) > limit:
            out.append(cur); cur = s
        else:
            cur += s
    if cur:
        out.append(cur)
    return out


def main():
    secs = parse()
    OUT.mkdir(parents=True, exist_ok=True)
    all_shots, counts = [], {}
    for key, title, paras in secs:
        shots = []
        for pi, para in enumerate(paras, 1):
            if key == "intro":
                # 片头按句单独成镜，便于字幕卡对齐
                parts = [s for s in re.split(r"(?<=[。？！])", para) if s.strip()]
            else:
                parts = chunks(para)
            for ui, ch in enumerate(parts, 1):
                uid = "%s-p%02d-u%02d" % (key, pi, ui)
                shots.append({"id": uid, "text": ch})
                counts[key] = counts.get(key, 0) + len(ch)
        all_shots.extend(shots)
        job = {
            "out_dir": str(RAW), "model_dir": MODEL,
            "seed": 7, "cfg_value": 2.0, "inference_timesteps": 10,
            "desc": "", "desc_in_text": False,
            "reference_wav": REF, "prompt_wav": PROMPT_WAV, "prompt_text": PROMPT_TEXT,
            "shots": shots,
        }
        (OUT / (key + ".json")).write_text(json.dumps(job, ensure_ascii=False, indent=1), encoding="utf-8")
    job_all = {
        "out_dir": str(RAW), "model_dir": MODEL,
        "seed": 7, "cfg_value": 2.0, "inference_timesteps": 10,
        "desc": "", "desc_in_text": False,
        "reference_wav": REF, "prompt_wav": PROMPT_WAV, "prompt_text": PROMPT_TEXT,
        "shots": all_shots,
    }
    (OUT / "all.json").write_text(json.dumps(job_all, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(counts.values())
    print("sections", len(secs), "shots", len(all_shots), "chars", total,
          "est_min", round(total / 3.3 / 60, 1))
    for k, v in counts.items():
        print(" ", k, v)


if __name__ == "__main__":
    main()
