# Chengwu turnaround v1 runner for ddbbi (stdlib only; run with shared\runtime\engines\stills-runtime python_embeded).
# Adapted from E:\program\1project\video\shared\runtime\engines\stills-runtime\scripts\run_stills.py (not modified). Headless: main.py --disable-auto-launch, API only.
# Waits while: foreign gpu.lock alive, TTS python running, ComfyUI 8188/8189 queues non-empty. Never touches other servers.
import json, os, sys, time, subprocess, urllib.request, urllib.parse, urllib.error, uuid

W = r"E:\program\1project\video\projects\悬疑动漫\drafts\chengwu-turnaround-history\v1"
PORTABLE = r"E:\program\1project\video\shared\runtime\engines\stills-runtime\ComfyUI_windows_portable"
EXTRA = r"E:\program\1project\video\shared\runtime\engines\stills-runtime\extra_model_paths.yaml"
PORT = 8192   # 8190 is used by kepu/lieqi stills runners, 8191 by i2v-cmp
URL = "http://127.0.0.1:%d" % PORT
LOCK = r"E:\program\1project\video\shared\work\cache\gpu.lock"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
LOGF = None; COMFY = None; HAVE_LOCK = False

def log(m):
    s = time.strftime("[%m-%d %H:%M:%S] ") + m
    print(s, flush=True)
    with open(LOGF, "a", encoding="utf-8") as f: f.write(s + "\n")

def http(url, data=None, timeout=30):
    req = urllib.request.Request(url, data=(json.dumps(data).encode() if data is not None else None), headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=timeout) as r: return r.read()

def up(base=URL):
    try: http(base + "/system_stats", timeout=5); return True
    except Exception: return False

def pid_alive(pid):
    try:
        out = subprocess.run(["tasklist", "/FI", "PID eq %d" % int(pid), "/NH"], capture_output=True, text=True, timeout=20).stdout
        return str(int(pid)) in out
    except Exception: return True

def tts_procs():
    try:
        ps = "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | % { \"$($_.ProcessId)`t$($_.CommandLine)\" }"
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=60).stdout
    except Exception: return []
    keys = ("shared\runtime\engines\tts", "voxcpm", "index-tts", "gen_voice", "gen_shots", "indextts", "run_shots")
    return [l[:120] for l in out.splitlines() if any(k in l.lower() for k in keys)]

def cuda_python():
    try:
        out = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,process_name", "--format=csv,noheader"], capture_output=True, text=True, timeout=20).stdout
    except Exception: return []
    ours = {COMFY.pid} if COMFY else set()
    res = []
    for line in out.strip().splitlines():
        parts = [x.strip() for x in line.split(",")]
        if parts and parts[0].isdigit() and int(parts[0]) not in ours and "python" in line.lower(): res.append(line.strip())
    return res

def other_runners():
    """Other agents' GPU runner processes (active or queued) -> we yield to them before starting."""
    try:
        ps = "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | % { \"$($_.ProcessId)`t$($_.CommandLine)\" }"
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=60).stdout
    except Exception: return []
    keys = ("i2v_cmp", "run_lieqi", "run_stills", "run_bakeoff", "train_network", "sdxl_train", "accelerate", "bench_", "run_h3")
    me = str(os.getpid())
    return [l[:140] for l in out.splitlines() if any(k in l.lower() for k in keys) and not l.startswith(me + "\t")]

def busy_reasons(strict=False):
    r = []
    if os.path.exists(LOCK):
        try:
            h = json.load(open(LOCK, encoding="utf-8"))
            if h.get("pid") != os.getpid() and pid_alive(h.get("pid", 0)): r.append("lock=%s" % h)
        except Exception: pass
    for p in (8188, 8189, 8190, 8191):
        b = "http://127.0.0.1:%d" % p
        if up(b):
            try:
                q = json.loads(http(b + "/queue", timeout=10))
                n = len(q.get("queue_running", [])) + len(q.get("queue_pending", []))
                if n: r.append("comfy%d queue=%d" % (p, n))
            except Exception as e: r.append("comfy%d queue? %s" % (p, e))
    t = tts_procs()
    if t: r.append("tts=%s" % t)
    c = cuda_python()
    if c: r.append("cuda=%s" % c)
    if strict:
        o = other_runners()
        if o: r.append("runners=%s" % o)
    return r

def wait_idle(where):
    waited = 0
    while True:
        r = busy_reasons(strict=True)
        if not r:
            if waited: log("GPU idle again after %ds (%s)" % (waited, where))
            return waited
        if waited % 300 == 0: log("WAIT gpu busy (%s): %s" % (where, r))
        time.sleep(30); waited += 30

def take_lock(tag):
    """Write gpu.lock, then re-read after 5s to make sure nobody raced us. Returns True if we hold it."""
    global HAVE_LOCK
    json.dump(dict(owner="chengwu-turnaround:" + tag, pid=os.getpid(), started=time.strftime("%Y-%m-%d %H:%M:%S")), open(LOCK, "w", encoding="utf-8"))
    time.sleep(5)
    try: mine = json.load(open(LOCK, encoding="utf-8")).get("pid") == os.getpid()
    except Exception: mine = False
    HAVE_LOCK = mine; log("gpu.lock taken" if mine else "gpu.lock race lost, waiting again"); return mine

def acquire(where, tag):
    while True:
        wait_idle(where)
        if take_lock(tag): return

def release_lock():
    global HAVE_LOCK
    try:
        if os.path.exists(LOCK) and json.load(open(LOCK, encoding="utf-8")).get("pid") == os.getpid():
            os.remove(LOCK); log("gpu.lock released")
    except Exception as e: log("lock release err %s" % e)
    HAVE_LOCK = False

def start_comfy():
    global COMFY
    if up(): raise SystemExit("port %d already in use by another ComfyUI; not touching it" % PORT)
    os.makedirs(W + r"\logs", exist_ok=True)
    lf = open(W + r"\logs\comfy_%s.log" % time.strftime("%m%d_%H%M%S"), "w", encoding="utf-8")
    args = [PORTABLE + r"\python_embeded\python.exe", "-s", PORTABLE + r"\ComfyUI\main.py", "--listen", "127.0.0.1", "--port", str(PORT),
            "--disable-auto-launch", "--extra-model-paths-config", EXTRA,
            "--output-directory", W + r"\comfy_output", "--input-directory", W + r"\comfy_input"]
    env = dict(os.environ); env["PYTHONIOENCODING"] = "utf-8"
    COMFY = subprocess.Popen(args, cwd=PORTABLE, stdout=lf, stderr=subprocess.STDOUT, env=env, creationflags=0x08000000)
    log("started comfy pid %d port %d" % (COMFY.pid, PORT))
    for _ in range(300):
        if up(): log("comfy up"); return
        if COMFY.poll() is not None: raise SystemExit("comfy exited early")
        time.sleep(2)
    raise SystemExit("comfy did not come up")

def stop_comfy():
    global COMFY
    if COMFY:
        try: http(URL + "/free", {"unload_models": True, "free_memory": True})
        except Exception: pass
        COMFY.terminate()
        try: COMFY.wait(30)
        except Exception: COMFY.kill()
        log("comfy terminated"); COMFY = None

def upload(path):
    b = uuid.uuid4().hex; name = os.path.basename(path); data = open(path, "rb").read()
    body = (("--%s\r\nContent-Disposition: form-data; name=\"image\"; filename=\"%s\"\r\nContent-Type: image/png\r\n\r\n" % (b, name)).encode()
            + data + ("\r\n--%s\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--%s--\r\n" % (b, b)).encode())
    req = urllib.request.Request(URL + "/upload/image", data=body, headers={"Content-Type": "multipart/form-data; boundary=" + b})
    with OPENER.open(req, timeout=60) as r: return json.loads(r.read())["name"]

def run_job(job, outdir):
    prompt = job["prompt"]
    for node in prompt.values():
        for k, v in list(node["inputs"].items()):
            if isinstance(v, str) and v.startswith("@ref:"): node["inputs"][k] = upload(v[5:])
    t0 = time.time()
    try: r = json.loads(http(URL + "/prompt", {"prompt": prompt, "client_id": "chengwu-turnaround"}))
    except urllib.error.HTTPError as e: return dict(ok=False, error="submit: " + e.read().decode("utf-8", "replace")[:2000])
    pid = r["prompt_id"]
    while True:
        time.sleep(1)
        if COMFY and COMFY.poll() is not None: return dict(ok=False, error="comfy crashed")
        try: h = json.loads(http(URL + "/history/" + pid))
        except Exception: continue
        if pid in h and h[pid].get("status", {}).get("completed") is not None: break
    ent = h[pid]; st = ent["status"]; msgs = {m[0]: m[1] for m in st.get("messages", [])}
    rec = dict(ok=st.get("status_str") == "success", wall_s=round(time.time() - t0, 1), files=[])
    if not rec["ok"]: rec["error"] = json.dumps(msgs.get("execution_error", msgs), ensure_ascii=False)[:2000]; return rec
    for o in ent.get("outputs", {}).values():
        for im in o.get("images", []):
            q = urllib.parse.urlencode({"filename": im["filename"], "subfolder": im.get("subfolder", ""), "type": im.get("type", "output")})
            data = OPENER.open(URL + "/view?" + q, timeout=60).read()
            dst = os.path.join(outdir, im["filename"]); open(dst, "wb").write(data); rec["files"].append(dst)
    return rec

def main():
    global LOGF
    spec = json.load(open(sys.argv[1], encoding="utf-8")); tag = spec["tag"]
    os.makedirs(W + r"\logs", exist_ok=True); LOGF = W + r"\logs\run_%s.log" % tag
    outdir = W + r"\out\%s" % tag; os.makedirs(outdir, exist_ok=True)
    ok = fail = 0; t_all = time.time()
    log("=== START %s (%d jobs)" % (tag, len(spec["jobs"])))
    try:
        acquire("start", tag); start_comfy()
        for j in spec["jobs"]:
            if os.path.exists(os.path.join(outdir, j["id"] + ".done")): log("[skip] %s" % j["id"]); continue
            r = busy_reasons()
            if r:
                log("others busy before %s: %s -> stop our comfy and wait" % (j["id"], r))
                stop_comfy(); release_lock(); acquire(j["id"], tag); start_comfy()
            rec = run_job(j, outdir)
            meta = {k: v for k, v in j.items() if k != "prompt"}; meta.update(rec, finished=time.strftime("%Y-%m-%d %H:%M:%S"))
            json.dump(dict(meta, prompt=j["prompt"]), open(os.path.join(outdir, j["id"] + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            if rec["ok"]:
                ok += 1; open(os.path.join(outdir, j["id"] + ".done"), "w").write("ok")
                log("[ok] %s wall=%.1fs files=%s" % (j["id"], rec["wall_s"], [os.path.basename(f) for f in rec["files"]]))
            else:
                fail += 1; log("[FAIL] %s %s" % (j["id"], rec.get("error", "")[:1500]))
                if COMFY and COMFY.poll() is not None: log("comfy died; restart"); start_comfy()
    except SystemExit as e: log("ABORT %s" % e); fail += 1
    except Exception as e: log("ABORT %r" % e); fail += 1
    finally:
        stop_comfy(); release_lock()
    log("=== END ok=%d fail=%d total=%.0fs" % (ok, fail, time.time() - t_all))

if __name__ == "__main__": main()
