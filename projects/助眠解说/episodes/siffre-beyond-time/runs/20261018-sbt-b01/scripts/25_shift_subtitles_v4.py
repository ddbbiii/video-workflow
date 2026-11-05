# -*- coding: utf-8 -*-
"""字幕整体平移 v4(2026-10-20 片头 v4 快钩标准四段重制;任务书:文本不变,不重对齐)。

片头起点 43.363s(r1 真源,v2 慢钩对齐基) -> 23.825s(v4 实测),全部 cue 整体
平移 delta = v4 片头 - 43.363;正文语音相对时间轴未变(body_narration.wav 未动),
因此平移即精确,无需重跑 FunASR 对齐。真源取 r1(非 r2):r1 是唯一对齐记录,
r2/r3 均由其派生,避免平移误差累积(0.001s 级舍入同理)。

输出:runs/.../subtitles/r3/{cues.json, body.srt, body.ass, burn/};
重烧 video/final/siffre-beyond-time_sub.mp4(-c:a copy;音轨哈希与 clean 核验)。
r1/r2 原样保留。烧录口径同 22 号(cwd=烧录目录+fontsdir 相对路径)。
移植自 24_shift_subtitles_v3.py(v4:r3 目录,基 r1)。
"""
from __future__ import annotations
import hashlib, json, shutil, subprocess
from pathlib import Path

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\siffre-beyond-time")
RUN = EP / "runs" / "20261018-sbt-b01"
SRC = RUN / "subtitles" / "r1" / "cues.json"
OUT = RUN / "subtitles" / "r3"
INTRO_TL = RUN / "intro_timeline.json"
CLEAN = EP / "video" / "final" / "siffre-beyond-time_clean.mp4"
SUB_OUT = EP / "video" / "final" / "siffre-beyond-time_sub.mp4"
FONT_ASSET = Path(r"E:\program\1project\video\assets\助眠解说\subtitles\style-r4\fonts\SourceHanSansSC-Heavy.otf")
FFMPEG = r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"
BURN_CRF, BURN_PRESET = "19", "veryfast"


def main():
    cd = json.loads(SRC.read_text(encoding="utf-8"))
    old_offset = float(cd["intro_seconds"])
    new_offset = json.loads(INTRO_TL.read_text(encoding="utf-8"))["intro_seconds"]
    delta = round(new_offset - old_offset, 3)
    cues = cd["cues"]
    shifted = []
    for c in cues:
        s, e = round(c["start_s"] + delta, 3), round(c["end_s"] + delta, 3)
        assert s >= 0, f"cue 平移后为负: {c}"
        shifted.append({"unit": c["unit"], "text": c["text"], "start_s": s, "end_s": e})
    # 不变量校验:条数/文本逐字一致/相对时长不变/无重叠
    assert len(shifted) == len(cues)
    assert all(a["text"] == b["text"] for a, b in zip(cues, shifted))
    assert all(abs((a["end_s"] - a["start_s"]) - (b["end_s"] - b["start_s"])) < 0.002
               for a, b in zip(cues, shifted))
    overlaps = [i for i in range(len(shifted) - 1)
                if shifted[i]["end_s"] > shifted[i + 1]["start_s"] + 1e-6]
    assert not overlaps, f"平移引入重叠 {overlaps}"

    OUT.mkdir(parents=True, exist_ok=True)
    doc = {**cd, "intro_seconds": new_offset, "cues": shifted,
           "shift": {"from_offset_s": old_offset, "to_offset_s": new_offset,
                     "delta_s": delta, "method": "整体平移,文本与正文相对时间不变,未重对齐",
                     "source_cues": str(SRC),
                     "note": "v4:基 r1 真源单次平移(r2 为 v3 版记录,保留)"}}
    (OUT / "cues.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                                   encoding="utf-8")

    def srt_t(t):
        h, m = int(t // 3600), int(t % 3600 // 60)
        s, ms = int(t % 60), int(round((t % 1) * 1000))
        if ms == 1000: s, ms = s + 1, 0
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    with (OUT / "body.srt").open("w", encoding="utf-8-sig") as f:
        for i, c in enumerate(shifted, 1):
            f.write(f"{i}\n{srt_t(c['start_s'])} --> {srt_t(c['end_s'])}\n{c['text']}\n\n")

    def ass_t(t):
        h, m = int(t // 3600), int(t % 3600 // 60)
        s, cs = int(t % 60), int(round((t % 1) * 100))
        if cs == 100: s, cs = s + 1, 0
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

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
    with (OUT / "body.ass").open("w", encoding="utf-8") as f:
        f.write("\ufeff" + hdr)
        for c in shifted:
            f.write(f"Dialogue: 0,{ass_t(c['start_s'])},{ass_t(c['end_s'])},B,,0,0,0,,{c['text']}\n")

    print(f"cues {len(shifted)} shifted by {delta:+.3f}s "
          f"({old_offset:.3f} -> {new_offset:.3f}); "
          f"span {shifted[0]['start_s']:.3f}-{shifted[-1]['end_s']:.3f}s")

    # ---- 烧录(口径同 22 号)----
    burn = OUT / "burn"
    burn.mkdir(exist_ok=True)
    (burn / "fonts").mkdir(exist_ok=True)
    shutil.copy(OUT / "body.ass", burn / "subs.ass")
    shutil.copy(FONT_ASSET, burn / "fonts" / FONT_ASSET.name)
    r = subprocess.run([FFMPEG, "-y", "-i", str(CLEAN),
                        "-vf", "subtitles=subs.ass:fontsdir=fonts",
                        "-c:v", "libx264", "-preset", BURN_PRESET, "-crf", BURN_CRF,
                        "-pix_fmt", "yuv420p", "-c:a", "copy",
                        "-movflags", "+faststart", str(SUB_OUT)],
                       capture_output=True, text=True, cwd=str(burn))
    if r.returncode != 0:
        raise RuntimeError("burn failed: " + (r.stderr or "")[-800:])
    print(f"burn OK -> {SUB_OUT} ({SUB_OUT.stat().st_size // 1024 // 1024}MB)")

    # ---- 音轨哈希核验 ----
    def audio_md5(video, tmp):
        subprocess.run([FFMPEG, "-y", "-i", str(video), "-map", "0:a:0",
                        "-c:a", "copy", "-f", "adts", str(tmp)],
                       capture_output=True, text=True)
        return hashlib.md5(tmp.read_bytes()).hexdigest()
    t1, t2 = burn / "_a1.aac", burn / "_a2.aac"
    h1, h2 = audio_md5(CLEAN, t1), audio_md5(SUB_OUT, t2)
    t1.unlink(); t2.unlink()
    print(f"audio md5 clean={h1[:12]} sub={h2[:12]} same={h1 == h2}")
    if h1 != h2:
        raise RuntimeError("烧录后音轨与 clean 不一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
