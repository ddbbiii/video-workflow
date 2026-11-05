# -*- coding: utf-8 -*-
"""最终拼装(final-delivery 口径)。
逐镜:affine/i2v mp4 → 按 timeline 目标时长 trim/补足 → 章节视频(无声)
→ 正文视频 → 片头视频 + 正文视频 = clean.mp4(无音轨)
旁白:intro.wav + body_narration.wav = life-manual_narration.wav
输出 video/final/{life-manual_clean.mp4, life-manual_narration.wav}

mariana 无受控模拟镜头(全集零图表),sim 分支仅作兼容保留。
INTRO_BATCH 须与 14_build_intro.py 的 OUT 批次名保持一致。
移植自 newton 15_assemble.py。
"""
from __future__ import annotations
import json, subprocess, math
from pathlib import Path

EP = Path(r"E:\program\1project\video\编剧3")
RUN = EP / "runs" / "20261024-lm-b01"
AFFINE = RUN / "media" / "affine"
SIMS = EP / "image" / "sims"          # 本集无 sim,兼容保留
I2V = RUN / "i2v"                     # 2026-10-20 对齐 run_mariana_i2v_batch 交付目录(siffre 同款裁决)
SHOT_VID = RUN / "media" / "shot"      # per-shot adjusted mp4
CHAP_VID = RUN / "chapters"
INTRO_BATCH = "batch-20261024-v1"     # TODO: 与 14_build_intro.py OUT 同步
INTRO_VID = RUN / "intro" / INTRO_BATCH / "clean-intro.mp4"
BODY_AUDIO = CHAP_VID / "body_narration.wav"
INTRO_AUDIO = CHAP_VID / "intro.wav"
FINAL = EP / "video" / "final"
FFMPEG = r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"
FFPROBE = r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffprobe.exe"
FPS = 30
BODY_SECTIONS = ["bridge", "ch01", "ch02", "ch03", "ch04", "ch05",
                 "ch06", "ch07", "ch08", "ch09", "ch10", "epilogue"]

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "")[-600:])
    return r

def probe_dur(path):
    r = subprocess.run([FFPROBE,"-v","error","-show_entries","format=duration",
                        "-of","csv=p=0",str(path)], capture_output=True, text=True)
    return float(r.stdout.strip())

def nframes(path):
    r = subprocess.run([FFPROBE,"-v","error","-show_entries","stream=nb_frames",
                        "-of","csv=p=0",str(path)], capture_output=True, text=True)
    v = r.stdout.strip()
    return int(v) if v.isdigit() else -1

XFADE_F = 14  # V5-C 首尾叠化 14f(0.4667s),siffre 2026-10-20 实测口径

def build_v5c_shot(src, n_frames, out):
    """V5-C 循环镜(siffre 15_assemble 移植):原速遍 + 拉伸循环遍,首尾叠化,精确 n_frames 帧。

    i2v 289f@24fps -> 361f@30fps 原速;目标更长时第二遍慢放循环补足,接缝 14f 叠化。
    目标 ≤ 361f 时无需循环,直接截取。
    """
    if n_frames <= 361:
        run([FFMPEG,"-y","-i",str(src),"-an",
             "-vf","scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30",
             "-frames:v",str(n_frames),
             "-c:v","libx264","-preset","veryfast","-crf","16","-pix_fmt","yuv420p",str(out)])
        return
    xf = XFADE_F
    base = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
    pa = out.with_name(out.stem + "_passA.mp4")
    pb = out.with_name(out.stem + "_passB.mp4")
    run([FFMPEG,"-y","-i",str(src),"-an","-vf",f"{base},fps=30",
         "-c:v","libx264","-preset","veryfast","-crf","16","-pix_fmt","yuv420p",str(pa)])
    na = nframes(pa)
    nb = n_frames - na + xf
    k = (nb + 2) / na
    run([FFMPEG,"-y","-i",str(src),"-an",
         "-vf",f"{base},fps=30,setpts={k:.6f}*PTS,fps=30",
         "-frames:v",str(nb),
         "-c:v","libx264","-preset","veryfast","-crf","16","-pix_fmt","yuv420p",str(pb)])
    if nframes(pb) != nb:
        raise RuntimeError(f"{out.name}: passB {nframes(pb)}f != {nb}f")
    off, dur = (na - xf) / FPS, xf / FPS
    run([FFMPEG,"-y","-i",str(pa),"-i",str(pb),
         "-filter_complex",
         f"[0:v][1:v]xfade=transition=fade:duration={dur:.6f}:offset={off:.6f},format=yuv420p",
         "-r",str(FPS),"-frames:v",str(n_frames),
         "-c:v","libx264","-preset","veryfast","-crf","16","-pix_fmt","yuv420p",str(out)])
    got = nframes(out)
    if got != n_frames:
        raise RuntimeError(f"{out.name}: v5c frames {got} != {n_frames}")
    pa.unlink(); pb.unlink()

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
    """把 src mp4 调整到 target 秒:长则截断,短则末帧冻结补足。统一 1920x1080@30fps 无音。"""
    sdur = probe_dur(src)
    if sdur >= target - 0.01:
        # trim + scale
        cmd=[FFMPEG,"-y","-i",str(src),"-t",f"{target:.3f}","-an",
             "-vf","scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30",
             "-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p",str(out)]
    else:
        # freeze last frame to fill: tpad
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

    # 1. 段落视频(pacing 产物 build_pacing merge,已含段内 0.4s 叠化与帧数校验;
    #    2026-10-22 节奏重构:全片 ≤12s 换镜,替代旧的逐镜 est 配额)
    PARA = RUN / "media" / "para"
    para_files = {}
    for pid, t in sorted(tl["paragraphs"].items(), key=lambda kv: kv[1]["start_s"]):
        sec = pid.rsplit("-", 1)[0]
        if sec not in BODY_SECTIONS:
            continue
        f = PARA / f"{pid}.mp4"
        if not f.exists():
            print(f"WARN para video missing: {pid}"); continue
        para_files.setdefault(sec, []).append(f)
    n_para = sum(len(v) for v in para_files.values())
    print(f"para videos: {n_para}")
    # 2. 每章视频(拼后补齐到章节音频时长,填补段间/章间留白,保证视音同步)
    chapter_videos=[]
    for sec in BODY_SECTIONS:
        paths = para_files.get(sec, [])
        if not paths:
            print(f"no para videos for {sec}"); continue
        cv = CHAP_VID / f"{sec}_video.mp4"
        concat(paths, cv)
        cv_dur = probe_dur(cv)
        # 章节音频时长(含留白)
        sec_audio = tl["sections"][sec]["seconds"]
        if cv_dur < sec_audio - 0.05:
            pad = sec_audio - cv_dur
            cvp = CHAP_VID / f"{sec}_video_padded.mp4"
            run([FFMPEG,"-y","-i",str(cv),"-an",
                 "-vf",f"tpad=stop_mode=clone:stop_duration={pad:.3f},fps=30",
                 "-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p",str(cvp)])
            cv = cvp; cv_dur = probe_dur(cv)
        chapter_videos.append(cv)
        print(f"{sec}: {len(paths)} shot -> {cv_dur:.1f}s (audio {sec_audio:.1f}s)")
    # 3. 正文视频(补齐到 body_narration 时长,补章间留白与尾部)
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
    clean = FINAL / "life-manual_clean.mp4"
    if INTRO_VID.exists():
        concat([INTRO_VID, body_v], clean)
    else:
        print("intro video missing, body-only"); concat([body_v], clean)
    print(f"CLEAN {probe_dur(clean):.1f}s -> {clean}")
    # 5. narration wav
    narr = FINAL / "life-manual_narration.wav"
    narr_list = narr.with_suffix(".txt")
    paths=[p for p in [INTRO_AUDIO, BODY_AUDIO] if p.exists()]
    narr_list.write_text("".join(f"file '{p.as_posix()}'\n" for p in paths), encoding="utf-8")
    run([FFMPEG,"-y","-f","concat","-safe","0","-i",str(narr_list),
         "-c:a","pcm_s16le","-ar","48000","-ac","1",str(narr)])
    print(f"NARRATION {probe_dur(narr):.1f}s -> {narr}")
    # 6. 差值检查
    cv_dur=probe_dur(clean); nv_dur=probe_dur(narr)
    print(f"DIFF {abs(cv_dur-nv_dur):.3f}s (limit ~1/{FPS}s={1/FPS:.3f}s)")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
