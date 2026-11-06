# -*- coding: utf-8 -*-
"""Assemble intro + body, mux narration, burn subtitles, write finals."""
import json, subprocess
from pathlib import Path

RUN = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws\runs\20261106-ulw-b01")
EP = RUN.parents[1]
CLIPS = RUN / "clips_affine"
FINAL = EP / "video" / "final"
FINAL.mkdir(parents=True, exist_ok=True)


def run(cmd, cwd=None):
    r = subprocess.run(cmd, capture_output=True, cwd=cwd)
    if r.returncode != 0:
        raise SystemExit("FAIL: %s\n%s" % (" ".join(cmd[:6]), r.stderr.decode("utf-8", "replace")[:800]))


def main():
    tl = json.loads((RUN / "timeline.json").read_text(encoding="utf-8"))
    shots = [s for sec in tl["sections"] for s in sec["shots"]]
    lst = RUN / "clips.txt"
    lst.write_text("\n".join("file '%s'" % (CLIPS / (s["id"] + ".mp4")).as_posix() for s in shots), encoding="utf-8")
    silent = RUN / "body_silent.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c", "copy", str(silent)])
    # if the clip sum is short of the narration, append black tail so -shortest never cuts speech
    def dur(p):
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nw=1:nk=1", str(p)], capture_output=True, text=True)
        return float(r.stdout.strip())
    vd, ad = dur(silent), dur(EP / "audio" / "narration_body.wav")
    if vd < ad - 0.05:
        tail = RUN / "tail_black.mp4"
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
             "-i", "color=c=black:s=1920x1080:r=30", "-t", "%.3f" % (ad - vd + 0.8),
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
             "-pix_fmt", "yuv420p", "-an", str(tail)])
        lst.write_text(lst.read_text(encoding="utf-8") + "\nfile '%s'" % tail.as_posix(), encoding="utf-8")
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
             "-c", "copy", str(silent)])
    body = RUN / "body.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent),
         "-i", str(EP / "audio" / "narration_body.wav"),
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ac", "2",
         "-shortest", "-movflags", "+faststart", str(body)])
    intro = RUN / "intro" / "intro.mp4"
    cat = RUN / "intro_body.txt"
    cat.write_text("file '%s'\nfile '%s'" % (intro.as_posix(), body.as_posix()), encoding="utf-8")
    clean = FINAL / "unproven-laws_clean.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(cat),
         "-c", "copy", "-movflags", "+faststart", str(clean)])
    gain = RUN / "clean_gain.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clean),
         "-c:v", "copy", "-af", "volume=4dB", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", str(gain)])
    clean.unlink()
    gain.rename(clean)
    sub = FINAL / "unproven-laws_sub.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clean),
         "-vf", "ass=body.ass",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
         "-c:a", "copy", "-movflags", "+faststart", str(sub)],
        cwd=str(RUN / "subtitles"))
    for p in (clean, sub):
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration:stream=codec_type,width,height,r_frame_rate",
                            "-of", "default=nw=1", str(p)], capture_output=True, text=True)
        print(p.name, "\n" + r.stdout)


if __name__ == "__main__":
    main()
