"""Render the silent body, time-align the SRT, and run delivery gates."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from PIL import Image

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[3]
PYTHON = sys.executable
PLAN = json.loads((EP / "storyboard/SHOT_PLAN-v1.json").read_text())
FINAL_DIR = EP / "video/final"
FINAL_DIR.mkdir(parents=True, exist_ok=True)
FINAL = FINAL_DIR / "悬疑_纸替_正文_v1.mp4"
SRT = FINAL.with_suffix(".srt")
RUN = EP / "video/render-v1"
RUN.mkdir(parents=True, exist_ok=True)
CLIPS = EP / "video/clips-v1"
CLIPS.mkdir(parents=True, exist_ok=True)

SPEC = importlib.util.spec_from_file_location("camera_motion", ROOT / "shared/camera-motion/camera_motion.py")
cm = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cm
SPEC.loader.exec_module(cm)


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def motion_plan() -> dict:
    shots = []
    for source in PLAN["shots"]:
        image = EP / "image/final" / f"{source['id']}.png"
        if not image.exists():
            raise FileNotFoundError(image)
        with Image.open(image) as frame:
            source_aspect = frame.width / frame.height
        base_h = source_aspect / (1920 / 1080)
        frames24 = int(source["frames"])
        frames60 = round(frames24 * 60 / PLAN["fps"])
        is_static = source["motion"] == "static"
        start = [0.0, (1 - base_h) / 2, 1.0, base_h]
        end = start.copy()
        if not is_static:
            end_h = 0.88 * base_h
            end = [0.06, (1 - end_h) / 2, 0.88, end_h]
        shots.append({
            "id": source["id"], "source": str(image), "frames": frames60,
            "duration_s": frames60 / 60, "start_view": start,
            "end_view": end, "curve": {"type": "ramped_linear", "ramp_s": 0.7},
            "required_regions": [[0.1, 0.15, 0.8, 0.7]],
            "frames24": frames24, "cue": source["cue"], "fact": source["fact"],
        })
    config = {"schema_version": 1, "backend": "affine",
              "output": {"width": 1920, "height": 1080, "fps": 60},
              "transition_s": 0, "shots": shots}
    path = EP / "video/motion_plan-v1.json"
    write_json(path, config)
    return {"config": config, "path": path}


def render() -> None:
    plan = motion_plan()
    subprocess.run([PYTHON, str(ROOT / "shared/camera-motion/validate_plan.py"), str(plan["path"])], check=True)
    loaded = cm.load_plan(plan["path"])
    for shot in loaded["shots"]:
        source = EP / "image/final" / f"{shot['id']}.png"
        native = RUN / f"{shot['id']}-60.mp4"
        out = CLIPS / f"{shot['id']}.mp4"
        # A repaired image must invalidate both cached render stages.
        if native.exists() and source.stat().st_mtime_ns > native.stat().st_mtime_ns:
            native.unlink()
            out.unlink(missing_ok=True)
        if not native.exists():
            mats, timing = cm.render_affine(shot, native, plan["config"]["output"])
            cm.write_trajectory(RUN / f"{shot['id']}-trajectory.json", shot, mats, "affine", timing["source_size_rendered"])
        if not out.exists():
            subprocess.run([
                "ffmpeg", "-v", "error", "-y", "-i", str(native), "-vf",
                f"tpad=stop_mode=clone:stop_duration=0.05,fps=24", "-frames:v", str(shot["frames24"]),
                "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", str(out)
            ], check=True)
        probe = cm.probe(out)["streams"][0]
        if int(probe["nb_frames"]) != shot["frames24"] or (probe["width"], probe["height"]) != (1920, 1080):
            raise RuntimeError(f"Clip mismatch: {shot['id']} {probe}")
        print("RENDERED", shot["id"], shot["frames24"], flush=True)

    concat = CLIPS / "concat.txt"
    concat.write_text("".join(f"file '{CLIPS / (s['id'] + '.mp4')}'\n" for s in loaded["shots"]))
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-map", "0:v:0", "-an", "-sn", "-frames:v", str(PLAN["frames"]), "-c:v", "libx264",
        "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "24",
        "-movflags", "+faststart", str(FINAL)
    ], check=True)


def subtitles() -> None:
    source = (EP / "qa/body-sentences.srt").read_text()
    last = PLAN["duration"]
    parsed = re.sub(r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})",
                    lambda m: f"{timestamp(to_seconds(m.group(1)) * last / source_end(source))} --> "
                              f"{timestamp(min(last, to_seconds(m.group(2)) * last / source_end(source)))}", source)
    sentence = EP / "video/srt/sentences-v1.srt"
    sentence.parent.mkdir(parents=True, exist_ok=True)
    sentence.write_text(parsed)
    subprocess.run([
        PYTHON, str(ROOT / "shared/workflows/subtitles/split_srt.py"), str(sentence),
        "--out", str(SRT), "--cues-json", str(EP / "video/srt/cues-v1.json"),
        "--report", str(EP / "qa/srt-split-v1.json"), "--allow-word-split"
    ], check=True)
    checked = subprocess.run([PYTHON, str(ROOT / "shared/workflows/subtitles/check_srt.py"), str(SRT),
                              "--json"], check=True, capture_output=True, text=True)
    (EP / "qa/srt-check-v1.json").write_text(checked.stdout)


def to_seconds(value: str) -> float:
    h, m, rest = value.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def timestamp(seconds: float) -> str:
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def source_end(text: str) -> float:
    times = re.findall(r"\d{2}:\d{2}:\d{2},\d{3} --> (\d{2}:\d{2}:\d{2},\d{3})", text)
    return to_seconds(times[-1])


def quality() -> None:
    probe = cm.probe(FINAL)
    write_json(EP / "qa/final-ffprobe.json", probe)
    delivery = EP / "qa/delivery.json"
    subprocess.run([PYTHON, str(ROOT / "shared/workflows/body-only/check_delivery.py"),
                    "--video", str(FINAL), "--srt", str(SRT), "--json", str(delivery)], check=True)
    stream = next(s for s in probe["streams"] if s["codec_type"] == "video")
    if int(stream["nb_frames"]) != PLAN["frames"] or stream["avg_frame_rate"] != "24/1":
        raise RuntimeError("Final frame count or frame rate mismatch")
    subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(FINAL), "-map", "0:v:0", "-an", "-f", "null", "-"], check=True)

    stat = EP / "qa/pixel-stats.txt"
    with stat.open("w") as out:
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(FINAL), "-vf",
                        f"signalstats,metadata=print:file={stat}", "-an", "-f", "null", "-"],
                       stdout=subprocess.DEVNULL, stderr=out, check=True)
    report = {"frames": int(stream["nb_frames"]), "fps": stream["avg_frame_rate"],
              "size": [stream["width"], stream["height"]], "audio_streams": 0,
              "subtitle_streams": 0, "all_frames_decode": True,
              "duration_s": int(stream["nb_frames"]) / 24,
              "srt": str(SRT.relative_to(EP)), "video_sha256": hashlib.sha256(FINAL.read_bytes()).hexdigest(),
              "source_frames": len(PLAN["shots"]), "estimated_timing_not_voice_synced": True}
    write_json(EP / "qa/delivery-summary.json", report)


if __name__ == "__main__":
    render()
    subtitles()
    quality()
