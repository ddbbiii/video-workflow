# -*- coding: utf-8 -*-
"""Combine the two three-way runs into 3-column sheets (dklapi | mxwell | xxcapi)."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
A = ROOT / "runs" / "20261109-073513-three-way"   # dklapi + mxwell
B = ROOT / "runs" / "20261109-074040-three-way"   # xxcapi (AZ channel)
OUT = ROOT / "runs" / "20261109-075000-three-way-combined"
FONT = r"C:\Windows\Fonts\msyh.ttc"

COLUMNS = [
    ("dklapi  0.16 元 · 2048x1152", A / "dklapi-{p}.png"),
    ("mxwell  0.02 元 · 2048x1152", A / "mxwell-{p}.png"),
    ("xxcapi  约 0.13 元 · 1672x941", B / "xxcapi-{p}.png"),
]
TITLES = {
    "G": "G · 复杂 2x2 深海四格（3 烟囱 / 5 管虫 / 机械臂 / 4 小虾）",
    "S1": "S1 · 悬疑人物全身 + 右手持钥匙",
    "S5": "S5 · 悬疑三视图拼版（正 / 侧 / 背 / 面部）",
}


def build(label: str, height: int = 540) -> Path:
    tiles = []
    for caption, pattern in COLUMNS:
        path = Path(str(pattern).format(p=label))
        if path.exists():
            tiles.append((caption, Image.open(path).convert("RGB")))
    width = int(height * 16 / 9)
    pad, header = 10, 58
    canvas = Image.new("RGB", (width * len(tiles) + pad * (len(tiles) + 1), height + header + pad),
                       (14, 14, 16))
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, 4), TITLES[label], fill=(232, 232, 232), font=ImageFont.truetype(FONT, 23))
    for index, (caption, image) in enumerate(tiles):
        x = pad + index * (width + pad)
        canvas.paste(image.resize((width, height), Image.LANCZOS), (x, header))
        color = (240, 200, 120) if index == 0 else (150, 210, 240) if index == 1 else (190, 240, 170)
        draw.text((x, header - 22), caption, fill=color, font=ImageFont.truetype(FONT, 17))
    out = OUT / f"sheet-{label}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    return out


if __name__ == "__main__":
    for name in ("G", "S1", "S5"):
        print(build(name))
