import json, uuid, urllib.request, pathlib, time, shutil
API = "http://127.0.0.1:8188"
OUT_ROOT = pathlib.Path(r"E:\program\1project\video\shared\project-tools\production\comfyui-output")
IN_DIR = pathlib.Path(r"E:\program\1project\video\shared\project-tools\production\comfyui-input")
PORTABLE_IN = pathlib.Path(r"E:\program\1project\video\shared\runtime\comfy\installs\portable\ComfyUI\input")

def get(url):
    with urllib.request.urlopen(url, timeout=90) as r:
        return json.loads(r.read().decode())

def post(url, data):
    req = urllib.request.Request(
        url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())

def wait(pid, label):
    for i in range(400):
        time.sleep(2)
        h = get(API + f"/history/{pid}")
        if pid in h:
            print(label, "finished", h[pid].get("status", {}).get("status_str"))
            imgs = []
            for _nid, o in (h[pid].get("outputs") or {}).items():
                for im in o.get("images") or []:
                    print(label, "IMAGE", im)
                    imgs.append(im)
            for m in (h[pid].get("status", {}).get("messages") or [])[-6:]:
                if m[0] == "execution_error":
                    b = m[1]
                    print(label, "ERR", b.get("node_type"), (b.get("exception_message") or "")[:800])
            return imgs
        if i % 10 == 0:
            print(label, "waiting", i * 2)
    raise TimeoutError(label)

def stage_in(name, src):
    shutil.copy2(src, IN_DIR / name)
    try:
        PORTABLE_IN.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, PORTABLE_IN / name)
    except Exception as e:
        print("portable copy skip", e)

stage_in(
    "chengwu_identity_v4.png",
    r"E:\program\1project\video\shared\project-tools\production\comfyui-output\character-lock\pulid-v4-cleanface_00001_.png",
)
stage_in(
    "chengwu_pose_halfbody.png",
    r"E:\program\1project\video\shared\project-tools\production\character-library\chengwu-v1\halfbody-start-v1.png",
)

info = get(API + "/object_info")
ckpt = next(
    c
    for c in info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    if "animagine" in c.lower()
)
pulid = next(
    p for p in info["PulidModelLoader"]["input"]["required"]["pulid_file"][0] if "pulid" in p.lower()
)
cn = "xinsir-controlnet-canny-sdxl-1.0-v2.safetensors"
canny_type = "CannyEdgePreprocessor" if "CannyEdgePreprocessor" in info else "Canny"
canny_in = {"image": ["3", 0]}
if canny_type == "CannyEdgePreprocessor":
    canny_in.update({"low_threshold": 100, "high_threshold": 200, "resolution": 1024})
else:
    canny_in.update({"low_threshold": 0.4, "high_threshold": 0.8})

pos_pose = (
    "masterpiece, best quality, anime screencap, soft cel shading, solo, 1girl, adult Chinese woman, pale skin, "
    "dark slate blue bob hair, bangs, brown eyes, black choker, teal off-shoulder top, standing facing viewer, "
    "arms at sides, upper body to hips, hallway"
)
neg = (
    "lowres, worst quality, bad anatomy, bad hands, jpeg artifacts, watermark, blurry, multiple people, "
    "photorealistic, 3d, child, loli, bald, bald spot, weird hair, red eyes, cargo pants, zip-up jacket, blue hoodie"
)
pos_lock = (
    "masterpiece, best quality, anime screencap, soft cel shading, muted cool colors, solo, 1girl, adult Chinese woman, "
    "pale clean skin, narrow oval face, dark slate blue bob hair, straight bangs covering one eye, brown eyes, "
    "black thin choker, teal off-shoulder top, collarbones, clean hairline, looking at viewer, standing pose, soft side lighting"
)

s1 = {
    "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": ckpt}},
    "2": {"class_type": "LoadImage", "inputs": {"image": "chengwu_identity_v4.png"}},
    "3": {"class_type": "LoadImage", "inputs": {"image": "chengwu_pose_halfbody.png"}},
    "4": {"class_type": "PulidModelLoader", "inputs": {"pulid_file": pulid}},
    "5": {"class_type": "PulidInsightFaceLoader", "inputs": {"provider": "CUDA"}},
    "6": {"class_type": "PulidEvaClipLoader", "inputs": {}},
    "7": {
        "class_type": "ApplyPulid",
        "inputs": {
            "model": ["1", 0],
            "pulid": ["4", 0],
            "eva_clip": ["6", 0],
            "face_analysis": ["5", 0],
            "image": ["2", 0],
            "method": "fidelity",
            "weight": 0.85,
            "start_at": 0.0,
            "end_at": 1.0,
        },
    },
    "8": {"class_type": canny_type, "inputs": canny_in},
    "9": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": cn}},
    "11": {"class_type": "CLIPTextEncode", "inputs": {"text": pos_pose, "clip": ["1", 1]}},
    "12": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["1", 1]}},
    "13": {
        "class_type": "ControlNetApplyAdvanced",
        "inputs": {
            "positive": ["11", 0],
            "negative": ["12", 0],
            "control_net": ["9", 0],
            "image": ["8", 0],
            "strength": 0.55,
            "start_percent": 0.0,
            "end_percent": 0.80,
        },
    },
    "14": {"class_type": "VAEEncode", "inputs": {"pixels": ["2", 0], "vae": ["1", 2]}},
    "15": {
        "class_type": "KSampler",
        "inputs": {
            "seed": 202609190,
            "steps": 28,
            "cfg": 4.5,
            "sampler_name": "dpmpp_2m",
            "scheduler": "sgm_uniform",
            "denoise": 0.70,
            "model": ["7", 0],
            "positive": ["13", 0],
            "negative": ["13", 1],
            "latent_image": ["14", 0],
        },
    },
    "16": {"class_type": "VAEDecode", "inputs": {"samples": ["15", 0], "vae": ["1", 2]}},
    "17": {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "keyframe/51e-stage1-pose", "images": ["16", 0]},
    },
}

resp = post(API + "/prompt", {"prompt": s1, "client_id": str(uuid.uuid4())})
print("s1 queued", resp.get("prompt_id"), resp.get("error"))
assert resp.get("prompt_id")
imgs = wait(resp["prompt_id"], "s1")
assert imgs
src = OUT_ROOT / imgs[0].get("subfolder", "") / imgs[0]["filename"]
if not src.exists():
    src = OUT_ROOT / "keyframe" / imgs[0]["filename"]
print("stage1", src, src.exists())
stage1_name = "chengwu_51e_stage1.png"
shutil.copy2(src, IN_DIR / stage1_name)
try:
    shutil.copy2(src, PORTABLE_IN / stage1_name)
except Exception as e:
    print(e)

s2 = {
    "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": ckpt}},
    "2": {"class_type": "LoadImage", "inputs": {"image": "chengwu_identity_v4.png"}},
    "3": {"class_type": "LoadImage", "inputs": {"image": stage1_name}},
    "4": {"class_type": "PulidModelLoader", "inputs": {"pulid_file": pulid}},
    "5": {"class_type": "PulidInsightFaceLoader", "inputs": {"provider": "CUDA"}},
    "6": {"class_type": "PulidEvaClipLoader", "inputs": {}},
    "7": {
        "class_type": "ApplyPulid",
        "inputs": {
            "model": ["1", 0],
            "pulid": ["4", 0],
            "eva_clip": ["6", 0],
            "face_analysis": ["5", 0],
            "image": ["2", 0],
            "method": "fidelity",
            "weight": 1.0,
            "start_at": 0.0,
            "end_at": 1.0,
        },
    },
    "11": {"class_type": "CLIPTextEncode", "inputs": {"text": pos_lock, "clip": ["1", 1]}},
    "12": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["1", 1]}},
    "14": {"class_type": "VAEEncode", "inputs": {"pixels": ["3", 0], "vae": ["1", 2]}},
    "15": {
        "class_type": "KSampler",
        "inputs": {
            "seed": 202609191,
            "steps": 28,
            "cfg": 4.0,
            "sampler_name": "dpmpp_2m",
            "scheduler": "sgm_uniform",
            "denoise": 0.40,
            "model": ["7", 0],
            "positive": ["11", 0],
            "negative": ["12", 0],
            "latent_image": ["14", 0],
        },
    },
    "16": {"class_type": "VAEDecode", "inputs": {"samples": ["15", 0], "vae": ["1", 2]}},
    "17": {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "keyframe/51e-twostage", "images": ["16", 0]},
    },
}

comp = pathlib.Path(r"E:\program\1project\video\shared\project-tools\workflows\components\51e-shot-keyframe-twostage-v1.api.json")
comp.write_text(json.dumps({"stage1": s1, "stage2": s2}, ensure_ascii=False, indent=2), encoding="utf-8")
resp = post(API + "/prompt", {"prompt": s2, "client_id": str(uuid.uuid4())})
print("s2 queued", resp.get("prompt_id"), resp.get("error"), resp.get("node_errors"))
assert resp.get("prompt_id")
print("DONE", wait(resp["prompt_id"], "s2"))
