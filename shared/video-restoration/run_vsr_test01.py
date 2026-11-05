"""Single-shot RealBasicVSR comparison for the cinematic retry output.

The queue invokes this script only after the source I2V task is complete.
Model weights are fetched through ModelScope on first run and cached locally.
The source and Lanczos baseline are never overwritten.
"""
import json
import os
import shutil
import subprocess
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
INPUT = PROJECT / "projects/助眠解说/legacy-source/zhumian/b-geomagnetic-reversal/gen_rebuild/runs/20261007-ltx-cinematic-retry-c04"
OUTPUT = Path(os.environ.get("VSR_OUTPUT_DIR", str(INPUT.parent / "20261007-vsr-baseline-c04")))
MODEL_ID = "damo/cv_realbasicvsr_video-super-resolution_videolq"
VIDEO = INPUT / "ch1-c04-v2-01-raw-1280x704.mp4"
BASELINE = INPUT / "ch1-c04-v2-01-1920x1080-hq.mp4"
FFMPEG = shutil.which("ffmpeg") or r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"


def run(cmd):
    subprocess.run(cmd, check=True)


def main():
    if not VIDEO.exists() or not BASELINE.exists():
        raise FileNotFoundError("retry-c04 source or Lanczos baseline is missing")
    OUTPUT.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    manifest = {
        "id": "zhumian-vsr-baseline-c04-20261007",
        "model": MODEL_ID,
        "input": str(VIDEO),
        "baseline": str(BASELINE),
        "output_directory": str(OUTPUT),
        "status": "running",
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    from modelscope.pipelines import pipeline
    from modelscope.utils.constant import Tasks

    sr_raw = OUTPUT / "ch1-c04-v2-01-realbasicvsr-raw.mp4"
    sr_hq = OUTPUT / "ch1-c04-v2-01-realbasicvsr-1920x1080.mp4"
    pipe = pipeline(Tasks.video_super_resolution, model=MODEL_ID)
    result = pipe(str(VIDEO), output_video=str(sr_raw), demo_service=False)
    produced = Path(result.get("output_video", sr_raw))
    if produced != sr_raw:
        shutil.copy2(produced, sr_raw)
    run([FFMPEG, "-v", "error", "-y", "-i", str(sr_raw), "-an", "-vf", "scale=1920:1080:flags=lanczos,setsar=1", "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(sr_hq)])
    for path in (VIDEO, BASELINE, sr_raw, sr_hq):
        run([FFMPEG, "-v", "error", "-i", str(path), "-f", "null", "-"])
    manifest.update({
        "status": "completed",
        "realbasicvsr_raw": str(sr_raw),
        "realbasicvsr_1920x1080": str(sr_hq),
        "decode_ok": True,
        "elapsed_s": round(time.monotonic() - started, 1),
        "visual_qa": "pending_playback",
    })
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    lock = PROJECT / "shared/work/cache/gpu.lock"
    if (PROJECT / "shared/runtime/comfy/cache/gpu.lock").exists():
        raise RuntimeError("Shared GPU lock exists")
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("x", encoding="utf-8") as handle:
        json.dump({"owner": "zhumian-vsr-baseline-c04-retry2-20261007", "pid": os.getpid()}, handle)
    try:
        main()
    finally:
        if lock.exists() and json.loads(lock.read_text(encoding="utf-8")).get("pid") == os.getpid():
            lock.unlink()
