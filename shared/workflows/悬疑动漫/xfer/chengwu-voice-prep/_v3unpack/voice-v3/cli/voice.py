# -*- coding: utf-8 -*-
"""Voice Pipeline v3 single CLI: preflight | index | audition | render | mix | migrate-status."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"E:\program\1project\video\shared\project-tools")
V3 = ROOT / "production" / "voice-v3"
REG = V3 / "registry" / "anchors.json"
LIB = V3 / "library" / "anchors"
DRAFTS = V3 / "library" / "drafts"
RUNS = V3 / "runs"
BASE = Path(r"E:\AI\Qwen3-TTS\models\Qwen3-TTS-12Hz-1.7B-Base")
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
PY_TTS = Path(r"E:\AI\Qwen3-TTS\.venv\Scripts\python.exe")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest().upper()


def load_registry() -> dict:
    if not REG.exists():
        raise FileNotFoundError(f"missing registry: {REG}")
    return json.loads(REG.read_text(encoding="utf-8"))


def save_registry(data: dict) -> None:
    REG.parent.mkdir(parents=True, exist_ok=True)
    REG.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_anchor(anchor_id: str, *, require_approved: bool = True) -> dict:
    data = load_registry()
    anchor = next((a for a in data.get("anchors", []) if a.get("id") == anchor_id), None)
    if not anchor:
        raise RuntimeError(f"anchor not found: {anchor_id}")
    if require_approved and anchor.get("status") != "approved":
        raise RuntimeError(f"anchor not approved: {anchor_id} status={anchor.get('status')}")
    ref = Path(anchor["reference_wav"])
    if not ref.is_file():
        raise FileNotFoundError(f"reference wav missing: {ref}")
    got = sha256_file(ref)
    expect = (anchor.get("sha256") or "").upper()
    if expect and got != expect:
        raise RuntimeError(f"sha mismatch {anchor_id}: got {got} expect {expect}")
    transcript = anchor.get("transcript") or ""
    if not transcript:
        txt = Path(anchor.get("reference_txt") or "")
        if txt.is_file():
            transcript = txt.read_text(encoding="utf-8").strip()
    if not transcript:
        raise RuntimeError(f"missing transcript for {anchor_id}")
    return {**anchor, "reference_wav": ref, "transcript": transcript, "sha256": got}


def comfy_busy(ports=(8188, 8189)) -> list:
    busy = []
    for port in ports:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/system_stats", timeout=1)
            busy.append(port)
        except Exception:
            pass
    return busy


def cmd_preflight(args: argparse.Namespace) -> int:
    checks = []
    def add(ok, code, detail, blocking=True):
        checks.append({"passed": bool(ok), "code": code, "detail": detail, "blocking": blocking})

    add(V3.is_dir(), "v3-root", str(V3))
    add(REG.is_file(), "registry", str(REG))
    add(BASE.is_dir(), "base-model", str(BASE))
    cfg = BASE / "config.json"
    if cfg.exists():
        t = json.loads(cfg.read_text(encoding="utf-8")).get("tts_model_type")
        add(t == "base", "base-type", f"tts_model_type={t}")
    else:
        add(False, "base-type", "config.json missing")
    add(Path(FFMPEG).exists() or shutil.which("ffmpeg"), "ffmpeg", FFMPEG)
    busy = comfy_busy()
    add(not busy, "comfy-idle", f"busy={busy}" if busy else "idle", blocking=False)
    data = load_registry() if REG.exists() else {"anchors": []}
    approved = [a for a in data.get("anchors", []) if a.get("status") == "approved"]
    add(True, "anchor-count", f"approved={len(approved)} total={len(data.get('anchors', []))}", blocking=False)
    if args.anchor:
        try:
            a = find_anchor(args.anchor)
            add(True, "anchor-ok", f"{a['id']} sha={a['sha256'][:12]}...")
        except Exception as e:
            add(False, "anchor-ok", str(e))
    blocking_fail = [c for c in checks if c["blocking"] and not c["passed"]]
    out = {
        "schema": "voice-v3-preflight",
        "ready": not blocking_fail,
        "checks": checks,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["ready"] else 2


def cmd_index(args: argparse.Namespace) -> int:
    data = load_registry()
    entries = []
    for a in data.get("anchors", []):
        wav = a.get("reference_wav")
        entries.append({
            "id": a.get("id"),
            "status": a.get("status"),
            "project": a.get("project"),
            "display_name": a.get("display_name"),
            "roles": a.get("roles") or [],
            "reference_wav": wav,
            "audio_exists": bool(wav) and Path(wav).exists(),
            "sha256": a.get("sha256"),
        })
    for d in sorted(DRAFTS.glob("*")) if DRAFTS.exists() else []:
        if d.is_dir():
            entries.append({
                "id": d.name,
                "status": "draft",
                "project": "draft",
                "path": str(d),
                "audio_exists": any(d.glob("*.wav")),
            })
    index = {
        "schema": "voice-v3-index",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "registry": str(REG),
        "count": len(entries),
        "entries": entries,
    }
    out = V3 / "VOICE-INDEX.json"
    out.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "count": len(entries)}, ensure_ascii=False))
    return 0


def _import_tts():
    import numpy as np
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel
    return np, sf, torch, Qwen3TTSModel


def normalize_wav(src: Path, dst: Path) -> dict:
    import soundfile as sf
    subprocess.run(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
         "-af", "highpass=f=55,loudnorm=I=-18:TP=-3:LRA=7,aresample=48000",
         "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(dst)],
        check=True,
    )
    info = sf.info(str(dst))
    return {
        "sample_rate": int(info.samplerate),
        "channels": int(info.channels),
        "duration_seconds": round(info.frames / info.samplerate, 3),
    }


def _render_segments(anchor: dict, segments: list, out: Path, seed: int, language: str, allow_busy: bool, combined: bool, tag: str) -> dict:
    np, sf, torch, Qwen3TTSModel = _import_tts()
    busy = comfy_busy()
    if busy and not allow_busy:
        raise RuntimeError(f"Comfy busy on {busy}; stop render or pass --allow-comfy-busy")
    out.mkdir(parents=True, exist_ok=True)
    work = out / "_raw"
    work.mkdir(exist_ok=True)
    random.seed(seed)
    np.random.seed(seed % (2**32))
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    t0 = time.perf_counter()
    model = Qwen3TTSModel.from_pretrained(str(BASE), device_map="cuda:0", dtype=torch.bfloat16, attn_implementation="sdpa")
    prompt = model.create_voice_clone_prompt(
        ref_audio=str(anchor["reference_wav"]),
        ref_text=anchor["transcript"],
        x_vector_only_mode=False,
    )
    prompt_fp = sha256_text(f"{anchor['id']}|{anchor['sha256']}|{anchor['transcript']}|seed={seed}|do_sample=false")
    records = []
    for i, seg in enumerate(segments, 1):
        text = seg["text"].strip()
        sid = seg.get("id") or f"S{i:02d}"
        began = time.perf_counter()
        audio, sr = model.generate_voice_clone(text=text, language=language, voice_clone_prompt=prompt, do_sample=False)
        raw = work / f"{i:03d}-{sid}-raw.wav"
        sf.write(raw, audio[0], sr, subtype="PCM_16")
        final = out / f"{i:03d}-{sid}-48k.wav"
        meta = normalize_wav(raw, final)
        raw.unlink(missing_ok=True)
        records.append({
            "index": i, "id": sid, "text": text, "audio": str(final),
            "sha256": sha256_file(final), "generation_seconds": round(time.perf_counter() - began, 3), **meta,
        })
        print(f"OK {sid} {meta['duration_seconds']}s", flush=True)
    combined_path = None
    if combined and records:
        silence = out / "_silence.wav"
        subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                        "-i", "anullsrc=r=48000:cl=mono", "-t", "0.35", "-c:a", "pcm_s16le", str(silence)], check=True)
        lines = []
        for j, rec in enumerate(records):
            lines.append(f"file '{Path(rec['audio']).as_posix()}'")
            if j < len(records) - 1:
                lines.append(f"file '{silence.as_posix()}'")
        lst = out / "_concat.txt"
        lst.write_text("\n".join(lines) + "\n", encoding="utf-8")
        combined_path = out / "combined-48k.wav"
        subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
                        "-i", str(lst), "-c", "copy", str(combined_path)], check=True)
        silence.unlink(missing_ok=True)
        lst.unlink(missing_ok=True)
    try:
        work.rmdir()
    except OSError:
        pass
    manifest = {
        "schema": "voice-v3-run",
        "pipeline": "voice-v3",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tag": tag or None,
        "anchor_id": anchor["id"],
        "anchor_sha256": anchor["sha256"],
        "project": anchor.get("project"),
        "engine": "Qwen3-TTS-12Hz-1.7B-Base",
        "clone_prompt_fingerprint": prompt_fp,
        "decode": {"do_sample": False, "language": language},
        "episode_seed": seed,
        "comfy_busy": busy,
        "segments": records,
        "combined": str(combined_path) if combined_path else None,
        "elapsed_seconds": round(time.perf_counter() - t0, 3),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def cmd_audition(args: argparse.Namespace) -> int:
    anchor = find_anchor(args.anchor)
    texts = args.text or [
        "雨停以后，街道反而比刚才更安静。她站在门外，没有立刻掏钥匙。",
        "我知道那个人说的每一句话都像我，可停顿的位置和我不一样。",
        "他把票递回来，声音很轻：你可以不相信这辆车，但门里的人已经等了很久。",
    ]
    if len(texts) != 3:
        raise RuntimeError("audition requires exactly 3 texts")
    segs = [{"id": f"T{i}", "text": t} for i, t in enumerate(texts, 1)]
    out = Path(args.out) if args.out else RUNS / f"audition-{args.anchor}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    man = _render_segments(anchor, segs, out, args.seed, args.language, args.allow_comfy_busy, True, "audition")
    man["status"] = "human-listening-review-required"
    (out / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "combined": man.get("combined")}, ensure_ascii=False))
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    anchor = find_anchor(args.anchor)
    if args.texts_json:
        data = json.loads(Path(args.texts_json).read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("segments") or data.get("texts") or []
        segs = []
        for i, item in enumerate(data, 1):
            if isinstance(item, str):
                segs.append({"id": f"S{i:02d}", "text": item})
            else:
                segs.append({"id": item.get("id") or f"S{i:02d}", "text": item["text"]})
    elif args.text:
        segs = [{"id": f"S{i:02d}", "text": t} for i, t in enumerate(args.text, 1)]
    else:
        raise RuntimeError("need --texts-json or --text")
    out = Path(args.out) if args.out else RUNS / f"render-{args.anchor}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    man = _render_segments(anchor, segs, out, args.seed, args.language, args.allow_comfy_busy, args.combined, args.tag or "render")
    print(json.dumps({"ok": True, "out": str(out), "segments": len(man["segments"]), "elapsed": man["elapsed_seconds"]}, ensure_ascii=False))
    return 0


def cmd_mix(args: argparse.Namespace) -> int:
    video, voice, out = Path(args.video), Path(args.voice), Path(args.out)
    if not video.is_file() or not voice.is_file():
        raise FileNotFoundError("video or voice missing")
    out.parent.mkdir(parents=True, exist_ok=True)
    fc = f"[0:a]volume={args.bed_vol}[a0];[1:a]volume={args.voice_vol},apad[a1];[a0][a1]amix=inputs=2:duration=first:dropout_transition=2[aout]"
    subprocess.run(
        [FFMPEG, "-hide_banner", "-y", "-i", str(video), "-i", str(voice),
         "-filter_complex", fc, "-map", "0:v", "-map", "[aout]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)],
        check=True,
    )
    print(json.dumps({"ok": True, "out": str(out)}, ensure_ascii=False))
    return 0


def cmd_migrate_status(args: argparse.Namespace) -> int:
    data = load_registry() if REG.exists() else {"anchors": []}
    print(json.dumps({
        "v3_root": str(V3),
        "registry": str(REG),
        "anchors": len(data.get("anchors", [])),
        "approved": sum(1 for a in data.get("anchors", []) if a.get("status") == "approved"),
        "library_dirs": [p.name for p in LIB.iterdir()] if LIB.exists() else [],
    }, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="voice-v3")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("preflight"); sp.add_argument("--anchor"); sp.set_defaults(func=cmd_preflight)
    sp = sub.add_parser("index"); sp.set_defaults(func=cmd_index)
    sp = sub.add_parser("audition")
    sp.add_argument("--anchor", required=True)
    sp.add_argument("--out")
    sp.add_argument("--text", action="append")
    sp.add_argument("--seed", type=int, default=2026092111)
    sp.add_argument("--language", default="Chinese")
    sp.add_argument("--allow-comfy-busy", action="store_true")
    sp.set_defaults(func=cmd_audition)
    sp = sub.add_parser("render")
    sp.add_argument("--anchor", required=True)
    sp.add_argument("--out")
    sp.add_argument("--texts-json")
    sp.add_argument("--text", action="append")
    sp.add_argument("--seed", type=int, default=2026092111)
    sp.add_argument("--language", default="Chinese")
    sp.add_argument("--allow-comfy-busy", action="store_true")
    sp.add_argument("--combined", action="store_true")
    sp.add_argument("--tag", default="")
    sp.set_defaults(func=cmd_render)
    sp = sub.add_parser("mix")
    sp.add_argument("--video", required=True)
    sp.add_argument("--voice", required=True)
    sp.add_argument("--out", required=True)
    sp.add_argument("--voice-vol", type=float, default=1.0)
    sp.add_argument("--bed-vol", type=float, default=0.18)
    sp.set_defaults(func=cmd_mix)
    sp = sub.add_parser("migrate-status"); sp.set_defaults(func=cmd_migrate_status)

    args = p.parse_args()
    try:
        return args.func(args)
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
