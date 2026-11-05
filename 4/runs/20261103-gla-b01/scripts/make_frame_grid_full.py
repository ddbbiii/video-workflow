# -*- coding: utf-8 -*-
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
D = Path(r"E:\program\1project\video\4\runs\20261103-gla-b01\qa\frames_full")
OUT = D.parent / "frame_grid_full.jpg"
ts = [21, 124, 282, 434, 588, 753, 903, 1062, 1245, 1420, 1589, 1772, 1965, 2103]
labels = ["片头", "ch01", "ch02", "ch03", "ch04", "ch05", "ch06", "ch07",
          "ch08", "ch09", "ch10", "ch11", "ch12", "尾声"]
TW, TH = 480, 270
cols = 4
rows = (len(ts) + cols - 1) // cols
sheet = Image.new("RGB", (cols * TW, rows * (TH + 22)), (10, 12, 16))
d = ImageDraw.Draw(sheet)
font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 16)
for i, (t, lab) in enumerate(zip(ts, labels)):
    im = Image.open(D / f"t{t}.jpg").convert("RGB")
    im.thumbnail((TW, TH))
    x = (i % cols) * TW
    y = (i // cols) * (TH + 22)
    sheet.paste(im, (x, y))
    d.text((x + 4, y + TH + 2), f"{lab}  {t}s", font=font, fill=(225, 230, 236))
sheet.save(OUT, quality=90)
print(OUT, sheet.size)
