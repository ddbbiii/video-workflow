from pathlib import Path
import concurrent.futures
import json
import shutil
import sys

from PIL import Image

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[3]
sys.path.insert(0, str(EP / "scripts"))
import generate as g

CANDIDATES = EP / "image/candidates-v2"
PLATES = CANDIDATES / "plates"
AGE_ANCHOR = CANDIDATES / "zhou-43.png"

g.SCENES = {
    "mall": (
        "Closed indoor older Chinese shopping mall basement concourse. The escalator is on the left, "
        "a dark stone plinth with one chipped corner beside it, and a scratched steel railing runs along "
        "the right. The old hotpot storefront is on the far wall. Low basement ceiling, worn tile grout, "
        "grey-blue fluorescent ambient light and one small warm storefront lamp. No windows, trees, sky, "
        "daylight, street view, outdoor plants, readable text, or people."
    ),
    "entrance": (
        "Interior view from inside an old self-service hotpot restaurant toward its entrance. The compact "
        "cashier counter is immediately left of the entry with a plain scanner and stacked empty trays; "
        "the doorway leads to an enclosed basement concourse, never outdoors. The central buffet island is "
        "visible deeper inside. Worn tile, scratched counter, faded yellow pillar, cold ceiling light and "
        "one warm practical lamp. No windows, trees, sky, logos, lettering, or people."
    ),
    "table": (
        "The single recurring booth in the same enclosed basement hotpot restaurant: two teal vinyl bench "
        "seats face each other across one scratched brown square table with exactly two small steel hotpots "
        "in black induction rings and two plain dipping bowls. A square yellow pillar with a pale rectangular "
        "tape scar stands immediately left of the booth; a frosted glass partition is on its right. Through "
        "the gap behind the right bench, the same red-handled drink dispenser is visible. The two long "
        "parallel chest-freezer rows form one central island farther away and block the view of the far exit. "
        "No windows or exterior view. Scuffed floor and table edges, readable midtones, one warm overhead "
        "lamp against cold grey-blue ambient light."
    ),
    "counter": (
        "The same self-service hotpot buffet every time: two long parallel brushed-steel chest-freezer rows "
        "form one central island and create a narrow aisle along its left edge. The aisle connects the seating "
        "booth to the red-handled drink dispenser near the booth end, then continues past frozen-food trays "
        "to a square yellow pillar with one pale rectangular tape scar at the far bend. A return path wraps "
        "around the same freezer island; do not create a second restaurant or unrelated corridor. The glass "
        "door is only at the far end behind the island. Enclosed basement, no windows, trees, sky or outdoor "
        "view. Scratched freezer rims, chipped floor tiles, cold grey-blue ceiling light and one warm pool."
    ),
    "drinks": (
        "The drink station attached to the right-rear edge of the same buffet counter, not a separate room. "
        "One waist-high brushed steel dispenser with exactly two transparent rectangular reservoirs of dark "
        "plum juice and two red pull handles, a metal drip tray, and a short stack of clear tumblers. The same "
        "yellow pillar with pale tape scar is behind it; freezer island edge continues into the background. "
        "Enclosed basement with no windows or exterior view, scratched surfaces, cold grey-blue light and one "
        "small warm ceiling lamp. No writing or people."
    ),
    "threshold": (
        "One full-height hinged restaurant EXIT doorway with a chipped grey jamb and a single vertical metal "
        "push bar, wide enough for a person to walk through. The doorway opens directly into the same enclosed "
        "mall basement concourse; escalator on the left and dark railing on the right. This is a normal human "
        "entry door, not a refrigerator: absolutely no glass-front freezer cabinets, display cases, merchandise "
        "shelves, or rows of cabinet handles anywhere in this frame. Restaurant floor tile lines continue across "
        "the sill; a small part of the restaurant interior is visible beside the doorway. No portal effects, "
        "windows, trees, sky, street or lettering. Worn restaurant surfaces, renovated mall surfaces, cold "
        "grey-blue ambient light and a small warm restaurant lamp."
    ),
    "mall_after": (
        "The exact same enclosed basement concourse as the older mall scene, same camera direction, escalator "
        "on the left, railing on the right, and the same dark stone plinth with its single chipped corner in "
        "the same place. Eleven years later the floor, railing and ceiling are renovated; the storefront at the "
        "old hotpot restaurant position is now a neutral pharmacy with plain packages and no readable labels. "
        "No restaurant furniture, no windows, trees, sky or outdoor view. Cool clean overhead lighting with "
        "subtle wear and realistic midtone detail."
    ),
    "service": (
        "Service desk inside the same renovated basement concourse, positioned beside the left-side escalator "
        "and within sight of the same dark stone plinth with one chipped corner. One worn pale counter with "
        "a chipped front corner; a single closed folder, plain grey landline phone and blank paper are on top. "
        "The pharmacy remains far across the concourse, not behind the desk. No staff, logos, readable text, "
        "windows, plants or outside view. Cool overhead light with one small warm desk lamp."
    ),
    "noodle": (
        "A modest enclosed Chinese noodle shop downstairs at night, clearly separate from the hotpot restaurant. "
        "One worn square laminate table, two plain wooden stools, two small steaming noodle bowls, and a black "
        "vinegar bottle on the distant counter. Chipped floor tile, taped fan cable, stacked plain chopstick "
        "sleeves. No hotpot equipment, teal booth, yellow pillar, freezer or red drink dispenser. Cold grey-blue "
        "room light with one warm practical lamp; no people, text or posters."
    ),
}

g.CHAR["zhou_old"] = (
    "The SAME Zhou eleven years later, exactly 43, still clearly recognizable and not elderly. Same broad oval "
    "face and small mole beside the LEFT eyebrow. The eleven years must read clearly at a glance: visible grey "
    "at both temples, deeper forehead creases, fine but distinct crow's feet, pronounced tired under-eye hollows, "
    "defined nasolabial folds, leaner cheeks, subtle neck lines, weathered dry skin. Charcoal casual jacket over "
    "olive shirt, dark trousers, black shoes. Slight protective limp on the left ankle; shoulders a little lowered "
    "from years of waiting. No beard, no full white hair, no extreme elderly wrinkles, no change to face identity."
)

def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def build_plates():
    PLATES.mkdir(parents=True, exist_ok=True)
    names = list(g.SCENES)
    def one(pair):
        i, name = pair
        tag = "rebuild-v2-plate-threshold-exit" if name == "threshold" else f"rebuild-v2-plate-{name}"
        out = g.generate(tag, "EMPTY ENVIRONMENT ONLY. ZERO PEOPLE OR FIGURES. " + g.SCENES[name], None, False, g.CHANNELS[i % len(g.CHANNELS)])
        dest = PLATES / f"{name}.png"
        shutil.copyfile(out, dest)
        print(f"PLATE_READY {name} {Image.open(dest).size}", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(one, enumerate(names)))
    tag = "rebuild-v2-anchor-zhou-43"
    prompt = (
        "One three-quarter full-body character reference on a plain neutral grey ground, arms relaxed, full shoes "
        "visible, no scene, no text. Age the attached exact Zhou identity by eleven years to exactly 43. "
        + g.CHAR["zhou_old"] + " Keep his recognizable face and left-eyebrow mole."
    )
    out = g.generate(tag, prompt, EP / "image/anchors/zhou.png", True, g.CHANNELS[0])
    shutil.copyfile(out, AGE_ANCHOR)
    print(f"AGE_ANCHOR_READY {Image.open(AGE_ANCHOR).size}", flush=True)

def shot(pair):
    i, s = pair
    paths = [PLATES / f"{s['scene_id']}.png"]
    for cid in s["character_ids"]:
        if cid == "chen":
            paths.extend([EP / "image/anchors/chen-front.png", EP / "image/anchors/chen-face.png"])
        elif cid == "zhou_old":
            paths.append(AGE_ANCHOR)
        else:
            paths.append(EP / "image/anchors" / f"{cid}.png")
    ref = g.refstrip(f"rebuild-v2-{s['id']}", paths)
    kind = {
        "E": "Wide establishing view from a real doorway, with foreground architecture and legible deep focus.",
        "M": "Medium eye-level 28mm deep-focus view from 3m; place people on thirds and preserve the room layout.",
        "C": "Close three-quarter deep-focus evidence view; keep the key prop large, clear and unobstructed.",
    }[s["shot_type"]]
    context = g.SCENES[s["scene_id"]]
    cast = (" EXACT CAST " + str(len(s["character_ids"])) + ": " + "; ".join(g.CHAR[c] for c in s["character_ids"])
            if s["character_ids"] else " EXACTLY ZERO people, hands, reflections or human silhouettes.")
    if "zhou" in s["character_ids"]:
        n = int(s["id"][1:])
        cast += " Zhou state: " + ("young 32-year-old before the time jump, olive overshirt, tired, left ankle injured and shoe slightly loose, light limp; no grey hair, no wrinkles." if s["id"] == "S37" else
                                   "young 32-year-old, ordinary healthy appearance." if n < 13 else
                                   "young 32-year-old with tired red eyes." if n < 16 else
                                   "young 32-year-old, tired with left ankle injury and loosened shoe." if n < 34 else
                                   "exactly 43, visibly weathered by eleven years, slight left limp.")
    content = (
        "Use reference 1 ONLY for exact architecture and location continuity. Use following references ONLY for "
        "the named character identities. Draw one complete full-frame image, never a collage or reference strip. "
        + kind + " " + context + cast + " ACTION AND PROP STATE: " + s["visual"] +
        " Main story fact to depict, never write as text: " + s["fact"] +
        " Preserve the floor plan, camera-side landmarks, and object counts from the scene bible. Do not add "
        "windows or outdoor scenery inside the basement. Phones, forms and paper have no readable text, pseudo-text, "
        "numbers or UI. Maintain crisp cel shading, worn surfaces and readable midtones."
    )
    tag = ("rebuild-v2-S28-exit-door" if s["id"] == "S28" else
           "rebuild-v2-S37-flashback" if s["id"] == "S37" else f"rebuild-v2-{s['id']}")
    out = g.generate(tag, content, ref, bool(s["character_ids"]) or s["shot_type"] == "C", g.CHANNELS[i % len(g.CHANNELS)])
    dest = CANDIDATES / f"{s['id']}.png"
    shutil.copyfile(out, dest)
    with Image.open(dest) as im:
        if im.size not in [(1672, 941), (2048, 1152)]:
            raise ValueError(f"Unexpected image size for {s['id']}: {im.size}")
    return s["id"]

def build_shots(mode):
    CANDIDATES.mkdir(parents=True, exist_ok=True)
    plan = json.loads((EP / "storyboard/SHOT_PLAN.json").read_text(encoding="utf-8"))
    pilot = {"S01", "S02", "S03", "S06", "S17", "S20", "S27", "S28", "S29", "S34", "S35", "S41"}
    rows = [(i, s) for i, s in enumerate(plan["shots"]) if mode == "shots" or s["id"] in pilot]
    def lane(n):
        for pair in rows[n::2]:
            print("SHOT_READY", shot(pair), flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lane, range(2)))
    tags = ["rebuild-v2-S37-flashback" if s["id"] == "S37" else f"rebuild-v2-{s['id']}" for _, s in rows]
    g.sheet(tags, f"rebuild-v2-{mode}.jpg")

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in {"plates", "pilot", "shots"}:
        raise SystemExit("Usage: rebuild_visuals.py plates|pilot|shots")
    if sys.argv[1] == "plates":
        build_plates()
    else:
        build_shots(sys.argv[1])
