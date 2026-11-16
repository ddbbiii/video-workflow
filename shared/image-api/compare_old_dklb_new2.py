# -*- coding: utf-8 -*-
"""Compare legacy DKL, current DKL backup, and new2 image-2 on suspense shots."""
from __future__ import annotations

import base64
import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
import winreg
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "projects" / "悬疑" / "visual-tests" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-old-dklb-new2")
RAW = RUN / "raw"
UA = "OpenAI/Python 1.60.0"
TIMEOUT = 900

CHANNELS = [
    {"tag": "old", "model": "gpt-image-2.5-sunburst", "base": "https://dklapi.com/v1",
     "key_env": "IMAGE_RELAY_KEY_1K", "size": "2048x1152", "price": 0.16,
     "price_basis": "仓库记录的单张价"},
    {"tag": "dkl-b", "model": "gpt-image-2.5-sunburst", "base": "https://dklapi.com/v1",
     "key_env": "IMAGE_API_KEY_DKL", "size": "2048x1152", "price": 0.018,
     "price_basis": "用户确认的单张价"},
    {"tag": "new2-image-2", "model": "AZ-gpt-image-2", "base_env": "IMAGE_API_BASE_URL_XXC",
     "base_default": "https://xxcapi.com/v1", "key_env": "IMAGE_API_KEY_XXC",
     "size": "1672x941", "price": 0.058 / 3,
     "price_basis": "用户刚核对的 AZ-gpt-image-2 三张账单均价"},
]

RULES = ROOT / "rules" / "悬疑" / "visual.md"
STYLE_POS = (
    "desaturated graphic-novel panel, mature simplified cel-shaded anime characters, flat color blocks "
    "with hard-edged cel shadows, clean ink linework, cold grey-blue palette, one controlled warm practical "
    "light, ordinary Chinese urban interior or street, worn and lived-in surfaces, legible horror staging, "
    "clear foreground subject and evidence prop, slightly off-center composition, deep focus, layered "
    "foreground occlusion in wide shots, volumetric dust in cold window light, 16:9"
)
STYLE_NEG = (
    "photograph, photorealistic, 3d render, cgi, live action, film still, cinematic still, 35mm, shallow "
    "depth of field, bokeh, motion blur, glossy skin, hyperreal texture, clean new building, spotless, "
    "pristine, showroom, symmetrical centered hero shot, chibi, big eyes, text, letters, numbers, labels, "
    "watermark, UI, logo, gore, monster, jump-scare face"
)
CEL_BOOST = (
    "2D cel animation key visual, flat unshaded color areas, hard-edged shadow shapes, no gradients on "
    "fabric or walls, clean black linework, anime screencap"
)

SHOTS = [
    {"tag": "S1-corridor", "name": "empty corridor", "cel": False,
     "body": "Dim fourth-floor corridor of an old six-storey Chinese apartment building. Camera at the stair "
     "landing looking down the corridor, 24mm deep focus, slightly off-center; rusted door frame presses "
     "the left foreground. Peeling green paint along the skirting, a dark water stain below the far window, "
     "yellowed plastic stool and drying rack with two dark shirts in the middle ground, swollen repainted "
     "window at the far end. Cold grey dusk window light; one narrow warm light leaks under a closed door. "
     "No people, no readable text."},
    {"tag": "S2-investigator", "name": "investigator and junction box", "cel": True,
     "body": "Medium-long shot from behind of a lean Chinese male investigator in his late thirties, short "
     "black hair, dark work jacket and grey trousers, standing beside an open beige metal electrical "
     "junction box. His right hand holds a small flashlight directed at the box; five fingers readable. "
     "Camera outside the doorway at eye level, 24mm deep focus, investigator on the right third; chipped "
     "door frame occludes the left foreground. Peeling paint, rust on the box hinge, taped repair on the "
     "wall, coiled extension cord on the floor. Cold corridor light with one weak warm practical light. "
     "Face not visible; no readable text."},
    {"tag": "S3-latch", "name": "damaged latch evidence close-up", "cel": True,
     "body": "Close evidence view of a beige metal junction box latch: steel plate bent outward and torn, "
     "hinge buckled, rust and chipped enamel clearly visible, dust on the rim. Camera just left of the box, "
     "slightly above, deep focus; latch fills at least one third of the image and sits off-center. A scuffed "
     "painted wall and a strip of old repair tape remain visible around it. Cold raking light from the right, "
     "one subtle warm reflection only. No hands, no labels, no text."},
    {"tag": "S4-anomaly", "name": "spatial anomaly", "cel": False,
     "body": "Wide view from a half-open apartment doorway into a worn ordinary Chinese living room. A wall "
     "calendar hangs beside a water-stained doorframe; a plastic stool and slippers sit in the foreground. "
     "In the deep background, the open doorway appears to lead back into the same living room from an "
     "impossible angle, while all furniture remains ordinary and undamaged. Keep the anomaly legible but "
     "subtle, no supernatural figure. Peeling wallpaper, scuffed floor tiles, taped crack repair. Camera "
     "outside the door, 24mm deep focus, door edge occludes the left third. Cold grey-blue light, one warm "
     "table lamp. Calendar has no legible marks or text."},
]


def read_block(name: str) -> str:
    import re
    text = RULES.read_text(encoding="utf-8")
    match = re.search(rf"`{name}`：\s*```text\s*(.*?)```", text, re.S)
    if not match:
        raise RuntimeError(f"Missing {name} block in {RULES}")
    return " ".join(match.group(1).split())


def get_key(env_name: str) -> str:
    value = os.environ.get(env_name, "").strip()
    if value:
        return value
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, env_name)[0]


def get_base(channel: dict) -> str:
    return os.environ.get(channel.get("base_env", ""), channel.get("base_default", channel.get("base", ""))).rstrip("/")


def download(url: str, dest: Path) -> None:
    curl = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "curl.exe"
    if curl.exists():
        result = subprocess.run([str(curl), "-L", "--retry", "3", "--retry-delay", "2", "--max-time", "300",
                                 "-A", UA, "-o", str(dest), url], capture_output=True, text=True)
        if result.returncode == 0 and dest.exists() and dest.stat().st_size:
            return
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=300) as response:
        dest.write_bytes(response.read())


def call(channel: dict, shot: dict, key: str, style_pos: str, style_neg: str) -> dict:
    prompt = f"{style_pos}, {CEL_BOOST + ', ' if shot['cel'] else ''}{shot['body']}\nAvoid: {style_neg}"
    payload = {"model": channel["model"], "prompt": prompt, "size": channel["size"], "n": 1}
    req = urllib.request.Request(f"{get_base(channel)}/images/generations",
                                 data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), method="POST",
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                                          "Accept": "application/json", "User-Agent": UA})
    started = time.time()
    started_at = datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read()
    elapsed = round(time.time() - started, 1)
    result = {"channel": channel["tag"], "model": channel["model"], "shot": shot["tag"],
              "started_at": started_at, "http_status": status, "elapsed_s": elapsed,
              "requested_size": channel["size"], "price_estimate_cny": round(channel["price"], 4),
              "price_basis": channel["price_basis"]}
    if status != 200:
        result.update({"ok": False, "error": raw[:500].decode("utf-8", "replace")})
        return result
    try:
        body = json.loads(raw.decode("utf-8"))
        item = (body.get("data") or [{}])[0]
        dest = RAW / f"{channel['tag']}-{shot['tag']}.png"
        if item.get("b64_json"):
            dest.write_bytes(base64.b64decode(item["b64_json"]))
            delivery = "b64_json"
        elif item.get("url"):
            download(item["url"], dest)
            delivery = "url"
        else:
            raise ValueError("response missing image")
        with Image.open(dest) as image:
            image.load()
            result.update({"ok": True, "file": str(dest.resolve()), "dims": list(image.size),
                           "bytes": dest.stat().st_size, "delivery": delivery,
                           "usage": body.get("usage")})
    except Exception as exc:
        result.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
    return result


def make_contact_sheet(results: list[dict]) -> None:
    width, height, label_h, pad = 640, 360, 34, 10
    font_path = Path(r"C:\Windows\Fonts\msyh.ttc")
    font = ImageFont.truetype(str(font_path), 18) if font_path.exists() else ImageFont.load_default()
    canvas = Image.new("RGB", (pad + 3 * (width + pad), pad + len(SHOTS) * (height + label_h + pad)), (20, 20, 22))
    draw = ImageDraw.Draw(canvas)
    for row, shot in enumerate(SHOTS):
        for col, channel in enumerate(CHANNELS):
            x, y = pad + col * (width + pad), pad + row * (height + label_h + pad)
            draw.text((x + 4, y + 4), f"{shot['tag']} | {channel['tag']} | {channel['model']}", font=font, fill=(235, 235, 235))
            item = next((r for r in results if r["shot"] == shot["tag"] and r["channel"] == channel["tag"] and r.get("ok")), None)
            if item:
                with Image.open(item["file"]) as image:
                    preview = image.convert("RGB")
                    preview.thumbnail((width, height), Image.Resampling.LANCZOS)
                    canvas.paste(preview, (x, y + label_h))
            else:
                draw.text((x + 8, y + label_h + 12), "NO IMAGE", font=font, fill=(220, 100, 100))
    canvas.save(RUN / "contact-sheet.jpg", quality=86)


def main() -> int:
    global RUN, RAW
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default="", help="Resume an existing comparison directory; successful cells are reused")
    args = parser.parse_args()
    if args.run:
        RUN = Path(args.run).resolve()
        RAW = RUN / "raw"
    style_pos, style_neg = read_block("STYLE_POS"), read_block("STYLE_NEG")
    keys = {channel["tag"]: get_key(channel["key_env"]) for channel in CHANNELS}
    RAW.mkdir(parents=True, exist_ok=True)
    manifest_path = RUN / "manifest.json"
    results: list[dict] = []
    if manifest_path.exists():
        results = json.loads(manifest_path.read_text(encoding="utf-8")).get("results", [])
    for shot in SHOTS:
        completed = {(item["shot"], item["channel"]) for item in results if item.get("ok")}
        pending = [channel for channel in CHANNELS if (shot["tag"], channel["tag"]) not in completed]
        if not pending:
            continue
        with ThreadPoolExecutor(max_workers=len(CHANNELS)) as pool:
            futures = [pool.submit(call, channel, shot, keys[channel["tag"]], style_pos, style_neg)
                       for channel in pending]
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                print(json.dumps({k: v for k, v in result.items() if k not in ("error", "usage")}, ensure_ascii=False), flush=True)
                if not result.get("ok"):
                    print(json.dumps({"error": result.get("error")}, ensure_ascii=False), flush=True)
                manifest_path.write_text(json.dumps({
                    "run": RUN.name, "style_pos": style_pos, "style_neg": style_neg,
                    "cel_boost": CEL_BOOST, "shots": SHOTS, "results": results,
                }, ensure_ascii=False, indent=2), encoding="utf-8")
    results.sort(key=lambda item: (item["shot"], [c["tag"] for c in CHANNELS].index(item["channel"])))
    manifest_path.write_text(json.dumps({
        "run": RUN.name, "style_pos": style_pos, "style_neg": style_neg,
        "cel_boost": CEL_BOOST, "shots": SHOTS, "results": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    make_contact_sheet(results)
    cost_lines = ["# old / dkl-b / new2 对照成本与文件清单", "",
                  "成本按站点/历史单价估算；new2 AZ-gpt-image-2 使用用户刚核对的三张合计 ¥0.058 换算均价。接口账单未逐请求归属，因此以用户账单复核为准。", "",
                  "| 镜头 | 通道 | 模型 | 文件 | 尺寸 | 估算费用 |", "|---|---|---|---|---|---:|"]
    for item in results:
        filename = Path(item.get("file", "-")).name if item.get("file") else "失败"
        dims = "×".join(map(str, item.get("dims", []))) or "-"
        cost_lines.append(f"| {item['shot']} | {item['channel']} | {item['model']} | `{filename}` | {dims} | ¥{item['price_estimate_cny']:.4f} |")
    totals = {channel["tag"]: round(sum(r["price_estimate_cny"] for r in results if r["channel"] == channel["tag"] and r.get("ok")), 4) for channel in CHANNELS}
    cost_lines += ["", "| 通道 | 成功张数 | 估算小计 |", "|---|---:|---:|"]
    for channel in CHANNELS:
        count = sum(1 for r in results if r["channel"] == channel["tag"] and r.get("ok"))
        cost_lines.append(f"| {channel['tag']} | {count} | ¥{totals[channel['tag']]:.4f} |")
    cost_lines.append(f"| **总计** | **{sum(1 for r in results if r.get('ok'))}** | **¥{sum(totals.values()):.4f}** |")
    (RUN / "COST.md").write_text("\n".join(cost_lines) + "\n", encoding="utf-8")
    print(f"DONE {RUN}", flush=True)
    return 0 if all(item.get("ok") for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
