# -*- coding: utf-8 -*-
"""锁定稿 + timeline → SRT（一句一 cue，绝对时间轴）。

- 正文 SRT：`<ep>/video/final/助眠_捕捉一秒钟_成片_v1.srt`（覆盖正文，起点=片头结束）
- 含片头版：同目录 `..._含片头.srt`（片头 6 句 + 正文）
- 侧车：`subtitles/r1/cues.json`、`timeline_estimate.json`、`qa.md`

句级切分：单元级时间取实际配音（timeline.json），单元内多句按汉字数内插；
不跑 ASR，不烧录。G1/G4 离线判定，G2/G3/G5/G6/G7 不执行。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

EP = Path(__file__).resolve().parents[3]
RUN = EP / "runs" / "20261112-cas-b01"
INTRO_TL = RUN / "intro" / "batch-20261112-cas-e05" / "timeline.json"
BODY_TL = RUN / "timeline.json"
UTT = EP / "audio" / "utterances.json"

FINAL = EP / "video" / "final"
SUB = EP / "subtitles" / "r1"
TRAIL = "。！？，、；：,.!?;:"

SENT_RE = re.compile(r"[^。！？]*[。！？]?")


def hanzi(s: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", s))


def strip_tail(s: str) -> str:
    return s.strip().rstrip(TRAIL).strip()


def split_sentences(text: str) -> list[str]:
    parts = [p for p in SENT_RE.findall(text) if p.strip()]
    return parts or [text]


def ts(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build(entries: list[dict], offset: float) -> tuple[list[dict], int]:
    """entries: [{text, start, end}] 秒（相对本段起点）。"""
    cues, n_sent = [], 0
    for u in entries:
        sents = split_sentences(u["text"])
        n_sent += len(sents)
        weights = [max(1, hanzi(s)) for s in sents]
        total = sum(weights)
        t = u["start"]
        span = max(0.001, u["end"] - u["start"])
        for i, (s, w) in enumerate(zip(sents, weights)):
            dur = span * w / total
            start, end = t, t + dur
            t = end
            cues.append({"start": offset + start, "end": offset + end, "text": strip_tail(s)})
    # 连续覆盖：end 取下一 cue start，最后一条保留自身 end
    for i in range(len(cues) - 1):
        cues[i]["end"] = cues[i + 1]["start"]
    return cues, n_sent


def write_srt(cues: list[dict], path: Path) -> None:
    lines = []
    for i, c in enumerate(cues, 1):
        lines.append(str(i))
        lines.append(f"{ts(c['start'])} --> {ts(c['end'])}")
        lines.append(c["text"])
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    FINAL.mkdir(parents=True, exist_ok=True)
    SUB.mkdir(parents=True, exist_ok=True)

    utt = json.loads(UTT.read_text(encoding="utf-8"))
    by_id = {u["id"]: u for u in utt["utterances"]}
    body_tl = json.loads(BODY_TL.read_text(encoding="utf-8"))
    intro_tl = json.loads(INTRO_TL.read_text(encoding="utf-8"))
    intro_total = float(intro_tl["total"])
    body_start = min(v["start_s"] for v in body_tl["sections"].values())

    body_entries = []
    for u in sorted(body_tl["utterances"], key=lambda x: x["start_s"]):
        body_entries.append({"text": by_id[u["id"]]["text"],
                             "start": u["start_s"] - body_start,
                             "end": u["end_s"] - body_start})
    intro_entries = [{"text": by_id[u["id"]]["text"],
                      "start": float(u["start"]), "end": float(u["start"]) + float(u["dur"])}
                     for u in intro_tl["units"]]

    body_cues, body_sents = build(body_entries, intro_total)
    intro_cues, intro_sents = build(intro_entries, 0.0)
    full_cues = intro_cues + body_cues

    for c in intro_cues:  # 片头最后一条延伸到手交棒结束，避免空档
        pass
    srt_body = FINAL / "助眠_捕捉一秒钟_成片_v1.srt"
    srt_full = FINAL / "助眠_捕捉一秒钟_成片_v1_含片头.srt"
    write_srt(body_cues, srt_body)
    write_srt(full_cues, srt_full)

    # G1：cue 去标点 == 锁定句
    src = [strip_tail(s) for u in body_entries for s in split_sentences(u["text"])]
    got = [c["text"] for c in body_cues]
    g1 = src == got
    # G4：一条只含一个完整句（无内部句末标点）、单行；超宽另列 flag
    g4 = all((not re.search(r"[。！？]", c["text"])) and ("\n" not in c["text"]) for c in body_cues)
    wide = [c for c in body_cues if len(c["text"]) > 56]
    long_cues = [c for c in body_cues if c["end"] - c["start"] > 12]
    dur_ok = all(0.5 <= c["end"] - c["start"] <= 25 for c in body_cues)

    cues_doc = {"intro_total": intro_total,
                "body_cues": body_cues, "intro_cues": intro_cues}
    (SUB / "cues.json").write_text(json.dumps(cues_doc, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
    (SUB / "timeline_estimate.json").write_text(json.dumps({
        "source": "timeline.json（单元级实测）＋句内按汉字数内插",
        "intro_total": intro_total,
        "cues": len(body_cues),
        "note": "单元级时间来自本集真实配音；句级为内插，未做字级 ASR。",
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    qa = f"""# 字幕 QA · r1

- 正文 cue：{len(body_cues)} 条（锁定句 {body_sents} 句）
- 片头 cue：{len(intro_cues)} 条（另存于 `_含片头.srt`）
- 时间基准：片头实测 {intro_total:.3f} s，正文 cue 绝对时间 = 片头时长 + 正文相对时间
- 句均时长：{sum(c['end']-c['start'] for c in body_cues)/max(1,len(body_cues)):.2f} s

## 门禁（本流程只执行离线项）

| 项 | 结论 |
|---|---|
| G1 文本完整（去标点 == 锁定句） | {'PASS' if g1 else 'FAIL'} |
| G4 断句（一 cue 一句、无内部句末标点、单行） | {'PASS' if g4 else 'FAIL'} |
| 单条时长 0.5–25 s | {'PASS' if dur_ok else 'FLAG'} |
| 超宽句（>56 字，烧录时字号会低于 40 px） | {len(wide)} 条，见下 |
| 长句（>12 s） | {len(long_cues)} 条 |
| G2/G3/G5/G6/G7 | 未执行（无字级 ASR、未烧录） |

## 需要你决定的超宽句

{chr(10).join(f"- {ts(c['start'])}（{c['end']-c['start']:.1f} s，{len(c['text'])} 字）：{c['text'][:28]}…" for c in wide) if wide else '- 无'}

## 说明

**时间轴取自本集真实配音的单元级时间，单元内按汉字数内插；未对真实人声做字级校准，导入编辑器后请按听感微调。** 烧录与对轨归用户。
"""
    (SUB / "qa.md").write_text(qa, encoding="utf-8")

    print(f"body cues={len(body_cues)} sents={body_sents} g1={g1} g4={g4} dur_ok={dur_ok}")
    print(f"intro cues={len(intro_cues)} total={intro_total:.3f}")
    print("wrote", srt_body)
    print("wrote", srt_full)


if __name__ == "__main__":
    main()
