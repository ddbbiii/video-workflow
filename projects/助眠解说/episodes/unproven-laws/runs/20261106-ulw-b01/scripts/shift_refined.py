# -*- coding: utf-8 -*-
"""Apply a measured global lead to refined subtitles (timing only)."""
import re
from pathlib import Path

RUN = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws\runs\20261106-ulw-b01")
SHIFT = -0.12


def sec(t):
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return "%d:%02d:%05.2f" % (h, m, s)


def srt_ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = int(t % 60); ms = int(round((t % 1) * 1000))
    if ms == 1000:
        s += 1; ms = 0
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


lines = (RUN / "subtitles" / "body_refined.ass").read_text(encoding="utf-8-sig").splitlines()
out, srt, idx = [], [], 0
for l in lines:
    if l.startswith("Dialogue:"):
        p = l.split(",", 9)
        s = max(0.0, sec(p[1]) + SHIFT); e = max(s + 0.6, sec(p[2]) + SHIFT)
        out.append("Dialogue: 0,%s,%s,%s,,0,0,0,,%s" % (ts(s), ts(e), p[3], p[9]))
        idx += 1
        srt.append("%d\n%s --> %s\n%s\n" % (idx, srt_ts(s), srt_ts(e), p[9].replace("\\N", "\n")))
    else:
        out.append(l)
(RUN / "subtitles" / "body_refined.ass").write_text("\ufeff" + "\n".join(out) + "\n", encoding="utf-8")
(RUN / "subtitles" / "body_refined.srt").write_text("\n".join(srt), encoding="utf-8")
print("shifted", idx, "cues by", SHIFT)
