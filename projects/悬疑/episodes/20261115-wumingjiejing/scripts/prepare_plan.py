import json
from pathlib import Path

episode = Path(__file__).resolve().parents[1]
path = episode / "storyboard" / "SHOT_PLAN.json"
data = json.loads(path.read_text(encoding="utf-8"))
character_id = data["character"]["character_id"]

for shot in data["shots"]:
    shot["shot_type"] = shot["type"]
    shot["scene_id"] = shot["scene"]
    shot["has_character"] = shot["cast"] in ("linxu", "hand")
    shot["character_ids"] = [character_id] if shot["has_character"] else []
    shot["line"] = "悬疑"
    shot["step"] = "static"
    shot["character_closeup"] = shot["type"] == "C" and shot["has_character"]
    shot["hands_visible"] = shot["cast"] == "hand"
    shot["evidence_id"] = shot["id"] if shot["type"] == "C" else ""
    shot["subject_class"] = "environment" if shot["cast"] == "none" else "person"
    shot["push_ratio"] = 0.0
    shot["needs_2048"] = False
    shot["location_anchors"] = data["locations"][shot["scene"]]["anchors"]

path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"prepared {len(data['shots'])} shots")
