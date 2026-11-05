# -*- coding: utf-8 -*-
"""把 ASS 平移到某个 60s 片段并烧两份对照：A=当前 r4（原折行），B=门禁修正（词边界折行 + ASR 对齐）。"""
import re
import subprocess
from pathlib import Path

EP = Path(r"E:\program\1project\video\4")
RUN = EP / "runs" / "20261103-gla-b01"
CLEAN = EP / "video" / "final" / "glacier-river_clean.mp4"
NARR = EP / "video" / "final" / "glacier-river_narration.wav"
A_IN = RUN / "subtitles/r4/body.ass"
B_IN = RUN / "subtitles/gate1/fixed.ass"
OUT = RUN / "qa/gate_sample"
SS, DUR = 100.0, 60.0
FF = r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"


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


def shift(src, dst):
    lines = []
    for ln in src.read_text(encoding="utf-8-sig").splitlines():
        if not ln.startswith("Dialogue:"):
            lines.append(ln); continue
        parts = ln.split(",", 9)
        st, en = parts[1], parts[2]
        st2, en2 = t2s(st) - SS, t2s(en) - SS
        if en2 <= 0:
            continue
        parts[1], parts[2] = s2t(st2), s2t(en2)
        lines.append(",".join(parts))
    dst.write_text("\n".join(lines), encoding="utf-8")
    # 字体目录
    fontdir = dst.parent / "fonts"
    fontdir.mkdir(exist_ok=True)
    for f in (EP / "assets/助眠解说/subtitles/style-r4/fonts").glob("*"):
        (fontdir / f.name).write_bytes(f.read_bytes())


def burn(ass, out):
    r = subprocess.run([FF, "-y", "-ss", str(SS), "-t", str(DUR), "-i", str(CLEAN),
                        "-ss", str(SS), "-t", str(DUR), "-i", str(NARR),
                        "-vf", f"subtitles={ass.name}:fontsdir=fonts",
                        "-map", "0:v", "-map", "1:a",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", str(out)],
                       capture_output=True, text=True, cwd=str(ass.parent))
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "")[-600:])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    a = OUT / "A_current.ass"; b = OUT / "B_gate.ass"
    shift(A_IN, a); shift(B_IN, b)
    burn(a, OUT / "A_current.mp4")
    burn(b, OUT / "B_gate.mp4")
    print("ok", OUT)


if __name__ == "__main__":
    main()
