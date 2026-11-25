"""Generate the registered source for the door impact shot."""
from pathlib import Path

from generate import generate

DESCRIPTION = (
    "LOCKED INTERIOR DOOR EVIDENCE SHOT, crisp high-contrast cel illustration with thicker sharply "
    "defined ink boundaries and strongly separated bright and dark flat color blocks. Neutral eye-level "
    "almost straight-on shot from INSIDE an old stone forest cabin. Entire five-plank wooden door from "
    "head to threshold, its rectangular edges entirely on screen, placed on the right two thirds. "
    "Warm stove light from left casts clear bright amber shapes across honey-brown worn planks and "
    "the cool ivory-grey rough stone jamb. Expose for the door and the physical evidence. "
    "A single dark horizontal square-ended sliding iron bar, visibly 25 percent of total image width, "
    "on the INSIDE face of the door, goes snugly into a small fixed iron keeper on the RIGHT stone jamb. "
    "The small keeper has two pale screw heads and the immediately adjoining plank has a nick under it. "
    "The door is fully closed and secured. Solid braced structure and crisply readable fittings. "
    "Foreground worn split firewood and chipped enamel cup on a scuffed hearth slab in the lower left. "
    "Right stone jamb has cracked mortar; paint scuffed on the wood. A small cold blue light at the "
    "bottom seam from snow outside. Exactly zero people and humanoid silhouettes. Keep midtones clear and bright."
)

if __name__ == "__main__":
    raise SystemExit(0 if generate("door-hero", Path("image/plates/door-hero.png"), DESCRIPTION, "dkl-b", cel=True) else 1)
