# -*- coding: utf-8 -*-
"""拼一张 9 张已出静帧的联系表，便于目检画风。"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

EP = Path(r"E:\program\1project\video\4")
SRC = EP / "image" / "stills"
OUT = EP / "runs" / "20261103-gla-b01" / "qa" / "contact_preview9.jpg"
ids = ["c1-s01", "c1-s02", "c1-s03", "c1-s04", "c1-s05",
       "c1-s10", "c2-s01", "c2-s06", "c2-s09"]
TW, TH = 600, 400
cols, rows = 3, 3
sheet = Image.new("RGB", (cols * TW, rows * (TH + 34)), (12, 16, 22))
d = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 22)
except Exception:
    font = ImageFont.load_default()
for i, sid in enumerate(ids):
    p = SRC / f"{sid}.jpg"
    if not p.exists():
        continue
    im = Image.open(p).convert("RGB")
    im.thumbnail((TW, TH))
    x = (i % cols) * TW + (TW - im.width) // 2
    y = (i // cols) * (TH + 34) + (TH - im.height) // 2
    sheet.paste(im, (x, y))
    d.text(((i % cols) * TW + 8, (i // cols) * (TH + 34) + TH + 4), sid, font=font, fill=(230, 235, 240))
OUT.parent.mkdir(parents=True, exist_ok=True)
sheet.save(OUT, quality=92)
print(OUT, sheet.size)
