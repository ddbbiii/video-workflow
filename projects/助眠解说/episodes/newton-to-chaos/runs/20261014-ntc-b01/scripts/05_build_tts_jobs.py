# -*- coding: utf-8 -*-
"""Build TTS chapter jobs (validate/lead/ch01..ch08 + intro body-part) from utterances.json."""
from __future__ import annotations
import json
from pathlib import Path

EP = Path(__file__).resolve().parents[3]
UTT = EP / "audio" / "utterances.json"
JOBS = EP / "audio" / "jobs"
RAW = EP / "audio" / "vo-raw" / "lightexpr-seed7"
PROFILE = json.loads(Path(r"E:\program\1project\video\shared\runtime\engines\tts\voice-assets\b2-warm-male\light-expression-profile.json").read_text(encoding="utf-8"))

VALIDATE_IDS = ["intro-p01-u01", "intro-p02-u01", "ch01-p09-u01", "ch04-p19-u01", "ch08-p30-u01"]

def job_for(section: str, utts):
    return {
        "out_dir": str(RAW),
        "model_dir": r"E:\program\1project\video\shared\runtime\engines\tts\voxcpm\pretrained_models\VoxCPM2",
        "seed": PROFILE["seed"],
        "cfg_value": PROFILE["cfg_value"],
        "inference_timesteps": PROFILE["inference_timesteps"],
        "desc": "",
        "desc_in_text": False,
        "reference_wav": PROFILE["reference_wav"],
        "prompt_wav": PROFILE["prompt_wav"],
        "prompt_text": PROFILE["prompt_text"],
        "shots": [{"id": u["id"], "text": u["text"]} for u in utts if not u["tts_blocked"]],
    }

def main():
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
    val_utts = [u for u in doc["utterances"] if u["id"] in VALIDATE_IDS]
    (JOBS / "validate.json").write_text(json.dumps(job_for("validate", val_utts), ensure_ascii=False, indent=1), encoding="utf-8")
    print("validate:", len(val_utts), "shots -> jobs/validate.json")

if __name__ == "__main__":
    main()
