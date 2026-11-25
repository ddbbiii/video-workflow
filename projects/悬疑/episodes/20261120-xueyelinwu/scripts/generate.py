"""Generate Snow Cabin artwork using the repository image routes."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import sys
import tempfile

from PIL import Image

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[3]
spec = importlib.util.spec_from_file_location(
    "image_api", ROOT / "projects/悬疑/visual-tests/20261114-pilot-8shots/gen_pilot.py"
)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
api.TIMEOUT_S = 150
policy = json.loads((ROOT / "shared/image-api/channel-policy.json").read_text())
active = policy["policies"][policy["active"]]
channels = active["parallel_channels"]
style, negative, cel_style = (api.read_block(k) for k in ("STYLE_POS", "STYLE_NEG", "CEL_BOOST"))
quality = (
    "One complete full-frame widescreen image, no text, watermark, logo or border. "
    "Clean flat fills describe the rendering technique, not pristine physical condition. "
    "Apply story-driven wear as hard-edged shapes, and keep the cold and warm details readable."
)
cabin = (
    "Remote Changbai mountain ranger cabin in a night blizzard, an old grey fieldstone shell with "
    "a timber roof and a single stout timber front door. Interior geography from the back wall: "
    "closed brown vertical plank door on right, low black cast-iron stove on left, sleeping area "
    "left of frame on its opposite side. Door has a dark rectangular iron sliding crossbar fitted "
    "on INTERIOR face only, running horizontally into an iron keeper on the right stone jamb, "
    "with two dark screw heads on the keeper and a nick in the door plank just below it. "
    "Scuffed stone hearth, scratched boards and damp stains on the jamb, stacked firewood, "
    "a plain chipped enamel cup on the hearth. Low amber stove glow and soft cold blue door edge. "
    "No added doors, no other light source, no damage that opens an escape gap."
)
characters = {
    "narrator": "One Chinese male university senior, 22, slim, narrow face, angular black eyebrows, straight short black hair side parted, navy winter parka with light grey collar, charcoal pants, dark hiking boots.",
    "zhao": "One Chinese male university senior, 22, compact stocky build, rounder face and short black crew cut, dull olive winter parka and brown pants, dark hiking boots.",
    "sun": "One Chinese male university senior, 22, tallest of the three, long face and swept black fringe, faded ochre winter parka and charcoal pants, dark hiking boots.",
    "keeper": "One elderly Chinese man, 68, weathered angular face, left eye clouded closed with old knife scar down left cheek, cropped grey hair, faded charcoal padded coat, burgundy cloth scarf, dark work trousers.",
}

def generate(tag, destination, description, assigned, *, reference=None, cel=False, trial=False):
    target = EP / destination
    sidecar = EP / "logs" / f"{tag}.json"
    prompt = "\n".join(filter(None, [style, cel_style if cel else None, quality, description, "Avoid: " + negative]))
    if target.exists() and sidecar.exists():
        previous = json.loads(sidecar.read_text())
        if previous.get("ok") and previous.get("prompt") == prompt and previous.get("sha256") == hashlib.sha256(target.read_bytes()).hexdigest():
            return True
    results = []
    for name in [assigned, *(name for name in channels if name != assigned)]:
        if name in os.environ.get("SNOW_CABIN_PAUSED_ROUTES", "").split(","):
            continue
        channel = dict(policy["channels"][name], name=name)
        for attempt in range(1, active["retry"]["same_channel_max"] + 1):
            with tempfile.TemporaryDirectory(prefix="snow-cabin-image-") as temp:
                api.HERE = api.RAW = api.CROPS = Path(temp)
                result = api.call(channel, prompt, {"tag": tag}, reference, attempt)
                error = result.pop("error", None)
                if isinstance(error, dict):
                    payload = error.get("error", {})
                    error = payload.get("code") if isinstance(payload, dict) else None
                if error and not isinstance(error, (int, float)):
                    # Avoid persisting relay messages which may include account details or signed URLs.
                    error = error if str(error).replace("_", "").isalnum() else str(error).split(":")[0]
                result.update(model=channel["model"], fallback_from=assigned if name != assigned else None, error=error)
                if result.get("ok"):
                    image_path = Path(temp) / result["file"]
                    metrics = api.measure(image_path)
                    result["metrics"] = metrics
                    if problems := api.gate(result, channel):
                        result.update(ok=False, error="image_quality_gate", gate_findings=problems)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with Image.open(image_path) as im:
                            im.verify()
                        target.write_bytes(image_path.read_bytes())
                        result["file"] = str(destination)
                        result["attempts"] = results
                        sidecar.write_text(json.dumps(result, ensure_ascii=False, indent=2))
                        print(tag, name, "READY", tuple(result["dims"]), flush=True)
                        return True
                results.append(result)
                print(tag, name, attempt, result.get("http_status"), result.get("error"), flush=True)
                if result.get("http_status") in (401, 403) or trial:
                    break
    sidecar.write_text(json.dumps({"ok": False, "attempts": results}, ensure_ascii=False, indent=2))
    return False

def probe():
    return generate(
        "cabin-preflight", Path("image/plates/interior.png"),
        "Architecture study, ZERO people. " + cabin,
        channels[0], trial=True,
    )

def anchors():
    for index, (name, identity) in enumerate(characters.items()):
        if name == "narrator":
            layout = (
                "A 2x2 character model sheet, consistent height and body shape, same single person "
                "in each panel, mid-grey plain backdrop, no dividers or lettering. Top left front "
                "full body, top right exact left profile full body, bottom left back full body, "
                "bottom right front face. Shoes fully visible in full body views; hands relaxed."
            )
        else:
            layout = "Single three-quarter full-body neutral pose, plain light grey backdrop, entire boots visible and tightly framed from hair to boots near the frame edges. Crisp thick linework, strongly defined separate flat shadow and lit shapes, ample contrast between figure and background. Exactly one person."
        if not generate("anchor-" + name, Path(f"image/anchors/{name}.png"), layout + " " + identity, "dkl-b", cel=True):
            return False
    return True

if __name__ == "__main__":
    command = {"probe": probe, "anchors": anchors}[sys.argv[1]]
    raise SystemExit(0 if command() else 1)
