# -*- coding: utf-8 -*-
"""Octopus TTS: intro+bridge+ch01..ch10 under GPU lock (sleep-aid self-managed)."""
from __future__ import annotations
import json, os, subprocess, sys, time
from datetime import datetime
from pathlib import Path

REQ_ID = "zhumian-octopus-tts-20261010"
REQ = Path(rf"E:\program\1project\video\shared\gpu-queue\requests\{REQ_ID}.json")
LOCK = Path(r"E:\program\1project\video\shared\work\cache\gpu.lock")
LEGACY = Path(r"E:\program\1project\video\shared\runtime\comfy\cache\gpu.lock")
PY = Path(r"E:\program\1project\video\shared\runtime\engines\tts\voxcpm\.venv\Scripts\python.exe")
GEN = Path(r"E:\program\1project\video\shared\runtime\engines\tts\voxcpm\gen_shots.py")
EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\you-are-an-octopus")
JOBS = EP / "audio" / "jobs"
OUT = EP / "audio" / "vo-raw" / "seed7"
RUN = EP / "runs" / "20261010-octopus-b01"
LOG = RUN / "logs" / "tts.log"
CKPT = RUN / "CHECKPOINT.json"
STATUS = RUN / "STATUS.md"
STATE_APPEND = Path(r"E:\program\1project\video\shared\gpu-queue\STATE.md")
ORDER = [
    "intro.json", "bridge.json",
    "ch01.json", "ch02.json", "ch03.json", "ch04.json", "ch05.json",
    "ch06.json", "ch07.json", "ch08.json", "ch09.json", "ch10.json",
]

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["MODELSCOPE_CACHE"] = r"E:\program\1project\video\shared\runtime\engines\tts\modelscope-cache"
os.environ["HF_HOME"] = r"E:\program\1project\video\shared\runtime\engines\tts\hf-cache"

LOG.parent.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def log(msg: str):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def write_req(**kw):
    d = json.loads(REQ.read_text(encoding="utf-8-sig")) if REQ.exists() else {}
    d.update(kw)
    REQ.write_text(json.dumps(d, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    return d


def update_ckpt(**kw):
    d = {}
    if CKPT.exists():
        try:
            d = json.loads(CKPT.read_text(encoding="utf-8"))
        except Exception:
            d = {}
    d.update(kw)
    d["updated_at"] = now_iso()
    CKPT.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_status(body: str):
    STATUS.write_text(body.strip() + "\n", encoding="utf-8")


def acquire():
    if LOCK.exists() or LEGACY.exists():
        for p in (LOCK, LEGACY):
            if not p.exists():
                continue
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                pid = d.get("pid")
                if pid:
                    r = subprocess.run(
                        ["powershell", "-NoProfile", "-Command",
                         f"Get-Process -Id {pid} -ErrorAction SilentlyContinue"],
                        capture_output=True,
                    )
                    if r.returncode == 0 and r.stdout.strip():
                        raise RuntimeError(f"GPU lock held by {d.get('owner')} pid {pid}")
                p.unlink(missing_ok=True)
            except RuntimeError:
                raise
            except Exception:
                p.unlink(missing_ok=True)
    payload = {
        "owner": REQ_ID,
        "line": "助眠解说",
        "pid": os.getpid(),
        "started": now_iso(),
        "task": "octopus VoxCPM2 intro+bridge+ch01-ch10 VO",
    }
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
                if d.get("owner") == REQ_ID and d.get("pid") == os.getpid():
                    p.unlink()
                    log(f"released {p}")
                else:
                    log(f"skip release {p} owner={d.get('owner')} pid={d.get('pid')}")
        except Exception as e:
            log(f"release error {p}: {e}")


def count_wavs():
    return len(list(OUT.glob("*.wav")))


def expected_ids(job_path: Path):
    d = json.loads(job_path.read_text(encoding="utf-8"))
    return [s["id"] for s in d.get("shots", [])]


def missing_ids(job_path: Path):
    miss = []
    for sid in expected_ids(job_path):
        if not (OUT / f"{sid}.wav").exists():
            miss.append(sid)
    return miss


def main():
    log("START octopus TTS runner")
    lock = acquire()
    log(f"acquired lock pid={lock['pid']}")
    write_req(
        status="running",
        pid=os.getpid(),
        log_path=str(LOG),
        started_at=now_iso(),
    )
    update_ckpt(
        stage="tts",
        in_progress=["tts_all_chapters"],
        next_action="run intro→ch10 under lock; skip existing wavs via missing-id resume",
        tts_pid=os.getpid(),
        tts_req=REQ_ID,
    )
    failed = None
    done_chapters = []
    try:
        for name in ORDER:
            job = JOBS / name
            if not job.exists():
                raise FileNotFoundError(str(job))
            miss = missing_ids(job)
            if not miss:
                log(f"CHAPTER skip {name} all {len(expected_ids(job))} wavs present")
                done_chapters.append(name)
                continue
            log(f"CHAPTER begin {name} missing={len(miss)}/{len(expected_ids(job))} wavs_before={count_wavs()}")
            t0 = time.time()
            # gen_shots.py: second arg = missing ids to avoid re-running whole chapter
            cmd = [str(PY), str(GEN), str(job)]
            if len(miss) < len(expected_ids(job)):
                cmd.append(",".join(miss))
            proc = subprocess.run(cmd, cwd=str(GEN.parent), capture_output=False)
            dt = round(time.time() - t0, 1)
            still = missing_ids(job)
            log(f"CHAPTER end {name} exit={proc.returncode} elapsed_s={dt} still_missing={len(still)} wavs_after={count_wavs()}")
            if proc.returncode != 0 or still:
                failed = f"{name} exit={proc.returncode} still_missing={len(still)}"
                break
            done_chapters.append(name)
            update_ckpt(
                completed=[f"tts:{c}" for c in done_chapters],
                tts_wav_count=count_wavs(),
                last_chapter=name,
            )
            update_status(
                f"""# STATUS 你是一只章鱼 — 20261010-octopus-b01

- 时间：{now_iso()}
- 阶段：TTS 进行中（已完成 {', '.join(done_chapters)}）
- wav 数：{count_wavs()} / 280
- 日志：{LOG}
- 下一：继续后续章节 TTS → 章完即 vo_gate
"""
            )
        if failed:
            write_req(status="failed", finished_at=now_iso(), error=failed)
            update_ckpt(stage="tts_failed", blockers=[failed], next_action="fix failed chapter")
            log(f"FAILED {failed}")
            return 1
        write_req(
            status="completed",
            finished_at=now_iso(),
            wav_count=count_wavs(),
            note="raw TTS completed; vo_gate + atempo next",
        )
        with STATE_APPEND.open("a", encoding="utf-8") as f:
            f.write(
                f"\n- {datetime.now().strftime('%Y-%m-%d %H:%M')}（+08:00）：{REQ_ID} completed"
                f"（助眠解说自管，raw wav={count_wavs()}）。\n"
            )
        update_ckpt(
            stage="tts_done",
            completed=[f"tts:{c}" for c in done_chapters],
            in_progress=["vo_gate"],
            next_action="run vo_gate then atempo=0.7304",
            tts_wav_count=count_wavs(),
        )
        update_status(
            f"""# STATUS 你是一只章鱼 — 20261010-octopus-b01

- 时间：{now_iso()}
- 阶段：TTS raw 完成 wav={count_wavs()}
- 下一：vo_gate → atempo 0.7304 → 时间轴；并行静帧 API
"""
        )
        log(f"COMPLETED wavs={count_wavs()}")
        return 0
    finally:
        release()


if __name__ == "__main__":
    raise SystemExit(main())