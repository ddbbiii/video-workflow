# -*- coding: utf-8 -*-
"""Probe a new relay (yy.shagentai.com) with two 2x2 grid prompts.

Why two grids: one reuses the exact hydrothermal-vent 2x2 prompt used in the
2026-11-09 three-way A/B, so the sharpness numbers are directly comparable with
OLD dklapi (lap 839) and NEW1 mxwell (lap 311); the second is a different subject
class (interior + mechanical + highlight handling) to see whether the channel's
weakness is prompt-specific.

Key comes from IMAGE_API_KEY_YY only (never printed, never written to disk).
Outputs under runs/<ts>-yy-grid2x2/:
  raw/*-response.json, raw/*-grid.png, cells/*-p1..p4.png, compare/full-*.png,
  report.json, REPORT.md
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE = os.environ.get("YY_BASE", "https://yy.shagentai.com/v1").rstrip("/")
ROOT = Path(__file__).resolve().parent
RUN = ROOT / "runs" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-yy-grid2x2")
RAW, CELLS, CMP = RUN / "raw", RUN / "cells", RUN / "compare"
UA = "OpenAI/Python 1.60.0"
SIZE = os.environ.get("YY_SIZE", "2048x1152")
MODEL = os.environ.get("YY_MODEL", "")
INSET = 4
TIMEOUT_S = 600
FONT_PATHS = [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf"]

# --- prompt A: byte-identical to compare_grid_2x2.py (comparable to OLD 839 / NEW1 311) ---
A_SHARED = (
    "A single 2x2 grid of four distinct cinematic stills, separated by thin black gutters "
    "6 px wide, each panel a complete 16:9 frame. One continuous world: the same hydrothermal-vent "
    "field on the deep seafloor, filmed within a few minutes. Identical palette and optics across "
    "all four panels: near-black teal-blue water full of fine suspended particles, amber ROV "
    "floodlight at about 3200 K as the only warm source, volumetric haze, photorealistic mineral "
    "and organic textures, high dynamic range, cinematic science-documentary still, deep focus "
    "where noted. No text, no letters, no numbers, no labels, no watermark, no extra borders."
)
A_PANELS = [
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
PROMPT_A = (A_SHARED + "\n" + "\n".join(A_PANELS) + "\n"
            "Continuity: all panels share the same site, light temperature and water colour; no panel "
            "repeats another panel's composition; no human figures; absolutely no text of any kind.")

# --- prompt B: different subject class (interior, metal/glass structure, bright highlights) ---
B_SHARED = (
    "A single 2x2 grid of four distinct cinematic stills, separated by thin black gutters 6 px "
    "wide, each panel a complete 16:9 frame. One continuous world: an abandoned high-mountain "
    "observatory dome at blue hour, in the same building during one evening. Identical palette "
    "and optics across all four panels: cold slate-blue shadows, one warm tungsten work lamp as "
    "the only warm source, faint snow light through the slit, soft atmospheric haze, photorealistic "
    "painted-steel and glass textures, high dynamic range, cinematic documentary still. No text, "
    "no letters, no numbers, no labels, no watermark, no extra borders, no lens flares."
)
B_PANELS = [
    "Panel 1 (top-left): wide shot across the rotunda floor. A giant equatorial telescope mount "
    "dominates the frame, its cradle and counterweights silhouetted against the open dome slit; "
    "the circular rail track is visible in the floor; a single tungsten lamp on a tripod lights "
    "the lower-left corner and throws long shadows across dusty concrete. 20 mm, deep focus.",
    "Panel 2 (top-right): medium close-up of the telescope's gear housing and brass setting "
    "circle, machine bolts, oxidized paint, thin frost on the metal, the warm lamp raking from the "
    "left, cold blue rim from the slit behind. 50 mm, shallow depth.",
    "Panel 3 (bottom-left): interior of the control desk: analog dials, toggle switches, a "
    "rotary phone handset off the hook, a half-empty enamel mug, all surfaces dust-covered and "
    "cold-lit, warm pool of lamp light on the desk, no readable markings anywhere. 35 mm, slight "
    "high angle.",
    "Panel 4 (bottom-right): looking up through the open slit at deep indigo sky with a few "
    "stars and a thin band of milky cloud; the dome's steel edge frames the sky as a bright wedge, "
    "snow drifting in past the opening, the telescope's top edge dark in the foreground. 24 mm, "
    "deep focus, controlled highlights.",
]
PROMPT_B = (B_SHARED + "\n" + "\n".join(B_PANELS) + "\n"
            "Continuity: all four panels are the same observatory on the same evening, same lamp "
            "and same palette; each panel shows a different part of it; absolutely no text of any kind.")

TESTS = [
    {"tag": "a-vent", "prompt": PROMPT_A,
     "note": "与 2026-11-09 三站 A/B 完全同词；OLD lap 839 / NEW1 lap 311 可直接对照"},
    {"tag": "b-dome", "prompt": PROMPT_B,
     "note": "不同题材：室内金属/玻璃结构、高光控制、无文字仪表"},
]


def font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_PATHS:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def key() -> str:
    value = os.environ.get("IMAGE_API_KEY_YY", "").strip()
    if not value:
        raise SystemExit("FATAL: IMAGE_API_KEY_YY not set")
    return value


def request(path: str, payload: dict | None = None) -> tuple[int, bytes, dict]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload else None
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, method="POST" if data else "GET",
        headers={"Authorization": f"Bearer {key()}", "Content-Type": "application/json",
                 "Accept": "application/json", "User-Agent": UA},
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as response:
            return response.status, response.read(), {"headers": dict(response.headers),
                                                      "elapsed": round(time.time() - started, 1)}
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), {"headers": dict(exc.headers),
                                      "elapsed": round(time.time() - started, 1)}


def list_models() -> int:
    status, raw, meta = request("/models")
    print(f"GET {BASE}/models -> HTTP {status} in {meta['elapsed']}s")
    try:
        body = json.loads(raw.decode("utf-8"))
    except Exception:
        print(raw[:800].decode("utf-8", "replace").replace(key(), "[redacted]"))
        return 1
    if status != 200:
        print(json.dumps(body, ensure_ascii=False)[:1200].replace(key(), "[redacted]"))
        return 1
    ids = sorted({item.get("id", "") for item in (body.get("data") or [])})
    print(f"{len(ids)} models:")
    for name in ids:
        print("  " + name)
    return 0


def gen(tag: str, prompt: str) -> dict:
    payload = {"model": MODEL, "prompt": prompt, "size": SIZE, "n": 1}
    status, raw, meta = request("/images/generations", payload)
    (RAW / f"{tag}-response.json").write_bytes(raw)
    info = {"tag": tag, "http_status": status, "elapsed_s": meta["elapsed"],
            "request": {"model": MODEL, "size": SIZE, "n": 1}}
    if status != 200:
        info["ok"] = False
        try:
            info["error"] = json.loads(raw.decode("utf-8"))
        except Exception:
            info["error"] = raw[:600].decode("utf-8", "replace").replace(key(), "[redacted]")
        return info

    body = json.loads(raw.decode("utf-8"))
    item = (body.get("data") or [{}])[0]
    png = RAW / f"{tag}-grid.png"
    if item.get("b64_json"):
        png.write_bytes(base64.b64decode(item["b64_json"]))
        info["delivery"] = "b64_json"
    elif item.get("url"):
        info["delivery"] = "url"
        image_req = urllib.request.Request(item["url"], headers={"User-Agent": UA})
        with urllib.request.urlopen(image_req, timeout=TIMEOUT_S) as image_response:
            png.write_bytes(image_response.read())
    else:
        info["ok"] = False
        info["error"] = "no b64_json / url"
        return info

    with Image.open(png) as image:
        image.load()
        dims = list(image.size)
    info.update({"ok": True, "dims": dims, "bytes": png.stat().st_size,
                 "resp_size_field": body.get("size"), "quality": body.get("quality"),
                 "output_format": body.get("output_format"), "usage": body.get("usage"),
                 "top_keys": sorted(body.keys())})
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
        dims = list(image.size)
    return {
        "dims": dims,
        "lap_var": round(lap_var(gray), 1),
        "delivery_lap_var_1080p": round(lap_var(delivery), 1),
        "mean_lum": round(float(gray.mean()), 1),
        "std_lum": round(float(gray.std()), 1),
        "p01_lum": round(float(np.percentile(gray, 1)), 1),
        "p99_lum": round(float(np.percentile(gray, 99)), 1),
        "clip_high_pct": round(float((gray >= 254).mean() * 100), 2),
        "mean_sat": round(float(hsv[:, :, 1].mean()), 1),
        "mean_rgb": [round(float(arr[:, :, i].mean()), 1) for i in range(3)],
    }


def gutter_check(path: Path) -> dict:
    with Image.open(path) as image:
        gray = np.asarray(image.convert("L"), dtype=np.float64)
    height, width = gray.shape

    def band(samples) -> dict:
        arr = np.array(samples)
        return {"mean": round(float(arr.mean()), 1), "std": round(float(arr.std()), 1),
                "max": round(float(arr.max()), 1)}

    return {"v_seam": band(gray[:, width // 2 - 2: width // 2 + 3].ravel().tolist()),
            "h_seam": band(gray[height // 2 - 2: height // 2 + 3, :].ravel().tolist())}


def crop_cells(tag: str) -> list[Path]:
    with Image.open(RAW / f"{tag}-grid.png") as image:
        image.load()
        width, height = image.size
        half_w, half_h = width // 2, height // 2
        boxes = [(INSET, INSET, half_w - INSET, half_h - INSET),
                 (half_w + INSET, INSET, width - INSET, half_h - INSET),
                 (INSET, half_h + INSET, half_w - INSET, height - INSET),
                 (half_w + INSET, half_h + INSET, width - INSET, height - INSET)]
        paths = []
        for index, box in enumerate(boxes, start=1):
            path = CELLS / f"{tag}-p{index}.png"
            image.crop(box).save(path)
            paths.append(path)
    return paths


def sheet(tag: str, cells: list[Path]) -> Path:
    cell_w, cell_h = Image.open(cells[0]).size
    pad, header = 12, 46
    canvas = Image.new("RGB", (cell_w * 2 + pad * 3, cell_h * 2 + pad * 3 + header), (16, 16, 18))
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, 10), f"YY {tag}  ·  {MODEL}  ·  {SIZE}", fill=(230, 230, 230), font=font(26))
    for index, cell in enumerate(cells):
        x = pad + (index % 2) * (cell_w + pad)
        y = header + pad + (index // 2) * (cell_h + pad)
        canvas.paste(Image.open(cell).convert("RGB"), (x, y))
    out = CMP / f"full-{tag}.png"
    canvas.save(out)
    return out


def gate(info: dict, m: dict, policy: dict) -> tuple[bool, list[str]]:
    reasons = []
    if info.get("dims") != [2048, 1152]:
        reasons.append(f"size {info.get('dims')}")
    if m["std_lum"] < policy["std_lum"]:
        reasons.append(f"std_lum {m['std_lum']}")
    if m["lap_var"] < policy["lap_var"]:
        reasons.append(f"lap {m['lap_var']}")
    if m["delivery_lap_var_1080p"] < policy["delivery_lap"]:
        reasons.append(f"delivery_lap {m['delivery_lap_var_1080p']}")
    return not reasons, reasons


def main() -> int:
    for folder in (RAW, CELLS, CMP):
        folder.mkdir(parents=True, exist_ok=True)
    if not MODEL:
        raise SystemExit("FATAL: YY_MODEL not set")
    policy = {"std_lum": 18, "lap_var": 60, "delivery_lap": 15}
    report = {"base": BASE, "model": MODEL, "size": SIZE, "inset_px": INSET,
              "started": datetime.now().isoformat(timespec="seconds"),
              "tests": [], "policy_gate": policy}
    for test in TESTS:
        tag = test["tag"]
        (RUN / f"prompt-{tag}.txt").write_text(test["prompt"], encoding="utf-8")
        print(f"[{tag}] POST {BASE}/images/generations  model={MODEL} size={SIZE}", flush=True)
        info = gen(tag, test["prompt"])
        entry = {"tag": tag, "note": test["note"], "call": info}
        print(json.dumps({k: info.get(k) for k in
                          ("http_status", "ok", "elapsed_s", "dims", "bytes", "delivery",
                           "resp_size_field", "usage", "error") if k in info},
                         ensure_ascii=False), flush=True)
        report["tests"].append(entry)
        (RUN / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
        if not info.get("ok"):
            print(f"[{tag}] FAILED, stopping before spending the second call", flush=True)
            return 1

    for entry in report["tests"]:
        tag = entry["tag"]
        cells = crop_cells(tag)
        entry["grid_metrics"] = metrics(RAW / f"{tag}-grid.png")
        entry["gutter"] = gutter_check(RAW / f"{tag}-grid.png")
        entry["cells"] = []
        for index, cell in enumerate(cells, start=1):
            m = metrics(cell)
            m["panel"] = index
            m["file"] = str(cell)
            m["delivery_lap_var_1080p"] = round(
                lap_var(np.asarray(Image.open(cell).convert("RGB").resize((1920, 1080),
                                                                          Image.LANCZOS)
                                   .convert("L"), dtype=np.float64)), 1)
            entry["cells"].append(m)
        entry["sheet"] = str(sheet(tag, cells))
        passed, reasons = gate(entry["call"], entry["grid_metrics"], policy)
        entry["gate_pass"] = passed
        entry["gate_reasons"] = reasons
        print(json.dumps({"tag": tag, "grid": entry["grid_metrics"], "gate_pass": passed,
                          "reasons": reasons}, ensure_ascii=False), flush=True)
    (RUN / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    print(f"done: {RUN}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(list_models() if "--models" in sys.argv else main())
