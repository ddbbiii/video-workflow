# -*- coding: utf-8 -*-
import json, subprocess
from pathlib import Path

RUN = Path(r"E:\program\1project\video\4\runs\20261103-gla-b01")
plan = json.load(open(RUN / "manifests" / "pacing_plan.json", encoding="utf-8"))
FP = r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffprobe.exe"
bad, missing = [], []
for p in plan["paragraphs"]:
    f = RUN / "media" / "para" / f"{p['pid']}.mp4"
    if not f.exists():
        missing.append(p["pid"]); continue
    r = subprocess.run([FP, "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=nb_frames", "-of", "csv=p=0", str(f)],
                       capture_output=True, text=True)
    v = r.stdout.strip()
    n = int(v) if v.isdigit() else -1
    if n != p["frames"]:
        bad.append((p["pid"], n, p["frames"]))
print("paras", len(plan["paragraphs"]), "missing", missing[:5], "len", len(missing))
print("mismatch", len(bad), bad[:8])
