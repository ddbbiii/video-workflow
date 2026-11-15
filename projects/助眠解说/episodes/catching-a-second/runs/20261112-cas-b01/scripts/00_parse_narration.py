# -*- coding: utf-8 -*-
"""catching-a-second: NARRATION_MASTER.md -> audio/utterances.json

改写自 glacier-river runs/20261103-gla-b01/scripts/01_parse_narration.py。
本集小节：片头(intro)、正文引入(bridge)、第一章..第七章(ch01..ch07)、尾声(epilogue)。
片头单独走 intro-e 流程，不参与正文装配；正文=bridge+ch01..ch07+epilogue。
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

EP = Path(__file__).resolve().parents[3]
STORY = EP / "story" / "NARRATION_MASTER.md"
OUT = EP / "audio" / "utterances.json"

SECTION_KEYS = [
    ("片头", "intro"),
    ("正文引入", "bridge"),
    ("第一章", "ch01"), ("第二章", "ch02"), ("第三章", "ch03"), ("第四章", "ch04"),
    ("第五章", "ch05"), ("第六章", "ch06"), ("第七章", "ch07"),
    ("尾声", "epilogue"),
]
MAX_UNIT = 64  # 字；CosyVoice3 逐单元，过长易重复/漏字


def split_sentences(para: str) -> list[str]:
    parts = re.split(r"(?<=[。！？])", para)
    return [p.strip() for p in parts if p.strip()]


def to_units(para: str) -> list[str]:
    units, cur = [], ""
    for s in split_sentences(para):
        if not cur:
            cur = s
        elif len(cur) + len(s) <= MAX_UNIT:
            cur += s
        else:
            units.append(cur)
            cur = s
    if cur:
        units.append(cur)
    # 单句超长：按 ，、 再切
    out = []
    for u in units:
        if len(u) <= MAX_UNIT * 1.6:
            out.append(u)
            continue
        buf = ""
        for piece in re.split(r"(?<=[，、])", u):
            if not buf:
                buf = piece
            elif len(buf) + len(piece) <= MAX_UNIT:
                buf += piece
            else:
                out.append(buf)
                buf = piece
        if buf:
            out.append(buf)
    return out


def main() -> None:
    text = STORY.read_text(encoding="utf-8")
    sha = hashlib.sha256(STORY.read_bytes()).hexdigest()

    sections, paragraphs = [], []
    cur, buf = None, []

    def flush() -> None:
        nonlocal buf
        if cur is not None and buf:
            joined = "".join(buf).strip()
            if joined:
                paragraphs.append((cur, joined))
        buf = []

    for line in text.splitlines():
        s = line.strip()
        if not s:
            flush()
            continue
        if s.startswith("# ") or s.startswith(">"):
            continue
        if s.startswith("## "):
            flush()
            title = s[3:].strip()
            key = next((k for marker, k in SECTION_KEYS if title.startswith(marker)), None)
            if key is None:
                raise SystemExit(f"unknown section heading: {title}")
            cur = key
            sections.append((key, title))
            continue
        if cur is None:
            continue
        buf.append(s)
    flush()

    counters: dict[str, int] = {}
    utterances, order = [], []
    for key, para in paragraphs:
        counters[key] = counters.get(key, 0) + 1
        pid = f"{key}-p{counters[key]:02d}"
        units = to_units(para)
        for i, u in enumerate(units):
            utterances.append({
                "id": f"{pid}-u{i + 1:02d}",
                "paragraph_id": pid,
                "section": key,
                "text": u,
                "tts_blocked": False,
                "blocked_reason": None,
            })
        order.append(pid)

    body = [u for u in utterances if u["section"] != "intro"]
    n_chars = sum(len(re.findall(r"[\u4e00-\u9fff]", u["text"])) for u in body)

    doc = {
        "source": "story/NARRATION_MASTER.md",
        "source_sha256": sha,
        "version": "v1",
        "parsed_at": "2026-11-12",
        "sections": [{"key": k, "title": t} for k, t in sections],
        "paragraph_order": order,
        "narrated_chars": n_chars,
        "notes": [
            "章节标题与文档说明不配音；片头(intro)走 intro-e 独立流程，正文=bridge+ch01..ch07+epilogue。",
            "utterance 为 TTS 生成单元（1-2 句、≤64 字）；段 ID 为画面关联单元。",
            "片头分钟数按正文实测音轨回填；当前写作值 33 分钟。",
        ],
        "utterances": utterances,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    print("sha256:", sha[:16])
    print("sections:", [k for k, _ in sections])
    print("paragraphs:", len(order), "utterances:", len(utterances), "body_chars:", n_chars)
    for k, _ in sections:
        us = [u for u in utterances if u["section"] == k]
        print(f"  {k}: utts={len(us)} chars={sum(len(u['text']) for u in us)} max={max((len(u['text']) for u in us), default=0)}")


if __name__ == "__main__":
    main()
