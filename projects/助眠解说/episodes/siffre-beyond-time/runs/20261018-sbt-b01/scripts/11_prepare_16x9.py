# -*- coding: utf-8 -*-
"""把 image/stills/*.jpg 裁成 16:9(中心裁切)并放大到 1920x1080,输出 image/stills_16x9/。
siffre 实际入库尺寸:single 1536x1024 -> 裁 1536x864 -> 放大 1920x1080;
tile 单元 1024x576(已 16:9)-> 直接放大 1920x1080。单图与 2x2 裁切件同规格输出。
LANCZOS 一次放大(后续 affine 运镜直接按 1080p 源采样,避免逐帧三样)。
可断点续跑。移植自 newton 11_prepare_16x9.py,按本集装配任务书改为 1080p 定尺输出。
注意:只读 image/stills/,不改动既有产物。
"""
from __future__ import annotations
from pathlib import Path
from PIL import Image

EP = Path(__file__).resolve().parents[3]
SRC = EP / "image" / "stills"
OUT = EP / "image" / "stills_16x9"
TARGET = (1920, 1080)

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
            im2 = im.crop((left, top, left+nw, top+nh)).convert("RGB")
            if im2.size != TARGET:
                im2 = im2.resize(TARGET, Image.Resampling.LANCZOS)
            im2.save(dst, quality=95, optimize=True)
            n+=1
    print(f"cropped+upscaled {n} skipped {skip} -> {TARGET[0]}x{TARGET[1]}")

if __name__=="__main__":
    main()
