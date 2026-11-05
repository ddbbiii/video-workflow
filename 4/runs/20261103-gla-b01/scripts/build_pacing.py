# -*- coding: utf-8 -*-
"""glacier-river 全片节奏重构(2026-10-22,响应用户反馈:30s-2min 素材不换不动)。

像片头那样做,全片三条规则:
1. 任何单一素材连续出镜 ≤ MAXHOLD(12s):长段落自动切分,复用本章素材轮换(全片同素材 ≤2 次、不相邻);
2. 段落内换镜用 0.4s 叠化(不抢语音,只切画面),段与段(章内)硬切,章与章自然过渡;
3. 每一段都有缓慢运镜(P1 单向推/拉/平移逐段变向;i2v 镜保持原生 V1 截取,不冻结长停)。

产物:
  manifests/pacing_plan.json   — 逐段计划(段落→segments[sid,cls,dur,profile])
  media/para/<pid>.mp4         — 每段落的最终视频(叠化已含,帧数=段落音频帧数)
用法:
  python build_pacing.py plan            # 只出计划
  python build_pacing.py render 0 6      # 分片渲染(片号/总分片)
  python build_pacing.py merge           # 按段落叠化合并+帧数校验
组合白名单遵守 visual-motion.md:P1/P2(推拉类)与 i2v V1 截取;不跨类拼镜。
"""
from __future__ import annotations
import json, math, shutil, subprocess, sys, time
from pathlib import Path

EP = Path(__file__).resolve().parents[3]
RUN = EP / "runs" / "20261103-gla-b01"
TL = RUN / "timeline.json"
SP = EP / "visual" / "SHOT_PLAN.json"
PLAN = RUN / "manifests" / "pacing_plan.json"
STILLS16 = EP / "image" / "stills_16x9"
I2V = RUN / "i2v"
AFF_OUT = RUN / "media" / "pacing_segs"
PARA_OUT = RUN / "media" / "para"
CM = Path(r"E:\program\1project\video\shared\camera-motion\camera_motion.py")
FF = shutil.which("ffmpeg") or r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"
FP = shutil.which("ffprobe") or str(Path(FF).with_name("ffprobe.exe"))
FPS = 30
MAXHOLD = 12.0
MIN_SEG = 4.0
XFADE = 0.4

# P1 单向运镜模板(白名单合规:单向推/拉/平移,不往返)
PROFILES = {
    "pin":   ([0.010, 0.010, 0.980, 0.980], [0.055, 0.055, 0.870, 0.870]),
    "pout":  ([0.055, 0.055, 0.870, 0.870], [0.010, 0.010, 0.980, 0.980]),
    "panR":  ([0.010, 0.045, 0.900, 0.900], [0.085, 0.045, 0.900, 0.900]),
    "panL":  ([0.085, 0.045, 0.900, 0.900], [0.010, 0.045, 0.900, 0.900]),
    "diag":  ([0.010, 0.010, 0.940, 0.940], [0.065, 0.065, 0.850, 0.850]),
}
PROFILE_ORDER = ["pin", "pout", "panR", "panL", "diag"]
I2V_NATIVE_S = 361 / FPS          # 289f@24fps -> 361f@30fps
I2V_CAP_S = 361 / FPS - 0.5       # i2v 段上限留出叠化余量(不触发截尾)


def load():
    tl = json.loads(TL.read_text(encoding="utf-8"))
    sp = json.loads(SP.read_text(encoding="utf-8"))
    return tl, sp


def build_plan():
    tl, sp = load()
    paras = sorted(tl["paragraphs"].items(), key=lambda kv: kv[1]["start_s"])
    by_para: dict[str, list] = {}
    for s in sp["shots"]:
        by_para.setdefault(s["paragraph_id"], []).append(s)
    sec_pool: dict[str, list] = {}
    for s in sp["shots"]:
        sec_pool.setdefault(s["section"], []).append(s["id"])

    use_count: dict[str, int] = {}
    out_paras = []
    global_pi = 0
    for pid, info in paras:
        sec = pid.rsplit("-", 1)[0]
        if sec == "intro":
            continue
        dur = info["end_s"] - info["start_s"]
        natives = by_para.get(pid, [])
        segs = []
        # 先放本段原生镜(i2v 按原生时长上限)
        for s in natives:
            segs.append({"sid": s["id"], "cls": s["shot_class"]})
        # 时长配额:原生镜按 est 权重;i2v 上限原生 12s,超出让给后续 affine
        ests = [max(s.get("est_seconds", 5), 4) for s in natives] or [5]
        alloc = []
        for i, s in enumerate(natives):
            share = dur * ests[i] / sum(ests) if natives else dur
            alloc.append(share)
        scale = dur / sum(alloc) if alloc else 1
        alloc = [a * scale for a in alloc]

        cls_of = {s["id"]: s["shot_class"] for s in sp["shots"]}
        def cap_for(cls):
            return I2V_CAP_S if cls == "image_to_video" else MAXHOLD
        def pick_extra(prev_sid, affine_only=False):
            pool = [x for x in sec_pool.get(sec, [])
                    if use_count.get(x, 0) < 2 and x != prev_sid
                    and (not affine_only or cls_of[x] != "image_to_video")]
            if not pool:
                pool = [x for x in sec_pool.get(sec, []) if x != prev_sid
                        and (not affine_only or cls_of[x] != "image_to_video")]
            if not pool:
                return None
            pool.sort(key=lambda x: (use_count.get(x, 0), x))
            return pool[0]

        result = []   # [sid, cls, dur]
        prev = None
        def add(sid, want):
            nonlocal prev
            cls = cls_of[sid]
            take = min(want, cap_for(cls))
            # 小额只折进 affine 末段;i2v 末段绝不折叠(超源上限会缺帧),小额单列
            if take < MIN_SEG and result and result[-1][1] != "image_to_video" and result[-1][0] != sid:
                result[-1][2] += take
            else:
                result.append([sid, cls, take])
            prev = result[-1][0]
            use_count[sid] = use_count.get(sid, 0) + 1

        # 2026-10-24 重构:先加全部原生镜(避免补段抢走后续原生镜造成相邻同镜),
        # 再用同章补段填余量;补段永远避开 prev,不相邻红线由结构保证。
        added = 0.0
        for s, a in zip(natives, alloc):
            add(s["id"], a)
            added += min(a, cap_for(s["shot_class"]))
        rem = dur - added
        while rem > MIN_SEG + 0.5:
            sid = pick_extra(prev)
            if sid is None:
                break
            take = min(rem, cap_for(cls_of[sid]))
            if take < MIN_SEG + 0.5 and result and result[-1][1] != "image_to_video":
                result[-1][2] += take
                rem -= take
                continue
            add(sid, take)
            rem -= take
        if rem > 0 and result:
            if result[-1][1] == "image_to_video":
                sid = pick_extra(prev, affine_only=True)
                if sid is not None:
                    add(sid, rem)
                else:
                    result[-1][2] += rem
            else:
                result[-1][2] += rem
        if not result:
            # 极短段落(<2.5s)没有原生镜、fill 循环也不会触发:至少分一个镜,避免空段崩溃
            sid = pick_extra(None) or (sec_pool.get(sec) or [None])[0]
            if sid is None:
                raise SystemExit(f"{pid}: no shot available in {sec}")
            result.append([sid, cls_of[sid], dur])
            use_count[sid] = use_count.get(sid, 0) + 1
            prev = sid
        got = sum(r[2] for r in result)
        while dur - got > 2.5:
            sid = pick_extra(prev)
            if sid is None:
                break
            want = dur - got
            if cls_of[sid] == "image_to_video" and want < MIN_SEG + 0.5:
                sid = pick_extra(prev, affine_only=True) or sid
            add(sid, want)
            got += result[-1][2]
        if dur - got > 0 and result:
            if result[-1][1] == "image_to_video" and dur - got > 0.5:
                sid = pick_extra(prev, affine_only=True)
                if sid:
                    add(sid, dur - got)
                else:
                    result[-1][2] += dur - got
            else:
                result[-1][2] += dur - got
        # 链尾补偿:xfade 链可用长度 = sum(dur) - (n-1)*XFADE + 末段余量,
        # 给末段追加 (n-1)*XFADE 保证链长 ≥ 段落帧数(实测短 36f/4 段的根因)
        if len(result) > 1:
            ext = (len(result) - 1) * XFADE
            sid = pick_extra(prev, affine_only=True)
            if result[-1][1] == "image_to_video" or (
                    sid is not None and result[-1][2] + ext > MAXHOLD):
                if sid is not None:
                    result.append([sid, cls_of[sid], max(ext + 1.5, 2.0)])
                    use_count[sid] = use_count.get(sid, 0) + 1
                elif result[-1][1] != "image_to_video":
                    result[-1][2] += ext
                # i2v 末段且池空:保底不动,由 merge 的 tpad 兜尾
            else:
                result[-1][2] += ext
        # 运镜模板:全片逐段轮换方向(原实现每段重置为 pin,导致几乎全是推近)
        for r in result:
            if r[1] != "image_to_video":
                r.append(PROFILE_ORDER[global_pi % len(PROFILE_ORDER)])
                global_pi += 1
            else:
                r.append("v1")
        out_paras.append({
            "pid": pid, "section": sec, "dur_s": round(dur, 3),
            "frames": round(dur * FPS),
            "segments": [{"sid": r[0], "cls": r[1], "dur_s": round(r[2], 3), "profile": r[3]}
                         for r in result],
        })
    doc = {
        "schema_version": 2, "episode": "glacier-river",
        "rules": [f"单素材连续出镜≤{MAXHOLD}s(个别尾部补偿≤16s)", f"段内换镜叠化{XFADE}s(末段补足帧数)", "P1 单向运镜逐段变向;i2v 原生截取不冻结"],
        "maxhold_s": MAXHOLD, "xfade_s": XFADE, "fps": FPS,
        "use_count": use_count,
        "paragraphs": out_paras,
    }
    PLAN.parent.mkdir(parents=True, exist_ok=True)
    PLAN.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    nseg = sum(len(p["segments"]) for p in out_paras)
    print(f"pacing plan: {len(out_paras)} paras / {nseg} segments -> {PLAN}")
    return doc


def nframes(path):
    out = subprocess.run([FP, "-v", "error", "-show_entries", "stream=nb_frames",
                          "-of", "csv=p=0", str(path)], capture_output=True).stdout.decode()
    v = out.strip()
    return int(v) if v.isdigit() else -1


def render(doc, shard, nshards):
    AFF_OUT.mkdir(parents=True, exist_ok=True)
    segs = []
    for p in doc["paragraphs"]:
        for i, s in enumerate(p["segments"]):
            segs.append((p["pid"], i, s))
    mine = [x for idx, x in enumerate(segs) if idx % nshards == shard]
    for pid, i, s in mine:
        out = AFF_OUT / f"{pid}__{i:02d}__{s['sid']}.mp4"
        need_frames = round(s["dur_s"] * FPS) + XFADE_S_FRAMES
        if out.exists() and nframes(out) == need_frames:
            continue
        if s["cls"] == "image_to_video":
            src = I2V / f"{s['sid']}.mp4"
            if not src.exists():   # i2v 批量未完:先跳过,等 i2v 交付后幂等补渲
                print(f"seg {out.stem} SKIP (i2v pending)", flush=True)
                continue
            subprocess.run([FF, "-y", "-v", "error", "-i", str(src), "-an",
                            "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30",
                            "-frames:v", str(need_frames),
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
                            "-pix_fmt", "yuv420p", str(out)], check=True)
        else:
            src = STILLS16 / f"{s['sid']}.jpg"
            if not src.exists():  # 桥段新图可能尚未 11 处理,即时裁
                from PIL import Image
                raw = EP / "image" / "stills" / f"{s['sid']}.jpg"
                with Image.open(raw) as im:
                    w, h = im.size
                    tw, th = (w, round(w * 9 / 16)) if w / h >= 16 / 9 else (round(h * 16 / 9), h)
                    im.crop(((w - tw) // 2, (h - th) // 2, (w + tw) // 2, (h + th) // 2))\
                      .save(src, quality=95)
            sview, eview = PROFILES[s["profile"]]
            sub = {"id": out.stem, "source": str(src),
                   "duration_s": need_frames / FPS,
                   "start_view": sview, "end_view": eview,
                   "curve": {"type": "ramped_linear", "ramp_s": 0.6}}
            plan = {"schema_version": 1, "backend": "affine",
                    "output": {"width": 1920, "height": 1080, "fps": FPS},
                    "transition_s": 0, "shots": [sub]}
            tmp = AFF_OUT / (out.stem + "_run")
            if tmp.exists():
                shutil.rmtree(tmp)
            tmp.mkdir(parents=True)
            pp = tmp / "plan.json"
            pp.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            r = subprocess.run([sys.executable, str(CM), str(pp), "--out", str(tmp)],
                               capture_output=True)
            if r.returncode != 0:
                raise RuntimeError((r.stderr or b"")[-500:].decode("utf-8", "replace"))
            produced = tmp / (out.stem + ".mp4")
            shutil.move(str(produced), str(out))
            shutil.rmtree(tmp, ignore_errors=True)
        print(f"seg {out.stem} {need_frames}f ok", flush=True)


XFADE_S_FRAMES = round(XFADE * FPS)  # 12


def merge(doc):
    PARA_OUT.mkdir(parents=True, exist_ok=True)
    for p in doc["paragraphs"]:
        out = PARA_OUT / f"{p['pid']}.mp4"
        clips = []
        for i, s in enumerate(p["segments"]):
            clips.append(AFF_OUT / f"{p['pid']}__{i:02d}__{s['sid']}.mp4")
        missing = [c.name for c in clips if not c.exists() or nframes(c) <= 0]
        if missing:
            raise SystemExit(f"{p['pid']}: missing segs {missing}")
        if len(clips) == 1:
            if nframes(clips[0]) == p["frames"]:
                shutil.copy2(clips[0], out)
            else:  # 单段:裁掉叠化余量,帧数精确
                r = subprocess.run([FF, "-y", "-v", "error", "-i", str(clips[0]), "-an",
                                    "-frames:v", str(p["frames"]),
                                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
                                    "-pix_fmt", "yuv420p", str(out)], capture_output=True)
                if r.returncode != 0:
                    raise RuntimeError((r.stderr or b"")[-500:].decode("utf-8", "replace"))
        else:
            inputs = []
            for c in clips:
                inputs += ["-i", str(c)]
            fc = ""
            prev = "[0:v]"
            # 叠化吃掉 12f/接缝:第 j 接缝 offset = sum(前 j 段时长) - j*XFADE
            acc = 0.0
            offs = []
            for j, s in enumerate(p["segments"][:-1]):
                acc += s["dur_s"]
                offs.append(acc - (j + 1) * XFADE)
            for j in range(1, len(clips)):
                lab = f"[v{j}]"
                fc += (f"{prev}[{j}:v]xfade=transition=fade:duration={XFADE}"
                       f":offset={offs[j-1]:.3f}{lab};")
                prev = lab
            # tpad 保底:输入略有短缺时末帧克隆 ≤1s,-frames:v 锁精确帧数
            fc += f"{prev}tpad=stop_mode=clone:stop_duration=1.0,format=yuv420p[vout]"
            r = subprocess.run([FF, "-y", "-v", "error"] + inputs +
                               ["-filter_complex", fc, "-map", "[vout]",
                                "-r", str(FPS), "-frames:v", str(p["frames"]),
                                "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
                                "-pix_fmt", "yuv420p", str(out)], capture_output=True)
            if r.returncode != 0:
                raise RuntimeError((r.stderr or b"")[-600:].decode("utf-8", "replace"))
        got = nframes(out)
        status = "OK" if got == p["frames"] else f"FRAME_MISMATCH({got}/{p['frames']})"
        print(f"{p['pid']}: {got}f target {p['frames']}f {status}", flush=True)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "plan"
    if mode == "plan":
        build_plan()
    elif mode == "render":
        doc = json.loads(PLAN.read_text(encoding="utf-8"))
        render(doc, int(sys.argv[2]), int(sys.argv[3]))
    elif mode == "merge":
        doc = json.loads(PLAN.read_text(encoding="utf-8"))
        merge(doc)
    else:
        raise SystemExit("usage: plan | render <shard> <nshards> | merge")
