# -*- coding: utf-8 -*-
"""把 shots_table.py 的镜头表对齐 utterances.json，生成 shots.json。

规则：每镜 cue_start 是本镜第一句（前缀匹配）；本镜覆盖到下一镜起点前的所有句。
时长权重 = 本镜汉字数（句间留白按句数另计），由 timeline 段长归一化。
"""
import json
import re
import sys
from pathlib import Path

EP = Path(r"E:\program\1project\video\projects\悬疑\episodes\20261112-feigongdan")
sys.path.insert(0, str(EP / "storyboard"))
from shots_table import SHOTS, STYLE, CHAR, NEG  # noqa: E402

utts = json.loads((EP / "audio" / "utterances.json").read_text(encoding="utf-8"))["utterances"]
body = [u for u in utts if u["section"] == "body"]

starts = []
cur = 0
for sid, cue_start, move, prompt in SHOTS:
    found = None
    for i in range(cur, len(body)):
        if body[i]["display_text"].startswith(cue_start):
            found = i
            break
    if found is None:
        raise SystemExit(f"[shots] cue_start 未匹配: {sid} {cue_start!r}")
    if found != cur:
        print(f"[warn] {sid} 跳过 {found-cur} 句: {[body[j]['display_text'] for j in range(cur, found)]}")
    starts.append(found)
    cur = found

if starts[0] != 0:
    raise SystemExit("[shots] 第一镜未从第 1 句开始")
# 末尾：最后一镜吃掉剩余句
n = len(body)
spans = []
for k, p in enumerate(starts):
    end = starts[k + 1] if k + 1 < len(starts) else n
    spans.append((p, end))
    if end <= p:
        raise SystemExit(f"[shots] {SHOTS[k][0]} 没有分到句子")

shots = []
for k, (p, end) in enumerate(spans):
    sid, cue_start, move, prompt = SHOTS[k]
    ids = [body[j]["id"] for j in range(p, end)]
    text = "".join(body[j]["display_text"] for j in range(p, end))
    chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    shots.append({
        "id": sid,
        "section": "body",
        "weight": round(chars + 2 * (end - p), 2),  # 字数 + 句间留白当量
        "cue_ids": ids,
        "cue": text,
        "visual": prompt,
        "move": move,
        "evidence": "",
        "characters": ["chenmo"] if sid in {
            "S03", "S19", "S20", "S23", "S26", "S28", "S33", "S35", "S43", "S45", "S48"} else [],
        "prompt_full": STYLE + prompt,
        "negative": NEG,
    })

(EP / "storyboard" / "shots.json").write_text(
    json.dumps({"schema": 1, "episode": "20261112-feigongdan", "shots": shots, "count": len(shots)},
               ensure_ascii=False, indent=1), encoding="utf-8")

print("shots", len(shots), "cues", n)
for s in shots:
    print(s["id"], s["weight"], s["cue"][:28])
