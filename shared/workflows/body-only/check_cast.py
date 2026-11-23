# -*- coding: utf-8 -*-
"""门禁：在场人物 / 特写部位 / 角度三字段（rules/shared/script-workflow.md §15.1）。

检查项：
1. 每镜必须有 cast / closeup_part / view_angle，且取值在枚举内；
2. cast 里的角色必须有当前人生体验线 v7 参考图；
3. cast 与 visual 文字不能矛盾（主角镜须在 visual 中明确出现）；
4. side / back 不允许 closeup_part=face（character.md §4.2）。

用法：
    python shared/workflows/body-only/check_cast.py --script <script.md> --refs <refs 目录>
退出码：0 通过 / 1 失败 / 2 输入错误。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CHARACTERS = {"catman", "chen", "helper-a", "helper-b", "helper-c"}
PART_OK = {"face", "hand", "paw", "prop", "none"}
ANGLE_OK = {"front", "three-quarter", "side", "back", "none"}
SHOT = re.compile(r"^(S\d{1,3})[\s\u3000]+(.*)$")
FIELD = re.compile(r"^(visual|shot_type|scene_id|cast|closeup_part|view_angle)[：:]\s*(.*)$")
REFS = {
    "catman": ("face-style-D.png", "turnaround.png"),
    "chen": ("ref-chen.png",),
    "helper-a": ("ref-helper-a.png",),
    "helper-b": ("ref-helper-b.png",),
    "helper-c": ("ref-helper-c.png",),
}


def valid_cast(cast: str) -> bool:
    if cast in ("none", "body-only"):
        return True
    parts = cast.split("+")
    return (1 <= len(parts) <= len(CHARACTERS)
            and len(parts) == len(set(parts))
            and set(parts) <= CHARACTERS)


def load(path: Path):
    shots, cur = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = SHOT.match(line.strip())
        if m:
            cur = dict(id=m.group(1), cue=m.group(2).strip())
            shots.append(cur)
            continue
        f = FIELD.match(line.strip())
        if f and cur is not None:
            cur[f.group(1)] = f.group(2).strip()
    return shots


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True)
    ap.add_argument("--refs", default="")
    a = ap.parse_args(argv)
    script = Path(a.script)
    if not script.exists():
        print("not found:", script, file=sys.stderr)
        return 2
    refs = Path(a.refs) if a.refs else None
    shots = load(script)
    fails = []
    for s in shots:
        sid = s["id"]
        for k in ("cast", "closeup_part", "view_angle", "visual", "shot_type", "scene_id"):
            if not s.get(k):
                fails.append((sid, "缺字段 " + k))
        cast, part, angle = s.get("cast", ""), s.get("closeup_part", ""), s.get("view_angle", "")
        if cast and not valid_cast(cast):
            fails.append((sid, "cast 非法: " + cast))
        if part and part not in PART_OK:
            fails.append((sid, "closeup_part 非法: " + part))
        if angle and angle not in ANGLE_OK:
            fails.append((sid, "view_angle 非法: " + angle))
        v = s.get("visual", "")
        if "catman" in cast:
            if not re.search(r"猫头|猫爪|他的|两人|两个人|主角|孩子", v):
                fails.append((sid, "cast 含 catman 但 visual 没有主角"))
        if "chen" in cast and "老陈" not in v and "两人" not in v:
            fails.append((sid, "cast 含 chen 但 visual 没有老陈"))
        if angle in ("side", "back") and part == "face":
            fails.append((sid, "side/back 不得做脸部特写（character.md §4.2）"))
        if refs is not None:
            for cid in cast.split("+"):
                for ref_name in REFS.get(cid, ()):
                    if not (refs / ref_name).exists():
                        fails.append((sid, "缺参考图 " + ref_name))
    print("shots=%d  字段完整=%d  问题=%d" % (len(shots), len(shots) - len({f[0] for f in fails}), len(fails)))
    for sid, why in fails[:40]:
        print("  [FAIL] %-4s %s" % (sid, why))
    if fails:
        print("\n结论：FAIL")
        return 1
    print("\n结论：PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
