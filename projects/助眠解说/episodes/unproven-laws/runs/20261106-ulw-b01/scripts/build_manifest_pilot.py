# -*- coding: utf-8 -*-
"""Build the c0 pilot manifest for unproven-laws. No API calls."""
import json
from pathlib import Path

RUN = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws\runs\20261106-ulw-b01")

STYLE = (
    "cinematic historical science documentary, photorealistic, deep teal-blue shadows with "
    "controlled warm amber highlights, volumetric light, fine material texture, layered depth, "
    "asymmetrical cinematic composition, calm dreamlike mood, 16:9 widescreen"
)

HEADER = (
    "Create ONE single 2048x1152 image laid out as EXACTLY a 2x2 grid of four independent, "
    "complete 16:9 landscape scenes. Each scene fills exactly one quadrant (about 1024x576); "
    "the quadrants are separated only by thin straight dividers along the exact vertical and "
    "horizontal center lines, with no outer frame. The four panels are mutually independent "
    "shots: nothing crosses a divider; no object, light beam, horizon or texture continues "
    "from one panel into another; each panel has its own camera, subject and composition. "
    "Do not draw any text, letters, numbers, panel numbers, captions, labels or watermarks "
    "anywhere in the image."
)

SHARED = (
    "Shared world and style for all four panels: " + STYLE + ". "
    "Recurring prop when present: two small spheres about 8 cm across, one matte dark iron "
    "gray with a slightly pitted surface, one pale unfinished wood with visible grain; keep "
    "their relative size and material identical in every panel. Period: late Renaissance to "
    "early modern Europe; materials are iron, brass, wood, paper, glass and stone. No modern "
    "objects. No faces; a hand may appear, but never a head or body."
)

NEG = (
    "Global negatives: no text, no letters, no numbers, no labels, no captions, no watermark, "
    "no arrows, no diagrams, no charts, no UI, no border, no panel numbers, no modern objects, "
    "no faces, no extra spheres, no duplicated objects, no object floating without a shadow, "
    "no chromatic aberration, no lens flare."
)

G01 = "\n\n".join([
    HEADER,
    SHARED,
    "Panel 1 (top-left): low angle from the foot of a leaning stone tower at dusk. Two small "
    "spheres, one dark iron and one pale wood, are caught in mid-air a little apart, falling "
    "toward a patch of grass; a faint puff of dust rises below them. The weathered stone base "
    "of the tower is soft at the left frame edge, warm amber sky behind, deep teal shadows. "
    "No people, no hands.",
    "Panel 2 (top-right): ground-level close shot on trampled grass. The same two spheres rest "
    "side by side, dark iron and pale wood, with equal-length soft shadows; dew on the blades, "
    "shallow depth of field, dusk amber side light, deep teal background. No people.",
    "Panel 3 (bottom-left): candlelit wooden desk, close shot. A single hand with a dark cuff "
    "(no face, no head) holds a white quill and writes on aged paper; the ink marks stay soft "
    "and unreadable. Warm candlelight from the right, deep teal shadow, faint dust in the air.",
    "Panel 4 (bottom-right): an open old book on a dark wooden desk, worn page edges, the pages "
    "softly blank and unreadable; a lit candle stands beside it, a warm amber pool of light on "
    "the paper, deep teal background, a thin thread of smoke.",
    NEG,
])

G02 = "\n\n".join([
    HEADER,
    SHARED,
    "Panel 1 (top-left): a plain night sky filled with stars, no horizon, no landscape, deep "
    "blue-black with a faint atmospheric glow near the lower edge; extremely calm, no Milky Way "
    "band, no constellation lines.",
    "Panel 2 (top-right): an hourglass on a dark wooden table, sand mid-flow in a thin stream, "
    "single warm side light, deep teal background, no numerals, no markings, no metal frame "
    "engraving.",
    "Panel 3 (bottom-left): a slate blackboard seen slightly from the side. One single chalk "
    "line is half-erased, chalk dust falling in cool window light from the left; the board is "
    "otherwise empty, no letters, no numbers, no diagrams, no frames.",
    "Panel 4 (bottom-right): top-down on a dark wood table. Two spheres, one dark iron and one "
    "pale wood, roll toward each other with soft contact shadows; a warm overhead lamp, deep "
    "teal edges, no hands, no people.",
    NEG,
])

S01 = "\n\n".join([
    "A single 2048x1152 cinematic photograph: a leaning stone tower at dusk, seen from its "
    "base with a low angle, the tower leaning diagonally across the frame. Warm amber sky, deep "
    "teal shadows, weathered stone with fine texture, soft atmospheric haze. No people, no "
    "text, no labels, no watermark. " + STYLE + ".",
])

S02 = "\n\n".join([
    "A single 2048x1152 cinematic photograph: a stone parapet at the top of a tower at dusk. "
    "Two small spheres rest side by side on the worn stone, one matte dark iron gray and one "
    "pale unfinished wood, with equal soft shadows. Shallow depth of field, warm amber side "
    "light, deep teal background. No hands, no people, no text, no labels, no watermark. "
    + STYLE + ".",
])

jobs = [
    {"job_id": "G01", "kind": "grid2x2", "scope": "c0-s03/s04/s05/s06", "final_request_text": G01},
    {"job_id": "G02", "kind": "grid2x2", "scope": "c0-s07/s08/s09/s10", "final_request_text": G02},
    {"job_id": "S01", "kind": "single", "scope": "c0-s01", "final_request_text": S01},
    {"job_id": "S02", "kind": "single", "scope": "c0-s02", "final_request_text": S02},
]

manifest = {
    "episode": "unproven-laws",
    "batch": "20261106-ulw-b01",
    "stage": "pilot_c0",
    "model": "gpt-image-2.5-sunburst",
    "size": "2048x1152",
    "planned_calls": 4,
    "jobs": jobs,
}
out = RUN / "grid-manifest.json"
out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote", out, "jobs", len(jobs))
for j in jobs:
    print(j["job_id"], j["kind"], j["scope"], len(j["final_request_text"]))
