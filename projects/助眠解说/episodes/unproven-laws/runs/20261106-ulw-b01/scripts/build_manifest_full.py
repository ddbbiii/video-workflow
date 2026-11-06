# -*- coding: utf-8 -*-
"""Build the full image manifest for unproven-laws (36 grids + 17 singles). No API calls."""
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
    "Recurring prop when present: two small spheres of EQUAL diameter about 8 cm, one matte "
    "dark iron gray with a slightly pitted surface, one pale unfinished wood with visible "
    "grain; keep their relative size and material identical in every panel. Period: late "
    "Renaissance to early modern Europe; materials are iron, brass, wood, paper, glass and "
    "stone. No modern objects. No faces; a hand may appear, but never a head or body."
)
NEG = (
    "Global negatives: no text, no letters, no numbers, no labels, no captions, no watermark, "
    "no arrows, no diagrams, no charts, no UI, no border, no panel numbers, no modern objects, "
    "no faces, no extra spheres, no duplicated objects, no object floating without a shadow, "
    "no chromatic aberration, no lens flare."
)

GRIDS = []


def g(job, scope, panels):
    assert len(panels) == 4, job
    body = []
    for i, p in enumerate(panels, 1):
        tag = ["top-left", "top-right", "bottom-left", "bottom-right"][i - 1]
        body.append("Panel %d (%s): %s" % (i, tag, p))
    GRIDS.append({"job_id": job, "kind": "grid2x2", "scope": scope,
                  "final_request_text": "\n\n".join([HEADER, SHARED] + body + [NEG])})


def s(job, scope, text):
    GRIDS.append({"job_id": job, "kind": "single", "scope": scope,
                  "final_request_text": "\n\n".join([
                      "A single 2048x1152 cinematic photograph: " + text,
                      STYLE + ". No text, no letters, no numbers, no labels, no watermark, no faces."])})


# ---------------- c0 开场 ----------------
g("G01", "c0-s03/s04/s06/spare", [
    "Low angle from the foot of a leaning stone tower at dusk; two small spheres, one dark iron and one pale wood, are caught in mid-air a little apart, falling toward a patch of grass; a faint puff of dust rises below; weathered stone at the left frame edge, warm amber sky behind, deep teal shadows.",
    "Ground-level close shot on trampled grass; the same two spheres rest side by side with equal-length soft shadows, dew on the blades, shallow depth of field, dusk amber side light, deep teal background.",
    "An open old book on a dark wooden desk, worn page edges, pages softly blank and unreadable, a lit candle beside it, warm amber pool of light on the paper, deep teal background, a thin thread of smoke.",
    "Closer variant of the falling pair: the two spheres large in frame against the amber sky, still apart, dust and a few grass blades lifted by the air, motion implied but not streaked.",
])
g("G02", "c0-s07/s08/s09/s10", [
    "A plain night sky filled with stars, no horizon, no landscape, deep blue-black with a faint atmospheric glow near the lower edge; extremely calm, no Milky Way band, no constellation lines.",
    "An hourglass on a dark wooden table, sand mid-flow in a thin stream, single warm side light, deep teal background, no numerals, no markings, no engraving.",
    "A slate blackboard seen slightly from the side; one single chalk line is half-erased, chalk dust falling in cool window light from the left; the board is otherwise empty, no letters, no numbers, no diagrams.",
    "Top-down on a dark wood table; two spheres, one dark iron and one pale wood, roll toward each other with soft contact shadows, a warm overhead lamp, deep teal edges, no hands.",
])

# ---------------- c1 碰撞 ----------------
g("G03", "c1-s01..s04", [
    "A billiard table under a low green-shaded lamp; one ivory-white ball at rest on the green felt, its reflection soft, the room dark beyond, warm pool of light, deep teal shadows.",
    "A wooden cue stick entering frame from the right, a hand at its butt end (no face), chalk dust on the tip, the white ball just ahead, warm lamp light, shallow depth of field.",
    "Two billiard balls in the instant of collision, chalk dust lifted between them, the impact point crisp, warm top light, deep teal background, no table markings.",
    "The two balls separated and rolling toward the dark rails, one toward the left cushion, one toward the right, soft motion, green felt, warm lamp pool, calm.",
])
g("G04", "c1-s05..s08", [
    "A billiard ball come to rest against the dark wooden rail of the table, still, a faint scuff of chalk on the felt, warm side light, deep teal shadows.",
    "A narrow beam of warm light through a dark room, fine dust motes drifting slowly in the beam, no objects, no text, deep teal air.",
    "A wooden table leg and the floorboards beneath it, dust settled in the grain, a soft shadow, warm low light, deep teal background.",
    "The curved limb of Earth seen from space at night, thin blue atmosphere, slow cloud bands, a few city lights on the dark side, deep blue-black space, no labels.",
])
g("G05", "c1-s09..s12", [
    "A dark sea at night, a single slow swell rising and falling under moonlight, no shore, no boat, deep teal water with a silver path of light.",
    "A city at night seen from above, long-exposure light trails of traffic drawn as thin continuous lines between dark buildings, warm amber and deep teal, no signage or text.",
    "An old ledger open on a desk, page edges worn, the pages softly blank and unreadable, a quill resting in the gutter, warm candlelight from the left, deep teal shadows.",
    "A brass balance scale on a dark wooden table, one pan slightly lower, the beam settling, a single candle behind, warm highlights on the brass, deep teal background.",
])
g("G06", "c1-s13..s16", [
    "A wooden abacus on a dark table, rows of warm wooden beads, no numerals or markings, a single candle at the edge, deep teal shadows, shallow depth of field.",
    "Two lumps of soft clay in the instant of collision, one dark gray, one pale ochre, deforming and beginning to stick together, a neutral dark background, warm side light.",
    "The joined clay lump on a dark surface, a thin thread of steam rising from the seam, warm side light, deep teal background.",
    "Two hands (no face) pulling the joined clay apart, leaving a torn seam and fingerprints, dark wooden table, warm side light, deep teal shadows.",
])
g("G07", "c1-s21..s24", [
    "A slate blackboard filling the frame, one small chalk dot near the center, the rest empty, chalk dust faintly visible, cool side light, no text or lines.",
    "The same blackboard seen from farther back in a dark classroom, the single chalk dot now tiny, rows of empty desks in shadow, cool window light.",
    "A window at night, the shadow of a tree branch moving slowly across the wall beside it, warm interior light against deep teal darkness, no text.",
    "A single candle flame close up in a dark room, the flame steady and soft, warm amber core, deep teal background, no smoke ring, no flicker.",
])
g("G08", "spares-c1", [
    "Two clay lumps colliding again, a different angle, one compressing the other, warm side light, dark neutral background, no hands.",
    "A Newton's cradle of five brass spheres at rest on a dark wooden base, warm side light, deep teal background, no text or engraving.",
    "Two billiard balls colliding at a slight angle, chalk dust, green felt, warm lamp light, deep teal background.",
    "A single iron sphere resting in the palm of a hand (no face), the fingers curled loosely, warm side light, deep teal background.",
])

# ---------------- c2 两个人的半个世纪 ----------------
g("G09", "c2-s01..s04", [
    "A seventeenth-century study at night: a cluttered desk with books, a brass candlestick, a globe, a tall window with leaded panes, warm candlelight pooling on the wood, deep teal shadows.",
    "A close shot of a white quill writing on aged paper, the ink marks soft and unreadable, a dark cuff at the edge, warm candlelight from the right, deep teal shadow.",
    "A hand (no face) closing a thick leather-bound book, the cover plain and unmarked, candlelight on the worn leather, deep teal background.",
    "A man's silhouette from behind, seated at a desk by a tall window, hat and shoulders only, no face, candlelight rimming his outline, deep teal room.",
])
g("G10", "c2-s05..s08", [
    "A brighter seventeenth-century study: stacks of letters tied with ribbon, a writing slope, a window with morning light, warm wood and paper tones against deep teal shadows.",
    "A letter opener slicing the fold of a sealed letter, a hand (no face) holding it, wax seal cracking, warm side light, dark desk.",
    "Two sealed letters side by side on a dark desk, red wax seals blank and unmarked, a candle at the edge, warm highlights, deep teal background.",
    "A man's silhouette from behind, hunched over a desk, quill in hand, candlelight from the left, no face, deep teal shadows.",
])
g("G11", "c2-s09..s11+s13", [
    "Two brass spheres, one large and one small, rolling down a shallow wooden incline, warm side light, dark background, no markings or numbers.",
    "Two pendulums of different lengths hanging from a wooden beam, both released from the same height, brass bobs, warm side light, deep teal background.",
    "The two pendulum bobs crossing in mid-air at different heights, blurred only slightly, warm brass highlights, deep teal shadows.",
    "Three folded manuscripts on a dark table, pages softly blank and unreadable, a candle and a pair of brass dividers beside them, warm light, deep teal background.",
])
g("G12", "c2-s15..s18", [
    "A Parisian salon at night: a small table with wine glasses, candlelight, blurred figures in the background as soft silhouettes, no faces, warm amber against deep teal.",
    "A hand (no face) pushing two chess pieces side by side on a dark board, the pieces plain, warm candlelight, deep teal background.",
    "Two oil lamps on a dark table, one burning brightly, the other nearly out, warm amber pools shrinking, deep teal shadows.",
    "Pages of an open book lifted by a draft, caught mid-turn, warm candlelight from the side, deep teal background, no text.",
])
g("G13", "c2-s19..s21+spare", [
    "A tall window at night, a distant bell tower silhouette against deep blue, one warm window lit in the tower, calm.",
    "Two books on a dark desk, one closed and one open, a candle between them, warm light on worn leather, deep teal shadows.",
    "A candle just extinguished, a thin curl of smoke rising, the wick still orange, deep teal darkness around, calm.",
    "A hand (no face) closing a leather notebook on a dark desk, candlelight from the side, deep teal shadows.",
])

# ---------------- c3 牛顿的舞台 ----------------
g("G14", "c3-s01..s04", [
    "A wooden desk by a window at night: a glass prism, a candle, a leather-bound book, warm light entering the prism, deep teal shadows.",
    "A beam of white light passing through a glass prism and spreading into a soft band of colour on the desk, no labels or diagrams, warm highlights, deep teal room.",
    "A hand (no face) turning the prism slowly, the colour band shifting across the wood, warm light, deep teal shadows.",
    "An open book on a desk, page edges worn, pages softly blank and unreadable, a candle beside it, warm light, deep teal background.",
])
g("G15", "c3-s05/s11..s13", [
    "A brass compass drawing a circle on a sheet of paper, the needle fixed at the centre, a hand (no face) turning it, warm side light, no text or numbers.",
    "An empty room with one wooden chair in a shaft of window light, dust motes drifting, deep teal shadows, no people.",
    "The same chair from a different angle, the light now on the seat, dust in the air, warm amber and deep teal.",
    "A tree's shadow moving slowly across a plaster wall, late afternoon light, deep teal room, no window frame visible.",
])
g("G16", "c3-s14..s17", [
    "Still water at night reflecting a field of stars, the surface almost glass, deep blue-black, a faint ripple at the edge.",
    "A single drop striking still water, a ring of ripples expanding, starlight broken on the surface, deep teal and silver.",
    "The ripples almost gone, the star reflection almost whole again, calm, deep blue-black.",
    "A pendulum clock's brass bob at the end of its swing, nearly stopped, warm side light, deep teal background.",
])

# ---------------- c4 换一种问法 ----------------
g("G17", "c4-s01..s04", [
    "Sunlight through a tall window falling on a stone floor, a bright parallelogram of light, dust in the beam, deep teal shadows.",
    "Sunlight refracting through water onto the bottom of a shallow pool, shifting caustic patterns, blue-green water, warm light, no text.",
    "A magnifying glass focusing sunlight onto a sheet of paper, a thin thread of smoke starting, a hand (no face) holding the handle, warm light, dark background.",
    "A small bead sliding down a curved iron wire, the wire mounted on a dark wooden board, warm side light, deep teal background.",
])
g("G18", "c4-s05/s07..s09", [
    "Two iron wires of different curves mounted side by side on a dark board, two beads at their starting points, warm side light, no labels.",
    "A soap film stretched across a wire frame, pulling itself into a minimal surface, soft rainbow reflections, dark background, warm rim light.",
    "A heavy iron chain hanging from two points, forming a natural curve, warm side light on the links, deep teal background.",
    "A honeycomb close-up, hexagonal cells in warm amber wax, shallow depth of field, dark background, no bees.",
])
g("G19", "c4-s10..s13", [
    "A taut rope stretched between two posts, a hand (no face) plucking it, a wave travelling along the rope, warm side light, dark background.",
    "A loose knot in a thick rope beginning to release, the rope springing, warm side light, dark wooden floor.",
    "Water running down a shallow slope, splitting into thin braided streams, warm low light, dark stone.",
    "A wide landscape seen from a slowly moving viewpoint, a field and a line of trees, warm dusk light, deep teal shadows.",
])
g("G20", "c4-s14..s16+spare", [
    "A view from a carriage window: trees and fields sliding past, the window frame dark in the foreground, warm late light, slight softness.",
    "The same carriage window at dusk, the sky deepening, the landscape darker, one warm light on the horizon.",
    "A faint reflection of a person's outline in a dark window glass, no face, warm interior light behind, deep teal outside.",
    "A single bead at the bottom of a curved wire, at rest, warm side light, dark board, no labels.",
])

# ---------------- c5 诺特 ----------------
g("G21", "c5-s01..s04", [
    "A 1918 lecture room: a large slate blackboard, rows of empty wooden chairs, tall windows with cool daylight, dust in the air, deep teal shadows.",
    "The blackboard close up, covered in faint erased chalk traces, no legible letters or numbers, cool window light from the left.",
    "A hand (no face) lifting a piece of white chalk from the board ledge, cool daylight, deep teal shadows.",
    "The same hand drawing one single long chalk arc on the blackboard, no letters, no diagram, chalk dust falling, cool light.",
])
g("G22", "c5-s06/s09..s11", [
    "A starfish resting in shallow clear water, five-fold symmetry, warm sand and cool water, soft daylight, no text.",
    "A view from a train window: fields and fences sliding past in horizontal bands, warm daylight, slight motion softness, no text.",
    "The same field from a fixed viewpoint, the camera still, cloud shadows moving across the grass, warm daylight, deep teal distance.",
    "A patch of sunlight on a plaster wall, slowly moving, the edge soft, warm amber against deep teal shadow, no objects.",
])
g("G23", "c5-s13..s16", [
    "A potter's wheel with a wet clay vessel rising under two hands (no face), the wheel spinning, warm side light, deep teal background.",
    "Concentric ripples spreading on dark still water, a single drop having just fallen, silver rings, deep blue-black.",
    "A river flowing steadily between dark banks, the water moving, the stones and banks unchanged, cool daylight, deep teal.",
    "An hourglass on a dark table, sand running from the upper bulb to the lower, the total amount unchanged, warm side light, deep teal background.",
])
g("G24", "c5-s17..s20", [
    "A night sky rotating slowly around a fixed point, star trails beginning to form, deep blue-black, no labels.",
    "Earth's limb from space with the terminator line, day on one side, night on the other, thin blue atmosphere, no labels.",
    "A framed mirror on a dark wall reflecting a single candle flame, the frame plain, warm flame against deep teal.",
    "The same mirror, the reflection trembling slightly as if the glass moved, warm flame, deep teal room.",
])
g("G25", "c5-s22+spares", [
    "Snow gathering on a dark stone windowsill, large flakes landing and melting at the edge, cool blue-grey light, deep teal shadows.",
    "A spinning brass gyroscope on a dark table, the rotor a blur, warm side light, deep teal background.",
    "A stone sundial in a garden, the shadow of the gnomon moving across the blank face, no numerals, warm daylight.",
    "Earth's curved horizon at dawn, a thin band of warm light along the limb, deep blue-black space, no labels.",
])

# ---------------- c6 规律的边界 ----------------
g("G26", "c6-s01..s04", [
    "A clear glass sphere resting on a dark wooden table, the wood grain beneath it magnified and bent, warm side light, deep teal shadows.",
    "A glass filled with water on a dark table, the background beyond it bent and displaced, warm side light, deep teal.",
    "A river bending through a dark landscape, the surface reflecting the sky, cool daylight, deep teal banks.",
    "A tidal flat at low tide, water receding in thin sheets, wet sand reflecting the sky, cool blue-grey, calm.",
])
g("G27", "c6-s05..s08", [
    "A small boat far out at sea, growing smaller with distance, calm water, cool blue-grey light, no shore.",
    "A deep-space field of galaxies, small and distant, slowly receding, deep blue-black, no labels or arrows.",
    "A heavy wooden door standing half open, a wedge of warm light falling through the gap onto a stone floor, deep teal darkness.",
    "A bare foot (no face, no body beyond the ankle) stopped on the threshold of the open door, warm light ahead, deep teal behind.",
])
g("G28", "c6-s09..s12", [
    "A cliff edge above a sea of clouds, the rock dark and wet, the clouds lit from below by a low sun, deep teal and amber.",
    "A flat horizon at dusk, sea meeting sky in a single dark line, cool blue-grey with a thin warm band, no objects.",
    "The worn edge of an old map on a dark desk, the paper frayed, the map surface softly blank and unreadable, warm side light.",
    "The same desk beyond the map's edge: bare dark wood, a faint ring from a cup, warm side light, deep teal shadow.",
])
g("G29", "c6-s13/s14/s17/s18", [
    "A hand (no face) pushing the old map slightly toward the edge of the desk, the frayed edge lifting, warm side light, deep teal.",
    "A heavy door closing slowly, the wedge of warm light narrowing to a line, dust in the gap, deep teal darkness.",
    "Rain running down a dark window at night, blurred warm lights beyond, deep teal and amber.",
    "Rainwater dripping from a dark roof edge, a single drop falling, cool blue-grey, deep teal background.",
])
g("G30", "c6-s18..s19+spares", [
    "A shallow puddle on dark stone reflecting a grey sky, a single drip breaking the surface, cool light, calm.",
    "A glass sphere on dark wood again, seen from a lower angle, the bent grain sharper, warm side light, deep teal.",
    "A cliff edge at dusk, the clouds below now deep blue, the last warm line on the horizon.",
    "A map edge lifting in a draft, the blank paper curling, warm side light, dark desk.",
])

# ---------------- c7 只能说发现 ----------------
g("G31", "c7-s01..s04", [
    "A late-night laboratory desk: a green-shaded lamp, a notebook open to a blank page, a fountain pen, warm pool of light, deep teal shadows.",
    "A hand (no face) writing the first line in the notebook, the ink marks soft and unreadable, warm lamp light, deep teal.",
    "The pen stopped on the page, a small ink blot spreading, warm lamp light, deep teal shadow.",
    "A brass telescope by a dark window, pointed at the night sky, warm interior light, deep teal outside.",
])
g("G32", "c7-s05..s08", [
    "The circular view through a telescope eyepiece: a dense field of stars, crisp at the centre, soft at the edge, deep blue-black.",
    "An observer's silhouette from behind, seated at the telescope, motionless, warm lamp light rimming the shoulders, no face.",
    "A ceramic coffee cup on the desk, a thin thread of steam rising and fading, the cup half full, warm lamp light, deep teal.",
    "A window at dawn, the sky shifting from deep blue to pale grey, the room still dark, calm.",
])
g("G33", "c7-s10..s13", [
    "Two spheres on a dark desk, one iron and one wood, side by side, warm lamp light, deep teal background.",
    "A hand (no face) setting the two spheres side by side, fingers just releasing them, warm lamp light, deep teal.",
    "The two spheres lit from the side, their shadows exactly equal in length, warm light, dark desk.",
    "A hand (no face) turning off a green-shaded lamp, the warm pool collapsing, deep teal darkness rising.",
])
g("G34", "c7-s15..s16+spares", [
    "A shelf of old books, worn spines softly blank and unreadable, warm side light, deep teal shadows.",
    "A wall clock stopped, the hands still, the face plain without numerals, warm side light, deep teal.",
    "A single star in a dark sky, soft and steady, deep blue-black, no labels.",
    "A dark room with one warm window, the rest in deep teal shadow, calm.",
])

# ---------------- c8 尾声 ----------------
g("G35", "c8-s01/s03..s05", [
    "A quiet bedroom at night: a warm bedside lamp, a curtain half drawn, the bed softly lit, deep teal shadows, calm.",
    "A hand (no face) gently pushing two small spheres together on a bedside table, warm lamp light, deep teal room.",
    "A city at night seen through a bedroom window, the lights soft and out of focus, warm and deep blue.",
    "A clear night sky above the city, stars steady, deep blue-black, calm.",
])
g("G36", "c8-s06..s08+spare", [
    "The moon with thin cloud passing across it, soft silver light, deep blue-black sky, calm.",
    "A curtain lifting slightly in a night breeze, warm lamplight behind it, deep teal shadows.",
    "A hand (no face) turning down a bedside lamp, the warm light dimming, deep teal room.",
    "The bedroom almost dark, only a faint warm line under the curtain, calm.",
])

SINGLES = [
    ("S01", "c0-s01", "A leaning stone tower at dusk, seen from its base with a low angle, the tower leaning diagonally across the frame; warm amber sky, deep teal shadows, weathered stone with fine texture, soft atmospheric haze."),
    ("S02", "c0-s02", "A stone parapet at the top of a tower at dusk; two small spheres of equal diameter rest side by side on the worn stone, one matte dark iron gray and one pale unfinished wood, equal soft shadows, shallow depth of field, warm amber side light, deep teal background."),
    ("S03", "c0-s05", "A candlelit wooden desk, close shot; a hand with a dark wool cuff and a white lace cuff (no face) holds a white quill just above a completely blank sheet of aged paper, no writing or ink marks; a small glass ink pot and a brass candlestick at the right, warm candlelight, deep teal shadows, shallow depth of field."),
    ("S04", "c1-s17", "A Newton's cradle of five polished brass spheres hanging from a dark wooden frame, at rest, warm side light, deep teal background, no text or engraving."),
    ("S05", "c2-s12", "A long table in a seventeenth-century meeting room, candles in brass stands, empty wooden chairs, tall windows with night beyond, warm candlelight, deep teal shadows, no people."),
    ("S06", "c2-s14", "A Huygens-style pendulum clock on a wooden stand, brass bob and weight, the case plain and unmarked, warm side light, deep teal shadows."),
    ("S07", "c3-s06", "A brass orrery on a dark wooden table, small planets on thin arms, slowly turning, warm side light on the brass, deep teal background, no labels or numbers."),
    ("S08", "c3-s07", "A close-up of a brass clock escapement: gears and a pallet fork, precise and clean, warm side light, deep teal shadows, no numerals."),
    ("S09", "c3-s08", "A long-case pendulum clock, the brass bob swinging steadily, the case dark wood and plain, warm side light, deep teal background."),
    ("S10", "c3-s09", "An empty room with one wooden chair in a shaft of window light, dust motes drifting, deep teal shadows, no people, calm."),
    ("S11", "c4-s06", "A large soap bubble floating in a dark room, its surface showing slow flowing rainbow films, warm backlight, deep teal background."),
    ("S12", "c5-s05", "A single large snowflake landing on a dark wool sleeve, its six-fold structure just visible before melting, cool blue-grey light, deep teal background."),
    ("S13", "c5-s07", "A spinning brass gyroscope on a dark wooden table, the rotor a soft blur, the frame steady, warm side light, deep teal background."),
    ("S14", "c5-s12", "A stone sundial in a garden, the shadow of the gnomon moving across the blank face, no numerals or markings, warm daylight, deep teal shadows."),
    ("S15", "c5-s23", "A close-up of clock gears, brass teeth meshing slowly, warm side light, deep teal shadows, no numerals."),
    ("S16", "c7-s09", "Two spheres on a dark desk, one matte iron gray and one pale wood, equal diameter, side by side, warm lamp light, deep teal background."),
    ("S17", "c8-s02", "Two small spheres on a bedside table at night, one iron gray and one pale wood, warm lamp light, deep teal room, calm."),
]

jobs = GRIDS + [{"job_id": jid, "kind": "single", "scope": scope, "final_request_text": None} for jid, scope, _ in SINGLES]
for jid, scope, text in SINGLES:
    for j in jobs:
        if j["job_id"] == jid:
            j["final_request_text"] = "\n\n".join([
                "A single 2048x1152 cinematic photograph: " + text,
                STYLE + ". No text, no letters, no numbers, no labels, no watermark, no faces."])
manifest = {
    "episode": "unproven-laws", "batch": "20261106-ulw-b01", "stage": "full_stills",
    "model": "gpt-image-2.5-sunburst", "size": "2048x1152",
    "grids": sum(1 for j in jobs if j["kind"] == "grid2x2"),
    "singles": sum(1 for j in jobs if j["kind"] == "single"),
    "planned_calls": len(jobs), "jobs": jobs,
}
out = RUN / "grid-manifest-full.json"
out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote", out)
print("grids", manifest["grids"], "singles", manifest["singles"], "calls", manifest["planned_calls"])
for j in jobs:
    print(j["job_id"], j["kind"], j["scope"], len(j["final_request_text"]))
