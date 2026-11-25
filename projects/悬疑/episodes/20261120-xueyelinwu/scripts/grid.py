"""Generate one four-panel group for the ordinary indoor reaction shots."""
from pathlib import Path
import json
import tempfile

from PIL import Image
from generate import EP, generate, characters, cabin
from shots import LockedRouting, ROWS, resize, reference_sheet

IDS = ("S13", "S14", "S17", "S23")
SLOTS = ("top left", "top right", "bottom left", "bottom right")
assert (EP / "qa/pilot.md").is_file()
cast = ("narrator", "zhao", "keeper")
introduction = (
    "A 2x2 contact sheet of FOUR DIFFERENT 16:9 cel-animation stills at exactly equal "
    "quadrants. Seamless abutting edges, no labels, no lettering, no black bars, no gutters. "
    "The image on the left of the reference is the empty cabin layout reference. "
    "The reference's three right-side rows show narrator, Zhao and keeper, respectively. "
    "The storyboard starts after 2am. Keep damp parka cuffs, hard-edged flat colors, "
    "lower stove embers, individual hairstyles. No Sun, no unseen caller made visible, "
    "no new event. Follow the exact casting and view for each quadrant. "
)
panels = []
for slot, key in zip(SLOTS, IDS):
    row = ROWS[key]
    selected = "; ".join(characters[i] for i in row["character_ids"])
    panels.append(f"{slot.upper()}: Exactly {len(row['character_ids'])} figures, "
                  f"and only these identities: {selected}. {row['visual']}")

grid = Path("image/plates/cabin-reactions-grid.png")
with tempfile.TemporaryDirectory(prefix="snow-cabin-grid-") as tmp:
    ref = Path(tmp) / "ref.png"
    reference_sheet(ref, EP / "image/plates/S05.png", cast)
    with LockedRouting():
        ok = generate("cabin-reactions-grid", grid, introduction + cabin + "\n" +
                      "\n".join(panels), "dkl-b", reference=ref, cel=True)
if not ok:
    raise SystemExit(1)
with Image.open(EP / grid) as image:
    w, h = image.size
    for index, key in enumerate(IDS):
        x, y = index % 2, index // 2
        dst = EP / f"image/final/{key}.png"
        if (EP / f"logs/{key}.json").exists() and dst.is_file():
            continue  # An accepted independent replacement takes precedence.
        resize(image.crop((x*w//2+4, y*h//2+4, (x+1)*w//2-4, (y+1)*h//2-4))).save(dst)
(EP / "logs/grid-manifest.json").write_text(json.dumps(
    {"grid": str(grid), "reference": "S05 empty plate and locked cast",
     "panel_specs": {key: {"slot": slot, "prompt": prompt} for slot, key, prompt in zip(SLOTS, IDS, panels)}},
    indent=2, ensure_ascii=False) + "\n")
