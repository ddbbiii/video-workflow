# -*- coding: utf-8 -*-
"""Crop full raws into 1920x1080 shot stills and build per-chapter contact sheets."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

RUN = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws\runs\20261106-ulw-b01")
RAW, OUT, QA = RUN / "raw_full", RUN / "crops_full", RUN / "qa"

GRID = {
    "G01": ["c0-s03", "c0-s04", "c0-s06", None],
    "G02": ["c0-s07", "c0-s08", "c0-s09", "c0-s10"],
    "G03": ["c1-s01", "c1-s02", "c1-s03", "c1-s04"],
    "G04": ["c1-s05", "c1-s06", "c1-s07", "c1-s08"],
    "G05": ["c1-s09", "c1-s10", "c1-s11", "c1-s12"],
    "G06": ["c1-s13", "c1-s14", "c1-s15", "c1-s16"],
    "G07": ["c1-s21", "c1-s22", "c1-s23", "c1-s24"],
    "G08": [None, None, None, None],
    "G09": ["c2-s01", "c2-s02", "c2-s03", "c2-s04"],
    "G10": ["c2-s05", "c2-s06", "c2-s07", "c2-s08"],
    "G11": ["c2-s09", "c2-s10", "c2-s11", "c2-s13"],
    "G12": ["c2-s15", "c2-s16", "c2-s17", "c2-s18"],
    "G13": ["c2-s19", "c2-s20", "c2-s21", None],
    "G14": ["c3-s01", "c3-s02", "c3-s03", "c3-s04"],
    "G15": ["c3-s05", "c3-s11", "c3-s12", "c3-s13"],
    "G16": ["c3-s14", "c3-s15", "c3-s16", "c3-s17"],
    "G17": ["c4-s01", "c4-s02", "c4-s03", "c4-s04"],
    "G18": ["c4-s05", "c4-s07", "c4-s08", "c4-s09"],
    "G19": ["c4-s10", "c4-s11", "c4-s12", "c4-s13"],
    "G20": ["c4-s14", "c4-s15", "c4-s16", None],
    "G21": ["c5-s01", "c5-s02", "c5-s03", "c5-s04"],
    "G22": ["c5-s06", "c5-s09", "c5-s10", "c5-s11"],
    "G23": ["c5-s13", "c5-s14", "c5-s15", "c5-s16"],
    "G24": ["c5-s17", "c5-s18", "c5-s19", "c5-s20"],
    "G25": ["c5-s22", None, None, None],
    "G26": ["c6-s01", "c6-s02", "c6-s03", "c6-s04"],
    "G27": ["c6-s05", "c6-s06", "c6-s07", "c6-s08"],
    "G28": ["c6-s09", "c6-s10", "c6-s11", "c6-s12"],
    "G29": ["c6-s13", "c6-s14", "c6-s17", "c6-s18"],
    "G30": ["c6-s19", None, None, None],
    "G31": ["c7-s01", "c7-s02", "c7-s03", "c7-s04"],
    "G32": ["c7-s05", "c7-s06", "c7-s07", "c7-s08"],
    "G33": ["c7-s10", "c7-s11", "c7-s12", "c7-s13"],
    "G34": ["c7-s15", "c7-s16", None, None],
    "G35B": ["c8-s01", "c8-s03", "c8-s04", "c8-s05"],
    "G36B": ["c8-s06", "c8-s07", "c8-s08", None],
}
SINGLE = {
    "S01": "c0-s01", "S02": "c0-s02", "S03": "c0-s05", "S04": "c1-s17",
    "S05": "c2-s12", "S06": "c2-s14", "S07": "c3-s06", "S08": "c3-s07",
    "S09": "c3-s08", "S10": "c3-s09", "S11": "c4-s06", "S12": "c5-s05",
    "S13": "c5-s07", "S14": "c5-s12", "S15": "c5-s23", "S16": "c7-s09",
    "S17B": "c8-s02",
}

OUT.mkdir(exist_ok=True); QA.mkdir(exist_ok=True)
made = []
for gid, cells in GRID.items():
    src = RAW / (gid + ".png")
    if not src.exists():
        print("MISSING", src); continue
    im = Image.open(src).convert("RGB"); w, h = im.size
    boxes = [(0, 0, w // 2, h // 2), (w // 2, 0, w, h // 2),
             (0, h // 2, w // 2, h), (w // 2, h // 2, w, h)]
    for i, shot in enumerate(cells):
        if not shot:
            continue
        cell = im.crop(boxes[i]).resize((1920, 1080), Image.LANCZOS)
        out = OUT / (shot + ".png")
        cell.save(out)
        made.append((shot, out, gid, i + 1))
for sid, shot in SINGLE.items():
    src = RAW / (sid + ".png")
    if not src.exists():
        print("MISSING", src); continue
    im = Image.open(src).convert("RGB").resize((1920, 1080), Image.LANCZOS)
    out = OUT / (shot + ".png")
    im.save(out)
    made.append((shot, out, sid, 0))

made.sort(key=lambda x: x[0])
(OUT / "manifest.json").write_text(json.dumps(
    [{"shot": s, "file": str(p), "job": j, "cell": c} for s, p, j, c in made],
    ensure_ascii=False, indent=2), encoding="utf-8")

# per-chapter contact sheets
try:
    font = ImageFont.load_default(size=16)
except TypeError:
    font = ImageFont.load_default()
chapters = {}
for s, p, j, c in made:
    chapters.setdefault(s.split("-")[0], []).append((s, p))
for ch, items in chapters.items():
    cols, tw, th, pad, top = 4, 384, 216, 10, 30
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * pad, top + rows * (th + pad) + pad), (16, 18, 22))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 6), "%s  %d shots" % (ch, len(items)), font=font, fill=(210, 210, 210))
    for i, (s, p) in enumerate(items):
        r, c = divmod(i, cols)
        x, y = pad + c * (tw + pad), top + r * (th + pad)
        sheet.paste(Image.open(p).resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x + 3, y + th + 2), s, font=font, fill=(170, 190, 200))
    sheet.save(QA / ("sheet_%s.jpg" % ch), quality=90)
    print("sheet", ch, len(items))
print("total", len(made))
