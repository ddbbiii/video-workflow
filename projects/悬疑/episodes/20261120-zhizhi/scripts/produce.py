"""Generate the locked storyboard frames through the configured image API."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[3]
SPEC = importlib.util.spec_from_file_location(
    "image_api", ROOT / "projects/悬疑/visual-tests/20261114-pilot-8shots/gen_pilot.py"
)
api = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = api
SPEC.loader.exec_module(api)
api.HERE = EP
api.RULES = ROOT / "rules/悬疑/visual.md"
api.RAW = EP / "image/raw"
api.CROPS = EP / "image/crops"
for folder in (api.RAW, api.CROPS, EP / "image/final", EP / "image/plates", EP / "image/anchors", EP / "logs", EP / "qa"):
    folder.mkdir(parents=True, exist_ok=True)

POLICY = json.loads((ROOT / "shared/image-api/channel-policy.json").read_text())
ACTIVE = POLICY["policies"][POLICY["active"]]
POS, NEG, CEL = (api.read_block(name) for name in ("STYLE_POS", "STYLE_NEG", "CEL_BOOST"))
PLAN = json.loads((EP / "storyboard/SHOT_PLAN-v1.json").read_text())
PLATE = EP / "image/plates/bedroom-reference.png"
MANIFEST = EP / "image/manifest.json"
LOCKS = {name: threading.Lock() for name in ACTIVE["parallel_channels"]}
MANIFEST_LOCK = threading.Lock()
FORCE = set(sys.argv[2].partition("=")[2].split(",")) if len(sys.argv) > 2 and sys.argv[2].startswith("--force=") else set()

ROOM = (
    "the same single modest rural Chinese farmhouse bedroom at night, low wooden ceiling beams, "
    "aged wood bed on the left, small square wooden stool at the foot of the bed, old wooden door "
    "and simple interior latch opposite the bed, one old window on the back wall, a small oil lamp; "
    "keep this room layout consistent, peeling paint and a water stain on the wall, scuffed floorboards, "
    "worn quilt and a thermos as ordinary lived-in details; cold moonlight with one small warm lamp, "
    "midtones readable and important evidence clearly lit"
)
QUALITY = (
    "one complete 16:9 illustration, no panels or collage; crisp ink contours, flat cel color regions, "
    "hard-edged shadows, no gradients on paper clothing or walls; deep focus; off-center composition "
    "with one foreground obstruction; readable room layers; keep dark areas detailed, avoid crushed blacks"
)
AVOID = "Avoid: " + NEG

DETAILS = {
    "S01": "From the foot of the bed, the small stool is now empty; the wooden door remains shut and its latch is visibly set from inside. No paper figure in frame.",
    "S02": "The same 45 cm paper effigy stands on the stool at the foot of the bed. A seated adult uncle is only partly visible at frame edge, placing it carefully; keep the effigy below the adult knee. The bed edge makes its small scale obvious.",
    "S03": "Close evidence view of the 45 cm effigy on the stool: flat white paper face, exactly two black ink-dot eyes, round red cheeks, red-and-green folded paper robe, thin bamboo ribs at the joints. Clearly a small handcrafted paper object, no human skin.",
    "S04": "Interior three-quarter view of the old wooden door as the narrator's ordinary adult hand slides the latch into place; bed edge and the same small effigy on its stool remain in the background.",
    "S05": "Close but contextual view of the effigy from head to stool seat; its full 45 cm scale remains below a nearby adult knee implied at frame edge. Preserve the flat paper face, ink-dot eyes, round cheeks, folded red-green robe and bamboo frame.",
    "S06": "First-person view from the bed toward the same effigy still standing on the stool. Only one small oil lamp glows; the closed window and familiar room remain readable, the ink dots on its face stand out in the low light.",
    "S07": "Same room and same small effigy, now standing on the floor beside the bed; the stool at the bed foot is empty in the same frame. It remains exactly 45 cm tall, clothing undisturbed; no wind or motion blur.",
    "S08": "First-person view from bed: one ordinary adult hand lies stiff on the quilt in foreground, fingers barely tense. The closed window, latched door and small effigy on the floor are all visible; no paper hands yet.",
    "S09": "Evidence close view: one tiny dark water droplet trails from beside one black ink eye down the flat white paper cheek; one small black wet dot rests on the pillow beside it. No blood, no realistic tears, no changed face.",
    "S10": "The same 45 cm effigy now stands on the pillow at close range, next to a full-size pillow for scale; several thin bamboo ribs peek from one paper sleeve. Keep its small body proportions unchanged.",
    "S11": "First-person bed view: the small effigy has turned its back and is angled toward the distant wooden door. A narrow strip of folded robe and bamboo frame is visible; keep the figure 45 cm tall and movement implied only by pose.",
    "S12": "Side view of the 45 cm paper effigy standing on the pillow beside the adult-size pillow, with its entire head-to-foot body visible for direct scale comparison. Same folded robe, same face, no growth.",
    "S13": "From near the bed foot, the wooden door is still mostly shut; the interior latch has just slipped open and a thin line of cooler hallway light enters. The small effigy remains near the pillow.",
    "S14": "The wooden door is open. One adult figure in plain modern dark home clothes, seen only from behind with face fully hidden, crosses the threshold into the hallway. The small effigy remains on the pillow in the foreground; no other people.",
    "S15": "First-person downward view from pillow height: two very small paper hands rest on the quilt, visibly folded white paper with thin bamboo ribs at the wrists, clearly belonging to the 45 cm effigy. The room furniture appears larger from this low viewpoint; no human skin.",
    "S16": "Foreground: the small folded paper hands with bamboo wrists remain on the pillow. In the background, the open doorway and empty hall are visible, with no person present. Hold a quiet unresolved final image; no supernatural explanation or text."
}


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def generate(shot: dict, index: int) -> dict:
    target = EP / "image/final" / f"{shot['id']}.png"
    if target.exists() and shot["id"] not in FORCE:
        return {"id": shot["id"], "cached": True, "file": str(target.relative_to(EP))}
    assigned = shot["channel_assigned"]
    channel_names = [assigned, *[x for x in ACTIVE["parallel_channels"] if x != assigned]]
    prompt = "\n".join((POS, CEL, QUALITY, ROOM, DETAILS[shot["id"]], AVOID))
    last = None
    for channel_name in channel_names:
        channel = dict(POLICY["channels"][channel_name], name=channel_name, policy=POLICY["active"])
        for attempt in (1, 2):
            with LOCKS[channel_name]:
                reference = PLATE
                info = api.call(channel, prompt, {"tag": shot["id"]}, reference, attempt)
            info.update({"policy": POLICY["active"], "assigned_channel": assigned,
                         "fallback_from": channel_name if channel_name != assigned else None,
                         "model": channel["model"], "reference": str(reference.relative_to(EP)) if reference else None,
                         "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()})
            if info.get("ok"):
                source = EP / info["file"]
                info["metrics"] = api.measure(source)
                issues = api.gate(info, channel)
                if not issues:
                    shutil.copyfile(source, target)
                    info["file"] = str(target.relative_to(EP))
                    info["qa"] = "pass"
                    last = info
                    break
                info["qa"] = issues
            save_json(EP / "logs" / f"{shot['id']}-{channel_name}-a{attempt}.json", info)
            last = info
            if info.get("http_status") in (401, 403):
                break
        if last and last.get("qa") == "pass":
            break
    if not last or last.get("qa") != "pass":
        raise RuntimeError(f"{shot['id']} failed: {last}")
    print("FRAME", shot["id"], last["channel"], last["dims"], flush=True)
    with MANIFEST_LOCK:
        existing = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
        existing[shot["id"]] = {k: last.get(k) for k in ("file", "channel", "model", "dims", "metrics", "qa", "sha256", "reference", "fallback_from")}
        save_json(MANIFEST, existing)
    return existing[shot["id"]]


def main() -> None:
    selected = {x.strip() for x in sys.argv[1].split(",")} if len(sys.argv) > 1 else set()
    shots = [s for s in PLAN["shots"] if not selected or s["id"] in selected]
    # The six dkl-b pilot frames run first; the same quality checks gate the remainder.
    pilot = [s for s in shots if s["channel_assigned"] == "dkl-b"][:6]
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda pair: generate(*pair), [(s, i) for i, s in enumerate(pilot)]))
        rest = [s for s in shots if s not in pilot]
        list(pool.map(lambda pair: generate(*pair), [(s, i) for i, s in enumerate(rest)]))


if __name__ == "__main__":
    main()
