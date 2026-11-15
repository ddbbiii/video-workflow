# -*- coding: utf-8 -*-
"""Three-channel 2x2 grid A/B: dkl old (0.16) / dkl new key (0.015) / new2 xxcapi (0.018).

Same model family, same two 2x2 prompts, one call per channel per prompt, no retry.
Every failure is recorded so a dead relay never blocks the matrix.

Prompts:
  G-grid  deep-sea 4-panel grid (verbatim from the 2026-11-09 benchmark)
  S-grid  suspense character grid, same man in four scenes (identity + prop check)

Outputs under runs/<ts>-dkl3way-2x2/:
  raw/<channel>-<prompt>.png|.json
  cells/<channel>-<prompt>-p1..p4.png
  compare/sheet-<prompt>.png       3 columns, labelled
  compare/panel-<n>-<prompt>.png   per panel 100%
  report.json, REPORT.md

Keys: env first, then HKCU\\Environment. Never printed, never written to disk.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
import winreg
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
RUN_OVERRIDE = os.environ.get("RUN_DIR", "").strip()
RUN = (Path(RUN_OVERRIDE) if RUN_OVERRIDE else
       ROOT / "runs" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-dkl3way-2x2"))
RAW, CELLS, CMP = RUN / "raw", RUN / "cells", RUN / "compare"
UA = "OpenAI/Python 1.60.0"
TIMEOUT_S = 900
INSET = 4

CHANNELS = [
    {"tag": "dkl-old", "label": "DKL 旧 key · 0.16 元 · 2048x1152", "base": "https://dklapi.com/v1",
     "key_env": "IMAGE_RELAY_KEY_1K", "model": "gpt-image-2.5-sunburst", "size": "2048x1152",
     "price": 0.16},
    {"tag": "dkl-new", "label": "DKL 新 key · 0.015 元 · 2048x1152", "base": "https://dklapi.com/v1",
     "key_env": "IMAGE_API_KEY_DKL2", "model": "gpt-image-2.5-sunburst", "size": "2048x1152",
     "price": 0.015},
    {"tag": "new2", "label": "NEW2 xxcapi · 0.018 元 · 1672x941", "base": "https://xxcapi.com/v1",
     "key_env": "IMAGE_API_KEY_XXC", "model": "AZ-gpt-image-2.5-sunburst", "size": "1672x941",
     "price": 0.018},
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

S_PROMPT = (
    "A single 2x2 grid of four distinct cinematic stills, separated by thin dark gutters six "
    "pixels wide, each panel a complete 16:9 frame. The same character in every panel: mature "
    "simplified cel-shaded anime man, thirties, short black hair, grey wool coat over a dark "
    "shirt. Same cold grey-blue palette, one warm lamp as the only warm source, ordinary lived-in "
    "urban interior, legible staging, clean line work, rich material texture, no text, no letters, "
    "no numbers, no labels, no UI, no watermark, no gore, no chibi proportions, no photorealistic "
    "faces. "
    "Panel 1 (top-left): he stands in a dim apartment corridor facing the camera, one hand in his "
    "coat pocket, a door ajar behind him with warm light spilling on the floor. "
    "Panel 2 (top-right): medium shot from behind his shoulder as he looks at a desk lamp and a "
    "scattered stack of papers, his face in profile lit by the lamp. "
    "Panel 3 (bottom-left): close-up of his hand turning a brass door key in a lock, cold light "
    "from the left rimming the metal, his coat cuff visible. "
    "Panel 4 (bottom-right): he sits on the edge of a bed in a dark room, elbows on knees, face "
    "half in shadow, one warm bedside lamp behind him. "
    "Continuity: identical face, hair, coat length and belt in all four panels; no panel repeats "
    "another panel's composition."
)

PROMPTS = [
    {"tag": "G-grid", "title": "G · 深海热液 2x2（11-09 基准同词）", "prompt": G_PROMPT},
    {"tag": "S-grid", "title": "S · 悬疑人物 2x2（同一角色四场景）", "prompt": S_PROMPT},
]

FONT_PATHS = [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\arial.ttf",
              r"C:\Windows\Fonts\segoeui.ttf"]


def font(size: int):
    for path in FONT_PATHS:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def key_for(env_name: str) -> tuple[str | None, str | None]:
    value = os.environ.get(env_name, "").strip()
    if value:
        return env_name, value
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
            return env_name, winreg.QueryValueEx(handle, env_name)[0]
    except OSError:
        return None, None


def post_json(url: str, key: str, payload: dict) -> tuple[int, bytes, float]:
    request = urllib.request.Request(
        url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "Accept": "application/json", "User-Agent": UA})
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            return response.status, response.read(), round(time.time() - started, 1)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), round(time.time() - started, 1)


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
        return {"http_status": exc.code, "error": exc.read()[:300].decode("utf-8", "replace")}
    except Exception as exc:  # noqa: BLE001
        return {"http_status": None, "error": f"{type(exc).__name__}: {exc}"}


def download(url: str, path: Path, attempts: int = 4) -> int:
    """Stream to disk with retries; the cheap relay's CDN drops mid-body."""
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        got = 0
        try:
            request = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response, \
                    open(path, "wb") as handle:
                while True:
                    chunk = response.read(1 << 20)
                    if not chunk:
                        break
                    handle.write(chunk)
                    got += len(chunk)
            if got > 200_000:
                return got
            last = RuntimeError(f"short body {got} bytes")
        except Exception as exc:  # noqa: BLE001
            last = exc
        print(f"    download attempt {attempt} failed: {type(last).__name__}: {last}", flush=True)
        time.sleep(3 * attempt)
    raise RuntimeError(f"download failed after {attempts} attempts: {last}")


def call(channel: dict, prompt: dict, key: str) -> dict:
    payload = {"model": channel["model"], "prompt": prompt["prompt"],
               "size": channel["size"], "n": 1}
    stem = f"{channel['tag']}-{prompt['tag']}"
    info = {"channel": channel["tag"], "prompt": prompt["tag"], "request": payload}
    try:
        status, raw, elapsed = post_json(f"{channel['base']}/images/generations", key, payload)
        (RAW / f"{stem}-response.json").write_bytes(raw)
        info.update({"http_status": status, "elapsed_s": elapsed})
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
            info["bytes_downloaded"] = download(item["url"], png)
        else:
            info["ok"] = False
            info["error"] = "no b64_json / url in response"
            return info
        with Image.open(png) as image:
            image.load()
            info["dims"] = list(image.size)
        info.update({"ok": True, "bytes": png.stat().st_size,
                     "size_field": body.get("size"), "usage": body.get("usage")})
    except Exception as exc:  # noqa: BLE001
        info.update({"ok": False, "http_status": info.get("http_status"),
                     "error": f"{type(exc).__name__}: {exc}"[:300]})
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
        delivery = np.asarray(rgb.resize((1920, 1080), Image.LANCZOS).convert("L"),
                              dtype=np.float64)
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


def error_tile(text: str) -> Image.Image:
    tile = Image.new("RGB", (640, 360), (32, 26, 26))
    draw = ImageDraw.Draw(tile)
    draw.rectangle([4, 4, 635, 355], outline=(120, 60, 60), width=2)
    draw.text((20, 160), text, fill=(235, 150, 150), font=font(22))
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
        tile = (Image.open(path).convert("RGB").resize((width, height), Image.LANCZOS)
                if path.exists() else error_tile(f"{channel['tag']}: 无图"))
        canvas.paste(tile, (x, header))
        draw.text((x, header - 20), channel["label"], fill=(240, 200, 120), font=font(17))
    out = CMP / f"sheet-{label}.png"
    canvas.save(out)
    return out


def panel_sheet(label: str, index: int) -> Path:
    size, pad, header = 560, 10, 50
    canvas = Image.new("RGB", (size * len(CHANNELS) + pad * (len(CHANNELS) + 1),
                               size + header + pad), (14, 14, 16))
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, 10), f"{label} · 第 {index} 格 100%（同尺寸缩放）",
              fill=(232, 232, 232), font=font(22))
    for i, channel in enumerate(CHANNELS):
        x = pad + i * (size + pad)
        path = CELLS / f"{channel['tag']}-{label}-p{index}.png"
        tile = (Image.open(path).convert("RGB").resize((size, size), Image.LANCZOS)
                if path.exists() else error_tile(f"{channel['tag']}: 无图"))
        canvas.paste(tile, (x, header))
        draw.text((x, header - 18), channel["label"], fill=(240, 200, 120), font=font(16))
    out = CMP / f"panel-{index}-{label}.png"
    canvas.save(out)
    return out


def fmt_error(info: dict) -> str:
    err = info.get("error")
    if isinstance(err, dict):
        inner = err.get("error") or {}
        return str(inner.get("code") or inner.get("message") or err)[:160]
    return str(err)[:160]


def main() -> int:
    for folder in (RAW, CELLS, CMP):
        folder.mkdir(parents=True, exist_ok=True)
    report = {"started": datetime.now().isoformat(timespec="seconds"),
              "channels": [], "results": [], "sheets": [], "panels": []}
    state_file = RUN / "report.json"

    for channel in CHANNELS:
        key_name, key = key_for(channel["key_env"])
        entry = {k: channel[k] for k in ("tag", "label", "base", "model", "size", "price")}
        entry["key_env"] = channel["key_env"]
        entry["key_present"] = bool(key)
        if key:
            entry["probe"] = probe_models(channel, key)
        report["channels"].append(entry)
        print(f"probe {channel['tag']}: {json.dumps(entry.get('probe'), ensure_ascii=False)}",
              flush=True)
    state_file.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    previous = {}
    if state_file.exists():
        try:
            old_report = json.loads(state_file.read_text(encoding="utf-8"))
            previous = {(r["channel"], r["prompt"]): r for r in old_report.get("results", [])}
        except Exception:  # noqa: BLE001
            previous = {}

    for prompt in PROMPTS:
        (RUN / f"prompt-{prompt['tag']}.txt").write_text(prompt["prompt"], encoding="utf-8")
        for channel in CHANNELS:
            _, key = key_for(channel["key_env"])
            png = RAW / f"{channel['tag']}-{prompt['tag']}.png"
            prior = previous.get((channel["tag"], prompt["tag"]))
            dims = None
            if png.exists() and png.stat().st_size > 200_000:
                try:
                    with Image.open(png) as image:
                        image.load()
                        dims = list(image.size)
                except Exception:  # noqa: BLE001
                    png.unlink(missing_ok=True)
                    dims = None
            if dims:
                info = {"channel": channel["tag"], "prompt": prompt["tag"], "ok": True,
                        "http_status": 200, "reused": True, "dims": dims,
                        "bytes": png.stat().st_size,
                        "delivery": (prior or {}).get("delivery"),
                        "elapsed_s": (prior or {}).get("elapsed_s")}
                print(f"[{prompt['tag']}] {channel['tag']} reused {dims}", flush=True)
            elif not key:
                info = {"channel": channel["tag"], "prompt": prompt["tag"], "ok": False,
                        "http_status": None, "error": f"{channel['key_env']} not set"}
            else:
                print(f"[{prompt['tag']}] {channel['tag']} -> {channel['model']} "
                      f"{channel['size']}", flush=True)
                info = call(channel, prompt, key)
            info["channel_label"] = channel["label"]
            report["results"].append(info)
            print("  " + json.dumps({k: info.get(k) for k in
                                     ("http_status", "ok", "elapsed_s", "dims", "bytes",
                                      "delivery", "error") if k in info}, ensure_ascii=False),
                  flush=True)
            state_file.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                                  encoding="utf-8")

    for prompt in PROMPTS:
        label = prompt["tag"]
        for channel in CHANNELS:
            path = RAW / f"{channel['tag']}-{label}.png"
            result = next((r for r in report["results"]
                           if r["channel"] == channel["tag"] and r["prompt"] == label), None)
            if result is None or not result.get("ok") or not path.exists():
                continue
            result["metrics"] = metrics(path)
            result["cells"] = []
            for index, cell in enumerate(crop_cells(channel["tag"], label), start=1):
                m = metrics(cell)
                m["panel"] = index
                result["cells"].append(m)
        state_file.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    for prompt in PROMPTS:
        label = prompt["tag"]
        if any((RAW / f"{c['tag']}-{label}.png").exists() for c in CHANNELS):
            report["sheets"].append(str(sheet(label, prompt["title"])))
        if all((CELLS / f"{c['tag']}-{label}-p1.png").exists() for c in CHANNELS):
            for index in range(1, 5):
                report["panels"].append(str(panel_sheet(label, index)))

    state_file.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    write_markdown(report, PROMPTS)
    print(f"done: {RUN}", flush=True)
    return 0


def write_markdown(report: dict, prompts: list[dict]) -> None:
    lines = ["# 三通道 2×2 生图对比（DKL 旧 key / DKL 新 key / new2）", ""]
    lines.append(f"- 运行时间：{report['started']}")
    lines.append("- 每通道每提示词 1 次调用，无重试；同模型 `gpt-image-2.5-sunburst` 系列，"
                 "2×2 四格提示词各一版。")
    lines.append("")
    lines.append("## 1. 通道")
    lines.append("")
    lines.append("| 通道 | 基址 | 模型 | 请求尺寸 | 单价 | key | /models |")
    lines.append("|---|---|---|---|---|---|---|")
    for entry in report["channels"]:
        probe = entry.get("probe") or {}
        models = probe.get("models")
        note = (f"{len(models)} 个：{', '.join(models[:6])}" if probe.get("http_status") == 200
                and models else str(probe.get("error", "no key"))[:90])
        lines.append(f"| {entry['tag']} | `{entry['base']}` | `{entry['model']}` | "
                     f"{entry['size']} | {entry['price']} 元 | {entry['key_env']} | {note} |")
    lines.append("")
    lines.append("## 2. 出图结果")
    lines.append("")
    lines.append("| 提示词 | 通道 | HTTP | 耗时 s | 实际尺寸 | 原生 lap_var | 交付 1080p lap_var | 饱和 | 高光裁切 % |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for prompt in prompts:
        for result in report["results"]:
            if result.get("prompt") != prompt["tag"]:
                continue
            m = result.get("metrics") or {}
            dims = m.get("dims") or result.get("dims") or "—"
            status = result.get("http_status")
            lines.append(f"| {prompt['tag']} | {result['channel']} | {status} | "
                         f"{result.get('elapsed_s')} | {dims} | {m.get('lap_var', '—')} | "
                         f"{m.get('delivery_lap_var_1080p', '—')} | {m.get('mean_sat', '—')} | "
                         f"{m.get('clip_high_pct', '—')} |")
    lines.append("")
    lines.append("## 3. 每格交付锐度（1080p lap_var，格内 100%）")
    lines.append("")
    header = "| 提示词 | 格 | " + " | ".join(c["tag"] for c in CHANNELS) + " |"
    lines.append(header)
    lines.append("|---|---|" + "---|" * len(CHANNELS))
    for prompt in prompts:
        for index in range(1, 5):
            cells = " | ".join(
                str((next((r for r in report["results"]
                           if r["channel"] == c["tag"] and r["prompt"] == prompt["tag"]
                           and r.get("cells")), None) or {}).get("cells", [{}] * 4)[index - 1]
                    .get("delivery_lap_var_1080p", "—"))
                for c in CHANNELS)
            lines.append(f"| {prompt['tag']} | p{index} | {cells} |")
    lines.append("")
    lines.append("## 4. 对照图")
    lines.append("")
    for item in report["sheets"] + report["panels"]:
        lines.append(f"- `{Path(item).relative_to(RUN).as_posix()}`")
    lines.append("")
    (RUN / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
