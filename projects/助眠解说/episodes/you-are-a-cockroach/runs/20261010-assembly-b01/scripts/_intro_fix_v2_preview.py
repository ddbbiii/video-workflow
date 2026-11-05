# -*- coding: utf-8 -*-
"""Intro fix v2: center zooming intro ASS + 2s title card + preview_head24s."""
from __future__ import annotations
import json, math, shutil, subprocess, sys, wave
from pathlib import Path
from datetime import datetime, timezone, timedelta

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\you-are-a-cockroach")
RUN = EP / "runs" / "20261010-assembly-b01"
OUT = RUN / "intro_v2"
FFMPEG = Path(r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe")
FFPROBE = FFMPEG.with_name("ffprobe.exe")
FONT_DIR = Path(r"E:\program\1project\video\assets\助眠解说\subtitles\style-r4\fonts")
STILL = EP / "image" / "stills" / "intro-art-01.jpg"
SR = 48000
FPS = 30
TZ = timezone(timedelta(hours=8))
TITLE_MAIN = "你是一只蟑螂"
TITLE_SUB = "落叶下的漫长演化"
TITLE_DUR = 2.0

# Measured from intro_audio_concat parts
LINES = [
    # start, end, text (with \\N), transform_ms
    (0.40, 6.810375, "你是一只蟑螂。\\N刚刚，你从捕食者的嘴边逃了出来。", 6410),
    (7.260375, 12.924729, "现在，你藏在树皮下面，\\N等待外面的影子离开。", 5664),
    (13.374729, 20.841229, "接下来的45分钟，我们来讲讲蟑螂这个家族，\\N漫长的演化史。", 7467),
]

def now_iso():
    return datetime.now(TZ).isoformat(timespec="seconds")

def atomic_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)

def probe(path: Path) -> float:
    r = subprocess.run([str(FFPROBE), "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())

def ass_time(t: float) -> str:
    if t < 0:
        t = 0
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def write_silence_stereo(path: Path, seconds: float):
    samples = int(round(seconds * SR))
    with wave.open(str(path), "w") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"\x00\x00\x00\x00" * samples)

def ensure_fonts_link(work: Path):
    fonts = work / "fonts"
    if fonts.exists():
        return
    try:
        fonts.symlink_to(FONT_DIR, target_is_directory=True)
    except OSError:
        # copy heavy font only if symlink fails
        fonts.mkdir(parents=True, exist_ok=True)
        src = FONT_DIR / "SourceHanSansSC-Heavy.otf"
        dst = fonts / "SourceHanSansSC-Heavy.otf"
        if not dst.exists():
            shutil.copy2(src, dst)

def write_intro_ass(path: Path):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: IntroCenter,Source Han Sans SC Heavy,78,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,7,0,5,64,64,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    for start, end, text, tms in LINES:
        tag = "{\\fscx85\\fscy85\\t(0," + str(tms) + ",\\fscx110\\fscy110)}"
        ev.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},IntroCenter,,0,0,0,,{tag}{text}")
    path.write_text(header + "\n".join(ev) + "\n", encoding="utf-8")

def write_title_ass(path: Path):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TitleMain,Source Han Sans SC Heavy,120,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,8,0,5,64,64,0,1
Style: TitleSub,Source Han Sans SC Heavy,56,&H00E8E8E8,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,4,0,1,5,0,5,64,64,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = [
        f"Dialogue: 0,0:00:00.00,0:00:02.00,TitleMain,,0,0,0,,{{\\pos(960,470)}}{TITLE_MAIN}",
        f"Dialogue: 0,0:00:00.00,0:00:02.00,TitleSub,,0,0,0,,{{\\pos(960,610)}}{TITLE_SUB}",
    ]
    path.write_text(header + "\n".join(ev) + "\n", encoding="utf-8")

def run(cmd, cwd=None, log=None):
    print("$", " ".join(map(str, cmd)))
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if log:
        log.write_text((r.stdout or "") + "\n" + (r.stderr or ""), encoding="utf-8")
    if r.returncode != 0:
        print(r.stderr[-1200:] if r.stderr else r.stdout[-1200:])
        raise SystemExit(f"cmd failed rc={r.returncode}")
    return r

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    logs = OUT / "logs"
    logs.mkdir(exist_ok=True)
    work = OUT / "work"
    work.mkdir(exist_ok=True)
    ensure_fonts_link(work)

    atomic_json(OUT / "CHECKPOINT.json", {
        "stage": "preview_head",
        "completed": [],
        "running": ["build_intro_ass", "title_card", "preview"],
        "next_action": "preview_head24s then full remux",
        "updated_at": now_iso(),
    })

    intro_video = RUN / "intro" / "intro_video.mp4"
    intro_stereo = RUN / "intro" / "intro_stereo.wav"
    assert intro_video.is_file(), intro_video
    assert intro_stereo.is_file(), intro_stereo
    assert STILL.is_file(), STILL

    intro_ass = OUT / "intro.ass"
    write_intro_ass(intro_ass)
    title_ass = OUT / "title.ass"
    write_title_ass(title_ass)

    # copy ass into work for relative fontsdir
    (work / "intro.ass").write_text(intro_ass.read_text(encoding="utf-8"), encoding="utf-8")
    (work / "title.ass").write_text(title_ass.read_text(encoding="utf-8"), encoding="utf-8")

    # 1) burn intro center subs
    intro_with_subs = OUT / "intro_with_subs.mp4"
    run([
        str(FFMPEG), "-y", "-i", str(intro_video),
        "-vf", "ass=intro.ass:fontsdir=fonts",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-an", str(intro_with_subs),
    ], cwd=str(work), log=logs / "burn_intro.log")
    # move from work if ffmpeg wrote relative — we gave absolute OUT path so ok
    print("intro_with_subs", probe(intro_with_subs), "s", intro_with_subs.stat().st_size)

    # 2) title card 2s from still + darken + title ASS
    title_card = OUT / "title_card_2s.mp4"
    # build darkened still video then burn ASS (two-step for reliability)
    title_base = OUT / "title_base.mp4"
    run([
        str(FFMPEG), "-y", "-loop", "1", "-i", str(STILL),
        "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,eq=brightness=-0.15:saturation=0.8:contrast=1.05",
        "-t", str(TITLE_DUR), "-r", str(FPS),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-an", str(title_base),
    ], log=logs / "title_base.log")
    run([
        str(FFMPEG), "-y", "-i", str(title_base),
        "-vf", "ass=title.ass:fontsdir=fonts",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-an", str(title_card),
    ], cwd=str(work), log=logs / "title_burn.log")
    print("title_card", probe(title_card), "s")

    # screenshot of title card mid frame
    shot = OUT / "title_card_frame.jpg"
    run([
        str(FFMPEG), "-y", "-ss", "1.0", "-i", str(title_card),
        "-frames:v", "1", "-q:v", "2", str(shot),
    ], log=logs / "title_shot.log")

    # 3) concat intro_with_subs + title_card (re-encode for safety)
    head_video = OUT / "head_video.mp4"
    concat_list = OUT / "head_concat.txt"
    concat_list.write_text(
        f"file '{intro_with_subs.as_posix()}'\nfile '{title_card.as_posix()}'\n",
        encoding="utf-8",
    )
    run([
        str(FFMPEG), "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-an", str(head_video),
    ], log=logs / "head_concat.log")
    head_s = probe(head_video)
    print("head_video", head_s)

    # 4) audio: intro_stereo + 2s silence
    silence = OUT / "silence_2s.wav"
    write_silence_stereo(silence, TITLE_DUR)
    audio_list = OUT / "head_audio_concat.txt"
    audio_list.write_text(
        f"file '{intro_stereo.as_posix()}'\nfile '{silence.as_posix()}'\n",
        encoding="utf-8",
    )
    head_audio = OUT / "head_audio.wav"
    run([
        str(FFMPEG), "-y", "-f", "concat", "-safe", "0", "-i", str(audio_list),
        "-c", "pcm_s16le", str(head_audio),
    ], log=logs / "head_audio.log")
    print("head_audio", probe(head_audio))

    # 5) preview mux
    preview = OUT / "preview_head24s.mp4"
    run([
        str(FFMPEG), "-y", "-i", str(head_video), "-i", str(head_audio),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
        str(preview),
    ], log=logs / "preview_mux.log")
    print("PREVIEW", preview, probe(preview), "MB", round(preview.stat().st_size / 1e6, 2))

    # also extract frames at mid of each intro line for QA
    for i, (start, end, *_rest) in enumerate(LINES, 1):
        mid = (start + end) / 2
        fp = OUT / f"preview_line{i}_t{mid:.2f}.jpg"
        run([
            str(FFMPEG), "-y", "-ss", f"{mid:.3f}", "-i", str(preview),
            "-frames:v", "1", "-q:v", "2", str(fp),
        ], log=logs / f"frame_line{i}.log")

    meta = {
        "created_at": now_iso(),
        "intro_audio_s": probe(intro_stereo),
        "intro_video_s": probe(intro_video),
        "intro_with_subs_s": probe(intro_with_subs),
        "title_card_s": probe(title_card),
        "head_video_s": head_s,
        "head_audio_s": probe(head_audio),
        "preview_s": probe(preview),
        "title_main": TITLE_MAIN,
        "title_sub": TITLE_SUB,
        "still": str(STILL),
        "lines": [{"start": a, "end": b, "text": t.replace("\\N", " / ")} for a, b, t, _ in LINES],
        "preview": str(preview),
        "title_card_frame": str(shot),
    }
    atomic_json(OUT / "preview_meta.json", meta)
    atomic_json(OUT / "CHECKPOINT.json", {
        "stage": "preview_done",
        "completed": ["intro_ass", "title_card", "preview_head24s"],
        "running": [],
        "next_action": "full remux clean/sub after preview OK",
        "updated_at": now_iso(),
        "preview": str(preview),
    })
    print("OK", json.dumps(meta, ensure_ascii=False))

if __name__ == "__main__":
    main()