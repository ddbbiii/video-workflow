# -*- coding: utf-8 -*-
"""回填 cast / closeup_part / view_angle 三字段（script-workflow §15.1）。

规则：只按 visual 里明确写的人名与部位归类；不确定的进 review 列表，人工再改。

用法：python story/make_cast.py [--write]
产物：story/cast.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EP = Path(__file__).resolve().parent.parent
SCRIPT = EP / "story" / "script-v3.md"
OUT = EP / "story" / "cast.json"

SHOT = re.compile(r"^(S\d{1,3})[\s\u3000]+(.*)$")
VISUAL = re.compile(r"^visual[：:]\s*(.*)$")


def load():
    shots, cur = [], None
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        m = SHOT.match(line.strip())
        if m:
            cur = dict(id=m.group(1), cue=m.group(2).strip(), visual="")
            shots.append(cur)
            continue
        v = VISUAL.match(line.strip())
        if v and cur is not None:
            cur["visual"] = v.group(1).strip()
    return shots


def classify(shot):
    v = shot["visual"]
    subj_m = re.search(r"人物：([^；]+)", v)
    subj = subj_m.group(1) if subj_m else ""
    has_cat = ("猫头" in v) or ("他的" in subj) or ("两人" in subj) or ("两个人" in subj)
    has_chen = "老陈" in v or "两人" in subj or "两个人" in subj
    if "无人" in subj and "老陈" not in v:
        cast = "none"
    elif has_cat and has_chen:
        cast = "catman+chen"
    elif has_chen:
        cast = "chen"
    elif has_cat:
        cast = "catman"
    else:
        cast = "body-only"

    closeup = shot.get("shot_type") == "C"
    if not closeup:
        part = "none"
    elif re.search(r"猫爪|爪子|爪尖|前爪", subj) or re.search(r"猫爪|爪尖|前爪", v) and "手" not in subj:
        part = "paw"
    elif re.search(r"手|指|掌|腕|虎口", subj):
        part = "hand" if ("老陈" in subj or "普通人" in subj or "成年人" in subj) else "paw"
    elif re.search(r"脸|头|眼睛|下半张", subj):
        part = "face"
    elif cast == "none":
        part = "prop"
    else:
        part = "face"

    if re.search(r"背面|背影|背对", v):
        angle = "back"
    elif re.search(r"四分之三|侧脸", v):
        angle = "three-quarter"
    elif cast == "none":
        angle = "none"
    else:
        angle = "front"
    return cast, part, angle


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    st = {r["id"]: r for r in json.loads((EP / "story" / "shot-types.json").read_text(encoding="utf-8"))["shots"]}
    rows = {}
    review = []
    for s in load():
        s["shot_type"] = st[s["id"]]["shot_type"]
        cast, part, angle = classify(s)
        rows[s["id"]] = dict(cast=cast, closeup_part=part, view_angle=angle)
        if part == "face" and angle in ("side", "back"):
            review.append((s["id"], "side/back 不能做脸部特写"))
    import collections
    print("cast:", dict(collections.Counter(r["cast"] for r in rows.values())))
    print("part:", dict(collections.Counter(r["closeup_part"] for r in rows.values())))
    print("angle:", dict(collections.Counter(r["view_angle"] for r in rows.values())))
    if review:
        print("REVIEW:", review)
    if a.write:
        OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
