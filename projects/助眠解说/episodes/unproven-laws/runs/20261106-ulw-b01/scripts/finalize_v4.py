# -*- coding: utf-8 -*-
"""Final assembly for v4: affine clips + CosyVoice narration + BGM + subtitles."""
import json, subprocess
from pathlib import Path

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws")
RUN = EP / "runs" / "20261106-ulw-b01"
FIN = EP / "video" / "final"
CLIPS = RUN / "clips_affine"
SUBS = RUN / "subtitles"
BGM = Path(r"E:\program\1project\video\bgm\bgm\bgm\Ambient-Loop-isaiah658.wav")


def run(cmd, cwd=None):
    r = subprocess.run(cmd, capture_output=True, cwd=cwd)
    if r.returncode != 0:
        raise SystemExit("FAIL: %s\n%s" % (" ".join(cmd[:6]), r.stderr.decode("utf-8", "replace")[:800]))


def dur(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(p)], capture_output=True, text=True)
    return float(r.stdout.strip())


def main():
    tl = json.loads((RUN / "timeline.json").read_text(encoding="utf-8"))
    shots = [s for sec in tl["sections"] for s in sec["shots"]]
    lst = RUN / "clips_cosy.txt"
    lst.write_text("\n".join("file '%s'" % (CLIPS / (s["id"] + ".mp4")).as_posix() for s in shots), encoding="utf-8")
    silent = RUN / "body_cosy_silent.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c", "copy", str(silent)])
    body = RUN / "body_cosy.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent),
         "-i", str(EP / "audio" / "narration_body.wav"),
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-shortest",
         "-movflags", "+faststart", str(body)])
    intro = RUN / "intro" / "intro.mp4"
    total = dur(intro) + dur(body)
    cat = RUN / "intro_body_cosy.txt"
    cat.write_text("file '%s'\nfile '%s'" % (intro.as_posix(), body.as_posix()), encoding="utf-8")
    clean = FIN / "unproven-laws_clean.mp4"
    fade_out = max(0.0, total - 3.0)
    fc = ("[0:v]crop=1912:1072:4:4,scale=1920:1080[v];"
          "[0:a]aformat=sample_rates=48000:channel_layouts=stereo[va];"
          "[1:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=-17.2dB,"
          "afade=t=in:st=0:d=2,afade=t=out:st=%.2f:d=3[bg];"
          "[va][bg]amix=inputs=2:duration=first:normalize=0[a]" % fade_out)
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(cat),
         "-stream_loop", "-1", "-i", str(BGM), "-filter_complex", fc,
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
         "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(clean)])
    sub = FIN / "unproven-laws_sub.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clean), "-vf", "ass=body.ass",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-c:a", "copy",
         "-movflags", "+faststart", str(sub)], cwd=str(SUBS))
    print("total", round(total, 2), "clean", round(dur(clean), 2), "sub", round(dur(sub), 2))


if __name__ == "__main__":
    main()
