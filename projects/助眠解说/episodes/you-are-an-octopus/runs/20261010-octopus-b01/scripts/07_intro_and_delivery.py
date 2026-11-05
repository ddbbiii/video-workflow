# -*- coding: utf-8 -*-
"""Resolve intro minute, build intro video (affine), concat body+intro, write clean/sub delivery + FINAL_QA."""
from __future__ import annotations
import json, math, subprocess, sys, wave
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_common import (
    EP, RUN, FFMPEG, FFPROBE, PYTHON, CAMERA_MOTION, FPS, SR,
    INTRO_HEAD, INTRO_BETWEEN, INTRO_TAIL, STILLS, FONT_DIR, VO_DIR,
    load_json, atomic_json, update_checkpoint, log_stage, now_iso, run_cmd, BGM_GAIN,
)

AUDIO = RUN / "audio"
CHAPTERS = RUN / "chapters"
DELIVERY = RUN / "delivery"
SUBS = RUN / "subs"
MEDIA = RUN / "media"
INTRO_DIR = RUN / "intro"
INTRO_DIR.mkdir(parents=True, exist_ok=True)
DELIVERY.mkdir(parents=True, exist_ok=True)

def ensure_intro_still(src: Path, dst: Path, tw=1536, th=864) -> Path:
    """Center-crop/resize to exact 16:9 so affine view validation passes."""
    from PIL import Image, ImageOps
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_file() and dst.stat().st_mtime >= src.stat().st_mtime:
        return dst
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        w, h = im.size
        ar, tar = w / h, tw / th
        if ar > tar:
            nw = int(h * tar); x = (w - nw) // 2; im = im.crop((x, 0, x + nw, h))
        else:
            nh = int(w / tar); y = (h - nh) // 2; im = im.crop((0, y, w, y + nh))
        im = im.resize((tw, th), Image.Resampling.LANCZOS)
        im.save(dst, quality=95)
    return dst



def probe(path: Path) -> float:
    r = subprocess.run([str(FFPROBE), "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def write_silence(path: Path, seconds: float):
    samples = int(round(seconds * SR))
    with wave.open(str(path), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b"\x00\x00" * samples)


def resolve_minute(body_s: float, intro_est: float = 20.0) -> dict:
    """Use existing minute resolution; NEVER call prepare_handoff (it overwrites locked plans)."""
    res_path = EP / "audio" / "intro-minute-resolution.json"
    if res_path.is_file():
        data = load_json(res_path)
        log_stage("07_intro", f"reuse intro-minute-resolution minute={data.get('minute')}")
        return data
    minute = int(math.floor((body_s + intro_est) / 60 + 0.5))
    text = f"接下来的{minute}分钟，我们来讲讲章鱼漫长的进化史。"
    data = {"body_seconds": body_s, "intro_seconds": intro_est, "minute": minute,
            "resolved_text": text, "status": "local_fallback_no_prepare_handoff"}
    atomic_json(res_path, data)
    log_stage("07_intro", f"wrote local minute resolution minute={minute}")
    return data


def try_generate_intro_p03(resolved_text: str) -> Path | None:
    """If GPU lock free and TTS available, generate; else return None and use placeholder note."""
    job = EP / "audio" / "jobs" / "intro-minute-resolved.json"
    if not job.is_file():
        return None
    # Check for existing processed file
    out_raw = EP / "audio" / "vo-raw" / "seed7-final" / "intro" / "intro-p003-u01.wav"
    out_proc = VO_DIR / "intro" / "intro-p003-u01.wav"
    if out_proc.is_file():
        return out_proc
    # Do not start TTS here if lock busy; mark pending
    lock = Path(r"E:\program\1project\video\shared\work\cache\gpu.lock")
    if lock.is_file():
        log_stage("07_intro", f"gpu.lock present; skip TTS intro-p003: {lock.read_text(encoding='utf-8', errors='ignore')[:200]}")
        return None
    log_stage("07_intro", "intro-p003 not generated yet; delivery will include body-only note or skip intro audio")
    return None


def build_intro_visual(intro_audio_s: float) -> Path:
    """Simple intro: sequential P1 over 8 intro stills covering intro_audio_s (draft, not full op4 layout)."""
    fixed_dir = INTRO_DIR / "stills_fixed"
    stills = []
    for i in range(1, 9):
        raw = STILLS / f"intro-art-{i:02d}.jpg"
        if not raw.is_file():
            raise FileNotFoundError(raw)
        stills.append(ensure_intro_still(raw, fixed_dir / f"intro-art-{i:02d}.jpg"))
    # allocate equal time, snap frames
    total_frames = max(2 * len(stills), int(round(intro_audio_s * FPS)))
    base = total_frames // len(stills)
    rem = total_frames - base * len(stills)
    specs = []
    for i, src in enumerate(stills):
        frames = base + (1 if i < rem else 0)
        dur = frames / FPS
        # alternate push/pull like intro-node guidance (~3%)
        if i % 2 == 0:
            start_view, end_view = [0.06, 0.06, 0.88, 0.88], [0.03, 0.03, 0.94, 0.94]
        else:
            start_view, end_view = [0.03, 0.03, 0.94, 0.94], [0.06, 0.06, 0.88, 0.88]
        span = (frames - 1) / FPS
        curve = {"type": "smoothstep"} if span < 0.4 else {"type": "ramped_linear", "ramp_s": min(0.5, span / 2 - 0.01)}
        specs.append({
            "id": f"intro-art-{i+1:02d}",
            "source": str(src.resolve()),
            "duration_s": dur,
            "start_view": start_view,
            "end_view": end_view,
            "curve": curve,
        })
    plan = INTRO_DIR / "intro_affine_plan.json"
    atomic_json(plan, {"schema_version": 1, "backend": "affine", "output": {"width": 1920, "height": 1080, "fps": FPS},
                       "transition_s": 0, "shots": specs})
    out_dir = INTRO_DIR / "affine"
    out_dir.mkdir(parents=True, exist_ok=True)
    rc = run_cmd([str(PYTHON), str(CAMERA_MOTION), str(plan), "--out", str(out_dir)], RUN / "logs" / "07_intro_affine.log")
    if rc != 0:
        raise SystemExit("intro affine failed")
    # concat
    lst = INTRO_DIR / "intro_concat.txt"
    lst.write_text("".join(f"file '{(out_dir / (s['id'] + '.mp4')).as_posix()}'\n" for s in specs), encoding="utf-8")
    video = INTRO_DIR / "intro_video.mp4"
    subprocess.run([str(FFMPEG), "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(video)],
                   check=True, capture_output=True)
    return video


def build_intro_audio() -> tuple[Path, float, dict]:
    """Build intro audio from available processed wavs; placeholder silence for missing p03."""
    p01 = VO_DIR / "intro" / "intro-p001-u01.wav"
    p02 = VO_DIR / "intro" / "intro-p002-u01.wav"
    p03 = VO_DIR / "intro" / "intro-p003-u01.wav"
    status = {"p01": p01.is_file(), "p02": p02.is_file(), "p03": p03.is_file()}
    parts = INTRO_DIR / "audio_parts"
    parts.mkdir(parents=True, exist_ok=True)
    lines = []
    write_silence(parts / "head.wav", INTRO_HEAD)
    lines.append(f"file '{(parts / 'head.wav').as_posix()}'")
    lines.append(f"file '{p01.as_posix()}'")
    write_silence(parts / "g1.wav", INTRO_BETWEEN)
    lines.append(f"file '{(parts / 'g1.wav').as_posix()}'")
    lines.append(f"file '{p02.as_posix()}'")
    write_silence(parts / "g2.wav", INTRO_BETWEEN)
    lines.append(f"file '{(parts / 'g2.wav').as_posix()}'")
    if p03.is_file():
        lines.append(f"file '{p03.as_posix()}'")
    else:
        # placeholder ~4s for unresolved minute line so visual still has slot
        write_silence(parts / "p03_placeholder.wav", 4.0)
        lines.append(f"file '{(parts / 'p03_placeholder.wav').as_posix()}'")
        status["p03_placeholder"] = True
    write_silence(parts / "tail.wav", INTRO_TAIL)
    lines.append(f"file '{(parts / 'tail.wav').as_posix()}'")
    lst = INTRO_DIR / "intro_audio_concat.txt"
    lst.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = INTRO_DIR / "intro_narration.wav"
    subprocess.run([str(FFMPEG), "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c:a", "pcm_s16le", "-ar", str(SR), "-ac", "1", str(out)], check=True, capture_output=True)
    return out, probe(out), status


def concat_body_video() -> Path:
    idx = load_json(RUN / "chapters_index.json")
    order = [c["section"] for c in idx["chapters"]]
    lst = DELIVERY / "body_concat.txt"
    paths = []
    for sec in order:
        p = CHAPTERS / f"{sec}_video.mp4"
        if not p.is_file():
            raise FileNotFoundError(p)
        paths.append(p)
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in paths), encoding="utf-8")
    body = DELIVERY / "body_video.mp4"
    subprocess.run([str(FFMPEG), "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", str(body)], check=True, capture_output=True)
    return body


def main():
    update_checkpoint(stage="intro",
                      completed=["create_run", "build_timeline", "build_media_map", "prepare_shot_media", "assemble_chapters", "build_audio", "build_subtitles"],
                      running=["intro_and_delivery"], next_action="intro resolve + clean/sub")
    tl = load_json(RUN / "timeline.json")
    body_s = float(tl["body_total_seconds_audio"])
    resolved = resolve_minute(body_s, intro_est=20.0)
    try_generate_intro_p03(resolved.get("text", ""))

    intro_audio, intro_s, intro_status = build_intro_audio()
    intro_video = build_intro_visual(intro_s)
    intro_draft = INTRO_DIR / "intro_draft.mp4"
    subprocess.run([str(FFMPEG), "-y", "-i", str(intro_video), "-i", str(intro_audio),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(intro_draft)],
                   check=True, capture_output=True)

    body_video = concat_body_video()
    # full video = intro + body
    full_list = DELIVERY / "full_concat.txt"
    full_list.write_text(f"file '{intro_video.as_posix()}'\nfile '{body_video.as_posix()}'\n", encoding="utf-8")
    full_video = DELIVERY / "full_video.mp4"
    subprocess.run([str(FFMPEG), "-y", "-f", "concat", "-safe", "0", "-i", str(full_list),
                    "-c", "copy", str(full_video)], check=True, capture_output=True)

    # full narration: intro + body narration-dry (no BGM on intro)
    # Build full mix: intro narr (mono->stereo) then body mix-master
    body_mix = AUDIO / "mix-master.wav"
    # pad intro audio to stereo silence BGM
    intro_stereo = INTRO_DIR / "intro_stereo.wav"
    subprocess.run([str(FFMPEG), "-y", "-i", str(intro_audio),
                    "-af", f"aformat=sample_rates={SR}:channel_layouts=mono,pan=stereo|c0=c0|c1=c0",
                    "-c:a", "pcm_s16le", str(intro_stereo)], check=True, capture_output=True)
    full_audio_list = DELIVERY / "full_audio_concat.txt"
    full_audio_list.write_text(f"file '{intro_stereo.as_posix()}'\nfile '{body_mix.as_posix()}'\n", encoding="utf-8")
    full_audio = DELIVERY / "full_mix.wav"
    subprocess.run([str(FFMPEG), "-y", "-f", "concat", "-safe", "0", "-i", str(full_audio_list),
                    "-c", "pcm_s16le", str(full_audio)], check=True, capture_output=True)

    clean = DELIVERY / "你是一只章鱼_1080p_clean.mp4"
    subprocess.run([str(FFMPEG), "-y", "-i", str(full_video), "-i", str(full_audio),
                    "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", str(clean)], check=True, capture_output=True)

    # burn subs for body only: shift ASS by intro_s for full timeline
    # For draft: burn body.ass onto clean by re-filtering with Delay
    ass = SUBS / "body.ass"
    # create shifted ass
    shifted = SUBS / "full_shifted.ass"
    lines = ass.read_text(encoding="utf-8").splitlines()
    out_lines = []
    def shift_ts(ts: str, off: float) -> str:
        # h:mm:ss.cs
        h, m, rest = ts.split(":")
        s, cs = rest.split(".")
        total = int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100.0 + off
        if total < 0: total = 0
        cs2 = int(round(total * 100))
        h, cs2 = divmod(cs2, 360000)
        m, cs2 = divmod(cs2, 6000)
        s, cs2 = divmod(cs2, 100)
        return f"{h}:{m:02d}:{s:02d}.{cs2:02d}"
    for line in lines:
        if line.startswith("Dialogue:"):
            parts = line.split(",", 9)
            # Dialogue: 0,start,end,Style,...
            parts[1] = shift_ts(parts[1], intro_s)
            parts[2] = shift_ts(parts[2], intro_s)
            out_lines.append(",".join(parts))
        else:
            out_lines.append(line)
    shifted.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    sub = DELIVERY / "你是一只章鱼_1080p_sub.mp4"
    # Windows: cwd to subs dir, relative paths for ass + fontsdir
    # copy ass to delivery work
    work = DELIVERY / "sub_work"
    work.mkdir(parents=True, exist_ok=True)
    ass_rel = work / "full_shifted.ass"
    ass_rel.write_text(shifted.read_text(encoding="utf-8"), encoding="utf-8")
    # fontsdir relative from work
    fonts_link = work / "fonts"
    if not fonts_link.exists():
        try:
            fonts_link.symlink_to(FONT_DIR, target_is_directory=True)
        except Exception:
            # copy not needed; pass absolute with escaped path carefully
            pass
    vf = f"ass=full_shifted.ass:fontsdir=fonts"
    # Prefer fontsdir absolute via ffmpeg if symlink fails
    if not (work / "fonts").exists():
        # use subtitles filter with fontsdir absolute - escape for windows
        font_esc = str(FONT_DIR).replace("\\", "/").replace(":", "\\:")
        ass_esc = str(ass_rel).replace("\\", "/").replace(":", "\\:")
        vf = f"ass='{ass_esc}':fontsdir='{font_esc}'"
        cmd = [str(FFMPEG), "-y", "-i", str(clean), "-vf", vf,
               "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
               "-c:a", "copy", str(sub)]
        r = subprocess.run(cmd, capture_output=True, text=True)
    else:
        cmd = [str(FFMPEG), "-y", "-i", str(clean), "-vf", vf,
               "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
               "-c:a", "copy", str(sub)]
        r = subprocess.run(cmd, cwd=str(work), capture_output=True, text=True)
    if r.returncode != 0:
        log_stage("07_intro", f"sub burn failed: {r.stderr[-500:]}")
        # still keep clean
        sub = None
    else:
        log_stage("07_intro", f"sub ok {sub}")

    mm = load_json(RUN / "media-map.json")
    pending = [s["shot_id"] for s in mm["shots"] if s.get("pending_review")]
    fallbacks = [s for s in mm["shots"] if s.get("class_change_reason")]
    gen_motion = sum(float(s.get("generated_motion_seconds") or 0) for s in mm["shots"])
    total_vid = float(tl["body_total_seconds_video"])
    i2v_used = sum(1 for s in mm["shots"] if s.get("combo") in ("V1", "V3"))
    qa = {
        "created_at": now_iso(),
        "auto_checks": {
            "timeline_audio_s": body_s,
            "timeline_video_s": total_vid,
            "intro_audio_s": intro_s,
            "intro_status": intro_status,
            "clean_path": str(clean),
            "clean_duration_s": probe(clean) if clean.is_file() else None,
            "sub_path": str(sub) if sub else None,
            "sub_ok": sub is not None and Path(sub).is_file(),
            "bgm_gain": BGM_GAIN,
            "minute_resolution": resolved,
        },
        "pending_review": pending,
        "pending_review_count": len(pending),
        "fallbacks": [{"shot_id": s["shot_id"], "reason": s.get("class_change_reason"), "combo": s.get("combo")} for s in fallbacks],
        "native_i2v_shots": i2v_used,
        "native_generated_motion_seconds": gen_motion,
        "native_motion_ratio_of_body": gen_motion / total_vid if total_vid else 0,
        "combo_stats": mm.get("stats"),
        "notes": [
            "Draft uses Lanczos I2V; VSR not applied (formal HD pending).",
            "Intro uses sequential affine over 8 stills (simplified vs full op4 四格 layout).",
            "intro-p003 may be placeholder silence until TTS resolve completes.",
            "visual_qa pending retained; not marked passed.",
        ],
        "unfinished": [],
    }
    if not intro_status.get("p03"):
        qa["unfinished"].append("intro-p003 TTS + re-process + re-resolve minute after actual intro measure")
    qa["unfinished"].append("optional FunASR subtitle refine")
    qa["unfinished"].append("VSR on selected I2V for formal delivery")
    qa["unfinished"].append("full op4 intro layout polish + theme art text layer")
    atomic_json(RUN / "FINAL_QA.json", qa)
    atomic_json(DELIVERY / "delivery_manifest.json", {
        "clean": str(clean),
        "sub": str(sub) if sub else None,
        "intro_draft": str(intro_draft),
        "body_video": str(body_video),
        "full_mix": str(full_audio),
    })
    update_checkpoint(stage="qa",
                      completed=["create_run", "build_timeline", "build_media_map", "prepare_shot_media",
                                 "assemble_chapters", "build_audio", "build_subtitles", "intro", "delivery", "qa"],
                      running=[], next_action="done_draft")
    log_stage("07_intro", f"FINAL_QA written; clean={clean}")
    print("OK delivery", json.dumps(qa["auto_checks"], ensure_ascii=False))

if __name__ == "__main__":
    main()