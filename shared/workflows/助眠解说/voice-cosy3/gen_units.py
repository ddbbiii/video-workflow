# -*- coding: utf-8 -*-
"""CosyVoice3 per-utterance narration generator (sleep line default since 2026-11-06).

Run with the CosyVoice venv python:
  <cosyvoice3>/.venv/Scripts/python.exe gen_units.py --episode E:\\...\\4 --sections ch01

Reads <episode>/audio/utterances.json, writes <episode>/audio/vo-raw/<tag>/<id>.wav.
Resumable: existing non-empty wavs are skipped.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_PROFILE = HERE.parents[2] / "runtime" / "engines" / "tts" / "voice-assets" / "b2-warm-male-cosy3" / "profile.json"


def load_profile(path: Path) -> dict:
    prof = json.loads(path.read_text(encoding="utf-8"))
    for key in ("repo_dir", "model_dir", "venv_python", "reference_wav", "reference_text", "speed", "tag"):
        if not prof.get(key):
            raise SystemExit(f"[profile] missing {key}: {path}")
    return prof


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", required=True, help="episode dir containing audio/utterances.json")
    ap.add_argument("--profile", default=str(DEFAULT_PROFILE))
    ap.add_argument("--sections", default="", help="comma list; default = all except intro")
    ap.add_argument("--max-units", type=int, default=0, help="limit for smoke tests")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    prof = load_profile(Path(args.profile))
    ep = Path(args.episode).resolve()
    utt_path = ep / "audio" / "utterances.json"
    if not utt_path.exists():
        raise SystemExit(f"[episode] utterances.json not found: {utt_path}")
    doc = json.loads(utt_path.read_text(encoding="utf-8"))
    tag = args.tag or prof["tag"]
    out_dir = ep / "audio" / "vo-raw" / tag
    out_dir.mkdir(parents=True, exist_ok=True)

    wanted = [s.strip() for s in args.sections.split(",") if s.strip()]
    units = []
    for u in doc["utterances"]:
        if u.get("tts_blocked"):
            continue
        if u["section"] == "intro" and not wanted:
            continue
        if wanted and u["section"] not in wanted:
            continue
        units.append(u)
    if args.max_units > 0:
        units = units[: args.max_units]
    if not units:
        raise SystemExit("[units] nothing selected")

    repo = Path(prof["repo_dir"])
    sys.path.insert(0, str(repo))
    sys.path.insert(0, str(repo / "third_party" / "Matcha-TTS"))
    cache = Path(prof.get("cache_dir") or (repo.parent / "cache"))
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MODELSCOPE_CACHE", str(cache))
    os.environ.setdefault("HF_HOME", str(cache))

    import numpy as np
    import soundfile as sf
    import torch
    from cosyvoice.cli.cosyvoice import AutoModel

    t0 = time.time()
    model = AutoModel(model_dir=prof["model_dir"])
    sr = model.sample_rate
    prompt_text = prof["prompt_prefix"] + prof["reference_text"]
    speed = float(prof["speed"])
    print(f"[load] model loaded in {time.time()-t0:.1f}s sr={sr} speed={speed} tag={tag}", flush=True)

    meta_path = out_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    meta.update({"voice_id": prof.get("voice_id"), "engine": prof.get("engine"),
                 "profile": str(Path(args.profile).resolve()), "speed": speed,
                 "reference_wav": prof["reference_wav"], "sr": sr, "items": meta.get("items", {})})

    done = skipped = failed = 0
    total_audio = 0.0
    for i, u in enumerate(units, 1):
        dst = out_dir / f"{u['id']}.wav"
        if dst.exists() and dst.stat().st_size > 0:
            skipped += 1
            continue
        torch.cuda.synchronize()
        st = time.time()
        try:
            chunks = [j["tts_speech"].squeeze(0).cpu().numpy()
                      for j in model.inference_zero_shot(u["text"], prompt_text, prof["reference_wav"],
                                                         stream=False, speed=speed)]
            wav = np.concatenate(chunks) if chunks else np.zeros(1, dtype=np.float32)
            sf.write(str(dst), wav, sr, subtype="PCM_16")
            dt = time.time() - st
            sec = len(wav) / sr
            total_audio += sec
            meta["items"][u["id"]] = {"ok": True, "text": u["text"], "audio_s": round(sec, 3),
                                      "gen_s": round(dt, 1), "chars": len(u["text"])}
            done += 1
            print(f"[{i}/{len(units)}] {u['id']} {sec:.2f}s gen={dt:.1f}s", flush=True)
        except Exception as e:  # noqa: BLE001 - report and continue, per-unit resume
            meta["items"][u["id"]] = {"ok": False, "error": repr(e), "text": u["text"]}
            failed += 1
            print(f"[{i}/{len(units)}] {u['id']} FAIL {e!r}", flush=True)
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    meta["summary"] = {"units": len(units), "done": done, "skipped": skipped, "failed": failed,
                       "audio_s": round(total_audio, 2), "elapsed_s": round(time.time() - t0, 1)}
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[done] done={done} skipped={skipped} failed={failed} audio={total_audio:.1f}s", flush=True)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
