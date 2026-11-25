"""Retiming the visual-only cut and SRT to a confirmed Jianying voice reference."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import tempfile

EP = Path(__file__).resolve().parents[1]
FPS = 24
VOICE_CPS = 4.6
GAP_FRAMES = 5
SOURCE_CUES = EP / "video/srt/下集/cues.json"
SOURCE_PLAN = EP / "storyboard/下集_SHOT_PLAN.json"
OUTPUT_STEM = "悬疑_林娜案下集_正文_v2"
OUTPUT_VIDEO = EP / f"video/final/{OUTPUT_STEM}.mp4"
OUTPUT_SRT = EP / f"video/final/{OUTPUT_STEM}.srt"


def visible_len(text):
    return sum(1 for ch in text if ch.isalnum() or "\u4e00" <= ch <= "\u9fff")


def normalize(text):
    return re.sub(r"[^\w\u4e00-\u9fff]", "", text, flags=re.UNICODE)


def read_cues_json(path):
    data = json.loads(path.read_text())
    cues = data.get("cues", [])
    if not cues or any(not cue.get("text") for cue in cues):
        raise ValueError(f"invalid cue data: {path}")
    return [{"text": cue["text"]} for cue in cues]


def timecode(frames):
    ms = round(frames * 1000 / FPS)
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    seconds, ms = divmod(ms, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{ms:03}"


def group_cues(shots, cues):
    groups = []
    cursor = 0
    for shot in shots:
        wanted = normalize(shot["cue"])
        joined = ""
        begin = cursor
        while cursor < len(cues) and len(joined) < len(wanted):
            joined += normalize(cues[cursor]["text"])
            cursor += 1
        if joined != wanted:
            raise ValueError(f"SRT text does not map to {shot['id']}: {len(joined)} != {len(wanted)}")
        groups.append(cues[begin:cursor])
    if cursor != len(cues):
        raise ValueError(f"unmapped SRT cues remain: {len(cues) - cursor}")
    return groups


def build_timeline(shots, groups):
    frame_cursor = 0
    retimed_cues = []
    retimed_shots = []
    cue_index = 0
    total = sum(len(group) for group in groups)
    for shot, group in zip(shots, groups):
        shot_start = frame_cursor
        for cue in group:
            chars = visible_len(cue["text"])
            duration = max(1, round(chars / VOICE_CPS * FPS))
            start = frame_cursor
            end = start + duration
            retimed_cues.append({"start_frame": start, "end_frame": end, "text": cue["text"]})
            frame_cursor = end
            cue_index += 1
            if cue_index < total:
                frame_cursor += GAP_FRAMES
        retimed_shots.append({
            "id": shot["id"],
            "start_frame": shot_start,
            "frames": frame_cursor - shot_start,
        })
    if normalize("".join(c["text"] for c in retimed_cues)) != normalize("".join(s["cue"] for s in shots)):
        raise ValueError("retimed SRT text differs from the locked narration")
    return retimed_cues, retimed_shots, frame_cursor


def write_srt(cues):
    blocks = []
    for i, cue in enumerate(cues, 1):
        blocks.append(
            f"{i}\n{timecode(cue['start_frame'])} --> {timecode(cue['end_frame'])}\n{cue['text']}"
        )
    OUTPUT_SRT.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def retime_clip(row, source_frames, target_frames, temp_dir):
    source = Path(row["clip"])
    if not source.exists():
        raise FileNotFoundError(source)
    target = Path(temp_dir) / f"{row['id']}.mp4"
    ratio = target_frames / source_frames
    vf = f"setpts={ratio:.12f}*PTS,fps={FPS},trim=end_frame={target_frames},setpts=PTS-STARTPTS"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-i", str(source), "-vf", vf,
        "-frames:v", str(target_frames), "-an", "-c:v", "libx264",
        "-preset", "fast", "-threads", "1", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", str(FPS), "-fps_mode", "cfr",
        "-movflags", "+faststart", str(target),
    ], check=True)
    probe = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=nb_frames,avg_frame_rate", "-of", "json", str(target)
    ]))
    stream = probe["streams"][0]
    if int(stream["nb_frames"]) != target_frames or stream["avg_frame_rate"] != f"{FPS}/1":
        raise RuntimeError(f"wrong frame count for {row['id']}: {stream}")
    return row["id"], target, target_frames


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()

    plan = json.loads(SOURCE_PLAN.read_text())
    shots = plan["shots"]
    source_cues = read_cues_json(SOURCE_CUES)
    groups = group_cues(shots, source_cues)
    cues, shot_timings, total_frames = build_timeline(shots, groups)
    print(json.dumps({
        "voice": "解说小帅",
        "effective_cps": VOICE_CPS,
        "inter_cue_gap_seconds": GAP_FRAMES / FPS,
        "subtitle_cues": len(cues),
        "shots": len(shots),
        "duration_seconds": round(total_frames / FPS, 3),
        "duration_minutes": round(total_frames / FPS / 60, 3),
        "source_duration_seconds": round(plan["frames"] / FPS, 3),
        "frames": total_frames,
    }, ensure_ascii=False, indent=2))
    if args.plan_only:
        return

    OUTPUT_VIDEO.parent.mkdir(parents=True, exist_ok=True)
    write_srt(cues)
    manifest_shots = {}
    source_frames = {}
    for shot in shots:
        clip = EP / f"video/clips/{shot['id']}.mp4"
        metadata = json.loads(clip.with_suffix(".json").read_text())
        source_frames[shot["id"]] = int(metadata["frames"])
        if source_frames[shot["id"]] != int(shot["frames"]):
            raise ValueError(f"source clip duration differs from shot plan: {shot['id']}")
        manifest_shots[shot["id"]] = {"id": shot["id"], "clip": str(clip)}
    with tempfile.TemporaryDirectory(prefix="linna-voice-retime-") as temp_dir:
        jobs = [(manifest_shots[timing["id"]], source_frames[timing["id"]], timing["frames"], temp_dir)
                for timing in shot_timings]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            rendered = list(pool.map(lambda job: retime_clip(*job), jobs))
        concat = Path(temp_dir) / "concat.txt"
        concat.write_text("\n".join("file '" + str(path) + "'" for _, path, _ in rendered) + "\n")
        subprocess.run([
            "ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
            "-map", "0:v:0", "-c", "copy", "-an", "-frames:v", str(total_frames),
            "-movflags", "+faststart", str(OUTPUT_VIDEO),
        ], check=True)

    report = {
        "voice": "解说小帅",
        "reference_file": "/Users/mac/Movies/11月23日 (1).mp4",
        "effective_cps": VOICE_CPS,
        "gap_frames": GAP_FRAMES,
        "fps": FPS,
        "frames": total_frames,
        "duration_seconds": total_frames / FPS,
        "subtitle_cues": len(cues),
        "source_plan": str(SOURCE_PLAN),
        "video": str(OUTPUT_VIDEO),
        "video_sha256": sha256(OUTPUT_VIDEO),
        "srt": str(OUTPUT_SRT),
        "text_preserved": True,
        "audio_included": False,
    }
    report_path = EP / "qa/下集-voice-retime-v2.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("RETIME_COMPLETE", OUTPUT_VIDEO, OUTPUT_SRT, report_path, flush=True)


if __name__ == "__main__":
    main()
