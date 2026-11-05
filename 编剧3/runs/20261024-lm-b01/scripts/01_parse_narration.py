# -*- coding: utf-8 -*-
"""Parse NARRATION_MASTER.md v1 into stable paragraph IDs -> audio/utterances.json.

life-manual sections: intro (片头), bridge (故事由来), ch01..ch10, epilogue (尾声).
The intro placeholder paragraph (【正文实测分钟数】) is marked tts_blocked.
Chapter headings and the document preamble are not narrated.

移植自 newton-to-chaos runs/20261014-ntc-b01/scripts/01_parse_narration.py (2026-10-18)。
口播锁定(用户认可 NARRATION_MASTER)后才能运行。
"""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path

EP = Path(__file__).resolve().parents[3]
STORY = EP / "story" / "NARRATION_MASTER.md"
OUT = EP / "audio" / "utterances.json"

SECTION_KEYS = {
    "片头": "intro",
    "引入": "bridge",   # 本集 bridge=原稿"片头"第2-7段(引入),无"故事由来"章
    "第一章": "ch01", "第二章": "ch02", "第三章": "ch03", "第四章": "ch04",
    "第五章": "ch05", "第六章": "ch06", "第七章": "ch07", "第八章": "ch08",
    "第九章": "ch09", "第十章": "ch10",
    "尾声": "epilogue",
}
PLACEHOLDER_RE = re.compile(r"【正文实测分钟数】")

def main():
    text = STORY.read_text(encoding="utf-8")
    sha = hashlib.sha256(STORY.read_bytes()).hexdigest()
    lines = text.splitlines()
    sections = []          # [(key, title)]
    paragraphs = []        # [(section_key, text)]
    cur = None
    buf = []
    def flush():
        nonlocal buf
        if cur is not None and buf:
            joined = "".join(buf).strip()
            if joined:
                paragraphs.append((cur, joined))
        buf = []
    for line in lines:
        s = line.strip()
        if not s:
            flush()
            continue
        if s.startswith("# "):
            flush()
            continue  # doc title
        if s.startswith("## "):
            flush()
            title = s[3:].strip()
            key = None
            for marker, k in SECTION_KEYS.items():
                if title.startswith(marker) or title == marker:
                    key = k
                    break
            if key is None:
                raise SystemExit(f"unknown section heading: {title}")
            cur = key
            sections.append((key, title))
            continue
        # skip the doc preamble paragraph (first block before first ##)
        if cur is None:
            continue
        buf.append(s)
    flush()

    counters = {}
    utterances = []
    order = []
    for key, para in paragraphs:
        counters[key] = counters.get(key, 0) + 1
        pid = f"{key}-p{counters[key]:02d}"
        blocked = bool(PLACEHOLDER_RE.search(para))
        # split into utterances by sentence groups (1-2 sentences, <= ~80 chars)
        sents = re.split(r"(?<=[。？！])", para)
        sents = [x for x in (s.strip() for s in sents) if x]
        chunks = []
        cur_chunk = ""
        for s in sents:
            if cur_chunk and len(cur_chunk) + len(s) > 80:
                chunks.append(cur_chunk)
                cur_chunk = s
            else:
                cur_chunk += s
        if cur_chunk:
            chunks.append(cur_chunk)
        for i, ch in enumerate(chunks):
            uid = f"{pid}-u{i+1:02d}"
            utterances.append({
                "id": uid,
                "paragraph_id": pid,
                "section": key,
                "text": ch,
                "tts_blocked": blocked,
                "blocked_reason": "intro_minute_placeholder" if blocked else None,
            })
        order.append(pid)
    utterances = [u for u in utterances if u]

    n_chars = sum(len(u["text"]) for u in utterances if not u["tts_blocked"])
    doc = {
        "source": "story/NARRATION_MASTER.md",
        "source_sha256": sha,
        "version": "v1",
        "parsed_at": "2026-10-18",
        "sections": [{"key": k, "title": t} for k, t in sections],
        "paragraph_order": order,
        "narrated_chars": n_chars,
        "notes": [
            "章节标题与文档说明不配音；intro最后一段含【正文实测分钟数】占位，禁止送TTS，音轨确定后回填。",
            "utterance为TTS生成单元（1-2句、约<=80字）；段ID为画面关联单元。",
            "正文=bridge+ch01..ch10+epilogue；intro单独走片头(慢钩型)流程，正文视频不含intro段落。",
            "锁定后下一步：02_beats_a/b.py 编排 段落->已有镜头ID 映射，再跑 04_build_shot_plan.py 重建时间轴。",
        ],
        "utterances": utterances,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("sha256:", sha)
    print("sections:", [k for k, _ in sections])
    print("paragraphs:", len(order), "utterances:", len(utterances),
          "tts_blocked:", sum(1 for u in utterances if u["tts_blocked"]),
          "narrated_chars:", n_chars)
    for k, _ in sections:
        n = sum(1 for u in utterances if u["section"] == k and not u["tts_blocked"])
        c = sum(len(u["text"]) for u in utterances if u["section"] == k and not u["tts_blocked"])
        print(f"  {k}: utts={n} chars={c}")

if __name__ == "__main__":
    main()
