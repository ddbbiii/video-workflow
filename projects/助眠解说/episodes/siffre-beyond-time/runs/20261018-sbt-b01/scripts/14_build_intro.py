# -*- coding: utf-8 -*-
"""片头视觉构建 v4.4 工艺(intro-node.md; sleep-aid-intro skill v4.4,两型通用)。

siffre-beyond-time 片头 v4 为**快钩·标准四段**(2026-10-20 用户否决 v3 紧凑版
"钩子缺语境",剧本侧改回约 20s 快钩四段文案;实测音轨 23.825s,超快钩 20s 上限
3.8s —— 文案用户锁定不改字,newton v4.4 先例 21.562s 同型交付,本版按 26s 硬门
+WARN>20s 记录偏差待用户复核)。背景池从正文已验收池按语义选取,段落数以
intro_timeline.json 为准(v4 文案 3 段)。

v4.4 工艺要点(与 newton 批次一致):
- 常显文字轨道:文字全程在场,逗号级分卡,卡间 0.35s 交叉淡变,仅片首/片尾 0.6s 淡入出;
- 背景 0.45s 叠化精确落在句间停顿(上句语音结束+0.04s 起,下句开口前≥0.07s 完成),
  朗读期间零切画;最终主题句画面驻留至片尾;
- 两层架构:背景 xfade 串接 → 标题全局时间轴 overlay;-frames:v 锁帧数。

v4 本集升级(2026-10-20 v4 任务书第 4 条 a/b):
a. 卡面文字加轻微压暗衬底:全局静态 scrim(中心加权柔边暗色渐变,峰值 ~30% 不透明度),
   叠在背景之上、文字层之下,全程恒定无动效(不违反静态字规则;不做进卡 PNG 是为避免
   交叉淡变中双 scrim 叠加产生明暗脉动 —— v4.3 教训);
b. (v5 已废弃)末卡曾改《超出时间》标题卡 —— 用户 2026-10-20 v5 复核要求去掉:平台封面
   用户自制,视频内不需要标题定妆卡。

v5 重制(2026-10-20 晚三,本版):
- **片头全程统一分句文字卡、风格连贯**:末段不再使用《超出时间》标题卡,交棒句的最后
  子句(卡 6"讲讲这两个月，和你身体里——那只看不见的钟")用与其他卡完全一致的
  分句文字卡(MaShanZheng 同字号体系 title_layout:21 字 -> 两行 fs=123),该卡时间窗
  与 v4 逐点一致(淡入起 18.263s 落句间停顿内),驻留至片尾零切换,背景仍为 c8-s04
  深蓝一点暖光(与 v4 相同,末次叠化 16.132-16.582 后零切换)。
- **音轨/intro_timeline/切卡/scrim 全部复用 v4**(intro_cards.json 不变,chapters/intro.wav
  不变);片头总时长与 v4 逐帧一致(715f=23.833s,音轨 23.825s)。

移植自 newton 14_build_intro.py(v3 批次基础上升级 v4 -> v5:sbt r5 去标题卡)。
"""
from __future__ import annotations
import json, shutil, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\siffre-beyond-time")
RUN = EP / "runs" / "20261018-sbt-b01"
AFF = RUN / "media" / "affine"          # image_camera_motion 运镜池(优先)
SHOT = RUN / "media" / "shot"           # i2v 镜头池(intro-node §3:图生视频亦可)
CARDS = RUN / "intro_cards.json"
INTRO_TL = RUN / "intro_timeline.json"
OUT = RUN / "intro" / "batch-20261020-v5"
FONT = Path(r"E:\program\1project\video\assets\助眠解说\intro\fonts\MaShanZheng-Regular.ttf")
FFMPEG = r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"
FFPROBE = FFMPEG.replace("ffmpeg.exe", "ffprobe.exe")
FPS = 30
XFADE = 0.45            # 背景叠化时长(必须整体落在句间停顿内)
GAP_LEAD = 0.04         # 上一句语音结束后多少秒开始叠化
SWAP = 0.35             # 文字交叉淡变时长
EDGE = 0.60             # 片首淡入 / 片尾淡出时长
W, H = 1920, 1080
SAFE_W = 1728           # 1920 - 2*96 安全区宽度

# v4 本集升级 b:(v5 废弃)《超出时间》标题卡 —— 用户要求去掉,视频内不留标题定妆卡,
# 封面归用户自制;末卡回归与其他卡一致的分句文字卡(MaShanZheng 同字号体系)。
TITLE_CARD_TEXT = None        # v5:None = 不启用标题卡,末卡走 title_layout 常规分句渲染
TITLE_FS_MAX = 430      # (弃用)v4 标题卡字号上限
# v4 本集升级 a:全局静态 scrim(压暗衬底)参数
SCRIM_RGB = (10, 16, 24)     # 深蓝黑,与主字描边同族,压暗不带色偏
SCRIM_PEAK = 0.30            # 峰值不透明度 30%(任务书 25-35% 区间中值)
SCRIM_SIG_Y = 270            # 垂直高斯 σ(盖住单行/两行/标题卡文字块)
SCRIM_SIG_X = 780            # 水平高斯 σ(柔边,中心聚焦)

# 每句(=每个 intro 段落)一个背景,按段落顺序。2026-10-20 v4 选片(v4 任务书
# 语义建议 + 时长可行性裁决;均为正文 v3 已验收池,无相邻重复):
#   p01 "一九六二年…一住两个月"  -> brg-s01 (i2v,冰川洞内暖黄营地灯;住进黑暗两个月
#                       最强语义;24.6s 需求 ~10.1s 可行)【任务书指定】
#   p02 "出来那天…已经是九月"    -> c1-s08 (affine,母题①手表:表被留在石块上、人影
#                       远走 —— 时间意象;9.2s 需求 ~6.9s 可行)。任务书原指定
#                       c1-s06(摘表特写)实测仅 3.27s < 需求 6.9s,按 v2 先例
#                       (c10-s01/s02 短于渲染需求改同族镜头)换同母题①最长镜 c1-s08。
#   p03 交棒句"接下来的三十五分钟…" -> c8-s04 (affine,超现实深蓝近黑空间中央一点
#                       暖光 ="你身体里那只看不见的钟"直接意象,深暗底衬末卡文字;
#                       16.8s 需求 ~7.7s 可行)作末卡底,驻留至片尾(v5 末卡=分句文字卡)。
#                       (任务书另一候选 ep-s05 卧室一线微光 10.7s 亦可,留备选;
#                        c8-s04 与末句"看不见的钟"语义对位更强、标题对比度更好)
PARA_BG = {
    "intro-p01": "brg-s01",
    "intro-p02": "c1-s08",
    "intro-p03": "c8-s04",
}


def probe_dur(p):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return float(r.stdout.strip())


def split_two_lines(text):
    if "，" in text:
        i = text.index("，")
        l1, l2 = text[:i], text[i + 1:]
        if l1 and l2:
            return l1, l2
    n = len(text)
    k = (n + 1) // 2
    return text[:k], text[k:]


def title_layout(text):
    n = len(text)
    fs1 = min(150, SAFE_W // n)
    if fs1 >= 112:
        return [text], fs1
    l1, l2 = split_two_lines(text)
    fs2 = min(140, SAFE_W // max(len(l1), len(l2)))
    return [l1, l2], max(fs2, 96)


def render_title_png(text, out_path, title_card=False):
    """title_card=True:《超出时间》标题卡 —— 单行横排,安全区内尽量大。"""
    if title_card:
        fs = TITLE_FS_MAX
        font = ImageFont.truetype(str(FONT), fs)
        d0 = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
        bb = d0.textbbox((0, 0), text, font=font)
        tw = bb[2] - bb[0]
        if tw > SAFE_W - 48:                       # 超安全区则按比例缩到贴合
            fs = int(fs * (SAFE_W - 48) / tw)
            font = ImageFont.truetype(str(FONT), fs)
            bb = d0.textbbox((0, 0), text, font=font)
        lines, fs_final = [text], fs
    else:
        lines, fs_final = title_layout(text)
        fs = fs_final
        font = ImageFont.truetype(str(FONT), fs)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    gap = int(fs * 0.30)
    boxes = []
    for ln in lines:
        bb = d.textbbox((0, 0), ln, font=font)
        boxes.append((bb[2] - bb[0], bb[3] - bb[1], bb))
    total_h = sum(b[1] for b in boxes) + gap * (len(lines) - 1)
    y = (H - total_h) // 2
    stroke = (10, 16, 24, 235)
    warm = (245, 240, 232, 255)
    r = max(3, fs // 50)
    for ln, (tw, th, bb) in zip(lines, boxes):
        x = (W - tw) // 2 - bb[0]
        yy = y - bb[1]
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r:
                    d.text((x + dx, yy + dy), ln, font=font, fill=stroke)
        d.text((x, yy), ln, font=font, fill=warm)
        y += th + gap
    img.save(str(out_path))
    return lines, fs_final


def build_scrim_png(out_path):
    """全局静态压暗衬底:中心加权椭圆高斯,峰值 SCRIM_PEAK,柔边渐隐。
    全程恒定(无淡变无动效)→ 不与交叉淡变叠加产生明暗脉动(v4.3 教训)。"""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    gy = np.exp(-((yy - H / 2) / SCRIM_SIG_Y) ** 2)
    gx = np.exp(-((xx - W / 2) / SCRIM_SIG_X) ** 2)
    alpha = np.clip(SCRIM_PEAK * gy * gx, 0, 1)
    a8 = (alpha * 255).astype(np.uint8)
    img = np.zeros((H, W, 4), dtype=np.uint8)
    img[..., 0], img[..., 1], img[..., 2] = SCRIM_RGB
    img[..., 3] = a8
    Image.fromarray(img, "RGBA").save(str(out_path))
    return float(alpha.max()), float(alpha[H // 2, W // 2])


def build_bg(src_video, render_dur, out):
    frames = max(2, int(round(render_dur * FPS)))
    cmd = [FFMPEG, "-y", "-i", str(src_video),
           "-vf", (f"trim=duration={render_dur:.3f},setpts=PTS-STARTPTS,"
                   f"scale=1920:1080:force_original_aspect_ratio=increase,"
                   f"crop=1920:1080,fps={FPS},format=yuv420p"),
           "-frames:v", str(frames), "-r", str(FPS),
           "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"bg {out.name}: {(r.stderr or '')[-600:]}")


def main():
    if not PARA_BG:
        raise SystemExit("PARA_BG 为空:待正文视频池(media/affine)验收后,按慢钩型规则"
                         "逐段选取背景镜头并填写本脚本 PARA_BG。")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "gate").mkdir(exist_ok=True)
    cards = json.loads(CARDS.read_text(encoding="utf-8"))["cards"]
    intro_tl = json.loads(INTRO_TL.read_text(encoding="utf-8"))
    audio_s = intro_tl["intro_seconds"]
    if audio_s > 26.0:
        raise SystemExit(f"硬门 26s 超时: {audio_s:.2f}s(v4 快钩文案锁定;newton 先例 21.56s)")
    if audio_s > 20.0:
        print(f"WARN: 音轨 {audio_s:.3f}s 超快钩型 20s 上限 "
              f"({audio_s - 20.0:+.1f}s) —— v4 文案用户锁定不改字,"
              f"按 newton 21.56s 先例交付,偏差记录 manifest/REPORT 待用户复核")
    n_frames = round(audio_s * FPS)
    TOTAL = n_frames / FPS
    have = {p.stem: p for p in list(AFF.glob("*.mp4")) + list(SHOT.glob("*.mp4"))}
    print(f"intro audio {audio_s:.3f}s -> video TOTAL {TOTAL:.3f}s ({n_frames}f), "
          f"{len(cards)} cards")

    # 1. 常显文字窗口:卡 i 从(语音起点-0.10)显示到下一卡窗口起点;尾卡到片尾
    ws = [max(0.0, c["start_s"] - 0.10) for c in cards]
    we = ws[1:] + [min(cards[-1]["end_s"] + 0.25, TOTAL)]

    # 2. 背景按段落(句)分组;叠化时刻=上一句末卡语音结束+GAP_LEAD
    paras = []
    for i, c in enumerate(cards):
        pid = c["para"].rsplit("-u", 1)[0]      # intro-p01-u01 -> intro-p01
        if i == 0 or pid != cards[i - 1]["para"].rsplit("-u", 1)[0]:
            paras.append({"para": pid, "start_idx": i, "end_idx": i})
        paras[-1]["end_idx"] = i
    # T_j: 第 j 段背景的开始时刻(也是第 j 次叠化的启动点);T_0=0
    # XF_j: 第 j 次叠化时长(启动于 T[j]);停顿不足 0.55s 时缩短叠化而不是压语音
    #       (v4.4 规则;newton 实测 FunASR 字界给出的实际停顿 > 窗口间 0.4245s,
    #        通常全额 0.45s 可容纳,这里保留自适应兜底)
    T = [0.0]
    XF = [0.0]
    for j in range(1, len(paras)):
        prev_end = cards[paras[j - 1]["end_idx"]]["end_s"]
        nxt_start = cards[paras[j]["start_idx"]]["start_s"]
        t = prev_end + GAP_LEAD
        room = (nxt_start - 0.03) - t
        assert room >= 0.15, \
            f"句间停顿不足以容纳叠化: {prev_end:.2f}-{nxt_start:.2f}"
        if room < XFADE:
            print(f"WARN: 句{j} 停顿仅容 {room:.2f}s 叠化(标准 {XFADE}s),按 v4.4 缩短")
        T.append(round(t, 3))
        XF.append(round(min(XFADE, room), 3))
    T.append(TOTAL)
    print("bg timeline:", [(paras[j]["para"], round(T[j], 2)) for j in range(len(paras))],
          "| blends:", [(round(T[j], 2), round(T[j] + XF[j], 2)) for j in range(1, len(paras))])

    # 3. 渲染背景段(每句一个):段 j 覆盖输出 [T[j], T[j+1]+XF[j+1]],末段到 TOTAL
    seg_paths = []
    for j, p in enumerate(paras):
        bg_key = PARA_BG.get(p["para"])
        if bg_key is None:
            raise SystemExit(f"PARA_BG 缺少 {p['para']} 的背景镜头映射")
        if bg_key not in have:
            raise FileNotFoundError(f"bg pool missing: {bg_key}.mp4")
        render_dur = (T[j + 1] - T[j]) + (XF[j + 1] if j < len(paras) - 1 else 0)
        bg_dur = probe_dur(have[bg_key])
        assert bg_dur >= render_dur + 0.05, \
            f"bg {bg_key} {bg_dur:.1f}s < need {render_dur:.1f}s (sentence {j})"
        seg_mp4 = OUT / f"bg{j}.mp4"
        build_bg(have[bg_key], render_dur, seg_mp4)
        seg_paths.append(seg_mp4)
        print(f"  bg{j} [{T[j]:.2f}-{T[j+1]:.2f}] {bg_key} render={render_dur:.2f}s")

    # 4. 第一层:背景 xfade 串接(叠化启动点=T[j],整体落在句间停顿内)
    inputs = []
    for s in seg_paths:
        inputs += ["-i", str(s)]
    fc = ""
    prev = "[0:v]"
    for j in range(1, len(seg_paths)):
        lab = f"[v{j}]"
        fc += (f"{prev}[{j}:v]xfade=transition=fade:duration={XF[j]}"
               f":offset={round(T[j], 3)}{lab};")
        prev = lab
    fc += f"{prev}format=yuv420p[bgbase]"
    bg_base = OUT / "bg_base.mp4"
    r = subprocess.run([FFMPEG, "-y"] + inputs + ["-filter_complex", fc,
                       "-map", "[bgbase]", "-c:v", "libx264", "-preset", "medium",
                       "-crf", "20", "-r", str(FPS),
                       "-frames:v", str(n_frames), str(bg_base)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("FAIL bg xfade:", (r.stderr or "")[-800:])
        return 1
    print(f"bg_base.mp4 {probe_dur(bg_base):.3f}s")

    # 5. 第二层:常显标题轨道(全局时间轴,交叉淡变)
    # v2 修正(v1 缺陷:换卡边界"先出后进"相邻不重叠,暗背景下出现 ~0.3s 近无字谷,
    #   违反 v4.4 规格"上出下入同时进行";newton 因背景亮+0.5s 步进未暴露):
    #   i>0 的淡入提前到 ws[i]-SWAP,与上一卡淡出同时起止,总字量恒定无脉动。
    # v4 升级 a:先叠全局静态 scrim(背景之上、文字之下,恒定无动效;不进卡 PNG,
    #   避免交叉淡变中双 scrim 叠加的明暗脉动)。
    # v4 升级 b:末卡 = 《超出时间》标题卡(大字替换末子句文本,时间窗不变)。
    scrim_peak, scrim_center = build_scrim_png(OUT / "scrim.png")
    print(f"scrim.png built: peak {scrim_peak:.2f} center {scrim_center:.2f} "
          f"rgb {SCRIM_RGB} sig ({SCRIM_SIG_X},{SCRIM_SIG_Y})")
    inputs = ["-i", str(bg_base),
              "-loop", "1", "-i", str(OUT / "scrim.png")]
    for i in range(len(cards)):
        inputs += ["-loop", "1", "-i", str(OUT / f"title_{i:02d}.png")]
    layout_log = []
    fc = ""
    fc += "[1:v]fps=30,format=rgba[scrim];"
    fc += "[0:v][scrim]overlay=0:0[o_s];"
    prev = "[o_s]"
    # v5 升级:末卡不再启用标题卡(TITLE_CARD_TEXT=None),全部 7 卡统一分句文字卡,
    # 同字号体系(MaShanZheng title_layout),风格全程连贯;末卡时间窗与 v4 一致。
    for i, c in enumerate(cards):
        is_title = bool(TITLE_CARD_TEXT) and i == len(cards) - 1
        disp = TITLE_CARD_TEXT if is_title else c["text"]
        lines, fs = render_title_png(disp, OUT / f"title_{i:02d}.png",
                                     title_card=is_title)
        d_in = EDGE if i == 0 else SWAP
        d_out = EDGE if i == len(cards) - 1 else SWAP
        st_in = ws[i] if i == 0 else ws[i] - SWAP      # 与上卡淡出同时启动
        st_out = we[i] - d_out
        lab_out = f"[t{i}]"
        fc += (f"[{i + 2}:v]fps={FPS},format=rgba,"
               f"fade=t=in:st={st_in:.3f}:d={d_in:.3f}:alpha=1,"
               f"fade=t=out:st={st_out:.3f}:d={d_out:.3f}:alpha=1{lab_out};"
               f"{prev}{lab_out}overlay=x='(W-w)/2':y='(H-h)/2'"
               f":enable='between(t,{st_in - 0.05:.3f},{we[i] + 0.05:.3f})'[o{i}];")
        prev = f"[o{i}]"
        layout_log.append(dict(idx=i, text=disp,
                               clause_text=c["text"] if is_title else None,
                               title_card=is_title, fontsize=fs, lines=lines,
                               window=[round(st_in, 3), round(we[i], 3)],
                               swap=[round(st_out, 3), round(st_out + d_out, 3)]))
    fc += f"{prev}format=yuv420p[vout]"
    final = OUT / "clean-intro.mp4"
    r = subprocess.run([FFMPEG, "-y"] + inputs + ["-filter_complex", fc,
                       "-map", "[vout]", "-c:v", "libx264", "-preset", "medium",
                       "-crf", "20", "-r", str(FPS),
                       "-frames:v", str(n_frames), str(final)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("FAIL title overlay:", (r.stderr or "")[-800:])
        return 1
    print(f"OK clean-intro.mp4 {probe_dur(final):.3f}s -> {final}")

    # 6. 批次产物
    (OUT / "timeline.json").write_text(json.dumps({
        "total_s": TOTAL, "audio_s": audio_s, "cards": layout_log,
        "cards_source": str(CARDS),
        "text_track": "persistent; swap crossfade 0.35s; edge fades 0.6s",
        "scrim": {"static": True, "peak_alpha": round(scrim_peak, 3),
                  "center_alpha": round(scrim_center, 3), "rgb": list(SCRIM_RGB),
                  "sigma": [SCRIM_SIG_X, SCRIM_SIG_Y],
                  "note": "全局恒定层,背景上文字下,无淡变无动效"},
        "title_card": {"enabled": False, "text": None,
                       "replaces_clause": None, "dwell_to_end": True,
                       "note": "v5 废弃《超出时间》标题卡(用户自制平台封面);末卡=交棒句"
                               "末子句分句文字卡,同字号体系,驻留至片尾零切换;"
                               "v4 记录见 batch-20261020-v4/timeline.json"},
        "bg_timeline": {"T": [round(t, 3) for t in T], "xfade_s": XF[1:],
                        "blends": [[round(T[j], 3), round(T[j] + XF[j], 3), XF[j]]
                                   for j in range(1, len(paras))]}},
        ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "manifest.json").write_text(json.dumps({
        "version": "v5-unified-clause-endcard-sbt-r5", "created": "2026-10-20",
        "intro_type": "fast-hook standard (快钩·标准四段;文案锁定实测 23.825s,"
                      "超快钩 20s 上限 +3.8s,newton 21.562s 先例,待用户复核)",
        "r5_change": "去掉片尾《超出时间》标题大字卡(用户自制平台封面,视频内不留标题"
                     "定妆卡)——片头全程统一分句文字卡、风格连贯:末卡回归交棒句末子句"
                     "文本(MaShanZheng 同字号体系 title_layout,21 字两行 fs=123),"
                     "时间窗与 v4 逐点一致,驻留至片尾零切换;背景 c8-s04 深蓝一点暖光"
                     "沿用;音轨/intro_timeline/切卡/scrim 全部复用 v4,时长逐帧一致"
                     "(715f=23.833s)",
        "design": ("常显文字轨道(交叉淡变 0.35s,片首/片尾 0.6s);"
                    "背景 0.45s 叠化精确置于句间停顿(上句语音结束+0.04s 起,"
                    "下句开口前≥0.07s 完成),朗读期间零切画;"
                    "最终主题句画面从停顿处驻留至片尾;"
                    "静态居中字(用户覆盖 intro-node 缩放默认项);"
                    "v5:全 7 卡统一分句文字卡,无标题卡"),
        "font": str(FONT), "xfade_s": XFADE, "swap_s": SWAP,
        "bg_pool": "runs/20261018-sbt-b01/media/{affine,shot} (正文 v3 已验收池;affine=image_camera_motion 优先,brg-s01=i2v)",
        "bg_by_para": PARA_BG,
        "bg_notes": "任务书原指定 p02=c1-s06(摘表特写)实测 3.27s<需求 6.9s,"
                    "按 v2 短镜换同族先例改同母题① c1-s08(表被留在地上 9.2s);"
                    "p03 两候选(c8-s04/ep-s05)取 c8-s04:末句'看不见的钟'语义对位"
                    "+深暗底衬末卡文字(v5 起末卡为分句文字卡)",
        "cards": [{"idx": l["idx"], "text": l["text"], "window_s": l["window"],
                   "title_card": l.get("title_card", False)}
                  for l in layout_log]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.copy(RUN / "chapters" / "intro.wav", OUT / "narration.wav")

    # 7. QA:逐卡中点 + 常显连续性(1.0s→TOTAL-0.7s 之间任何帧中央都应有字)
    qa = ["# intro batch QA (v4.4 persistent text)", "",
          "| idx | mid_s | text% | ok |", "|---|---|---|---|"]
    fails = []
    for i, c in enumerate(cards):
        mid = (ws[i] + we[i]) / 2
        qf = OUT / "gate" / f"card_{i:02d}.jpg"
        subprocess.run([FFMPEG, "-y", "-ss", f"{mid:.2f}", "-i", str(final),
                        "-frames:v", "1", "-q:v", "3", str(qf)], capture_output=True)
        im = Image.open(qf).convert("RGB")
        w, h = im.size
        box = im.crop((int(w * 0.15), int(h * 0.25), int(w * 0.85), int(h * 0.75)))
        px = list(box.getdata())
        bright = sum(1 for r, g, b in px if r > 225 and g > 218 and b > 205) / len(px)
        ok = bright >= 0.015
        if not ok:
            fails.append(i)
        disp = c["text"]                    # v5:无标题卡,显示文本=分句原文
        qa.append(f"| {i} | {mid:.2f} | {bright*100:.2f} | {'OK' if ok else 'FAIL'} |"
                  f" {disp}{'【末卡·分句文字】' if i == len(cards) - 1 else ''} |")
    # 连续性:淡变期间两卡各半透明,阈值放低
    blanks = []
    t = 1.0
    while t < TOTAL - 0.7:
        qf = OUT / "gate" / "cont_probe.jpg"
        subprocess.run([FFMPEG, "-y", "-ss", f"{t:.2f}", "-i", str(final),
                        "-frames:v", "1", "-q:v", "3", str(qf)], capture_output=True)
        im = Image.open(qf).convert("RGB")
        w, h = im.size
        box = im.crop((int(w * 0.15), int(h * 0.28), int(w * 0.85), int(h * 0.72)))
        px = list(box.getdata())
        lit = sum(1 for r, g, b in px if r > 150 and g > 145 and b > 135)
        if lit < 60:
            blanks.append(round(t, 2))
        t += 0.5
    if blanks:
        fails.append(f"blank frames: {blanks}")
    qa += ["", f"card fails: {[f for f in fails if isinstance(f, int)]}",
           f"continuity blanks: {blanks if blanks else 'none'}",
           f"duration: {probe_dur(final):.3f}s (target {TOTAL})"]
    (OUT / "gate" / "qa_report.md").write_text("\n".join(qa), encoding="utf-8")
    print(f"QA: {'ALL OK' if not fails else 'FAILS ' + str(fails)} -> gate/qa_report.md")
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
