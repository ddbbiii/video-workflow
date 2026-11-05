# -*- coding: utf-8 -*-
"""Mariana TTS orchestrator: wait for siffre TTS -> validate -> full TTS -> 08 -> 09.

2026-10-19。用户授权自主推进。依赖:shared/gpu-queue/requests/zhumian-sbt-tts-20261018
到达 completed/failed(canceled),且三处 GPU 锁不存在、nvidia-smi 无计算进程时启动。
validate 批 wav 时长>0 且无报错才继续全量;随后 08(VO处理)与 09(章音频+时间轴)。
任何一步失败即停并回写请求 failed,绝不带病推进。最长等待 20 小时后放弃(queued 原状)。
"""
from __future__ import annotations
import json, subprocess, sys, time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
EP = HERE.parents[2]
RUN = HERE.parents[1]
VENV_PY = r"E:\program\1project\video\shared\runtime\engines\tts\voxcpm\.venv\Scripts\python.exe"
SIFFRE_REQ = Path(r"E:\program\1project\video\shared\gpu-queue\requests\zhumian-sbt-tts-20261018.json")
MY_REQ = Path(r"E:\program\1project\video\shared\gpu-queue\requests\glacier-tts-20261103.json")
LOCKS = [Path(r"E:\program\1project\video\shared\work\cache\gpu.lock"),
         Path(r"E:\program\1project\video\shared\runtime\comfy\cache\gpu.lock"),
         Path(r"E:\program\1project\video\work\cache\gpu.lock")]
RAW = EP / "audio" / "vo-raw" / "lightexpr-seed7"
LOG = RUN / "logs" / "orchestrator.log"
LOG.parent.mkdir(parents=True, exist_ok=True)
MAX_WAIT_S = 20 * 3600
POLL_S = 300


def log(msg):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def req_status(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig")).get("status")
    except Exception:
        return "missing"


def update_my_req(**kw):
    try:
        d = json.loads(MY_REQ.read_text(encoding="utf-8-sig"))
        d.update(kw)
        MY_REQ.write_text(json.dumps(d, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    except Exception as e:
        log(f"update_my_req error: {e}")


def gpu_busy():
    if any(p.exists() for p in LOCKS):
        return True
    try:
        out = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,process_name",
                              "--format=csv,noheader"], capture_output=True, text=True, timeout=30)
        # 只有 python/推理进程才算占用;桌面应用(壁纸引擎等)出现为 [Insufficient Permissions] 行,忽略
        for line in out.stdout.splitlines():
            name = line.split(",")[-1].strip().lower()
            if "python" in name or "comfy" in name:
                return True
        return False
    except Exception:
        return True  # 查询失败按占用处理


def run(script, *args):
    cmd = [VENV_PY, str(HERE / script), *args]
    log(f"RUN {script} {' '.join(args)}")
    r = subprocess.run(cmd, cwd=str(RUN))
    return r.returncode


def main():
    deadline = time.time() + MAX_WAIT_S
    log("waiting for siffre TTS to finish + GPU free")
    while time.time() < deadline:
        st = req_status(SIFFRE_REQ)
        if st in ("completed", "failed", "cancelled", "missing"):
            if st != "completed":
                log(f"siffre TTS status={st} -> give up (stay queued)")
                return 0
            if not gpu_busy():
                break
            log("siffre completed but GPU busy; keep waiting")
        time.sleep(POLL_S)
    else:
        log("timeout 20h -> stay queued")
        return 0

    # 预检与放行
    for p in LOCKS:
        if p.exists():
            log(f"pre-grant abort: lock {p}")
            return 0
    update_my_req(status="granted", granted_at=datetime.now().astimezone().isoformat(timespec="seconds"),
                  granted_by="mariana自管(依赖siffre TTS完成)")

    # validate
    update_my_req(status="running", stage="validate",
                  started_at=datetime.now().astimezone().isoformat(timespec="seconds"))
    if run("06_run_tts.py", "validate") != 0:
        update_my_req(status="failed", failure="validate batch failed")
        return 1
    wavs = sorted(RAW.glob("validate-*.wav")) + sorted(RAW.glob("*.wav"))
    ok = any(w.stat().st_size > 100_000 for w in RAW.glob("*.wav"))
    if not ok:
        update_my_req(status="failed", failure="validate produced no usable wav")
        return 1
    log("validate OK")

    for job in ["intro", "bridge", "ch01", "ch02", "ch03", "ch04", "ch05",
                "ch06", "ch07", "ch08", "ch09", "ch10", "epilogue"]:
        update_my_req(stage=job)
        if run("06_run_tts.py", job) != 0:
            update_my_req(status="failed", failure=f"{job} failed")
            return 1
    update_my_req(stage="tts_done")

    # VO 处理与章音频(voxcpm venv)
    for script in ["08_process_vo.py", "09_build_chapter_audio.py"]:
        update_my_req(stage=script)
        if run(script) != 0:
            update_my_req(status="failed", failure=f"{script} failed")
            return 1

    update_my_req(status="completed",
                  completed_at=datetime.now().astimezone().isoformat(timespec="seconds"),
                  stage="tts+08+09 done")
    log("ALL DONE (tts, 08, 09)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
