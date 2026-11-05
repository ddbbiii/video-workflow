# -*- coding: utf-8 -*-
"""在 r2 基础上再整体后移 0.5s（用户反馈字幕约早 1s，先半量校正），输出 r3。"""
from __future__ import annotations
import json
import shutil
import sys
from pathlib import Path

EP = Path(r"E:\program\1project\video\4")
RUN = EP / "runs" / "20261103-gla-b01"
R2 = RUN / "subtitles" / "r2"
R3 = RUN / "subtitles" / "r3"
FONT_ASSET = Path(r"E:\program\1project\video\assets\助眠解说\subtitles\style-r4\fonts\SourceHanSansSC-Heavy.otf")
EXTRA = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5


def srt_t(t):
    h, m = int(t // 3600), int(t % 3600 // 60)
    s, ms = int(t % 60), int(round((t % 1) * 1000))
    if ms == 1000:
        s, ms = s + 1, 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def ass_t(t):
    h, m = int(t // 3600), int(t % 3600 // 60)
    s, cs = int(t % 60), int(round((t % 1) * 100))
    if cs == 100:
        s, cs = s + 1, 0
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def main():
    R3.mkdir(parents=True, exist_ok=True)
    doc = json.loads((R2 / "cues.json").read_text(encoding="utf-8"))
    cues = [{**c, "start_s": round(c["start_s"] + EXTRA, 3),
             "end_s": round(c["end_s"] + EXTRA, 3)} for c in doc["cues"]]
    print("extra", EXTRA, "first", cues[0]["start_s"], "last", cues[-1]["end_s"])
    (R3 / "cues.json").write_text(json.dumps({**doc, "cues": cues, "extra_shift_s": EXTRA},
                                            ensure_ascii=False, indent=1), encoding="utf-8")
    with (R3 / "body.srt").open("w", encoding="utf-8-sig") as f:
        for i, c in enumerate(cues, 1):
            f.write(f"{i}\n{srt_t(c['start_s'])} --> {srt_t(c['end_s'])}\n{c['text']}\n\n")
    hdr = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n"
        "WrapStyle: 2\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
        "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding\n"
        "Style: B,Source Han Sans SC Heavy,96,&H00FFFFFF,&H000000FF,&H00000000,"
        "&H80000000,0,0,0,0,100,100,0,0,1,5,2,2,96,96,118,1\n\n[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    with (R3 / "body.ass").open("w", encoding="utf-8") as f:
        f.write("\ufeff" + hdr)
        for c in cues:
            f.write(f"Dialogue: 0,{ass_t(c['start_s'])},{ass_t(c['end_s'])},B,,0,0,0,,{c['text']}\n")
    burn = R3 / "burn"
    (burn / "fonts").mkdir(parents=True, exist_ok=True)
    shutil.copy(R3 / "body.ass", burn / "subs.ass")
    shutil.copy(FONT_ASSET, burn / "fonts" / FONT_ASSET.name)
    print("ok", R3)


if __name__ == "__main__":
    main()
