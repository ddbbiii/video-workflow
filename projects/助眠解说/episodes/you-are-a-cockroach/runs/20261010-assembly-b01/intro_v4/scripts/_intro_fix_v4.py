# -*- coding: utf-8 -*-
"""Intro v4: shrink title main font so it fits; keep daytime jungle; remux delivery."""
from __future__ import annotations
import json, math, shutil, subprocess, wave
from pathlib import Path
from datetime import datetime, timezone, timedelta

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\you-are-a-cockroach")
RUN = EP / "runs" / "20261010-assembly-b01"
V3 = RUN / "intro_v3"
OUT = RUN / "intro_v4"
DELIVERY = RUN / "delivery"
SUBS = RUN / "subs"
FFMPEG = Path(r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe")
FFPROBE = FFMPEG.with_name("ffprobe.exe")
FONT_DIR = Path(r"E:\program\1project\video\assets\助眠解说\subtitles\style-r4\fonts")
STAGE = Path(r"C:\Users\10060\agent-tools")
SR = 48000
FPS = 30
TZ = timezone(timedelta(hours=8))
TITLE_MAIN = "你是一只蟑螂"
TITLE_SUB = "落叶下的漫长演化"
TITLE_DUR = 2.0
# v3 actual was 500/168 (overflow). Target ~22-24% screen height.
MAIN_FS = 380
SUB_FS = 148
INTRO_FS = 96

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
        log.write_text((r.stdout or "") + "\n" + (r.stderr or ""), encoding="utf-8")
    if r.returncode != 0:
        print((r.stderr or r.stdout or "")[-2000:])
        raise SystemExit(f"cmd failed rc={r.returncode}")
    return r

def backup(path: Path, tag: str = "_pre_intro_v4") -> Path | None:
    if not path.is_file() or path.stat().st_size < 1000:
        return None
    bak = path.with_name(path.stem + tag + path.suffix)
    if bak.exists():
        bak.unlink()
    shutil.copy2(path, bak)
    print("backup", bak, flush=True)
    return bak

def write_title_ass(path: Path):
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TitleMain,Source Han Sans SC Heavy,{MAIN_FS},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,4,0,1,12,0,5,64,64,0,1
Style: TitleSub,Source Han Sans SC Heavy,{SUB_FS},&H00F5F5F5,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,6,0,1,7,0,5,64,64,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = [
        f"Dialogue: 0,0:00:00.00,0:00:02.00,TitleMain,,0,0,0,,{{\\pos(960,450)}}{TITLE_MAIN}",
        f"Dialogue: 0,0:00:00.00,0:00:02.00,TitleSub,,0,0,0,,{{\\pos(960,720)}}{TITLE_SUB}",
    ]
    path.write_text(header + "\n".join(ev) + "\n", encoding="utf-8")

def ensure_fonts_link(work: Path):
    fonts = work / "fonts"
    if fonts.exists() or fonts.is_symlink():
        return
    try:
        fonts.symlink_to(FONT_DIR, target_is_directory=True)
    except OSError:
        fonts.mkdir(parents=True, exist_ok=True)
        src = FONT_DIR / "SourceHanSansSC-Heavy.otf"
        dst = fonts / "SourceHanSansSC-Heavy.otf"
        if not dst.exists():
            shutil.copy2(src, dst)

def measure_white_band_height(jpg: Path) -> float | None:
    try:
        from PIL import Image
        import numpy as np
        im = Image.open(jpg).convert("RGB")
        arr = np.asarray(im)
        # bright near-white text
        mask = (arr[:, :, 0] > 220) & (arr[:, :, 1] > 220) & (arr[:, :, 2] > 220)
        rows = np.where(mask.any(axis=1))[0]
        if len(rows) == 0:
            return None
        # take the upper cluster (main title) — rows above mid
        mid = arr.shape[0] // 2
        upper = rows[rows < mid]
        if len(upper) < 5:
            upper = rows
        h = int(upper.max() - upper.min() + 1)
        return round(100.0 * h / arr.shape[0], 1)
    except Exception as e:
        print("measure skip:", e, flush=True)
        return None

def shift_ts(ts: str, offset: float) -> str:
    parts = ts.strip().split(":")
    if len(parts) != 3:
        return ts
    h = int(parts[0]); m = int(parts[1])
    sec_cs = parts[2].split(".")
    s = int(sec_cs[0]); cs = int(sec_cs[1]) if len(sec_cs) > 1 else 0
    total = h * 3600 + m * 60 + s + cs / 100.0 + offset
    if total < 0:
        total = 0
    cs_i = int(round(total * 100))
    h, cs_i = divmod(cs_i, 360000)
    m, cs_i = divmod(cs_i, 6000)
    s, cs_i = divmod(cs_i, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs_i:02d}"

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    logs = OUT / "logs"; logs.mkdir(exist_ok=True)
    work = OUT / "work"; work.mkdir(exist_ok=True)
    scripts = OUT / "scripts"; scripts.mkdir(exist_ok=True)
    ensure_fonts_link(work)

    # copy this script into run for provenance
    self_path = Path(__file__).resolve()
    try:
        shutil.copy2(self_path, scripts / "_intro_fix_v4.py")
    except Exception:
        pass

    still = OUT / "title_bg_day_jungle.jpg"
    if not still.is_file():
        shutil.copy2(V3 / "title_bg_day_jungle.jpg", still)

    intro_with_subs = OUT / "intro_with_subs.mp4"
    if not intro_with_subs.is_file():
        shutil.copy2(V3 / "intro_with_subs.mp4", intro_with_subs)
        shutil.copy2(V3 / "intro.ass", OUT / "intro.ass")

    atomic_json(OUT / "CHECKPOINT.json", {
        "stage": "title_card",
        "completed": [],
        "running": ["title_card", "preview"],
        "next_action": "render title then remux",
        "main_fontsize": MAIN_FS,
        "sub_fontsize": SUB_FS,
        "updated_at": now_iso(),
    })

    title_ass = OUT / "title.ass"
    write_title_ass(title_ass)
    (work / "title.ass").write_text(title_ass.read_text(encoding="utf-8"), encoding="utf-8")

    title_base = OUT / "title_base.mp4"
    run([
        str(FFMPEG), "-y", "-loop", "1", "-i", str(still),
        "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,eq=brightness=0.04:saturation=1.08:contrast=1.02",
        "-t", str(TITLE_DUR), "-r", str(FPS),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-an", str(title_base),
    ], log=logs / "title_base.log")

    title_card = OUT / "title_card_2s.mp4"
    run([
        str(FFMPEG), "-y", "-i", str(title_base),
        "-vf", "ass=title.ass:fontsdir=fonts",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-an", str(title_card),
    ], cwd=str(work), log=logs / "title_burn.log")
    print("title_card", probe(title_card), flush=True)

    shot = OUT / "title_card_frame.jpg"
    run([
        str(FFMPEG), "-y", "-ss", "1.0", "-i", str(title_card),
        "-frames:v", "1", "-q:v", "2", str(shot),
    ], log=logs / "title_shot.log")
    main_h_pct = measure_white_band_height(shot)
    print("main_height_pct_measured", main_h_pct, flush=True)

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
    print("head_video", probe(head_video), flush=True)

    # reuse v3 head audio (same timing)
    head_audio = OUT / "head_audio.wav"
    if not head_audio.is_file():
        shutil.copy2(V3 / "head_audio.wav", head_audio)
        shutil.copy2(V3 / "silence_2s.wav", OUT / "silence_2s.wav")
    head_audio_s = probe(head_audio)

    preview = OUT / "preview_head24s.mp4"
    run([
        str(FFMPEG), "-y", "-i", str(head_video), "-i", str(head_audio),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
        str(preview),
    ], log=logs / "preview_mux.log")
    print("PREVIEW", preview, probe(preview), flush=True)

    # stage preview assets early so parent can show even while remux runs
    shutil.copy2(shot, STAGE / "title_card_frame_intro_v4.jpg")
    shutil.copy2(preview, STAGE / "preview_head24s_intro_v4.mp4")
    print("staged preview assets", flush=True)

    meta = {
        "created_at": now_iso(),
        "version": "intro_v4",
        "intro_audio_s": head_audio_s - TITLE_DUR,
        "title_card_s": TITLE_DUR,
        "head_video_s": probe(head_video),
        "head_audio_s": head_audio_s,
        "preview_s": probe(preview),
        "title_main": TITLE_MAIN,
        "title_sub": TITLE_SUB,
        "main_fontsize": MAIN_FS,
        "sub_fontsize": SUB_FS,
        "intro_fontsize": INTRO_FS,
        "still": str(still),
        "title_card_frame": str(shot),
        "preview": str(preview),
        "note": "daytime jungle retained; main title shrunk from v3 500→380 to fit margins",
        "main_height_pct_measured": main_h_pct,
        "prev_main_fontsize": 500,
        "updated_at": now_iso(),
    }
    atomic_json(OUT / "preview_meta.json", meta)
    atomic_json(OUT / "CHECKPOINT.json", {
        "stage": "full_remux",
        "completed": ["title_card", "preview_head24s", "stage_preview"],
        "running": ["full_concat", "clean", "sub"],
        "next_action": "mux clean then burn sub",
        "main_fontsize": MAIN_FS,
        "sub_fontsize": SUB_FS,
        "main_height_pct_measured": main_h_pct,
        "updated_at": now_iso(),
    })

    body_video = DELIVERY / "body_video.mp4"
    body_mix = RUN / "audio" / "mix-master.wav"
    for p in (head_video, head_audio, body_video, body_mix):
        assert p.is_file(), p

    clean_path = DELIVERY / "you-are-a-cockroach_clean.mp4"
    sub_path = DELIVERY / "you-are-a-cockroach_sub.mp4"
    bak_clean = backup(clean_path)
    bak_sub = backup(sub_path)
    backup(DELIVERY / "full_mix.wav")

    full_list = OUT / "full_concat.txt"
    full_list.write_text(
        f"file '{head_video.as_posix()}'\nfile '{body_video.as_posix()}'\n",
        encoding="utf-8",
    )
    full_video = OUT / "full_video.mp4"
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

    # audio timing unchanged vs v3 — reuse if identical length, else rebuild
    full_mix = OUT / "full_mix.wav"
    v3_mix = V3 / "full_mix.wav"
    if v3_mix.is_file() and abs(probe(v3_mix) - (head_audio_s + probe(body_mix))) < 0.05:
        shutil.copy2(v3_mix, full_mix)
        print("reused v3 full_mix", flush=True)
    else:
        audio_list = OUT / "full_audio_concat.txt"
        audio_list.write_text(
            f"file '{head_audio.as_posix()}'\nfile '{body_mix.as_posix()}'\n",
            encoding="utf-8",
        )
        run([
            str(FFMPEG), "-y", "-f", "concat", "-safe", "0", "-i", str(audio_list),
            "-c", "pcm_s16le", str(full_mix),
        ], log=logs / "full_audio.log")
    shutil.copy2(full_mix, DELIVERY / "full_mix.wav")
    print("full_mix", probe(full_mix), flush=True)

    print("encoding clean...", flush=True)
    run([
        str(FFMPEG), "-y", "-i", str(full_video), "-i", str(full_mix),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
        str(clean_path),
    ], log=logs / "clean_mux.log")
    clean_s = probe(clean_path)
    print("clean", clean_s, "MB", round(clean_path.stat().st_size / 1e6, 1), flush=True)

    # ASS shift same as v3 — reuse shifted file if present
    shifted = OUT / "full_shifted.ass"
    v3_shifted = V3 / "full_shifted.ass"
    if v3_shifted.is_file():
        shutil.copy2(v3_shifted, shifted)
    else:
        ass = SUBS / "body.ass"
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
    shutil.copy2(shifted, SUBS / "full_shifted.ass")

    sub_work = OUT / "sub_work"
    sub_work.mkdir(parents=True, exist_ok=True)
    (sub_work / "full_shifted.ass").write_text(shifted.read_text(encoding="utf-8"), encoding="utf-8")
    ensure_fonts_link(sub_work)

    print("burning sub (long)...", flush=True)
    run([
        str(FFMPEG), "-y", "-i", str(clean_path),
        "-vf", "ass=full_shifted.ass:fontsdir=fonts",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "copy", str(sub_path),
    ], cwd=str(sub_work), log=logs / "sub_burn.log")
    sub_s = probe(sub_path)
    print("sub", sub_s, "MB", round(sub_path.stat().st_size / 1e6, 1), flush=True)

    intro_only_s = head_audio_s - TITLE_DUR
    old_qa = {}
    qa_path = RUN / "FINAL_QA.json"
    if qa_path.is_file():
        old_qa = json.loads(qa_path.read_text(encoding="utf-8"))
    tl = json.loads((RUN / "timeline.json").read_text(encoding="utf-8"))
    body_s = float(tl["body_total_seconds_audio"])
    total = body_s + head_audio_s
    minute = int(math.floor(total / 60 + 0.5))
    qa = dict(old_qa) if old_qa else {}
    qa["created_at"] = now_iso()
    qa["intro_fix"] = {
        "version": "intro_v4",
        "title_main": TITLE_MAIN,
        "title_sub": TITLE_SUB,
        "main_fontsize_ass": MAIN_FS,
        "sub_fontsize_ass": SUB_FS,
        "intro_fontsize_ass": INTRO_FS,
        "main_height_pct_measured": main_h_pct,
        "prev_main_fontsize_ass": 500,
        "still": str(still),
        "still_note": "daytime jungle retained from intro_v3",
        "intro_narration_s": intro_only_s,
        "title_card_s": TITLE_DUR,
        "head_total_s": head_audio_s,
        "center_zoom_ass": True,
        "preview": str(preview),
        "title_card_frame": str(shot),
        "backup_clean": str(bak_clean) if bak_clean else None,
        "backup_sub": str(bak_sub) if bak_sub else None,
        "body_ass_shift_s": head_audio_s,
        "staging": {
            "title_card_frame": str(STAGE / "title_card_frame_intro_v4.jpg"),
            "preview": str(STAGE / "preview_head24s_intro_v4.mp4"),
        },
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
            "status": "resolved_after_intro_v4",
            "measured_at": now_iso(),
            "clean_duration_s": clean_s,
        },
    })
    qa["auto_checks"] = auto
    notes = list(qa.get("notes") or [])
    notes.append(f"intro_v4: shrink main title ASS {500}→{MAIN_FS} (sub {SUB_FS}); daytime jungle kept; fit left/right margins.")
    qa["notes"] = notes
    unfinished = [u for u in (qa.get("unfinished") or []) if "op4 intro" not in u and "theme art" not in u]
    unfinished.append("optional FunASR subtitle refine")
    unfinished.append("VSR on selected I2V for formal delivery")
    unfinished.append("full op4 intro layout polish (title card v4 done; 四格 layout still draft)")
    qa["unfinished"] = unfinished
    atomic_json(qa_path, qa)

    atomic_json(DELIVERY / "delivery_manifest.json", {
        "clean": str(clean_path),
        "sub": str(sub_path),
        "intro_v4_preview": str(preview),
        "intro_with_subs": str(intro_with_subs),
        "title_card": str(title_card),
        "title_card_frame": str(shot),
        "title_bg": str(still),
        "head_video": str(head_video),
        "body_video": str(body_video),
        "full_mix": str(DELIVERY / "full_mix.wav"),
        "full_video": str(full_video),
        "intro_audio_s": intro_only_s,
        "title_card_s": TITLE_DUR,
        "head_total_s": head_audio_s,
        "main_fontsize_ass": MAIN_FS,
        "sub_fontsize_ass": SUB_FS,
        "main_height_pct_measured": main_h_pct,
        "clean_duration_s": clean_s,
        "backup_clean": str(bak_clean) if bak_clean else None,
        "backup_sub": str(bak_sub) if bak_sub else None,
        "updated_at": now_iso(),
        "version": "intro_v4",
    })

    notes_md = f"""# INTRO_FIX_NOTES (intro_v4)

- 时间：{now_iso()}
- 标题主行：你是一只蟑螂（ASS Fontsize={MAIN_FS}，v3 为 500 溢出；本版缩小以留左右安全边）
- 副行：落叶下的漫长演化（ASS Fontsize={SUB_FS}）
- 实测主标题白字带高占比：{main_h_pct}%（目标约 22–24%）
- 封面气质：白天丛林（沿用 intro_v3 底图），未改色
- 片头三句：沿用 v3 正中放大字幕（Fontsize={INTRO_FS}）
- 片头口播：{intro_only_s:.6f}s；标题封面 2.0s；合计 {head_audio_s:.6f}s
- 正文 ASS 偏移：+{head_audio_s:.6f}s
- 试片：`intro_v4/preview_head24s.mp4`
- 封面截图：`intro_v4/title_card_frame.jpg`
- 新成片：
  - clean: `delivery/you-are-a-cockroach_clean.mp4`（{clean_s:.3f}s）
  - sub: `delivery/you-are-a-cockroach_sub.mp4`（{sub_s:.3f}s）
- 旧成片备份：`*_pre_intro_v4.mp4`
- staging：`C:\\Users\\10060\\agent-tools\\title_card_frame_intro_v4.jpg` / `preview_head24s_intro_v4.mp4`
"""
    (OUT / "INTRO_FIX_NOTES.md").write_text(notes_md, encoding="utf-8")
    (RUN / "INTRO_FIX_NOTES.md").write_text(notes_md, encoding="utf-8")

    atomic_json(OUT / "CHECKPOINT.json", {
        "stage": "done",
        "completed": ["title_card", "preview_head24s", "stage_preview", "full_concat", "clean", "sub", "qa"],
        "running": [],
        "next_action": "done",
        "updated_at": now_iso(),
        "clean": str(clean_path),
        "sub": str(sub_path),
        "clean_duration_s": clean_s,
        "sub_duration_s": sub_s,
        "head_total_s": head_audio_s,
        "main_fontsize": MAIN_FS,
        "sub_fontsize": SUB_FS,
        "main_height_pct_measured": main_h_pct,
    })
    atomic_json(RUN / "CHECKPOINT.json", {
        "stage": "qa",
        "completed": [
            "create_run", "build_timeline", "build_media_map", "prepare_shot_media",
            "assemble_chapters", "build_audio", "build_subtitles", "intro", "delivery", "qa",
            "intro_v2", "intro_v3", "intro_v4",
        ],
        "running": [],
        "next_action": "done_intro_v4",
        "blocked": "",
        "updated_at": now_iso(),
    })
    print("DONE", json.dumps({
        "clean": str(clean_path),
        "clean_s": clean_s,
        "sub": str(sub_path),
        "sub_s": sub_s,
        "head_s": head_audio_s,
        "main_fs": MAIN_FS,
        "sub_fs": SUB_FS,
        "main_h_pct": main_h_pct,
        "preview": str(preview),
        "frame": str(shot),
        "stage_frame": str(STAGE / "title_card_frame_intro_v4.jpg"),
        "stage_preview": str(STAGE / "preview_head24s_intro_v4.mp4"),
    }, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    main()