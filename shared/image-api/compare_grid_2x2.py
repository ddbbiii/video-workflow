# -*- coding: utf-8 -*-
"""A/B a single complex 2x2 grid prompt on two relays, then compare.

Old (production): https://dklapi.com/v1  key IMAGE_RELAY_KEY_1K
New (candidate):  https://api.mxwell.ai/v1 key IMAGE_API_KEY_MX

Same model, same size, same prompt, one call each (no retry). Outputs:
  raw/<tag>-grid.png            full 2048x1152 grid
  raw/<tag>-response.json       raw API payload
  cells/<tag>-p1..p4.png        cells cropped with a 4 px inset (rule: 3-4 px)
  compare/full-<tag>.png        labelled 2x2 contact sheet
  compare/panel-<n>-ab.png      old | new side by side for panel n
  report.json                   timings, dims, bytes, sharpness/color metrics
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
RUN = ROOT / "runs" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-grid2x2-ab")
RAW = RUN / "raw"
CELLS = RUN / "cells"
CMP = RUN / "compare"
MODEL = "gpt-image-2.5-sunburst"
SIZE = "2048x1152"
INSET = 4
TIMEOUT_S = 600
UA = "OpenAI/Python 1.60.0"

TARGETS = [
    {"tag": "old", "base": "https://dklapi.com/v1",
     "env": ("IMAGE_RELAY_KEY_1K",), "reg": ("IMAGE_RELAY_KEY_1K",)},
    {"tag": "new", "base": "https://api.mxwell.ai/v1",
     "env": ("MXWELL_API_KEY",), "reg": ("IMAGE_API_KEY_MX",)},
]

SHARED = (
    "A single 2x2 grid of four distinct cinematic stills, separated by thin black gutters "
    "6 px wide, each panel a complete 16:9 frame. One continuous world: the same hydrothermal-vent "
    "field on the deep seafloor, filmed within a few minutes. Identical palette and optics across "
    "all four panels: near-black teal-blue water full of fine suspended particles, amber ROV "
    "floodlight at about 3200 K as the only warm source, volumetric haze, photorealistic mineral "
    "and organic textures, high dynamic range, cinematic science-documentary still, deep focus "
    "where noted. No text, no letters, no numbers, no labels, no watermark, no extra borders."
)
PANELS = [
    (
        "Panel 1 (top-left): wide establishing shot from 3 m above the seafloor. A cluster of "
        "exactly three black-smoker chimneys of different heights, the tallest at center-right, in "
        "almost black water; two ROV floodlights from the left rake the scene so the left faces of "
        "the chimneys glow warm amber while the right side falls into deep teal-black. A field of "
        "pale tube worms spreads across the middle ground. 24 mm lens, deep focus."
    ),
    (
        "Panel 2 (top-right): extreme close-up of a row of exactly five tube worms on a basalt "
        "ledge, their red-and-white plumes visible, one at the left edge softly out of focus in the "
        "foreground. Camera 20 cm away, 100 mm macro, razor-thin depth of field, warm rim light "
        "from the upper right, faint cool fill from below, wet reflective surfaces."
    ),
    (
        "Panel 3 (bottom-left): medium close-up inside the ROV work area. A black robotic "
        "manipulator arm enters from the lower left, its parallel jaws gripping a fist-sized piece "
        "of shimmering sulphide rock; visible hydraulic lines and scratched paint on the arm; the "
        "sample glows amber in the lamp beam against dark blue water. 35 mm, slight low angle."
    ),
    (
        "Panel 4 (bottom-right): tight shot of the tallest chimney's mouth: mineral crust in "
        "ochre, rust and pale grey, a translucent plume of superheated fluid rising and bending to "
        "the right in the current, exactly four tiny shrimp silhouettes clinging to the rim, soft "
        "backlight making the plume glow, water particles catching light. 85 mm, shallow depth."
    ),
]
PROMPT = (
    SHARED + "\n" + "\n".join(PANELS) + "\n"
    "Continuity: all panels share the same site, light temperature and water colour; no panel "
    "repeats another panel's composition; no human figures; absolutely no text of any kind."
)

FONT_PATHS = [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf"]


def font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_PATHS:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def get_key(env_names: tuple[str, ...], reg_names: tuple[str, ...]) -> tuple[str | None, str | None]:
    for name in env_names:
        value = os.environ.get(name)
        if value:
            return name, value
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
            for name in reg_names:
                try:
                    return name, winreg.QueryValueEx(handle, name)[0]
                except FileNotFoundError:
                    continue
    except OSError:
        pass
    return None, None


def call_base(base: str, key: str, prompt: str, size: str, tag: str) -> dict:
    payload = json.dumps({"model": MODEL, "prompt": prompt, "size": size, "n": 1},
                         ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{base}/images/generations", data=payload, method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "Accept": "application/json", "User-Agent": UA},
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            raw = response.read()
            status = response.status
            headers = dict(response.headers)
    except urllib.error.HTTPError as exc:
        raw, status, headers = exc.read(), exc.code, dict(exc.headers)
    elapsed = round(time.time() - started, 1)
    (RAW / f"{tag}-response.json").write_bytes(raw)
    info = {"tag": tag, "base": base, "http_status": status, "elapsed_s": elapsed,
            "content_type_event": headers.get("Content-Type")}
    if status != 200:
        info["ok"] = False
        try:
            info["error"] = json.loads(raw.decode("utf-8"))
        except Exception:
            info["error"] = raw[:500].decode("utf-8", "replace").replace(key, "[redacted]")
        return info

    data = json.loads(raw.decode("utf-8"))
    item = (data.get("data") or [{}])[0]
    png = RAW / f"{tag}-grid.png"
    if item.get("b64_json"):
        png.write_bytes(base64.b64decode(item["b64_json"]))
        info["delivery"] = "b64_json"
    elif item.get("url"):
        info["delivery"] = "url"
        with urllib.request.urlopen(item["url"], timeout=TIMEOUT_S) as image_response:
            png.write_bytes(image_response.read())
    else:
        info["ok"] = False
        info["error"] = "no b64_json / url"
        return info

    with Image.open(png) as image:
        image.load()
        dims = image.size
    info.update({"ok": True, "dims": list(dims), "bytes": png.stat().st_size,
                 "size_field": data.get("size"), "quality": data.get("quality"),
                 "output_format": data.get("output_format"), "usage": data.get("usage"),
                 "keys": sorted(data.keys())})
    return info


def crop_cells(tag: str) -> list[Path]:
    grid = RAW / f"{tag}-grid.png"
    with Image.open(grid) as image:
        image.load()
        width, height = image.size
        half_w, half_h = width // 2, height // 2
        boxes = [
            (INSET, INSET, half_w - INSET, half_h - INSET),
            (half_w + INSET, INSET, width - INSET, half_h - INSET),
            (INSET, half_h + INSET, half_w - INSET, height - INSET),
            (half_w + INSET, half_h + INSET, width - INSET, height - INSET),
        ]
        paths = []
        for index, box in enumerate(boxes, start=1):
            path = CELLS / f"{tag}-p{index}.png"
            image.crop(box).save(path)
            paths.append(path)
    return paths


def metrics(path: Path) -> dict:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        gray = np.asarray(rgb.convert("L"), dtype=np.float64)
        arr = np.asarray(rgb, dtype=np.float64)
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1]
           + gray[1:-1, :-2] + gray[1:-1, 2:])
    hsv = np.asarray(Image.open(path).convert("HSV"), dtype=np.float64)
    return {
        "sharpness_lap_var": round(float(lap.var()), 1),
        "mean_lum": round(float(gray.mean()), 1),
        "std_lum": round(float(gray.std()), 1),
        "p01_lum": round(float(np.percentile(gray, 1)), 1),
        "p99_lum": round(float(np.percentile(gray, 99)), 1),
        "mean_sat": round(float(hsv[:, :, 1].mean()), 1),
        "mean_rgb": [round(float(arr[:, :, i].mean()), 1) for i in range(3)],
    }


def gutter_check(path: Path, tag: str) -> dict:
    """The seam of a 2x2 grid must be a thin dark gutter, not a bright band."""
    with Image.open(path) as image:
        gray = np.asarray(image.convert("L"), dtype=np.float64)
    height, width = gray.shape

    def band(samples: list[float]) -> dict:
        arr = np.array(samples)
        return {"mean": round(float(arr.mean()), 1), "std": round(float(arr.std()), 1),
                "max": round(float(arr.max()), 1)}

    return {
        "v_seam": band(gray[:, width // 2 - 2: width // 2 + 3].ravel().tolist()),
        "h_seam": band(gray[height // 2 - 2: height // 2 + 3, :].ravel().tolist()),
    }


def sheet(tag: str, cells: list[Path]) -> Path:
    cell_w, cell_h = Image.open(cells[0]).size
    pad, header = 12, 44
    canvas = Image.new("RGB", (cell_w * 2 + pad * 3, cell_h * 2 + pad * 3 + header), (16, 16, 18))
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, 10), f"{tag.upper()}  ·  {MODEL}  ·  {SIZE}", fill=(230, 230, 230), font=font(26))
    for index, cell in enumerate(cells):
        x = pad + (index % 2) * (cell_w + pad)
        y = header + pad + (index // 2) * (cell_h + pad)
        canvas.paste(Image.open(cell).convert("RGB"), (x, y))
    out = CMP / f"full-{tag}.png"
    canvas.save(out)
    return out


def side_by_side(old_cell: Path, new_cell: Path, index: int) -> Path:
    width, height = Image.open(old_cell).size
    pad, header = 10, 40
    canvas = Image.new("RGB", (width * 2 + pad * 3, height + pad * 2 + header), (16, 16, 18))
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, 8), f"OLD  ·  dklapi", fill=(235, 235, 235), font=font(24))
    draw.text((pad * 2 + width, 8), "NEW  ·  mxwell", fill=(235, 235, 235), font=font(24))
    canvas.paste(Image.open(old_cell).convert("RGB"), (pad, header + pad))
    canvas.paste(Image.open(new_cell).convert("RGB"), (pad * 2 + width, header + pad))
    out = CMP / f"panel-{index}-ab.png"
    canvas.save(out)
    return out


def main() -> int:
    for folder in (RAW, CELLS, CMP):
        folder.mkdir(parents=True, exist_ok=True)
    report = {"prompt": PROMPT, "model": MODEL, "size": SIZE, "inset_px": INSET,
              "started": datetime.now().isoformat(timespec="seconds"), "calls": [], "panels": [],
              "sheets": {}, "ab": [], "gutter": {}}
    (RUN / "prompt.txt").write_text(PROMPT, encoding="utf-8")

    for target in TARGETS:
        key_name, key = get_key(target["env"], target["reg"])
        if not key:
            print(f"FATAL: no key for {target['tag']}", flush=True)
            return 2
        print(f"[{target['tag']}] POST {target['base']}/images/generations", flush=True)
        info = call_base(target["base"], key, PROMPT, SIZE, target["tag"])
        info["key_source"] = key_name
        report["calls"].append(info)
        print(json.dumps({k: info[k] for k in info if k in
                          ("tag", "http_status", "ok", "elapsed_s", "dims", "bytes", "delivery")},
                         ensure_ascii=False), flush=True)
        (RUN / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        if not info.get("ok"):
            return 1

    for target in TARGETS:
        tag = target["tag"]
        cells = crop_cells(tag)
        for index, cell in enumerate(cells, start=1):
            report["panels"].append({"tag": tag, "panel": index, "file": str(cell),
                                     **metrics(cell)})
        report["gutter"][tag] = gutter_check(RAW / f"{tag}-grid.png", tag)
        report["sheets"][tag] = str(sheet(tag, cells))
        (RUN / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    old_cells = crop_cells("old")
    new_cells = crop_cells("new")
    for index, (old_cell, new_cell) in enumerate(zip(old_cells, new_cells), start=1):
        report["ab"].append(str(side_by_side(old_cell, new_cell, index)))
    (RUN / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report["gutter"], ensure_ascii=False), flush=True)
    print(f"done: {RUN}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
