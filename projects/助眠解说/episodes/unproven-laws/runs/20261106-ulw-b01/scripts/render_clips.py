# -*- coding: utf-8 -*-
"""Render one 1080p30 clip per shot from a still + slow motion, in parallel."""
import json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RUN = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws\runs\20261106-ulw-b01")
CLIPS = RUN / "clips"
CLIPS.mkdir(exist_ok=True)
CROPS = RUN / "crops_full"
REUSE = {
    "c0-s11": "c0-s01",
    "c1-s18": "c1-s17", "c1-s19": "c1-s17", "c1-s20": "c1-s17",
    "c2-s22": "c2-s21",
    "c3-s10": "c3-s09",
    "c5-s08": "c5-s07",
    "c6-s15": "c6-s14",
    "c8-s09": "c8-s08",
}
BLACK = {"c3-s18", "c5-s21", "c6-s16", "c7-s14", "c8-s10"}


def vf(motion, dur):
    m = motion or ""
    n = max(1, int(round(dur * 30)))
    if "拉" in m:
        z = "1.06-0.06*on/%d" % n
        x = "iw/2-(iw/zoom/2)"; y = "ih/2-(ih/zoom/2)"
    elif "横移" in m:
        z = "1.05"
        x = "(iw-iw/zoom)*on/%d" % n; y = "ih/2-(ih/zoom/2)"
    elif "静" in m:
        z = "1"; x = "0"; y = "0"
    else:
        z = "1+0.06*on/%d" % n
        x = "iw/2-(iw/zoom/2)"; y = "ih/2-(ih/zoom/2)"
    return ("zoompan=z='%s':x='%s':y='%s':d=1:s=1920x1080:fps=30,format=yuv420p"
            % (z, x, y))


def render(shot):
    out = CLIPS / (shot["id"] + ".mp4")
    dur = max(1.0, float(shot["dur"]))
    nf = max(1, int(round(float(shot["end"]) * 30)) - int(round(float(shot["start"]) * 30)))
    if out.exists():
        return shot["id"], "skip"
    if shot["id"] in BLACK:
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
               "-i", "color=c=black:s=1920x1080:r=30", "-frames:v", str(nf),
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
               "-pix_fmt", "yuv420p", "-an", str(out)]
        r = subprocess.run(cmd, capture_output=True)
        return shot["id"], "ok" if r.returncode == 0 else "FAIL black"
    img = CROPS / ((REUSE.get(shot["id"], shot["id"])) + ".png")
    if not img.exists():
        return shot["id"], "FAIL missing " + img.name
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1",
           "-i", str(img), "-frames:v", str(nf),
           "-vf", vf(shot.get("motion"), nf / 30.0), "-r", "30",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
           "-an", str(out)]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        return shot["id"], "FAIL " + r.stderr.decode("utf-8", "replace")[:200]
    return shot["id"], "ok"


def main():
    tl = json.loads((RUN / "timeline.json").read_text(encoding="utf-8"))
    shots = [s for sec in tl["sections"] for s in sec["shots"]]
    print("shots", len(shots))
    ok = 0
    with ThreadPoolExecutor(max_workers=4) as ex:
        for sid, st in ex.map(render, shots):
            if st.startswith("FAIL"):
                print(sid, st)
            else:
                ok += 1
            if ok % 20 == 0:
                print("progress", ok, "/", len(shots), flush=True)
    print("done", ok, "/", len(shots))


if __name__ == "__main__":
    main()
