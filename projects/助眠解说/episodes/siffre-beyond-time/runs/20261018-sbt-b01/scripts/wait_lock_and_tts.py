# -*- coding: utf-8 -*-
"""等锁守望:轮询三处共享 gpu.lock,全部空闲(不存在或持有进程已死)时
立即执行 06_run_tts.py intro intro-p06-u01(占位段补配)。

背景:mariana-i2v-batch-20261020 持锁跑 34 个 i2v 作业(约数小时),本任务
GPU 需求仅 1 个 TTS 单元。守望着锁即走,不删他人锁、不并行抢卡。
产物:logs/tts_lock_watch.log 逐行记录;logs/TTS_P06_DONE.json 完成标记。
"""
import json, subprocess, sys, time
from datetime import datetime
from pathlib import Path

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\siffre-beyond-time")
RUN = EP / "runs" / "20261018-sbt-b01"
LOCKS = [
    Path(r"E:\program\1project\video\shared\work\cache\gpu.lock"),
    Path(r"E:\program\1project\video\shared\runtime\comfy\cache\gpu.lock"),
    Path(r"E:\program\1project\video\work\cache\gpu.lock"),
]
LOG = RUN / "logs" / "tts_lock_watch.log"
DONE = RUN / "logs" / "TTS_P06_DONE.json"
POLL_S = 60
DEADLINE_S = 8 * 3600

def log(msg):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def pid_alive(pid):
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        f"Get-Process -Id {pid} -ErrorAction SilentlyContinue"],
                       capture_output=True)
    return r.returncode == 0 and r.stdout.strip()

def lock_busy(p):
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        pid = d.get("pid")
        if pid and pid_alive(pid):
            return d.get("owner")
    except Exception:
        pass
    return None  # 死锁/坏锁视为空闲(06 自带同样的陈锁清理)

def main():
    t0 = time.time()
    log("watcher start: waiting for all gpu locks free")
    while True:
        holders = {str(p): lock_busy(p) for p in LOCKS}
        busy = {k: v for k, v in holders.items() if v}
        if not busy:
            log("all locks free -> run TTS now")
            break
        if time.time() - t0 > DEADLINE_S:
            log("DEADLINE exceeded, give up")
            DONE.write_text(json.dumps({"ok": False, "error": "deadline"}), encoding="utf-8")
            return 1
        log("busy: " + "; ".join(f"{k}={v}" for k, v in busy.items()))
        time.sleep(POLL_S)
    r = subprocess.run([sys.executable, str(RUN / "scripts" / "06_run_tts.py"),
                        "intro", "intro-p06-u01"],
                       cwd=str(RUN / "scripts"), capture_output=True, text=True)
    log(f"06_run_tts exit={r.returncode}")
    if r.stdout:
        log("stdout tail: " + r.stdout[-1500:])
    if r.stderr:
        log("stderr tail: " + r.stderr[-800:])
    wav = EP / "audio" / "vo-raw" / "lightexpr-seed7" / "intro-p06-u01.wav"
    DONE.write_text(json.dumps({"ok": r.returncode == 0 and wav.exists(),
                                "exit": r.returncode, "wav": str(wav),
                                "wav_exists": wav.exists(),
                                "finished_at": datetime.now().isoformat(timespec="seconds")},
                               ensure_ascii=False), encoding="utf-8")
    return r.returncode

if __name__ == "__main__":
    raise SystemExit(main())
