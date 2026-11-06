# -*- coding: utf-8 -*-
"""Trim + fade + 48 kHz resample for CosyVoice raw units (system Python, numpy only).

Input : <episode>/audio/vo-raw/<tag>/<id>.wav   (24 kHz PCM16)
Output: <episode>/audio/vo-processed/<tag>/<id>.wav (48 kHz PCM16)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DEFAULT_PROFILE = HERE.parents[2] / "runtime" / "engines" / "tts" / "voice-assets" / "b2-warm-male-cosy3" / "profile.json"


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


def trim_fade(y: np.ndarray, sr: int, rms_db: float, frame_ms: int,
              keep_head: float, keep_tail: float, fade: float):
    n = max(1, int(sr * frame_ms / 1000))
    m = len(y) // n
    if m == 0:
        return y
    rms = np.sqrt(np.mean(y[: m * n].reshape(m, n) ** 2, axis=1))
    act = np.where(rms > 10 ** (rms_db / 20))[0]
    if not len(act):
        return y
    a = max(0, int(act[0] * n - keep_head * sr))
    b = min(len(y), int((act[-1] + 1) * n + keep_tail * sr))
    out = y[a:b].copy()
    f = int(fade * sr)
    if len(out) > 2 * f:
        out[:f] *= np.linspace(0, 1, f, dtype=np.float32)
        out[-f:] *= np.linspace(1, 0, f, dtype=np.float32)
    return out


def resample(src: Path, dst: Path, sr_out: int):
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
           "-ar", str(sr_out), "-ac", "1", "-c:a", "pcm_s16le", str(dst)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit((r.stderr or r.stdout)[-800:])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", required=True)
    ap.add_argument("--profile", default=str(DEFAULT_PROFILE))
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    prof = json.loads(Path(args.profile).read_text(encoding="utf-8"))
    ep = Path(args.episode).resolve()
    tag = args.tag or prof["tag"]
    src_dir = ep / "audio" / "vo-raw" / tag
    dst_dir = ep / "audio" / "vo-processed" / tag
    dst_dir.mkdir(parents=True, exist_ok=True)
    tmp = dst_dir / "_tmp24.wav"

    manifest_path = dst_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    manifest.update({k: prof[k] for k in ("voice_id", "speed", "trim_rms_db", "trim_frame_ms",
                                         "trim_keep_head_s", "trim_keep_tail_s", "fade_s", "sample_rate")})
    manifest.setdefault("items", {})

    wavs = sorted(src_dir.glob("*.wav"))
    if not wavs:
        raise SystemExit(f"[input] no wav under {src_dir}")
    done = skipped = 0
    for p in wavs:
        dst = dst_dir / p.name
        if dst.exists() and dst.stat().st_size > 0:
            skipped += 1
            continue
        y, sr = read_pcm16(p)
        y = trim_fade(y, sr, prof["trim_rms_db"], prof["trim_frame_ms"],
                      prof["trim_keep_head_s"], prof["trim_keep_tail_s"], prof["fade_s"])
        write_pcm16(tmp, y, sr)
        resample(tmp, dst, prof["sample_rate"])
        y2, sr2 = read_pcm16(dst)
        manifest["items"][p.stem] = {"ok": True, "raw_sr": sr, "raw_s": round(len(y) / sr, 3),
                                     "out_sr": sr2, "out_s": round(len(y2) / sr2, 3),
                                     "bytes": dst.stat().st_size}
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
        done += 1
        print(f"[trim] {p.stem} {len(y)/sr:.2f}s -> {len(y2)/sr2:.2f}s", flush=True)
    tmp.unlink(missing_ok=True)
    print(f"[done] processed={done} skipped={skipped}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
