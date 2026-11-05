# -*- coding: utf-8 -*-
"""Parse NARRATION_MASTER.md v1 into stable paragraph IDs -> audio/utterances.json.

Sections: intro (片头), lead (正文引入), ch01..ch08.
The intro placeholder paragraph (成片实测分钟数) is marked tts_blocked.
Chapter headings and the document preamble are not narrated.
"""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path

EP = Path(__file__).resolve().parents[3]
STORY = EP / "story" / "NARRATION_MASTER.md"
OUT = EP / "audio" / "utterances.json"

SECTION_KEYS = {
    "片头": "intro",
    "正文引入": "lead",
    "第一章": "ch01", "第二章": "ch02", "第三章": "ch03", "第四章": "ch04",
    "第五章": "ch05", "第六章": "ch06", "第七章": "ch07", "第八章": "ch08",
}
PLACEHOLDER_RE = re.compile(r"【成片实测分钟数】")

def main():
    text = STORY.read_text(encoding="utf-8")
    sha = hashlib.sha256(STORY.read_bytes()).hexdigest()
    lines = text.splitlines()
    sections = []          # [(key, title)]
    paragraphs = []        # [(section_key, idx_within_section, text)]
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
        utterances.append(None)  # marker; removed below
    # remove markers
    utterances = [u for u in utterances if u]

    n_chars = sum(len(u["text"]) for u in utterances if not u["tts_blocked"])
    doc = {
        "source": "story/NARRATION_MASTER.md",
        "source_sha256": sha,
        "version": "v1",
        "parsed_at": "2026-10-14",
        "sections": [{"key": k, "title": t} for k, t in sections],
        "paragraph_order": order,
        "narrated_chars": n_chars,
        "notes": [
            "章节标题与文档说明不配音；intro最后一段含【成片实测分钟数】占位，禁止送TTS，音轨确定后回填。",
            "utterance为TTS生成单元（1-2句、约<=80字）；段ID为画面关联单元。",
        ],
        "utterances": utterances,
    }
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
