# -*- coding: utf-8 -*-
"""片头视觉构建 v4.4(intro-node.md §3,用户 2026-10-18 定稿方向)。

v4.3→v4.4 变更(用户:"一段话还没结束就切画面;最终主题时画面停留久一点"):
- 背景叠化从"边界-1s 启动"(吃掉每句末尾 ~0.5s 朗读)改为 **0.45s 叠化精确
  放在句间停顿内**:上一句语音结束 +0.04s 启动,下一句开口前 ≥0.07s 完成。
- 最终主题句(p04)的单线散星河画面从停顿处一直停留到片尾,读主题期间零切换。

v4.3 设计(保留):常显文字轨道——文字全程在场,分句边界 0.35s 交叉淡变,
仅片首/片尾各一次 0.6s 真淡入/淡出;逗号级 8 卡;背景按句切换。

两层架构:背景 xfade 串接 → 标题全局时间轴 overlay。
编码注意:输出帧数用 -frames:v 精确锁定(-t 在帧边界会多收一帧)。
批次目录:intro/batch-20261018-short/(manifest 版本号区分)。
"""
from __future__ import annotations
import json, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\newton-to-chaos")
RUN = EP / "runs" / "20261014-ntc-b01"
AFF = RUN / "media" / "affine"
CARDS = RUN / "intro_cards.json"
INTRO_TL = RUN / "intro_timeline.json"
OUT = RUN / "intro" / "batch-20261018-short"
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

# 每句(=每个 intro 段落)一个背景,按段落顺序
PARA_BG = {
    "intro-p01": "ch05-p20-s01",   # 问句 —— 光带束于半透明边界(预测视界)
    "intro-p02": "ch05-p16-s01",   # 牛顿成功 —— 太阳系全景轨道
    "intro-p03": "ch03-p06-s01",   # 三体崩塌 —— 碎裂的椭圆光环
    "intro-p04": "ch08-p03-s01",   # 交棒 —— 单线光束散成多轨迹星河
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


def render_title_png(text, out_path):
    lines, fs = title_layout(text)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(FONT), fs)
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
    return lines, fs


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
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "gate").mkdir(exist_ok=True)
    cards = json.loads(CARDS.read_text(encoding="utf-8"))["cards"]
    intro_tl = json.loads(INTRO_TL.read_text(encoding="utf-8"))
    audio_s = intro_tl["intro_seconds"]
    n_frames = round(audio_s * FPS)
    TOTAL = n_frames / FPS
    have = {p.stem: p for p in AFF.glob("*.mp4")}
    print(f"intro audio {audio_s:.3f}s -> video TOTAL {TOTAL:.3f}s ({n_frames}f), "
          f"{len(cards)} cards")

    # 1. 常显文字窗口:卡 i 从(语音起点-0.10)显示到下一卡窗口起点;尾卡到片尾
    ws = [max(0.0, c["start_s"] - 0.10) for c in cards]
    we = ws[1:] + [min(cards[-1]["end_s"] + 0.25, TOTAL)]

    # 2. 背景按段落(句)分组;叠化时刻=上一句末卡语音结束+GAP_LEAD,
    #    确保叠化整体落在句间停顿内,不压到任何一句的朗读
    paras = []
    for i, c in enumerate(cards):
        pid = c["para"].rsplit("-u", 1)[0]      # intro-p01-u01 -> intro-p01
        if i == 0 or pid != cards[i - 1]["para"].rsplit("-u", 1)[0]:
            paras.append({"para": pid, "start_idx": i, "end_idx": i})
        paras[-1]["end_idx"] = i
    # T_j: 第 j 段背景的开始时刻(也是第 j 次叠化的启动点);T_0=0
    T = [0.0]
    for j in range(1, len(paras)):
        prev_end = cards[paras[j - 1]["end_idx"]]["end_s"]
        nxt_start = cards[paras[j]["start_idx"]]["start_s"]
        t = prev_end + GAP_LEAD
        assert t + XFADE <= nxt_start - 0.03, \
            f"句间停顿不足以容纳叠化: {prev_end:.2f}-{nxt_start:.2f}"
        T.append(round(t, 3))
    T.append(TOTAL)
    print("bg timeline:", [(paras[j]["para"], round(T[j], 2)) for j in range(len(paras))],
          "| blends:", [(round(T[j], 2), round(T[j] + XFADE, 2)) for j in range(1, len(paras))])

    # 3. 渲染背景段(每句一个):段 j 覆盖输出 [T[j], T[j+1]+XFADE],末段到 TOTAL
    seg_paths = []
    for j, p in enumerate(paras):
        bg_key = PARA_BG[p["para"]]
        if bg_key not in have:
            raise FileNotFoundError(f"affine bg missing: {bg_key}.mp4")
        render_dur = (T[j + 1] - T[j]) + (XFADE if j < len(paras) - 1 else 0)
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
        fc += (f"{prev}[{j}:v]xfade=transition=fade:duration={XFADE}"
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
    inputs = ["-i", str(bg_base)]
    for i in range(len(cards)):
        inputs += ["-loop", "1", "-i", str(OUT / f"title_{i:02d}.png")]
    layout_log = []
    fc = ""
    prev = "[0:v]"
    for i, c in enumerate(cards):
        lines, fs = render_title_png(c["text"], OUT / f"title_{i:02d}.png")
        d_in = EDGE if i == 0 else SWAP
        d_out = EDGE if i == len(cards) - 1 else SWAP
        st_out = we[i] - d_out
        lab_out = f"[t{i}]"
        fc += (f"[{i + 1}:v]fps={FPS},format=rgba,"
               f"fade=t=in:st={ws[i]:.3f}:d={d_in:.3f}:alpha=1,"
               f"fade=t=out:st={st_out:.3f}:d={d_out:.3f}:alpha=1{lab_out};"
               f"{prev}{lab_out}overlay=x='(W-w)/2':y='(H-h)/2'"
               f":enable='between(t,{ws[i] - 0.05:.3f},{we[i] + 0.05:.3f})'[o{i}];")
        prev = f"[o{i}]"
        layout_log.append(dict(idx=i, text=c["text"], fontsize=fs, lines=lines,
                               window=[round(ws[i], 3), round(we[i], 3)],
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
        "bg_timeline": {"T": [round(t, 3) for t in T], "xfade_s": XFADE,
                        "blends": [[round(T[j], 3), round(T[j] + XFADE, 3)]
                                   for j in range(1, len(paras))]}},
        ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "manifest.json").write_text(json.dumps({
        "version": "v4.4-gap-aligned-bg", "created": "2026-10-18",
        "design": ("常显文字轨道(交叉淡变 0.35s,片首/片尾 0.6s);"
                    "背景 0.45s 叠化精确置于句间停顿(上句语音结束+0.04s 起,"
                    "下句开口前≥0.07s 完成),朗读期间零切画;"
                    "最终主题句星河画面从停顿处停留至片尾(~5s 无切换);"
                    "静态居中字(用户覆盖 intro-node 缩放默认项)"),
        "font": str(FONT), "xfade_s": XFADE, "swap_s": SWAP,
        "bg_pool": "runs/20261014-ntc-b01/media/affine (正文已验收运镜池)",
        "bg_by_para": PARA_BG,
        "cards": [{"idx": l["idx"], "text": l["text"], "window_s": l["window"]}
                  for l in layout_log]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.copy(RUN / "chapters" / "intro.wav", OUT / "narration.wav")

    # 7. QA:逐卡中点 + 常显连续性(1.0s→TOTAL-0.7s 之间任何帧中央都应有字)
    qa = ["# intro batch QA (v4.3 persistent text)", "",
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
        qa.append(f"| {i} | {mid:.2f} | {bright*100:.2f} | {'OK' if ok else 'FAIL'} | {c['text']} |")
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
