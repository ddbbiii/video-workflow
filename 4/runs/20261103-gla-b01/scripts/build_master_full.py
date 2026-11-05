# -*- coding: utf-8 -*-
"""从完整剧本 md 生成全量 NARRATION_MASTER（零改字）。

规则：
- 只取每个 ## 章节下的旁白段落；[画面…]、[停顿…]、[最后一句…] 等方括号提示行跳过；
- 文档开头的说明块跳过；
- 片头沿用预览版的 5 个呼吸段（逐字不变，保证已生成配音可复用）；
- 其余章节按 md 原段落顺序逐段收录，不改一个字。
"""
from __future__ import annotations
import json
import re
from pathlib import Path

EP = Path(r"E:\program\1project\video\4")
SRC = EP / "冰川是一条缓慢的河_完整版助眠剧本.md"
PREVIEW = EP / "story" / "NARRATION_MASTER.md"
OUT = EP / "story" / "NARRATION_MASTER_FULL.md"

SECTION_MAP = [
    ("片头", "intro"),
    ("第一章", "ch01"), ("第二章", "ch02"), ("第三章", "ch03"), ("第四章", "ch04"),
    ("第五章", "ch05"), ("第六章", "ch06"), ("第七章", "ch07"), ("第八章", "ch08"),
    ("第九章", "ch09"), ("第十章", "ch10"), ("第十一章", "ch11"), ("第十二章", "ch12"),
    ("尾声", "epilogue"),
]


def parse_md(text):
    sections = []       # [(key, title)]
    paras = []          # [(key, text)]
    cur = None
    buf = []

    def flush():
        nonlocal buf
        if cur and buf:
            s = "".join(buf).strip()
            if s:
                paras.append((cur, s))
        buf = []

    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            flush()
            continue
        if s.startswith("# "):
            flush()
            continue
        if s.startswith("## "):
            flush()
            title = s[3:].strip()
            norm = re.sub(r"^\d+[｜|]\s*", "", title)
            key = None
            for marker, k in SECTION_MAP:
                if norm.startswith(marker):
                    key = k
                    break
            if key is None:
                cur = None      # 参考时间轴/制作提示/参考资料等附录：跳过
                continue
            cur = key
            sections.append((key, title))
            continue
        if s.startswith("[") and s.endswith("]"):
            continue
        if s.startswith("**") or s.startswith("-") or s.startswith("|") or s.startswith(">"):
            continue
        if cur is None:
            continue
        buf.append(s)
    flush()
    return sections, paras


def preview_intro():
    text = PREVIEW.read_text(encoding="utf-8")
    body = text.split("## 片头")[1].split("## 第一章")[0]
    blocks = [b.strip() for b in re.split(r"\n\s*\n", body) if b.strip()]
    # body 开头是 "｜一条没有水声的河" 这半个标题行，去掉
    if blocks and blocks[0].startswith("｜"):
        blocks = blocks[1:]
    return blocks


def main():
    sections, paras = parse_md(SRC.read_text(encoding="utf-8"))
    intro = preview_intro()
    out_sections = []
    out_paras = []
    for key, title in sections:
        out_sections.append((key, title))
        if key == "intro":
            for p in intro:
                out_paras.append((key, p))
        else:
            for k, p in paras:
                if k == key:
                    out_paras.append((key, p))

    lines = ["# 《冰川是一条缓慢的河》口播（全片 v1.0）", "",
             "来源：`冰川是一条缓慢的河_完整版助眠剧本.md`（2026-11-03 15:53）。",
             "由剧本旁白段逐字生成，**零改字**；只做分节与片头 5 段呼吸分组。",
             "方括号画面提示、制作备注、参考时间轴、参考资料均不参与配音。",
             "章节名不配音。", ""]
    cur = None
    for key, title in out_sections:
        lines.append(f"## {title}")
        lines.append("")
        for k, p in out_paras:
            if k == key:
                lines.append(p)
                lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")

    total = sum(len(p) for _, p in out_paras)
    print("sections:", len(out_sections), "paragraphs:", len(out_paras), "chars:", total)
    from collections import Counter
    c = Counter(k for k, _ in out_paras)
    for key, _ in out_sections:
        print(f"  {key}: {c[key]} paras, {sum(len(p) for k,p in out_paras if k==key)} chars")


if __name__ == "__main__":
    main()
