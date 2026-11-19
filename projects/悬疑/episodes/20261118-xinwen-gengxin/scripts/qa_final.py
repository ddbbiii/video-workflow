from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[3]
VIDEO = EP / "video/final/悬疑_新闻更新前_正文_v1.mp4"
SRT = VIDEO.with_suffix(".srt")
QA = EP / "qa"
FPS = 24

def run(args, output=None):
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    if output:
        Path(output).write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout

def ts_seconds(match):
    h, m, s, ms = match.groups()
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000

def main():
    QA.mkdir(parents=True, exist_ok=True)
    probe = json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(VIDEO)]))
    streams = probe["streams"]
    if len(streams) != 1 or streams[0].get("codec_type") != "video":
        raise AssertionError(f"expected one video stream only, got {[s.get('codec_type') for s in streams]}")
    stream = streams[0]
    frames = int(stream["nb_frames"])
    if (stream.get("width"), stream.get("height"), stream.get("avg_frame_rate"), stream.get("pix_fmt")) != (1920, 1080, "24/1", "yuv420p"):
        raise AssertionError("video stream format differs from the 1920x1080/24fps/yuv420p contract")
    if frames != int(json.loads((EP / "storyboard/SHOT_PLAN-v1.json").read_text())["frames"]):
        raise AssertionError("final frame count differs from locked timeline")

    lock = json.loads((EP / "story/LOCK.json").read_text(encoding="utf-8"))
    if hashlib.sha256((EP / "story" / lock["script"]).read_bytes()).hexdigest() != lock["sha256"]:
        raise AssertionError("locked narration hash changed")

    metadata_file = QA / "pixel-stats.txt"
    run(["ffmpeg", "-v", "error", "-xerror", "-i", str(VIDEO), "-vf",
         f"signalstats,metadata=mode=print:file={metadata_file}", "-an", "-f", "null", "-"], QA / "decode.log")
    records, current = [], None
    for line in metadata_file.read_text(encoding="utf-8", errors="replace").splitlines():
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
    if len(records) != frames:
        raise AssertionError(f"decoded {len(records)} frame metrics for {frames} frames")

    def intervals(predicate):
        result, start = [], None
        for i, row in enumerate(records + [{}]):
            matched = i < len(records) and predicate(row)
            if matched and start is None:
                start = i
            elif not matched and start is not None:
                if i - start >= FPS:
                    result.append({"start_frame": start, "end_frame": i, "duration_s": (i - start) / FPS})
                start = None
        return result

    black = intervals(lambda r: r.get("YAVG", 255) <= 24 and r.get("YMAX", 255) <= 32)
    white = intervals(lambda r: r.get("YAVG", 0) >= 230 and r.get("YMIN", 0) >= 220)
    for kind, filters in (("black", ["blackdetect=d=1:pix_th=0.10:pic_th=0.98"]),
                          ("white", ["negate", "blackdetect=d=1:pix_th=0.10:pic_th=0.98"])):
        result = subprocess.run(["ffmpeg", "-v", "info", "-xerror", "-i", str(VIDEO), "-vf", ",".join(filters),
                                 "-an", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8")
        (QA / f"{kind}-98pct.log").write_text(result.stderr, encoding="utf-8")
        if result.returncode:
            raise RuntimeError(result.stderr)
        found = [{"start_s": float(a), "end_s": float(b), "duration_s": float(c)}
                 for a, b, c in re.findall(r"black_start:([\d.]+) black_end:([\d.]+) black_duration:([\d.]+)", result.stderr)
                 if float(c) >= 1]
        if kind == "black":
            black.extend(found)
        else:
            white.extend(found)

    frame_json = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_frames",
                                 "-show_entries", "frame=best_effort_timestamp_time", "-of", "json", str(VIDEO)]))
    pts = [float(frame["best_effort_timestamp_time"]) for frame in frame_json["frames"]]
    if len(pts) != frames:
        raise AssertionError("ffprobe decoded frame count mismatch")
    max_step = max(abs((b - a) - 1 / FPS) for a, b in zip(pts, pts[1:]))

    srt_text = SRT.read_text(encoding="utf-8-sig")
    srt_cues = re.findall(r"\d+\s*\n(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\s*\n([^\n]+)", srt_text)
    if not srt_cues:
        raise AssertionError("no SRT cues parsed")
    if ts_seconds(re.match(r"(\d+):(\d+):(\d+),(\d+)", srt_cues[0][0])) != 0:
        raise AssertionError("SRT must start at zero")
    clean = lambda text: "".join(ch for ch in text if ch.isalnum())
    script = (EP / "story/script-v1.md").read_text(encoding="utf-8")
    narration = "".join(re.findall(r"^S\d{2}\s+(.+)$", script, re.M))
    subtitle_text = "".join(cue[2] for cue in srt_cues)
    if clean(subtitle_text) != clean(narration):
        raise AssertionError("SRT text does not match the locked narration")

    report = {
        "pass": not black and not white and max_step < 0.00001,
        "frames": frames, "fps": FPS, "duration_s": frames / FPS, "decoded_frames": len(records),
        "pixel_scan": "every frame: signalstats plus 98%-coverage black/white detection",
        "black_intervals_ge_1s": black, "white_intervals_ge_1s": white,
        "cfr_max_step_error_s": max_step, "narration_exact_match": True,
        "video_sha256": hashlib.sha256(VIDEO.read_bytes()).hexdigest(),
        "srt_sha256": hashlib.sha256(SRT.read_bytes()).hexdigest(),
    }
    (QA / "pixel-and-content-v1.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if not report["pass"]:
        raise AssertionError(json.dumps(report, ensure_ascii=False))
    run([sys.executable, str(ROOT / "shared/workflows/body-only/check_delivery.py"), "--video", str(VIDEO),
         "--srt", str(SRT), "--json", str(QA / "delivery-v1.json")], QA / "delivery-check-v1.log")
    run([sys.executable, str(ROOT / "shared/workflows/subtitles/check_srt.py"), str(SRT), "--json"], QA / "srt-check-v1.json")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
