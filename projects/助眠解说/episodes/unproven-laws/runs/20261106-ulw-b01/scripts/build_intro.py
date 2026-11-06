# -*- coding: utf-8 -*-
"""Build the 3-card intro (text over stills) and intro audio."""
import json, subprocess, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

RUN = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws\runs\20261106-ulw-b01")
EP = RUN.parents[1]
PILOT = RUN / "crops"
OUT = RUN / "intro"
OUT.mkdir(exist_ok=True)
FONT = r"E:\program\1project\video\assets\助眠解说\intro\fonts\MaShanZheng-Regular.ttf"
SR = 48000

LINES = [
    ("我们总说，发现了一条规律。", "很少有人说，证明了它。"),
    ("一条规律可以被检验一万次。", "第一万零一次，它仍然可能失效。"),
    ("那么，一条无法被证明的规律，", "真的存在吗？"),
]
BGS = ["S01_c0-s01.png", "S02_c0-s02.png", "G02_p1_c0-s07.png"]


def text_png(i, path):
    im = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, 86)
    l1, l2 = LINES[i]
    for line, y in ((l1, 470), (l2, 610)):
        w = d.textlength(line, font=f)
        d.text(((1920 - w) / 2, y), line, font=f, fill=(246, 235, 212, 255),
               stroke_width=5, stroke_fill=(24, 18, 12, 235))
    im.save(path)


def intro_audio():
    job = json.loads((EP / "audio" / "jobs" / "all.json").read_text(encoding="utf-8"))
    dur = json.loads((RUN / "durations.json").read_text(encoding="utf-8"))
    ids = [s["id"] for s in job["shots"] if s["id"].startswith("intro-")]
    out = OUT / "intro.wav"
    starts, pos = [], 0.35
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(np.zeros(int(0.35 * SR), dtype=np.int16).tobytes())
        for i, sid in enumerate(ids):
            starts.append(pos)
            with wave.open(str(EP / "audio" / "vo-proc" / (sid + ".wav")), "rb") as r:
                w.writeframes(r.readframes(r.getnframes()))
            pos += dur[sid]
            gap = 0.65 if i < len(ids) - 1 else 0.8
            w.writeframes(np.zeros(int(gap * SR), dtype=np.int16).tobytes())
            pos += gap
    return ids, starts, pos


def main():
    ids, starts, total = intro_audio()
    durs = json.loads((RUN / "durations.json").read_text(encoding="utf-8"))
    cards = []
    groups = [[0, 1], [2, 3], [4]]
    for i, grp in enumerate(groups):
        png = OUT / ("card%d.png" % (i + 1))
        text_png(i, png)
        d = sum(durs[ids[j]] for j in grp) + 0.65 * (len(grp) - 1) + 0.45
        if i == len(groups) - 1:
            d += 1.0
        bg = PILOT / BGS[i]
        card = OUT / ("card%d.mp4" % (i + 1))
        n = int(round(d * 30))
        vf = ("[0:v]zoompan=z='1+0.05*on/%d':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
              "d=1:s=1920x1080:fps=30,format=yuv420p[bg];"
              "[1:v]format=rgba,fade=t=in:st=0.25:d=0.55:alpha=1,"
              "fade=t=out:st=%.2f:d=0.55:alpha=1[t];[bg][t]overlay=0:0,format=yuv420p"
              % (n, d - 0.8))
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(bg),
               "-loop", "1", "-i", str(png), "-t", "%.3f" % d,
               "-filter_complex", vf, "-r", "30", "-c:v", "libx264",
               "-preset", "veryfast", "-crf", "18", "-an", str(card)]
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode != 0:
            print("CARD FAIL", i, r.stderr.decode("utf-8", "replace")[:300]); return
        cards.append(card)
        print("card", i + 1, "%.2fs" % d)
    lst = OUT / "cards.txt"
    lst.write_text("\n".join("file '%s'" % c.as_posix() for c in cards), encoding="utf-8")
    silent = OUT / "intro_silent.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-c", "copy", str(silent)], check=True)
    final = OUT / "intro.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent),
                    "-i", str(OUT / "intro.wav"), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-ac", "2", "-shortest", str(final)], check=True)
    with wave.open(str(OUT / "intro.wav"), "rb") as w:
        print("intro audio", round(w.getnframes() / w.getframerate(), 2))
    print("intro", final)


if __name__ == "__main__":
    main()
