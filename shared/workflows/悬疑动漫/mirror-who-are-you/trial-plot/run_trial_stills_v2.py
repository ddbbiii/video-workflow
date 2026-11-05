# -*- coding: utf-8 -*-
# one-shot v2. reference = turnaround png via IPAdapter. does not edit shared workflows.
import json, os, sys, time, subprocess, urllib.request, urllib.parse, urllib.error, struct, zlib

PY_COMFY = r"E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe"
PORTABLE = r"E:\program\1project\video\shared\runtime\comfy\installs\portable"
MAIN = PORTABLE + r"\ComfyUI\main.py"
EXTRA = PORTABLE + r"\ComfyUI\extra_model_paths.yaml"
LOCK = r"E:\program\1project\video\shared\work\cache\gpu.lock"
OUTDIR = r"E:\program\1project\video\projects\悬疑动漫\mirror-who-are-you\trial-plot-stills-2026-10-05"
REF = r"E:\program\1project\video\projects\悬疑动漫\chengwu-turnaround-v5\cw_turnaround_v5_01.png"
PORT = 8191
URL = "http://127.0.0.1:%d" % PORT
CKPT = "animagine-xl-4.0-opt.safetensors"
LORA = "chengwu-sdxl-v1b.safetensors"
OWNER = "xuanyi-trial-plot-stills-v2"
LOGP = os.path.join(OUTDIR, "run-v2.log")
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PROC = None

NEG = (
    "child, loli, open mouth, talking, teeth, tongue, "
    "choker, black collar, teal boat neck, teal scoop neck, bare shoulders, camisole, tank top, "
    "character sheet, turnaround, reference sheet, three views, duplicate, clone, identical faces, "
    "bad anatomy, extra fingers, missing fingers, watermark, lowres, worst quality"
)
CLOTHES = (
    "short grey-blue hair, black leather jacket, dark green inner shirt, silver necklace, "
    "grey pants, black boots, young adult, closed mouth"
)

JOBS = [
    # kind, seed, attempt, lora, ipa, mask, prompt
    ("fog", 52041, 1, 0.65, 0.35, False,
     "bathroom mirror extreme close-up, fogged glass, one index finger writing in the condensation, "
     "the Chinese character 程 is huge, sharp and readable in the center, hanzi 程 is the subject, "
     "face in the mirror is blurred, " + CLOTHES + ", anime, vertical, mist"),
    ("fog", 52042, 2, 0.55, 0.25, False,
     "macro of fogged bathroom mirror, fingertip has written one large handwritten Chinese character 程, "
     "程 fills the frame and is legible, only the character and one finger, blurred reflection, "
     + CLOTHES + ", anime"),
    ("fog", 52043, 3, 0.7, 0.5, False,
     "chengwu, fogged bathroom mirror, finger writes the clear character 程, 程 is sharp, "
     "reflection soft and out of focus, " + CLOTHES + ", not a portrait, anime vertical"),
    ("group", 52051, 1, 0.5, 0.8, True,
     "indoor group photo of three different young adults, the center person is chengwu standing in the exact middle, "
     + CLOTHES + ", eyes curved in a closed-mouth smile, "
     "on the left a boy with short black hair and a grey hoodie, different face, "
     "on the right a girl with long brown hair and a cream sweater, different face, "
     "not clones, anime, vertical, full group"),
    ("group", 52052, 2, 0.4, 0.65, True,
     "snapshot, three friends indoors, only the middle girl has short grey-blue hair and a black leather jacket, "
     "dark green shirt, grey pants, black boots, silver necklace, smiling eyes, mouth closed, "
     "left person has brown hair and a navy jacket, right person has black ponytail and a white shirt, "
     "distinct faces, anime vertical"),
    ("group", 52053, 3, 0.55, 0.9, True,
     "chengwu standing center of a four-person indoor photo, " + CLOTHES + ", curved smiling eyes, mouth shut, "
     "the other three people have different hair colors and different clothes, not copies of her, anime"),
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
    return any(key in line and "LISTENING" in line for line in out.splitlines())

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
        busy = port_listen(8190) or port_listen(PORT)
        if (h is None or not alive) and not busy:
            h2 = read_lock()
            alive2 = bool(h2) and pid_alive(h2.get("pid"))
            if (h2 is None or not alive2) and not port_listen(8190) and not port_listen(PORT):
                log("lock free %s" % h2)
                return True
        log("WAIT lock=%s alive=%s busy=%s left=%ss" % (h, alive, busy, int(deadline - time.time())))
        time.sleep(75)
    log("TIMEOUT lock=%s" % read_lock())
    return False

def acquire():
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
                log("gpu.lock NOT ours: %s" % h)
        else:
            log("gpu.lock already absent")
    except Exception as e:
        log("lock release error %s" % e)

def http(path, data=None, timeout=120):
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

def write_png(path, w, h):
    # white center band, black sides, RGB
    raw = bytearray()
    x0, x1 = int(w * 0.30), int(w * 0.70)
    for y in range(h):
        raw.append(0)
        for x in range(w):
            v = 255 if x0 <= x < x1 else 0
            raw.extend((v, v, v))
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    open(path, "wb").write(png)

def upload(path):
    boundary = "----xuanyiboundary"
    name = os.path.basename(path)
    data = open(path, "rb").read()
    body = ("--%s\r\nContent-Disposition: form-data; name=\"image\"; filename=\"%s\"\r\nContent-Type: image/png\r\n\r\n" % (boundary, name)).encode()
    body += data
    body += ("\r\n--%s\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--%s--\r\n" % (boundary, boundary)).encode()
    req = urllib.request.Request(URL + "/upload/image", data=body, headers={"Content-Type": "multipart/form-data; boundary=" + boundary})
    with OPENER.open(req, timeout=120) as r:
        info = json.loads(r.read())
    log("uploaded %s -> %s" % (name, info.get("name")))
    return info["name"]

def start_comfy():
    global PROC
    if port_listen(PORT):
        raise SystemExit("port in use")
    udir = os.path.join(OUTDIR, "comfy-user-v2")
    for d in ("in", "comfy-out-v2", "temp-v2", udir):
        os.makedirs(os.path.join(OUTDIR, d), exist_ok=True)
    args = [PY_COMFY, "-s", MAIN, "--listen", "127.0.0.1", "--port", str(PORT),
            "--disable-auto-launch", "--disable-pinned-memory",
            "--input-directory", os.path.join(OUTDIR, "in"),
            "--output-directory", os.path.join(OUTDIR, "comfy-out-v2"),
            "--temp-directory", os.path.join(OUTDIR, "temp-v2"),
            "--user-directory", udir,
            "--extra-model-paths-config", EXTRA]
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        env.pop(k, None)
    lf = open(os.path.join(OUTDIR, "comfy-8191-v2.log"), "w", encoding="utf-8")
    PROC = subprocess.Popen(args, cwd=PORTABLE, stdout=lf, stderr=subprocess.STDOUT, env=env, creationflags=0x08000000)
    log("started comfy pid %s" % PROC.pid)
    t0 = time.time()
    while time.time() - t0 < 360:
        if up():
            log("comfy up after %.0fs" % (time.time() - t0))
            return
        if PROC.poll() is not None:
            raise RuntimeError("comfy exited %s" % PROC.returncode)
        time.sleep(2)
    raise RuntimeError("comfy did not come up")

def stop_comfy():
    global PROC
    if PROC is None:
        return
    if PROC.poll() is None:
        PROC.terminate()
        try:
            PROC.wait(timeout=25)
        except Exception:
            PROC.kill()
    log("comfy stopped code=%s" % PROC.returncode)
    PROC = None

def graph(pos, seed, prefix, lora_s, ipa_w, ref_name, mask_name):
    g = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoraLoader", "inputs": {
            "model": ["1", 0], "clip": ["1", 1], "lora_name": LORA,
            "strength_model": lora_s, "strength_clip": lora_s,
        }},
        "10": {"class_type": "LoadImage", "inputs": {"image": ref_name}},
        "11": {"class_type": "IPAdapterUnifiedLoader", "inputs": {
            "model": ["2", 0], "preset": "PLUS (high strength)",
        }},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["2", 1]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["2", 1]}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 768, "height": 1344, "batch_size": 1}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": prefix}},
    }
    ipa = {
        "model": ["11", 0], "ipadapter": ["11", 1], "image": ["10", 0],
        "weight": ipa_w, "weight_type": "linear", "combine_embeds": "average",
        "start_at": 0.0, "end_at": 0.85, "embeds_scaling": "V only",
    }
    if mask_name:
        g["20"] = {"class_type": "LoadImage", "inputs": {"image": mask_name}}
        g["21"] = {"class_type": "ImageToMask", "inputs": {"image": ["20", 0], "channel": "red"}}
        ipa["attn_mask"] = ["21", 0]
    g["12"] = {"class_type": "IPAdapterAdvanced", "inputs": ipa}
    g["6"] = {"class_type": "KSampler", "inputs": {
        "model": ["12", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0],
        "seed": seed, "steps": 28, "cfg": 5.5, "sampler_name": "euler_ancestral",
        "scheduler": "normal", "denoise": 1.0,
    }}
    return g

def run_one(kind, seed, attempt, lora_s, ipa_w, use_mask, pos, ref_name, mask_name):
    g = graph(pos, seed, "tryv2/%s-%d" % (kind, seed), lora_s, ipa_w, ref_name, mask_name if use_mask else None)
    t0 = time.time()
    try:
        r = json.loads(http("/prompt", {"prompt": g, "client_id": "xuanyi-v2"}))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", "replace")[:2500]
        log("SUBMIT FAIL %s %s %s" % (kind, seed, err))
        return {"kind": kind, "seed": seed, "attempt": attempt, "ok": False, "error": err, "lora": lora_s, "ipa": ipa_w}
    pid = r["prompt_id"]
    log("queued %s seed %s ipa %s lora %s id %s" % (kind, seed, ipa_w, lora_s, pid))
    while True:
        time.sleep(1)
        if PROC and PROC.poll() is not None:
            return {"kind": kind, "seed": seed, "ok": False, "error": "comfy died"}
        try:
            h = json.loads(http("/history/" + pid, timeout=30))
        except Exception:
            continue
        if pid in h and h[pid].get("status", {}).get("completed"):
            break
        if time.time() - t0 > 700:
            return {"kind": kind, "seed": seed, "ok": False, "error": "timeout"}
    ent = h[pid]
    ok = ent.get("status", {}).get("status_str") == "success"
    saved = []
    if not ok:
        log("RUN FAIL %s %s" % (kind, json.dumps(ent.get("status"), ensure_ascii=False)[:1000]))
    else:
        for o in ent.get("outputs", {}).values():
            for im in o.get("images", []):
                q = urllib.parse.urlencode({"filename": im["filename"], "subfolder": im.get("subfolder", ""), "type": im.get("type", "output")})
                data = OPENER.open(URL + "/view?" + q, timeout=60).read()
                name = "%s-v2-seed%d-a%d.png" % (kind, seed, attempt)
                path = os.path.join(OUTDIR, name)
                open(path, "wb").write(data)
                saved.append(path)
                log("saved %s %d" % (path, len(data)))
    return {"kind": kind, "seed": seed, "attempt": attempt, "ok": ok, "files": saved,
            "lora": lora_s, "ipa": ipa_w, "mask": use_mask, "positive": pos, "seconds": round(time.time()-t0, 1)}

def main():
    os.makedirs(OUTDIR, exist_ok=True)
    log("v2 start pid=%s" % os.getpid())
    if not os.path.exists(REF):
        log("missing ref")
        return 3
    if not wait_lock():
        log("=== END timeout")
        return 2
    try:
        acquire()
        mask_path = os.path.join(OUTDIR, "center-mask.png")
        write_png(mask_path, 768, 1344)
        start_comfy()
        ref_name = upload(REF)
        mask_name = upload(mask_path)
        results = []
        for job in JOBS:
            results.append(run_one(*job, ref_name, mask_name))
        json.dump({"ckpt": CKPT, "lora": LORA, "ref": REF, "ipa_preset": "PLUS (high strength)",
                   "negative": NEG, "results": results},
                  open(os.path.join(OUTDIR, "manifest-v2.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
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