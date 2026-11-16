# -*- coding: utf-8 -*-
"""Compare mxwell with current production relays on identical suspense prompts."""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
import winreg
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "shared" / "image-api" / "runs" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-mxwell-dklb-new2")
RAW = RUN / "raw"
UA = "OpenAI/Python 1.60.0"
TIMEOUT = 900

CHANNELS = [
    {"tag": "new2", "model": "AZ-gpt-image-2.5-sunburst", "base_env": "IMAGE_API_BASE_URL_XXC",
     "base_default": "https://xxcapi.com/v1", "key_env": "IMAGE_API_KEY_XXC", "size": "1672x941",
     "price_label": "¥0.018 CNY/request (channel-policy estimate)"},
    {"tag": "dkl-b", "model": "gpt-image-2.5-sunburst", "base": "https://dklapi.com/v1",
     "key_env": "IMAGE_API_KEY_DKL", "size": "2048x1152",
     "price_label": "¥0.018 CNY/request (user-confirmed historical rate)"},
    {"tag": "mxwell", "model": "gpt-image-2.5-sunburst", "base_env": "IMAGE_API_BASE_URL_MX",
     "base_default": "https://api.mxwell.ai/v1", "key_env": "IMAGE_API_KEY_MX", "size": "2048x1152",
     "price_label": "$0.02 USD/request (price shown in supplied screenshot)"},
]

STYLE = (
    "Desaturated 2D graphic-novel panel, mature simplified cel-shaded characters, flat color blocks, "
    "hard-edged shadows, clean dark ink linework, cold grey-blue palette with one restrained warm practical "
    "light, ordinary worn Chinese apartment interior, deep focus, layered foreground, legible suspense staging, "
    "16:9. No photorealism, 3D, gradients on characters, readable text, letters, numbers, watermark or logo."
)
SHOTS = [
    {"tag": "S1-empty-corridor", "cel": False,
     "body": "Wide empty fourth-floor corridor in an old Chinese apartment building at dusk. Camera from the "
     "stair landing looking down the hall, deep focus; a chipped green doorframe presses into the left foreground. "
     "Peeling paint, water stain below the far window, yellowed plastic stool and drying rack with two dark shirts. "
     "The far end feels subtly too long but remains physically plausible. Cold blue-grey window light, one narrow "
     "warm line under a closed door. No people."},
    {"tag": "S2-investigator", "cel": True,
     "body": "Medium-long rear view of a lean Chinese male investigator in his late thirties, short black hair, "
     "dark work jacket and grey trousers, standing beside an open beige metal electrical junction box. His right "
     "hand holds a small flashlight aimed at the box; fingers clearly formed. Camera outside the doorway at eye "
     "level, investigator on the right third, chipped doorframe occludes the left foreground. Peeling paint, rust "
     "at the hinge, taped wall repair and coiled extension cord. Cold corridor light and one weak warm spill. "
     "Face not visible."},
    {"tag": "S3-latch-evidence", "cel": True,
     "body": "Close evidence view of a beige metal junction-box latch bent outward and torn, hinge buckled, rust "
     "and chipped enamel clearly visible. Camera just left of the box and slightly above, deep focus; latch fills "
     "one third of the image, off-center. Scuffed painted wall and old repair tape remain visible. Cold raking "
     "light from the right with one subtle warm reflection. No hands, labels or text."},
]


def get_key(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, name)[0]


def base_url(channel: dict) -> str:
    return os.environ.get(channel.get("base_env", ""), channel.get("base_default", channel.get("base", ""))).rstrip("/")


def call(channel: dict, shot: dict, key: str) -> dict:
    prompt = STYLE + (" 2D cel animation key visual, flat unshaded color areas, hard-edged shadow shapes, "
                      "no gradients on fabric or walls, clean black linework." if shot["cel"] else "") + " " + shot["body"]
    payload = {"model": channel["model"], "prompt": prompt, "size": channel["size"], "n": 1}
    request = urllib.request.Request(
        base_url(channel) + "/images/generations",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "Accept": "application/json", "User-Agent": UA},
    )
    start = time.time()
    started_at = datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read()
    except Exception as exc:
        return {"channel": channel["tag"], "model": channel["model"], "shot": shot["tag"],
                "ok": False, "started_at": started_at, "elapsed_s": round(time.time() - start, 1),
                "error": f"{type(exc).__name__}: {str(exc)[:300]}"}

    result = {"channel": channel["tag"], "model": channel["model"], "shot": shot["tag"],
              "started_at": started_at, "http_status": status, "elapsed_s": round(time.time() - start, 1),
              "requested_size": channel["size"], "price_label": channel["price_label"]}
    if not 200 <= status < 300:
        result.update({"ok": False, "error": raw[:500].decode("utf-8", "replace")})
        return result
    try:
        body = json.loads(raw.decode("utf-8"))
        item = (body.get("data") or [{}])[0]
        dest = RAW / f"{channel['tag']}-{shot['tag']}.png"
        if item.get("b64_json"):
            dest.write_bytes(base64.b64decode(item["b64_json"]))
        elif item.get("url"):
            req = urllib.request.Request(item["url"], headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=300) as response:
                dest.write_bytes(response.read())
        else:
            raise ValueError("response missing image")
        with Image.open(dest) as image:
            image.load()
            result.update({"ok": True, "file": str(dest.resolve()), "dims": list(image.size),
                           "bytes": dest.stat().st_size, "usage": body.get("usage")})
    except Exception as exc:
        result.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
    return result


def main() -> int:
    keys = {item["tag"]: get_key(item["key_env"]) for item in CHANNELS}
    RAW.mkdir(parents=True, exist_ok=True)
    results = []
    manifest = {"run": RUN.name, "started": datetime.now().astimezone().isoformat(timespec="seconds"),
                "channels": CHANNELS, "shots": SHOTS, "style": STYLE,
                "credential_note": "mxwell used the configured local credential; no credential value is stored",
                "results": results}
    manifest_path = RUN / "manifest.json"
    for shot in SHOTS:
        with ThreadPoolExecutor(max_workers=len(CHANNELS)) as pool:
            futures = [pool.submit(call, channel, shot, keys[channel["tag"]]) for channel in CHANNELS]
            for future in as_completed(futures):
                item = future.result()
                results.append(item)
                print(json.dumps({k: v for k, v in item.items() if k not in ("error", "usage")}, ensure_ascii=False), flush=True)
                manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    font_path = Path(r"C:\Windows\Fonts\msyh.ttc")
    font = ImageFont.truetype(str(font_path), 18) if font_path.exists() else ImageFont.load_default()
    thumb_w, thumb_h, label_h, pad = 640, 360, 34, 10
    sheet = Image.new("RGB", (pad + 3 * (thumb_w + pad), pad + len(SHOTS) * (thumb_h + label_h + pad)), (24, 24, 26))
    draw = ImageDraw.Draw(sheet)
    for row, shot in enumerate(SHOTS):
        for col, channel in enumerate(CHANNELS):
            x, y = pad + col * (thumb_w + pad), pad + row * (thumb_h + label_h + pad)
            draw.text((x + 4, y + 4), f"{shot['tag']} | {channel['tag']}", font=font, fill="white")
            item = next((r for r in results if r["shot"] == shot["tag"] and r["channel"] == channel["tag"] and r.get("ok")), None)
            if item:
                with Image.open(item["file"]) as image:
                    image.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                    sheet.paste(image.convert("RGB"), (x, y + label_h))
    sheet.save(RUN / "contact-sheet.jpg", quality=88)
    lines = ["# mxwell / dkl-b / new2 image comparison", "",
             "同提示词、同模型家族，对照 3 个悬疑场景。单价来自截图或历史口径，未与本次账单逐笔核销。", "",
             "| 场景 | 通道 | 模型 | 成图尺寸 | 秒 | 参考单价 |", "|---|---|---|---:|---:|---|"]
    for item in sorted(results, key=lambda r: (r["shot"], [c["tag"] for c in CHANNELS].index(r["channel"]))):
        dims = "×".join(map(str, item.get("dims", []))) or "失败"
        price = next(channel["price_label"] for channel in CHANNELS if channel["tag"] == item["channel"])
        lines.append(f"| {item['shot']} | {item['channel']} | {item['model']} | {dims} | {item.get('elapsed_s', '-') } | {price} |")
    lines += ["", "## 质量记录", "", "待人工查看联系表后补充构图、风格、主体和细节评分。", ""]
    (RUN / "ASSESSMENT.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"DONE {RUN}", flush=True)
    return 0 if all(item.get("ok") for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
