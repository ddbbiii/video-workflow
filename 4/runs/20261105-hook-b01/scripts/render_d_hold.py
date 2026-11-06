# -*- coding: utf-8 -*-
"""字幕浮现 → 缓慢放大 → 定格。"""
import json
import subprocess

import hook_intro as H

META = json.loads((H.RUN / "intro_timeline.json").read_text(encoding="utf-8"))
CUES = json.loads((H.RUN / "transition_cues.json").read_text(encoding="utf-8"))

H.T_ANIM = {
    "scale_start": 0.96,
    "whoosh_scale": 1.00,
    "whoosh_s": 0.35,
    "settle_s": 0.10,
    "scale_end": 1.10,
    "zoom_ms": 1700,
    "fade_in_ms": 260,
}
ass = H.RUN / "preview" / "burn" / "D_float.ass"
H.write_hook_ass(META, CUES, ass)
full = H.RUN / "presets" / "D_float_hold.mp4"
H.burn(H.RUN / "intro_av.mp4", H.RUN / "intro.wav", ass, full)
subprocess.run([H.FF, "-y", "-t", "30", "-i", str(full),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                str(H.RUN / "presets" / "D_float_30s.mp4")], check=True, capture_output=True)
print("done")
