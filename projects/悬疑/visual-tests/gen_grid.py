# -*- coding: utf-8 -*-
"""2x2 grid test for 《病历对不上》 — style check only.

Follows the house grid convention (see 07_gen_stills.py build_grid_prompt):
one 16:9 image split into 4 equal 16:9 cells, no gutter ornaments, no labels.
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "https://dklapi.com/v1"
MODEL = "gpt-image-2.5-sunburst"
SIZE = "2048x1152"
OUT_DIR = Path(r"E:\program\1project\video\projects\悬疑\visual-tests\20261107-gpt-style")

STYLE = (
    "成熟简化赛璐璐动漫静帧，低饱和冷灰蓝基调，仅一处受控暖光源，"
    "道具用较重的墨线勾边，暗部保留细节、物件必须一眼可辨（可读性恐怖），"
    "构图克制、轻微偏心，16:9 横屏。"
    "禁止：写实照片、3D 渲染、幼态 Q 版、大眼萌系、高饱和、重暗角、血浆、怪物、"
    "通栏文字、水印、UI、拼贴排版。"
)

CELLS = [
    (
        "第1行第1列（冷开场）",
        "深夜病案室，扫描仪的绿色光带正扫过一张泛黄病历纸，纸面平铺、四角微翘，"
        "页眉的患者姓名被一圈咖啡渍洇开、字迹糊掉看不清，纸边有生锈的回形针压痕。"
        "画面里只有纸、绿光带和一只人的手（手在画面右下角，食指按着纸角）。"
        "所有文字都不可辨认：模糊的钢笔字迹、没有可读的汉字或数字。"
        "冷灰蓝环境，绿光带是唯一的高亮，桌面是旧木质。",
    ),
    (
        "第1行第2列（日常）",
        "普通家庭冰箱门的局部特写，白色漆面有一道细划痕。门上用磁贴压着三样东西："
        "一张淡蓝色的医院预约卡（字迹不可辨认，只有模糊的表格线和一枚红色三角标记）、"
        "一张儿童蜡笔画（歪扭的房子和三个火柴人）、一枚圆形冰箱贴。"
        "冰箱顶灯投下偏冷的光，磁贴边缘反光；画面右侧边缘露出一点厨房的暗部。"
        "没有任何可读文字。",
    ),
    (
        "第2行第1列（验证）",
        "医院走廊的长椅，冷白日光灯。一位六十多岁的老年女性坐在长椅上，"
        "左袖被撩到手肘上方，小臂内侧露出一排密集的针眼和一块 bloc 淤青；"
        "她低着头，表情疲惫而平静。画面前景是另一人的手（成年男性），"
        "虚焦，正扶在她的手肘旁。背景走廊虚化，尽头的门半开，透出一条暖色光。"
        "人物为成熟简化的动漫比例，不做写实脸。",
    ),
    (
        "第2行第2列（反转）",
        "家庭餐桌俯拍偏斜角，木桌上摊开一份医院知情同意书的表格（表格线清晰、"
        "手写内容全部模糊不可辨认，签名栏有一道刚写完的墨迹），"
        "一支黑色签字笔滚到桌沿；一只女人的手（手指修长、指甲短）按在纸的右下角，"
        "手腕上戴着一根细红绳。桌角有一杯凉掉的茶，茶面没有热气。"
        "冷灰蓝环境，桌上方一盏暖色吊灯照亮纸面。没有任何可读文字。",
    ),
]


def build_prompt():
    header = (
        "生成一张严格等分的2x2网格图，总画幅16:9，每格也为横屏16:9。"
        "格子之间没有间距、没有装饰边框、没有文字或编号；不同场景只能在各自格子内，不能跨格。"
        "四格必须共用同一套画风与同一套色彩规则。以下位置和编号只用于指令，不要画到图中。"
    )
    parts = [header, "\n\n统一画风：", STYLE]
    for pos, body in CELLS:
        parts.append(f"\n\n{pos}：\n{body}")
    return "".join(parts)


def main():
    key = os.environ.get("IMAGE_RELAY_KEY_1K")
    if not key:
        print("FATAL: IMAGE_RELAY_KEY_1K missing", flush=True)
        return 2
    prompt = build_prompt()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "grid-prompt-v1.txt").write_text(prompt, encoding="utf-8")
    payload = json.dumps({"model": MODEL, "prompt": prompt, "size": SIZE, "n": 1},
                         ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + "/images/generations", data=payload,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST")
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        (OUT_DIR / "grid-error.json").write_bytes(raw)
        print(f"HTTP {exc.code}: {raw[:400]!r}", flush=True)
        return 1
    elapsed = round(time.time() - started, 1)
    (OUT_DIR / "grid-response-v1.json").write_bytes(raw)
    data = json.loads(raw.decode("utf-8"))
    item = (data.get("data") or [{}])[0]
    out = OUT_DIR / "grid-v1.png"
    if item.get("b64_json"):
        out.write_bytes(base64.b64decode(item["b64_json"]))
    elif item.get("url"):
        with urllib.request.urlopen(item["url"], timeout=600) as r:
            out.write_bytes(r.read())
    else:
        print("no image in response", flush=True)
        return 1
    print(f"OK status={status} elapsed={elapsed}s bytes={out.stat().st_size}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
