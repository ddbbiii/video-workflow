# -*- coding: utf-8 -*-
"""Build body timeline from measured VO durations + planned shot weights; write narration wav."""
import json, re, wave
from pathlib import Path
import numpy as np

RUN = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws\runs\20261106-ulw-b01")
EP = RUN.parents[1]
PROC = EP / "audio" / "vo-proc"
SHOT_MD = EP / "visual" / "SHOT_PLAN_DRAFT.md"

HEAD_S = 0.3774
UNIT_GAP = 0.19
PARA_GAP = 0.4245
CHAP_GAP = 0.7547
SR = 48000

SEC2CH = {"bridge": "c0", "ch01": "c1", "ch02": "c2", "ch03": "c3",
          "ch04": "c4", "ch05": "c5", "ch06": "c6", "ch07": "c7", "epilogue": "c8"}
BODY_ORDER = ["bridge", "ch01", "ch02", "ch03", "ch04", "ch05", "ch06", "ch07", "epilogue"]

# ---- planned shots ----
shots_plan = []
for line in SHOT_MD.read_text(encoding="utf-8").splitlines():
    if re.match(r"^\|\s*c\d-s\d+\s*\|", line):
        p = [x.strip() for x in line.split("|")]
        sid, motion, sec = p[1], p[3], int(p[4])
        shots_plan.append({"id": sid, "motion": motion, "seconds": sec})

# ---- utterances ----
job = json.loads((EP / "audio" / "jobs" / "all.json").read_text(encoding="utf-8"))
dur = json.loads((RUN / "durations.json").read_text(encoding="utf-8"))
utts = []
for s in job["shots"]:
    sid = s["id"]
    sec = sid.split("-p")[0]
    if sec not in BODY_ORDER:
        continue
    if sid not in dur:
        print("MISSING DUR", sid); continue
    utts.append({"id": sid, "section": sec, "para": sid.split("-u")[0],
                 "text": s["text"], "dur": dur[sid]})

# ---- place utterances sequentially with gaps ----
cursor = HEAD_S
prev_para = None
prev_sec = None
for u in utts:
    if prev_sec is None:
        gap = 0.0
    elif u["section"] != prev_sec:
        gap = CHAP_GAP
    elif u["para"] != prev_para:
        gap = PARA_GAP
    else:
        gap = UNIT_GAP
    u["start"] = round(cursor + gap, 3)
    u["end"] = round(u["start"] + u["dur"], 3)
    cursor = u["end"]
    prev_para, prev_sec = u["para"], u["section"]
total = cursor + 0.6

sec_ranges = {}
for u in utts:
    r = sec_ranges.setdefault(u["section"], {"start": u["start"], "end": u["end"]})
    r["end"] = u["end"]

# ---- allocate planned shots inside each section by weight ----
sections = []
for sec in BODY_ORDER:
    ch = SEC2CH[sec]
    plan = [s for s in shots_plan if s["id"].startswith(ch + "-")]
    if not plan:
        continue
    st, en = sec_ranges[sec]["start"], sec_ranges[sec]["end"]
    span = en - st + 0.35
    wsum = sum(s["seconds"] for s in plan)
    acc = 0.0
    out = []
    for i, s in enumerate(plan):
        a = st + span * acc / wsum
        acc += s["seconds"]
        b = st + span * acc / wsum
        if i == len(plan) - 1:
            b = st + span
        out.append({"id": s["id"], "start": round(a, 3), "end": round(b, 3),
                    "dur": round(b - a, 3), "motion": s["motion"],
                    "image": str(EP / "runs" / RUN.name / "crops_full" / (s["id"] + ".png"))})
    sections.append({"key": sec, "chapter": ch, "start": st, "end": en, "shots": out})

timeline = {"total": round(total, 3), "sections": sections,
            "utterances": [{"id": u["id"], "start": u["start"], "end": u["end"],
                            "text": u["text"]} for u in utts]}
(RUN / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=1), encoding="utf-8")

# ---- write narration wav by streaming silence + utterance frames ----
out = EP / "audio" / "narration_body.wav"
with wave.open(str(out), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    pos = 0.0
    for u in utts:
        gap = u["start"] - pos
        if gap > 0:
            w.writeframes(np.zeros(int(gap * SR), dtype=np.int16).tobytes())
        with wave.open(str(PROC / (u["id"] + ".wav")), "rb") as r:
            w.writeframes(r.readframes(r.getnframes()))
        pos = u["end"]
    tail = max(0.0, total - pos)
    w.writeframes(np.zeros(int(tail * SR), dtype=np.int16).tobytes())

print("shots", sum(len(s["shots"]) for s in sections), "utts", len(utts),
      "total_s", round(total, 1), "min", round(total / 60, 1))
for s in sections:
    print(" ", s["key"], len(s["shots"]), round(s["end"] - s["start"], 1))
