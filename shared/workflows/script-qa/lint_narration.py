# -*- coding: utf-8 -*-
"""旁白 lint：拦住「导演提示/镜头术语」混进观众听到的旁白与字幕。

2026-11-11 事故：S41「时间蒙太奇：凉席、电热毯…」、S59「镜头拉远：窗帘还拉着…」
把导演提示写成了旁白行，配音念了、字幕也压了，三道门全过。

用法：
    python shared/workflows/script-qa/lint_narration.py <script.md> [<shots.json> <timeline.json> <x.ass> ...]
    python shared/workflows/script-qa/lint_narration.py <script.md> --json out.json

退出码：0 干净 / 1 命中 / 2 输入错误。
规则：`rules/shared/script-workflow.md` §12、`rules/shared/srt.md` §1。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 只收「观众不该听到的制作术语」；自然口语里的同形词（如「镜头」当望远镜）由人工复核
TERMS = [
    "蒙太奇", "镜头", "画面", "空镜", "特写", "远景", "近景", "中景", "全景",
    "静帧", "分屏", "四格", "拼图", "转场", "淡入", "淡出", "切至", "切到",
    "画外音", "旁白", "字幕", "配音", "口播", "录音", "音效", "配乐", "垫乐", "BGM",
    "调色", "画幅", "构图", "打光", "第一帧", "最后一帧", "卡点", "闪回", "素材",
]
# 括号注释：画面提示常被随手写在括号里
PAREN_HINT = re.compile(r"[（(【\[][^）)】\]]{0,20}(画面|镜头|注|说明|音效|配乐|字幕)[^）)】\]]{0,20}[）)】\]]")
SHOT_ID = re.compile(r"^(S\d{1,3})[\s　]+(.*)$")
USER_LITERAL = "# user-literal"


def from_markdown(path: Path) -> list[tuple[str, str, str]]:
    """返回 [(位置, id, 文本)]；只认 `S12　…` 这种行。"""
    out = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        m = SHOT_ID.match(line.strip())
        if m:
            text = m.group(2).strip()
            literal = USER_LITERAL in text
            if literal:
                text = text.replace(USER_LITERAL, "").strip()
            where = f"{path.name}:{i}" + (f" {USER_LITERAL}" if literal else "")
            out.append((where, m.group(1), text))
    return out


def from_json(path: Path) -> list[tuple[str, str, str]]:
    d = json.loads(path.read_text(encoding="utf-8"))
    shots = d.get("shots") or d.get("cues") or d.get("cue") or []
    if isinstance(d, dict) and "shots" not in d and "shots" in str(d)[:200]:
        shots = d["shots"]
    out = []
    for s in shots:
        if isinstance(s, dict) and "cue" in s:
            where = f"{path.name}:{s.get('id', '?')}"
            if s.get("user_literal"):
                where += f" {USER_LITERAL}"
            out.append((where, s.get("id", "?"), str(s["cue"])))
    return out


def from_ass(path: Path) -> list[tuple[str, str, str]]:
    out = []
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        if not line.startswith("Dialogue:"):
            continue
        parts = line.split(",", 9)
        if len(parts) < 10:
            continue
        text = re.sub(r"\{[^}]*\}", "", parts[9]).strip()
        out.append((f"{path.name}:{i}", parts[1], text))
    return out


def load(path: Path) -> list[tuple[str, str, str]]:
    suf = path.suffix.lower()
    if suf in (".md", ".txt"):
        return from_markdown(path)
    if suf == ".json":
        return from_json(path)
    if suf == ".ass":
        return from_ass(path)
    raise ValueError("unsupported file: %s" % path)


def check(units: list[tuple[str, str, str]]) -> list[dict]:
    hits = []
    for where, sid, text in units:
        if USER_LITERAL in where:
            continue
        found = [t for t in TERMS if t in text]
        paren = PAREN_HINT.search(text)
        if found or paren:
            hits.append({"where": where, "id": sid, "terms": found,
                         "paren": paren.group(0) if paren else None, "text": text})
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json")
    a = ap.parse_args()

    units: list[tuple[str, str, str]] = []
    for f in a.files:
        p = Path(f)
        if not p.exists():
            print("not found:", p, file=sys.stderr)
            return 2
        try:
            got = load(p)
        except ValueError as e:
            print(e, file=sys.stderr)
            return 2
        print("%-52s %4d 条" % (p.name, len(got)))
        units.extend(got)

    hits = check(units)
    print("\n共检查 %d 条，命中 %d 条" % (len(units), len(hits)))
    for h in hits:
        why = "、".join(h["terms"]) if h["terms"] else ""
        if h["paren"]:
            why = (why + " + 括号注释 " + h["paren"]).strip(" +")
        print("  [FAIL] %-28s %-4s <%s>  %s" % (h["where"], h["id"], why, h["text"][:46]))

    if a.json:
        report = Path(a.json)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps({"files": a.files, "units": len(units), "hits": hits},
                                     ensure_ascii=False, indent=1), encoding="utf-8")
    if hits:
        print("\n结论：FAIL —— 旁白里混进了制作术语/画面提示，禁止进入 TTS 与字幕。")
        return 1
    print("\n结论：PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
