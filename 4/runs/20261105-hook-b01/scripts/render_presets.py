# -*- coding: utf-8 -*-
"""用同一套背景/音轨，渲染 A/B/C 三种大字节奏，各出 30s 预览。"""
import json
import subprocess
from pathlib import Path

import hook_intro as H

META = json.loads((H.RUN / "intro_timeline.json").read_text(encoding="utf-8"))
CUES = json.loads((H.RUN / "transition_cues.json").read_text(encoding="utf-8"))
OUT = H.RUN / "presets"
OUT.mkdir(parents=True, exist_ok=True)

PRESETS = {
    "A_stable": {"scale_start": 0.94, "whoosh_scale": 1.02, "whoosh_s": 0.30,
                 "settle_s": 0.15, "scale_end": 1.12, "exit_ms": 700,
                 "fade_in_ms": 220},
    "B_soft": {"scale_start": 0.88, "whoosh_scale": 1.05, "whoosh_s": 0.18,
               "settle_s": 0.15, "scale_end": 1.22, "exit_ms": 800,
               "fade_in_ms": 180},
    "C_big": {"scale_start": 0.85, "whoosh_scale": 1.08, "whoosh_s": 0.20,
              "settle_s": 0.12, "scale_end": 1.35, "exit_ms": 600,
              "fade_in_ms": 200},
}

for name, anim in PRESETS.items():
    H.T_ANIM = anim
    ass = H.RUN / "preview" / "burn" / f"{name}.ass"
    H.write_hook_ass(META, CUES, ass)
    full = OUT / f"{name}.mp4"
    H.burn(H.RUN / "intro_av.mp4", H.RUN / "intro.wav", ass, full)
    preview = OUT / f"{name}_30s.mp4"
    subprocess.run([H.FF, "-y", "-t", "30", "-i", str(full),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", str(preview)],
                   check=True, capture_output=True)
    print("done", name, flush=True)
print("->", OUT)
