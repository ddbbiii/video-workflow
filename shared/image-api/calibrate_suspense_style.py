# -*- coding: utf-8 -*-
"""悬疑画风校准：用 `rules/悬疑/visual.md` §二 的 STYLE_POS / STYLE_NEG，同题跑 dkl2 / new2 / old。

- 每个通道每个镜头只调 1 次，不重试；失败照实记录。
- 风格块从规则文件解析，不在这里手写，避免脚本与规则再次漂移。
- GPT 图片 API 没有独立负向参数，STYLE_NEG 以 `Avoid:` 追加在正向末尾（与生产口径一致）。
- 输出：runs/<ts>-style-calib/raw|crops|compare，report.json，REPORT.md。

用法：
  python calibrate_suspense_style.py            # 全量 3 镜 × 3 通道
  python calibrate_suspense_style.py --only S1  # 只跑某镜（已存在则跳过）
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
import winreg
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RULES = REPO / "rules" / "悬疑" / "visual.md"
RUN = HERE / "runs" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-style-calib")
RAW, CROPS, CMP = RUN / "raw", RUN / "crops", RUN / "compare"
UA = "OpenAI/Python/1.60.0"
TIMEOUT_S = 900

CHANNELS = [
    {"tag": "dkl2", "label": "DKL2 0.015", "base": "https://dklapi.com/v1",
     "key_env": "IMAGE_API_KEY_DKL2", "model": "gpt-image-2.5-sunburst",
     "size": "2048x1152", "price": 0.015},
    {"tag": "new2", "label": "NEW2 0.018", "base": os.environ.get("IMAGE_API_BASE_URL_XXC", "https://xxcapi.com/v1"),
     "key_env": "IMAGE_API_KEY_XXC", "model": "AZ-gpt-image-2.5-sunburst",
     "size": "1672x941", "price": 0.018},
    {"tag": "old", "label": "OLD 0.16", "base": "https://dklapi.com/v1",
     "key_env": "IMAGE_RELAY_KEY_1K", "model": "gpt-image-2.5-sunburst",
     "size": "2048x1152", "price": 0.16},
]

# 三镜按 visual.md §4.2 的顺序写：主体 → 前中后景 → 光线 → 证据 → 事实；破败与生活痕迹按 §三。
SHOTS = [
    {
        "tag": "S1",
        "name": "走廊（环境 / 破败 + 生活痕迹）",
        "body": (
            "dim fourth-floor corridor of an old Chinese apartment building, peeling green paint "
            "along the skirting, a dark water stain spreading down from the window frame, one dead "
            "sensor lamp, a plastic stool and a stack of old newspapers beside a door, cold grey "
            "window light from the far end, slightly off-center composition with a door frame in "
            "the left foreground, deep focus, no people, no readable text"
        ),
    },
    {
        "tag": "S2",
        "name": "人物背影（赛璐璐人物 + 证据箱）",
        "body": (
            "medium shot from behind: a lean Chinese man in his late thirties, short black buzz cut, "
            "dark navy work jacket with a blank rectangular badge patch, dark grey trousers, black "
            "gloves, standing before an open beige metal junction box, rust bleeding from the box "
            "hinge, scuffed wall, a coiled extension cord on the floor, cold corridor light from "
            "behind, face not visible, door frame in the left foreground"
        ),
    },
    {
        "tag": "S3",
        "name": "证据特写（非文书 / 可辨细节）",
        "body": (
            "extreme close-up of a beige metal junction box latch: the steel plate bent outward and "
            "torn, hinge buckled, rust and chipped enamel, a thin layer of dust on the rim, cold "
            "raking light from the right, scuffed wall behind, the latch fills one third of the "
            "frame, slightly off-center, no text"
        ),
    },
]

# 追加：人物镜在 STYLE_POS 之外再压一层"禁止渐变"的赛璐璐强化，只测 dkl2（2048 原生）。
SHOTS.append({
    "tag": "S2b",
    "name": "人物背影 + 赛璐璐强化（只测 dkl2）",
    "channels": ["dkl2"],
    "body": SHOTS[1]["body"] + (
        ", 2D cel animation key visual, flat unshaded color areas, hard-edged shadow shapes, "
        "no gradients on fabric or walls, clean black linework, anime screencap"
    ),
})

FONT_PATHS = [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\arial.ttf"]

def font(size: int):
    for path in FONT_PATHS:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def read_block(name: str) -> str:
    text = RULES.read_text(encoding="utf-8")
    match = re.search(rf"`{name}`：\s*```text\s*(.*?)```", text, re.S)
    if not match:
        raise SystemExit(f"找不到 {name} 块：{RULES}")
    return re.sub(r"\s+", " ", match.group(1)).strip()


def key_for(env_name: str) -> str:
    value = os.environ.get(env_name, "").strip()
    if value:
        return value
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, env_name)[0]


def download(url: str, dest: Path) -> None:
    curl = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "curl.exe"
    if curl.exists():
        result = subprocess.run(
            [str(curl), "-L", "--retry", "3", "--retry-delay", "2", "--max-time", "300",
             "-A", UA, "-o", str(dest), url], capture_output=True, text=True)
        if result.returncode == 0 and dest.exists() and dest.stat().st_size > 0:
            return
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=300) as resp:
        dest.write_bytes(resp.read())


def call(channel: dict, prompt: str, shot_tag: str, key: str) -> dict:
    payload = {"model": channel["model"], "prompt": prompt, "size": channel["size"], "n": 1}
    request = urllib.request.Request(
        f"{channel['base']}/images/generations",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "Accept": "application/json", "User-Agent": UA})
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read()
    except Exception as exc:  # noqa: BLE001
        return {"channel": channel["tag"], "shot": shot_tag, "ok": False,
                "error": f"{type(exc).__name__}: {exc}"}
    elapsed = round(time.time() - started, 1)
    stem = f"{channel['tag']}-{shot_tag}"
    (RAW / f"{stem}-response.json").write_bytes(raw)
    info = {"channel": channel["tag"], "shot": shot_tag, "http_status": status,
            "elapsed_s": elapsed, "request_size": channel["size"], "price_cny": channel["price"]}
    if status != 200:
        info["ok"] = False
        try:
            info["error"] = json.loads(raw.decode("utf-8"))
        except Exception:
            info["error"] = raw[:400].decode("utf-8", "replace")
        return info
    body = json.loads(raw.decode("utf-8"))
    item = (body.get("data") or [{}])[0]
    png = RAW / f"{stem}.png"
    if item.get("b64_json"):
        png.write_bytes(base64.b64decode(item["b64_json"]))
        info["delivery"] = "b64_json"
    elif item.get("url"):
        info["delivery"] = "url"
        download(item["url"], png)
    else:
        info["ok"] = False
        info["error"] = "no b64_json / url"
        return info
    with Image.open(png) as image:
        image.load()
        info["dims"] = list(image.size)
        rgb = image.convert("RGB")
        gray = np.asarray(rgb.convert("L"), dtype=np.float64)
        hsv = np.asarray(rgb.convert("HSV"), dtype=np.float64)
        delivery = np.asarray(rgb.resize((1920, 1080), Image.LANCZOS).convert("L"), dtype=np.float64)
        info["metrics"] = {
            "std_lum": round(float(gray.std()), 1),
            "mean_sat": round(float(hsv[:, :, 1].mean()), 1),
            "lap_var": round(lap_var(gray), 1),
            "delivery_lap_var": round(lap_var(delivery), 1),
        }
        # 100% 中心裁切，便于看线条/平涂/纹理
        width, height = rgb.size
        crop_w, crop_h = min(1000, width), min(562, height)
        box = ((width - crop_w) // 2, (height - crop_h) // 2,
               (width + crop_w) // 2, (height + crop_h) // 2)
        rgb.crop(box).save(CROPS / f"{stem}-c.png")
    info.update({"ok": True, "bytes": png.stat().st_size, "usage": body.get("usage")})
    return info


def lap_var(gray: np.ndarray) -> float:
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1]
           + gray[1:-1, :-2] + gray[1:-1, 2:])
    return float(lap.var())


def tile(path: Path, width: int, height: int, caption: str) -> Image.Image:
    canvas = Image.new("RGB", (width, height + 30), (18, 18, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 5), caption, fill=(230, 230, 230), font=font(18))
    if path.exists():
        with Image.open(path) as image:
            canvas.paste(image.convert("RGB").resize((width, height), Image.LANCZOS), (0, 30))
    else:
        draw.text((8, 50), "NO IMAGE", fill=(230, 120, 120), font=font(24))
    return canvas


def main() -> None:
    global RUN, RAW, CROPS, CMP
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default="")
    parser.add_argument("--run", default="", help="已有 run 目录；补单格或续跑")
    args = parser.parse_args()
    only = {part.strip() for part in args.only.split(",") if part.strip()}
    if args.run:
        RUN = Path(args.run).resolve()
        RAW, CROPS, CMP = RUN / "raw", RUN / "crops", RUN / "compare"

    POS, NEG = read_block("STYLE_POS"), read_block("STYLE_NEG")
    RUN.mkdir(parents=True, exist_ok=True)
    for directory in (RAW, CROPS, CMP):
        directory.mkdir(parents=True, exist_ok=True)

    cells = {}
    report_path = RUN / "report.json"
    if report_path.exists():
        for item in json.loads(report_path.read_text(encoding="utf-8")).get("results", []):
            cells[(item.get("shot"), item.get("channel"))] = item

    for shot in SHOTS:
        if only and shot["tag"] not in only:
            continue
        prompt = f"{POS}, {shot['body']}\nAvoid: {NEG}"
        print(f"[{shot['tag']}] {shot['name']}", flush=True)
        jobs = []
        for channel in CHANNELS:
            if shot.get("channels") and channel["tag"] not in shot["channels"]:
                continue
            if (RAW / f"{channel['tag']}-{shot['tag']}.png").exists():
                print("  skip", channel["tag"], flush=True)
                continue
            jobs.append(channel)
        with ThreadPoolExecutor(max_workers=len(jobs) or 1) as pool:
            futures = {pool.submit(call, ch, prompt, shot["tag"], key_for(ch["key_env"])): ch for ch in jobs}
            for future in futures:
                info = future.result()
                cells[(info.get("shot"), info.get("channel"))] = info
                print(f"  {info['channel']}: {'OK' if info.get('ok') else 'FAIL'} "
                      f"{info.get('elapsed_s', '-')}s {info.get('dims', '')} {info.get('error', '')}", flush=True)

    # 3 镜 × 3 通道对照
    results = [cells[(shot["tag"], channel["tag"])]
               for shot in SHOTS for channel in CHANNELS
               if (shot["tag"], channel["tag"]) in cells]
    cell_w, cell_h, pad = 720, 405, 10
    rows = [s for s in SHOTS if not only or s["tag"] in only]
    canvas = Image.new("RGB", (pad + len(CHANNELS) * (cell_w + pad),
                               pad + len(rows) * (cell_h + 30 + pad)), (12, 12, 14))
    for r, shot in enumerate(rows):
        y = pad + r * (cell_h + 30 + pad)
        for c, channel in enumerate(CHANNELS):
            x = pad + c * (cell_w + pad)
            if shot.get("channels") and channel["tag"] not in shot["channels"]:
                block = Image.new("RGB", (cell_w, cell_h + 30), (18, 18, 20))
                ImageDraw.Draw(block).text((12, 44), "SKIP · 本镜未测", fill=(110, 110, 110), font=font(20))
                canvas.paste(block, (x, y))
                continue
            path = RAW / f"{channel['tag']}-{shot['tag']}.png"
            canvas.paste(tile(path, cell_w, cell_h, f"{shot['tag']} · {channel['label']}"), (x, y))
    canvas.save(CMP / "sheet-style-calib.png")

    (RUN / "report.json").write_text(json.dumps({
        "run": RUN.name,
        "style_pos": POS,
        "style_neg": NEG,
        "results": results,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = ["# 悬疑画风校准（STYLE_POS / STYLE_NEG × dkl2 / new2 / old）", "",
             f"- 运行：{RUN.name}", f"- 规则：`{RULES.relative_to(REPO)}` §二", "",
             "| 镜 | 通道 | 状态 | 尺寸 | std_lum | sat | 原生锐度 | 1080p 锐度 | 耗时 s |",
             "|---|---|---|---|---|---|---|---|---|"]
    for info in results:
        m = info.get("metrics") or {}
        lines.append("| {shot} | {channel} | {status} | {dims} | {std} | {sat} | {lap} | {dlap} | {elapsed} |".format(
            shot=info.get("shot", ""), channel=info.get("channel", ""),
            status="OK" if info.get("ok") else "FAIL",
            dims="×".join(map(str, info.get("dims", []))) or "-",
            std=m.get("std_lum", "-"), sat=m.get("mean_sat", "-"),
            lap=m.get("lap_var", "-"), dlap=m.get("delivery_lap_var", "-"),
            elapsed=info.get("elapsed_s", "-")))
    lines += ["", "## 对照图", "", "- `compare/sheet-style-calib.png`",
              "- `crops/<channel>-<shot>-c.png`（100% 中心裁切）", "",
              "## 判读口径", "",
              "1. 人物帧是否平涂 + 硬边阴影 + 线稿（赛璐璐），还是半写实/照片；",
              "2. 环境帧是否有 ≥2 处损耗与 ≥1 处生活痕迹，且不在虚化里；",
              "3. 构图是否偏置、有前景遮挡、深焦，而不是对称电影剧照。"]
    (RUN / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("DONE", RUN)


if __name__ == "__main__":
    main()
