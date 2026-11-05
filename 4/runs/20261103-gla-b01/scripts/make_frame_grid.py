# -*- coding: utf-8 -*-
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

D = Path(r"E:\program\1project\video\4\runs\20261103-gla-b01\qa\frames")
OUT = D.parent / "frame_grid.jpg"
ts = [2, 9, 21, 35, 55, 90, 150, 220, 300]
TW, TH = 600, 338
cols = 3
rows = (len(ts) + cols - 1) // cols
sheet = Image.new("RGB", (cols * TW, rows * (TH + 26)), (10, 12, 16))
d = ImageDraw.Draw(sheet)
font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 18)
for i, t in enumerate(ts):
    p = D / f"t{t}.jpg"
    im = Image.open(p).convert("RGB")
    im.thumbnail((TW, TH))
    x = (i % cols) * TW + (TW - im.width) // 2
    y = (i // cols) * (TH + 26)
    sheet.paste(im, (x, y))
    d.text(((i % cols) * TW + 6, y + TH + 2), f"{t}s", font=font, fill=(230, 235, 240))
sheet.save(OUT, quality=90)
print(OUT, sheet.size)
