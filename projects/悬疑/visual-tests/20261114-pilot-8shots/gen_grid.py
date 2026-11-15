# -*- coding: utf-8 -*-
"""2×2 网格对照：把 8 镜拆成两张 2×2（A/B 一张、C/D 一张），与单张版逐格对比。

口径：
- `rules/shared/image-grid-generation.md`：一次网格调用=一个通道；四格各有独立文案；
  统一世界观 + 逐格视觉事实 + 连续性 + 全局/格子专属禁止项；裁格内缩 3–4 px。
- `rules/悬疑/visual.md` §4.2：STYLE_POS →(CEL_BOOST)→ 构图语法 → 主体 → 三层 → 光线 → 证据 → 禁止 → Avoid: STYLE_NEG。
- 通道仍读 `channel-policy.json` 的 active（v6 → new2，1672×941；2×2 每格 836×471）。
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw

import gen_pilot as g

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw-grid"
CELLS = HERE / "cells"
OUT = HERE / "compare-2x2"
INSET = 4  # 裁格内缩

GRID_PREAMBLE = (
    "four-panel 2x2 storyboard grid on one square-grid canvas, four independent wide shots of the same "
    "old Chinese apartment building in a southern city, same cold grey-blue world, same worn surfaces, "
    "each panel a separate 16:9 composition with its own camera, equal quarters separated by thin dark "
    "gutters; no borders, no panel numbers, no captions, no text, no watermark"
)

# 每格独立文案：构图四件套 → 主体 → 三层 → 破败 → 光线 →（证据）
GRIDS = [
    {
        "tag": "G1", "name": "A+B：楼道 / 出租屋 / 门口 / 走廊尽端",
        "cel": True,
        "anchor": "zhouxu:front,side,face",
        "continuity": ("panels 3 and 4 show the same thin 14-year-old boy, same navy school jacket with white "
                       "piping, same grey trousers and white sneakers, same hair"),
        "cells": [
            ("P1", "A1", "camera medium at the stair landing, 24mm wide-angle, deep focus; empty fourth-floor corridor "
                         "receding to the right third, no people; foreground: rusted steel door frame with a strip of grey "
                         "duct tape pressing the left quarter; middle ground: yellowed plastic stool, drying rack with two "
                         "dark shirts, taped-over electrical box; background: far window at the corridor end, cold dusk "
                         "light; decay: peeling green paint along the skirting, dark water stain from the window frame, rust "
                         "on the hinge; light: cold window light, one warm light under a closed door on the left"),
            ("P2", "A2", "camera medium from the doorway, 24mm, deep focus; one rented single room, no people; foreground: "
                         "faded floral door curtain on the left edge with two strips of repair tape; middle ground: folding "
                         "table with two upside-down bowls and a thermos, blue plastic stool, slippers beside the bed; "
                         "background: steel window with laundry hanging outside; decay: wallpaper lifting in the corner, "
                         "cracked threshold tile, water ring on the sill; light: cold overcast window light, one warm desk lamp"),
            ("P3", "B1", "camera medium four metres back, 28mm, deep focus; the boy standing in the doorway on the left "
                         "third, back three-quarters, right hand on the frame, about one third of the panel height; "
                         "foreground: plaid curtain pressing the right quarter; middle ground: scuffed door leaf with a "
                         "taped repair, slippers inside the threshold; background: dark hall with one bathroom door ajar; "
                         "decay: peeling frame paint, water stain beside it, chipped threshold tile; light: cold corridor "
                         "light from behind, one warm light from the bathroom"),
            ("P4", "B2", "camera far, 24mm, deep focus; the same boy standing at the right third near the corridor end, back "
                         "three-quarters, looking at the half-open steel safety door; foreground: laundry pole with two dark "
                         "garments top left, metal railing bottom left; middle ground: cardboard boxes, plastic stool; "
                         "background: the safety door with cold light beyond; decay: peeling wall paint, long ceiling water "
                         "stain, rusted meter box; light: cold light through the door, one warm bulb above the left door"),
        ],
        "ban": ("no extra people, no text on any surface, no signs, no door numbers, no lettering on boxes or clothing, "
                "no panel borders inside a panel, no glitch bars"),
    },
    {
        "tag": "G2", "name": "C+D：桌面证据 / 手部持物 / 走廊尽头 / 楼梯井",
        "cel": True,
        "anchor": "zhouxu:front,face",
        "continuity": ("panel 2 shows the right hand of the same 14-year-old boy from the other grid; the brass key with "
                       "the faded red cord is the same key in panels 1 and 2"),
        "cells": [
            ("P1", "C1", "camera close, slightly above table height, 28mm, deep focus; one old brass key with a faded red "
                         "cord lying on a wooden table at the left third, the key at least a fifth of the panel width, no "
                         "people; foreground: woven placemat pressing the bottom right; middle ground: ring-shaped water "
                         "stain, cigarette burn, chipped enamel mug; background: dark kitchen doorway; decay: scratched "
                         "table, cracked floor tile; light: cold window light, one warm bulb above the table"),
            ("P2", "C2", "camera close, slightly above, 28mm, deep focus; the boy's right hand entering from the bottom "
                         "right, holding the same brass key upright between thumb and forefinger at the right third, the key "
                         "about a third of the panel height; foreground: curtain edge pressing the top left; middle ground: "
                         "scratched table, thermos lying on its side; background: dark kitchen doorway; decay: table water "
                         "stains, taped table edge, chipped enamel; light: cold window light, one warm bulb above the hand"),
            ("P3", "D1", "camera far, locked-off at chest height, 28mm, deep focus; corridor axis left of centre, no people; "
                         "foreground: rusted iron railing and a rolled bamboo blind pressing the right quarter; middle "
                         "ground: worn floor tiles, mop, plastic bucket; background: where a window should be a door stands "
                         "wide open and the same corridor continues behind it, same tiles, same four doors, another window "
                         "at its far end, cold light; decay: cracked floor tiles, long ceiling water stain, scuffed skirting; "
                         "light: cold daylight from the far end, one warm light at the left door crack"),
            ("P4", "D2", "camera far, locked-off, looking down the stairwell from the fifth-floor landing, 24mm, deep focus; "
                         "the well falls along the right third, no people; foreground: steel handrail with a towel over it "
                         "pressing the left quarter; middle ground: chipped concrete steps, meter box, mop; background: the "
                         "bottom landing where a single plastic stool faces the wall with an empty bowl on it, and that "
                         "landing has no door at all; decay: chipped step edges, water stains down the wall, rust on the "
                         "handrail; light: cold grey light from above, one warm bulb on the fifth-floor wall"),
        ],
        "ban": ("no extra people, no faces, no readable text, no engraving or numbers on the key, no labels or name plates, "
                "no blood, no glitch bars"),
    },
]


def build_prompt(grid: dict, pos: str, neg: str, cel: str) -> str:
    parts = [pos]
    if grid["cel"]:
        parts.append(cel)
    parts.append(GRID_PREAMBLE)
    for name, tag, text in grid["cells"]:
        parts.append(f"{name} ({ {'P1': 'top left', 'P2': 'top right', 'P3': 'bottom left', 'P4': 'bottom right'}[name] }) — shot {tag}: {text}")
    parts.append(f"continuity: {grid['continuity']}")
    parts.append(f"hard constraints: {grid['ban']}")
    return ", ".join(parts)


def split(grid_png: Path, tag: str) -> list[dict]:
    with Image.open(grid_png) as img:
        rgb = img.convert("RGB")
    width, height = rgb.size
    half_w, half_h = width // 2, height // 2
    boxes = {"P1": (0, 0, half_w, half_h), "P2": (half_w, 0, width, half_h),
             "P3": (0, half_h, half_w, height), "P4": (half_w, half_h, width, height)}
    out = []
    for name, (x0, y0, x1, y1) in boxes.items():
        box = (x0 + INSET, y0 + INSET, x1 - INSET, y1 - INSET)
        cell = rgb.crop(box)
        path = CELLS / f"{tag}-{name}.png"
        cell.save(path)
        out.append({"panel": name, "file": str(path.relative_to(HERE)).replace("\\", "/"),
                    "dims": list(cell.size)})
    return out


def measure(path: Path) -> dict:
    import numpy as np
    with Image.open(path) as image:
        rgb = image.convert("RGB")
    gray = np.asarray(rgb.convert("L"), dtype=np.float64)
    hsv = np.asarray(rgb.convert("HSV"), dtype=np.float64)
    delivery = np.asarray(rgb.resize((1920, 1080), Image.LANCZOS).convert("L"), dtype=np.float64)
    return {"std_lum": round(float(gray.std()), 1), "mean_sat": round(float(hsv[:, :, 1].mean()), 1),
            "lap_var": round(g.lap_var(gray), 1), "delivery_lap_var": round(g.lap_var(delivery), 1)}


def main() -> int:
    for directory in (RAW, CELLS, OUT):
        directory.mkdir(parents=True, exist_ok=True)
    g.RAW = RAW  # g.call 写到 raw-grid/，不覆盖单张图
    pos, neg, cel = g.read_block("STYLE_POS"), g.read_block("STYLE_NEG"), g.read_block("CEL_BOOST")
    channel = g.active_channel()
    print(f"channel={channel['name']} policy={channel['policy']} size={channel['size']}", flush=True)

    results = []
    for grid in GRIDS:
        prompt = build_prompt(grid, pos, neg, cel)
        anchor = g.build_anchor(grid["anchor"]) if grid["anchor"] else None
        stem = {"tag": grid["tag"], "kind": grid["name"], "prompt": prompt,
                "anchor": str(anchor) if anchor else ""}
        info = g.call(channel, prompt, stem, anchor, 1)
        print(f"  {grid['tag']}: {'OK' if info.get('ok') else 'FAIL'} {info.get('elapsed_s', '-')}s "
              f"{info.get('dims', '')} {info.get('error', '')}", flush=True)
        if not info.get("ok"):
            results.append({**stem, "ok": False, "error": info.get("error")})
            continue
        png = HERE / info["file"]
        cells = split(png, grid["tag"])
        for cell in cells:
            cell["metrics"] = measure(HERE / cell["file"])
            cell["shot"] = grid["cells"][int(cell["panel"][1]) - 1][1]
            print("   ", cell["shot"], cell["dims"], cell["metrics"], flush=True)
        results.append({**stem, "ok": True, "dims": info.get("dims"), "cells": cells})

    comparison = compare(results)
    (HERE / "manifest-grid.json").write_text(json.dumps({
        "run": HERE.name, "generated_at": datetime.now().isoformat(timespec="seconds"),
        "channel_policy": channel["policy"], "channel": channel["name"],
        "grid_size": channel["size"], "cell_size": [836, 471], "inset_px": INSET,
        "calls": sum(1 for r in results if r.get("ok")), "results": results,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print("DONE", HERE, comparison, flush=True)
    return 0


def compare(results: list[dict]) -> int:
    """单张 vs 网格裁格：同宽并排，便于看破败、证据、线条。"""
    cell_w, cell_h = 700, 394
    rows = []
    for result in results:
        if result.get("ok"):
            rows.extend(result["cells"])
    canvas = Image.new("RGB", (2 * (cell_w + 12) + 220, len(rows) * (cell_h + 34) + 12), (12, 12, 14))
    draw = ImageDraw.Draw(canvas)
    draw.text((10, 6), "left: single (new2 1672) | right: 2x2 cell (836) — upscaled to same width",
              fill=(230, 230, 230), font=g.font(20))
    for index, cell in enumerate(rows):
        y = 34 + index * (cell_h + 34)
        draw.text((10, y - 2), f"{cell['shot']}  cell {cell['dims'][0]}x{cell['dims'][1]}  lap {cell['metrics']['lap_var']}",
                  fill=(200, 200, 200), font=g.font(18))
        single = HERE / "raw" / f"{cell['shot']}.png"
        if single.exists():
            with Image.open(single) as img:
                canvas.paste(img.convert("RGB").resize((cell_w, cell_h), Image.LANCZOS), (250, y + 22))
        with Image.open(HERE / cell["file"]) as img:
            canvas.paste(img.convert("RGB").resize((cell_w, cell_h), Image.LANCZOS), (250 + cell_w + 12, y + 22))
    canvas.save(OUT / "single-vs-cell.png")
    return len(rows)


if __name__ == "__main__":
    raise SystemExit(main())
