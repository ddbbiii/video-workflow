# -*- coding: utf-8 -*-
"""Timeline v2: align paragraphs to shots by character-bigram similarity (monotonic DP)."""
import json, re, wave
from pathlib import Path
import numpy as np

RUN = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws\runs\20261106-ulw-b01")
EP = RUN.parents[1]
PROC = EP / "audio" / "vo-proc"
SHOT_MD = EP / "visual" / "SHOT_PLAN_DRAFT.md"

HEAD_S, UNIT_GAP, PARA_GAP, CHAP_GAP, SR = 0.3774, 0.19, 0.4245, 0.7547, 48000
SEC2CH = {"bridge": "c0", "ch01": "c1", "ch02": "c2", "ch03": "c3",
          "ch04": "c4", "ch05": "c5", "ch06": "c6", "ch07": "c7", "epilogue": "c8"}
BODY_ORDER = ["bridge", "ch01", "ch02", "ch03", "ch04", "ch05", "ch06", "ch07", "epilogue"]


def bigrams(s):
    s = re.sub(r"[^\u4e00-\u9fff]", "", s)
    return set(s[i:i + 2] for i in range(len(s) - 1))


def sim(a, b):
    A, B = bigrams(a), bigrams(b)
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


# ---- shots ----
shots_plan = {}
for line in SHOT_MD.read_text(encoding="utf-8").splitlines():
    if re.match(r"^\|\s*c\d-s\d+\s*\|", line):
        p = [x.strip() for x in line.split("|")]
        sid, desc, motion, sec = p[1], p[2], p[3], int(p[4])
        ch = sid.split("-")[0]
        shots_plan.setdefault(ch, []).append(
            {"id": sid, "desc": desc, "motion": motion, "seconds": sec})

# ---- utterances ----
job = json.loads((EP / "audio" / "jobs" / "all.json").read_text(encoding="utf-8"))
dur = json.loads((RUN / "durations.json").read_text(encoding="utf-8"))
utts = []
for s in job["shots"]:
    sid = s["id"]
    sec = sid.split("-p")[0]
    if sec not in BODY_ORDER or sid not in dur:
        continue
    utts.append({"id": sid, "section": sec, "para": sid.split("-u")[0],
                 "text": s["text"], "dur": dur[sid]})

cursor = HEAD_S
prev_para = prev_sec = None
for u in utts:
    gap = 0.0 if prev_sec is None else (CHAP_GAP if u["section"] != prev_sec else
                                       (PARA_GAP if u["para"] != prev_para else UNIT_GAP))
    u["start"] = round(cursor + gap, 3)
    u["end"] = round(u["start"] + u["dur"], 3)
    cursor = u["end"]
    prev_para, prev_sec = u["para"], u["section"]
total = cursor + 0.6

sec_ranges = {}
for u in utts:
    r = sec_ranges.setdefault(u["section"], {"start": u["start"], "end": u["end"]})
    r["end"] = u["end"]

sections = []
for sec in BODY_ORDER:
    ch = SEC2CH[sec]
    shots = shots_plan.get(ch, [])
    if not shots:
        continue
    paras = []
    seen = {}
    for u in utts:
        if u["section"] != sec:
            continue
        if u["para"] not in seen:
            seen[u["para"]] = {"id": u["para"], "text": "", "start": u["start"], "end": u["end"]}
            paras.append(seen[u["para"]])
        p = seen[u["para"]]
        p["text"] += u["text"]
        p["end"] = u["end"]
    P, S = len(paras), len(shots)
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
                for k in range(0, j + 1):
                    if dp[i - 1][k] > best:
                        best, bi = dp[i - 1][k], k
                if bi >= 0:
                    dp[i][j] = best + base
                    bk[i][j] = bi
    j = max(range(S), key=lambda x: dp[P - 1][x])
    assign = [0] * P
    for i in range(P - 1, -1, -1):
        assign[i] = j
        j = bk[i][j] if i > 0 else -1
    per_shot = [[] for _ in range(S)]
    for i, j in enumerate(assign):
        per_shot[j].append(paras[i])
    st, en = sec_ranges[sec]["start"], sec_ranges[sec]["end"]
    MIN = 3.5
    anchors = [(ps[0]["start"] if ps else None) for ps in per_shot]
    anchors[0] = st if anchors[0] is None else anchors[0]
    known = [i for i, a in enumerate(anchors) if a is not None]
    for a, b in zip(known, known[1:]):
        for m in range(a + 1, b):
            anchors[m] = anchors[a] + (anchors[b] - anchors[a]) * (m - a) / (b - a)
    if anchors[-1] is None:
        anchors[-1] = en
    B = [st] + anchors[1:] + [en]
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
    sections.append({"key": sec, "chapter": ch, "start": st, "end": en, "shots": out})

timeline = {"total": round(total, 3), "sections": sections,
            "utterances": [{"id": u["id"], "start": u["start"], "end": u["end"],
                            "text": u["text"]} for u in utts]}

# make shots contiguous over [0, total] so image time equals audio time (chapter gaps included)
flat = [s for sec in sections for s in sec["shots"]]
flat[0]["start"] = 0.0
for i in range(1, len(flat)):
    flat[i]["start"] = flat[i - 1]["end"]
flat[-1]["end"] = round(total, 3)
for s in flat:
    s["dur"] = round(s["end"] - s["start"], 3)

(RUN / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=1), encoding="utf-8")

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
    w.writeframes(np.zeros(int(max(0.0, total - pos) * SR), dtype=np.int16).tobytes())

print("shots", sum(len(s["shots"]) for s in sections), "utts", len(utts),
      "total", round(total, 1), "min", round(total / 60, 1))
