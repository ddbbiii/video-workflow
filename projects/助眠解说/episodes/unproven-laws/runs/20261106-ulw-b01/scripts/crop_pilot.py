# -*- coding: utf-8 -*-
"""Crop pilot raws: 2x2 grids -> four 1024x576 panels -> Lanczos 1920x1080; singles -> 1920x1080.
No API calls. Builds a labeled QA contact sheet."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

RUN = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws\runs\20261106-ulw-b01")
RAW, CROPS, QA = RUN / "raw", RUN / "crops", RUN / "qa"

MAP = {
    "G01": [("p1", "c0-s03"), ("p2", "c0-s04"), ("p4", "c0-s06")],
    "G02": [("p1", "c0-s07"), ("p2", "c0-s08"), ("p3", "c0-s09"), ("p4", "c0-s10")],
    "S01": [("single", "c0-s01")],
    "S02": [("single", "c0-s02")],
    "S03": [("single", "c0-s05")],
}

CROPS.mkdir(exist_ok=True)
QA.mkdir(exist_ok=True)
made = []
for job, cells in MAP.items():
    src = RAW / (job + ".png")
    if not src.exists():
        print("MISSING", src)
        continue
    im = Image.open(src).convert("RGB")
    w, h = im.size
    if job.startswith("G"):
        boxes = {
            "p1": (0, 0, w // 2, h // 2),
            "p2": (w // 2, 0, w, h // 2),
            "p3": (0, h // 2, w // 2, h),
            "p4": (w // 2, h // 2, w, h),
        }
        for tag, shot in cells:
            cell = im.crop(boxes[tag]).resize((1920, 1080), Image.LANCZOS)
            out = CROPS / ("%s_%s_%s.png" % (job, tag, shot))
            cell.save(out, quality=95)
            made.append((shot, out, job, tag, (w // 2, h // 2)))
            print("crop", out.name, cell.size)
    else:
        cell = im.resize((1920, 1080), Image.LANCZOS)
        out = CROPS / ("%s_%s.png" % (job, cells[0][1]))
        cell.save(out, quality=95)
        made.append((cells[0][1], out, job, "single", (w, h)))
        print("single", out.name, cell.size)

# contact sheet: 5 columns x 2 rows, 384x216 thumbs, labels
cols, tw, th, pad, top = 5, 384, 216, 12, 34
rows = (len(made) + cols - 1) // cols
sheet = Image.new("RGB", (cols * tw + (cols + 1) * pad, top + rows * (th + pad) + pad), (18, 20, 24))
d = ImageDraw.Draw(sheet)
try:
    font = ImageFont.load_default(size=18)
except TypeError:
    font = ImageFont.load_default()
d.text((pad, 8), "unproven-laws c0 pilot | 20261106-ulw-b01 | cells Lanczos 1920x1080", font=font, fill=(220, 220, 220))
for i, (shot, path, job, tag, orig) in enumerate(made):
    r, c = divmod(i, cols)
    x = pad + c * (tw + pad)
    y = top + r * (th + pad)
    thumb = Image.open(path).resize((tw, th), Image.LANCZOS)
    sheet.paste(thumb, (x, y))
    d.text((x + 4, y + th + 3), "%s  %s %s" % (shot, job, tag), font=font, fill=(180, 200, 210))
sheet.save(QA / "c0_pilot_contact.jpg", quality=92)
print("contact", QA / "c0_pilot_contact.jpg", sheet.size)
(CROPS / "crops_manifest.json").write_text(json.dumps(
    [{"shot": s, "file": str(p), "grid": j, "cell": t, "source_cell_px": list(o)} for s, p, j, t, o in made],
    ensure_ascii=False, indent=2), encoding="utf-8")
