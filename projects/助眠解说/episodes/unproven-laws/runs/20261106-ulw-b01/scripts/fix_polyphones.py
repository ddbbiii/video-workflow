# -*- coding: utf-8 -*-
"""Rewrite risky polyphone phrases in narration + job files, report affected unit ids."""
import json
from pathlib import Path

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws")
REPL = [
    ("一重一轻，同时落地。", "一个重些，一个轻些，同时落地。"),
    ("一格一格地量。", "一格一格地测量。"),
    ("他量了很多次。", "他测量了很多次。"),
    ("一次次去量。", "一次次去测量。"),
    ("从来没量到对不上的时候", "从来没测量到对不上的时候"),
    ("再量它们分开的速度", "再测量它们分开的速度"),
    ("人们量到了这个弯", "人们测量到了这个弯"),
]
changed = []


def fix_text(t):
    for a, b in REPL:
        if a in t:
            return t.replace(a, b)
    return None


# NARRATION_MASTER
p = EP / "story" / "NARRATION_MASTER.md"
s = p.read_text(encoding="utf-8")
for a, b in REPL:
    s = s.replace(a, b)
p.write_text(s, encoding="utf-8")

# all.json + utterances.json
for fn in ("jobs/all.json", "utterances.json"):
    p = EP / "audio" / fn
    doc = json.loads(p.read_text(encoding="utf-8"))
    for u in doc.get("shots", doc.get("utterances", [])):
        n = fix_text(u["text"])
        if n:
            u["text"] = n
            changed.append(u["id"])
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

print("changed", len(changed), changed)
