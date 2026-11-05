# lieqi runner (copied from kepu-pipeline/windows/comfy/run_stills.py 2026-10-01, own log/output dirs) for ddbbi (stdlib only; runs with comfy-stills python_embeded).
# Usage: python run_stills.py <jobs.json>        (normally launched hidden by run_stills.ps1)
# Jobs come from scripts/stills.py jobs (box). For each job: fill-in done on the box already (API graph in job["prompt"]),
# here we: take the GPU lock, wait for TTS, start ComfyUI (never the browser page), upload refs, run jobs one by one
# (grouped by workflow -> each model loads once), save <raw_dir>\<shot>\<id>.png + <id>.json, zip them to pull_zip,
# shut ComfyUI down, release the lock. Log: <root>\logs\stills_<tag>.log, last line '=== END ok=N fail=M ...'.
# Resumable: jobs whose png already exists in raw_dir are skipped.
import json, os, sys, time, subprocess, urllib.request, urllib.parse, urllib.error, uuid, shutil, zipfile

INSTANCES = {
    # name -> how to start it. Add "portable-8188" here when the sdxl_lora provider is implemented.
    "comfy-stills": dict(root=r"E:\program\1project\video\projects\猎奇", portable=r"E:\program\1project\video\shared\runtime\engines\stills-runtime\ComfyUI_windows_portable",
                         port=8190, extra=r"E:\program\1project\video\shared\runtime\engines\stills-runtime\extra_model_paths.yaml"),
}
LOCK = r"E:\program\1project\video\shared\work\cache\gpu.lock"   # shared GPU lock (TTS run_shots.ps1 waits while it is held)
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
LOGF = None
COMFY_PROC = None
URL = None


def log(msg):
    s = time.strftime("[%m-%d %H:%M:%S] ") + msg
    print(s, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(s + "\n")


def http(path, data=None, timeout=30):
    req = urllib.request.Request(URL + path, data=(json.dumps(data).encode() if data is not None else None),
                                 headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=timeout) as r:
        return r.read()


def up():
    try:
        http("/system_stats", timeout=5); return True
    except Exception:
        return False


def pid_alive(pid):
    try:
        out = subprocess.run(["tasklist", "/FI", "PID eq %d" % int(pid), "/NH"], capture_output=True, text=True, timeout=20).stdout
        return str(int(pid)) in out
    except Exception:
        return True


def tts_procs():
    try:
        ps = ("Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
              "% { \"$($_.ProcessId)`t$($_.CommandLine)\" }")
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return []
    keys = ("shared\runtime\engines\tts", "voxcpm", "index-tts", "gen_voice", "gen_shots", "indextts")
    return [l for l in out.splitlines() if any(k in l.lower() for k in keys)]


def other_gpu_python():
    try:
        out = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,process_name", "--format=csv,noheader"],
                             capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return []
    ours = {COMFY_PROC.pid} if COMFY_PROC else set()
    res = []
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if parts and parts[0].isdigit() and int(parts[0]) not in ours and "python" in line.lower():
            res.append(line.strip())
    return res


def acquire_lock(tag):
    """Wait for: a live foreign gpu.lock, TTS python processes, other CUDA python processes. Then write the lock."""
    waited = 0
    while True:
        holder = None
        if os.path.exists(LOCK):
            try:
                holder = json.load(open(LOCK, encoding="utf-8"))
                if holder.get("pid") == os.getpid() or not pid_alive(holder.get("pid", 0)):
                    log("stale gpu.lock (%s) -> taking over" % holder); holder = None
            except Exception:
                holder = None
        t = tts_procs(); g = other_gpu_python()
        if not holder and not t and not g:
            break
        if waited % 300 == 0:
            log("WAIT gpu busy: lock=%s tts=%s cuda=%s" % (holder, [x[:120] for x in t], g))
        time.sleep(30); waited += 30
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    json.dump(dict(owner="lieqi:" + tag, pid=os.getpid(), started=time.strftime("%Y-%m-%d %H:%M:%S")), open(LOCK, "w", encoding="utf-8"))
    log("gpu.lock acquired (waited %ds)" % waited)
    return waited


def release_lock():
    try:
        if os.path.exists(LOCK) and json.load(open(LOCK, encoding="utf-8")).get("pid") == os.getpid():
            os.remove(LOCK); log("gpu.lock released")
    except Exception as e:
        log("lock release error %s" % e)


def start_comfy(inst):
    global COMFY_PROC
    if up():
        log("comfy already up on %s (not started by us, will not shut it down)" % URL); return
    root = inst["root"]; portable = inst["portable"]
    os.makedirs(root + r"\logs", exist_ok=True)
    lf = open(os.path.join(root, "logs", "comfy_lieqi_%s.log" % time.strftime("%m%d_%H%M%S")), "w", encoding="utf-8")
    args = [portable + r"\python_embeded\python.exe", "-s", portable + r"\ComfyUI\main.py", "--listen", "127.0.0.1",
            "--port", str(inst["port"]), "--disable-auto-launch", "--extra-model-paths-config", inst["extra"],
            "--output-directory", root + r"\comfy_output", "--input-directory", root + r"\comfy_input"]
    env = dict(os.environ); env["PYTHONIOENCODING"] = "utf-8"
    COMFY_PROC = subprocess.Popen(args, cwd=portable, stdout=lf, stderr=subprocess.STDOUT, env=env, creationflags=0x08000000)
    log("started comfy pid %d (port %d, --disable-auto-launch)" % (COMFY_PROC.pid, inst["port"]))
    for _ in range(300):
        if up():
            log("comfy up"); return
        if COMFY_PROC.poll() is not None:
            raise SystemExit("comfy exited early")
        time.sleep(2)
    raise SystemExit("comfy did not come up")


def upload(path):
    b = uuid.uuid4().hex; name = os.path.basename(path)
    with open(path, "rb") as f:
        data = f.read()
    body = (("--%s\r\nContent-Disposition: form-data; name=\"image\"; filename=\"%s\"\r\nContent-Type: image/png\r\n\r\n" % (b, name)).encode()
            + data + ("\r\n--%s\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--%s--\r\n" % (b, b)).encode())
    req = urllib.request.Request(URL + "/upload/image", data=body, headers={"Content-Type": "multipart/form-data; boundary=" + b})
    with OPENER.open(req, timeout=60) as r:
        return json.loads(r.read())["name"]


def run_job(job, raw_dir):
    prompt = job["prompt"]
    for node in prompt.values():
        for k, v in list(node["inputs"].items()):
            if isinstance(v, str) and v.startswith("@ref:"):
                node["inputs"][k] = upload(v[5:])
    t0 = time.time()
    try:
        r = json.loads(http("/prompt", {"prompt": prompt, "client_id": "lieqi"}))
    except urllib.error.HTTPError as e:
        return dict(ok=False, error="submit: " + e.read().decode("utf-8", "replace")[:2000])
    pid = r["prompt_id"]
    while True:
        time.sleep(0.5)
        if COMFY_PROC and COMFY_PROC.poll() is not None:
            return dict(ok=False, error="comfy crashed (exit %s)" % COMFY_PROC.returncode)
        try:
            h = json.loads(http("/history/" + pid))
        except Exception:
            continue
        if pid in h and h[pid].get("status", {}).get("completed") is not None:
            st = h[pid]["status"]
            if st.get("status_str") == "error" or h[pid].get("outputs"):
                break
    ent = h[pid]; st = ent["status"]; msgs = {m[0]: m[1] for m in st.get("messages", [])}
    exec_s = None
    if "execution_start" in msgs:
        end = msgs.get("execution_success") or msgs.get("execution_error") or {}
        if end.get("timestamp"):
            exec_s = (end["timestamp"] - msgs["execution_start"]["timestamp"]) / 1000.0
    rec = dict(ok=st.get("status_str") == "success", exec_s=exec_s, wall_s=round(time.time() - t0, 2))
    if not rec["ok"]:
        rec["error"] = json.dumps(msgs.get("execution_error", msgs), ensure_ascii=False)[:2000]; return rec
    for o in ent.get("outputs", {}).values():
        for im in o.get("images", []):
            q = urllib.parse.urlencode({"filename": im["filename"], "subfolder": im.get("subfolder", ""), "type": im.get("type", "output")})
            data = OPENER.open(URL + "/view?" + q, timeout=60).read()
            dst = os.path.join(raw_dir, job["shot"], job["id"] + ".png")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as f:
                f.write(data)
            rec["file"] = dst
            break
    return rec


def main():
    global LOGF, URL
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    tag = spec["tag"]; inst = INSTANCES[spec.get("instance", "comfy-stills")]
    URL = "http://127.0.0.1:%d" % inst["port"]
    LOGF = os.path.join(inst["root"], "logs", "lieqi_%s.log" % tag)
    os.makedirs(os.path.dirname(LOGF), exist_ok=True)
    raw = spec["raw_dir"]; os.makedirs(raw, exist_ok=True)
    t_all = time.time(); ok = fail = skip = 0; times = []
    log("=== START %s (%d jobs) raw=%s" % (tag, len(spec["jobs"]), raw))
    try:
        xfer_refs = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), "refs")
        for r in spec.get("refs", []):
            if not os.path.exists(r["win"]):
                src = os.path.join(xfer_refs, os.path.basename(r["win"]))
                os.makedirs(os.path.dirname(r["win"]), exist_ok=True); shutil.copy2(src, r["win"]); log("ref %s -> %s" % (src, r["win"]))
        waited = acquire_lock(tag)
        start_comfy(inst)
        try:
            http("/free", {"unload_models": True, "free_memory": True})
        except Exception:
            pass
        for j in spec["jobs"]:
            dst = os.path.join(raw, j["shot"], j["id"] + ".png")
            if os.path.exists(dst):
                skip += 1; log("[skip] %s (exists)" % j["id"]); continue
            if j.get("prompt") is None:
                log("[skip] %s provider %s runs on the box" % (j["id"], j.get("provider"))); continue
            rec = run_job(j, raw)
            meta = {k: v for k, v in j.items() if k != "prompt"}
            meta.update(rec, finished=time.strftime("%Y-%m-%d %H:%M:%S"), tag=tag)
            if rec["ok"]:
                ok += 1; times.append(rec["exec_s"] or rec["wall_s"])
                json.dump(meta, open(dst[:-4] + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                log("[ok] %s %s exec=%.1fs wall=%.1fs" % (j["shot"], j["id"], rec["exec_s"] or -1, rec["wall_s"]))
            else:
                fail += 1; log("[FAIL] %s %s" % (j["id"], rec.get("error", "")[:1500]))
                if COMFY_PROC and COMFY_PROC.poll() is not None:
                    log("comfy died; restarting"); start_comfy(inst)
        try:
            http("/free", {"unload_models": True, "free_memory": True})
        except Exception:
            pass
    except SystemExit as e:
        log("ABORT %s" % e); fail += 1
    except Exception as e:
        log("ABORT %r" % e); fail += 1
    finally:
        if spec.get("shutdown_after", True) and COMFY_PROC:
            COMFY_PROC.terminate()
            try:
                COMFY_PROC.wait(30)
            except Exception:
                COMFY_PROC.kill()
            log("comfy terminated")
        release_lock()
    try:   # zip everything of this tag for the box
        z = spec.get("pull_zip")
        if z:
            os.makedirs(os.path.dirname(z), exist_ok=True)
            n = 0
            with zipfile.ZipFile(z, "w", zipfile.ZIP_STORED) as zf:
                for d, _, fs in os.walk(raw):
                    for f in fs:
                        p = os.path.join(d, f); zf.write(p, os.path.relpath(p, raw)); n += 1
            log("zip %s (%d files, %.1f MB)" % (z, n, os.path.getsize(z) / 1e6))
    except Exception as e:
        log("zip error %r" % e)
    med = sorted(times)[len(times) // 2] if times else -1
    log("=== END ok=%d fail=%d skip=%d median_exec=%.1fs total=%.0fs" % (ok, fail, skip, med, time.time() - t_all))


if __name__ == "__main__":
    main()
