# -*- coding: utf-8 -*-
"""Build <episode>/audio/utterances.json for the CosyVoice3 voice line."""
import json
from pathlib import Path

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws")
RUN = EP / "runs" / "20261106-ulw-b01"
job = json.loads((EP / "audio" / "jobs" / "all.json").read_text(encoding="utf-8"))
ORDER = ["intro", "bridge", "ch01", "ch02", "ch03", "ch04", "ch05", "ch06", "ch07", "epilogue"]
utt = []
for s in job["shots"]:
    sec = s["id"].split("-p")[0]
    utt.append({"id": s["id"], "paragraph_id": s["id"].split("-u")[0],
                "section": sec, "text": s["text"], "tts_blocked": False})
utt.append({"id": "intro-trans", "paragraph_id": "intro-trans", "section": "intro",
            "text": "我们从比萨斜塔上的两个球开始，一直走到物理学家不得不承认：我们只能发现规律，不能证明规律。",
            "tts_blocked": False})
paras, seen = [], set()
for u in utt:
    if u["paragraph_id"] not in seen:
        seen.add(u["paragraph_id"]); paras.append(u["paragraph_id"])
doc = {
    "source": "story/NARRATION_MASTER.md",
    "version": "v1-cosy3",
    "sections": [{"key": k, "title": k} for k in ORDER],
    "paragraph_order": paras,
    "narrated_chars": sum(len(u["text"]) for u in utt),
    "utterances": utt,
}
(EP / "audio" / "utterances.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
print("utts", len(utt), "chars", doc["narrated_chars"])
