# -*- coding: utf-8 -*-
"""158 镜总联系表（8 列），用于全片画风/错误抽检。"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

EP = Path(r"E:\program\1project\video\4")
SRC = EP / "image" / "stills"
OUT = EP / "runs" / "20261103-gla-b01" / "qa" / "contact_full.jpg"
ids = []
ids += [f"c1-s{i:02d}" for i in range(1, 15)]
ids += [f"c2-s{i:02d}" for i in range(1, 13)]
ids += [f"c3-s{i:02d}" for i in range(1, 13)]
ids += [f"c4-s{i:02d}" for i in range(1, 12)]
ids += [f"c5-s{i:02d}" for i in range(1, 13)]
ids += [f"c6-s{i:02d}" for i in range(1, 13)]
ids += [f"c7-s{i:02d}" for i in range(1, 13)]
ids += [f"c8-s{i:02d}" for i in range(1, 14)]
ids += [f"c9-s{i:02d}" for i in range(1, 14)]
ids += [f"c10-s{i:02d}" for i in range(1, 13)]
ids += [f"c11-s{i:02d}" for i in range(1, 14)]
ids += [f"c12-s{i:02d}" for i in range(1, 15)]
ids += [f"e-s{i:02d}" for i in range(1, 9)]
TW, TH = 240, 160
cols = 8
rows = (len(ids) + cols - 1) // cols
sheet = Image.new("RGB", (cols * TW, rows * (TH + 18)), (10, 12, 16))
d = ImageDraw.Draw(sheet)
font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 13)
missing = []
for i, sid in enumerate(ids):
    p = SRC / f"{sid}.jpg"
    if not p.exists():
        missing.append(sid); continue
    im = Image.open(p).convert("RGB")
    im.thumbnail((TW, TH))
    x = (i % cols) * TW
    y = (i // cols) * (TH + 18)
    sheet.paste(im, (x, y))
    d.text((x + 3, y + TH + 1), sid, font=font, fill=(220, 226, 232))
sheet.save(OUT, quality=88)
print(OUT, sheet.size, "missing:", missing)
