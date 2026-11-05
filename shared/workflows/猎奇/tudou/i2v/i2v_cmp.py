# i2v model comparison on ddbbi, 2026-10-01. stdlib only; run with portable python_embeded.
# Usage: python i2v_cmp.py [model ...]   models: wan ltx hunyuan h3 (default: all, in that order)
# For each model: take E:\program\1project\video\shared\work\cache\gpu.lock (same rules as kepu-pipeline run_stills.py), start a private
# ComfyUI instance (--disable-auto-launch, all writable dirs under SCR), run one I2V job, sample VRAM, /free, stop, release.
import json, os, sys, time, subprocess, urllib.request, urllib.error, uuid, threading, re, shutil

SCR = r"E:\program\1project\video\shared\work\scratch\legacy-numbered\i2v-cmp-2026-10-01"
LOCK = r"E:\program\1project\video\shared\work\cache\gpu.lock"
PY = r"E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe"
PORTABLE = r"E:\program\1project\video\shared\runtime\comfy\installs\portable"
H3_ROOT = r"E:\program\1project\video\shared\runtime\comfy\installs\h3"
H3_LAUNCH = r"E:\program\1project\video\shared\runtime\comfy\installs\h3-runtime\launch_h3.py"
IDLE_8188_PID = 30528          # someone else's idle portable ComfyUI on 8188 (0 models loaded); excluded from the CUDA wait if its queue is empty
IMAGE = "i2v_first_frame.png"   # b-dream-overfit stills_v4/shot_06_s06.png (1188x2112, passed still gate)
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
LOGF = os.path.join(SCR, "logs", "i2v_cmp.log")
RESF = os.path.join(SCR, "results.json")
URL = None
PROC = None

PROMPT = ("Slow, steady cinematic push-in toward a small candle burning on an old wooden desk in a dark, quiet study at night. "
          "The candle flame flickers softly and a thin curl of smoke rises and drifts slowly upward, gently swirling in the cool "
          "moonlight from the window. The desk, notebook, bookshelf and window stay solid and still. Calm and quiet, realistic "
          "lighting, smooth continuous motion, no cuts, no text.")
NEG = ("overexposed, oversaturated, static freeze, fast camera movement, camera shake, scene change, cut, blurry details, "
       "subtitles, text, watermark, logo, worst quality, low quality, jpeg artifacts, warping, melting objects, deformed furniture, "
       "bending lines, flicker, extra candles, people")

def log(msg):
    s = time.strftime("[%m-%d %H:%M:%S] ") + msg
    print(s, flush=True)
    with open(LOGF, "a", encoding="utf-8") as f:
        f.write(s + "\n")

def http(path, data=None, timeout=60):
    req = urllib.request.Request(URL + path, data=(json.dumps(data).encode() if data is not None else None),
                                 headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=timeout) as r:
        return r.read()

def jget(path, timeout=60):
    return json.loads(http(path, timeout=timeout).decode("utf-8"))

def up(url):
    try:
        with OPENER.open(url + "/system_stats", timeout=5) as r:
            r.read(); return True
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

def q8188_idle():
    try:
        with OPENER.open("http://127.0.0.1:8188/queue", timeout=10) as r:
            q = json.loads(r.read().decode())
        return not q.get("queue_running") and not q.get("queue_pending")
    except Exception:
        return True   # not reachable -> not running anything

def other_gpu_python():
    try:
        out = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,process_name", "--format=csv,noheader"],
                             capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return []
    ours = {PROC.pid} if PROC else set()
    res = []
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if not (parts and parts[0].isdigit() and "python" in line.lower()):
            continue
        pid = int(parts[0])
        if pid in ours:
            continue
        if pid == IDLE_8188_PID and q8188_idle():
            continue
        res.append(line.strip())
    return res

def acquire_lock(tag):
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
    json.dump(dict(owner="i2v-cmp-2026-10-01:" + tag, pid=os.getpid(), started=time.strftime("%Y-%m-%d %H:%M:%S")),
              open(LOCK, "w", encoding="utf-8"))
    log("gpu.lock acquired for %s (waited %ds)" % (tag, waited))
    return waited

def release_lock():
    try:
        if os.path.exists(LOCK) and json.load(open(LOCK, encoding="utf-8")).get("pid") == os.getpid():
            os.remove(LOCK); log("gpu.lock released")
    except Exception as e:
        log("lock release error %s" % e)

def start_comfy(kind, tag):
    global PROC, URL
    port = 8189 if kind == "h3" else 8191
    URL = "http://127.0.0.1:%d" % port
    if up(URL):
        raise SystemExit("port %d already in use by someone else; refusing to use it" % port)
    udir = os.path.join(SCR, "user-" + kind)
    for d in ("in", "out", "temp", udir):
        os.makedirs(os.path.join(SCR, d), exist_ok=True)
    common = ["--listen", "127.0.0.1", "--port", str(port), "--disable-auto-launch", "--disable-pinned-memory",
              "--input-directory", os.path.join(SCR, "in"), "--output-directory", os.path.join(SCR, "out"),
              "--temp-directory", os.path.join(SCR, "temp"), "--user-directory", udir]
    env = dict(os.environ); env["PYTHONIOENCODING"] = "utf-8"
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy", "PYTHONPATH"):
        env.pop(k, None)
    if kind == "h3":
        env["HF_ENDPOINT"] = "https://hf-mirror.com"
        args = [PY, H3_LAUNCH] + common; cwd = H3_ROOT
    else:
        args = [PY, "-s", PORTABLE + r"\ComfyUI\main.py"] + common + ["--extra-model-paths-config", os.path.join(SCR, "extra_model_paths_diffusion.yaml")]; cwd = PORTABLE
    clog = os.path.join(SCR, "logs", "comfy_%s_%s.log" % (tag, time.strftime("%H%M%S")))
    lf = open(clog, "w", encoding="utf-8")
    t0 = time.time()
    PROC = subprocess.Popen(args, cwd=cwd, stdout=lf, stderr=subprocess.STDOUT, env=env, creationflags=0x08000000)
    log("started comfy (%s) pid %d port %d log %s args=%s" % (kind, PROC.pid, port, clog, " ".join(args[1:])))
    for _ in range(450):
        if up(URL):
            log("comfy up after %.0fs" % (time.time() - t0)); return clog
        if PROC.poll() is not None:
            raise RuntimeError("comfy exited early, see %s" % clog)
        time.sleep(2)
    raise RuntimeError("comfy did not come up")

def stop_comfy():
    global PROC
    if PROC is None:
        return
    try:
        http("/free", {"unload_models": True, "free_memory": True}); time.sleep(3)
    except Exception as e:
        log("free warn %s" % e)
    try:
        PROC.terminate(); PROC.wait(timeout=60)
    except Exception:
        try:
            PROC.kill()
        except Exception:
            pass
    log("comfy terminated")
    PROC = None

class Sampler:
    """nvidia-smi total used (1s) + per-process dedicated/shared GPU memory (perf counters, 2s)."""
    def __init__(self, pid, tag):
        self.pid = pid; self.stop = False; self.total = []
        self.csv = os.path.join(SCR, "logs", "vram_%s.csv" % tag)
        self.th = threading.Thread(target=self.run, daemon=True); self.th.start()
        self.pp = subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(SCR, "vram_sampler.ps1"), "-p", str(pid), "-f", self.csv + ".proc"], creationflags=0x08000000)
    def run(self):
        while not self.stop:
            try:
                out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                                     capture_output=True, text=True, timeout=10).stdout.strip()
                self.total.append((time.strftime("%H:%M:%S"), int(out.splitlines()[0])))
            except Exception:
                pass
            time.sleep(1)
    def finish(self):
        self.stop = True; self.th.join(timeout=5)
        try:
            self.pp.kill()
        except Exception:
            pass
        with open(self.csv, "w", encoding="utf-8") as f:
            for t, v in self.total:
                f.write("%s,%d\n" % (t, v))
        ded = sh = []
        try:
            rows = [l.strip().split(",") for l in open(self.csv + ".proc", encoding="utf-8") if l.strip()]
            ded = [float(r[1]) for r in rows if r[1]]; sh = [float(r[2]) for r in rows if r[2]]
        except Exception:
            pass
        return dict(total_used_peak_mib=max([v for _, v in self.total] or [0]),
                    proc_dedicated_peak_gib=round(max(ded or [0]) / 2**30, 2),
                    proc_shared_peak_gib=round(max(sh or [0]) / 2**30, 2))

# ---------------- graphs ----------------
def img_nodes(g, w, h):
    g["img"] = {"class_type": "LoadImage", "inputs": {"image": IMAGE}}
    g["imgs"] = {"class_type": "ImageScale", "inputs": {"image": ["img", 0], "upscale_method": "bicubic", "width": w, "height": h, "crop": "center"}}
    return ["imgs", 0]

def save_nodes(g, images, prefix, audio=None):
    cv = {"images": images, "fps": 24.0}
    if audio:
        cv["audio"] = audio
    g["cv"] = {"class_type": "CreateVideo", "inputs": cv}
    g["save"] = {"class_type": "SaveVideo", "inputs": {"video": ["cv", 0], "filename_prefix": prefix, "format": "mp4", "codec": "h264"}}

def g_wan(w, h, f, steps, prefix):
    g = {}
    im = img_nodes(g, w, h)
    g["1"] = {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_ti2v_5B_fp16.safetensors", "weight_dtype": "default"}}
    g["2"] = {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}}
    g["3"] = {"class_type": "VAELoader", "inputs": {"vae_name": "wan2.2_vae.safetensors"}}
    g["5"] = {"class_type": "CLIPTextEncode", "inputs": {"text": PROMPT, "clip": ["2", 0]}}
    g["6"] = {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["2", 0]}}
    g["7"] = {"class_type": "ModelSamplingSD3", "inputs": {"model": ["1", 0], "shift": 8.0}}
    g["8"] = {"class_type": "Wan22ImageToVideoLatent", "inputs": {"vae": ["3", 0], "start_image": im, "width": w, "height": h, "length": f, "batch_size": 1}}
    g["9"] = {"class_type": "KSampler", "inputs": {"model": ["7", 0], "positive": ["5", 0], "negative": ["6", 0], "latent_image": ["8", 0],
              "seed": 42, "steps": steps, "cfg": 5.0, "sampler_name": "uni_pc", "scheduler": "simple", "denoise": 1.0}}
    g["10"] = {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}}
    save_nodes(g, ["10", 0], prefix)
    return g

def g_hunyuan(w, h, f, steps, prefix):
    g = {}
    im = img_nodes(g, w, h)
    g["12"] = {"class_type": "UNETLoader", "inputs": {"unet_name": "hunyuanvideo1.5_480p_i2v_step_distilled_fp8_scaled.safetensors", "weight_dtype": "default"}}
    g["11"] = {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "clip_name2": "byt5_small_glyphxl_fp16.safetensors", "type": "hunyuan_video_15", "device": "default"}}
    g["10"] = {"class_type": "VAELoader", "inputs": {"vae_name": "hunyuanvideo15_vae_fp16.safetensors"}}
    g["81"] = {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "sigclip_vision_patch14_384.safetensors"}}
    g["79"] = {"class_type": "CLIPVisionEncode", "inputs": {"clip_vision": ["81", 0], "image": im, "crop": "center"}}
    g["44"] = {"class_type": "CLIPTextEncode", "inputs": {"text": PROMPT, "clip": ["11", 0]}}
    g["93"] = {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["11", 0]}}
    g["78"] = {"class_type": "HunyuanVideo15ImageToVideo", "inputs": {"positive": ["44", 0], "negative": ["93", 0], "vae": ["10", 0], "width": w, "height": h,
               "length": f, "batch_size": 1, "start_image": im, "clip_vision_output": ["79", 0]}}
    g["130"] = {"class_type": "ModelSamplingSD3", "inputs": {"model": ["12", 0], "shift": 7.0}}
    g["129"] = {"class_type": "CFGGuider", "inputs": {"model": ["130", 0], "positive": ["78", 0], "negative": ["78", 1], "cfg": 6.0}}
    g["126"] = {"class_type": "BasicScheduler", "inputs": {"model": ["12", 0], "scheduler": "simple", "steps": steps, "denoise": 1.0}}
    g["127"] = {"class_type": "RandomNoise", "inputs": {"noise_seed": 42}}
    g["128"] = {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}}
    g["125"] = {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["127", 0], "guider": ["129", 0], "sampler": ["128", 0], "sigmas": ["126", 0], "latent_image": ["78", 2]}}
    g["8"] = {"class_type": "VAEDecode", "inputs": {"samples": ["125", 0], "vae": ["10", 0]}}
    save_nodes(g, ["8", 0], prefix)
    return g

def g_ltx(w, h, f, steps, prefix):
    # official two-stage LTX-2.3 I2V (component 40) in API form: half-res stage 1 (8 distilled sigmas) -> x2 spatial upscaler -> stage 2 (3 sigmas)
    ck = "ltx-2.3-22b-dev-fp8.safetensors"
    g = {}
    im = img_nodes(g, w, h)
    g["1"] = {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": ck}}
    g["2"] = {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": "ltx_2.3_22b_distilled_1.1_lora_dynamic_fro09_avg_rank_111_bf16.safetensors", "strength_model": 0.5}}
    g["3"] = {"class_type": "LTXAVTextEncoderLoader", "inputs": {"text_encoder": "gemma_3_12B_it_fp4_mixed.safetensors", "ckpt_name": ck, "device": "default"}}
    g["4"] = {"class_type": "CLIPTextEncode", "inputs": {"text": PROMPT, "clip": ["3", 0]}}
    g["5"] = {"class_type": "CLIPTextEncode", "inputs": {"text": "pc game, console game, video game, cartoon, childish, ugly", "clip": ["3", 0]}}
    g["6"] = {"class_type": "LTXVConditioning", "inputs": {"positive": ["4", 0], "negative": ["5", 0], "frame_rate": 24.0}}
    g["9"] = {"class_type": "ResizeImagesByLongerEdge", "inputs": {"images": im, "longer_edge": 1536}}
    g["10"] = {"class_type": "LTXVPreprocess", "inputs": {"image": ["9", 0], "img_compression": 18}}
    g["11"] = {"class_type": "EmptyLTXVLatentVideo", "inputs": {"width": w // 2, "height": h // 2, "length": f, "batch_size": 1}}
    g["12"] = {"class_type": "LTXVImgToVideoInplace", "inputs": {"vae": ["1", 2], "image": ["10", 0], "latent": ["11", 0], "strength": 0.7, "bypass": False}}
    g["13"] = {"class_type": "LTXVAudioVAELoader", "inputs": {"ckpt_name": ck}}
    g["14"] = {"class_type": "LTXVEmptyLatentAudio", "inputs": {"frames_number": f, "frame_rate": 24, "batch_size": 1, "audio_vae": ["13", 0]}}
    g["15"] = {"class_type": "LTXVConcatAVLatent", "inputs": {"video_latent": ["12", 0], "audio_latent": ["14", 0]}}
    g["16"] = {"class_type": "CFGGuider", "inputs": {"model": ["2", 0], "positive": ["6", 0], "negative": ["6", 1], "cfg": 1.0}}
    g["17"] = {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler_ancestral_cfg_pp"}}
    g["18"] = {"class_type": "ManualSigmas", "inputs": {"sigmas": "1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0"}}
    g["19"] = {"class_type": "RandomNoise", "inputs": {"noise_seed": 42}}
    g["20"] = {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["19", 0], "guider": ["16", 0], "sampler": ["17", 0], "sigmas": ["18", 0], "latent_image": ["15", 0]}}
    g["21"] = {"class_type": "LTXVSeparateAVLatent", "inputs": {"av_latent": ["20", 0]}}
    g["22"] = {"class_type": "LatentUpscaleModelLoader", "inputs": {"model_name": "ltx-2.3-spatial-upscaler-x2-1.1.safetensors"}}
    g["23"] = {"class_type": "LTXVLatentUpsampler", "inputs": {"samples": ["21", 0], "upscale_model": ["22", 0], "vae": ["1", 2]}}
    g["24"] = {"class_type": "LTXVImgToVideoInplace", "inputs": {"vae": ["1", 2], "image": ["10", 0], "latent": ["23", 0], "strength": 1.0, "bypass": False}}
    g["25"] = {"class_type": "LTXVConcatAVLatent", "inputs": {"video_latent": ["24", 0], "audio_latent": ["21", 1]}}
    g["26"] = {"class_type": "LTXVCropGuides", "inputs": {"positive": ["6", 0], "negative": ["6", 1], "latent": ["21", 0]}}
    g["27"] = {"class_type": "CFGGuider", "inputs": {"model": ["2", 0], "positive": ["26", 0], "negative": ["26", 1], "cfg": 1.0}}
    g["28"] = {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler_cfg_pp"}}
    g["29"] = {"class_type": "ManualSigmas", "inputs": {"sigmas": "0.85, 0.7250, 0.4219, 0.0"}}
    g["30"] = {"class_type": "RandomNoise", "inputs": {"noise_seed": 42}}
    g["31"] = {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["30", 0], "guider": ["27", 0], "sampler": ["28", 0], "sigmas": ["29", 0], "latent_image": ["25", 0]}}
    g["32"] = {"class_type": "LTXVSeparateAVLatent", "inputs": {"av_latent": ["31", 0]}}
    g["33"] = {"class_type": "VAEDecodeTiled", "inputs": {"samples": ["32", 0], "vae": ["1", 2], "tile_size": 512, "overlap": 64, "temporal_size": 64, "temporal_overlap": 8}}
    g["34"] = {"class_type": "LTXVAudioVAEDecode", "inputs": {"samples": ["32", 1], "audio_vae": ["13", 0]}}
    save_nodes(g, ["33", 0], prefix, audio=["34", 0])
    return g

def g_h3(w, h, f, steps, prefix):
    g = {}
    im = img_nodes(g, w, h)
    g["1"] = {"class_type": "UNETLoader", "inputs": {"unet_name": "minimax_h3_fl2va_pruned_int8_convrot.safetensors", "weight_dtype": "default"}}
    g["1b"] = {"class_type": "EasyCache", "inputs": {"model": ["1", 0], "reuse_threshold": 0.3, "start_percent": 0.2, "end_percent": 0.9, "verbose": True}}
    g["2"] = {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "type": "minimax", "device": "default"}}
    g["3"] = {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_fp16.safetensors"}}
    g["4"] = {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"}}
    g["5"] = {"class_type": "MiniMaxH3ImageToVideo", "inputs": {"clip": ["2", 0], "vae": ["3", 0], "first_frame": im,
              "prompt": "The scene from <Picture 1>. " + PROMPT + " Audio: soft quiet room tone, faint candle crackle.",
              "width": w, "height": h, "length": f}}
    g["6"] = {"class_type": "BasicGuider", "inputs": {"model": ["1b", 0], "conditioning": ["5", 0]}}
    g["7"] = {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}}
    g["8"] = {"class_type": "BasicScheduler", "inputs": {"model": ["1b", 0], "scheduler": "simple", "steps": steps, "denoise": 1.0}}
    g["9"] = {"class_type": "RandomNoise", "inputs": {"noise_seed": 42}}
    g["10"] = {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["9", 0], "guider": ["6", 0], "sampler": ["7", 0], "sigmas": ["8", 0], "latent_image": ["5", 1]}}
    g["11"] = {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["3", 0]}}
    g["12"] = {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["10", 0], "vae": ["4", 0]}}
    save_nodes(g, ["11", 0], prefix, audio=["12", 0])
    return g

# model -> (instance kind, builder, [(w,h,frames,steps,label), fallback...], timeout_s, notes)
PLAN = {
    "wan":     ("portable", g_wan,     [(704, 1280, 121, 20, "720p"), (480, 832, 121, 20, "480p")], 3600, "uni_pc/simple cfg5 shift8, seed42"),
    "ltx":     ("portable", g_ltx,     [(704, 1280, 121, 11, "720p"), (480, 832, 121, 11, "480p")], 3600, "2-stage: 352x640 8 sigmas + x2 upscaler + 3 sigmas; distilled LoRA 0.5; cfg1; with AV audio"),
    "hunyuan": ("portable", g_hunyuan, [(480, 848, 121, 20, "480p")], 3600, "480p model only; euler/simple cfg6 shift7 (component 31 settings)"),
    "h3":      ("h3",       g_h3,      [(704, 1280, 124, 20, "720p"), (480, 864, 124, 20, "480p")], 5400, "res_multistep/simple, BasicGuider, EasyCache 0.3/0.2/0.9 (documented draft default), with audio"),
}
NEED = {"wan": ["Wan22ImageToVideoLatent", "CreateVideo", "SaveVideo"],
        "ltx": ["LTXVImgToVideoInplace", "LTXVLatentUpsampler", "LTXAVTextEncoderLoader", "LTXVAudioVAELoader", "LTXVCropGuides", "ManualSigmas"],
        "hunyuan": ["HunyuanVideo15ImageToVideo", "CLIPVisionEncode", "DualCLIPLoader"],
        "h3": ["MiniMaxH3ImageToVideo", "EasyCache", "VAEDecodeAudio"]}

def comfy_log_tail(clog, n=60):
    try:
        return open(clog, encoding="utf-8", errors="replace").read().splitlines()[-n:]
    except Exception:
        return []

def run_one(model, cfg, clog):
    kind, builder, w, h, f, steps, label, timeout = cfg
    tag = "%s_%s" % (model, label)
    prefix = "i2v-cmp/%s_%dx%d_%df" % (model, w, h, f)
    g = builder(w, h, f, steps, prefix)
    with open(os.path.join(SCR, "logs", "graph_%s.json" % tag), "w", encoding="utf-8") as fh:
        json.dump(g, fh, indent=1, ensure_ascii=False)
    try:
        http("/free", {"unload_models": True, "free_memory": True}); time.sleep(3)
    except Exception:
        pass
    st = jget("/system_stats")
    pre = dict(ram_free_gb=round(st["system"]["ram_free"] / 2**30, 1), vram_free_gb=round(st["devices"][0]["vram_free"] / 2**30, 1))
    log("%s pre-run %s" % (tag, pre))
    smp = Sampler(PROC.pid, tag)
    t0 = time.time()
    rec = dict(model=model, label=label, width=w, height=h, frames=f, steps=steps, fps=24, pre=pre)
    try:
        resp = json.loads(http("/prompt", {"prompt": g, "client_id": str(uuid.uuid4())}).decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        rec.update(ok=False, error="prompt rejected: " + body[:2000]); smp.finish(); log("%s REJECTED %s" % (tag, body[:2000])); return rec
    pid = resp["prompt_id"]; log("%s queued %s" % (tag, pid))
    entry = None
    while True:
        time.sleep(10)
        el = time.time() - t0
        if PROC.poll() is not None:
            rec.update(ok=False, error="comfy process died (exit %s) — likely OOM/crash" % PROC.returncode); break
        try:
            hist = jget("/history/%s" % pid, timeout=30)
        except Exception as e:
            log("%s history err %s" % (tag, e)); continue
        if pid in hist:
            entry = hist[pid]; break
        if int(el) % 120 < 10:
            log("%s running %.0fs" % (tag, el))
        if el > timeout:
            rec.update(ok=False, error="timeout %ds" % timeout)
            try:
                http("/interrupt", {})
            except Exception:
                pass
            break
    rec["elapsed_s"] = round(time.time() - t0, 1)
    rec.update(smp.finish())
    if entry is not None:
        status = entry.get("status", {})
        rec["ok"] = status.get("status_str") == "success"
        errs = [m for m in status.get("messages", []) if m and m[0] == "execution_error"]
        if errs:
            e = errs[0][1]
            rec["error"] = ("%s: %s" % (e.get("node_type"), e.get("exception_message", "")))[:1500]
        files = []
        for nid, out in entry.get("outputs", {}).items():
            for k in ("images", "videos", "gifs", "animated"):
                for it in out.get(k, []) if isinstance(out.get(k), list) else []:
                    if isinstance(it, dict) and it.get("filename"):
                        files.append(os.path.join(SCR, "out", it.get("subfolder", ""), it["filename"]))
        rec["files"] = files
    tail = comfy_log_tail(clog, 400)
    m = [l for l in tail if "Prompt executed in" in l]
    rec["comfy_exec_line"] = m[-1].strip() if m else None
    rec["comfy_flags"] = sorted(set(l.strip()[:160] for l in tail if re.search(r"(?i)out of memory|OOM|loaded partially|lowvram|offload|tiled", l)))[:15]
    rec["oom"] = bool(re.search(r"(?i)out of memory|OutOfMemory|allocation", (rec.get("error") or "") + " ".join(rec["comfy_flags"])))
    log("%s RESULT %s" % (tag, json.dumps(rec, ensure_ascii=False)))
    return rec

def main():
    os.makedirs(os.path.join(SCR, "logs"), exist_ok=True)
    models = sys.argv[1:] or ["wan", "ltx", "hunyuan", "h3"]
    results = json.load(open(RESF, encoding="utf-8")) if os.path.exists(RESF) else []
    log("=== START models=%s pid=%d" % (models, os.getpid()))
    for model in models:
        kind, builder, tries, timeout, notes = PLAN[model]
        acquire_lock(model)
        clog = None
        try:
            t0 = time.time()
            clog = start_comfy(kind, model)
            startup = round(time.time() - t0, 1)
            missing = []
            for cls in NEED[model]:
                try:
                    if not jget("/object_info/%s" % cls):
                        missing.append(cls)
                except Exception:
                    missing.append(cls)
            if missing:
                rec = dict(model=model, ok=False, error="missing nodes: %s" % missing, startup_s=startup, notes=notes)
                log("%s MISSING NODES %s" % (model, missing)); results.append(rec)
            else:
                for (w, h, f, steps, label) in tries:
                    rec = run_one(model, (kind, builder, w, h, f, steps, label, timeout), clog)
                    rec.update(startup_s=startup, notes=notes, instance=kind, comfy_log=clog)
                    results.append(rec)
                    json.dump(results, open(RESF, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
                    if rec.get("ok"):
                        break
                    if PROC is None or PROC.poll() is not None:
                        log("%s instance died; restarting for fallback" % model)
                        stop_comfy(); clog = start_comfy(kind, model)
        except Exception as e:
            log("%s EXCEPTION %r" % (model, e)); results.append(dict(model=model, ok=False, error="runner exception: %r" % e, comfy_log=clog))
        finally:
            stop_comfy()
            release_lock()
            log("yield 60s so other waiting GPU jobs can take the lock")
            time.sleep(60)
            json.dump(results, open(RESF, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    log("=== END ok=%d fail=%d" % (sum(1 for r in results if r.get("ok")), sum(1 for r in results if not r.get("ok"))))

if __name__ == "__main__":
    main()
