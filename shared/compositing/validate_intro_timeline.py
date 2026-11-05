"""Validate intro timing against the exact final narration track."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def probe(path):
    return json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
    ], text=True))


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True)
    parser.add_argument("--video")
    parser.add_argument("--timeline", required=True)
    parser.add_argument("--write-manifest")
    args = parser.parse_args()
    audio = Path(args.audio)
    timeline = json.loads(Path(args.timeline).read_text(encoding="utf-8"))
    if timeline.get("timing_basis") != "final-audio-samples":
        raise SystemExit("FAIL: timeline.timing_basis must be final-audio-samples")
    sentences = timeline.get("sentences", [])
    if not sentences:
        raise SystemExit("FAIL: no sentence boundaries")
    audio_probe = probe(audio)
    stream = next((s for s in audio_probe["streams"] if s["codec_type"] == "audio"), None)
    if not stream:
        raise SystemExit("FAIL: no audio stream")
    sample_rate = int(stream.get("sample_rate", 0))
    duration = float(audio_probe["format"]["duration"])
    previous = 0
    for index, sentence in enumerate(sentences, 1):
        start = int(sentence["start_sample"])
        end = int(sentence["end_sample"])
        if start < previous or end <= start or end > round(duration * sample_rate) + 1:
            raise SystemExit(f"FAIL: invalid sentence boundary at {index}")
        previous = end
    result = {
        "status": "pass",
        "audio": str(audio),
        "audio_sha256": sha256(audio),
        "sample_rate": sample_rate,
        "duration_seconds": duration,
        "timing_basis": "final-audio-samples",
        "sentence_count": len(sentences),
    }
    if args.video:
        video = Path(args.video)
        video_probe = probe(video)
        video_duration = float(video_probe["format"]["duration"])
        result.update({"video": str(video), "video_duration_seconds": video_duration,
                       "video_sha256": sha256(video)})
        if abs(video_duration - duration) > 1 / 30:
            raise SystemExit("FAIL: video and narration duration differ by more than one frame")
    if args.write_manifest:
        Path(args.write_manifest).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
