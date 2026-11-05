# -*- coding: utf-8 -*-
"""TTS runner with self-managed GPU lock (sleep-aid pattern, per STATE.md 2026-10-13).

移植自 newton 06_run_tts.py。TTS 引擎/venv 待 AUDIO_PLAN(见 AUDIO_PLAN.py)。

Usage: python 06_run_tts.py <jobname> [only_ids]
Writes/updates the gpu-queue request life-tts-20261024 across chapters.
"""
from __future__ import annotations
import json, os, subprocess, sys, time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
import sys as _sys
_sys.path.insert(0, str(HERE))
import AUDIO_PLAN as AP

EP = HERE.parents[2]
JOBS = EP / "audio" / "jobs"
OUT = EP / "audio" / "vo-raw" / (AP.VOICE_TAG or "TODO_AUDIO_PLAN")
RUN = EP / "runs" / "20261024-lm-b01"
CKPT = RUN / "CHECKPOINT.json"
LOCK = Path(r"E:\program\1project\video\shared\work\cache\gpu.lock")
LEGACY = Path(r"E:\program\1project\video\shared\runtime\comfy\cache\gpu.lock")
REQ = Path(r"E:\program\1project\video\shared\gpu-queue\requests\life-tts-20261024.json")

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["MODELSCOPE_CACHE"] = r"E:\program\1project\video\shared\runtime\engines\tts\modelscope-cache"
os.environ["HF_HOME"] = r"E:\program\1project\video\shared\runtime\engines\tts\hf-cache"

REQ_ID = "life-tts-20261024"
OWNER = f"{REQ_ID}:{sys.argv[1] if len(sys.argv) > 1 else 'na'}"

def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")

def log(msg):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [{OWNER}] {msg}"
    print(line, flush=True)
    (RUN / "logs" / "tts.log").parent.mkdir(parents=True, exist_ok=True)
    with (RUN / "logs" / "tts.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def update_ckpt(**kw):
    d = {}
    if CKPT.exists():
        try: d = json.loads(CKPT.read_text(encoding="utf-8"))
        except Exception: d = {}
    d.update(kw); d["updated_at"] = now_iso()
    CKPT.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def update_req(**kw):
    if REQ.exists():
        try:
            d = json.loads(REQ.read_text(encoding="utf-8-sig"))
            d.update(kw)
            REQ.write_text(json.dumps(d, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
        except Exception as e:
            log(f"req update skipped: {e}")

def pid_alive(pid):
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        f"Get-Process -Id {pid} -ErrorAction SilentlyContinue"],
                       capture_output=True)
    return r.returncode == 0 and r.stdout.strip()

def acquire():
    for p in (LOCK, LEGACY):
        if not p.exists():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            pid = d.get("pid")
            if pid and pid_alive(pid):
                raise RuntimeError(f"GPU lock held by {d.get('owner')} pid {pid}")
            p.unlink(missing_ok=True)
            log(f"cleared stale lock {p}")
        except RuntimeError:
            raise
        except Exception:
            p.unlink(missing_ok=True)
    payload = {"owner": OWNER, "line": "助眠解说", "pid": os.getpid(),
               "started": now_iso(), "task": "life-manual TTS (引擎待AUDIO_PLAN)"}
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LEGACY.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(text, encoding="utf-8")
    LEGACY.write_text(text, encoding="utf-8")
    return payload

def release():
    for p in (LOCK, LEGACY):
        try:
            if p.exists():
                d = json.loads(p.read_text(encoding="utf-8"))
                if d.get("owner") == OWNER:
                    p.unlink(); log(f"released {p}")
                else:
                    log(f"skip release {p} owner={d.get('owner')}")
        except Exception as e:
            log(f"release error {p}: {e}")

def main():
    AP.require_audio_plan("TTS_VENV_PY", "TTS_GEN_SCRIPT", "VOICE_TAG")
    jobname = sys.argv[1]
    only = sys.argv[2] if len(sys.argv) > 2 else None
    job_path = JOBS / f"{jobname}.json"
    job = json.loads(job_path.read_text(encoding="utf-8"))
    expected = [s["id"] for s in job["shots"]]
    missing = [i for i in expected if not (OUT / f"{i}.wav").exists()]
    if not missing:
        log(f"{jobname}: all {len(expected)} present, skip")
        return 0
    log(f"START {jobname} missing={len(missing)}/{len(expected)}")
    lock = acquire()
    log(f"acquired lock pid={lock['pid']}")
    update_req(status="running", pid=os.getpid(), log_path=str(RUN / "logs" / "tts.log"))
    update_ckpt(stage="tts", in_progress=[f"tts_{jobname}"],
                tts_pid=os.getpid(), tts_job=jobname, blockers=[])
    code = 1
    try:
        cmd = [str(AP.TTS_VENV_PY), str(AP.TTS_GEN_SCRIPT), str(job_path)]
        if only:
            cmd.append(only)
        r = subprocess.run(cmd)
        code = r.returncode
    finally:
        release()
    n_after = sum(1 for i in expected if (OUT / f"{i}.wav").exists())
    log(f"END {jobname} exit={code} have={n_after}/{len(expected)}")
    update_ckpt(tts_job=None, tts_pid=None,
                **{f"tts_done_{jobname}": n_after})
    update_req(status="completed" if n_after == len(expected) else "failed",
               completed_at=now_iso(), note=f"{jobname} {n_after}/{len(expected)}")
    return 0 if n_after == len(expected) else 1

if __name__ == "__main__":
    raise SystemExit(main())
