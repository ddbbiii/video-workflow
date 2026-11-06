# -*- coding: utf-8 -*-
"""Split Chinese narration into short subtitle cues (<=18 chars/line, <=2 lines)."""

PUNCT = "，。？！；：、"


def split_lines(text, maxlen=16):
    text = text.strip()
    lines, cur = [], ""
    for ch in text:
        cur += ch
        if len(cur) >= maxlen:
            lines.append(cur)
            cur = ""
        elif ch in PUNCT and len(cur) >= maxlen * 0.55:
            lines.append(cur)
            cur = ""
    if cur:
        lines.append(cur)
    # merge a tiny tail into previous line
    if len(lines) >= 2 and len(lines[-1]) <= 3:
        lines[-2] += lines[-1]
        lines.pop()
    return lines


def cues(text, maxlen=18, max_lines=2):
    lines = split_lines(text, maxlen)
    out = []
    for i in range(0, len(lines), max_lines):
        out.append("\\N".join(lines[i:i + max_lines]))
    return out


def timed_cues(start, dur, text, maxlen=18, max_lines=2):
    parts = cues(text, maxlen, max_lines)
    if not parts:
        return []
    total = sum(len(p.replace("\\N", "")) for p in parts)
    out, cum = [], 0
    for p in parts:
        n = len(p.replace("\\N", ""))
        s = start + dur * cum / total
        cum += n
        e = start + dur * cum / total
        if e - s < 0.35:
            e = s + 0.35
        out.append((s, e, p))
    out[-1] = (out[-1][0], start + dur, out[-1][2])
    return out
