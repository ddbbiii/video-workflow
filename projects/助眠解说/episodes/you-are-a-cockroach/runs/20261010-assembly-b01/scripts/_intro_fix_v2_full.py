# -*- coding: utf-8 -*-
"""Intro fix v2 full remux: backup, concat head+body, new clean/sub, QA notes."""
from __future__ import annotations
import json, math, shutil, subprocess, sys, wave
from pathlib import Path
from datetime import datetime, timezone, timedelta

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\you-are-a-cockroach")
RUN = EP / "runs" / "20261010-assembly-b01"
OUT = RUN / "intro_v2"
DELIVERY = RUN / "delivery"
SUBS = RUN / "subs"
AUDIO = RUN / "audio"
FFMPEG = Path(r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe")
FFPROBE = FFMPEG.with_name("ffprobe.exe")
FONT_DIR = Path(r"E:\program\1project\video\assets\助眠解说\subtitles\style-r4\fonts")
TZ = timezone(timedelta(hours=8))
TITLE_DUR = 2.0

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

def run(cmd, cwd=None, log=None):
    print("$", " ".join(map(str, cmd)), flush=True)
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text((r.stdout or "") + "\n" + (r.stderr or ""), encoding="utf-8")
    if r.returncode != 0:
        err = (r.stderr or r.stdout or "")[-1500:]
        print(err, flush=True)
        raise SystemExit(f"cmd failed rc={r.returncode}")
    return r

def shift_ts(ts: str, off: float) -> str:
    h, m, rest = ts.split(":")
    s, cs = rest.split(".")
    total = int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100.0 + off
    if total < 0:
        total = 0
    cs2 = int(round(total * 100))
    h, cs2 = divmod(cs2, 360000)
    m, cs2 = divmod(cs2, 6000)
    s, cs2 = divmod(cs2, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs2:02d}"

def backup(path: Path, suffix="_pre_introfix"):
    if not path.is_file() or path.stat().st_size < 1000:
        return None
    bak = path.with_name(path.stem + suffix + path.suffix)
    if bak.exists():
        print("backup exists, skip", bak)
        return bak
    print("backup", path.name, "->", bak.name, flush=True)
    shutil.move(str(path), str(bak))
    return bak

def main():
    logs = OUT / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    atomic_json(OUT / "CHECKPOINT.json", {
        "stage": "full_remux",
        "completed": ["intro_ass", "title_card", "preview_head24s"],
        "running": ["full_concat", "clean", "sub"],
        "next_action": "full remux",
        "updated_at": now_iso(),
    })

    head_video = OUT / "head_video.mp4"
    head_audio = OUT / "head_audio.wav"
    body_video = DELIVERY / "body_video.mp4"
    body_mix = AUDIO / "mix-master.wav"
    for p in (head_video, head_audio, body_video, body_mix):
        assert p.is_file(), p

    head_audio_s = probe(head_audio)
    print("head_audio_s", head_audio_s, flush=True)

    # backup delivery masters
    clean_path = DELIVERY / "you-are-a-cockroach_clean.mp4"
    sub_path = DELIVERY / "you-are-a-cockroach_sub.mp4"
    bak_clean = backup(clean_path)
    bak_sub = backup(sub_path)
    # also backup old full_video / full_mix if present
    backup(DELIVERY / "full_video.mp4")
    backup(DELIVERY / "full_mix.wav")

    # full video concat
    full_list = OUT / "full_concat.txt"
    full_list.write_text(
        f"file '{head_video.as_posix()}'\nfile '{body_video.as_posix()}'\n",
        encoding="utf-8",
    )
    full_video = OUT / "full_video.mp4"
    # try stream copy first
    r = subprocess.run([
        str(FFMPEG), "-y", "-f", "concat", "-safe", "0", "-i", str(full_list),
        "-c", "copy", str(full_video),
    ], capture_output=True, text=True)
    (logs / "full_concat_copy.log").write_text((r.stdout or "") + "\n" + (r.stderr or ""), encoding="utf-8")
    if r.returncode != 0 or not full_video.is_file() or full_video.stat().st_size < 1_000_000:
        print("copy concat failed, re-encode", flush=True)
        run([
            str(FFMPEG), "-y", "-f", "concat", "-safe", "0", "-i", str(full_list),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
            "-an", str(full_video),
        ], log=logs / "full_concat_reenc.log")
    print("full_video", probe(full_video), "MB", round(full_video.stat().st_size / 1e6, 1), flush=True)

    # full audio = head + body mix (body mix has no intro)
    audio_list = OUT / "full_audio_concat.txt"
    audio_list.write_text(
        f"file '{head_audio.as_posix()}'\nfile '{body_mix.as_posix()}'\n",
        encoding="utf-8",
    )
    full_mix = OUT / "full_mix.wav"
    run([
        str(FFMPEG), "-y", "-f", "concat", "-safe", "0", "-i", str(audio_list),
        "-c", "pcm_s16le", str(full_mix),
    ], log=logs / "full_audio.log")
    print("full_mix", probe(full_mix), flush=True)

    # also place copies/links into delivery for continuity
    shutil.copy2(full_mix, DELIVERY / "full_mix.wav")
    # full_video may be huge; prefer symlink or move reference in manifest to OUT
    try:
        dest_fv = DELIVERY / "full_video.mp4"
        if dest_fv.exists():
            dest_fv.unlink()
        dest_fv.symlink_to(full_video)
    except OSError:
        # hard copy too expensive; leave in intro_v2 and note in manifest
        pass

    # clean mux: prefer video copy + aac
    print("encoding clean...", flush=True)
    run([
        str(FFMPEG), "-y", "-i", str(full_video), "-i", str(full_mix),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
        str(clean_path),
    ], log=logs / "clean_mux.log")
    clean_s = probe(clean_path)
    print("clean", clean_s, "MB", round(clean_path.stat().st_size / 1e6, 1), flush=True)

    # shift body ASS by head_audio_s
    ass = SUBS / "body.ass"
    shifted = OUT / "full_shifted.ass"
    out_lines = []
    for line in ass.read_text(encoding="utf-8").splitlines():
        if line.startswith("Dialogue:"):
            parts = line.split(",", 9)
            parts[1] = shift_ts(parts[1], head_audio_s)
            parts[2] = shift_ts(parts[2], head_audio_s)
            out_lines.append(",".join(parts))
        else:
            out_lines.append(line)
    shifted.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    # also update run/subs copy
    shutil.copy2(shifted, SUBS / "full_shifted.ass")

    work = OUT / "sub_work"
    work.mkdir(parents=True, exist_ok=True)
    (work / "full_shifted.ass").write_text(shifted.read_text(encoding="utf-8"), encoding="utf-8")
    fonts = work / "fonts"
    if not fonts.exists():
        try:
            fonts.symlink_to(FONT_DIR, target_is_directory=True)
        except OSError:
            fonts.mkdir(exist_ok=True)
            shutil.copy2(FONT_DIR / "SourceHanSansSC-Heavy.otf", fonts / "SourceHanSansSC-Heavy.otf")

    print("burning sub (long)...", flush=True)
    run([
        str(FFMPEG), "-y", "-i", str(clean_path),
        "-vf", "ass=full_shifted.ass:fontsdir=fonts",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "copy", str(sub_path),
    ], cwd=str(work), log=logs / "sub_burn.log")
    sub_s = probe(sub_path)
    print("sub", sub_s, "MB", round(sub_path.stat().st_size / 1e6, 1), flush=True)

    # QA update
    old_qa = {}
    qa_path = RUN / "FINAL_QA.json"
    if qa_path.is_file():
        old_qa = json.loads(qa_path.read_text(encoding="utf-8"))
    tl = json.loads((RUN / "timeline.json").read_text(encoding="utf-8"))
    body_s = float(tl["body_total_seconds_audio"])
    intro_only_s = head_audio_s - TITLE_DUR
    total = body_s + head_audio_s
    minute = int(math.floor(total / 60 + 0.5))
    qa = dict(old_qa) if old_qa else {}
    qa["created_at"] = now_iso()
    qa["intro_fix"] = {
        "version": "intro_v2",
        "title_main": "你是一只蟑螂",
        "title_sub": "落叶下的漫长演化",
        "intro_narration_s": intro_only_s,
        "title_card_s": TITLE_DUR,
        "head_total_s": head_audio_s,
        "center_zoom_ass": True,
        "preview": str(OUT / "preview_head24s.mp4"),
        "title_card_frame": str(OUT / "title_card_frame.jpg"),
        "backup_clean": str(bak_clean) if bak_clean else None,
        "backup_sub": str(bak_sub) if bak_sub else None,
        "body_ass_shift_s": head_audio_s,
    }
    auto = qa.get("auto_checks") or {}
    auto.update({
        "timeline_audio_s": body_s,
        "intro_audio_s": intro_only_s,
        "head_total_s": head_audio_s,
        "title_card_s": TITLE_DUR,
        "clean_path": str(clean_path),
        "clean_duration_s": clean_s,
        "clean_size_bytes": clean_path.stat().st_size,
        "sub_path": str(sub_path),
        "sub_ok": sub_path.is_file() and sub_path.stat().st_size > 1_000_000,
        "sub_size_bytes": sub_path.stat().st_size,
        "minute_resolution": {
            "body_seconds": body_s,
            "intro_seconds": intro_only_s,
            "title_card_seconds": TITLE_DUR,
            "head_total_seconds": head_audio_s,
            "minute": minute,
            "text": f"接下来的{minute}分钟，我们来讲讲蟑螂这个家族，漫长的演化史。",
            "status": "resolved_after_intro_v2",
            "measured_at": now_iso(),
            "clean_duration_s": clean_s,
        },
    })
    qa["auto_checks"] = auto
    notes = list(qa.get("notes") or [])
    notes.append("intro_v2: center zoom ASS on intro lines + 2s title card before body.")
    qa["notes"] = notes
    unfinished = [u for u in (qa.get("unfinished") or []) if "op4 intro" not in u and "theme art" not in u]
    unfinished.append("optional FunASR subtitle refine")
    unfinished.append("VSR on selected I2V for formal delivery")
    unfinished.append("full op4 intro layout polish (title card done; 四格 layout still draft)")
    qa["unfinished"] = unfinished
    atomic_json(qa_path, qa)

    atomic_json(DELIVERY / "delivery_manifest.json", {
        "clean": str(clean_path),
        "sub": str(sub_path),
        "intro_v2_preview": str(OUT / "preview_head24s.mp4"),
        "intro_with_subs": str(OUT / "intro_with_subs.mp4"),
        "title_card": str(OUT / "title_card_2s.mp4"),
        "title_card_frame": str(OUT / "title_card_frame.jpg"),
        "head_video": str(head_video),
        "body_video": str(body_video),
        "full_mix": str(DELIVERY / "full_mix.wav"),
        "full_video": str(full_video),
        "intro_audio_s": intro_only_s,
        "title_card_s": TITLE_DUR,
        "head_total_s": head_audio_s,
        "clean_duration_s": clean_s,
        "backup_clean": str(bak_clean) if bak_clean else None,
        "backup_sub": str(bak_sub) if bak_sub else None,
        "updated_at": now_iso(),
    })

    notes_md = f"""# INTRO_FIX_NOTES (intro_v2)

- 时间：{now_iso()}
- 标题主行：你是一只蟑螂
- 副行：落叶下的漫长演化
- 片头三句：画面正中字幕（Alignment=5），白字粗黑边，ASS `\\t` 从 fsc 85→110
- 三句后插入 2.0s 静音标题封面（底图 intro-art-01 略压暗）
- 片头口播时长：{intro_only_s:.6f}s；标题封面：{TITLE_DUR:.1f}s；片头段合计：{head_audio_s:.6f}s
- 正文 ASS 整体偏移：+{head_audio_s:.6f}s
- 试片：`intro_v2/preview_head24s.mp4`（约 {probe(OUT / 'preview_head24s.mp4'):.2f}s）
- 封面截图：`intro_v2/title_card_frame.jpg`
- 新成片：
  - clean: `delivery/you-are-a-cockroach_clean.mp4`（{clean_s:.3f}s）
  - sub: `delivery/you-are-a-cockroach_sub.mp4`（{sub_s:.3f}s）
- 旧成片备份：`*_pre_introfix.mp4`
- 未改正文 VO / I2V / stills；仅重做 intro 段 + 整片 concat/mux
"""
    (OUT / "INTRO_FIX_NOTES.md").write_text(notes_md, encoding="utf-8")
    (RUN / "INTRO_FIX_NOTES.md").write_text(notes_md, encoding="utf-8")

    atomic_json(OUT / "CHECKPOINT.json", {
        "stage": "done",
        "completed": ["intro_ass", "title_card", "preview_head24s", "full_concat", "clean", "sub", "qa"],
        "running": [],
        "next_action": "done",
        "updated_at": now_iso(),
        "clean": str(clean_path),
        "sub": str(sub_path),
        "clean_duration_s": clean_s,
        "sub_duration_s": sub_s,
        "head_total_s": head_audio_s,
    })
    atomic_json(RUN / "CHECKPOINT.json", {
        "stage": "qa",
        "completed": [
            "create_run", "build_timeline", "build_media_map", "prepare_shot_media",
            "assemble_chapters", "build_audio", "build_subtitles", "intro", "delivery", "qa", "intro_v2",
        ],
        "running": [],
        "next_action": "done_intro_v2",
        "blocked": "",
        "updated_at": now_iso(),
    })
    print("DONE", json.dumps({
        "clean": str(clean_path),
        "clean_s": clean_s,
        "sub": str(sub_path),
        "sub_s": sub_s,
        "head_s": head_audio_s,
    }, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    main()