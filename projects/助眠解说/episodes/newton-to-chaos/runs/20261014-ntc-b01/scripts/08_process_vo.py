# -*- coding: utf-8 -*-
"""牛顿到混沌 VO 处理链（AUDIO_PLAN.md 第3节）：
裁头尾静音(RMS -45dB/20ms帧/前留0.10s/后留0.15s) → atempo=0.774224 一次。
CPU 任务，可断点续跑（已有输出跳过）。"""
from __future__ import annotations
import json, subprocess
from datetime import datetime
from pathlib import Path
import numpy as np
import soundfile as sf

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\newton-to-chaos")
RAW = EP / "audio" / "vo-raw" / "lightexpr-seed7"
OUT = EP / "audio" / "vo-processed" / "lightexpr-final"
LOG = EP / "runs" / "20261014-ntc-b01" / "logs" / "vo_process.log"
TMP = Path(r"C:\Users\10060\agent-tools\_vo_trim_tmp_ntc")
ATEMPO = 0.774224
FRAME_MS = 20
RMS_DB = -45.0
KEEP_HEAD = 0.10
KEEP_TAIL = 0.15
FFMPEG = r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"

OUT.mkdir(parents=True, exist_ok=True)
TMP.mkdir(parents=True, exist_ok=True)
LOG.parent.mkdir(parents=True, exist_ok=True)

def log(msg: str):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def trim_silence(y: np.ndarray, sr: int):
    if y.ndim > 1:
        y = y.mean(axis=1)
    frame = max(1, int(sr * FRAME_MS / 1000))
    thr = 10 ** (RMS_DB / 20.0)
    n = len(y) // frame
    if n == 0:
        return y
    frames = y[: n * frame].reshape(n, frame)
    rms = np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1))
    active = np.where(rms > thr)[0]
    if len(active) == 0:
        return y
    start = max(0, int(active[0] * frame - KEEP_HEAD * sr))
    end = min(len(y), int((active[-1] + 1) * frame + KEEP_TAIL * sr))
    return y[start:end]

def process_one(src: Path, dst: Path):
    y, sr = sf.read(str(src), always_2d=False)
    y = trim_silence(np.asarray(y), sr)
    tmp = TMP / (src.stem + ".trim.wav")
    sf.write(str(tmp), y, sr, subtype="PCM_16")
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [FFMPEG, "-y", "-i", str(tmp), "-filter:a", f"atempo={ATEMPO}", "-acodec", "pcm_s16le", str(dst)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    tmp.unlink(missing_ok=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[-800:])
    y2, sr2 = sf.read(str(dst))
    return {"sr": int(sr2), "seconds": round(len(y2) / float(sr2), 3), "bytes": dst.stat().st_size}

def main():
    utt = json.loads((EP / "audio" / "utterances.json").read_text(encoding="utf-8"))
    blocked = {u["id"] for u in utt["utterances"] if u.get("tts_blocked")}
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {
        "atempo": ATEMPO, "rms_db": RMS_DB, "keep_head": KEEP_HEAD, "keep_tail": KEEP_TAIL, "items": {}}
    wavs = sorted(p for p in RAW.glob("*.wav") if p.stem not in blocked)
    log(f"START process n={len(wavs)} blocked={len(blocked)}")
    for src in wavs:
        rel = src.name
        dst = OUT / rel
        if dst.exists() and dst.stat().st_size > 0:
            continue
        try:
            info = process_one(src, dst)
            manifest["items"][rel] = {"ok": True, **info, "src": str(src)}
            log(f"OK {rel} {info['seconds']}s")
        except Exception as e:
            manifest["items"][rel] = {"ok": False, "error": str(e)}
            log(f"FAIL {rel} {e}")
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    done = sum(1 for v in manifest["items"].values() if v.get("ok"))
    fails = [k for k, v in manifest["items"].items() if not v.get("ok")]
    total = sum(v.get("seconds", 0) for v in manifest["items"].values() if v.get("ok"))
    manifest["total_seconds"] = round(total, 2)
    manifest["fail_count"] = len(fails)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"DONE processed={done}/{len(wavs)} total_s={total:.1f} fails={len(fails)}")
    return 0 if not fails else 1

if __name__ == "__main__":
    raise SystemExit(main())
