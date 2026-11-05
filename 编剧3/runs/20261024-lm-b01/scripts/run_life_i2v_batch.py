# -*- coding: utf-8 -*-
"""life-manual (《下潜一万米》) batch LTX-2.3 I2V.

Adapted from the octopus batch runner (C:\\Users\\10060\\agent-tools\\run_octopus_i2v_batch.py).
Engine / workflow / model paths are IDENTICAL to the octopus run:
LTX-2.3 22B fp8 two-stage distilled I2V, 289 frames @24fps (~12s), 1280x704 native,
seed 42, manual sigmas unchanged; post: crop 1248x702 (crf10) -> lanczos 1920x1080 (crf14).

Differences from octopus (pipeline, not engine):
  - jobs come from runs/20261024-lm-b01/manifests/i2v_plan.json (40 shots, motion_prompt)
  - final deliverable: runs/20261024-lm-b01/i2v/<shot_id>.mp4 (1080p lanczos)
  - per-shot manifest: runs/20261024-lm-b01/manifests/i2v_manifest.json
  - idempotent (existing ok + on-disk mp4 -> skip); failed shots do not stop the batch
    (abort only when >5 shots have failed, per line red line)
  - negative prompt: octopus tokens minus octopus-creature-specific terms
  - holds ALL shared gpu.lock paths during the run (README main + legacy comfy + blender path)

Usage:
  python run_life_i2v_batch.py --only c1-s09,c6-s08   # pilot subset
  python run_life_i2v_batch.py                          # full batch (skips done)
"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, time
from datetime import datetime
from pathlib import Path
from PIL import Image

EP = Path(r"E:\program\1project\video\编剧3")
RUN = EP / "runs" / "20261024-lm-b01"
WORK = RUN / "i2v_work"          # in/out/temp/raw/crop/lanczos/logs/user dir for Comfy
FINAL = RUN / "i2v"              # deliverables <shot_id>.mp4
PLAN = RUN / "manifests" / "i2v_plan.json"
MF = RUN / "manifests" / "i2v_manifest.json"
HELPER = Path(r"E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\archive\i2v\select_v1\_work")
REQ = Path(r"E:\program\1project\video\shared\gpu-queue\requests\life-i2v-batch-20261024.json")
FF = shutil.which("ffmpeg") or r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"
FP = shutil.which("ffprobe") or str(Path(FF).with_name("ffprobe.exe"))

# 12s @ 24fps, 8n+1 legal for LTX (identical to octopus run)
FRAMES = 289
FPS = 24
WIDTH, HEIGHT = 1280, 704
SEED = 42
SHOT_TIMEOUT_S = 3600
MAX_FAILED = 5  # >5 failed shots -> abort batch and report (affine fallback exists per line)

# octopus negative minus octopus-creature tokens (deformed octopus / extra arms /
# missing arms / tentacle tangle / mutated cephalopod / neon octopus / armor removed)
NEGATIVE = (
    "overexposed, oversaturated, static freeze, fast camera movement, camera shake, scene change, cut, "
    "blurry details, subtitles, text, watermark, logo, worst quality, low quality, jpeg artifacts, "
    "warping, melting objects, humanoid face, gore, swarm, "
    "flicker, morphing, mutant"
)

sys.path.insert(0, str(HELPER))
import i2v_cmp as m  # noqa: E402

# --- shared GPU locks: README main + legacy comfy guard + blender_backend path ---
LOCK_PATHS = [
    Path(r"E:\program\1project\video\shared\work\cache\gpu.lock"),
    Path(r"E:\program\1project\video\shared\runtime\comfy\cache\gpu.lock"),
    Path(r"E:\program\1project\video\work\cache\gpu.lock"),
]


def log(msg):
    s = time.strftime("[%m-%d %H:%M:%S] ") + msg
    print(s, flush=True)
    with open(WORK / "logs" / "i2v.log", "a", encoding="utf-8") as f:
        f.write(s + "\n")


def ensure_dirs():
    for d in ("in", "out", "temp", "logs", "raw", "crop", "lanczos", "user-portable"):
        (WORK / d).mkdir(parents=True, exist_ok=True)
    FINAL.mkdir(parents=True, exist_ok=True)


def write_req(**kw):
    if REQ.exists():
        d = json.loads(REQ.read_text(encoding="utf-8"))
    else:
        d = {
            "id": "life-i2v-batch-20261024",
            "owner_thread": "助眠解说",
            "line": "助眠解说",
            "submitted_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "priority": 90,
            "status": "queued",
            "task": "《下潜一万米》(life-manual) 36 镜批量 LTX-2.3 I2V ~12s/镜(先 2 镜试点 c1-s09/c6-s08,合格后全量)",
            "command_or_workflow_path": str(Path(__file__).resolve()),
            "working_directory": str(RUN),
            "output_directory": str(FINAL),
            "estimated_minutes": 300,
            "estimated_vram_mb": 15000,
            "dependencies": [],
            "authorization": "2026-10-07 用户授权助眠线自管 GPU;2026-10-19 用户授权自主推进至成片;2026-10-20 静帧 134/134 目检通过",
            "pid": None,
            "log_path": str(WORK / "logs" / "i2v.log"),
            "plan_manifest": str(PLAN),
            "jobs": 36,
            "engine": "LTX-2.3 distilled I2V(与章鱼集 20261010 批次同工作流/参数)",
            "fallback": "失败镜回退 P1 affine 运镜并记 manifest(章鱼集 fallback 流程);≤5 失败属正常",
        }
    d.update(kw)
    REQ.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return d


def pid_alive(pid):
    """字节级判断(中文 Windows 控制台输出 GBK,text=True 解码会崩或误报)。"""
    try:
        out = subprocess.run(["tasklist", "/FI", "PID eq %d" % int(pid), "/NH"],
                             capture_output=True, timeout=20).stdout
        return str(int(pid)).encode() in out
    except Exception:
        return True


def _run_text(cmd, timeout=60):
    """Run command, decode bytes with errors=replace (PS output may be GBK, not UTF-8)."""
    try:
        return subprocess.run(cmd, capture_output=True, timeout=timeout).stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def tts_procs():
    ps = ("Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
          "% { \"$($_.ProcessId)`t$($_.CommandLine)\" }")
    out = _run_text(["powershell", "-NoProfile", "-Command", ps])
    keys = (r"shared\runtime\engines\tts", "voxcpm", "index-tts", "gen_voice", "gen_shots", "indextts")
    # 排除自身与子进程(本脚本可能用 voxcpm venv 解释器启动,命令行含关键字会被误判)
    mine = {os.getpid()}
    return [l for l in out.splitlines()
            if l.split("\t", 1)[0].strip().isdigit() and int(l.split("\t", 1)[0]) not in mine
            and any(k in l.lower() for k in keys)]


def other_gpu_python():
    out = _run_text(["nvidia-smi", "--query-compute-apps=pid,process_name", "--format=csv,noheader"], timeout=20)
    ours = {m.PROC.pid} if m.PROC else set()
    res = []
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if not (parts and parts[0].isdigit() and "python" in line.lower()):
            continue
        if int(parts[0]) in ours:
            continue
        res.append(line.strip())
    return res


def acquire_all_locks(timeout_s=86400):
    """Hold every shared gpu.lock path; poll at >=15min intervals per queue protocol."""
    deadline = time.time() + timeout_s
    taken: list[Path] = []
    while time.time() < deadline:
        busy = []
        for p in LOCK_PATHS:
            if not p.exists():
                continue
            try:
                holder = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                busy.append((p, "unreadable")); continue
            hpid = int(holder.get("pid") or 0)
            if hpid == os.getpid():
                continue
            if hpid and not pid_alive(hpid):
                log(f"stale gpu.lock at {p} (pid {hpid} dead) -> taking over")
                try: p.unlink()
                except OSError: pass
                continue
            busy.append((p, holder))
        t = tts_procs(); g = other_gpu_python()
        if not busy and not t and not g:
            for p in LOCK_PATHS:
                p.parent.mkdir(parents=True, exist_ok=True)
                fd = os.open(str(p), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump({"owner": "life-i2v-batch-20261024", "pid": os.getpid(),
                               "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
                               "log": str(WORK / "logs" / "i2v.log")}, fh)
                taken.append(p)
            log("gpu.lock acquired: %s" % [str(p) for p in taken])
            return taken
        log("WAIT gpu busy (poll 15min): locks=%s tts=%s cuda=%s" % (
            [(str(p), h) for p, h in busy], [x[:120] for x in t], g))
        release_all_locks(taken)
        time.sleep(900)
    raise TimeoutError("gpu locks not free within timeout")


def release_all_locks(taken):
    for p in taken:
        try:
            if p.exists():
                d = json.loads(p.read_text(encoding="utf-8"))
                if int(d.get("pid") or 0) == os.getpid():
                    p.unlink()
        except Exception as e:
            log(f"lock release error {p}: {e}")
    if taken:
        log("gpu.lock released")


def load_jobs():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    jobs = []
    for s in plan["shots"]:
        sid = s["id"]
        jpg = (EP / s["source_still"]).resolve()
        if not jpg.exists():
            raise FileNotFoundError(jpg)
        png = WORK / "in" / f"{sid}.png"
        if not png.exists():
            with Image.open(jpg) as im:
                im.convert("RGB").save(png)
        jobs.append({"shot": sid, "section": s.get("section"),
                     "strategy": s.get("strategy"), "source_still": str(jpg),
                     "i2v_input": str(png), "i2v_prompt": s["motion_prompt"],
                     "tail_extension_seconds": s.get("tail_extension_seconds")})
    return jobs


def probe(path):
    out = subprocess.run([FP, "-v", "error", "-show_entries",
                          "stream=width,height,nb_frames,avg_frame_rate:format=duration",
                          "-of", "json", str(path)], capture_output=True)
    j = json.loads(out.stdout.decode("utf-8", "replace"))  # 手动解码,stderr 的 GBK 路径不再触发解码崩溃
    st = j["streams"][0]
    dur = float(j["format"]["duration"])
    return {"w": st.get("width"), "h": st.get("height"),
            "frames": int(st.get("nb_frames") or 0), "duration_s": round(dur, 2),
            "fps": st.get("avg_frame_rate")}


def post(raw: Path, shot: str):
    crop = WORK / "crop" / f"{shot}-ltx-1248x702.mp4"
    base = WORK / "lanczos" / f"{shot}-ltx-lanczos-1920x1080.mp4"
    if not crop.exists():
        subprocess.run([FF, "-v", "error", "-y", "-i", str(raw), "-an", "-vf", "crop=1248:702,setsar=1",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "10", "-pix_fmt", "yuv420p", str(crop)], check=True)
    if not base.exists():
        subprocess.run([FF, "-v", "error", "-y", "-i", str(crop), "-an", "-vf", "scale=1920:1080:flags=lanczos,setsar=1",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-pix_fmt", "yuv420p", str(base)], check=True)
    final = FINAL / f"{shot}.mp4"
    if not final.exists():
        shutil.copy2(base, final)
    for p in (raw, crop, base, final):
        subprocess.run([FF, "-v", "error", "-i", str(p), "-f", "null", "-"], check=True)
    return crop, base, final


def run_shot(job) -> dict:
    shot = job["shot"]
    r = {
        "shot": shot, "section": job.get("section"), "strategy": job.get("strategy"),
        "engine": "LTX-2.3 distilled I2V (octopus-20261010 workflow, params unchanged)",
        "w": WIDTH, "h": HEIGHT, "frames": FRAMES, "fps": FPS, "seed": SEED,
        "input": job["i2v_input"], "source_still": job["source_still"],
        "prompt": job["i2v_prompt"], "negative": NEGATIVE,
        "tail_extension_seconds": job.get("tail_extension_seconds"),
        "started": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    t0 = time.monotonic()
    try:
        if m.PROC is None or m.PROC.poll() is not None:
            log("comfy not running -> restart")
            m.PROC = None
            m.start_comfy("portable", "life_i2v")
        m.IMAGE, m.PROMPT = f"{shot}.png", job["i2v_prompt"]
        g = m.g_ltx(WIDTH, HEIGHT, FRAMES, 11, "life-i2v/" + shot)
        g["19"]["inputs"]["noise_seed"] = SEED
        g["30"]["inputs"]["noise_seed"] = SEED
        g["5"]["inputs"]["text"] = NEGATIVE
        (WORK / "logs" / f"{shot}-graph.json").write_text(json.dumps(g, ensure_ascii=False, indent=1), encoding="utf-8")
        pid = json.loads(m.http("/prompt", {"prompt": g, "client_id": shot}))["prompt_id"]
        log(f"{shot} queued {pid} frames={FRAMES}")
        entry = None
        while True:
            time.sleep(5)
            if m.PROC.poll() is not None:
                raise RuntimeError("ComfyUI exited")
            h = m.jget("/history/" + pid)
            if pid in h:
                entry = h[pid]
                break
            if time.monotonic() - t0 > SHOT_TIMEOUT_S:
                m.http("/interrupt", {})
                raise TimeoutError(shot)
        if entry.get("status", {}).get("status_str") != "success":
            raise RuntimeError(str(entry.get("status"))[:500])
        out_dir = WORK / "out" / "life-i2v"
        raw0 = max(out_dir.glob(shot + "_*.mp4"), key=lambda p: p.stat().st_mtime)
        raw = WORK / "raw" / f"{shot}-ltx-raw-{WIDTH}x{HEIGHT}.mp4"
        shutil.copy2(raw0, raw)
        crop, base, final = post(raw, shot)
        meta = probe(final)
        r.update(ok=True, raw=str(raw), crop=str(crop), lanczos=str(base), mp4=str(final),
                 gen_s=round(time.monotonic() - t0, 1), decode_ok=True,
                 out_w=meta["w"], out_h=meta["h"], out_frames=meta["frames"],
                 out_duration_s=meta["duration_s"], visual_qa="pending")
        try:
            m.http("/free", {"unload_models": False, "free_memory": True})
        except Exception:
            pass
    except Exception as e:
        r.update(ok=False, error=repr(e)[:800], gen_s=round(time.monotonic() - t0, 1))
        log(f"{shot} FAILED {e!r}")
    r["ended"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return r


def save_manifest(results):
    MF.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated shot ids (pilot)")
    ap.add_argument("--max-shots", type=int, default=0,
                    help="process at most N pending shots this invocation (chunked mode; 0 = all)")
    args = ap.parse_args()
    ensure_dirs()
    shutil.copy2(HELPER / "extra_model_paths_diffusion.yaml", WORK / "extra_model_paths_diffusion.yaml")
    m.SCR = str(WORK)
    m.LOGF = str(WORK / "logs" / "runner.log")
    jobs = load_jobs()
    if args.only:
        want = [x.strip() for x in args.only.split(",") if x.strip()]
        jobs = [j for j in jobs if j["shot"] in want]
        if len(jobs) != len(want):
            raise SystemExit("unknown shot id in --only: %s" % want)
        write_req(task_mode="pilot", pilot=want)
    results = json.loads(MF.read_text(encoding="utf-8")) if MF.exists() else []
    done = {r["shot"] for r in results
            if r.get("ok") and (FINAL / (r["shot"] + ".mp4")).exists()}
    todo = [j for j in jobs if j["shot"] not in done]
    if args.max_shots and len(todo) > args.max_shots:
        todo = todo[:args.max_shots]
    log(f"batch start: jobs={len(jobs)} done={len(done & {j['shot'] for j in jobs})} todo={len(todo)}"
        + (f" (chunk max {args.max_shots})" if args.max_shots else ""))
    write_req(status="running", pid=os.getpid(),
              started_at=datetime.now().astimezone().isoformat(timespec="seconds"))
    locks = acquire_all_locks()
    failed_total = sum(1 for r in results if not r.get("ok"))
    aborted = False
    try:
        m.start_comfy("portable", "life_i2v")
        attempt = {}
        for job in todo:
            shot = job["shot"]
            attempt[shot] = attempt.get(shot, 0) + 1
            r = run_shot(job)
            results = [x for x in results if x["shot"] != shot] + [r]
            save_manifest(results)
            log(f"{shot} {'ok' if r.get('ok') else 'FAILED'} gen_s={r.get('gen_s')}")
            if r.get("ok"):
                done.add(shot)
            else:
                failed_total += 1
                if failed_total > MAX_FAILED and attempt[shot] >= 1 and len(todo) > 2:
                    # one same-params retry pass first; hard-abort only if >MAX_FAILED after retry
                    if attempt[shot] >= 2:
                        log(f"ABORT: {failed_total} shots failed (> {MAX_FAILED}) after retry -> stop batch")
                        aborted = True
                        break
        if not aborted:
            # single retry pass for shots failed in this process (same params, engine untouched)
            retry = [j for j in todo if attempt.get(j["shot"], 0) == 1 and
                     not any(r["shot"] == j["shot"] and r.get("ok") for r in results)]
            if retry:
                log(f"retry pass: {len(retry)} shot(s) at identical params")
                for job in retry:
                    shot = job["shot"]
                    attempt[shot] += 1
                    r = run_shot(job)
                    if r.get("ok"):
                        failed_total -= 1
                    results = [x for x in results if x["shot"] != shot] + [r]
                    save_manifest(results)
                    log(f"{shot} retry {'ok' if r.get('ok') else 'FAILED'}")
                    if not r.get("ok") and failed_total > MAX_FAILED:
                        log(f"ABORT after retry: {failed_total} failed (> {MAX_FAILED})")
                        aborted = True
                        break
    finally:
        try:
            m.stop_comfy()
        except Exception:
            pass
        release_all_locks(locks)
    bad = [r["shot"] for r in results if not r.get("ok")]
    ok = sum(1 for r in results if r.get("ok"))
    total_gen = round(sum(r.get("gen_s") or 0 for r in results) / 60.0, 1)
    remaining = [j["shot"] for j in load_jobs()
                 if j["shot"] not in {r["shot"] for r in results if r.get("ok")}
                 or not (FINAL / (j["shot"] + ".mp4")).exists()]
    if aborted:
        st = "failed"
    elif bad:
        st = "failed"
    elif remaining:
        st = "queued"  # chunk finished, more shots remain; next invocation resumes
    else:
        st = "completed"
    write_req(status=st,
              finished_at=datetime.now().astimezone().isoformat(timespec="seconds"),
              ok=ok, failed=bad, aborted=aborted, total_gpu_minutes=total_gen,
              remaining=remaining, pid=None if st == "queued" else os.getpid())
    log(f"DONE ok={ok} failed={bad} aborted={aborted} remaining={len(remaining)} total_gen_min={total_gen}")
    return 0 if (not bad and not aborted) else 1


if __name__ == "__main__":
    raise SystemExit(main())
