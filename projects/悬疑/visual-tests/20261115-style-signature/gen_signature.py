# -*- coding: utf-8 -*-
"""画风签名对照：同一批内容，三套风格块。

V0 baseline  现行 §二 STYLE_POS + CEL_BOOST（对照组）
V1 print     印刷漫画：平涂、三阶、墨线、纸纹，无渐变、无体积光（去掉摄影语言）
V2 print+spot 在 V1 之上，每帧只保留一个饱和色（证据/灯泡/凳子）

内容、构图、机位、锚点、禁止项全部复用 20261114-pilot-8shots 的分镜文案，
只换风格块，保证 A/B 可比。产物：raw/、anchors/、manifest.json、contact-sheet.png、
thumb-260.png（缩略判据）、REPORT.md（人工写）。
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PILOT = REPO / "projects" / "悬疑" / "visual-tests" / "20261114-pilot-8shots"
sys.path.insert(0, str(PILOT))
import gen_pilot as gp  # noqa: E402

RAW = HERE / "raw"
ANCH = HERE / "anchors"
for d in (RAW, ANCH):
    d.mkdir(parents=True, exist_ok=True)
gp.RAW = RAW
gp.ANCH = ANCH
gp.HERE = HERE  # call() 用 HERE 计算相对路径，必须指到本目录

TAGS = ["A1", "B2", "C1", "D1"]

PRINT_POS = (
    "desaturated screen-printed comic panel, flat posterized colour, three flat tones per surface, "
    "no gradients anywhere, bold black ink linework on walls, doors and props, hard-edged shadow shapes, "
    "cold grey-green palette, coarse paper grain, one small warm practical light as a flat warm shape, "
    "ordinary Chinese urban interior, 16:9"
)

# V3：修掉 V1/V2 的三处问题——偏绿、光晕还在、暖光变成第二个彩色
V3_POS = (
    "desaturated screen-printed comic panel, flat posterized colour, exactly three flat tones per surface, "
    "no gradients, bold black ink linework on walls, doors and props, hard-edged shadow shapes, "
    "cold grey-blue palette, no green cast, lamps and windows are pale grey-white flat shapes with no glow, "
    "no halo, no volumetric beam, coarse paper grain, ordinary Chinese urban interior, 16:9"
)

# V4：v3 + 阴影区粗网点（B 方案）
V4_POS = (
    V3_POS + ", coarse halftone dots in the shadow areas only, shadow tone printed as visible round ink dots "
    "about 6 px across at 1672 px width, midtones and highlights clean flat colour, no halftone in highlights"
)

PRINT_NEG = (
    "photographic, photorealistic, volumetric light, dust motes, texture detail, soft gradient, bokeh, "
    "shallow depth of field, 3d render, cgi, glossy, painterly, concept art, film still, cinematic still, "
    "clean new building, spotless, showroom, chibi, big eyes, text, letters, numbers, watermark, UI, gore, monster"
)

# 每帧唯一保留的饱和色
SPOT = {
    "A1": "spot colour: only the yellow plastic stool is fully saturated; every other surface stays grey-green",
    "B2": "spot colour: only the warm bulb is fully saturated amber; every other surface stays grey-green",
    "C1": "spot colour: only the red cord on the key is fully saturated red; the key, mug and table stay grey-green",
    "D1": "spot colour: only the light beyond the far doorway is fully saturated amber; every other surface stays grey-green",
}

# V3 的专色：只有一个红点，光一律不带色
SPOT_V3 = {
    "A1": "spot colour: only the red plastic stool is saturated red; everything else, including the lamps, is grey-blue",
    "B2": "spot colour: only the small red indicator light on the electrical meter box is saturated red; the bulb and the sky are pale grey-white, everything else grey-blue",
    "C1": "spot colour: only the red cord tied to the key is saturated red; the key, the mug and the lamp are grey",
    "D1": "spot colour: only the red bucket at the far end of the corridor is saturated red; the far doorway light is pale grey-white, everything else grey-blue",
}

VARIANTS = ["v0", "v1", "v2", "v3", "v4"]


def content(shot: dict) -> list[str]:
    parts = [shot["comp"], f"subject: {shot['subject']}", f"layers: {shot['layers']}",
             f"decay: {shot['decay']}", f"light: {shot['light']}"]
    if shot["evidence"]:
        parts.append(f"evidence: {shot['evidence']}")
    parts.append(f"hard constraints: {shot['ban']}")
    return parts


def prompt_for(variant: str, shot: dict) -> str:
    if variant == "v0":
        # 与 pilot 完全一致：STYLE_POS + CEL_BOOST + 内容 + Avoid
        base = gp.read_block("STYLE_POS") + ", " + gp.read_block("CEL_BOOST")
        parts = [base]
        if shot["character_ids"] and shot["anchor"]:
            parts.append(gp.CHAR_PREAMBLE)
        parts += content(shot)
        parts.append("Avoid: " + gp.read_block("STYLE_NEG"))
        return ", ".join(parts)
    parts = [{"v3": V3_POS, "v4": V4_POS}.get(variant, PRINT_POS)]
    if shot["character_ids"] and shot["anchor"]:
        parts.append(gp.CHAR_PREAMBLE)
    parts += content(shot)
    if variant == "v2":
        parts.append(SPOT[shot["source_tag"]])
    elif variant in ("v3", "v4"):
        parts.append(SPOT_V3[shot["source_tag"]])
    parts.append("Avoid: " + PRINT_NEG)
    return ", ".join(parts)


def pinned_channel(name: str) -> dict:
    """风格对照必须单一通道：v7 的 parallel 会混 new2 / dkl-b，尺寸与渲染不同，无法比。"""
    policy = json.loads(gp.POLICY.read_text(encoding="utf-8"))
    channel = dict(policy["channels"][name])
    channel["name"] = name
    channel["policy"] = f"{policy['active']}#pin:{name}"
    return channel


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="只跑指定变体：v0,v1,v2,v3,v4")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--rebuild", action="store_true", help="不调 API，按已有 png 重建 manifest")
    ap.add_argument("--channel", default="new2", help="固定通道（默认 new2，与前 16 张可比）")
    args = ap.parse_args()
    only = {x.strip() for x in args.only.split(",") if x.strip()}

    channel = pinned_channel(args.channel)
    print(f"channel={channel['name']} size={channel['size']} price={channel['price_cny']}", flush=True)
    shots = {s["tag"]: s for s in gp.SHOTS}
    todo = []
    for v in VARIANTS:
        if only and v not in only:
            continue
        for tag in TAGS:
            s = dict(shots[tag])
            s["tag"] = f"{tag}-{v}"
            s["source_tag"] = tag
            todo.append((v, s))

    def run(item):
        variant, shot = item
        anchor = gp.build_anchor(shot["anchor"]) if shot["anchor"] else None
        prompt = prompt_for(variant, shot)
        info = gp.call(channel, prompt, shot, anchor, 1)
        if not info.get("ok"):
            return {"variant": variant, "source_tag": shot["source_tag"], "ok": False,
                    "error": info.get("error"), "prompt": prompt}
        info["metrics"] = gp.measure(RAW / Path(info["file"]).name)
        info["qa"] = gp.gate(info, channel)
        return {"variant": variant, "source_tag": shot["source_tag"], "ok": True,
                "file": info["file"], "dims": info["dims"], "metrics": info["metrics"],
                "qa": info["qa"], "elapsed_s": info.get("elapsed_s"), "prompt": prompt}

    results = []
    if args.rebuild:
        for variant, shot in todo:
            path = RAW / f"{shot['tag']}.png"
            if not path.exists():
                continue
            with Image.open(path) as im:
                dims = list(im.size)
            probe = {"dims": dims, "metrics": gp.measure(path)}
            results.append({"variant": variant, "source_tag": shot["source_tag"], "ok": True,
                            "file": f"raw/{shot['tag']}.png", "rebuilt": True,
                            "dims": dims, "metrics": probe["metrics"],
                            "qa": gp.gate(probe, channel), "elapsed_s": None,
                            "prompt": prompt_for(variant, shot)})
        print(f"rebuilt {len(results)} records", flush=True)
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for r in pool.map(run, todo):
                results.append(r)
                print(f"  {r['source_tag']}-{r['variant']}: {'OK' if r['ok'] else 'FAIL'} "
                      f"{r.get('elapsed_s', '-')}s {r.get('dims', '')}", flush=True)

    manifest_path = HERE / "manifest.json"
    old = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    merged = {(r["source_tag"], r["variant"]): r for r in old.get("results", [])}
    for r in results:
        merged[(r["source_tag"], r["variant"])] = r
    order = {(t, v): i for i, (t, v) in enumerate((t, v) for t in TAGS for v in VARIANTS)}
    rows = sorted(merged.values(), key=lambda r: order.get((r["source_tag"], r["variant"]), 99))

    manifest = {
        "run": HERE.name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "channel": channel["name"], "policy": channel["policy"], "size": channel["size"],
        "print_pos": PRINT_POS, "v3_pos": V3_POS, "print_neg": PRINT_NEG,
        "spot": SPOT, "spot_v3": SPOT_V3,
        "results": rows,
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    # 联系表：行=镜，列=变体
    cell_w, cell_h, pad = 720, 405, 14
    cols = len(VARIANTS)
    canvas = Image.new("RGB", (cols * (cell_w + pad) + pad, 4 * (cell_h + 46) + pad), (12, 12, 14))
    draw = ImageDraw.Draw(canvas)
    font = gp.font(26)
    for row, tag in enumerate(TAGS):
        for col, v in enumerate(VARIANTS):
            path = RAW / f"{tag}-{v}.png"
            x = pad + col * (cell_w + pad)
            y = pad + row * (cell_h + 46)
            if path.exists():
                with Image.open(path) as im:
                    canvas.paste(im.convert("RGB").resize((cell_w, cell_h), Image.LANCZOS), (x, y + 34))
            draw.text((x + 6, y + 4), f"{tag} · {v}", fill=(235, 235, 235), font=font)
    canvas.save(HERE / "contact-sheet.png")

    # 缩略判据：每格 300px 宽
    tw = 300
    th = round(300 * 941 / 1672)
    sheet = Image.new("RGB", (cols * (tw + 10) + 10, 4 * (th + 34) + 10), (18, 18, 20))
    d2 = ImageDraw.Draw(sheet)
    f2 = gp.font(18)
    for row, tag in enumerate(TAGS):
        for col, v in enumerate(VARIANTS):
            path = RAW / f"{tag}-{v}.png"
            x = 10 + col * (tw + 10)
            y = 10 + row * (th + 34)
            if path.exists():
                with Image.open(path) as im:
                    sheet.paste(im.convert("RGB").resize((tw, th), Image.LANCZOS), (x, y + 22))
            d2.text((x, y + 2), f"{tag} {v}", fill=(230, 230, 230), font=f2)
    sheet.save(HERE / "thumb-260.png")
    print("DONE", HERE, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
