# -*- coding: utf-8 -*-
"""A 基础 + 全程缓慢持续拉近（不设静态停顿）。"""
import json
import subprocess

import hook_intro as H

META = json.loads((H.RUN / "intro_timeline.json").read_text(encoding="utf-8"))
CUES = json.loads((H.RUN / "transition_cues.json").read_text(encoding="utf-8"))

H.T_ANIM = {
    "scale_start": 0.94,
    "whoosh_scale": 1.02,
    "whoosh_s": 0.30,
    "settle_s": 0.15,
    "scale_end": 1.12,
    "exit_ms": 0,
    "fade_in_ms": 220,
}
ass = H.RUN / "preview" / "burn" / "A_cont.ass"
H.write_hook_ass(META, CUES, ass)
full = H.RUN / "presets" / "A_cont.mp4"
H.burn(H.RUN / "intro_av.mp4", H.RUN / "intro.wav", ass, full)
subprocess.run([H.FF, "-y", "-t", "30", "-i", str(full),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                str(H.RUN / "presets" / "A_cont_30s.mp4")], check=True, capture_output=True)
print("done")
