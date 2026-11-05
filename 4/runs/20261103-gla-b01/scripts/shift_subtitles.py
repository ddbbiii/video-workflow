# -*- coding: utf-8 -*-
"""把 r1 字幕整体平移到新片头时长（片头 43.033s -> intro_v2 10.59s）。

不需要重跑 ASR：cues 的显示文本与单元内字级时间都是对的，只是绝对偏移变了。
输出 subtitles/r2/{cues.json, body.srt, body.ass, burn/}。
"""
from __future__ import annotations
import json
import shutil
from pathlib import Path

EP = Path(r"E:\program\1project\video\4")
RUN = EP / "runs" / "20261103-gla-b01"
R1 = RUN / "subtitles" / "r1"
R2 = RUN / "subtitles" / "r2"
INTRO_TL = RUN / "intro_v2" / "intro_timeline.json"
FONT_ASSET = Path(r"E:\program\1project\video\assets\助眠解说\subtitles\style-r4\fonts\SourceHanSansSC-Heavy.otf")


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
    R2.mkdir(parents=True, exist_ok=True)
    old = json.loads((R1 / "cues.json").read_text(encoding="utf-8"))
    new_intro = json.loads(INTRO_TL.read_text(encoding="utf-8"))["intro_seconds"]
    shift = new_intro - old["intro_seconds"]
    cues = []
    for c in old["cues"]:
        cues.append({**c, "start_s": round(c["start_s"] + shift, 3),
                     "end_s": round(c["end_s"] + shift, 3)})
    print("shift", round(shift, 3), "cues", len(cues),
          "span", cues[0]["start_s"], cues[-1]["end_s"])
    out = {**old, "intro_seconds": new_intro, "cues": cues,
           "shift_from_r1_s": round(shift, 3)}
    (R2 / "cues.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    with (R2 / "body.srt").open("w", encoding="utf-8-sig") as f:
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
    with (R2 / "body.ass").open("w", encoding="utf-8") as f:
        f.write("\ufeff" + hdr)
        for c in cues:
            f.write(f"Dialogue: 0,{ass_t(c['start_s'])},{ass_t(c['end_s'])},B,,0,0,0,,{c['text']}\n")

    burn = R2 / "burn"
    (burn / "fonts").mkdir(parents=True, exist_ok=True)
    shutil.copy(R2 / "body.ass", burn / "subs.ass")
    shutil.copy(FONT_ASSET, burn / "fonts" / FONT_ASSET.name)
    print("ok", R2)


if __name__ == "__main__":
    main()
