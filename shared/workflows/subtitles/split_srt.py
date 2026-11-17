# -*- coding: utf-8 -*-
"""Split SRT cues into <=20-visible-character cues at semantic breakpoints.

Spec: rules/shared/srt.md §2/§4 (2026-11-14).

Breakpoints, in order: sentence end (。！？), semicolon/colon (；：),
comma/enumeration comma (，、), double dash / ellipsis (—— …… …).
A clause that still exceeds the limit is split on jieba word boundaries
(never inside a word or number string) and reported.

Each source cue keeps its start/end; the new cues split that span in
proportion to visible characters and stay contiguous. Use check_srt.py
afterwards as the gate.

Usage:
  python split_srt.py in.srt --out out.srt --cues-json cues.json \
      --report report.json --max-chars 20 \
      --overrides overrides.json
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

import jieba

TS = re.compile(
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*"
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})"
)
TAIL = "，。；：、！？——……,.!?;:"
BREAK_CHARS = "，、；：。！？"


def visible_len(text):
    return sum(1 for ch in text if unicodedata.category(ch)[0] in ("L", "N"))


def normalize(text):
    """Drop punctuation/symbols/space for G1-style comparison."""
    return re.sub(r"[\W_]+", "", text, flags=re.UNICODE)


def ts_seconds(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000.0


def fmt_ts(sec):
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


def read_srt(path):
    raw = Path(path).read_text(encoding="utf-8-sig")
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    cues = []
    for block in re.split(r"\n\s*\n", raw.strip()):
        lines = block.split("\n")
        ti = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if ti is None:
            continue
        match = TS.search(lines[ti])
        if not match:
            continue
        start = ts_seconds(*match.groups()[:4])
        end = ts_seconds(*match.groups()[4:])
        text = " ".join(line.strip() for line in lines[ti + 1:] if line.strip())
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\{[^}]*\}", "", text).strip()
        cues.append(dict(index=lines[0].strip() if ti > 0 else str(len(cues) + 1),
                         start=start, end=end, text=text))
    return cues


def strip_edges(text):
    return text.strip().strip(TAIL).strip()


def cut_segments(text):
    """Split at semantic punctuation into (text, delimiter) pairs.

    The delimiter stays with the clause before it so that clauses packed into
    the same cue keep their original punctuation; a delimiter at a cue edge is
    dropped by strip_edges().
    """
    text = re.sub(r"\s+", " ", text).strip()
    parts, buf, i = [], [], 0
    while i < len(text):
        if text.startswith("——", i) or text.startswith("……", i):
            parts.append(("".join(buf), text[i:i + 2])); buf = []; i += 2; continue
        ch = text[i]
        if ch in BREAK_CHARS or ch == "…":
            parts.append(("".join(buf), ch)); buf = []; i += 1; continue
        buf.append(ch); i += 1
    parts.append(("".join(buf), ""))
    out = []
    for body, delim in parts:
        body = body.strip()
        if body:
            out.append((body, delim))
        elif delim and out:
            out[-1] = (out[-1][0], out[-1][1] + delim)
    return out


def make_width_fn(font_path, k=0.6875, style_size=96):
    from PIL import ImageFont
    font = ImageFont.truetype(str(font_path), style_size)
    return lambda text: k * font.getlength(text)


def dp_groups(pieces, max_chars, min_pref=6, width_fn=None, max_px=None):
    """Partition contiguous (text, delim) pieces into <=max balanced groups."""
    n = len(pieces)
    inf = float("inf")
    best = [inf] * (n + 1)
    prev = [0] * (n + 1)
    best[0] = 0.0
    for i in range(1, n + 1):
        length = 0
        for j in range(i - 1, -1, -1):
            length += visible_len(pieces[j][0])
            if length > max_chars:
                break
            if width_fn:
                chunk = pieces[j:i]
                text = "".join(body + (delim if k < len(chunk) - 1 else "")
                               for k, (body, delim) in enumerate(chunk))
                if width_fn(text) > max_px:
                    continue
            penalty = (max_chars - length) ** 2
            if length < 4:
                penalty += 120
            elif length < min_pref:
                penalty += 30
            cost = best[j] + penalty
            if cost < best[i]:
                best[i] = cost
                prev[i] = j
    if best[n] == inf:
        raise ValueError("a piece exceeds %d chars or the %.0f px width limit: %r"
                         % (max_chars, max_px or 0, [p[0] for p in pieces]))
    groups, i = [], n
    while i:
        j = prev[i]
        groups.append(pieces[j:i])
        i = j
    return list(reversed(groups))


def word_split(text, max_chars, width_fn=None, max_px=None):
    """Split one overlong clause on word boundaries only."""
    tokens = [t for t in jieba.cut(text) if t.strip()]
    if any(visible_len(t) > max_chars for t in tokens):
        raise ValueError("token longer than %d chars: %r" % (max_chars, text))
    groups = dp_groups([(t, "") for t in tokens], max_chars,
                       width_fn=width_fn, max_px=max_px)
    out = ["".join(t for t, _ in g).strip() for g in groups]
    for piece in out:
        if visible_len(piece) > max_chars:
            raise ValueError("word split failed: %r" % piece)
    return [p for p in out if p]


def distribute(packed, start, end):
    """Split [start, end] across packed texts in proportion to visible chars."""
    weights = [max(1, visible_len(t)) for t in packed]
    total = sum(weights)
    span = max(0.001, end - start)
    t = start
    out = []
    for i, (txt, w) in enumerate(zip(packed, weights)):
        stop = end if i == len(packed) - 1 else t + span * w / total
        out.append(dict(start=t, end=max(t + 0.001, stop), text=strip_edges(txt)))
        t = stop
    out[-1]["end"] = end
    return out


def split_cue(cue, max_chars, overrides=None, allow_word_split=False,
              width_fn=None, max_px=None):
    text = cue["text"].strip()
    too_wide = bool(width_fn) and width_fn(text) > max_px
    if visible_len(text) <= max_chars and not too_wide:
        return [dict(start=cue["start"], end=cue["end"], text=strip_edges(text))], []

    whole = (overrides or {}).get(normalize(text))
    if whole:
        pieces = [p.strip() for p in whole if p.strip()]
        if normalize("".join(pieces)) != normalize(text):
            raise ValueError("override does not match cue: %r -> %r" % (text, pieces))
        for piece in pieces:
            if visible_len(piece) > max_chars:
                raise ValueError("override piece >%d chars: %r" % (max_chars, piece))
            if width_fn and width_fn(piece) > max_px:
                raise ValueError("override piece wider than %.0f px: %r" % (max_px, piece))
        return distribute(pieces, cue["start"], cue["end"]), []

    segments = cut_segments(text)
    pieces, notes = [], []
    for seg, delim in segments:
        curated = (overrides or {}).get(normalize(seg))
        if curated:
            if normalize("".join(curated)) != normalize(seg):
                raise ValueError("override does not match clause: %r -> %r" % (seg, curated))
            split = [p.strip() for p in curated if p.strip()]
            for piece in split:
                if visible_len(piece) > max_chars:
                    raise ValueError("override piece >%d chars: %r" % (max_chars, piece))
                if width_fn and width_fn(piece) > max_px:
                    raise ValueError("override piece wider than %.0f px: %r" % (max_px, piece))
        elif visible_len(seg) <= max_chars and not (width_fn and width_fn(seg) > max_px):
            pieces.append((seg, delim))
            continue
        elif allow_word_split:
            split = word_split(seg, max_chars, width_fn, max_px)
            notes.append(dict(clause=seg, chars=visible_len(seg), pieces=split))
        else:
            raise ValueError(
                "clause >%d chars (or wider than %.0f px) without a legal breakpoint: %r "
                "(add punctuation, revise the script, or pass --allow-word-split)"
                % (max_chars, max_px or 0, seg))
        for k, sub in enumerate(split):
            pieces.append((sub, delim if k == len(split) - 1 else ""))

    packed = []
    for group in dp_groups(pieces, max_chars, width_fn=width_fn, max_px=max_px):
        txt = ""
        for k, (body, delim) in enumerate(group):
            txt += body
            if k < len(group) - 1 and delim:
                txt += delim
        packed.append(strip_edges(txt))
    if normalize("".join(packed)) != normalize(text):
        raise ValueError("G1 mismatch after split: %r -> %r" % (text, packed))

    return distribute(packed, cue["start"], cue["end"]), notes


def write_srt(cues, path):
    lines = []
    for i, c in enumerate(cues, 1):
        lines.append(str(i))
        lines.append("%s --> %s" % (fmt_ts(c["start"]), fmt_ts(c["end"])))
        lines.append(c["text"])
        lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("srt")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cues-json", default="")
    ap.add_argument("--report", default="")
    ap.add_argument("--max-chars", type=int, default=20)
    ap.add_argument("--min-dur", type=float, default=0.7)
    ap.add_argument("--overrides", default="",
                    help="JSON dict: clause text -> list of pieces (curated splits)")
    ap.add_argument("--allow-word-split", action="store_true",
                    help="fallback: split an unbreakable clause on jieba word boundaries")
    ap.add_argument("--font", default="",
                    help="optional font file for a renderer-specific width check")
    ap.add_argument("--style-size", type=int, default=96)
    ap.add_argument("--k", type=float, default=0.6875)
    ap.add_argument("--canvas-width", type=int, default=1920)
    ap.add_argument("--max-width-frac", type=float, default=0.8)
    args = ap.parse_args(argv)

    overrides = {}
    if args.overrides:
        overrides = {normalize(k): v for k, v in
                     json.loads(Path(args.overrides).read_text(encoding="utf-8")).items()}

    width_fn, max_px = None, args.max_width_frac * args.canvas_width
    font_path = args.font
    if font_path:
        width_fn = make_width_fn(font_path, args.k, args.style_size)

    src = read_srt(args.srt)
    if not src:
        print("FAIL: no cues parsed from %s" % args.srt)
        return 1

    out, report = [], []
    for cue in src:
        try:
            pieces, notes = split_cue(cue, args.max_chars, overrides,
                                      args.allow_word_split, width_fn, max_px)
        except ValueError as exc:
            print("FAIL #%s: %s" % (cue["index"], exc))
            return 1
        out.extend(pieces)
        report.append(dict(index=cue["index"], source=cue["text"],
                           source_chars=visible_len(cue["text"]),
                           cues=len(pieces), word_split=notes))

    # clamp overlap introduced by ms rounding, keep sentence spans intact
    for i in range(len(out) - 1):
        if out[i]["end"] > out[i + 1]["start"]:
            out[i]["end"] = out[i + 1]["start"]

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    write_srt(out, args.out)

    counts = [visible_len(c["text"]) for c in out]
    short = [dict(index=i + 1, chars=visible_len(c["text"]), text=c["text"],
                  dur=round(c["end"] - c["start"], 3))
             for i, c in enumerate(out) if c["end"] - c["start"] < args.min_dur]
    word_splits = [n for r in report for n in r["word_split"]]

    if args.cues_json:
        Path(args.cues_json).write_text(json.dumps(
            {"cues": out, "max_chars": max(counts)}, ensure_ascii=False, indent=1),
            encoding="utf-8")
    if args.report:
        Path(args.report).write_text(json.dumps(dict(
            source=args.srt, out=args.out, max_chars=args.max_chars,
            src_cues=len(src), out_cues=len(out),
            chars_min=min(counts), chars_max=max(counts),
            chars_mean=round(sum(counts) / len(counts), 2),
            short_cues=short, word_splits=word_splits, per_source=report,
        ), ensure_ascii=False, indent=1), encoding="utf-8")

    print("src_cues=%d out_cues=%d chars min/max=%d/%d mean=%.2f"
          % (len(src), len(out), min(counts), max(counts), sum(counts) / len(counts)))
    print("word_splits=%d short_lt_%.1fs=%d"
          % (len(word_splits), args.min_dur, len(short)))
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
