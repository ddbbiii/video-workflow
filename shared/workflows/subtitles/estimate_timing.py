# -*- coding: utf-8 -*-
"""逐句估算时间轴：没有配音时，给 SRT 一条可用的起点时间轴。

Spec: rules/shared/srt.md §3（2026-11-14 起 SRT 只覆盖正文，offset 固定 0）。

本工具只做「句子级」时间：一句一条 cue，时长 = 可见字数 / --cps，句末加停顿，
章末加更长停顿，条与条首尾相接。拆条与 20 字上限交给 `split_srt.py`，
门禁交给 `check_srt.py`——三个执行件各管一段，不互相内嵌。

输入：剧本 markdown，旁白写在 `S12　……` 行（与 `script-qa/lint_narration.py` 同格式）；
      章标题写成 `## 第N章 ……`，只用来加章间停顿。
输出：`--out` 指定的句子级 SRT；`--json` 指定的逐句时间表（给下游/QA 用）。

用法：
    python shared/workflows/subtitles/estimate_timing.py story/script-v1.md \
        --out subtitles/r1/sentences.srt --json subtitles/r1/sentences.json --cps 4.8
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

SHOT = re.compile(r"^(S\d{1,3})[\s　]+(.*)$")
CHAPTER = re.compile(r"^##\s*第.+章")


def visible_len(text: str) -> int:
    return sum(1 for ch in text if unicodedata.category(ch)[0] in ("L", "N"))


def parse_script(path: Path):
    """返回 [(shot_id, cue_text, chapter_no)]。"""
    shots, chapter = [], 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if CHAPTER.match(line.strip()):
            chapter += 1
            continue
        m = SHOT.match(line.strip())
        if m:
            shots.append((m.group(1), m.group(2).strip(), chapter))
    return shots


def fmt(ts: float) -> str:
    ms = int(round(ts * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--out", required=True, help="句子级 SRT")
    ap.add_argument("--json", default="", help="逐句时间表 (JSON)")
    ap.add_argument("--cps", type=float, default=4.8,
                    help="估算语速（可见字/秒，标点间隙已含在内）")
    ap.add_argument("--pause", type=float, default=0.24, help="句间停顿（秒）")
    ap.add_argument("--chapter-pause", type=float, default=0.90, help="章间停顿（秒）")
    ap.add_argument("--min-cue", type=float, default=0.90, help="单句最短时长")
    ap.add_argument("--skip", default="", help="跳过的镜号（逗号分隔，如片头已含的 S01）")
    ap.add_argument("--offset", type=float, default=0.0, help="整体起点的绝对偏移（秒），如片头长度")
    args = ap.parse_args(argv)

    shots = parse_script(Path(args.script))
    if args.skip:
        skip = {s.strip() for s in args.skip.split(",") if s.strip()}
        shots = [s for s in shots if s[0] not in skip]
    if not shots:
        print("FAIL: no `S##　…` cue lines found in %s" % args.script)
        return 2

    rows, t = [], float(args.offset)
    for i, (shot_id, text, chapter) in enumerate(shots):
        last_in_chapter = bool(chapter) and chapter not in [c for _, _, c in shots[i + 1:]]
        pause = args.chapter_pause if last_in_chapter else args.pause
        dur = max(args.min_cue, visible_len(text) / args.cps) + pause
        rows.append(dict(shot=shot_id, chapter=chapter, text=text,
                         chars=visible_len(text),
                         start=round(t, 3), end=round(t + dur, 3)))
        t = round(t + dur, 3)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    blocks = ["%d\n%s --> %s\n%s\n" % (i, fmt(r["start"]), fmt(r["end"]), r["text"])
              for i, r in enumerate(rows, 1)]
    out.write_text("\n".join(blocks), encoding="utf-8")

    total_chars = sum(r["chars"] for r in rows)
    if args.json:
        Path(args.json).write_text(json.dumps(dict(
            source="估算（无配音）：可见字数/语速＋句间停顿",
            cps=args.cps, pause=args.pause, chapter_pause=args.chapter_pause,
            sentences=len(rows), visible_chars=total_chars, duration=round(t, 3),
            note="估算时间轴，未对真实人声校准；用户配音后自行对轨重排。",
            rows=rows), ensure_ascii=False, indent=1), encoding="utf-8")

    print("sentences=%d chars=%d duration=%.2fs (%d:%05.2f) cps=%.2f"
          % (len(rows), total_chars, t, int(t // 60), t % 60, args.cps))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
