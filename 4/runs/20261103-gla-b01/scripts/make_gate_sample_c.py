# -*- coding: utf-8 -*-
"""C 版：保留 r4 的时间（+0.504s），只用门禁的词边界折行。"""
import re
import subprocess
from pathlib import Path

EP = Path(r"E:\program\1project\video\4")
RUN = EP / "runs" / "20261103-gla-b01"
OUT = RUN / "qa/gate_sample"
SRC = RUN / "subtitles/gate1/fixed.ass"
DST = OUT / "C_r4time_newbreak.ass"
CLEAN = EP / "video" / "final" / "glacier-river_clean.mp4"
NARR = EP / "video" / "final" / "glacier-river_narration.wav"
FF = r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"
SS, DUR, ADD = 100.0, 60.0, 0.504


def t2s(t):
    h, m, rest = t.split(":")
    s, cs = rest.split(".")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100


def s2t(t):
    t = max(0.0, t)
    h = int(t // 3600); m = int(t % 3600 // 60); s = int(t % 60); cs = int(round((t % 1) * 100))
    if cs == 100:
        s += 1; cs = 0
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def main():
    lines = []
    for ln in SRC.read_text(encoding="utf-8-sig").splitlines():
        if not ln.startswith("Dialogue:"):
            lines.append(ln); continue
        p = ln.split(",", 9)
        st, en = t2s(p[1]) + ADD - SS, t2s(p[2]) + ADD - SS
        if en <= 0:
            continue
        p[1], p[2] = s2t(st), s2t(en)
        lines.append(",".join(p))
    DST.write_text("\n".join(lines), encoding="utf-8")
    r = subprocess.run([FF, "-y", "-ss", str(SS), "-t", str(DUR), "-i", str(CLEAN),
                        "-ss", str(SS), "-t", str(DUR), "-i", str(NARR),
                        "-vf", f"subtitles={DST.name}:fontsdir=fonts",
                        "-map", "0:v", "-map", "1:a",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                        str(OUT / "C_r4time_newbreak.mp4")],
                       capture_output=True, text=True, cwd=str(OUT))
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "")[-600:])
    print("ok")


if __name__ == "__main__":
    main()
