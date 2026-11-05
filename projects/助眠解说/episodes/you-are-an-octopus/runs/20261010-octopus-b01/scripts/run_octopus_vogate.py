# -*- coding: utf-8 -*-
"""Octopus vo_gate — do NOT hold gpu.lock while gate runs (run_shots waits on lock)."""
from __future__ import annotations
import json, os, subprocess, sys, time
from datetime import datetime
from pathlib import Path

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\you-are-an-octopus")
PY = Path(r"E:\program\1project\video\shared\runtime\engines\tts\voxcpm\.venv\Scripts\python.exe")
GATE = Path(r"E:\program\1project\video\shared\runtime\envs\vo-gate\kepu-pipeline-box\scripts\vo_gate.py")
PROFILE = EP / "audio" / "vo_gate" / "profile_b2_local.yaml"
SHOTS = EP / "audio" / "vo-raw" / "seed7"
JOBS = EP / "audio" / "jobs"
SHOTLISTS = EP / "audio" / "gate"
RUN = EP / "runs" / "20261010-octopus-b01"
stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
OUT_ROOT = EP / "audio" / "vo_gate" / "runs" / stamp
LOG = RUN / "logs" / "vo_gate.log"
CKPT = RUN / "CHECKPOINT.json"
ORDER = ["intro", "bridge", "ch01", "ch02", "ch03", "ch04", "ch05", "ch06", "ch07", "ch08", "ch09", "ch10"]
REQ_ID = "zhumian-octopus-vogate-20261010"
REQ = Path(rf"E:\program\1project\video\shared\gpu-queue\requests\{REQ_ID}.json")

os.environ["PYTHONPATH"] = r"E:\program\1project\video\shared\runtime\envs\vo-gate\pylibs"
os.environ["MODELSCOPE_CACHE"] = r"E:\program\1project\video\shared\runtime\envs\vo-gate\modelscope"
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["PYTHONIOENCODING"] = "utf-8"
OUT_ROOT.mkdir(parents=True, exist_ok=True)
LOG.parent.mkdir(parents=True, exist_ok=True)

def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")

def log(msg: str):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def update_ckpt(**kw):
    d = {}
    if CKPT.exists():
        try: d = json.loads(CKPT.read_text(encoding="utf-8"))
        except Exception: d = {}
    d.update(kw); d["updated_at"] = now_iso()
    CKPT.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def main():
    # clear stale vogate locks only; do not hold lock during gate
    for p in (
        Path(r"E:\program\1project\video\shared\work\cache\gpu.lock"),
        Path(r"E:\program\1project\video\shared\runtime\comfy\cache\gpu.lock"),
    ):
        if p.exists():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                if str(d.get("owner", "")).startswith("zhumian-octopus-vogate"):
                    p.unlink(); log(f"cleared stale {p}")
            except Exception:
                pass
    if REQ.exists():
        d = json.loads(REQ.read_text(encoding="utf-8-sig"))
        d.update({"status": "running", "pid": os.getpid(), "started_at": now_iso(), "log_path": str(LOG)})
        REQ.write_text(json.dumps(d, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    log(f"START vo_gate out={OUT_ROOT} (no parent lock)")
    update_ckpt(stage="vo_gate", vogate_out=str(OUT_ROOT), vogate_pid=os.getpid())
    summary = []
    try:
        for name in ORDER:
            shotlist = SHOTLISTS / f"{name}-shotlist.json"
            jobs = JOBS / f"{name}.json"
            out = OUT_ROOT / name
            final = EP / "audio" / "vo-raw" / "seed7-final" / name
            out.mkdir(parents=True, exist_ok=True)
            final.mkdir(parents=True, exist_ok=True)
            cmd = [str(PY), str(GATE), "gate",
                   "--shotlist", str(shotlist), "--profile", str(PROFILE),
                   "--shots-dir", str(SHOTS), "--final-dir", str(final),
                   "--out-dir", str(out), "--base-jobs", str(jobs), "--remote", "local"]
            log(f"CHAPTER begin {name}")
            t0 = time.time()
            proc = subprocess.run(cmd, cwd=str(GATE.parent))
            dt = round(time.time() - t0, 1)
            summary.append({"chapter": name, "exit": proc.returncode, "elapsed_s": dt})
            log(f"CHAPTER end {name} exit={proc.returncode} elapsed_s={dt}")
            update_ckpt(last_vogate_chapter=name, vogate_summary=summary)
        (OUT_ROOT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        fails = [s for s in summary if s["exit"] != 0]
        log(f"DONE fails={len(fails)} detail={fails}")
        if REQ.exists():
            d = json.loads(REQ.read_text(encoding="utf-8-sig"))
            d.update({"status": "completed" if not fails else "failed", "finished_at": now_iso(), "fails": fails})
            REQ.write_text(json.dumps(d, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
        update_ckpt(stage="vo_gate_done" if not fails else "vo_gate_partial", next_action="process atempo 0.7304")
        return 0 if not fails else 1
    except Exception as e:
        log(f"FATAL {e}")
        return 2

if __name__ == "__main__":
    raise SystemExit(main())