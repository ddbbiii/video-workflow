# -*- coding: utf-8 -*-
# one-shot stills. does not touch shared workflows. does not kill foreign comfy.
import json, os, sys, time, subprocess, urllib.request, urllib.parse, urllib.error, shutil

PY_COMFY = r"E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe"
PORTABLE = r"E:\program\1project\video\shared\runtime\comfy\installs\portable"
MAIN = PORTABLE + r"\ComfyUI\main.py"
EXTRA = PORTABLE + r"\ComfyUI\extra_model_paths.yaml"
LOCK = r"E:\program\1project\video\shared\work\cache\gpu.lock"
OUTDIR = r"E:\program\1project\video\projects\悬疑动漫\mirror-who-are-you\trial-plot-stills-2026-10-05"
XFER = r"E:\program\1project\video\xfer\trial-plot-stills-2026-10-05"
PORT = 8191
URL = "http://127.0.0.1:%d" % PORT
CKPT = "animagine-xl-4.0-opt.safetensors"
LORA = "chengwu-sdxl-v1b.safetensors"
OWNER = "xuanyi-trial-plot-stills"
LOGP = os.path.join(OUTDIR, "run.log")
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PROC = None

NEG = (
    "huge breasts, exaggerated bust, hourglass, cleavage, sexualized, large breasts, big chest, "
    "deep neckline, underboob, bikini, lingerie, child, loli, open mouth, talking, teeth, tongue, "
    "bad anatomy, extra fingers, missing fingers, extra arms, deformed hands, watermark, signature, "
    "lowres, worst quality, blurry jpeg"
)

JOBS = [
    ("fog", 51021, 1,
     "bathroom mirror extreme close-up of fogged glass, one index finger writing in condensation, "
     "the Chinese character 程 is large, clear, and legible in the center of the mirror, hanzi 程, "
     "the written character is the subject, face in the mirror heavily blurred and out of focus, "
     "not a portrait, not a bust shot, ordinary average build, modest chest, closed mouth, "
     "short grey-blue hair only as a soft blur, thin black choker, teal boat-neck top, shoulders covered, "
     "young adult, anime style, vertical composition, mist, condensation"),
    ("fog", 51022, 2,
     "macro view of a fogged bathroom mirror, a fingertip has just written one big handwritten Chinese character 程, "
     "程 fills the middle of the frame and is readable, only one finger, no face, no portrait, no chest, "
     "steam, water droplets, anime background, ordinary, closed mouth if any mouth is visible"),
    ("fog", 51023, 3,
     "chengwu, fogged bathroom mirror, finger writing the character 程 clearly, 程 is sharp, reflection of the girl is soft and blurred, "
     "short grey-blue bob, thin black choker, teal boat neck showing a little collarbone, shoulders mostly covered, "
     "young adult not childlike, ordinary slim body, small modest chest, closed mouth, anime, not a close-up of the body"),
    ("group", 51031, 1,
     "chengwu, indoor group photo of exactly four young adults standing together, full group in frame, "
     "the short grey-blue bob girl stands in the exact center, eyes curved in a closed-mouth smile, mouth shut, "
     "ordinary average build, modest small chest, plain teal boat-neck top, shoulders covered, thin black choker, "
     "young adult, friends on both sides, not a solo portrait, not a bust shot, anime style, vertical"),
    ("group", 51032, 2,
     "chengwu, snapshot of three young people indoors, she is the middle person, short grey-blue hair, "
     "smiling eyes, closed lips, average body proportions, flat modest chest, simple clothes, thin black choker, "
     "teal collar, shoulders covered, young adult, waist-up group, anime, no solo close-up"),
    ("group", 51033, 3,
     "chengwu, four friends group portrait in a small room, center girl has short grey-blue hair and a thin black choker, "
     "eyes smiling first, mouth closed, ordinary figure, no large chest, plain teal top, shoulders covered, "
     "everyone similar height, anime style, vertical framing, not a single person"),
]

def log(msg):
    s = time.strftime("[%m-%d %H:%M:%S] ") + msg
    print(s, flush=True)
    with open(LOGP, "a", encoding="utf-8") as f:
        f.write(s + "\n")

def pid_alive(pid):
    if not pid:
        return False
    try:
        out = subprocess.run(["tasklist", "/FI", "PID eq %d" % int(pid), "/NH"], capture_output=True, text=True, timeout=20).stdout
        return str(int(pid)) in out
    except Exception:
        return True

def port_listen(port):
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return False
    key = ":%d" % port
    for line in out.splitlines():
        if key in line and "LISTENING" in line:
            return True
    return False

def read_lock():
    if not os.path.exists(LOCK):
        return None
    try:
        return json.load(open(LOCK, encoding="utf-8"))
    except Exception as e:
        return {"owner": "unreadable", "pid": 0, "err": str(e)}

def wait_lock():
    deadline = time.time() + 40 * 60
    while time.time() < deadline:
        h = read_lock()
        alive = bool(h) and pid_alive(h.get("pid"))
        busy8190 = port_listen(8190)
        if (h is None or not alive) and not busy8190 and not port_listen(PORT):
            # recheck immediately before taking
            h2 = read_lock()
            alive2 = bool(h2) and pid_alive(h2.get("pid"))
            if (h2 is None or not alive2) and not port_listen(8190):
                log("lock free holder=%s alive=%s 8190_down" % (h2, alive2))
                return True
        left = int(deadline - time.time())
        log("WAIT lock=%s alive=%s port8190=%s left=%ss" % (h, alive, busy8190, left))
        time.sleep(75)
    h = read_lock()
    log("TIMEOUT lock still %s alive=%s port8190=%s" % (h, bool(h) and pid_alive((h or {}).get("pid")), port_listen(8190)))
    return False

def acquire():
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    json.dump({"owner": OWNER, "pid": os.getpid(), "started": time.strftime("%Y-%m-%d %H:%M:%S")},
              open(LOCK, "w", encoding="utf-8"))
    log("gpu.lock acquired pid=%s" % os.getpid())

def release():
    try:
        if os.path.exists(LOCK):
            h = json.load(open(LOCK, encoding="utf-8"))
            if h.get("pid") == os.getpid() and h.get("owner") == OWNER:
                os.remove(LOCK)
                log("gpu.lock released")
            else:
                log("gpu.lock NOT ours, left in place: %s" % h)
        else:
            log("gpu.lock already absent")
    except Exception as e:
        log("lock release error %s" % e)

def http(path, data=None, timeout=60):
    req = urllib.request.Request(URL + path, data=(json.dumps(data).encode("utf-8") if data is not None else None),
                                 headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=timeout) as r:
        return r.read()

def up():
    try:
        http("/system_stats", timeout=5)
        return True
    except Exception:
        return False

def start_comfy():
    global PROC
    if port_listen(PORT):
        raise SystemExit("port %d already in use; refusing" % PORT)
    udir = os.path.join(OUTDIR, "comfy-user")
    for d in ("in", "comfy-out", "temp", udir):
        os.makedirs(os.path.join(OUTDIR, d), exist_ok=True)
    args = [PY_COMFY, "-s", MAIN, "--listen", "127.0.0.1", "--port", str(PORT),
            "--disable-auto-launch", "--disable-pinned-memory",
            "--input-directory", os.path.join(OUTDIR, "in"),
            "--output-directory", os.path.join(OUTDIR, "comfy-out"),
            "--temp-directory", os.path.join(OUTDIR, "temp"),
            "--user-directory", udir,
            "--extra-model-paths-config", EXTRA]
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        env.pop(k, None)
    clog = os.path.join(OUTDIR, "comfy-8191.log")
    lf = open(clog, "w", encoding="utf-8")
    PROC = subprocess.Popen(args, cwd=PORTABLE, stdout=lf, stderr=subprocess.STDOUT, env=env, creationflags=0x08000000)
    log("started comfy pid %s port %s" % (PROC.pid, PORT))
    t0 = time.time()
    while time.time() - t0 < 300:
        if up():
            log("comfy up after %.0fs" % (time.time() - t0))
            return
        if PROC.poll() is not None:
            raise RuntimeError("comfy exited early code %s see %s" % (PROC.returncode, clog))
        time.sleep(2)
    raise RuntimeError("comfy did not come up")

def stop_comfy():
    global PROC
    if PROC is None:
        return
    if PROC.poll() is None:
        PROC.terminate()
        try:
            PROC.wait(timeout=20)
        except Exception:
            PROC.kill()
    log("comfy stopped code=%s" % PROC.returncode)
    PROC = None

def graph(pos, seed, prefix):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoraLoader", "inputs": {
            "model": ["1", 0], "clip": ["1", 1],
            "lora_name": LORA, "strength_model": 0.8, "strength_clip": 0.8,
        }},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["2", 1]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["2", 1]}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 768, "height": 1344, "batch_size": 1}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["2", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0],
            "seed": seed, "steps": 28, "cfg": 5.5, "sampler_name": "euler_ancestral",
            "scheduler": "normal", "denoise": 1.0,
        }},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": prefix}},
    }

def run_one(kind, seed, attempt, pos):
    prefix = "try/%s-%d" % (kind, seed)
    g = graph(pos, seed, prefix)
    t0 = time.time()
    try:
        r = json.loads(http("/prompt", {"prompt": g, "client_id": "xuanyi-trial-stills"}))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", "replace")[:2000]
        log("SUBMIT FAIL %s seed %s %s" % (kind, seed, err))
        return {"kind": kind, "seed": seed, "attempt": attempt, "ok": False, "error": err}
    pid = r["prompt_id"]
    log("queued %s seed %s prompt_id %s" % (kind, seed, pid))
    while True:
        time.sleep(1)
        if PROC and PROC.poll() is not None:
            return {"kind": kind, "seed": seed, "attempt": attempt, "ok": False, "error": "comfy died"}
        try:
            h = json.loads(http("/history/" + pid))
        except Exception:
            continue
        if pid in h and h[pid].get("status", {}).get("completed"):
            break
        if time.time() - t0 > 600:
            return {"kind": kind, "seed": seed, "attempt": attempt, "ok": False, "error": "timeout"}
    ent = h[pid]
    ok = ent.get("status", {}).get("status_str") == "success"
    saved = []
    if ok:
        for o in ent.get("outputs", {}).values():
            for im in o.get("images", []):
                q = urllib.parse.urlencode({"filename": im["filename"], "subfolder": im.get("subfolder", ""), "type": im.get("type", "output")})
                data = OPENER.open(URL + "/view?" + q, timeout=60).read()
                name = "%s-seed%d-a%d.png" % (kind, seed, attempt)
                path = os.path.join(OUTDIR, name)
                open(path, "wb").write(data)
                saved.append(path)
                log("saved %s bytes %d" % (path, len(data)))
    else:
        log("RUN FAIL %s seed %s %s" % (kind, seed, json.dumps(ent.get("status"), ensure_ascii=False)[:800]))
    return {"kind": kind, "seed": seed, "attempt": attempt, "ok": ok, "files": saved, "positive": pos, "seconds": round(time.time()-t0, 1)}

def main():
    os.makedirs(OUTDIR, exist_ok=True)
    log("runner start pid=%s" % os.getpid())
    if not wait_lock():
        log("=== END timeout, no images")
        return 2
    try:
        acquire()
        start_comfy()
        results = []
        for kind, seed, attempt, pos in JOBS:
            results.append(run_one(kind, seed, attempt, pos))
        meta = {
            "ckpt": CKPT, "lora": LORA, "lora_strength": 0.8,
            "size": [768, 1344], "steps": 28, "cfg": 5.5, "sampler": "euler_ancestral",
            "negative": NEG, "results": results,
        }
        json.dump(meta, open(os.path.join(OUTDIR, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        log("=== END generated %d" % len(results))
        return 0
    finally:
        stop_comfy()
        release()

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log("FATAL %r" % (e,))
        stop_comfy()
        release()
        raise