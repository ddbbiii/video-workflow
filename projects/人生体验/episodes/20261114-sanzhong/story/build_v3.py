# -*- coding: utf-8 -*-
"""从数据重建 story/script-v3.md（不再依赖任何旧版剧本）。

数据源：
  story/cues.json              每镜旁白（锁定，唯一真源）
  story/shot-types.json        shot_type / scene_id / chapter
  story/visuals-v3.part*.json  每镜画面描述（九字段）
  story/cast.json              cast / closeup_part / view_angle

用法：python story/build_v3.py [--check]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

EP = Path(__file__).resolve().parent.parent
DST = EP / "story" / "script-v3.md"
REQ = ("机位：", "焦段：", "人物：", "前景：", "中景：", "远景：", "光：", "环境色：", "动作：")
BAN = ("颗粒", "纸纹", "渐变", "写实", "照片感", "水印", "logo", "%")

HEADER = """# 《你第三次重复就死了》剧本 v3（v3.4 视觉：两层画风）

> 线路：人生体验 ｜ 单集：`20261114-sanzhong` ｜ 数据驱动：cue 与 shot_type/scene_id 锁定，visual 由 `story/visuals-v3.part*.json` 重建
> 定位：第二人称人生模拟器；「三重死则」末世 13 天，写实 Bad End。
> 画风：`rules/人生体验/style.md` **v3.4**（人物平涂 / 环境允许渐变·AO·材质·三光源）；主角 `character.md` **v7**；色彩 `color-script.md` **v1.3**。
> 镜头配比：`rules/shared/shot-composition.md`，E/M/C = 22/53/25，门禁 `check_shot_mix.py`。
> 每镜字段：`cue` ｜ `visual`（九字段）｜ `shot_type` ｜ `scene_id` ｜ `cast` ｜ `closeup_part` ｜ `view_angle`。
> 底部 1/5 为安全区；不写人物占比百分比。""".splitlines()


def load_visuals() -> dict:
    out = {}
    for p in sorted((EP / "story").glob("visuals-v3.part*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        dup = set(d) & set(out)
        if dup:
            raise SystemExit("duplicate ids in %s: %s" % (p.name, sorted(dup)))
        out.update(d)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)

    cues = json.loads((EP / "story" / "cues.json").read_text(encoding="utf-8"))
    rows = json.loads((EP / "story" / "shot-types.json").read_text(encoding="utf-8"))["shots"]
    types = {r["id"]: r for r in rows}
    order = [r["id"] for r in rows]
    cast = json.loads((EP / "story" / "cast.json").read_text(encoding="utf-8"))
    vis = load_visuals()

    problems = []
    for sid in order:
        if sid not in cues:
            problems.append((sid, "缺 cue"))
        if sid not in vis:
            problems.append((sid, "缺 visual"))
        if sid not in cast:
            problems.append((sid, "缺 cast"))
            continue
        t = vis.get(sid, "")
        miss = [k for k in REQ if k not in t]
        if miss:
            problems.append((sid, "visual 缺字段 " + ",".join(miss)))
        for b in BAN:
            if b in t:
                problems.append((sid, "禁用词 " + b))
        c = cast[sid]
        if not (c.get("cast") and c.get("closeup_part") and c.get("view_angle")):
            problems.append((sid, "cast 字段不全"))
    print("shots=%d problems=%d" % (len(order), len(problems)))
    for p in problems[:20]:
        print("  ", p[0], p[1])
    if problems:
        return 1
    if a.check:
        return 0

    out = list(HEADER) + [""]
    chapter = None
    for sid in order:
        ch = types[sid].get("chapter", "")
        if ch != chapter:
            chapter = ch
            out += ["## " + ch, ""]
        out.append("%s　%s" % (sid, cues[sid]))
        out.append("　　visual：" + vis[sid])
        out.append("　　shot_type：" + types[sid]["shot_type"])
        out.append("　　scene_id：" + types[sid]["scene_id"])
        out.append("　　cast：" + cast[sid]["cast"])
        out.append("　　closeup_part：" + cast[sid]["closeup_part"])
        out.append("　　view_angle：" + cast[sid]["view_angle"])
    DST.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("wrote", DST, len(order), "shots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
