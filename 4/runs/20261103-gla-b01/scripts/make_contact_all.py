# -*- coding: utf-8 -*-
"""拼 26 张静帧的联系表（5 列）。"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

EP = Path(r"E:\program\1project\video\4")
SRC = EP / "image" / "stills"
OUT = EP / "runs" / "20261103-gla-b01" / "qa" / "contact_all26.jpg"
ids = [f"c1-s{i:02d}" for i in range(1, 15)] + [f"c2-s{i:02d}" for i in range(1, 13)]
TW, TH = 380, 254
cols = 5
rows = (len(ids) + cols - 1) // cols
sheet = Image.new("RGB", (cols * TW, rows * (TH + 28)), (12, 16, 22))
d = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 18)
except Exception:
    font = ImageFont.load_default()
for i, sid in enumerate(ids):
    p = SRC / f"{sid}.jpg"
    if not p.exists():
        continue
    im = Image.open(p).convert("RGB")
    im.thumbnail((TW, TH))
    x = (i % cols) * TW + (TW - im.width) // 2
    y = (i // cols) * (TH + 28) + (TH - im.height) // 2
    sheet.paste(im, (x, y))
    d.text(((i % cols) * TW + 6, (i // cols) * (TH + 28) + TH + 3), sid, font=font, fill=(230, 235, 240))
OUT.parent.mkdir(parents=True, exist_ok=True)
sheet.save(OUT, quality=92)
print(OUT, sheet.size)
