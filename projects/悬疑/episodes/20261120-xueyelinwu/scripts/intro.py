"""Generate the approved cold open as a text-free still."""
from pathlib import Path

from PIL import Image

from generate import EP, generate
from shots import LockedRouting, resize

source = Path("image/intro/source.png")
target = EP / "image/intro/v1/悬疑_雪夜林屋_引入_01_v1.png"
prompt = (
    "One ominous illustrated shot, no people anywhere. Floor height view in the old stone "
    "ranger cabin after midnight, a tightly framed unmistakably EMPTY faded ochre sleeping bag "
    "with its top flap fully unzipped and folded away lies across the lower-left foreground, "
    "its empty dark lining and worn seams completely visible. In the middle distance at the "
    "right stands the CLOSED, tall worn wood plank door, resembling the reference. "
    "No visible figure or silhouette outside, no face, no outdoor view, no action effects, "
    "do not feature any door hardware in closeup. Chipped mortar and scratched planks, one old "
    "enamel cup beside a sliver of hearth on the far left. Thin cold blue rim at the base of "
    "the closed door contrasts with dying amber embers, enough light to read both the empty "
    "sleeping bag and closed door. Claustrophobic rough wall edges and floor perspective, "
    "hard graphic shapes and purposeful asymmetry, no white border, absolutely no words. "
    "Use the supplied reference for room materials and the appearance of the closed door only. "
    "Change the camera height and composition as described. The bag is the clear focal point."
)
with LockedRouting():
    ok = generate("intro-01", source, prompt, "dkl-b",
                  reference=EP / "image/plates/door-hero.png", cel=True)
if not ok:
    raise SystemExit(1)
target.parent.mkdir(parents=True, exist_ok=True)
with Image.open(EP / source) as im:
    resize(im).save(target)
