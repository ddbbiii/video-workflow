"""Create static frames with the episode's locked reference material."""
import fcntl
import json
import sys
import tempfile
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageOps
from generate import EP, generate, channels, cabin, characters, api

PLAN = json.loads((EP / "storyboard/SHOT_PLAN.json").read_text())
ROWS = {row["id"]: row for row in PLAN["shots"]}
PILOT = ["S01", "S02", "S03", "S05", "S06", "S08"]
STATIC_DOOR = {
    "S07": (166, 52, 2040, 1106),
    "S15": (970, 390, 2010, 975),
    "S16": (0, 0, 2048, 1152),
    "S18": (400, 150, 2040, 1073),
    "S24": (580, 250, 2040, 1071),
    "S25": (1298, 348, 2042, 767),
    "S26": (830, 332, 2046, 1016),
    "S32": (970, 390, 2010, 975),
}
FOREST = (
    "Old Changbai mountain fir forest and a remote narrow hiking trail in winter. "
    "Wind-scoured rocks, torn fir bark, worn irregular trail marker without writing, "
    "partly covered bootprints and broken dried twigs. Snow is visibly sweeping sideways."
)


class LockedRouting:
    """Keep each API route at one request in flight, including fallback."""
    def __enter__(self):
        self.call = api.call
        api.call = self.locked_call

    def __exit__(self, *args):
        api.call = self.call

    def locked_call(self, channel, *args):
        lock_path = Path(tempfile.gettempdir()) / f"video-workflow-image-{channel['name']}.lock"
        with lock_path.open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            return self.call(channel, *args)


def resize(image, size=(1920, 1080)):
    return ImageOps.fit(image.convert("RGB"), size, method=Image.Resampling.LANCZOS)


def save_crop(shot_id, box):
    path = EP / "image/plates/door-hero.png"
    with Image.open(path) as plate:
        resize(plate.crop(box)).save(EP / f"image/final/{shot_id}.png")


def reference_sheet(path, plate, cast):
    with Image.open(plate) as source:
        stage = resize(source, (1280, 720))
    if not cast:
        stage.save(path)
        return
    ref = Image.new("RGB", (1600, 720), "#b5b5b5")
    ref.paste(stage, (0, 0))
    for index, name in enumerate(cast):
        with Image.open(EP / f"image/anchors/{name}.png") as image:
            if name != "narrator":
                w, h = image.size
                image = image.crop((int(w * .34), 0, int(w * .66), h))
            thumbnail = ImageOps.contain(image.convert("RGB"), (310, 710 // len(cast)))
        height = 720 // len(cast)
        ref.paste(thumbnail, (1280 + (320 - thumbnail.width) // 2, index * height + (height - thumbnail.height) // 2))
    ref.save(path)


def shot(shot_id, channel):
    row = ROWS[shot_id]
    cast = row["character_ids"]
    in_cabin = row["scene_id"] == "cabin"
    setting = cabin if in_cabin else FOREST
    opening = "Past midnight after 2am, stove embers, warm copper light and blue rim lights reveal the foreground silhouettes. Bright warm angular reflectance and clearly separated cool shadows, strong contrast and never a uniformly dark frame. " if int(shot_id[1:]) >= 11 else ""
    visual = row["visual"]
    if shot_id in STATIC_DOOR:
        save_crop(shot_id, STATIC_DOOR[shot_id])
        return True
    if shot_id == "S05":
        visual = (
            "Mid-shot on the single keeper seated at the left by the black stove, holding "
            "a tiny curved tobacco pipe directly at his lips with a small thread of smoke above. "
            "No long staff, weapon or tool in this shot. Let the closed door be secondary."
        )
    if shot_id == "S08":
        visual = (
            "Close view of ONE hand in the charcoal jacket sleeve entering from the LEFT edge "
            "to touch the LEFT half of the horizontal iron bar and check that it holds. "
            "Keep the right half of the hardware centered-right and entirely unobstructed. "
            "The same squared bar visibly ends inside the right-side small rectangular keeper "
            "with its two screw heads. No other person, exposed face, loose bar or handle. "
            "Crisp ink contours, directional amber from the left."
        )
    if shot_id == "S21":
        visual = (
            "Medium on two separate figures several steps apart: furious stocky Zhao in olive "
            "at center, gripping the small chopping axe low by his side with its blade isolated "
            "against the warm pale stones; keeper on left in an old burgundy scarf, alert and "
            "looking to the closed door offscreen right. No strike, no extra figures."
        )
    if shot_id == "S19":
        visual = (
            "Readable medium shot dominated by the keeper standing just to the LEFT of the stove, "
            "warm strong stove reflection on his cheek and scarf and hard-edged pale reflected "
            "light on the near stone wall. He is looking toward the closed door far right. "
            "The double barrel hunting gun is in his tense hands, kept below face level and "
            "in profile, pointing toward the empty right side of the room. No other person, "
            "no muzzle flash. Three distinct value zones, not a uniformly low-key image."
        )
    if shot_id == "S23":
        visual = (
            "Three-quarter medium view with the closed door OUT OF FRAME to the right. "
            "The narrator in navy is close to camera, one hand cupped at his mouth, "
            "calling into the empty space to the right. Zhao watches behind him; the keeper "
            "remains far left by the stove. Nobody is near the doorway, no hand extends "
            "toward it, and no one touches or reaches for door hardware."
        )
    if shot_id == "S28":
        visual = (
            "Two clearly separated men in side profile. In front on the RIGHT stands the "
            "stocky short-haired Zhao in the OLIVE jacket, holding the only woodchopping axe "
            "close to his right shoulder with bent elbow. The slim young narrator in the "
            "NAVY jacket with LIGHT GRAY collar stands behind him on the LEFT, empty hands "
            "wrapped around the olive jacket at Zhao's waist. Navy-clad hands hold no prop. "
            "Make both jacket color blocks legible, restrained pose, no strike or other actor."
        )
    if shot_id == "S33":
        visual = (
            "Return to the precise hardware on the reference door. Large centered-right view of "
            "the steel bar ending inside the wall keeper. Narrator's navy shoulder only encroaches "
            "at the left margin. Everything is in focus. Maintain hardware geometry and closed door."
        )
    if not cast:
        # An environment-only prompt contains no casting descriptions.
        return generate(shot_id, Path(f"image/final/{shot_id}.png"),
                        opening + setting + " " + visual + " Zero people.", channel,
                        cel=bool(row["evidence_id"]))
    master = EP / "image/plates" / ("interior.png" if in_cabin else "forest.png")
    plate_rel = Path(f"image/plates/{shot_id}.png")
    if shot_id in ("S08", "S33"):
        master = EP / "image/plates/door-hero.png"
    elif not in_cabin or shot_id in PILOT or shot_id in {"S10", "S11"}:
        knowledge = (
            f"Unoccupied photographed angle for an illustrated sequence. Stage, no people. {opening}{setting} "
            f"Use frame scale {row['shot_type']} and this intended background and framing: "
            + (
                "Low at frosted trees and snowy trail, with near branches for a partial frame."
                if shot_id == "S03" else
                "Side view of winter trail and a wind-erased fork."
                if shot_id == "S02" else
                "View along a thin snowy trail among tall trees."
                if not in_cabin else
                "Stage the room for the image in the next pass. Keep rough stone, timber and the established geometry. "
                "Look toward the sleep area if needed and beyond the stove only where physically in frame."
            )
        )
        if not generate(shot_id + "-plate", plate_rel, knowledge, channel, reference=master):
            return False
        master = EP / plate_rel
    else:
        # Share the approved empty cabin plate so the established room stays coherent.
        # The actor pass changes the camera and framing, not the cabin architecture.
        shared_plate = EP / "image/plates/S05.png"
        if shared_plate.is_file():
            master = shared_plate
    with tempfile.TemporaryDirectory(prefix="snow-cabin-reference-") as temp:
        reference = Path(temp) / "scene-and-cast.png"
        reference_sheet(reference, master, cast)
        cast_order = " Top to bottom on the reference strip: " + " ".join(
            f"({index}) [{key}]. {characters[key]}" for index, key in enumerate(cast, 1)
        )
        state = (
            "Worn jackets, rubbed cuff edges, damp hems and tired winter faces. "
            "Hard-edged wet patches at shoulders, no snow falling inside."
            if in_cabin else
            "Visible snow sticking on shoulders and hoods. Each person is dressed in the original "
            "parka color. Natural staggered hiking positions and visibly uneven trail."
        )
        direction = (
            "Use the left region of the reference for environment continuity ONLY. "
            "The right gray strip contains visual identity references only, not the composition. "
            "Reframe to the requested angle and shot scale. "
            "Render a single full-bleed 16:9 narrative panel, no gray strip, no grid. "
            "No additional figures. Frame only the parts of characters visible in the shot. "
            "Keep the outlined two-tone color shapes on faces and clothing. "
        )
        return generate(shot_id, Path(f"image/final/{shot_id}.png"),
                        direction + opening + visual + " " + setting + " " + state + cast_order,
                        channel, reference=reference, cel=True)


def batch(ids):
    (EP / "image/final").mkdir(exist_ok=True)
    work = [(shot_id, channels[i % len(channels)]) for i, shot_id in enumerate(ids)]
    with ThreadPoolExecutor(max_workers=len(channels)) as pool:
        codes = list(pool.map(lambda item: subprocess.run(
            [sys.executable, __file__, "one", *item], cwd=EP
        ).returncode, work))
    return not any(codes)


if __name__ == "__main__":
    mode, *args = sys.argv[1:]
    if mode == "one":
        with LockedRouting():
            ok = shot(*args)
    elif mode == "pilot":
        ok = batch(PILOT)
    elif mode == "batch":
        assert (EP / "qa/pilot.md").exists(), "Pilot review required"
        ok = batch(args or [key for key in ROWS if key not in PILOT])
    else:
        raise SystemExit(f"Unknown mode: {mode}")
    raise SystemExit(0 if ok else 1)
