# -*- coding: utf-8 -*-
"""《病历对不上》GPT 关键帧：冷开场病历 / 冰箱证据 / 周砚。"""
import argparse
import base64
import json
import os
import time
import urllib3
import requests
from pathlib import Path

urllib3.disable_warnings()
OUT = Path(r"E:\program\1project\video\projects\悬疑\visual-tests\20261107-keyframes")
OUT.mkdir(parents=True, exist_ok=True)
URL = "https://dklapi.com/v1/images/generations"
MODEL = "gpt-image-2.5-sunburst"
SIZE = "2048x1152"

STYLE = (
    "成熟简化赛璐璐动漫静帧，低饱和冷灰蓝基调，仅一处受控暖光源，"
    "道具用较重的墨线勾边，暗部保留细节、物件必须一眼可辨（可读性恐怖），"
    "构图克制、轻微偏心，16:9 横屏。"
    "所有纸张、卡片、屏幕上的文字和数字都模糊不可辨认，禁止可读汉字、数字、标签。"
    "禁止：写实照片、3D 渲染、幼态 Q 版、大眼萌系、高饱和、重暗角、血浆、怪物、"
    "通栏文字、水印、UI、拼贴排版。"
)

SHOTS = {
    "K01-cold-open": (
        "深夜医院病案室，一台平板扫描仪的绿色光带正扫过一张泛黄的 2011 年血液内科病历纸。"
        "纸面平铺、四角微翘，页眉的患者姓名被一圈咖啡渍洇开、字迹糊掉；纸边有生锈回形针压痕。"
        "画面里只有纸、绿光带和一只成年男人的手（手在画面右下角，食指按着纸角）。"
        "冷灰蓝环境，绿光带是唯一高亮，桌面是旧木质。"
    ),
    "K02-fridge": (
        "普通家庭冰箱门的局部特写，白色漆面有一道细划痕。门上用磁贴压着三样东西："
        "一张淡蓝色医院预约卡（表格线和一枚红色三角标记，字迹不可辨认）、"
        "一张儿童蜡笔画（歪扭的房子和三个火柴人）、一枚圆形冰箱贴。"
        "冰箱顶灯投下偏冷的光，磁贴边缘反光；画面右侧边缘露出一点厨房暗部。没有可读文字。"
    ),
    "K02b-fridge": (
        "老小区厨房的旧冰箱局部，漆面发黄、有细划痕和旧磁贴，不是产品摄影，也不是3D渲染。"
        "冰箱门上用磁贴压着一张淡蓝色医院预约卡（表格线和一枚红色三角标记，字迹模糊不可辨认）、"
        "一张儿童蜡笔画（歪扭的房子和三个火柴人）、一枚圆形旧冰箱贴。"
        "厨房很暗，只有冰箱顶灯与走廊灯偏冷的微光；右侧背景是暗木橱柜和一点受控暖光。"
        "成熟简化漫画插画，清晰墨线、平涂色块、低饱和冷灰蓝；物件一眼可辨。没有可读文字。"
    ),
    "K03-zhouyan": (
        "病案室夜班，35 岁中国男人周砚，短黑发、瘦、眼下疲惫，穿深蓝灰外套，"
        "坐在旧木桌前，手里压着一摞病历档案。桌上有一盏受控暖色台灯和一叠摊开的纸，"
        "背景是成排的病案柜与扫描仪绿光。他侧脸，不看镜头，表情克制。"
        "成熟简化赛璐璐人物，正常成年比例，不做写实脸，不做幼态。"
    ),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    args = ap.parse_args()
    key = os.environ.get("IMAGE_RELAY_KEY_1K")
    if not key:
        raise SystemExit("IMAGE_RELAY_KEY_1K missing")
    ids = [args.only] if args.only else list(SHOTS)
    for sid in ids:
        prompt = STYLE + "\n\n" + SHOTS[sid]
        payload = {"model": MODEL, "prompt": prompt, "size": SIZE, "n": 1}
        t0 = time.time()
        r = requests.post(URL, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
                          json=payload, timeout=600, verify=False)
        print(sid, "HTTP", r.status_code, "elapsed", round(time.time() - t0, 1), flush=True)
        if r.status_code != 200:
            print(r.text[:500])
            continue
        data = r.json()
        item = (data.get("data") or [{}])[0]
        dst = OUT / f"{sid}.png"
        if item.get("b64_json"):
            dst.write_bytes(base64.b64decode(item["b64_json"]))
        elif item.get("url"):
            with requests.get(item["url"], timeout=600, verify=False) as im:
                dst.write_bytes(im.content)
        else:
            print("no image", json.dumps(data)[:300])
            continue
        print(sid, "saved", dst.stat().st_size, flush=True)


if __name__ == "__main__":
    main()
