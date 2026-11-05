# -*- coding: utf-8 -*-
"""助眠科普统一开头模块 V1.0（Hook Intro）。

配置驱动：configs/hook_intro_glacier.json
流程：TTS 三句 → 裁切/变速 → 拼音轨与时间轴 → 背景慢推 → 大字 slow_zoom_text
      → 过渡旁白常规字幕 → intro.mp4 / intro.wav → A/B 30s 预览。
只做开头，不改正文；输出独立目录，不影响已发布成片。
"""
from __future__ import annotations
import json
import math
import subprocess
import sys
import wave
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

EP = Path(r"E:\program\1project\video\4")
RUN = EP / "runs" / "20261105-hook-b01"
CFG = json.loads((EP / "configs" / "hook_intro_glacier.json").read_text(encoding="utf-8"))
FONT = Path(CFG["font"])
FF = r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"
FP = FF.replace("ffmpeg.exe", "ffprobe.exe")
VENV_PY = r"E:\program\1project\video\shared\runtime\engines\tts\voxcpm\.venv\Scripts\python.exe"
W, H, FPS = 1920, 1080, 30
SR = 48000
ATEMPO = 0.774224
FS = CFG["font_size"]
WARM = tuple(CFG["text_color"]) + (255,)
DARK = tuple(CFG["stroke_color"]) + (235,)
STROKE = CFG["stroke"]
T_ANIM = CFG["text_animation"]
CAM = CFG["camera_motion"]
VT = CFG["voice_timing"]


def log(*a):
    print(*a, flush=True)


def read_wav16(p):
    with wave.open(str(p), "rb") as w:
        sr, ch = w.getframerate(), w.getnchannels()
        y = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.int16)
    if ch > 1:
        y = y.reshape(-1, ch).mean(axis=1).astype(np.int16)
    return y, sr


def write_wav16(p, y, sr=SR):
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(np.asarray(y, dtype="<i2").tobytes())


def dur_of(p):
    r = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return float(r.stdout.strip())


def trim(y, sr):
    frame = max(1, int(sr * 0.02))
    thr = 10 ** (-45 / 20)
    n = len(y) // frame
    rms = np.sqrt(np.mean(y[: n * frame].reshape(n, frame).astype(np.float64) ** 2, axis=1))
    act = np.where(rms > thr)[0]
    if not len(act):
        return y
    a = max(0, int(act[0] * frame - 0.10 * sr))
    b = min(len(y), int((act[-1] + 1) * frame + 0.15 * sr))
    return y[a:b]


def process_audio():
    raw = RUN / "audio" / "raw"
    proc = RUN / "audio" / "processed"
    proc.mkdir(parents=True, exist_ok=True)
    out = {}
    for sid in ("hook-l1", "hook-l2", "hook-trans"):
        src, dst = raw / f"{sid}.wav", proc / f"{sid}.wav"
        if dst.exists():
            out[sid] = read_wav16(dst)[0]; continue
        y, sr = read_wav16(src)
        y = trim(y, sr)
        tmp = proc / f"{sid}.trim.wav"
        write_wav16(tmp, y, sr)
        subprocess.run([FF, "-y", "-i", str(tmp), "-filter:a", f"atempo={ATEMPO}",
                        "-acodec", "pcm_s16le", str(dst)], check=True, capture_output=True)
        tmp.unlink(missing_ok=True)
        out[sid] = read_wav16(dst)[0]
        log(sid, round(len(out[sid]) / SR, 3), "s")
    return out


def build_audio(pcm):
    head, g1, g2, tail = VT["head_s"], VT["gap1_s"], VT["gap2_s"], VT["tail_s"]
    chunks = [np.zeros(int(SR * head), dtype=np.int16)]
    t = head
    units = []
    for i, sid in enumerate(("hook-l1", "hook-l2", "hook-trans")):
        if i == 1:
            chunks.append(np.zeros(int(SR * g1), dtype=np.int16)); t += g1
        if i == 2:
            chunks.append(np.zeros(int(SR * g2), dtype=np.int16)); t += g2
        y = pcm[sid]
        s = t
        chunks.append(y); t += len(y) / SR
        units.append({"id": sid, "start_s": round(s, 3), "end_s": round(t, 3),
                      "seconds": round(len(y) / SR, 3)})
    chunks.append(np.zeros(int(SR * tail), dtype=np.int16)); t += tail
    full = np.concatenate(chunks)
    RUN.mkdir(parents=True, exist_ok=True)
    write_wav16(RUN / "intro.wav", full)
    meta = {"intro_seconds": round(t, 3), "units": units, "sample_rate": SR,
            "voice_timing": VT}
    (RUN / "intro_timeline.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                             encoding="utf-8")
    return meta


def dp_align(locked, toks):
    A = [c for c in locked if c not in "，,。？！；：、— "]
    B = [t["c"] for t in toks]
    n, m = len(A), len(B)
    NEG = -10 ** 9
    dp = np.full((n + 1, m + 1), NEG, dtype=np.int32)
    ptr = np.zeros((n + 1, m + 1), dtype=np.int8)
    dp[0, 0] = 0
    for i in range(1, n + 1):
        dp[i, 0] = -2 * i; ptr[i, 0] = 2
    for j in range(1, m + 1):
        dp[0, j] = -2 * j; ptr[0, j] = 3
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            sc = 3 if A[i - 1] == B[j - 1] else -1
            best = dp[i - 1, j - 1] + sc; p = 1
            up = dp[i - 1, j] - 2
            if up > best: best, p = up, 2
            left = dp[i, j - 1] - 2
            if left > best: best, p = left, 3
            dp[i, j] = best; ptr[i, j] = p
    pairs = {}
    i, j = n, m
    while i > 0 or j > 0:
        p = ptr[i, j]
        if i > 0 and j > 0 and p == 1:
            pairs[i - 1] = toks[j - 1]; i -= 1; j -= 1
        elif i > 0 and p == 2:
            i -= 1
        else:
            j -= 1
    return A, pairs


def transition_cues(meta):
    trans = meta["units"][2]
    wav = RUN / "audio" / "processed" / "hook-trans.wav"
    tokp = RUN / "transition_tokens.json"
    if not tokp.exists():
        subprocess.run([VENV_PY, str(RUN / "scripts" / "hook_asr.py"), str(wav), str(tokp)],
                       check=True, capture_output=True)
    toks = json.loads(tokp.read_text(encoding="utf-8"))
    A, pairs = dp_align(CFG["transition_narration"], toks)
    # 每个锁定字的时间
    chars = [None] * len(CFG["transition_narration"])
    ai = 0
    for i, ch in enumerate(CFG["transition_narration"]):
        if ch in "，,。？！；：、— ":
            continue
        if ai in pairs:
            chars[i] = (pairs[ai]["s"], pairs[ai]["e"])
        ai += 1
    # 按标点切句
    import re
    cues = []
    for m in re.finditer(r"[^，,。；;：]+[，,。；;]?", CFG["transition_narration"]):
        text = m.group(0).strip("，,。；;：")
        if not text:
            continue
        ts = [chars[i] for i in range(m.start(), m.end()) if i < len(chars) and chars[i]]
        if not ts:
            continue
        s, e = min(t[0] for t in ts), max(t[1] for t in ts)
        cues.append({"text": text, "start_s": round(trans["start_s"] + s, 3),
                     "end_s": round(trans["start_s"] + e + 0.10, 3)})
    return cues


def make_layer(lines):
    font = ImageFont.truetype(str(FONT), FS * 2)
    pad = STROKE * 2 + 30
    widths = [font.getlength(s) for s in lines]
    lw = int(max(widths)) + pad * 2
    step = int(FS * 1.55 * 2)          # 2x 画布上的行距
    lh = step * len(lines) + pad * 2
    img = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    y = pad
    r = STROKE * 2
    for ln in lines:
        tw = font.getlength(ln)
        x = (lw - tw) / 2
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r:
                    d.text((x + dx, y + dy), ln, font=font, fill=DARK)
        d.text((x, y), ln, font=font, fill=WARM)
        y += step
    return img


def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def _render_bg_seg(still, dur, z0, z1, tag):
    dur = round(dur * FPS) / FPS
    outdir = RUN / "media" / f"_bg_{tag}"
    if outdir.exists():
        import shutil; shutil.rmtree(outdir)
    outdir.mkdir(parents=True)
    plan = {
        "schema_version": 1, "backend": "affine",
        "output": {"width": W, "height": H, "fps": FPS},
        "transition_s": 0,
        "shots": [{"id": tag, "source": str(still), "duration_s": dur,
                   "start_view": [(1 - 1 / z0) / 2, (1 - 1 / z0) / 2, 1 / z0, 1 / z0],
                   "end_view": [(1 - 1 / z1) / 2, (1 - 1 / z1) / 2, 1 / z1, 1 / z1],
                   "curve": {"type": "linear"}}],
    }
    pp = outdir / "plan.json"
    pp.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, r"E:\program\1project\video\shared\camera-motion\camera_motion.py",
                        str(pp), "--out", str(outdir)], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[-800:])
    return outdir / f"{tag}.mp4"


def build_bg(meta):
    D = round(meta["intro_seconds"] * FPS) / FPS
    out = RUN / "media" / "bg.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    assets = CFG.get("intro_assets") or [{"path": CFG["intro_asset"],
                                          "zoom_start": CAM["zoom_start"],
                                          "zoom_end": CAM["zoom_end"]}]
    xf = float(CFG.get("bg_xfade_s", 0.8))
    segs = []
    for i, a in enumerate(assets):
        start = 0.0 if i == 0 else float(assets[i - 1].get("switch_s", 0.0))
        end = D if i == len(assets) - 1 else float(a.get("switch_s", D))
        dur = (end - start) + (xf if i < len(assets) - 1 else 0)
        segs.append(_render_bg_seg(EP / a["path"], dur,
                                   float(a.get("zoom_start", 1.0)),
                                   float(a.get("zoom_end", 1.1)), f"seg{i}"))
    if len(segs) == 1:
        subprocess.run([FF, "-y", "-i", str(segs[0]), "-c", "copy", str(out)],
                       check=True, capture_output=True)
        return out
    inputs = []
    for s in segs:
        inputs += ["-i", str(s)]
    if xf <= 0:
        # 硬切：两张图不做叠化，避免月亮/山脊重影
        fc = "".join(f"[{i}:v]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=0[bg]"
        r = subprocess.run([FF, "-y"] + inputs + ["-filter_complex", fc, "-map", "[bg]",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                            "-r", str(FPS), "-frames:v", str(round(D * FPS)), str(out)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError((r.stderr or r.stdout)[-800:])
        return out
    # 逐段 xfade；offset 为上一段内的时间点
    fc = ""
    prev = "[0:v]"
    for i in range(1, len(segs)):
        sw = float(assets[i].get("switch_s", D))
        lab = f"[v{i}]"
        fc += (f"{prev}[{i}:v]xfade=transition=fade:duration={xf}:offset={sw:.3f}{lab};")
        prev = lab
    fc += f"{prev}format=yuv420p[bg]"
    r = subprocess.run([FF, "-y"] + inputs + ["-filter_complex", fc, "-map", "[bg]",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                        "-r", str(FPS), "-frames:v", str(round(D * FPS)), str(out)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[-800:])
    return out


def render_intro(meta, cues):
    """背景 + 音轨 + ASS 矢量大字；不做逐帧位图缩放，避免边缘爬行/颤抖。"""
    D = round(meta["intro_seconds"] * FPS) / FPS
    bg = build_bg(meta)
    av = RUN / "intro_av.mp4"
    subprocess.run([FF, "-y", "-i", str(bg), "-i", str(RUN / "intro.wav"),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(av)],
                   check=True, capture_output=True)
    assdir = RUN / "preview" / "burn"
    (assdir / "fonts").mkdir(parents=True, exist_ok=True)
    for f in Path(r"E:\program\1project\video\assets\助眠解说\subtitles\style-r4\fonts").glob("*"):
        (assdir / "fonts" / f.name).write_bytes(f.read_bytes())
    for f in Path(r"E:\program\1project\video\assets\助眠解说\intro\fonts").glob("MaShanZheng*"):
        (assdir / "fonts" / f.name).write_bytes(f.read_bytes())
    ass = assdir / "hook.ass"
    write_hook_ass(meta, cues, ass)
    out = RUN / "intro_sub.mp4"
    burn(av, RUN / "intro.wav", ass, out)
    return out


SUBFONT = ImageFont.truetype(r"E:\program\1project\video\assets\助眠解说\subtitles\style-r4\fonts\SourceHanSansSC-Heavy.otf", 96)


def sub_br(text):
    if SUBFONT.getlength(text) <= 1560:
        return text
    marks = "，。；：、！？"
    mid = len(text) // 2
    cand = [i for i, ch in enumerate(text) if ch in marks and 4 <= i < len(text) - 4]
    if cand:
        i = min(cand, key=lambda x: abs(x - mid))
    else:
        i = mid
    left, right = text[:i + 1], text[i + 1:]
    if right and right[0] in "的地得了着过和与或而却":
        left, right = left + right[0], right[1:]
    return left + "\\N" + right


def write_hook_ass(meta, cues, path):
    hdr = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n"
        "WrapStyle: 2\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
        "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding\n"
        "Style: Big,Ma Shan Zheng,132,&H00E9F1F6,&H000000FF,&H00180F0A,"
        "&H80000000,0,0,0,0,100,100,0,0,1,5,2,5,0,0,0,1\n"
        "Style: Title,Ma Shan Zheng,450,&H00E9F1F6,&H000000FF,&H00180F0A,"
        "&H80000000,0,0,0,0,100,100,0,0,1,5,2,5,0,0,0,1\n"
        "Style: B,Source Han Sans SC Heavy,96,&H00FFFFFF,&H000000FF,&H00000000,"
        "&H80000000,0,0,0,0,100,100,0,0,1,5,2,2,96,96,118,1\n\n[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

    def at(t):
        h = int(t // 3600); m = int(t % 3600 // 60); s = int(t % 60)
        cs = int(round((t % 1) * 100))
        if cs == 100:
            s += 1; cs = 0
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    u = meta["units"]
    s1, e1 = VT["head_s"] - 0.10, u[1]["start_s"] - 0.30
    s2, e2 = u[1]["start_s"] - 0.10, u[2]["start_s"] - 0.35
    text1 = "".join(CFG["display_text_1"])
    text2 = "".join(CFG["display_text_2"])

    def anim(ss, ee, fs):
        ms = max(1, int(round((ee - ss) * 1000)))
        out0 = max(0, ms - 400)
        f0 = int(round(fs * T_ANIM["scale_start"]))
        fw = int(round(fs * T_ANIM.get("whoosh_scale", 1.18)))
        fe = int(round(fs * T_ANIM["scale_end"]))
        ws = int(round(T_ANIM.get("whoosh_s", 0.08) * 1000))
        st = int(round(T_ANIM.get("settle_s", 0.22) * 1000))
        return (f"{{\\fs{f0}\\an5\\move(960,548,960,540,0,{ms})"
                f"\\alpha&HFF&"
                f"\\t(0,{ws},\\fs{fw})"
                f"\\t(0,90,\\alpha&H00&)"
                f"\\t({ws},{ws + st},\\fs{fs})"
                f"\\t({ws + st},{ms},\\fs{fe})"
                f"\\t({out0},{ms},\\alpha&HFF&)}}")

    fs1 = int(CFG.get("font_size_1", CFG.get("font_size", 132)))
    fs2 = int(CFG.get("font_size_2", CFG.get("font_size", 132)))
    with path.open("w", encoding="utf-8") as f:
        f.write("\ufeff" + hdr)
        f.write(f"Dialogue: 0,{at(s1)},{at(e1)},Big,,0,0,0,,{anim(s1, e1, fs1)}{text1}\n")
        f.write(f"Dialogue: 0,{at(s2)},{at(e2)},Big,,0,0,0,,{anim(s2, e2, fs2)}{text2}\n")
        ct = CFG.get("center_title")
        if ct:
            ts = u[2]["start_s"] + float(CFG.get("center_title_delay_s", 0.15))
            cd = float(CFG.get("center_title_s", 3.2))
            ms = int(round(cd * 1000))
            f.write(f"Dialogue: 0,{at(ts)},{at(ts + cd)},Title,,0,0,0,,"
                    f"{{\\an5\\pos(960,540)\\alpha&HFF&"
                    f"\\t(0,450,\\alpha&H00&)\\t({max(0, ms - 400)},{ms},\\alpha&HFF&)}}{ct}\n")
        for c in cues:
            f.write(f"Dialogue: 0,{at(c['start_s'])},{at(c['end_s'])},B,,0,0,0,,{sub_br(c['text'])}\n")


def write_ass(cues, path, intro_offset=0.0):
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

    def at(t):
        h = int(t // 3600); m = int(t % 3600 // 60); s = int(t % 60); cs = int(round((t % 1) * 100))
        if cs == 100: s += 1; cs = 0
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    with path.open("w", encoding="utf-8") as f:
        f.write("\ufeff" + hdr)
        for c in cues:
            f.write(f"Dialogue: 0,{at(c['start_s'] + intro_offset)},{at(c['end_s'] + intro_offset)},B,,0,0,0,,{sub_br(c['text'])}\n")


def burn(video, audio, ass, out):
    r = subprocess.run([FF, "-y", "-i", str(video), "-i", str(audio),
                        "-vf", f"subtitles={ass.name}:fontsdir=fonts",
                        "-map", "0:v", "-map", "1:a",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", str(out)],
                       capture_output=True, text=True, cwd=str(ass.parent))
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "")[-800:])


def main():
    pcm = process_audio()
    meta = build_audio(pcm)
    if isinstance(CFG.get("intro_duration"), (int, float)):
        meta["intro_seconds"] = float(CFG["intro_duration"])
    D = round(meta["intro_seconds"] * FPS) / FPS
    meta["intro_seconds"] = D
    log("intro", D)
    cues = transition_cues(meta)
    (RUN / "transition_cues.json").write_text(json.dumps(cues, ensure_ascii=False, indent=1),
                                              encoding="utf-8")
    intro_sub = render_intro(meta, cues)
    # A: 现有成片 30s
    subprocess.run([FF, "-y", "-t", "30", "-i", str(EP / "video/final/glacier-river_sub.mp4"),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    str(RUN / "preview" / "A_current_30s.mp4")], check=True, capture_output=True)
    # B 30s
    subprocess.run([FF, "-y", "-t", "30", "-i", str(intro_sub),
                    "-c", "copy", str(RUN / "preview" / "B_hook_30s.mp4")],
                   check=True, capture_output=True)
    # B long: intro + body，0.5s 叠化进入正文
    body_start = 10.59
    XF = 0.5
    body_len = 10.5
    body = EP / "video/final/glacier-river_clean.mp4"
    body_seg = RUN / "preview" / "body10.mp4"
    subprocess.run([FF, "-y", "-ss", str(body_start), "-t", str(body_len), "-i", str(body),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p", str(body_seg)], check=True, capture_output=True)
    body_aud = RUN / "preview" / "body10.wav"
    subprocess.run([FF, "-y", "-ss", str(body_start + XF), "-t", "10.0",
                    "-i", str(EP / "video/final/glacier-river_narration.wav"),
                    "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "1", str(body_aud)],
                   check=True, capture_output=True)
    joined = RUN / "preview" / "B_long_video.mp4"
    subprocess.run([FF, "-y", "-i", str(RUN / "intro_av.mp4"), "-i", str(body_seg),
                    "-filter_complex", f"[0:v][1:v]xfade=transition=fade:duration={XF}:offset={D - XF}[v]",
                    "-map", "[v]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p", str(joined)], check=True, capture_output=True)
    # 合并音轨（正文音轨跳过叠化吃掉的 0.5s）
    aud_list = RUN / "preview" / "aud.txt"
    aud_list.write_text(f"file '{RUN/'intro.wav'}'\nfile '{body_aud}'\n", encoding="utf-8")
    joined_wav = RUN / "preview" / "B_long.wav"
    subprocess.run([FF, "-y", "-f", "concat", "-safe", "0", "-i", str(aud_list),
                    "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "1", str(joined_wav)],
                   check=True, capture_output=True)
    # 合并 ASS：过渡 + 正文（body 绝对时间 - (10.59+XF) + D）
    body_ass = RUN / "preview" / "body_shift.ass"
    src = Path(r"E:\program\1project\video\4\runs\20261103-gla-b01\subtitles\gate1\fixed.ass")
    shift = D - (body_start + XF)
    lines = []
    for ln in src.read_text(encoding="utf-8-sig").splitlines():
        if not ln.startswith("Dialogue:"):
            continue
        p = ln.split(",", 9)

        def t2s(t):
            h, m, rest = t.split(":"); s, cs = rest.split(".")
            return int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100

        def s2t(t):
            t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = int(t % 60)
            cs = int(round((t % 1) * 100))
            if cs == 100: s += 1; cs = 0
            return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
        p[1], p[2] = s2t(t2s(p[1]) + shift), s2t(t2s(p[2]) + shift)
        lines.append(",".join(p))
    hdr = src.read_text(encoding="utf-8-sig").split("[Events]")[0] + "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    body_ass.write_text("\ufeff" + hdr + "\n".join(lines), encoding="utf-8")
    # 合并 ASS：hook（Big/Title/B 样式）+ 正文（已平移）
    hook_ass = RUN / "preview" / "burn" / "hook.ass"
    hook_txt = hook_ass.read_text(encoding="utf-8-sig")
    merged_hdr = hook_txt.split("[Events]")[0] + "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    all_lines = [l for l in hook_txt.splitlines() if l.startswith("Dialogue:")]
    all_lines += [l for l in body_ass.read_text(encoding="utf-8-sig").splitlines() if l.startswith("Dialogue:")]
    merged = RUN / "preview" / "burn" / "merged.ass"
    merged.write_text("\ufeff" + merged_hdr + "\n".join(all_lines), encoding="utf-8")
    burn(joined, joined_wav, merged, RUN / "preview" / "B_long_45s.mp4")
    log("done", RUN / "preview")


if __name__ == "__main__":
    main()
