# -*- coding: utf-8 -*-
"""SHOT_PLAN.md + timeline.json -> motion_plan.json（affine 推拉）。

- 每章镜头按段落数均分，镜头边界落在段落起点，长度取整到帧（30 fps）。
- 视图：推近 1.00→0.91（9%），拉远 0.91→1.00（9%），横移 0.94 宽 6.4%。
- I2V 标记的镜头本版一律按 P1 渲染（动态版后补，不阻塞成片）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

EP = Path(__file__).resolve().parents[3]
RUN = EP / "runs" / "20261112-cas-b01"
PLAN_MD = EP / "story" / "SHOT_PLAN.md"
TIMELINE = RUN / "timeline.json"
OUT = RUN / "motion_plan.json"
SHOTS = EP / "assets" / "shots"

FPS = 30


def parse_plan() -> dict[str, list[dict]]:
    sections: dict[str, list[dict]] = {}
    cur = None
    for line in PLAN_MD.read_text(encoding="utf-8").splitlines():
        m = re.match(r"##\s+\d+\s+(\w+)", line)
        if m:
            cur = m.group(1)
            sections.setdefault(cur, [])
            continue
        if cur is None:
            continue
        r = re.match(r"\|\s*(S\d+)\s*\|\s*(.+?)\s*\|\s*(P1|I2V)", line)
        if r:
            sections[cur].append({"id": r.group(1), "desc": r.group(2), "motion": r.group(3)})
    return {k: v for k, v in sections.items() if v}


def find_source(shot_id: str) -> Path:
    hits = list(SHOTS.glob(f"*/{shot_id}.png"))
    if not hits:
        raise SystemExit(f"[missing] {shot_id}")
    return hits[0]


VIEW_FULL = [0.0, 0.0, 1.0, 1.0]
VIEW_IN = [0.045, 0.045, 0.91, 0.91]
VIEW_PAN_A = [0.0, 0.03, 0.94, 0.94]
VIEW_PAN_B = [0.06, 0.03, 0.94, 0.94]


def main() -> None:
    plan = parse_plan()
    tl = json.loads(TIMELINE.read_text(encoding="utf-8"))
    body_start = min(v["start_s"] for v in tl["sections"].values())

    shots = []
    sec_keys = [s for s in plan if s in tl["sections"]]
    starts = {s: tl["sections"][s]["start_s"] for s in sec_keys}
    order = sorted(sec_keys, key=lambda s: starts[s])
    next_start = {s: (starts[order[i + 1]] if i + 1 < len(order) else
                      max(v["end_s"] for v in tl["sections"].values()))
                  for i, s in enumerate(order)}

    for sec in order:
        items = plan[sec]
        para_ids = [p for p, v in sorted(tl["paragraphs"].items(), key=lambda kv: kv[1]["start_s"])
                    if v["section"] == sec]
        p = len(para_ids)
        n = len(items)
        sec_end = next_start[sec]
        for i, item in enumerate(items):
            a = (i * p) // n
            b = ((i + 1) * p) // n
            b = max(b, a + 1)
            start_s = tl["paragraphs"][para_ids[a]]["start_s"] if i else tl["sections"][sec]["start_s"]
            end_s = sec_end if i == n - 1 else tl["paragraphs"][para_ids[min(b, p - 1)]]["start_s"]
            f0 = round((start_s - body_start) * FPS)
            f1 = round((end_s - body_start) * FPS)
            if f1 - f0 < 2:
                f1 = f0 + 2
            mode = i % 4
            if mode == 0 or mode == 3:
                start_view, end_view = VIEW_FULL, VIEW_IN
            elif mode == 1:
                start_view, end_view = VIEW_IN, VIEW_FULL
            else:
                start_view, end_view = VIEW_PAN_A, VIEW_PAN_B
            shots.append({
                "id": item["id"],
                "source": str(find_source(item["id"])),
                "duration_s": (f1 - f0) / FPS,
                "start_view": start_view,
                "end_view": end_view,
                "curve": {"type": "smoothstep"},
                "planned_motion": item["motion"],
                "desc": item["desc"],
            })

    # 帧边界必须连续覆盖整段
    total = sum(round(s["duration_s"] * FPS) for s in shots)
    expect = round((max(v["end_s"] for v in tl["sections"].values()) - body_start) * FPS)
    print("shots", len(shots), "frames", total, "expect", expect, "drift", total - expect)

    doc = {
        "schema_version": 1,
        "backend": "affine",
        "output": {"width": 1920, "height": 1080, "fps": FPS},
        "transition_s": 0,
        "shots": shots,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
