"""Assemble the locked static timeline and verify the silent review cut."""
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageOps

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[3]
QA = EP / "qa"
PLAN_PATH = EP / "storyboard/SHOT_PLAN.json"
PLAN = json.loads(PLAN_PATH.read_text())
REVIEW = EP / "video/review/悬疑_雪夜林屋_正文_v1.mp4"
FINAL = EP / "video/final" / REVIEW.name


def run(*args):
    return subprocess.run(list(map(str, args)), check=True, capture_output=True, text=True)


def record(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode_still(work, row):
    source = EP / "image/final" / (row["id"] + ".png")
    still = work / (row["id"] + ".png")
    clip = still.with_suffix(".mp4")
    with Image.open(source) as im:
        ImageOps.fit(im.convert("RGB"), (1920, 1080), method=Image.Resampling.LANCZOS).save(still)
    run("ffmpeg", "-v", "error", "-xerror", "-loop", "1", "-framerate", "24", "-i", still,
        "-map", "0:v:0", "-an", "-frames:v", row["frames"], "-c:v", "libx264",
        "-x264-params", "keyint=240:min-keyint=240:scenecut=0", "-preset", "fast",
        "-tune", "stillimage", "-crf", "17", "-threads", "2", "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-video_track_timescale", "24000", clip)
    still.unlink()
    shot_id = row["id"]
    logs = EP / "logs"
    generated = logs / f"{shot_id}.json"
    if not generated.exists():
        generated = logs / "cabin-reactions-grid.json" if shot_id in ("S13", "S14", "S17") else logs / "door-hero.json"
    route = json.loads(generated.read_text())
    assert route["ok"], (shot_id, generated)
    return dict(id=shot_id, source=str(source.relative_to(EP)), sha256=digest(source),
                start_frame=row["start_frame"], frames=row["frames"], motion="static",
                transition="cut", fact=row["fact"], character_ids=row["character_ids"],
                origin=str(generated.relative_to(EP)), channel=route["channel"],
                attempts=route.get("attempts", []), fallback_from=route.get("fallback_from"),
                qa=route["metrics"])


def video_scan(path):
    metadata = json.loads(run("ffprobe", "-v", "error", "-show_streams", "-show_format",
                              "-of", "json", path).stdout)
    streams = metadata["streams"]
    assert len(streams) == 1 and streams[0]["codec_type"] == "video"
    v = streams[0]
    frames = PLAN["frames"]
    assert (v["width"], v["height"], v["codec_name"], v["pix_fmt"]) == (1920, 1080, "h264", "yuv420p")
    assert Fraction(v["avg_frame_rate"]) == 24 and int(v["nb_frames"]) == frames
    assert abs(float(metadata["format"]["duration"]) - frames / 24) <= 1 / 24
    decoded = json.loads(run(
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_frames",
        "-show_entries", "frame=best_effort_timestamp", "-of", "json", path
    ).stdout)["frames"]
    step = Fraction(1, 24) / Fraction(v["time_base"])
    pts = [int(f["best_effort_timestamp"]) for f in decoded]
    assert len(pts) == frames and pts[0] == 0
    max_error = max(abs(pts[i] - i * step) for i in range(frames))
    assert max_error == 0, f"Non-CFR timestamp deviation: {max_error} ticks"
    intervals = {}
    for label, filters in (("black", ""), ("white", "negate,")):
        output = run("ffmpeg", "-hide_banner", "-v", "info", "-xerror", "-i", path,
                     "-vf", filters + "blackdetect=d=0.95:pix_th=0.10:pic_th=0.98",
                     "-an", "-f", "null", "-").stderr
        intervals[label] = re.findall(r"black_start:(\S+) black_end:(\S+) black_duration:(\S+)", output)
    report = dict(pass_check=not any(intervals.values()), frames=frames, fps=24,
                  duration=PLAN["duration"], decoded_pts=len(pts), cfr_max_error_ticks=0,
                  full_frame_black_white_intervals=intervals, video_sha256=digest(path))
    record(QA / "video.json", metadata)
    record(QA / "pixel_scan.json", report)
    assert report["pass_check"], report


def render():
    rows = PLAN["shots"]
    assert len(rows) == 33 and PLAN["fps"] == 24
    assert digest(EP / "story/script.md") == PLAN["script_sha256"]
    assert all((EP / "image/final" / (row["id"] + ".png")).is_file() for row in rows)
    frame = 0
    for row in rows:
        assert row["start_frame"] == frame and row["motion"] == "static"
        frame += row["frames"]
    assert frame == PLAN["frames"]
    available = shutil.disk_usage(EP).free
    budget = 12 * 1024 ** 3
    assert available >= budget
    record(EP / "logs/render-preflight.json", dict(free_bytes=available, required_bytes=budget))
    REVIEW.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="static-encode-", dir=REVIEW.parent) as tmp:
        work = Path(tmp)
        with ThreadPoolExecutor(max_workers=4) as pool:
            manifest = list(pool.map(lambda row: encode_still(work, row), rows))
        concat = work / "concat.txt"
        concat.write_text("ffconcat version 1.0\n" + "".join(
            f"file '{row['id']}.mp4'\nduration {row['frames'] / 24:.9f}\n" for row in rows
        ))
        part = work / "join.mp4"
        run("ffmpeg", "-v", "error", "-xerror", "-f", "concat", "-safe", "0", "-i", concat,
            "-map", "0:v:0", "-c:v", "copy", "-an", "-frames:v", frame,
            "-video_track_timescale", "24000", "-movflags", "+faststart", part)
        video_scan(part)
        part.replace(REVIEW)
    record(EP / "logs/render-manifest.json", dict(shots=manifest, frames=frame,
           script_sha256=PLAN["script_sha256"], video_sha256=digest(REVIEW)))
    print(REVIEW)


def finalize():
    assert (QA / "review-approved.md").is_file(), "正文成片需先验看"
    assert REVIEW.is_file() and digest(REVIEW) == json.loads((QA / "pixel_scan.json").read_text())["video_sha256"]
    subtitles = ROOT / "shared/workflows/subtitles"
    sys.path.insert(0, str(subtitles))
    from split_srt import fmt_ts, normalize, read_srt, visible_len

    intro_folder = EP / "image/intro/v1"
    expected_intro = [intro_folder / f"悬疑_雪夜林屋_引入_{i:02}_v1.png" for i in (1, 2)]
    assert sorted(intro_folder.glob("*.png")) == expected_intro
    for intro in expected_intro:
        with Image.open(intro) as im:
            assert im.size == (1920, 1080) and im.format == "PNG"
            im.verify()
    rows = PLAN["shots"]
    run(sys.executable, ROOT / "shared/workflows/script-qa/lint_narration.py", PLAN_PATH,
        "--json", QA / "narration-lint-final.json")
    FINAL.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="srt-", dir=FINAL.parent) as tmp:
        tmp = Path(tmp)
        sentences = tmp / "sentences.srt"
        sentences.write_text("\n\n".join(
            f"{i}\n{fmt_ts(row['start'])} --> {fmt_ts(row['end'])}\n{row['cue']}"
            for i, row in enumerate(rows, 1)
        ) + "\n")
        stage = tmp / FINAL.with_suffix(".srt").name
        run(sys.executable, subtitles / "split_srt.py", sentences, "--out", stage,
            "--report", QA / "srt-split.json", "--allow-word-split")
        srt_check = run(sys.executable, subtitles / "check_srt.py", stage, "--json").stdout
        (QA / "srt-check.json").write_text(srt_check)
        blocks = read_srt(stage)
        locked = (EP / "story/script.md").read_text().split("\n", 1)[1]
        locked = re.sub(r"</?span[^>]*>", "", locked)
        assert normalize("".join(b["text"] for b in blocks)) == normalize(locked)
        assert blocks[0]["start"] == 0 and abs(blocks[-1]["end"] - PLAN["duration"]) < .001
        # The checker validates the same basename in the same staged directory.
        stage_video = stage.with_suffix(".mp4")
        shutil.copy2(REVIEW, stage_video)
        run(sys.executable, ROOT / "shared/workflows/body-only/check_delivery.py",
            "--video", stage_video, "--srt", stage, "--json", QA / "delivery.json")
        stage.replace(FINAL.with_suffix(".srt"))
        stage_video.replace(FINAL)
    record(EP / "video/timeline.json", dict(fps=24, frames=PLAN["frames"], estimated=True,
           shots=[{key: row[key] for key in ("id", "cue", "start", "end", "start_frame", "frames")}
                  for row in rows]))
    (QA / "srt_qa.md").write_text(f"# 正文字幕验收\n\n"
        f"锁定正文 {len(rows)} 个镜头旁白段，拆为 {len(blocks)} 条字幕，"
        f"最长 {max(visible_len(b['text']) for b in blocks)} 字。文本比对一致，字幕与交付检查通过。\n\n"
        f"时间范围 {fmt_ts(blocks[0]['start'])} 至 {fmt_ts(blocks[-1]['end'])}。"
        f"估算时间轴，未对真实人声校准。超长分句按词拆分，详见 srt-split.json。\n")
    REVIEW.unlink()
    print(FINAL)


if __name__ == "__main__":
    {"render": render, "finalize": finalize}[sys.argv[1]]()
