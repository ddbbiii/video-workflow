# -*- coding: utf-8 -*-
"""Generate 4 short intro VO lines with a chosen CosyVoice3 reference."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

WS = Path(r"E:\program\1project\video")
TTS = WS / "shared" / "runtime" / "engines" / "tts"
REPO = TTS / "cosyvoice3" / "repo"
MODEL = TTS / "cosyvoice3" / "model"
PROMPT_PREFIX = "You are a helpful assistant.<|endofprompt|>"

LINES = [
    ("line1-fragments", "世界只剩碎片。"),
    ("line2-hook", "城市空了，只剩你一人。"),
    ("line3-level", "第一级。"),
    ("line4-chapter", "空城的回声。"),
]

SHORT_LINES = [
    ("line1-fragments", "只剩碎片。"),
    ("line2-hook", "只剩你一人。"),
    ("line3-level", "一级。"),
    ("line4-chapter", "回声。"),
]

FULL_LINES = [
    ("line1-world", "这是你剩下的世界。"),
    ("line2-empty", "城市空了，只剩你一个人。"),
    ("line3-level", "第一级，空城的回声。"),
    ("line4-last", "你，是最后一个。"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--ref-text", required=True)
    ap.add_argument("--speed", type=float, default=1.05)
    ap.add_argument("--out", required=True)
    ap.add_argument("--short", action="store_true")
    ap.add_argument("--full", action="store_true")
    args = ap.parse_args()
    lines = FULL_LINES if args.full else (SHORT_LINES if args.short else LINES)

    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(REPO / "third_party" / "Matcha-TTS"))
    cache = TTS / "cosyvoice3" / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MODELSCOPE_CACHE", str(cache))
    os.environ.setdefault("HF_HOME", str(cache))

    import numpy as np
    import soundfile as sf
    import torch
    from cosyvoice.cli.cosyvoice import AutoModel

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    model = AutoModel(model_dir=str(MODEL))
    sr = model.sample_rate
    print(f"[load] {time.time()-t0:.1f}s sr={sr}", flush=True)

    meta = {"engine": "CosyVoice3-0.5B", "ref": args.ref, "speed": args.speed, "items": {}}
    for i, (key, text) in enumerate(lines):
        torch.manual_seed(2000 + i)
        st = time.time()
        chunks = [
            j["tts_speech"].squeeze(0).cpu().numpy()
            for j in model.inference_zero_shot(
                text, PROMPT_PREFIX + args.ref_text, args.ref,
                stream=False, speed=args.speed, text_frontend=False,
            )
        ]
        wav = np.concatenate(chunks) if chunks else np.zeros(1, dtype=np.float32)
        path = out / f"{key}.wav"
        sf.write(str(path), wav, sr, subtype="PCM_16")
        sec = len(wav) / sr
        meta["items"][key] = {"text": text, "wav": str(path), "duration_s": round(sec, 3),
                              "gen_s": round(time.time() - st, 1)}
        print(f"[ok] {key} {sec:.2f}s  {text}", flush=True)

    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[done]", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
