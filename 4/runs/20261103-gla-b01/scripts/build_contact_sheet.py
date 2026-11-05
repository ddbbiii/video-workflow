# -*- coding: utf-8 -*-
"""静帧验收拼图工具:把 image/stills/ 的静帧按章排成缩略拼图,每镜一格,标 shot_id。

用途:静帧子代理批量生图后,用户快速目检全量/分章画面(不用逐张打开)。
- 分章输出一张 JPG(章节中文标题 + 该章全部镜头);
- 缺失的镜渲染为深灰占位格并标 MISSING,一眼看出覆盖率;
- 同时打印/落盘每章 覆盖率摘要 (have/total)。

只读 image/stills 与 visual/SHOT_PLAN.json,不写 image/ 目录;
输出默认 runs/20261103-gla-b01/qa/contact_sheets/。

用法:
  python build_contact_sheet.py                     # 全部章节
  python build_contact_sheet.py --sections ch04 c7  # 只出指定章(支持 c4/ch04 两种写法)
  python build_contact_sheet.py --columns 6 --thumb-w 480
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

EP = Path(__file__).resolve().parents[3]
STILLS = EP / "image" / "stills"
PLAN = EP / "visual" / "SHOT_PLAN.json"
OUT_DIR = Path(__file__).resolve().parents[1] / "qa" / "contact_sheets"

SECTION_ORDER = ["bridge", "ch01", "ch02", "ch03", "ch04", "ch05",
                 "ch06", "ch07", "ch08", "ch09", "ch10", "epilogue"]
SECTION_TITLES = {  # 与 visual/build_shot_plan_v1.py SECTION_TITLES 一致
    "bridge": "故事由来",
    "ch01": "一、一个研究石头的人，把表留在了地上", "ch02": "二、两个时钟",
    "ch03": "三、时间开始变黏", "ch04": "四、灯最暗的那几周",
    "ch05": "五、你的“一天”，比一天长", "ch06": "六、他以为是8月20日",
    "ch07": "七、十年后，他又下去了，这次六个月", "ch08": "八、接过火把的人",
    "ch09": "九、一直住在洞里的人", "ch10": "十、今晚，你的钟也在走",
    "epilogue": "尾声：回到洞口",
}
BG = (16, 20, 26)
FG = (222, 228, 234)
ACCENT = (245, 200, 120)
MISS_BG = (40, 44, 50)
MISS_FG = (150, 90, 90)

CJK_FONTS = [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf",
             r"C:\Windows\Fonts\sim sun.ttf".replace(" ", "")]
MONO_FONTS = [r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\arial.ttf"]


def load_font(candidates, size):
    for p in candidates:
        p = Path(p)
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                continue
    return ImageFont.load_default()


def normalize_section(name: str) -> str:
    n = name.strip().lower()
    if n.isdigit() and len(n) <= 2:
        n = f"c{n}"
    if len(n) >= 3 and n[:2] == "ch" and n[2:].isdigit():
        n = "ch" + n[2:]
    if len(n) == 2 and n[0] == "c" and n[1].isdigit():
        n = f"ch0{n[1]}"
    if n.startswith("ep") and n != "epilogue":
        n = "epilogue"
    if n in ("brg", "origin"):
        n = "bridge"
    return n


def find_still(sid: str):
    for ext in (".jpg", ".jpeg", ".png"):
        p = STILLS / f"{sid}{ext}"
        if p.exists():
            return p
    return None


def thumb_cell(sid, shot, thumb_w, f_label):
    """单格:16:9 缩略图(缺失则占位) + 底部标签条。返回 PIL Image。"""
    thumb_h = round(thumb_w * 9 / 16)
    label_h = 26
    cell = Image.new("RGB", (thumb_w, thumb_h + label_h), BG)
    d = ImageDraw.Draw(cell)
    src = find_still(sid)
    if src is not None:
        with Image.open(src) as im:
            im = im.convert("RGB")
            w, h = im.size
            nw = w
            nh = round(w * 9 / 16)
            if nh > h:
                nh = h
                nw = round(h * 16 / 9)
            left = (w - nw) // 2
            top = (h - nh) // 2
            im = im.crop((left, top, left + nw, top + nh)).resize((thumb_w, thumb_h))
            cell.paste(im, (0, 0))
        color = FG
    else:
        d.rectangle([0, 0, thumb_w, thumb_h], fill=MISS_BG)
        d.text((thumb_w // 2 - 30, thumb_h // 2 - 8), "MISSING", fill=MISS_FG, font=f_label)
        color = MISS_FG
    tag = f"{sid}  {shot.get('strategy','')} {shot.get('image_mode','')}"
    d.rectangle([0, thumb_h, thumb_w, thumb_h + label_h], fill=(10, 13, 17))
    d.text((6, thumb_h + 5), tag[:46], fill=color, font=f_label)
    # i2v 镜头加琥珀色角标,便于关注重点镜
    if shot.get("shot_class") == "image_to_video":
        d.polygon([(thumb_w - 18, thumb_h), (thumb_w, thumb_h), (thumb_w, thumb_h - 18)],
                  fill=ACCENT)
    return cell


def build_section(sec, shots, out_dir, columns, thumb_w, f_label, f_title):
    columns = max(1, min(columns, len(shots) or 1))
    rows = (len(shots) + columns - 1) // columns
    cw = thumb_w
    ch = round(thumb_w * 9 / 16) + 26
    pad = 8
    title_h = 56
    W = columns * cw + (columns + 1) * pad
    H = title_h + rows * ch + (rows + 1) * pad
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    have = sum(1 for s in shots if find_still(s["id"]) is not None)
    title = f"{SECTION_TITLES.get(sec, sec)}   {sec}   {have}/{len(shots)}"
    d.text((pad + 4, 12), title, fill=ACCENT if have < len(shots) else FG, font=f_title)
    for i, s in enumerate(shots):
        r, c = divmod(i, columns)
        x = pad + c * (cw + pad)
        y = title_h + pad + r * (ch + pad)
        sheet.paste(thumb_cell(s["id"], s, thumb_w, f_label), (x, y))
    out = out_dir / f"{sec}_contact.jpg"
    sheet.save(str(out), quality=90, optimize=True)
    return out, have, len(shots)


def main():
    global STILLS
    ap = argparse.ArgumentParser(description="glacier-river 静帧分章验收拼图")
    ap.add_argument("--sections", nargs="*", default=None,
                    help="只出指定章(如 ch04 c7 ep);默认全部")
    ap.add_argument("--columns", type=int, default=5, help="每行格数(默认5)")
    ap.add_argument("--thumb-w", type=int, default=384, help="单格缩略宽(默认384)")
    ap.add_argument("--stills", default=str(STILLS), help="静帧目录")
    ap.add_argument("--out", default=str(OUT_DIR), help="输出目录")
    args = ap.parse_args()

    STILLS = Path(args.stills)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    shots = plan["shots"]
    by_sec = {}
    for s in shots:
        by_sec.setdefault(s["section"], []).append(s)

    f_label = load_font(MONO_FONTS, 15)
    f_title = load_font(CJK_FONTS, 26)

    secs = [normalize_section(x) for x in args.sections] if args.sections else SECTION_ORDER
    unknown = [s for s in secs if s not in by_sec]
    if unknown:
        raise SystemExit(f"未知章节: {unknown}; 可选: {list(by_sec)}")

    summary = {}
    total_have = total_all = 0
    for sec in secs:
        out, have, n = build_section(sec, by_sec[sec], out_dir, args.columns,
                                     args.thumb_w, f_label, f_title)
        summary[sec] = {"have": have, "total": n, "sheet": str(out)}
        total_have += have
        total_all += n
        print(f"{sec}: {have}/{n} -> {out.name}")
    print(f"TOTAL: {total_have}/{total_all} stills present")
    (out_dir / "contact_sheet_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
