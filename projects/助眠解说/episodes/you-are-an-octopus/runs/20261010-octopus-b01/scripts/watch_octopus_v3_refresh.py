# -*- coding: utf-8 -*-
"""Watch octopus V3 I2V batch; on ~78 ok, refresh media-map / shot clips / chapters / delivery.
No TTS/stills redo. Never stretch I2V; short clips fall back to affine via 03_prepare.
"""
from __future__ import annotations
import json, os, re, shutil, subprocess, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\you-are-an-octopus")
RUN = EP / "runs" / "20261010-octopus-b01"
BATCH = EP / "runs" / "20261010-i2v-batch-b01"
SCRIPTS = RUN / "scripts"
PYTHON = Path(r"E:\program\language\python\Python-3.11.0\python.exe")
FFPROBE = Path(r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffprobe.exe")
GPU_LOCK = Path(r"E:\program\1project\video\work\cache\gpu.lock")
BATCH_PID_HINT = 44456
TARGET_OK = 78
FRAMES_OK = 287
POLL_S = 180
TZ = timezone(timedelta(hours=8))
LOG = RUN / "logs" / "v3_watch_refresh.log"


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def log(msg: str) -> None:
    line = f"[{datetime.now(TZ).strftime('%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def atomic_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def update_checkpoint(**kw):
    ck = RUN / "CHECKPOINT.json"
    d = load_json(ck) if ck.exists() else {}
    d.update(kw)
    d["updated_at"] = now_iso()
    atomic_json(ck, d)


def probe(path: Path) -> float:
    r = subprocess.run(
        [str(FFPROBE), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())


def pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"if (Get-Process -Id {int(pid)} -ErrorAction SilentlyContinue) {{ '1' }} else {{ '0' }}"],
            capture_output=True, text=True, timeout=30,
        )
        return (r.stdout or "").strip() == "1"
    except Exception:
        return False


def find_batch_pid() -> int | None:
    if pid_alive(BATCH_PID_HINT):
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"(Get-CimInstance Win32_Process -Filter 'ProcessId={BATCH_PID_HINT}').CommandLine"],
                capture_output=True, text=True, timeout=30,
            )
            if "run_octopus_i2v_batch" in (r.stdout or ""):
                return BATCH_PID_HINT
        except Exception:
            return BATCH_PID_HINT
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'run_octopus_i2v_batch' } | Select-Object -ExpandProperty ProcessId"],
            capture_output=True, text=True, timeout=60,
        )
        for line in (r.stdout or "").splitlines():
            line = line.strip()
            if line.isdigit():
                cand = int(line)
                if pid_alive(cand):
                    return cand
    except Exception as e:
        log(f"pid scan failed: {e!r}")
    return None


def clear_stale_gpu_lock() -> bool:
    if not GPU_LOCK.exists():
        return False
    try:
        data = json.loads(GPU_LOCK.read_text(encoding="utf-8"))
        pid = int(data.get("pid") or 0)
    except Exception:
        pid = 0
    if pid and pid_alive(pid):
        return False
    GPU_LOCK.unlink(missing_ok=True)
    log(f"cleared stale GPU lock (owner pid={pid} dead)")
    return True


def manifest_stats():
    mf = BATCH / "i2v_manifest.json"
    if not mf.exists():
        return {"rows": 0, "ok_any": 0, "ok_ge287": 0, "fail": 0, "ok_shots": [], "fail_shots": []}
    rows = load_json(mf)
    ok_any = [r for r in rows if r.get("ok")]
    ok287 = [r for r in rows if r.get("ok") and int(r.get("frames") or 0) >= FRAMES_OK]
    fail = [r for r in rows if not r.get("ok")]
    return {
        "rows": len(rows),
        "ok_any": len(ok_any),
        "ok_ge287": len(ok287),
        "fail": len(fail),
        "ok_shots": [r["shot"] for r in ok287],
        "fail_shots": [r["shot"] for r in fail],
        "latest": sorted(ok_any, key=lambda r: r.get("ended") or "")[-1] if ok_any else None,
    }


def write_status(st: dict, note: str) -> None:
    pid = st.get("batch_pid")
    alive = st.get("batch_alive")
    ok = st.get("ok_ge287", 0)
    text = (
        f"# STATUS 你是一只章鱼 — 20261010-octopus-b01\n\n"
        f"- 时间：{now_iso()}\n"
        f"- **成片（affine-primary）可交**：clean + sub 均非空\n"
        f"  - clean: delivery/你是一只章鱼_1080p_clean.mp4\n"
        f"  - sub: delivery/你是一只章鱼_1080p_sub.mp4\n"
        f"- **V3 批量 I2V（12s/289帧）**：ok≥{FRAMES_OK} = {ok}/{TARGET_OK}；"
        f"pid={pid} alive={alive}\n"
        f"- {note}\n"
        f"- 规则：不拉伸 I2V；不够长回退 affine；不重做 TTS/静帧\n"
        f"- 监控脚本：scripts/watch_octopus_v3_refresh.py（满额后自动 refresh）\n"
    )
    (RUN / "STATUS.md").write_text(text, encoding="utf-8")


def restart_batch_if_needed(st: dict) -> int | None:
    if st["ok_ge287"] >= TARGET_OK and st["fail"] == 0:
        return st.get("batch_pid")
    pid = find_batch_pid()
    if pid:
        return pid
    if st["ok_ge287"] < TARGET_OK:
        clear_stale_gpu_lock()
        # ensure comfy port free if orphaned
        try:
            import urllib.request
            urllib.request.urlopen("http://127.0.0.1:8191/system_stats", timeout=2)
            log("port 8191 still up with no batch; killing orphan comfy")
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'ComfyUI\\\\main.py' -and $_.CommandLine -match '8191' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"],
                capture_output=True, text=True,
            )
            time.sleep(3)
        except Exception:
            pass
        log(f"batch dead at ok_ge287={st['ok_ge287']}; restarting resume from manifest")
        script = SCRIPTS / "run_octopus_i2v_batch.py"
        agent = Path(r"C:\Users\10060\agent-tools\run_octopus_i2v_batch.py")
        shutil.copy2(script, agent)
        out_log = RUN / "logs" / "i2v_batch.out.log"
        err_log = RUN / "logs" / "i2v_batch.err.log"
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        DETACHED_PROCESS = 0x00000008
        with out_log.open("a", encoding="utf-8") as out, err_log.open("a", encoding="utf-8") as err:
            proc = subprocess.Popen(
                [str(PYTHON), str(agent)],
                cwd=str(BATCH),
                stdout=out,
                stderr=err,
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                close_fds=True,
            )
        log(f"restarted batch pid={proc.pid}")
        global BATCH_PID_HINT
        BATCH_PID_HINT = proc.pid
        time.sleep(5)
        return proc.pid
    return None


def prefer_long_i2v_patch() -> None:
    for rel in ("02_build_media_map.py", "03_prepare_shot_media.py"):
        p = SCRIPTS / rel
        t = p.read_text(encoding="utf-8")
        if "prefer longer frames" in t:
            continue
        if rel.startswith("02"):
            new = '''def load_i2v():
    """Merge manifests; prefer longer frames (batch 289 over pilot 121)."""
    by = {}
    for p in I2V_MANIFEST_CANDIDATES:
        if p.exists():
            for x in load_json(p):
                prev = by.get(x["shot"])
                # prefer longer frames
                if prev is None or int(x.get("frames") or 0) >= int(prev.get("frames") or 0):
                    by[x["shot"]] = {**x, "_manifest": str(p)}
    return by
'''
            t2, n = re.subn(r"def load_i2v\(\):.*?return by\n", new, t, count=1, flags=re.S)
            if n:
                p.write_text(t2, encoding="utf-8")
                log(f"patched {rel} load_i2v prefer longer frames")
        else:
            new = '''def load_i2v_index():
    """Merge manifests; prefer ok+lanczos with longer frames (batch over pilot)."""
    by = {}
    for p in I2V_MANIFESTS:
        if not p.exists():
            continue
        for x in load_json(p):
            if x.get("ok") and x.get("lanczos") and Path(x["lanczos"]).is_file():
                prev = by.get(x["shot"])
                if prev is None or int(x.get("frames") or 0) >= int(prev.get("frames") or 0):
                    by[x["shot"]] = x  # prefer longer frames
    return by
'''
            t2, n = re.subn(r"def load_i2v_index\(\):.*?return by\n", new, t, count=1, flags=re.S)
            if n:
                p.write_text(t2, encoding="utf-8")
                log(f"patched {rel} load_i2v_index prefer longer frames")


def clear_v3_rebuild_targets(ok_shots: list[str]) -> None:
    shot_dir = RUN / "media" / "shot"
    v3_dir = RUN / "media" / "v3"
    tail_dir = RUN / "media" / "tail_frames"
    affine_tail = RUN / "media" / "affine_tail"
    n = 0
    for sid in ok_shots:
        for p in [
            shot_dir / f"{sid}.mp4",
            v3_dir / f"{sid}_i2v30.mp4",
            v3_dir / f"{sid}_concat.mp4",
            v3_dir / f"{sid}_concat.txt",
            tail_dir / f"{sid}.png",
            affine_tail / f"{sid}_tail.mp4",
        ]:
            if p.exists():
                p.unlink()
                n += 1
    ch_dir = RUN / "chapters"
    for p in list(ch_dir.glob("*_video.mp4")) + list(ch_dir.glob("*_draft.mp4")) + list(ch_dir.glob("*_video.txt")):
        p.unlink(); n += 1
    delivery = RUN / "delivery"
    for name in ["body_video.mp4", "full_video.mp4"]:
        p = delivery / name
        if p.exists():
            p.unlink(); n += 1
    log(f"cleared {n} rebuild targets for {len(ok_shots)} V3-ok shots + chapter/body caches")


def backup_affine_primary() -> dict:
    delivery = RUN / "delivery"
    mapping = {}
    for kind in ("clean", "sub"):
        src = delivery / f"你是一只章鱼_1080p_{kind}.mp4"
        dst = delivery / f"你是一只章鱼_1080p_{kind}_affine_primary.mp4"
        if src.is_file() and src.stat().st_size > 1000:
            if not dst.exists() or dst.stat().st_size != src.stat().st_size:
                shutil.copy2(src, dst)
                log(f"backed up {src.name} -> {dst.name} ({src.stat().st_size} B)")
            mapping[kind] = str(dst)
    return mapping


def run_py(script: str, log_name: str) -> int:
    out = RUN / "logs" / f"{log_name}.out.log"
    err = RUN / "logs" / f"{log_name}.err.log"
    log(f"RUN {script}")
    with out.open("w", encoding="utf-8") as o, err.open("w", encoding="utf-8") as e:
        r = subprocess.run([str(PYTHON), str(SCRIPTS / script)], cwd=str(RUN), stdout=o, stderr=e)
    log(f"EXIT {script} rc={r.returncode}")
    if r.returncode != 0:
        tail = err.read_text(encoding="utf-8", errors="replace")[-1500:]
        log(f"ERR {script}: {tail}")
    return r.returncode


def publish_v3refresh_names() -> dict:
    delivery = RUN / "delivery"
    paths = {}
    for kind in ("clean", "sub"):
        src = delivery / f"你是一只章鱼_1080p_{kind}.mp4"
        dst = delivery / f"你是一只章鱼_1080p_{kind}_v3refresh.mp4"
        if src.is_file():
            shutil.copy2(src, dst)
            paths[kind] = str(dst)
            log(f"published {dst.name} ({src.stat().st_size} B, {probe(src):.3f}s)")
    return paths


def do_refresh() -> int:
    log("=== V3 REFRESH START ===")
    prefer_long_i2v_patch()
    st = manifest_stats()
    update_checkpoint(
        stage="v3_refresh_start",
        in_progress=["v3_refresh"],
        i2v_batch_ok_ge287=st["ok_ge287"],
        i2v_batch_target=TARGET_OK,
        next_action="02 media-map -> 03 prepare -> 06 chapters -> 07b delivery",
    )
    write_status({**st, "batch_pid": None, "batch_alive": False},
                 "批量已满，开始 V3 refresh（media-map→镜头→章节→成片）")
    backups = backup_affine_primary()
    rc = run_py("02_build_media_map.py", "08_v3_media_map")
    if rc != 0:
        return rc
    mm = load_json(RUN / "media-map.json")
    v3_ready = [s["shot_id"] for s in mm["shots"] if s.get("combo") == "V3" and s.get("i2v_path")]
    clear_v3_rebuild_targets(sorted(set(st["ok_shots"]) | set(v3_ready)))
    rc = run_py("03_prepare_shot_media.py", "08_v3_prepare")
    if rc != 0:
        return rc
    prep = load_json(RUN / "media" / "shot_clips_manifest.json")
    prep_stats = prep.get("stats") or {}
    log(f"prepare stats: {prep_stats}")
    rc = run_py("06_assemble_chapters.py", "08_v3_chapters")
    if rc != 0:
        return rc
    rc = run_py("07b_resume_delivery.py", "08_v3_delivery")
    if rc != 0:
        return rc
    v3paths = publish_v3refresh_names()
    clean = RUN / "delivery" / "你是一只章鱼_1080p_clean.mp4"
    sub = RUN / "delivery" / "你是一只章鱼_1080p_sub.mp4"
    qa = {
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "delivery_mode": "v3_refresh",
        "auto_checks": {
            "clean_path": str(clean),
            "clean_exists": clean.is_file(),
            "clean_duration_s": probe(clean) if clean.is_file() else None,
            "clean_size_bytes": clean.stat().st_size if clean.is_file() else 0,
            "sub_path": str(sub),
            "sub_exists": sub.is_file(),
            "sub_duration_s": probe(sub) if sub.is_file() else None,
            "sub_size_bytes": sub.stat().st_size if sub.is_file() else 0,
            "resolution": "1920x1080",
            "fps": 30,
        },
        "affine_primary_backup": backups,
        "v3refresh_copies": v3paths,
        "i2v_batch": {
            "target_v3": TARGET_OK,
            "batch_manifest_ok_ge287": st["ok_ge287"],
            "batch_ok_shots": st["ok_shots"],
            "fail_shots": st["fail_shots"],
            "run_dir": str(BATCH),
        },
        "shot_prep_stats": prep_stats,
        "pending_review": "I2V visual_qa still pending on V3 clips",
        "unfinished": ["I2V visual_qa review"],
        "notes": [
            "V3 refresh complete; affine-primary backed up before overwrite.",
            "No TTS/stills redo.",
            "No I2V stretch; short I2V fell back to affine in 03_prepare.",
        ],
    }
    atomic_json(RUN / "FINAL_QA.json", qa)
    atomic_json(RUN / "delivery" / "FINAL_QA.json", qa)
    atomic_json(RUN / "delivery" / "delivery_manifest.json", {
        "mode": "v3_refresh",
        "clean": str(clean),
        "sub": str(sub),
        "clean_v3refresh": v3paths.get("clean"),
        "sub_v3refresh": v3paths.get("sub"),
        "affine_primary_backup": backups,
        "created_at": now_iso(),
    })
    update_checkpoint(
        stage="delivery_done_v3_refresh",
        in_progress=[],
        completed=list(dict.fromkeys(
            (load_json(RUN / "CHECKPOINT.json").get("completed") or [])
            + ["i2v_batch_12s", "v3_refresh", "delivery_clean_sub_v3_refresh"]
        )),
        next_action="I2V visual_qa review",
        delivery_mode="v3_refresh",
        v3_refresh_needed=False,
        i2v_batch_ok_ge287=st["ok_ge287"],
        shot_prep_stats=prep_stats,
        clean_path=str(clean),
        sub_path=str(sub),
        clean_duration_s=qa["auto_checks"]["clean_duration_s"],
        sub_duration_s=qa["auto_checks"]["sub_duration_s"],
        clean_size_bytes=qa["auto_checks"]["clean_size_bytes"],
        sub_size_bytes=qa["auto_checks"]["sub_size_bytes"],
        v3refresh_paths=v3paths,
        affine_primary_backup=backups,
    )
    write_status(
        {**st, "batch_pid": None, "batch_alive": False},
        f"**V3 refresh 完成** clean={qa['auto_checks']['clean_duration_s']:.1f}s；"
        f"prepare={prep_stats}；备份 affine_primary；另存 *_v3refresh",
    )
    log("=== V3 REFRESH DONE ===")
    return 0


def main():
    log("watch_and_refresh start")
    prefer_long_i2v_patch()
    refreshed = False
    while True:
        st = manifest_stats()
        pid = find_batch_pid()
        alive = bool(pid and pid_alive(pid))
        if (not alive) and st["ok_ge287"] < TARGET_OK:
            pid = restart_batch_if_needed(st)
            alive = bool(pid and pid_alive(pid))
        st["batch_pid"] = pid
        st["batch_alive"] = alive
        latest = st.get("latest") or {}
        remain = max(0, TARGET_OK - st["ok_ge287"])
        note = (
            f"监控中；latest={latest.get('shot')} frames={latest.get('frames')} "
            f"ended={latest.get('ended')}; ETA~{remain * 15}min"
        )
        write_status(st, note)
        update_checkpoint(
            stage="i2v_batch_running" if alive else (
                "i2v_batch_done" if st["ok_ge287"] >= TARGET_OK else "i2v_batch_interrupted"
            ),
            in_progress=["i2v_batch_12s"] if alive else (
                [] if st["ok_ge287"] >= TARGET_OK else ["i2v_batch_resume"]
            ),
            i2v_batch_pid=pid,
            i2v_batch_ok_ge287=st["ok_ge287"],
            i2v_batch_ok_any=st["ok_any"],
            i2v_batch_fail=st["fail"],
            i2v_batch_target=TARGET_OK,
            v3_refresh_needed=True,
            watcher="watch_octopus_v3_refresh.py",
            next_action=(
                "wait I2V batch" if alive else (
                    "start V3 refresh" if st["ok_ge287"] >= TARGET_OK else "resume I2V batch"
                )
            ),
            delivery_mode="affine_primary",
        )
        log(f"ok_ge287={st['ok_ge287']}/{TARGET_OK} ok_any={st['ok_any']} fail={st['fail']} pid={pid} alive={alive}")

        batch_finished = (not alive) and st["ok_ge287"] >= TARGET_OK
        if not alive and st["ok_ge287"] + st["fail"] >= TARGET_OK and st["ok_ge287"] >= max(70, TARGET_OK - 5):
            batch_finished = True

        if batch_finished and not refreshed:
            rc = do_refresh()
            refreshed = True
            return rc

        time.sleep(POLL_S)


if __name__ == "__main__":
    raise SystemExit(main())
