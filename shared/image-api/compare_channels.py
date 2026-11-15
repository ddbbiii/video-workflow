# -*- coding: utf-8 -*-
"""Image-channel A/B matrix: old dkl / dkl new key / new2 xxcapi / yy shagentai.

One call per channel per prompt, no retry. A channel that answers with an HTTP
error is recorded and the run continues, so a dead relay never blocks the matrix.
Existing PNGs in the run dir are reused: rerunning resumes only the missing
combinations (important because long calls get interrupted by session restarts).

Prompts (verbatim from the 2026-11-09 benchmark + suspense A/B):
  G-grid       complex 2x2 deep-sea grid
  S2-evidence  suspense evidence close-up (paper / hand / shallow DOF)
  S1-person    suspense character full body with a key ring in hand

Outputs under runs/<ts>-channels-3way/:
  raw/<channel>-<prompt>.png|.json
  cells/<channel>-<prompt>-p1..p4.png
  compare/sheet-<prompt>.png        one column per channel, error tiles included
  compare/panel-<n>-<prompt>.png    per panel 100%
  report.json, REPORT.md

Keys come from env first, then the HKCU\\Environment registry values (the repo
convention: keys live in user env, never in files). Never printed.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
import winreg
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
REUSE = os.environ.get("REUSE_RUN", "").strip()
RUN = (Path(REUSE) if REUSE else
       ROOT / "runs" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-channels-3way"))
RAW, CELLS, CMP = RUN / "raw", RUN / "cells", RUN / "compare"
UA = "OpenAI/Python 1.60.0"
TIMEOUT_S = 900

CHANNELS = [
    {"tag": "old", "label": "OLD · dklapi 旧 key · 0.16 元", "base": "https://dklapi.com/v1",
     "key_env": "IMAGE_RELAY_KEY_1K", "model": "gpt-image-2.5-sunburst", "size": "2048x1152",
     "price": 0.16},
    {"tag": "dkl2", "label": "DKL 新 key · 0.015 元", "base": "https://dklapi.com/v1",
     "key_env": "IMAGE_API_KEY_DKL2", "model": "gpt-image-2.5-sunburst", "size": "2048x1152",
     "price": 0.015},
    {"tag": "new2", "label": "NEW2 · xxcapi · 0.018 元", "base": "https://xxcapi.com/v1",
     "key_env": "IMAGE_API_KEY_XXC", "model": "AZ-gpt-image-2.5-sunburst", "size": "1672x941",
     "price": 0.018},
    {"tag": "yy", "label": "YY · shagentai · 待核价", "base": "https://yy.shagentai.com/v1",
     "key_env": "IMAGE_API_KEY_YY", "model": "gpt-image-2.5", "size": "2048x1152",
     "price": None},
]

G_SHARED = (
    "A single 2x2 grid of four distinct cinematic stills, separated by thin black gutters "
    "6 px wide, each panel a complete 16:9 frame. One continuous world: the same hydrothermal-vent "
    "field on the deep seafloor, filmed within a few minutes. Identical palette and optics across "
    "all four panels: near-black teal-blue water full of fine suspended particles, amber ROV "
    "floodlight at about 3200 K as the only warm source, volumetric haze, photorealistic mineral "
    "and organic textures, high dynamic range, cinematic science-documentary still, deep focus "
    "where noted. No text, no letters, no numbers, no labels, no watermark, no extra borders."
)
G_PANELS = [
    "Panel 1 (top-left): wide establishing shot from 3 m above the seafloor. A cluster of "
    "exactly three black-smoker chimneys of different heights, the tallest at center-right, in "
    "almost black water; two ROV floodlights from the left rake the scene so the left faces of "
    "the chimneys glow warm amber while the right side falls into deep teal-black. A field of "
    "pale tube worms spreads across the middle ground. 24 mm lens, deep focus.",
    "Panel 2 (top-right): extreme close-up of a row of exactly five tube worms on a basalt "
    "ledge, their red-and-white plumes visible, one at the left edge softly out of focus in the "
    "foreground. Camera 20 cm away, 100 mm macro, razor-thin depth of field, warm rim light "
    "from the upper right, faint cool fill from below, wet reflective surfaces.",
    "Panel 3 (bottom-left): medium close-up inside the ROV work area. A black robotic "
    "manipulator arm enters from the lower left, its parallel jaws gripping a fist-sized piece "
    "of shimmering sulphide rock; visible hydraulic lines and scratched paint on the arm; the "
    "sample glows amber in the lamp beam against dark blue water. 35 mm, slight low angle.",
    "Panel 4 (bottom-right): tight shot of the tallest chimney's mouth: mineral crust in "
    "ochre, rust and pale grey, a translucent plume of superheated fluid rising and bending to "
    "the right in the current, exactly four tiny shrimp silhouettes clinging to the rim, soft "
    "backlight making the plume glow, water particles catching light. 85 mm, shallow depth.",
]
G_PROMPT = (G_SHARED + "\n" + "\n".join(G_PANELS) + "\n"
            "Continuity: all panels share the same site, light temperature and water colour; no panel "
            "repeats another panel's composition; no human figures; absolutely no text of any kind.")

S2_PROMPT = (
    "cinematic desaturated comic-panel space, mature simplified cel-shaded anime characters with "
    "normal proportions, cold grey-blue palette with exactly one controlled warm light source, "
    "ordinary lived-in urban interior, legible horror staging through space and objects, clear "
    "foreground subject and props, slight off-center composition, volumetric dust, 16:9, sharp "
    "clean line work, rich material texture, no text, no letters, no numbers, no labels, no UI, "
    "no watermark, no gore, no chibi proportions, no photorealistic faces. Extreme close-up on a "
    "dark wooden table: a hand holds a crumpled paper receipt with faint illegible grey print "
    "lines (no readable characters at all), beside a cheap ballpoint pen and a chipped ceramic "
    "cup. Warm lamp light from the left, cold window light from the right, shallow depth of "
    "field, 100 mm macro, crisp paper fibre and skin texture."
)

S1_PROMPT = (
    "cinematic desaturated comic-panel space, mature simplified cel-shaded anime characters with "
    "normal proportions, cold grey-blue palette with exactly one controlled warm light source, "
    "ordinary lived-in urban interior, legible horror staging through space and objects, clear "
    "foreground subject and props, slight off-center composition, volumetric dust, 16:9, sharp "
    "clean line work, rich material texture, no text, no letters, no numbers, no labels, no UI, "
    "no watermark, no gore, no chibi proportions, no photorealistic faces. Full-body shot of a "
    "mature cel-shaded anime man in his thirties, short black hair, grey wool coat over a dark "
    "shirt, standing still in the doorway of a dim apartment, facing the camera. His right hand "
    "is raised at chest height holding a small brass key ring with two keys, fingers clearly "
    "separated and anatomically correct. Behind him a single warm desk lamp lights one wall; the "
    "rest of the room is cold blue shadow. Eye level camera, 50 mm."
)

PROMPTS = [
    {"tag": "G-grid", "title": "G · 复杂 2x2 深海四格（与 11-09 基准同词）", "prompt": G_PROMPT, "grid": True},
    {"tag": "S2-evidence", "title": "S2 · 悬疑证据特写（手/纸/浅景深）", "prompt": S2_PROMPT, "grid": False},
    {"tag": "S1-person", "title": "S1 · 悬疑人物全身（持钥匙的手）", "prompt": S1_PROMPT, "grid": False},
]

FONT_PATHS = [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\arial.ttf",
              r"C:\Windows\Fonts\segoeui.ttf"]
INSET = 4


def font(size: int):
    for path in FONT_PATHS:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def key_for(env_name: str) -> str | None:
    value = os.environ.get(env_name, "").strip()
    if value:
        return value
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
            return winreg.QueryValueEx(handle, env_name)[0]
    except OSError:
        return None


def probe_models(channel: dict, key: str) -> dict:
    request = urllib.request.Request(
        f"{channel['base']}/models",
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json", "User-Agent": UA})
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
            ids = sorted({item.get("id", "") for item in (body.get("data") or [])})
            return {"http_status": response.status, "models": ids,
                    "elapsed_s": round(time.time() - started, 1)}
    except urllib.error.HTTPError as exc:
        return {"http_status": exc.code, "error": exc.read()[:300].decode("utf-8", "replace"),
                "elapsed_s": round(time.time() - started, 1)}
    except Exception as exc:  # noqa: BLE001
        return {"http_status": None, "error": f"{type(exc).__name__}: {exc}",
                "elapsed_s": round(time.time() - started, 1)}


def download(url: str, dest: Path) -> None:
    """dklapi's CDN stalls on plain urllib; curl resumes and enforces its own cap."""
    curl = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "curl.exe"
    if curl.exists():
        result = subprocess.run(
            [str(curl), "-L", "--retry", "3", "--retry-delay", "2", "--max-time", "300",
             "-A", UA, "-o", str(dest), url],
            capture_output=True, text=True)
        if result.returncode == 0 and dest.exists() and dest.stat().st_size > 0:
            return
    with urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": UA}), timeout=300) as response:
        dest.write_bytes(response.read())


def call(channel: dict, prompt: str, label: str, key: str) -> dict:
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
        return {"channel": channel["tag"], "prompt": label, "ok": False,
                "http_status": None, "error": f"{type(exc).__name__}: {exc}"}
    elapsed = round(time.time() - started, 1)
    stem = f"{channel['tag']}-{label}"
    (RAW / f"{stem}-response.json").write_bytes(raw)
    info = {"channel": channel["tag"], "prompt": label, "http_status": status,
            "elapsed_s": elapsed, "request": payload, "channel_label": channel["label"]}
    if status != 200:
        info["ok"] = False
        try:
            info["error"] = json.loads(raw.decode("utf-8"))
        except Exception:
            info["error"] = raw[:400].decode("utf-8", "replace").replace(key, "[redacted]")
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
        info["error"] = "no b64_json / url in response"
        return info
    with Image.open(png) as image:
        image.load()
        info["dims"] = list(image.size)
    info.update({"ok": True, "bytes": png.stat().st_size,
                 "size_field": body.get("size"), "usage": body.get("usage")})
    return info


def lap_var(gray: np.ndarray) -> float:
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1]
           + gray[1:-1, :-2] + gray[1:-1, 2:])
    return float(lap.var())


def metrics(path: Path) -> dict:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        gray = np.asarray(rgb.convert("L"), dtype=np.float64)
        arr = np.asarray(rgb, dtype=np.float64)
        hsv = np.asarray(rgb.convert("HSV"), dtype=np.float64)
        delivery = np.asarray(rgb.resize((1920, 1080), Image.LANCZOS).convert("L"), dtype=np.float64)
    return {
        "dims": list(rgb.size),
        "lap_var": round(lap_var(gray), 1),
        "delivery_lap_var_1080p": round(lap_var(delivery), 1),
        "mean_lum": round(float(gray.mean()), 1),
        "std_lum": round(float(gray.std()), 1),
        "clip_high_pct": round(float((gray >= 254).mean() * 100), 2),
        "mean_sat": round(float(hsv[:, :, 1].mean()), 1),
        "mean_rgb": [round(float(arr[:, :, i].mean()), 1) for i in range(3)],
    }


def crop_cells(channel_tag: str, label: str) -> list[Path]:
    grid = RAW / f"{channel_tag}-{label}.png"
    with Image.open(grid) as image:
        image.load()
        width, height = image.size
        half_w, half_h = width // 2, height // 2
        boxes = [(INSET, INSET, half_w - INSET, half_h - INSET),
                 (half_w + INSET, INSET, width - INSET, half_h - INSET),
                 (INSET, half_h + INSET, half_w - INSET, height - INSET),
                 (half_w + INSET, half_h + INSET, width - INSET, height - INSET)]
        paths = []
        for index, box in enumerate(boxes, start=1):
            path = CELLS / f"{channel_tag}-{label}-p{index}.png"
            image.crop(box).save(path)
            paths.append(path)
    return paths


def error_tile(text: str, width: int = 640, height: int = 360) -> Image.Image:
    tile = Image.new("RGB", (width, height), (32, 26, 26))
    draw = ImageDraw.Draw(tile)
    draw.rectangle([4, 4, width - 5, height - 5], outline=(120, 60, 60), width=2)
    lines = text.split("\n")[:4]
    for i, line in enumerate(lines):
        draw.text((20, height // 2 - 40 + i * 30), line, fill=(235, 150, 150), font=font(20))
    return tile


def sheet(label: str, title: str) -> Path:
    width, height = 640, 360
    pad, header = 10, 54
    canvas = Image.new("RGB", (width * len(CHANNELS) + pad * (len(CHANNELS) + 1),
                               height + header + pad), (14, 14, 16))
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, 10), title, fill=(232, 232, 232), font=font(24))
    for index, channel in enumerate(CHANNELS):
        x = pad + index * (width + pad)
        path = RAW / f"{channel['tag']}-{label}.png"
        if path.exists():
            tile = Image.open(path).convert("RGB").resize((width, height), Image.LANCZOS)
        else:
            tile = error_tile(f"{channel['tag']}: 无图\n见 report.json")
        canvas.paste(tile, (x, header))
        draw.text((x, header - 20), channel["label"], fill=(240, 200, 120), font=font(17))
    out = CMP / f"sheet-{label}.png"
    canvas.save(out)
    return out


def panel_sheet(label: str, index: int) -> Path:
    size = 560
    pad, header = 10, 50
    canvas = Image.new("RGB", (size * len(CHANNELS) + pad * (len(CHANNELS) + 1), size + header + pad),
                       (14, 14, 16))
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, 10), f"{label} · 第 {index} 格（同尺寸缩放）", fill=(232, 232, 232), font=font(22))
    for i, channel in enumerate(CHANNELS):
        x = pad + i * (size + pad)
        path = CELLS / f"{channel['tag']}-{label}-p{index}.png"
        if path.exists():
            tile = Image.open(path).convert("RGB").resize((size, size), Image.LANCZOS)
        else:
            tile = error_tile(f"{channel['tag']}: 无图", size, size)
        canvas.paste(tile, (x, header))
        draw.text((x, header - 18), channel["label"], fill=(240, 200, 120), font=font(16))
    out = CMP / f"panel-{index}-{label}.png"
    canvas.save(out)
    return out


def main() -> int:
    for folder in (RAW, CELLS, CMP):
        folder.mkdir(parents=True, exist_ok=True)
    if REUSE and (RUN / "report.json").exists():
        report = json.loads((RUN / "report.json").read_text(encoding="utf-8"))
        print(f"resume: {RUN}", flush=True)
    else:
        report = {"started": datetime.now().isoformat(timespec="seconds"),
                  "channels": [], "results": [], "sheets": [], "panels": []}

    known = {entry["tag"] for entry in report["channels"]}
    for channel in CHANNELS:
        if channel["tag"] in known:
            continue
        key = key_for(channel["key_env"])
        entry = {k: channel[k] for k in ("tag", "label", "base", "model", "size", "key_env")}
        entry["key_present"] = bool(key)
        if key:
            entry["probe"] = probe_models(channel, key)
        report["channels"].append(entry)

    results = {(r["channel"], r["prompt"]): r for r in report["results"]}
    for prompt in PROMPTS:
        (RUN / f"prompt-{prompt['tag']}.txt").write_text(prompt["prompt"], encoding="utf-8")
        for channel in CHANNELS:
            png = RAW / f"{channel['tag']}-{prompt['tag']}.png"
            existing = results.get((channel["tag"], prompt["tag"]))
            if png.exists():
                if not (existing and existing.get("ok")):
                    with Image.open(png) as image:
                        dims = list(image.size)
                    results[(channel["tag"], prompt["tag"])] = {
                        "channel": channel["tag"], "prompt": prompt["tag"], "ok": True,
                        "http_status": 200, "elapsed_s": None, "dims": dims,
                        "channel_label": channel["label"],
                        "note": "图已存在，复用（耗时未知）"}
                continue
            key = key_for(channel["key_env"])
            if not key:
                info = {"channel": channel["tag"], "prompt": prompt["tag"], "ok": False,
                        "http_status": None, "error": f"{channel['key_env']} not set"}
            else:
                print(f"[{prompt['tag']}] {channel['tag']} -> {channel['model']}", flush=True)
                info = call(channel, prompt["prompt"], prompt["tag"], key)
            info["channel_label"] = channel["label"]
            results[(channel["tag"], prompt["tag"])] = info
            print(json.dumps({k: info.get(k) for k in
                              ("channel", "prompt", "http_status", "ok", "elapsed_s", "dims",
                               "bytes", "delivery", "error") if k in info},
                             ensure_ascii=False), flush=True)
            report["results"] = list(results.values())
            (RUN / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1),
                                             encoding="utf-8")

    report["results"] = list(results.values())
    grid = next(p for p in PROMPTS if p["grid"])
    for result in report["results"]:
        label = result["prompt"]
        channel = next(c for c in CHANNELS if c["tag"] == result["channel"])
        path = RAW / f"{channel['tag']}-{label}.png"
        result.pop("metrics", None)
        result.pop("cells", None)
        if not result.get("ok") or not path.exists():
            continue
        result["metrics"] = metrics(path)
        if label == grid["tag"]:
            result["cells"] = []
            for index, cell in enumerate(crop_cells(channel["tag"], label), start=1):
                m = metrics(cell)
                m["panel"] = index
                result["cells"].append(m)

    report["sheets"] = []
    for prompt in PROMPTS:
        label = prompt["tag"]
        if any((RAW / f"{c['tag']}-{label}.png").exists() for c in CHANNELS):
            report["sheets"].append(str(sheet(label, prompt["title"])))

    report["panels"] = []
    if sum((CELLS / f"{c['tag']}-{grid['tag']}-p1.png").exists() for c in CHANNELS) >= 2:
        for index in range(1, 5):
            report["panels"].append(str(panel_sheet(grid["tag"], index)))

    (RUN / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    write_markdown(report, PROMPTS)
    print(f"done: {RUN}", flush=True)
    return 0


def write_markdown(report: dict, prompts: list[dict]) -> None:
    lines = ["# 生图通道对比（dkl 旧 key / dkl 新 key / new2 xxcapi / yy shagentai）", ""]
    lines.append(f"- 运行时间：{report['started']}")
    lines.append("- 每通道每提示词 1 次调用，无重试；失败只记录，不静默跳过；已有图直接复用。")
    lines.append("")
    lines.append("## 1. 通道可用性")
    lines.append("")
    lines.append("| 通道 | 基址 | 模型 | 单价 | /models | 备注 |")
    lines.append("|---|---|---|---|---|---|")
    for channel in CHANNELS:
        entry = next(e for e in report["channels"] if e["tag"] == channel["tag"])
        probe = entry.get("probe") or {}
        models = probe.get("models")
        status = probe.get("http_status")
        price = f"{channel['price']} 元" if channel["price"] else "待核价"
        if status == 200 and models is not None:
            note = f"{len(models)} 个模型"
        else:
            note = str(probe.get("error", "no key"))[:100]
        lines.append(f"| {channel['tag']} | `{channel['base']}` | `{channel['model']}` | {price} | "
                     f"{status} | {note} |")
    lines.append("")
    lines.append("## 2. 出图结果与指标")
    lines.append("")
    lines.append("| 提示词 | 通道 | HTTP | 耗时 s | 尺寸 | 原生 lap_var | 交付 1080p lap_var | std_lum | 高光裁切 % | 饱和 |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for prompt in prompts:
        for channel in CHANNELS:
            result = next((r for r in report["results"]
                           if r["channel"] == channel["tag"] and r["prompt"] == prompt["tag"]), None)
            if not result:
                continue
            m = result.get("metrics") or {}
            dims = m.get("dims") or result.get("dims") or "—"
            lines.append(f"| {prompt['tag']} | {channel['tag']} | {result.get('http_status')} | "
                         f"{result.get('elapsed_s')} | {dims} | {m.get('lap_var', '—')} | "
                         f"{m.get('delivery_lap_var_1080p', '—')} | {m.get('std_lum', '—')} | "
                         f"{m.get('clip_high_pct', '—')} | {m.get('mean_sat', '—')} |")
    lines.append("")
    lines.append("## 3. 2x2 拆格指标（G-grid，交付 1080p 锐度）")
    lines.append("")
    lines.append("| 通道 | P1 | P2 | P3 | P4 |")
    lines.append("|---|---|---|---|---|")
    for channel in CHANNELS:
        result = next((r for r in report["results"]
                       if r["channel"] == channel["tag"] and r["prompt"] == "G-grid"), None)
        cells = (result or {}).get("cells") or []
        if not cells:
            lines.append(f"| {channel['tag']} | — | — | — | — |")
            continue
        vals = [str(c.get("delivery_lap_var_1080p", "—")) for c in cells]
        lines.append(f"| {channel['tag']} | " + " | ".join(vals) + " |")
    lines.append("")
    lines.append("## 4. 对照图")
    lines.append("")
    for item in report["sheets"] + report["panels"]:
        lines.append(f"- `{Path(item).relative_to(RUN).as_posix()}`")
    lines.append("")
    (RUN / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
