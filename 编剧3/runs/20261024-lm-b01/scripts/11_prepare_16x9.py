# -*- coding: utf-8 -*-
"""把 image/stills/*.jpg 裁成 16:9(中心裁切)到 image/stills_16x9/。
single: 1536x1024 -> 1536x864;tile 单元: 768x512 -> 768x432。可断点续跑。
mariana 生图口径与 newton 相同(gpt-image-2.5-sunburst: single 1536x1024 /
grid 2048x1152 四格裁剪 -> 768x512 单元)。移植自 newton 11_prepare_16x9.py。
注意:image/ 由静帧子代理占用;本脚本只在静帧验收后运行。
"""
from __future__ import annotations
from pathlib import Path
from PIL import Image

EP = Path(__file__).resolve().parents[3]
SRC = EP / "image" / "stills"
OUT = EP / "image" / "stills_16x9"

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    n=0; skip=0
    for p in sorted(SRC.glob("*.jpg")):
        dst = OUT / p.name
        if dst.exists() and dst.stat().st_size>1000:
            skip+=1; continue
        with Image.open(p) as im:
            w,h = im.size
            nw = w; nh = round(w*9/16)
            if nh > h: nh = h; nw = round(h*16/9)
            left = (w-nw)//2; top = (h-nh)//2
            im.crop((left, top, left+nw, top+nh)).convert("RGB").save(dst, quality=94, optimize=True)
            n+=1
    print(f"cropped {n} skipped {skip}")

if __name__=="__main__":
    main()
