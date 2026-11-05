# -*- coding: utf-8 -*-
"""Generic Base-clone voice renderer for approved anchors.

One resident Base model + one in-memory clone prompt per run.
Input: --anchor + --texts-json (list of {id,text}) OR --text repeated.
Output: segment wavs (48k mono) + manifest.json with fingerprints.

Does NOT register anchors. Does NOT use CustomVoice/VoiceDesign.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

ROOT = Path(r"E:\program\1project\video\shared\project-tools")
BASE = Path(r"E:\AI\Qwen3-TTS\models\Qwen3-TTS-12Hz-1.7B-Base")
REGISTRY = ROOT / "production/voice-library/voice-anchor-registry-v1.json"
PROFILE = ROOT / "tools/voice-consistency/qwen3-base-voice-clone-profile-v1.json"
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest().upper()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def load_anchor(anchor_id: str) -> dict:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    anchor = next((item for item in registry.get("anchors", []) if item.get("id") == anchor_id), None)
    if not anchor:
        raise RuntimeError(f"anchor not found: {anchor_id}")
    if anchor.get("status") != "approved":
        raise RuntimeError(f"anchor not approved: {anchor_id} status={anchor.get('status')}")
    audio = Path(anchor.get("audio_path") or (anchor.get("reference_audio") or {}).get("path") or "")
    transcript = anchor.get("exact_transcript") or (anchor.get("transcript") or {}).get("text")
    if not audio.is_file():
        raise FileNotFoundError(f"reference audio missing: {audio}")
    if not transcript:
        raise RuntimeError(f"anchor missing exact_transcript: {anchor_id}")
    expect = (anchor.get("sha256") or (anchor.get("reference_audio") or {}).get("sha256") or "").upper()
    got = sha256_file(audio)
    if expect and got != expect:
        raise RuntimeError(f"reference audio sha mismatch for {anchor_id}: got {got} expect {expect}")
    return {
        "id": anchor_id,
        "audio_path": audio,
        "transcript": transcript,
        "sha256": got,
        "raw": anchor,
    }


def comfy_busy(ports=(8188, 8189)) -> list:
    busy = []
    for port in ports:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/system_stats", timeout=1)
            busy.append(port)
        except Exception:
            pass
    return busy


def normalize_wav(src: Path, dst: Path) -> dict:
    subprocess.run(
        [
            FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(src),
            "-af", "highpass=f=55,loudnorm=I=-18:TP=-3:LRA=7,aresample=48000",
            "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(dst),
        ],
        check=True,
    )
    info = sf.info(str(dst))
    return {
        "sample_rate": int(info.samplerate),
        "channels": int(info.channels),
        "duration_seconds": round(info.frames / info.samplerate, 3),
    }


def load_segments(args) -> list:
    if args.texts_json:
        data = json.loads(Path(args.texts_json).read_text(encoding="utf-8"))
        if isinstance(data, dict) and "segments" in data:
            data = data["segments"]
        segs = []
        for i, item in enumerate(data, 1):
            if isinstance(item, str):
                segs.append({"id": f"S{i:02d}", "text": item})
            else:
                segs.append({"id": item.get("id") or f"S{i:02d}", "text": item["text"]})
        return segs
    if args.text:
        return [{"id": f"S{i:02d}", "text": t} for i, t in enumerate(args.text, 1)]
    raise RuntimeError("provide --texts-json or repeated --text")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render episode/audition voice from an approved Base-clone anchor")
    parser.add_argument("--anchor", required=True)
    parser.add_argument("--out", required=True, help="output directory")
    parser.add_argument("--texts-json", help="JSON list[{id,text}] or {segments:[...]}")
    parser.add_argument("--text", action="append", dest="text")
    parser.add_argument("--seed", type=int, default=2026092101)
    parser.add_argument("--language", default="Chinese")
    parser.add_argument("--allow-comfy-busy", action="store_true", help="allow run even if 8188/8189 respond")
    parser.add_argument("--combined", action="store_true", help="also write combined.wav with 0.35s gaps")
    parser.add_argument("--tag", default="", help="optional run tag stored in manifest")
    args = parser.parse_args()

    if not BASE.is_dir():
        raise FileNotFoundError(f"Base model missing: {BASE}")

    busy = comfy_busy()
    if busy and not args.allow_comfy_busy:
        raise RuntimeError(f"Comfy ports busy {busy}; stop H3/Portable or pass --allow-comfy-busy")

    anchor = load_anchor(args.anchor)
    segments = load_segments(args)
    if not segments:
        raise RuntimeError("no segments")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = out / "_raw"
    work.mkdir(exist_ok=True)

    profile = json.loads(PROFILE.read_text(encoding="utf-8")) if PROFILE.exists() else {}
    profile_fp = sha256_text(json.dumps(profile, sort_keys=True, ensure_ascii=False))

    random.seed(args.seed)
    np.random.seed(args.seed % (2**32))
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    started = time.perf_counter()
    model = Qwen3TTSModel.from_pretrained(
        str(BASE), device_map="cuda:0", dtype=torch.bfloat16, attn_implementation="sdpa"
    )
    clone_prompt = model.create_voice_clone_prompt(
        ref_audio=str(anchor["audio_path"]),
        ref_text=anchor["transcript"],
        x_vector_only_mode=False,
    )
    prompt_fp = sha256_text(
        f"{anchor['id']}|{anchor['sha256']}|{anchor['transcript']}|seed={args.seed}|do_sample=false"
    )

    records = []
    for index, seg in enumerate(segments, 1):
        text = (seg.get("text") or "").strip()
        if not text:
            raise RuntimeError(f"empty text for segment {seg.get('id')}")
        sid = str(seg.get("id") or f"S{index:02d}")
        began = time.perf_counter()
        audio, sample_rate = model.generate_voice_clone(
            text=text,
            language=args.language,
            voice_clone_prompt=clone_prompt,
            do_sample=False,
        )
        raw = work / f"{index:03d}-{sid}-raw.wav"
        sf.write(raw, audio[0], sample_rate, subtype="PCM_16")
        final = out / f"{index:03d}-{sid}-48k.wav"
        meta = normalize_wav(raw, final)
        raw.unlink(missing_ok=True)
        records.append({
            "index": index,
            "id": sid,
            "text": text,
            "audio": str(final),
            "sha256": sha256_file(final),
            "generation_seconds": round(time.perf_counter() - began, 3),
            **meta,
        })
        print(f"OK {sid} {meta['duration_seconds']}s", flush=True)

    combined_path = None
    if args.combined and records:
        silence = out / "_silence_0p35.wav"
        subprocess.run(
            [FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
             "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", "0.35",
             "-c:a", "pcm_s16le", str(silence)],
            check=True,
        )
        inter = []
        for i, rec in enumerate(records):
            inter.append(f"file '{Path(rec['audio']).as_posix()}'")
            if i < len(records) - 1:
                inter.append(f"file '{silence.as_posix()}'")
        lst = out / "_concat.txt"
        lst.write_text("\n".join(inter) + "\n", encoding="utf-8")
        combined_path = out / "combined-48k.wav"
        subprocess.run(
            [FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
             "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(combined_path)],
            check=True,
        )
        silence.unlink(missing_ok=True)
        lst.unlink(missing_ok=True)

    try:
        work.rmdir()
    except OSError:
        pass

    manifest = {
        "schema": "render-voice-episode-v1",
        "status": "rendered-stems-ready",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tag": args.tag or None,
        "anchor_id": anchor["id"],
        "anchor_sha256": anchor["sha256"],
        "engine": "Qwen3-TTS-12Hz-1.7B-Base",
        "profile_id": profile.get("profile_id"),
        "profile_fingerprint": profile_fp,
        "clone_prompt_fingerprint": prompt_fp,
        "decode": {"do_sample": False, "language": args.language},
        "episode_seed": args.seed,
        "policy": [
            "one resident Base model",
            "one in-memory clone prompt for all segments",
            "do_sample=false",
            "no atempo",
            "no CustomVoice/VoiceDesign for delivery",
        ],
        "comfy_ports_seen_busy": busy,
        "segments": records,
        "combined": str(combined_path) if combined_path else None,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "segments": len(records), "elapsed": manifest["elapsed_seconds"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
