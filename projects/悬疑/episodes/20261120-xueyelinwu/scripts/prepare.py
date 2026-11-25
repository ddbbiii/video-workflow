"""Compile chronological visual facts and a frame-based timeline from the current screenplay."""
from pathlib import Path
import hashlib
import json
import re

EP = Path(__file__).resolve().parents[1]
script = (EP / "story/script.md").read_text()
speech = re.sub(r"</?span[^>]*>", "", "\n".join(script.splitlines()[1:]))
speech = re.sub(r"\s+", "", speech)
beats = [row.split("|", 4) for row in (EP / "storyboard/beats.txt").read_text().splitlines()]
starts = []
offset = 0
for row in beats:
    cue_start = row[3]
    offset = speech.index(cue_start, offset)
    starts.append(offset)
    offset += len(cue_start)
assert starts[0] == 0
starts.append(len(speech))
keeper_state = "旧疤在左侧，独眼。火炉旁坐着、确认门闩、抱枪入睡、后来已在炉旁站起。"
shots = []
frame = 0
for idx, (row, begin, end) in enumerate(zip(beats, starts, starts[1:]), 1):
    kind, scene, cast, _, payload = row
    fact, visual = payload.split("|", 1)
    ids = [] if cast == "-" else cast.split(",")
    cue = speech[begin:end]
    visible = len(re.findall(r"[\w]", cue))
    pause = 1.0 if idx in (8, 12, 15, 26, 32, 33) else 0.18
    frames = round(max(2.75, visible / 3.6 + pause) * 24)
    evidence = {8: "BAR-CHECK", 12: "BAG", 15: "BAR-AFTER", 25: "DOOR-SEAM", 26: "DOOR-IMPACT", 32: "BAR-REVEAL", 33: "BAR-HOLD"}.get(idx, "")
    motion = "static"
    shot = {
        "id": f"S{idx:02}", "shot_type": kind, "scene_id": scene, "cue": cue,
        "fact": fact, "visual": visual, "line": "悬疑", "step": "single",
        "character_ids": ids, "has_character": bool(ids),
        "character_closeup": bool(ids) and kind == "C", "hands_visible": idx in (8, 21, 22, 27, 28, 30),
        "evidence_id": evidence, "subject_class": "mechanical" if evidence.startswith(("BAR", "DOOR")) else "prop" if evidence else "character" if ids else "environment",
        "push_ratio": 0, "needs_2048": bool(evidence),
        "motion": motion, "time_stage": "下午至夜幕" if idx <= 4 else "夜间，初到木屋" if idx <= 10 else "凌晨两点后",
        "continuity": "林中同一场风雪，衣服积雪和湿痕渐重" if scene == "forest" else "门在炉右，门闩始终卡在门框的同一个槽内。墙边是睡袋。大孙从消失以后不再出现在画面中。" + (keeper_state if "keeper" in ids else ""),
        "foley_requirement": "仅编辑注记：三下不同力度的沉闷撞门" if idx == 26 else "仅编辑注记：外部风雪随内外景切换",
        "start_frame": frame, "frames": frames, "start": frame / 24, "end": (frame + frames) / 24,
    }
    shots.append(shot)
    frame += frames
plan = {"fps": 24, "frames": frame, "duration": frame / 24, "script_sha256": hashlib.sha256(script.encode()).hexdigest(), "visible_chars": sum(len(re.findall(r"[\w]", s["cue"])) for s in shots), "shots": shots}
assert "".join(s["cue"] for s in shots) == speech
(EP / "storyboard/SHOT_PLAN.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
print(len(shots), plan["visible_chars"], plan["duration"])
