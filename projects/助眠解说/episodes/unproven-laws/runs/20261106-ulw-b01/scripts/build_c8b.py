# -*- coding: utf-8 -*-
"""Build c8 replacement manifest: timeless contemporary bedroom, no period furniture."""
import json
from pathlib import Path

RUN = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws\runs\20261106-ulw-b01")
STYLE = ("cinematic contemporary documentary, photorealistic, deep teal-blue night palette with "
         "controlled warm amber lamplight, volumetric light, fine linen and wood texture, "
         "calm dreamlike mood, 16:9 widescreen")
HEADER = ("Create ONE single 2048x1152 image laid out as EXACTLY a 2x2 grid of four independent, "
          "complete 16:9 landscape scenes, separated only by thin straight dividers on the exact "
          "center lines, no outer frame; nothing crosses a divider. No text, letters, numbers, "
          "labels or watermarks anywhere.")
SHARED = ("Shared world: a quiet contemporary bedroom at night, timeless and uncluttered; linen "
          "bedding, simple wooden bed and bedside table, one warm lamp, a window with soft city "
          "lights; no electronics, no visible clock, no screens, no people's faces. Recurring "
          "prop when present: two small spheres of equal diameter, one matte dark iron gray, one "
          "pale wood, about 8 cm.")
NEG = ("Negatives: no text, no letters, no numbers, no labels, no watermark, no UI, no screens, "
       "no phones, no clocks, no faces, no extra objects, no diagram, no border.")

G35 = "\n\n".join([HEADER, SHARED,
    "Panel 1 (top-left): wide view of the bedroom, bed with rumpled linen, warm bedside lamp, curtain half drawn, deep teal shadows.",
    "Panel 2 (top-right): close view of a hand (no face) gently pushing the two spheres together on the bedside table, warm lamp light.",
    "Panel 3 (bottom-left): the window at night, city lights soft and out of focus beyond the glass, curtain edge in the foreground.",
    "Panel 4 (bottom-right): the night sky above the city, stars steady, deep blue-black, no labels.", NEG])
G36 = "\n\n".join([HEADER, SHARED,
    "Panel 1 (top-left): the moon with thin cloud passing across it, soft silver light, deep blue-black sky.",
    "Panel 2 (top-right): a linen curtain lifting slightly in a night breeze, warm lamplight behind it, deep teal shadows.",
    "Panel 3 (bottom-left): a hand (no face) turning down the bedside lamp, the warm light dimming.",
    "Panel 4 (bottom-right): the bedroom almost dark, only a faint warm line under the curtain, calm.", NEG])
S17 = "\n\n".join([
    "A single 2048x1152 cinematic photograph: two small spheres of equal diameter, one matte dark iron gray and one pale wood, on a contemporary bedside table at night, a warm lamp just behind them, linen bedding soft in the background, deep teal shadows, calm.",
    STYLE + ". No text, no letters, no numbers, no labels, no watermark, no faces."])

jobs = [
    {"job_id": "G35B", "kind": "grid2x2", "scope": "c8-s01/s03/s04/s05", "final_request_text": G35},
    {"job_id": "G36B", "kind": "grid2x2", "scope": "c8-s06/s07/s08/spare", "final_request_text": G36},
    {"job_id": "S17B", "kind": "single", "scope": "c8-s02", "final_request_text": S17},
]
(RUN / "grid-manifest-c8b.json").write_text(json.dumps({"jobs": jobs}, ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote c8b", len(jobs))
