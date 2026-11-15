# -*- coding: utf-8 -*-
"""旁白 preflight：任何"把 cue 变成声音或字幕"的脚本，开工前先调这里。

    from guard import guard_paths, guard_units
    guard_paths([EP / "storyboard" / "shots.json"])        # 失败直接 SystemExit(1)

规则真源：`rules/shared/script-workflow.md` §12。
起因：2026-11-11 S41「时间蒙太奇：…」/ S59「镜头拉远：…」被当成旁白念出来、压进字幕。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lint_narration import check, load  # noqa: E402


def guard_paths(paths, strict: bool = True) -> list:
    """检查一批文件；有命中就打印并退出（strict）或只返回命中（非 strict）。"""
    units = []
    for p in paths:
        p = Path(p)
        if not p.exists():
            raise SystemExit("[narration-guard] 文件不存在：%s" % p)
        units.extend(load(p))
    hits = check(units)
    if hits and strict:
        print("[narration-guard] 旁白里混进了制作术语/画面提示，已阻断：", file=sys.stderr)
        for h in hits:
            why = "、".join(h["terms"]) or (h.get("paren") or "")
            print("  %s %s <%s>  %s" % (h["where"], h["id"], why, h["text"][:60]), file=sys.stderr)
        print("[narration-guard] 规则：rules/shared/script-workflow.md §12（cue 只写观众听到的话）",
              file=sys.stderr)
        raise SystemExit(1)
    return hits


def guard_cues(cues, strict: bool = True) -> list:
    """内存里的一批 (id, text) → 直接检查，不落盘。"""
    units = [("(memory)", str(i), str(t)) for i, t in cues]
    hits = check(units)
    if hits and strict:
        for h in hits:
            print("[narration-guard] %s %s %s" % (h["id"], h["terms"], h["text"][:60]), file=sys.stderr)
        raise SystemExit(1)
    return hits


if __name__ == "__main__":
    guard_paths(sys.argv[1:])
    print("[narration-guard] PASS")
