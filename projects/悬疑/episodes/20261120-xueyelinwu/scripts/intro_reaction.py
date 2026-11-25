"""Generate the second approved introductory still, a restrained reaction."""
from pathlib import Path
import tempfile

from PIL import Image

from generate import EP, characters, generate
from shots import LockedRouting, reference_sheet, resize

SOURCE = Path("image/intro/source-02.png")
DESTINATION = EP / "image/intro/v1/悬疑_雪夜林屋_引入_02_v1.png"
CAST = ("narrator", "zhao")
PROMPT = (
    "An illustrated story still at 2am inside the same stone and timber mountain cabin. "
    "The reference left panel is the room and door; the two panels stacked on the far right "
    "are identity references only, upper narrator, lower Zhao. Use a different, low diagonal "
    "angle at the level of two Chinese university-age hikers sitting up close to their bags. "
    "Exactly two people. Frame from waist up, with their faces in three-quarter profile at two "
    "different depths, facing a sound to the right. The slimmer young man in a navy coat and "
    "pale gray collar has stopped halfway through getting up, brows pinched and lips slightly "
    "parted. The stockier man in a dull olive coat has turned his head abruptly toward the "
    "closed door, with one hand quietly bracing against the floor. Small, believable signs of "
    "alarm: rigid shoulders, eyes fixed on the door, a worried glance without screaming, "
    "dramatic gestures, raised weapons or wide-open mouth. The two young faces are the first "
    "read. Keep a closed wooden door at the right in the middle distance, ordinary scale and "
    "no close view of its fittings. No person or silhouette outside. Low ember light makes "
    "sharp amber shapes on their cheeks and the worn cuffs; a colder blue reflection on the "
    "scratched planks and chipped mortar. A chipped enamel cup by the hearth edge. Dark room, "
    "but no crushed shadows or soft focus on the faces. A single full-bleed 16:9 composition; "
    "no split screen, borders, lettering, or effects that represent sound. "
    + " ".join(characters[who] for who in CAST)
)

with tempfile.TemporaryDirectory(prefix="snow-cabin-intro-") as folder:
    reference = Path(folder) / "cabin-and-cast.png"
    reference_sheet(reference, EP / "image/plates/door-hero.png", CAST)
    with LockedRouting():
        ok = generate("intro-02", SOURCE, PROMPT, "dkl-b", reference=reference, cel=True)
if not ok:
    raise SystemExit(1)
with Image.open(EP / SOURCE) as im:
    resize(im).save(DESTINATION)
