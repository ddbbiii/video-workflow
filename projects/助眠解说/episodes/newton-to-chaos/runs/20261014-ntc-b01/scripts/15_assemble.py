# -*- coding: utf-8 -*-
"""最终拼装（delivery/final-delivery.md）。
逐镜：affine/sim/I2V mp4 → 按 timeline 目标时长 trim/loop → 章节视频（无声）
→ 正文视频 → 片头视频 + 正文视频 = clean.mp4（无音轨）
旁白：intro.wav + body_narration.wav = newton-to-chaos_narration.wav
输出 video/final/{newton-to-chaos_clean.mp4, newton-to-chaos_narration.wav}"""
from __future__ import annotations
import json, subprocess, math
from pathlib import Path

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\newton-to-chaos")
RUN = EP / "runs" / "20261014-ntc-b01"
AFFINE = RUN / "media" / "affine"
SIMS = EP / "image" / "sims"
I2V = RUN / "media" / "i2v"
SHOT_VID = RUN / "media" / "shot"      # per-shot adjusted mp4
CHAP_VID = RUN / "chapters"
INTRO_VID = RUN / "intro" / "batch-20261018-short" / "clean-intro.mp4"
BODY_AUDIO = CHAP_VID / "body_narration.wav"
INTRO_AUDIO = CHAP_VID / "intro.wav"
FINAL = EP / "video" / "final"
FFMPEG = r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"
FFPROBE = r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffprobe.exe"
FPS = 30
BODY_SECTIONS = ["lead","ch01","ch02","ch03","ch04","ch05","ch06","ch07","ch08"]

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "")[-600:])
    return r

def probe_dur(path):
    r = subprocess.run([FFPROBE,"-v","error","-show_entries","format=duration",
                        "-of","csv=p=0",str(path)], capture_output=True, text=True)
    return float(r.stdout.strip())

def find_source(shot):
    sid = shot["id"]
    cls = shot.get("shot_class")
    if cls == "controlled_simulation":
        p = SIMS / f"{sid}.mp4"
    elif cls == "image_to_video":
        p = I2V / f"{sid}.mp4"
        if not p.exists(): p = AFFINE / f"{sid}.mp4"  # I2V 缺失退回 affine
    else:
        p = AFFINE / f"{sid}.mp4"
    return p if p.exists() else None

def adjust_duration(src, target, out):
    """把 src mp4 调整到 target 秒：长则截断，短则末帧冻结补足。统一 1920x1080@30fps 无音。"""
    sdur = probe_dur(src)
    if sdur >= target - 0.01:
        # trim + scale
        cmd=[FFMPEG,"-y","-i",str(src),"-t",f"{target:.3f}","-an",
             "-vf","scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30",
             "-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p",str(out)]
    else:
        # loop? no — freeze last frame to fill: use tpad
        pad = target - sdur
        cmd=[FFMPEG,"-y","-i",str(src),"-t",f"{target:.3f}","-an",
             "-vf",f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,tpad=stop_mode=clone:stop_duration={pad:.3f}",
             "-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p",str(out)]
    run(cmd)

def concat(paths, out, with_audio=False):
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in paths), encoding="utf-8")
    cmd=[FFMPEG,"-y","-f","concat","-safe","0","-i",str(lst),
         "-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p","-an",str(out)]
    if with_audio:
        cmd=[FFMPEG,"-y","-f","concat","-safe","0","-i",str(lst),
             "-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p","-an",str(out)]
    run(cmd)

def main():
    FINAL.mkdir(parents=True, exist_ok=True)
    SHOT_VID.mkdir(parents=True, exist_ok=True)
    plan = json.loads((EP/"visual"/"SHOT_PLAN.json").read_text(encoding="utf-8"))
    tl = json.loads((RUN/"timeline.json").read_text(encoding="utf-8"))
    intro_tl = json.loads((RUN/"intro_timeline.json").read_text(encoding="utf-8"))
    para_dur = {pid: round(t["end_s"]-t["start_s"],3) for pid,t in tl["paragraphs"].items()}
    by_para = {}
    for s in plan["shots"]:
        by_para.setdefault(s["paragraph_id"], []).append(s)

    # 1. 每镜调整时长
    missing=[]; prepared={}
    for s in plan["shots"]:
        sid=s["id"]; pid=s["paragraph_id"]
        if pid not in para_dur:
            # intro 段落：用 intro timeline 或 est
            continue
        src = find_source(s)
        if not src:
            missing.append(sid); continue
        shots_in_p = by_para[pid]
        total_est = sum(x.get("est_seconds",1) for x in shots_in_p)
        dur = para_dur[pid] * (s.get("est_seconds",1)/max(total_est,1e-6))
        dur = max(2/FPS, round(dur*FPS)/FPS)
        out = SHOT_VID / f"{sid}.mp4"
        if not out.exists():
            try: adjust_duration(src, dur, out)
            except Exception as e:
                print(f"FAIL adjust {sid}: {e}"); missing.append(sid); continue
        prepared[sid] = out
    if missing:
        print(f"MISSING/FAIL shots ({len(missing)}): {missing[:12]}...")
    # 2. 每章视频（拼后补齐到章节音频时长，填补段间/章间留白，保证视音同步）
    chapter_videos=[]
    for sec in BODY_SECTIONS:
        shots=[s for s in plan["shots"] if s.get("section")==sec and s["id"] in prepared]
        shots.sort(key=lambda s: s["paragraph_id"])
        paths=[prepared[s["id"]] for s in shots]
        if not paths:
            print(f"no shots for {sec}"); continue
        cv = CHAP_VID / f"{sec}_video.mp4"
        concat(paths, cv)
        cv_dur = probe_dur(cv)
        # 章节音频时长（含留白）
        sec_audio = tl["sections"][sec]["seconds"]
        if cv_dur < sec_audio - 0.05:
            pad = sec_audio - cv_dur
            cvp = CHAP_VID / f"{sec}_video_padded.mp4"
            run([FFMPEG,"-y","-i",str(cv),"-an",
                 "-vf",f"tpad=stop_mode=clone:stop_duration={pad:.3f},fps=30",
                 "-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p",str(cvp)])
            cv = cvp; cv_dur = probe_dur(cv)
        chapter_videos.append(cv)
        print(f"{sec}: {len(paths)} shots -> {cv_dur:.1f}s (audio {sec_audio:.1f}s)")
    # 3. 正文视频（补齐到 body_narration 时长，补章间留白与尾部）
    body_v_tmp = CHAP_VID / "body_video.mp4"
    concat(chapter_videos, body_v_tmp)
    bv_dur = probe_dur(body_v_tmp)
    body_audio = tl["body_seconds"]
    if bv_dur < body_audio - 0.05:
        pad = body_audio - bv_dur
        body_v = CHAP_VID / "body_video_padded.mp4"
        run([FFMPEG,"-y","-i",str(body_v_tmp),"-an",
             "-vf",f"tpad=stop_mode=clone:stop_duration={pad:.3f},fps=30",
             "-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p",str(body_v)])
    else:
        body_v = body_v_tmp
    print(f"BODY video {probe_dur(body_v):.1f}s (audio {body_audio:.1f}s)")
    # 4. clean = intro + body
    clean = FINAL / "newton-to-chaos_clean.mp4"
    if INTRO_VID.exists():
        concat([INTRO_VID, body_v], clean)
    else:
        print("intro video missing, body-only"); concat([body_v], clean)
    print(f"CLEAN {probe_dur(clean):.1f}s -> {clean}")
    # 5. narration wav
    narr = FINAL / "newton-to-chaos_narration.wav"
    narr_list = narr.with_suffix(".txt")
    paths=[p for p in [INTRO_AUDIO, BODY_AUDIO] if p.exists()]
    narr_list.write_text("".join(f"file '{p.as_posix()}'\n" for p in paths), encoding="utf-8")
    run([FFMPEG,"-y","-f","concat","-safe","0","-i",str(narr_list),
         "-c:a","pcm_s16le","-ar","48000","-ac","1",str(narr)])
    print(f"NARRATION {probe_dur(narr):.1f}s -> {narr}")
    # 6. 差值检查
    cv_dur=probe_dur(clean); nv_dur=probe_dur(narr)
    print(f"DIFF {abs(cv_dur-nv_dur):.3f}s (limit ~1/{FPS}s={1/FPS:.3f}s)")
    return 0 if not missing else 2

if __name__=="__main__":
    raise SystemExit(main())
