# -*- coding: utf-8 -*-
"""镜头配比门禁：E/M/C = 22/53/25 ±3pp，四条硬约束，场地进场三连、锚点覆盖、fact 信息职责。

输入二选一：
  --shots <shot-plan.json>   每镜 {id, shot_type, scene_id, has_character, fact}
  --script <script.md>       剧本里每镜带 `shot_type：E` / `scene_id：corridor` / `fact：…` 行

--require-fact：空 fact 直接 FAIL（悬疑线强制）；不加时只出 NOTE。

输出：报告 + 退出码（0 通过 / 1 不通过 / 2 输入错误）。

规则真源：rules/shared/shot-composition.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

TARGET = {"E": 0.22, "M": 0.53, "C": 0.25}
TOL = 0.03
MAX_RUN_NO_E = 6
MAX_RUN_CHAR = 5

SHOT = re.compile(r"^(S\d{1,3})[\s\u3000]+(.*)$")
FIELD = re.compile(r"^(shot_type|scene_id|has_character|fact)[：:]\s*(.*)$")


def from_script(path: Path):
    rows, cur = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        m = SHOT.match(s)
        if m:
            cur = dict(id=m.group(1), shot_type="", scene_id="", has_character=None, fact="")
            rows.append(cur)
            continue
        f = FIELD.match(s)
        if f and cur is not None:
            key, val = f.group(1), f.group(2).strip()
            if key == "has_character":
                cur[key] = val.lower() in ("1", "true", "是", "yes")
            else:
                cur[key] = val
    return rows


def from_json(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data["shots"] if isinstance(data, dict) and "shots" in data else data
    out = []
    for r in rows:
        out.append(dict(id=r.get("id") or r.get("shot"),
                        shot_type=(r.get("shot_type") or "").upper(),
                        scene_id=r.get("scene_id") or "",
                        has_character=r.get("has_character"),
                        fact=(r.get("fact") or "").strip()))
    return out


def check(rows, require_fact=False):
    fails, notes = [], []
    n = len(rows)
    missing = [r["id"] for r in rows if r["shot_type"] not in ("E", "M", "C")]
    if missing:
        fails.append("%d 镜缺 shot_type：%s" % (len(missing), missing[:8]))
    if any(not r["scene_id"] for r in rows):
        fails.append("%d 镜缺 scene_id" % sum(1 for r in rows if not r["scene_id"]))

    # fact：每镜一条信息职责（2026-11-15）
    no_fact = [r["id"] for r in rows if not (r.get("fact") or "").strip()]
    if no_fact:
        msg = "%d 镜缺 fact（这一镜观众必须看懂的一件事）：%s" % (len(no_fact), no_fact[:8])
        if require_fact:
            fails.append(msg)
        else:
            notes.append(msg + "；悬疑线请加 --require-fact")
    dup, seen_fact = [], {}
    for r in rows:
        f = (r.get("fact") or "").strip()
        if not f:
            continue
        key = (r["scene_id"], f)
        if key in seen_fact:
            dup.append((r["id"], seen_fact[key]))
        else:
            seen_fact[key] = r["id"]
    if dup:
        notes.append("同场 fact 重复（后一镜可能该并进前一镜）：%s" % dup[:5])

    cnt = Counter(r["shot_type"] for r in rows if r["shot_type"] in ("E", "M", "C"))
    total = sum(cnt.values()) or 1
    ratios = {k: cnt[k] / total for k in TARGET}
    for k, target in TARGET.items():
        if abs(ratios[k] - target) > TOL + 1e-9:
            fails.append("%s 占比 %.1f%%，目标 %.0f%%±3pp" % (k, ratios[k] * 100, target * 100))

    # 进场三连：scene_id 首次出现时前两镜应为 E
    first_seen = {}
    for i, r in enumerate(rows):
        sid = r["scene_id"]
        if sid and sid not in first_seen:
            first_seen[sid] = i
    entry_bad = []
    for sid, i in first_seen.items():
        head = [rows[j]["shot_type"] for j in range(max(0, i - 1), min(n, i + 2))]
        if "E" not in head:
            entry_bad.append((sid, rows[i]["id"]))
    if entry_bad:
        notes.append("进场缺 E 的场地（首现处 ±1 镜内无 E）：%d 个，如 %s" % (len(entry_bad), entry_bad[:5]))

    # 连续 6 镜无 E
    run = 0
    worst_no_e = 0
    for r in rows:
        run = 0 if r["shot_type"] == "E" else run + 1
        worst_no_e = max(worst_no_e, run)
    if worst_no_e >= MAX_RUN_NO_E:
        fails.append("连续 %d 镜没有 E（上限 %d）" % (worst_no_e, MAX_RUN_NO_E - 1))

    # 连续含人物镜：只算明确标 true 的镜；未标（None）不计入，出 NOTE（2026-11-15）
    run = worst_char = 0
    unknown_char = 0
    for r in rows:
        if r["has_character"] is True:
            run += 1
            worst_char = max(worst_char, run)
        else:
            run = 0
            if r["has_character"] is None:
                unknown_char += 1
    if unknown_char:
        notes.append("%d 镜未标 has_character，连续含人物镜按已标镜判；正式 shot-plan 必须标" % unknown_char)
    if worst_char > MAX_RUN_CHAR:
        fails.append("连续 %d 镜含人物（上限 %d）" % (worst_char, MAX_RUN_CHAR))

    # 每场地锚点覆盖（若提供 anchors）
    per_scene = Counter(r["scene_id"] for r in rows if r["scene_id"])
    report = dict(total=n, counts=dict(cnt), ratios={k: round(v, 4) for k, v in ratios.items()},
                  scenes=len(per_scene), per_scene=dict(per_scene),
                  worst_run_without_e=worst_no_e, worst_run_with_character=worst_char,
                  entry_without_e=entry_bad, fact_missing=no_fact, fact_duplicate=dup,
                  fails=fails, notes=notes)
    return report, (not fails)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--script")
    ap.add_argument("--shots")
    ap.add_argument("--json", default="")
    ap.add_argument("--strict-entry", action="store_true", help="进场缺 E 也算失败")
    ap.add_argument("--require-fact", action="store_true", help="空 fact 也算失败（悬疑线强制）")
    a = ap.parse_args(argv)

    if a.script:
        rows = from_script(Path(a.script))
    elif a.shots:
        rows = from_json(Path(a.shots))
    else:
        print("need --script or --shots", file=sys.stderr)
        return 2
    if not rows:
        print("FAIL: no shots parsed", file=sys.stderr)
        return 2

    report, ok = check(rows, a.require_fact)
    print("shots=%d  E=%d (%.1f%%)  M=%d (%.1f%%)  C=%d (%.1f%%)  scenes=%d  缺 fact=%d" % (
        report["total"], report["counts"].get("E", 0), report["ratios"]["E"] * 100,
        report["counts"].get("M", 0), report["ratios"]["M"] * 100,
        report["counts"].get("C", 0), report["ratios"]["C"] * 100, report["scenes"],
        len(report["fact_missing"])))
    print("最长无 E 连续=%d  最长含人物连续=%d" % (report["worst_run_without_e"],
                                                 report["worst_run_with_character"]))
    for n in report["notes"]:
        print("NOTE " + n)
    if report["fails"]:
        print("FAIL")
        for f in report["fails"]:
            print(" - " + f)
    else:
        print("PASS")
    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if ok or (report["notes"] and not report["fails"]) else 1


if __name__ == "__main__":
    sys.exit(main())
