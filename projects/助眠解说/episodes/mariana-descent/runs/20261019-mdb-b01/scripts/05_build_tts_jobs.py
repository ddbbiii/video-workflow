# -*- coding: utf-8 -*-
"""Build TTS chapter jobs (validate/intro/bridge/ch01..ch10/epilogue) from utterances.json.

移植自 newton 05_build_tts_jobs.py。声线/引擎参数待 AUDIO_PLAN(见 AUDIO_PLAN.py),
未定稿时拒绝运行。validate 抽检单元自动选取(intro 首末/bridge 首/ch04 中段/epilogue 末)。
"""
from __future__ import annotations
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import AUDIO_PLAN as AP

EP = HERE.parents[2]
UTT = EP / "audio" / "utterances.json"
JOBS = EP / "audio" / "jobs"
RAW = EP / "audio" / "vo-raw" / (AP.VOICE_TAG or "TODO_AUDIO_PLAN")


def job_for(section: str, utts):
    profile = json.loads(Path(AP.VOICE_PROFILE_JSON).read_text(encoding="utf-8"))
    return {
        "out_dir": str(RAW),
        "model_dir": AP.TTS_MODEL_DIR,
        "seed": profile["seed"],
        "cfg_value": profile["cfg_value"],
        "inference_timesteps": profile["inference_timesteps"],
        "desc": "",
        "desc_in_text": False,
        "reference_wav": profile["reference_wav"],
        "prompt_wav": profile["prompt_wav"],
        "prompt_text": profile["prompt_text"],
        "shots": [{"id": u["id"], "text": u["text"]} for u in utts if not u["tts_blocked"]],
    }


def pick_validate_ids(doc):
    """自动抽检:intro 首末(占位段除外)、bridge 首、正文中段、epilogue 末。"""
    utts = [u for u in doc["utterances"] if not u["tts_blocked"]]
    by_sec = {}
    for u in utts:
        by_sec.setdefault(u["section"], []).append(u["id"])
    body_secs = [s for s in ("bridge", "ch01", "ch02", "ch03", "ch04", "ch05",
                             "ch06", "ch07", "ch08", "ch09", "ch10", "epilogue") if s in by_sec]
    mid = body_secs[len(body_secs) // 2] if body_secs else None
    ids = []
    if "intro" in by_sec:
        ids += [by_sec["intro"][0], by_sec["intro"][-1]]
    if "bridge" in by_sec:
        ids.append(by_sec["bridge"][0])
    if mid:
        ids.append(by_sec[mid][len(by_sec[mid]) // 2])
    if "epilogue" in by_sec:
        ids.append(by_sec["epilogue"][-1])
    return ids


def main():
    AP.require_audio_plan("VOICE_PROFILE_JSON", "VOICE_TAG", "TTS_MODEL_DIR")
    JOBS.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    doc = json.loads(UTT.read_text(encoding="utf-8"))
    by_sec = {}
    for u in doc["utterances"]:
        by_sec.setdefault(u["section"], []).append(u)
    # intro job excludes the blocked minute-placeholder paragraph (tts_blocked)
    for sec, utts in by_sec.items():
        (JOBS / f"{sec}.json").write_text(json.dumps(job_for(sec, utts), ensure_ascii=False, indent=1), encoding="utf-8")
        n = sum(1 for u in utts if not u["tts_blocked"])
        print(f"{sec}: {n} shots -> jobs/{sec}.json")
    val_ids = pick_validate_ids(doc)
    val_utts = [u for u in doc["utterances"] if u["id"] in val_ids]
    (JOBS / "validate.json").write_text(json.dumps(job_for("validate", val_utts), ensure_ascii=False, indent=1), encoding="utf-8")
    print("validate:", sorted(val_ids), "-> jobs/validate.json")


if __name__ == "__main__":
    main()
