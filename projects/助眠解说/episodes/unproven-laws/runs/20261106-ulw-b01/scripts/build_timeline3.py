# -*- coding: utf-8 -*-
"""Build video timeline from the CosyVoice3 assembled timeline (utterance times fixed)."""
import json, re, wave
from pathlib import Path
import numpy as np

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws")
RUN = EP / "runs" / "20261106-ulw-b01"
COSY = EP / "runs" / "20261106-ulw-cosy3" / "timeline.json"
SHOT_MD = EP / "visual" / "SHOT_PLAN_DRAFT.md"

SEC2CH = {"bridge": "c0", "ch01": "c1", "ch02": "c2", "ch03": "c3",
          "ch04": "c4", "ch05": "c5", "ch06": "c6", "ch07": "c7", "epilogue": "c8"}
BODY_ORDER = ["bridge", "ch01", "ch02", "ch03", "ch04", "ch05", "ch06", "ch07", "epilogue"]
SR = 48000


def bigrams(s):
    s = re.sub(r"[^\u4e00-\u9fff]", "", s)
    return set(s[i:i + 2] for i in range(len(s) - 1))


def sim(a, b):
    A, B = bigrams(a), bigrams(b)
    return len(A & B) / len(A | B) if A and B else 0.0


shots_plan = {}
for line in SHOT_MD.read_text(encoding="utf-8").splitlines():
    if re.match(r"^\|\s*c\d-s\d+\s*\|", line):
        p = [x.strip() for x in line.split("|")]
        sid, desc, motion = p[1], p[2], p[3]
        shots_plan.setdefault(sid.split("-")[0], []).append(
            {"id": sid, "desc": desc, "motion": motion})

cosy = json.loads(COSY.read_text(encoding="utf-8"))
job = json.loads((EP / "audio" / "jobs" / "all.json").read_text(encoding="utf-8"))
texts = {s["id"]: s["text"] for s in job["shots"]}
utts = []
for u in cosy["utterances"]:
    if u["section"] not in BODY_ORDER:
        continue
    utts.append({"id": u["id"], "section": u["section"],
                 "para": u["paragraph_id"], "text": texts[u["id"]],
                 "start": float(u["start_s"]), "end": float(u["end_s"])})
utts.sort(key=lambda x: x["start"])

total = float(cosy["body_seconds"])
sections = []
for sec in BODY_ORDER:
    ch = SEC2CH[sec]
    shots = shots_plan.get(ch, [])
    if not shots:
        continue
    paras, seen = [], {}
    for u in utts:
        if u["section"] != sec:
            continue
        if u["para"] not in seen:
            seen[u["para"]] = {"id": u["para"], "text": "", "start": u["start"], "end": u["end"]}
            paras.append(seen[u["para"]])
        p = seen[u["para"]]
        p["text"] += u["text"]; p["end"] = u["end"]
    P, S = len(paras), len(shots)
    if not P:
        continue
    st = float(cosy["sections"][sec]["start_s"])
    en = float(cosy["sections"][sec]["end_s"])
    NEG = -1e9
    dp = [[NEG] * S for _ in range(P)]
    bk = [[-1] * S for _ in range(P)]
    for i in range(P):
        for j in range(S):
            base = sim(paras[i]["text"], shots[j]["desc"])
            base += 0.12 * (1 - abs(i / max(1, P - 1) - j / max(1, S - 1)))
            if i == 0:
                dp[i][j] = base + 0.12 * (1 - j / max(1, S - 1))
            else:
                best, bi = NEG, -1
                for k in range(j + 1):
                    if dp[i - 1][k] > best:
                        best, bi = dp[i - 1][k], k
                if bi >= 0:
                    dp[i][j] = best + base; bk[i][j] = bi
    j = max(range(S), key=lambda x: dp[P - 1][x])
    assign = [0] * P
    for i in range(P - 1, -1, -1):
        assign[i] = j
        j = bk[i][j] if i > 0 else -1
    per_shot = [[] for _ in range(S)]
    for i, j in enumerate(assign):
        per_shot[j].append(paras[i])
    anchors = [(ps[0]["start"] if ps else None) for ps in per_shot]
    anchors[0] = paras[0]["start"] if anchors[0] is None else anchors[0]
    known = [i for i, a in enumerate(anchors) if a is not None]
    for a, b in zip(known, known[1:]):
        for m in range(a + 1, b):
            anchors[m] = anchors[a] + (anchors[b] - anchors[a]) * (m - a) / (b - a)
    if anchors[-1] is None:
        anchors[-1] = total
    B = [st] + anchors[1:] + [en]
    MIN = 3.5
    for j in range(1, S):
        if B[j] - B[j - 1] < MIN:
            B[j] = B[j - 1] + MIN
    for j in range(S - 1, 0, -1):
        if B[j + 1] - B[j] < MIN:
            B[j] = B[j + 1] - MIN
    B[0], B[S] = st, en
    out = []
    for j, s in enumerate(shots):
        a, b = max(st, B[j]), min(en, B[j + 1])
        out.append({"id": s["id"], "start": round(a, 3), "end": round(b, 3),
                    "dur": round(b - a, 3), "motion": s["motion"],
                    "image": str(RUN / "crops_full" / (s["id"] + ".png"))})
    sections.append({"key": sec, "chapter": ch, "start": 0.0, "end": total, "shots": out})

# contiguous global: extend each section's last shot to the next section start
for i in range(1, len(sections)):
    prev = sections[i - 1]["shots"][-1]
    cur = sections[i]["shots"][0]
    prev["end"] = cur["start"]
flat = [s for sec in sections for s in sec["shots"]]
flat[0]["start"] = 0.0
flat[-1]["end"] = round(total, 3)
for s in flat:
    s["dur"] = round(s["end"] - s["start"], 3)

timeline = {"total": round(total, 3), "sections": sections,
            "utterances": [{"id": u["id"], "start": u["start"], "end": u["end"], "text": u["text"]} for u in utts]}
(RUN / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=1), encoding="utf-8")

# copy body narration
import shutil
src = Path(cosy["body_wav"])
shutil.copy2(src, EP / "audio" / "narration_body.wav")
print("total", round(total, 2), "shots", len(flat), "utts", len(utts))
