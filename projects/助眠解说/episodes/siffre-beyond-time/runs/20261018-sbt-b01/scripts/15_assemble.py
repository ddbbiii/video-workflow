# -*- coding: utf-8 -*-
"""siffre 正文装配(body-only,2026-10-20 装配任务书口径)。

- 消费 manifests/assembly_manifest.json(12 号脚本产出的逐镜真源):
  i2v 镜 -> fps30 换算 + 精确截取(-frames:v)/尾帧停留(tpad clone);
  V5-C 镜(v2 第二轮裁决) -> 原速遍 361f + 拉伸循环遍,首尾 0.4667s 叠化,精确帧数;
  affine 镜 -> media/affine/<id>.mp4 直通(12b 已按精确帧数渲染);
  junctions(v2) -> c6-s07→c6-s08 切口 0.4667s 交叉叠化:c6-s08 由 motion_plan 条目
     重渲为 83f(camera_motion,同起止 view),与 c6-s07 叠化合成 195f=126+69 替代
     相邻两镜入 concat,总帧数与全片时间轴不变。
- 正文视频 = concat 单次重编码(H.264 1920x1080 30fps CFR,无字幕无 BGM);
- clean = 正文视频 + chapters/body_narration.wav(旁白 AAC),音视时长差须 ≤1 帧;
- watch 版(章节标记)由 15 号脚本顺带产出:同 clean 内容 -c copy + ffmetadata 章节。

片头不在本脚本范围(等正文视频池验收后另跑 13/14/18)。
i2v 源:runs/20261018-sbt-b01/i2v/(2026-10-20 剧本侧裁决:常量由 media/i2v 改指)。
"""
from __future__ import annotations
import json, shutil, subprocess, sys
from pathlib import Path

EP = Path(__file__).resolve().parents[3]
RUN = EP / "runs" / "20261018-sbt-b01"
AFFINE = RUN / "media" / "affine"
I2V = RUN / "i2v"                      # 裁决 2026-10-20:由 RUN/media/i2v 改指本 run 交付目录
SHOT_VID = RUN / "media" / "shot"
JUNCTION_DIR = RUN / "media" / "junction"
MPLAN = RUN / "motion_plan.json"
CAMERA_MOTION = Path(r"E:\program\1project\video\shared\camera-motion\camera_motion.py")
MANIFEST = RUN / "manifests" / "assembly_manifest.json"
BODY_AUDIO = RUN / "chapters" / "body_narration.wav"
TIMELINE = RUN / "timeline.json"
FINAL = EP / "video" / "final"
WATCH = RUN / "watch"
FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"
FPS = 30
X264 = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p"]
SECTION_ORDER = ["bridge", "ch01", "ch02", "ch03", "ch04", "ch05",
                 "ch06", "ch07", "ch08", "ch09", "ch10", "epilogue"]

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "")[-800:])
    return r

def probe(path, entries):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", entries,
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return r.stdout.strip()

def probe_dur(path):
    return float(probe(path, "format=duration"))

def nframes(path):
    v = probe(path, "stream=nb_frames")
    return int(v) if v.isdigit() else -1

def build_i2v_shot(src, n_frames, hold_s, out):
    """i2v 24fps -> 30fps,精确 n_frames 帧;hold_s>0 时尾帧克隆补足。"""
    vf = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30"
    if hold_s > 0:
        vf += f",tpad=stop_mode=clone:stop_duration={hold_s + 1.0:.3f}"
    run([FFMPEG, "-y", "-i", str(src), "-an", "-vf", vf,
         "-frames:v", str(n_frames),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p",
         str(out)])
    got = nframes(out)
    if got != n_frames:
        raise RuntimeError(f"{out.name}: frames {got} != {n_frames}")

def build_v5c_shot(src, n_frames, xfade_f, out):
    """V5-C(第二轮裁决 2026-10-20): i2v 原速一遍 + 拉伸循环遍,首尾叠化,精确 n_frames 帧。

    passA = i2v 全长 fps30 换算(289f@24 -> 361f 原速);
    passB = 同源拉伸到 (n-361+xfade) 帧,慢放补足窗口,无冻结;
    xfade 首尾 14f(0.4667s)接缝,输出 -frames:v 精确裁齐(已实测帧级精确)。
    """
    base = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
    pa = out.with_name(out.stem + "_passA.mp4")
    pb = out.with_name(out.stem + "_passB.mp4")
    run([FFMPEG, "-y", "-i", str(src), "-an", "-vf", f"{base},fps=30",
         *X264, str(pa)])
    na = nframes(pa)
    if na <= xfade_f:
        raise RuntimeError(f"{out.name}: passA {na}f <= xfade {xfade_f}f")
    nb = n_frames - na + xfade_f
    k = (nb + 2) / na                       # +2f 余量,-frames:v 裁齐
    run([FFMPEG, "-y", "-i", str(src), "-an",
         "-vf", f"{base},fps=30,setpts={k:.6f}*PTS,fps=30",
         "-frames:v", str(nb), *X264, str(pb)])
    if nframes(pb) != nb:
        raise RuntimeError(f"{out.name}: passB {nframes(pb)}f != {nb}f")
    off, dur = (na - xfade_f) / FPS, xfade_f / FPS
    run([FFMPEG, "-y", "-i", str(pa), "-i", str(pb),
         "-filter_complex",
         f"[0:v][1:v]xfade=transition=fade:duration={dur:.6f}:offset={off:.6f},format=yuv420p",
         "-r", str(FPS), "-frames:v", str(n_frames), *X264, str(out)])
    got = nframes(out)
    if got != n_frames:
        raise RuntimeError(f"{out.name}: v5c frames {got} != {n_frames}")
    pa.unlink(); pb.unlink()

def build_junction(first_clip, junction, out):
    """切口叠化(v2): second 镜按 motion_plan 条目重渲 ext 帧后与 first_clip 叠化。

    合成段帧数 = first + ext - xfade,替代相邻两镜入 concat,时间轴不变。
    """
    a_id, b_id = junction["between"]
    xf, ext_f, comp = junction["xfade_frames"], junction["second_ext_frames"], junction["composite_frames"]
    mplan = json.loads(MPLAN.read_text(encoding="utf-8"))
    entry = next(s for s in mplan["shots"] if s["id"] == b_id)
    extd = JUNCTION_DIR / f"{b_id}_ext{ext_f}"
    ext = extd / f"{b_id}.mp4"
    if not (ext.exists() and nframes(ext) == ext_f):
        if extd.exists():
            shutil.rmtree(extd)            # renderer 要求干净 run 目录
        extd.mkdir(parents=True)
        sub = dict(entry)
        sub["duration_s"] = ext_f / FPS    # 同起止 view,全窗匀滑伸展
        plan = {"schema_version": 1, "backend": "affine",
                "output": {"width": 1920, "height": 1080, "fps": FPS},
                "transition_s": 0, "shots": [sub]}
        pp = extd / "plan.json"
        pp.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        r = subprocess.run([sys.executable, str(CAMERA_MOTION), str(pp), "--out", str(extd)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError((r.stderr or "")[-800:])
    na = nframes(first_clip)
    if na + ext_f - xf != comp:
        raise RuntimeError(f"junction {a_id}->{b_id}: {na}+{ext_f}-{xf} != {comp}")
    run([FFMPEG, "-y", "-i", str(first_clip), "-i", str(ext),
         "-filter_complex",
         f"[0:v][1:v]xfade=transition=fade:duration={xf/FPS:.6f}:offset={(na-xf)/FPS:.6f},"
         f"format=yuv420p",
         "-r", str(FPS), "-frames:v", str(comp), *X264, str(out)])
    got = nframes(out)
    if got != comp:
        raise RuntimeError(f"{out.name}: junction frames {got} != {comp}")

def main():
    FINAL.mkdir(parents=True, exist_ok=True)
    SHOT_VID.mkdir(parents=True, exist_ok=True)
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    tl = json.loads(TIMELINE.read_text(encoding="utf-8"))
    shots = man["shots"]
    total_frames = man["summary"]["total_frames"]

    # 1) 逐镜备料(幂等:已存在且帧数正确则跳过)
    pairs, built, reused = [], 0, 0
    for e in shots:
        sid, nf = e["id"], e["total_frames"]
        if e["shot_class"] == "image_to_video" and not e.get("fallback_from"):
            out = SHOT_VID / f"{sid}.mp4"
            if not (out.exists() and nframes(out) == nf):
                if e.get("tail_extension_mode") == "loop_xfade":
                    build_v5c_shot(Path(e["source"]), nf, e["xfade_frames"], out)
                else:
                    build_i2v_shot(Path(e["source"]), nf, e["tail_extension_seconds"], out)
                built += 1
            else:
                reused += 1
            pairs.append((sid, out))
        else:
            p = AFFINE / f"{sid}.mp4"
            if not p.exists() or nframes(p) != nf:
                raise SystemExit(f"affine 缺失或帧数不符: {sid} (先跑 12b_render_affine)")
            pairs.append((sid, p))
    print(f"shots: {len(pairs)} (i2v built {built}, reused {reused}, affine direct {len(pairs)-built-reused})")

    # 1b) junctions(v2 第二轮裁决): 切口叠化合成段替代相邻两镜
    for j in man.get("junctions", []):
        a_id, b_id = j["between"]
        idx = next((i for i, (sid, _) in enumerate(pairs)
                    if sid == a_id and i + 1 < len(pairs) and pairs[i + 1][0] == b_id), None)
        if idx is None:
            raise SystemExit(f"junction {a_id}->{b_id}: 相邻镜头未找到")
        comp = JUNCTION_DIR / f"{a_id}_{b_id}_xfade.mp4"
        if not (comp.exists() and nframes(comp) == j["composite_frames"]):
            build_junction(pairs[idx][1], j, comp)
        pairs[idx:idx + 2] = [(f"{a_id}+{b_id}", comp)]
        print(f"junction: {a_id}+{b_id} xfade {j['xfade_frames']/FPS:.4f}s "
              f"-> {comp.name} ({j['composite_frames']}f)")
    concat_paths = [p for _, p in pairs]

    # 2) 正文视频:单次重编码 concat(统一 SPS/时间基,CFR 30)
    body_v = RUN / "media" / "body_video.mp4"
    lst = body_v.with_suffix(".txt")
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in concat_paths), encoding="utf-8")
    if not (body_v.exists() and nframes(body_v) == total_frames):
        run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
             "-an", "-r", str(FPS), "-fps_mode", "cfr",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", str(body_v)])
    bv_frames = nframes(body_v)
    bv_dur = probe_dur(body_v)
    a_dur = probe_dur(BODY_AUDIO)
    print(f"BODY video {bv_frames}f {bv_dur:.3f}s / audio {a_dur:.3f}s / diff {abs(bv_dur-a_dur)*1000:.1f}ms")
    if bv_frames != total_frames:
        raise SystemExit(f"body frames {bv_frames} != manifest {total_frames}")

    # 3) clean:正文视频 + 旁白(无字幕无 BGM)
    clean = FINAL / "siffre-body_clean.mp4"
    run([FFMPEG, "-y", "-i", str(body_v), "-i", str(BODY_AUDIO),
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "1",
         "-movflags", "+faststart", str(clean)])
    cv_dur = probe_dur(clean)
    print(f"CLEAN {cv_dur:.3f}s -> {clean}")

    # 4) watch 版:同 clean 内容 + 章节标记(ffmetadata,-c copy)
    WATCH.mkdir(parents=True, exist_ok=True)
    sp = json.loads((EP / "visual" / "SHOT_PLAN.json").read_text(encoding="utf-8"))
    titles = sp.get("section_titles", {})
    meta = WATCH / "chapters_ffmetadata.txt"
    lines = [";FFMETADATA1"]
    bounds = [(k, tl["sections"][k]["start_s"], tl["sections"][k]["end_s"]) for k in SECTION_ORDER]
    for i, (k, st, en) in enumerate(bounds):
        end_ms = round((bounds[i + 1][1] if i + 1 < len(bounds) else tl["body_seconds"]) * 1000)
        lines += ["[CHAPTER]", "TIMEBASE=1/1000",
                  f"START={round(st*1000)}", f"END={end_ms}",
                  f"TITLE={k} {titles.get(k,'')}"]
    meta.write_text("\n".join(lines) + "\n", encoding="utf-8")
    watch = WATCH / "siffre-body_watch.mp4"
    run([FFMPEG, "-y", "-i", str(clean), "-i", str(meta),
         "-map", "0", "-map_chapters", "1", "-c", "copy", "-movflags", "+faststart", str(watch)])
    print(f"WATCH {probe_dur(watch):.3f}s -> {watch}")

    # 5) 差值终检(≤1 帧)
    av_diff = cv_dur - a_dur
    ok = abs(av_diff) <= 1 / FPS + 0.005
    print(f"AV DIFF {av_diff*1000:.1f}ms (limit {1000/FPS:.1f}ms) -> {'OK' if ok else 'FAIL'}")
    if not ok:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
