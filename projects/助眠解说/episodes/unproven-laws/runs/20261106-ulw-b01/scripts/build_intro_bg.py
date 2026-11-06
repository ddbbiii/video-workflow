# -*- coding: utf-8 -*-
"""Intro background 2x2 manifest: four distinct hook scenes, none equal to body c0-s01."""
import json
from pathlib import Path

RUN = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws\runs\20261106-ulw-b01")
STYLE = ("cinematic historical science documentary, photorealistic, deep teal-blue shadows with "
         "controlled warm amber highlights, volumetric light, fine material texture, "
         "asymmetrical composition, calm dreamlike mood, 16:9 widescreen")
HEADER = ("Create ONE single 2048x1152 image laid out as EXACTLY a 2x2 grid of four independent, "
          "complete 16:9 landscape scenes, separated only by thin straight dividers on the exact "
          "center lines, no outer frame; nothing crosses a divider. No text, letters, numbers, "
          "labels or watermarks anywhere.")
NEG = ("Negatives: no text, no letters, no numbers, no labels, no watermark, no UI, no faces, "
       "no people, no modern objects, no extra spheres, no diagram, no border.")
SHARED = ("Shared world: late Renaissance Italy at dusk and night; stone, wood, brass, paper, "
          "candlelight; recurring prop when present: two small spheres of equal diameter, one "
          "matte dark iron gray, one pale wood.")
PROMPT = "\n\n".join([
    HEADER, SHARED,
    "Panel 1 (top-left): a wide view of the Leaning Tower of Pisa from across dark rooftops at dusk, the tower small and distant on the right third, warm amber sky, deep teal foreground roofs, soft haze; no people.",
    "Panel 2 (top-right): the two spheres resting on a dark wooden table, a candle just behind them, warm light on the iron and the wood grain, deep teal background, shallow depth of field.",
    "Panel 3 (bottom-left): the tower's silhouette against a deep starry night sky, low on the horizon, no city detail, a faint warm glow at the base, calm.",
    "Panel 4 (bottom-right): a candlelit desk with a glass prism, a stack of old books and a white quill, warm amber pool of light, deep teal shadows, no text on the pages.",
    NEG])
jobs = [{"job_id": "GINTRO", "kind": "grid2x2", "scope": "intro-bg1..4",
         "final_request_text": PROMPT}]
(RUN / "grid-manifest-intro.json").write_text(
    json.dumps({"jobs": jobs}, ensure_ascii=False, indent=2), encoding="utf-8")
print("ok")
