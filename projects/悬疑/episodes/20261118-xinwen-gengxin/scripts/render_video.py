from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
from PIL import Image

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[3]
FPS = 24
WIDTH, HEIGHT = 1920, 1080
PLAN = json.loads((EP / "storyboard/SHOT_PLAN-v1.json").read_text(encoding="utf-8"))
OUT = EP / "video/final/悬疑_新闻更新前_正文_v1.mp4"
CLIPS = EP / "video/clips"
CLIPS.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location("camera_motion", ROOT / "shared/camera-motion/camera_motion.py")
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)

def build_plan():
    shots = []
    for source in PLAN["shots"]:
        image = EP / "image/final" / f"{source['id']}.png"
        if not image.exists():
            raise FileNotFoundError(image)
        with Image.open(image) as im:
            width, height = im.size
        view_h = min(1.0, width / (height * (16 / 9)))
        view_w = view_h * height * (16 / 9) / width
        start = [(1 - view_w) / 2, (1 - view_h) / 2, view_w, view_h]
        if source["motion"] == "affine_push":
            end = [start[0] + 0.05 * view_w, start[1] + 0.05 * view_h, 0.90 * view_w, 0.90 * view_h]
        else:
            end = start
        shots.append({
            "id": source["id"], "source": str(image), "duration_s": source["frames"] / FPS,
            "start_view": start, "end_view": end, "curve": {"type": "ramped_linear", "ramp_s": 0.7},
            "required_regions": [[0.12, 0.12, 0.76, 0.76]], "frames": source["frames"],
            "start_frame": source["start_frame"], "end_frame": source["end_frame"],
            "source_sha256": cm.digest(image), "motion": source["motion"], "fact": source["fact"],
        })
    plan = {"schema_version": 1, "backend": "affine", "output": {"width": WIDTH, "height": HEIGHT, "fps": FPS},
            "transition_s": 0, "shots": shots}
    path = EP / "video/motion_plan.json"
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    timeline = {"fps": FPS, "frames": PLAN["frames"], "duration_s": PLAN["duration_s"],
                "note": "估算时间轴，未对真实人声校准", "shots": PLAN["shots"]}
    (EP / "video/timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "shared/camera-motion/validate_plan.py"), str(path)], check=True)
    cm.load_plan(path)
    return plan

def render(shot):
    out = CLIPS / f"{shot['id']}.mp4"
    report_path = CLIPS / f"{shot['id']}.json"
    if out.exists() and report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("source_sha256") == shot["source_sha256"] and int(report.get("frames", 0)) == shot["frames"]:
            return out
    count = shot["frames"]
    started = time.time()
    if shot["motion"] == "static":
        src = cm.prepare_source(shot["source"], shot, WIDTH, HEIGHT)
        h, w = src.shape[:2]
        matrix = cm.sample_matrix(shot["start_view"], w, h, WIDTH, HEIGHT)
        frame = cv2.warpAffine(src, matrix, (WIDTH, HEIGHT), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP,
                               borderMode=cv2.BORDER_REPLICATE)
        still = CLIPS / f"{shot['id']}-static.png"
        Image.fromarray(frame).save(still)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-i", str(still),
                        "-frames:v", str(count), "-an", "-c:v", "libx264", "-preset", "fast", "-threads", "4",
                        "-crf", "18", "-pix_fmt", "yuv420p", str(out)], check=True)
        still.unlink()
        motion_report = {"backend": "affine-static", "render_fps": FPS, "matrix": matrix.tolist()}
    else:
        moving = copy.deepcopy(shot)
        moving["frames"] = round(shot["duration_s"] * 60)
        moving["duration_s"] = moving["frames"] / 60
        moving["span_s"] = (moving["frames"] - 1) / 60
        intermediate = CLIPS / f"{shot['id']}-60.mp4"
        matrices, motion_report = cm.render_affine(moving, intermediate, {"width": WIDTH, "height": HEIGHT, "fps": 60})
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(intermediate),
                        "-vf", f"tpad=stop_mode=clone:stop_duration=0.05,fps={FPS}", "-frames:v", str(count), "-an",
                        "-c:v", "libx264", "-preset", "fast", "-threads", "4", "-crf", "18", "-pix_fmt", "yuv420p",
                        str(out)], check=True)
        intermediate.unlink()
        motion_report.update(render_fps=60, matrix_start=matrices[0], matrix_end=matrices[-1])
    probe = cm.probe(out)["streams"][0]
    if int(probe.get("nb_frames", 0)) != count:
        raise RuntimeError(f"{shot['id']} frames={probe.get('nb_frames')} expected={count}")
    motion_report.update(id=shot["id"], frames=count, duration_s=count / FPS, source_sha256=shot["source_sha256"],
                         video_sha256=cm.digest(out), elapsed_s=round(time.time() - started, 2))
    report_path.write_text(json.dumps(motion_report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("RENDER", shot["id"], count, motion_report["elapsed_s"], flush=True)
    return out

def assemble(plan):
    free = shutil.disk_usage(EP).free
    if free < 12 * 1024**3:
        raise RuntimeError("disk preflight less than 12GB")
    (EP / "logs/encoding-preflight.json").write_text(json.dumps({
        "free_bytes": free, "estimated_outputs_bytes": 1024**3, "minimum_bytes": 12 * 1024**3, "pass": True,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    concat = CLIPS / "concat.txt"
    concat.write_text("".join("file '" + str(CLIPS / f"{shot['id']}.mp4").replace("'", "'\\''") + "'\n" for shot in plan["shots"]), encoding="utf-8")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
                    "-vf", "eq=saturation=0.96:contrast=1.015,colorbalance=bs=0.008:rs=-0.004", "-an", "-sn",
                    "-c:v", "libx264", "-preset", "medium", "-threads", "6", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-r", str(FPS), "-movflags", "+faststart", str(OUT)], check=True)
    probe = cm.probe(OUT)
    (EP / "qa/final-ffprobe.json").write_text(json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8")
    print("FINAL", OUT, flush=True)

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    plan = build_plan()
    if mode == "plan":
        return
    if mode == "partial":
        plan["shots"] = [shot for shot in plan["shots"] if (EP / "image/final" / f"{shot['id']}.png").exists()]
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(render, plan["shots"]))
    if mode != "partial":
        assemble(plan)

if __name__ == "__main__":
    main()
