from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[3]
VIDEO = EP / "video/final/悬疑_雪夜林屋_正文_v1.mp4"
SRT = VIDEO.with_suffix(".srt")
QA = EP / "qa"


def run(args: list[str]) -> str:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout


probe = json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(VIDEO)]))
assert len(probe["streams"]) == 1
stream = probe["streams"][0]
assert stream["codec_type"] == "video" and stream["codec_name"] == "h264"
assert (stream["width"], stream["height"], stream["pix_fmt"], stream["avg_frame_rate"]) == (1920, 1080, "yuv420p", "24/1")
frames = int(stream["nb_frames"])

stats_path = QA / "signalstats.txt"
run(["ffmpeg", "-v", "error", "-xerror", "-i", str(VIDEO), "-vf", f"signalstats,metadata=mode=print:file={stats_path}", "-an", "-f", "null", "-"])
records = []
current = None
for line in stats_path.read_text().splitlines():
    if line.startswith("frame:"):
        if current:
            records.append(current)
        current = {"frame": int(re.search(r"frame:(\d+)", line).group(1))}
    elif "=" in line and current is not None:
        key, value = line.split("=", 1)
        if key.startswith("lavfi.signalstats."):
            try:
                current[key.rsplit(".", 1)[1]] = float(value)
            except ValueError:
                pass
if current:
    records.append(current)
assert len(records) == frames, (len(records), frames)


def intervals(predicate):
    result, start = [], None
    for i, row in enumerate(records + [{}]):
        hit = i < len(records) and predicate(row)
        if hit and start is None:
            start = i
        elif not hit and start is not None:
            if i - start >= 24:
                result.append({"start_frame": start, "end_frame_exclusive": i, "duration_s": (i - start) / 24})
            start = None
    return result


black = intervals(lambda row: row["YAVG"] <= 24 and row["YMAX"] <= 32)
white = intervals(lambda row: row["YAVG"] >= 230 and row["YMIN"] >= 220)
timestamps = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_frames", "-show_entries", "frame=best_effort_timestamp_time", "-of", "json", str(VIDEO)]))["frames"]
pts = [float(row["best_effort_timestamp_time"]) for row in timestamps]
assert len(pts) == frames
step_error = max(abs((b - a) - 1 / 24) for a, b in zip(pts, pts[1:]))

subprocess.run([sys.executable, str(ROOT / "shared/workflows/body-only/check_delivery.py"), "--video", str(VIDEO), "--srt", str(SRT), "--json", str(QA / "delivery.json")], check=True)
subprocess.run([sys.executable, str(ROOT / "shared/workflows/subtitles/check_srt.py"), str(SRT), "--json"], check=True, stdout=(QA / "srt-check.json").open("w"))
strip = lambda value: "".join(char for char in value if char.isalnum())
source_text = "".join(line.split("　", 1)[1] for line in (EP / "story/script-body-v1.md").read_text().splitlines() if re.match(r"^S\d{2}　", line))
srt_text = "".join(line for line in SRT.read_text().splitlines() if line.strip() and "-->" not in line and not line.strip().isdigit())
assert strip(source_text) == strip(srt_text), "SRT narration differs from locked script"

intro = sorted((EP / "image/intro/v1").glob("*.png"))
assert len(intro) == 2
for path in intro:
    dimensions = run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)])
    assert re.search(r"pixelWidth: 1920\s+pixelHeight: 1080", dimensions), dimensions

report = {
    "passed": not black and not white and step_error < 0.00001,
    "decoded_frames": len(records),
    "expected_frames": frames,
    "fps": 24,
    "duration_s": frames / 24,
    "full_resolution_every_frame_decode": True,
    "black_intervals_ge_1s": black,
    "white_intervals_ge_1s": white,
    "cfr_max_step_error_s": step_error,
    "video_sha256": hashlib.sha256(VIDEO.read_bytes()).hexdigest(),
    "srt_sha256": hashlib.sha256(SRT.read_bytes()).hexdigest(),
    "intro_images": [str(p.relative_to(EP)) for p in intro],
    "intro_size": "1920x1080",
    "audio_streams": 0,
    "subtitle_streams": 0,
    "narration_exact_match": True,
}
(QA / "pixel_scan.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
(QA / "video.json").write_text(json.dumps(probe, ensure_ascii=False, indent=2) + "\n")
assert report["passed"], report
print(json.dumps(report, ensure_ascii=False, indent=2))
