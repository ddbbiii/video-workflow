# -*- coding: utf-8 -*-
"""Check an SRT against the 2026-11-13 subtitle length rule.

Spec: rules/shared/srt.md §2/§5 (2026-11-14).

Rule
  * every cue <= --max-chars visible characters (default 20)
  * visible = Unicode letters (Han, Latin, ...) + numbers; punctuation,
    spaces and symbols do not count
  * timing: start < end, cues ordered, no overlap beyond --overlap-ms

Exit code 1 on any violation, 0 when clean. Use --json for a machine report.
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

TS = re.compile(
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*"
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})"
)
DEFAULT_FONT = (Path(__file__).resolve().parents[3] / "assets" / "shared" /
                "subtitles" / "style-r4" / "fonts" / "SourceHanSansSC-Heavy.otf")

def visible_len(text):
    """Count visible characters: letters + numbers, no punctuation/symbols."""
    return sum(1 for ch in text if unicodedata.category(ch)[0] in ("L", "N"))


def ts_seconds(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000.0


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
        text_lines = [line.strip() for line in lines[ti + 1:] if line.strip()]
        text = " ".join(text_lines)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\{[^}]*\}", "", text).strip()
        index = lines[0].strip() if ti > 0 else str(len(cues) + 1)
        cues.append(dict(index=index, start=start, end=end, text=text,
                         chars=visible_len(text), multiline=len(text_lines) > 1))
    return cues


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("srt")
    ap.add_argument("--max-chars", type=int, default=20)
    ap.add_argument("--min-chars", type=int, default=0,
                    help="optional floor; reported as warning only")
    ap.add_argument("--overlap-ms", type=int, default=1)
    ap.add_argument("--font", default="",
                    help="font file for the 80%% width check (default: style_r4 if present)")
    ap.add_argument("--style-size", type=int, default=96)
    ap.add_argument("--k", type=float, default=0.6875,
                    help="rendered/layout width ratio for this font+renderer")
    ap.add_argument("--canvas-width", type=int, default=1920)
    ap.add_argument("--max-width-frac", type=float, default=0.8)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    font_path = args.font or (str(DEFAULT_FONT) if DEFAULT_FONT.exists() else "")

    cues = read_srt(args.srt)
    if not cues:
        print("FAIL: no cues parsed from %s" % args.srt)
        return 1

    over = [c for c in cues if c["chars"] > args.max_chars]
    short = [c for c in cues if c["chars"] < args.min_chars]
    multiline = [c for c in cues if c.get("multiline")]
    timing = []
    for i, c in enumerate(cues):
        if c["end"] <= c["start"]:
            timing.append((c["index"], "non-positive duration %.3f-%.3f"
                           % (c["start"], c["end"])))
        if i and c["start"] + args.overlap_ms / 1000.0 < cues[i - 1]["end"]:
            timing.append((c["index"], "overlaps previous cue by %.3f s"
                           % (cues[i - 1]["end"] - c["start"])))

    widths, over_width = [], []
    max_px = args.max_width_frac * args.canvas_width
    if font_path:
        from PIL import ImageFont
        font = ImageFont.truetype(font_path, args.style_size)
        for c in cues:
            c["width"] = args.k * font.getlength(c["text"])
            widths.append(c["width"])
        over_width = [c for c in cues if c["width"] > max_px]

    counts = [c["chars"] for c in cues]
    summary = dict(
        file=str(args.srt),
        cues=len(cues),
        max_chars=max(counts),
        min_chars=min(counts),
        mean_chars=round(sum(counts) / len(counts), 2),
        over_limit=len(over),
        over=over,
        short=short,
        multiline=multiline,
        timing=timing,
        max_width=round(max(widths), 1) if widths else None,
        over_width=over_width,
        max_allowed=args.max_chars,
        pass_=not over and not timing and not over_width and not multiline,
    )

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("cues=%d  chars min/mean/max=%d/%.2f/%d  max_allowed=%d  over_limit=%d"
              % (len(cues), min(counts), summary["mean_chars"], max(counts),
                 args.max_chars, len(over)))
        if widths:
            print("rendered max_width=%.0f px (%.1f%%)  over_width=%d"
                  % (max(widths), 100.0 * max(widths) / args.canvas_width, len(over_width)))
        for c in over:
            print("  OVER  #%s  %d chars  %s" % (c["index"], c["chars"], c["text"]))
        for c in over_width:
            print("  WIDE  #%s  %.0f px (%.1f%%)  %s"
                  % (c["index"], c["width"], 100.0 * c["width"] / args.canvas_width, c["text"]))
        for c in short:
            print("  SHORT #%s  %d chars  %s (warning)" % (c["index"], c["chars"], c["text"]))
        for c in multiline:
            print("  MULTILINE #%s  %s" % (c["index"], c["text"]))
        for index, msg in timing:
            print("  TIMING #%s  %s" % (index, msg))
        print("RESULT: %s" % ("PASS" if summary["pass_"] else "FAIL"))

    return 0 if summary["pass_"] else 1


if __name__ == "__main__":
    sys.exit(main())
