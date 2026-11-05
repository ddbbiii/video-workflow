# -*- coding: utf-8 -*-
"""Cover composition for siffre-beyond-time (typography as post layers, PIL only).

Hard constraints implemented and verified programmatically:
- Title text on independent layers (no AI-rendered text anywhere).
- Horizontal 1920x1080: every text ink bbox >= 96px from every edge;
  main title chars (超出时间, MaShanZheng) font size >= 320.
- Vertical 1080x1920: side ink bbox margins >= 120px, top >= 150px;
  all text ends above the bottom quarter (y <= 1400 < 1440);
  main title font size >= 260; text block sits mid-upper.
- 书名号 title (《超出时间》) - brackets optically scaled (0.45x) and
  ink-center aligned to main chars, since full-width brackets at main size
  cannot fit the safe width with chars >= 320px.
- Layers exported per candidate: scrim/brand/title/hook PNGs + text_all.
- Outputs: covers/<id>.jpg (composed), covers/<id>.clean.jpg (bg only).
- Writes covers/qa_data.json; QA.md assembled separately.

Usage: python build_cover.py [--only h-a ...]
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat

COVERS = Path(__file__).resolve().parent
BG = COVERS / "bg"
LAYERS = COVERS / "layers"
QA_DATA = COVERS / "qa_data.json"

FONT_TITLE = r"E:\program\1project\video\assets\助眠解说\intro\fonts\MaShanZheng-Regular.ttf"
FONT_HOOK = r"E:\program\1project\video\assets\助眠解说\subtitles\style-r4\fonts\SourceHanSansSC-Heavy.otf"

BRAND = "星夜慢谈"
TITLE_CHARS = "超出时间"
HOOK_H = "他在冰川下住了两个月，只过了一个月"
HOOK_V = ["他在冰川下住了两个月", "只过了一个月"]

C_TITLE = (245, 234, 214)      # warm ivory
C_TITLE_GLOW = (255, 176, 84)  # amber
C_HOOK = (213, 224, 236)       # cool moonlight gray
C_BRAND = (172, 188, 203)
C_ACCENT = (232, 163, 77)

BRACKET_SCALE = 0.45
MIN_MAIN_H, MIN_MAIN_V = 320, 260
SAFE_H, SAFE_V, SAFE_V_TOP, SAFE_V_BOTTOM_LIMIT = 96, 120, 150, 1400
TARGET_H, TARGET_V = (1920, 1080), (1080, 1920)

# bg candidates -> (out id, layout kind)
CANDIDATES = ["h-a", "h-b", "v-a", "v-b"]


def ink_bbox(layer: Image.Image, alpha_thresh=8):
    """Tight bbox of pixels with alpha above threshold."""
    a = layer.getchannel("A")
    bbox = a.point(lambda v: 255 if v > alpha_thresh else 0).getbbox()
    return bbox


def fit_bg(path: Path, size):
    """Center-crop to exact aspect then resize to target."""
    with Image.open(path) as im:
        rgb = im.convert("RGB")
    tw, th = size
    tr = tw / th
    w, h = rgb.size
    r = w / h
    if abs(r - tr) > 0.001:
        if r > tr:  # too wide -> crop sides
            nw = round(h * tr)
            x0 = (w - nw) // 2
            rgb = rgb.crop((x0, 0, x0 + nw, h))
        else:        # too tall -> crop top+bottom (keep slightly lower: light lives low)
            nh = round(w / tr)
            y0 = min((h - nh) // 3 * 2, h - nh) if False else round((h - nh) * 0.6)
            rgb = rgb.crop((0, y0, w, y0 + nh))
    return rgb.resize(size, Image.LANCZOS)


def line_plan(chars_fonts, tracking_em):
    """Return (total_width, draw_ops) where draw_ops = [(char, font, x_left)].
    tracking_em in em of each char's own font."""
    ops, x = [], 0.0
    for i, (ch, f) in enumerate(chars_fonts):
        if i > 0:
            prev_f = chars_fonts[i - 1][1]
            x += prev_f.size * tracking_em
        ops.append((ch, f, x))
        x += f.getlength(ch)
    return x, ops


def build_title_line(main_size, bracket_size, chars):
    fonts_main = ImageFont.truetype(FONT_TITLE, main_size)
    fonts_br = ImageFont.truetype(FONT_TITLE, bracket_size)
    seq = []
    for ch in chars:
        if ch in "《》":
            seq.append((ch, fonts_br))
        else:
            seq.append((ch, fonts_main))
    return seq


def draw_glow(canvas, strip, center_xy, color, radius, alpha):
    """Composite strip at center with a blurred glow underlay."""
    cx, cy = center_xy
    x0 = round(cx - strip.width / 2)
    y0 = round(cy - strip.height / 2)
    # position strip by its INK center, not canvas center of strip
    bb = ink_bbox(strip)
    if bb:
        ink_cx = (bb[0] + bb[2]) / 2
        ink_cy = (bb[1] + bb[3]) / 2
        x0 = round(cx - ink_cx)
        y0 = round(cy - ink_cy)
    glow = Image.new("RGBA", strip.size, (0, 0, 0, 0))
    glow.paste(strip, (0, 0))
    glow = glow.filter(ImageFilter.GaussianBlur(radius))
    tinted = Image.new("RGBA", strip.size, color + (0,))
    tinted.putalpha(glow.getchannel("A").point(lambda v: v * alpha // 255))
    canvas.alpha_composite(tinted, (x0, y0))
    canvas.alpha_composite(strip, (x0, y0))
    return (x0 + bb[0], y0 + bb[1], x0 + bb[2], y0 + bb[3]) if bb else None


def spaced_text(text, font, tracking_em, color):
    """Return strip with letterspaced text (anchor baseline fixed)."""
    n = len(text)
    total = sum(font.getlength(c) for c in text) + (n - 1) * font.size * tracking_em
    W = int(total) + 80
    H = font.size * 2 + 80
    strip = Image.new("RGBA", (max(1, W), max(1, H)), (0, 0, 0, 0))
    d = ImageDraw.Draw(strip)
    x, top = 40, 40 + int(font.size * 0.5)
    for c in text:
        d.text((x, top), c, font=font, fill=color + (255,), anchor="ls")
        x += font.getlength(c) + font.size * tracking_em
    return strip


def brand_strip(size=46, tracking=0.62):
    """Account tag: spaced text flanked by two small amber diamonds."""
    f = ImageFont.truetype(FONT_HOOK, size)
    n = len(BRAND)
    text_w = sum(f.getlength(c) for c in BRAND) + (n - 1) * f.size * tracking
    dot, gap = 7, 30
    W = int(dot + gap + text_w + gap + dot + 24)
    H = int(size * 2.4)
    strip = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(strip)
    top = 40
    x = dot + gap + 12
    for c in BRAND:
        d.text((x, top), c, font=f, fill=C_BRAND + (255,), anchor="ls")
        x += f.getlength(c) + f.size * tracking
    cy = top + size * 0.55
    for dx in (dot // 2 + 2, W - dot // 2 - 2):
        d.polygon([(dx, cy - dot), (dx + dot, cy), (dx, cy + dot), (dx - dot, cy)],
                  fill=C_ACCENT + (230,))
    return strip


def radial_scrim(size, center, radii, max_alpha=110):
    """Soft elliptical dark scrim to guarantee text contrast."""
    w, h = size
    scr = Image.new("L", (w // 4, h // 4), 0)
    d = ImageDraw.Draw(scr)
    cx, cy = center[0] // 4, center[1] // 4
    rx, ry = radii[0] // 4, radii[1] // 4
    steps = 26
    for i in range(steps, 0, -1):
        a = int(max_alpha * (i / steps) ** 2)
        f = i / steps
        d.ellipse((cx - rx * f, cy - ry * f, cx + rx * f, cy + ry * f), fill=a)
    scr = scr.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(24))
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    layer.putalpha(scr)
    return layer


def fit_main_size(kind):
    """Largest main-char size meeting width constraints (brackets at 0.45)."""
    if kind == "h":
        usable = TARGET_H[0] - 2 * SAFE_H - 60  # 60px slack inside safe box
        chars = "《" + TITLE_CHARS + "》"
        m = 400
        while m > MIN_MAIN_H:
            b = round(m * BRACKET_SCALE)
            seq = build_title_line(m, b, chars)
            total, _ = line_plan(seq, 0.05)
            if total <= usable:
                return m, b, total
            m -= 2
        return MIN_MAIN_H, round(MIN_MAIN_H * BRACKET_SCALE), None
    else:
        usable = TARGET_V[0] - 2 * SAFE_V - 30
        m = 340
        while m > MIN_MAIN_V:
            b = round(m * BRACKET_SCALE)
            l1 = build_title_line(m, b, "《超出")
            l2 = build_title_line(m, b, "时间》")
            t1, _ = line_plan(l1, 0.05)
            t2, _ = line_plan(l2, 0.05)
            if max(t1, t2) <= usable:
                return m, b, max(t1, t2)
            m -= 2
        return MIN_MAIN_V, round(MIN_MAIN_V * BRACKET_SCALE), None


def compose(cid):
    kind = "h" if cid.startswith("h") else "v"
    size = TARGET_H if kind == "h" else TARGET_V
    W, H = size
    bg_path = BG / f"{cid}.png"
    if not bg_path.exists():
        print(f"skip {cid}: no bg yet")
        return None
    bg = fit_bg(bg_path, size)
    bg.save(COVERS / f"{cid}.clean.jpg", quality=95, subsampling=0)

    # ---- sizes ----
    m_size, b_size, t_w = fit_main_size(kind)
    hook_size = 64 if kind == "h" else 58
    track_title, track_hook = 0.05, 0.10

    # ---- vertical bg light info (from bg QA) ----
    shift_up = 0
    mf = BG / "manifest.json"
    if kind == "v" and mf.exists():
        try:
            q = json.loads(mf.read_text(encoding="utf-8"))["items"][cid]["qa"]
            if q.get("light_centroid", [0, 1])[1] < 0.68:
                shift_up = 50  # keep hook clear of a higher-than-planned light
        except Exception:
            pass

    # ---- layout ----
    layers_dir = LAYERS / cid
    layers_dir.mkdir(parents=True, exist_ok=True)
    qa = {"id": cid, "canvas": [W, H], "main_size": m_size, "bracket_size": b_size,
          "hook_size": hook_size, "shift_up": shift_up, "items": {}}

    scrim = radial_scrim(size, (W // 2, (430 if kind == "h" else 660 - shift_up)),
                         ((W * 0.62, 430) if kind == "h" else (W * 0.52, 620)),
                         max_alpha=105)
    scrim.save(layers_dir / "scrim.png")

    brand = brand_strip()
    brand.save(layers_dir / "brand.png")

    title_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    if kind == "h":
        seq = build_title_line(m_size, b_size, "《" + TITLE_CHARS + "》")
        strip = render_line_plan(seq, track_title)
        strip = recolor(strip, C_TITLE)
        title_bb = draw_glow(title_layer, strip, (W // 2, 470), C_TITLE_GLOW,
                             radius=max(14, m_size // 14), alpha=88)
    else:
        l1 = recolor(render_line_plan(build_title_line(m_size, b_size, "《超出"), track_title), C_TITLE)
        l2 = recolor(render_line_plan(build_title_line(m_size, b_size, "时间》"), track_title), C_TITLE)
        line_h = m_size * 1.30
        cy1 = 470 - shift_up
        cy2 = cy1 + line_h
        title_bb = draw_glow(title_layer, l1, (W // 2, cy1), C_TITLE_GLOW,
                             radius=max(14, m_size // 14), alpha=88)
        bb2 = draw_glow(title_layer, l2, (W // 2, cy2), C_TITLE_GLOW,
                        radius=max(14, m_size // 14), alpha=88)
        title_bb = (min(title_bb[0], bb2[0]), min(title_bb[1], bb2[1]),
                    max(title_bb[2], bb2[2]), max(title_bb[3], bb2[3]))
    title_layer.save(layers_dir / "title.png")

    hook_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    f_hook = ImageFont.truetype(FONT_HOOK, hook_size)
    if kind == "h":
        strip = spaced_text(HOOK_H, f_hook, track_hook, C_HOOK)
        hook_bb = draw_glow(hook_layer, strip, (W // 2, 745), (255, 255, 255),
                            radius=8, alpha=26)
    else:
        bbs = []
        # first hook line sits below the title INK bottom (title_bb), not below
        # the second line's optical center - prevents overlap seen in v1
        cy = title_bb[3] + 58 + hook_size * 0.55
        for ln in HOOK_V:
            strip = spaced_text(ln, f_hook, track_hook, C_HOOK)
            bbs.append(draw_glow(hook_layer, strip, (W // 2, cy), (255, 255, 255),
                                 radius=7, alpha=24))
            cy += hook_size * 1.6
        hook_bb = (min(b[0] for b in bbs), min(b[1] for b in bbs),
                   max(b[2] for b in bbs), max(b[3] for b in bbs))
    hook_layer.save(layers_dir / "hook.png")

    # ---- brand placement ----
    canvas = bg.convert("RGBA")
    canvas.alpha_composite(scrim)
    brand_y = 150 if kind == "h" else 235 - shift_up
    bb = ink_bbox(brand)
    bx, by = round(W / 2 - (bb[0] + bb[2]) / 2), round(brand_y - (bb[1] + bb[3]) / 2)
    canvas.alpha_composite(brand, (bx, by))
    brand_pos = (bx + bb[0], by + bb[1], bx + bb[2], by + bb[3])
    canvas.alpha_composite(title_layer)
    canvas.alpha_composite(hook_layer)

    text_all = Image.new("RGBA", size, (0, 0, 0, 0))
    text_all.alpha_composite(brand, (bx, by))
    text_all.alpha_composite(title_layer)
    text_all.alpha_composite(hook_layer)
    text_all.save(layers_dir / "text_all.png")

    canvas.convert("RGB").save(COVERS / f"{cid}.jpg", quality=95, subsampling=0)

    # ---- safe zone verification (ink bboxes, strict) ----
    checks = {"brand": brand_pos, "title": title_bb, "hook": hook_bb}
    min_lr = SAFE_H if kind == "h" else SAFE_V
    min_top = SAFE_H if kind == "h" else SAFE_V_TOP
    for name, bbx in checks.items():
        if not bbx:
            qa["items"][name] = {"error": "no ink"}
            continue
        l, t, r, b = bbx
        entry = {"bbox": [round(v) for v in bbx],
                 "margins": {"left": round(l), "top": round(t),
                             "right": round(W - r), "bottom": round(H - b)}}
        ok = (l >= min_lr and (W - r) >= min_lr and t >= min_top
              and (kind == "h" or b <= SAFE_V_BOTTOM_LIMIT))
        entry["safe_ok"] = bool(ok)
        qa["items"][name] = entry

    # contrast: bg luminance under text (after scrim) where text ink is
    a = text_all.getchannel("A").point(lambda v: 255 if v > 60 else 0)
    composed_l = canvas.convert("L")
    mask_sel = Image.new("L", size, 0)
    mask_sel.paste(a, (0, 0))
    stat = ImageStat.Stat(composed_l, mask_sel)
    qa["text_zone_lum_after_scrim"] = round(stat.mean[0], 1)
    qa["bg_mean_lum"] = round(ImageStat.Stat(bg.convert("L")).mean[0], 1)
    return qa


def render_line_plan(seq, tracking_em):
    total, ops = line_plan(seq, tracking_em)
    pad = 120
    fs = max(f.size for _, f, _x in ops)
    max_w = max(x + f.getlength(ch) for ch, f, x in ops)
    strip = Image.new("RGBA", (int(max_w) + 2 * pad, int(fs * 2.6) + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(strip)
    top = pad + fs
    centers = {}
    for ch, f, x in ops:
        d.text((pad + x, top), ch, font=f, fill=(255, 255, 255, 255), anchor="ls")
    # optical vertical alignment of brackets: re-draw shifted
    main_bbs = []
    for ch, f, x in ops:
        if ch not in "《》":
            tmp = Image.new("RGBA", strip.size, (0, 0, 0, 0))
            ImageDraw.Draw(tmp).text((pad + x, top), ch, font=f,
                                     fill=(255, 255, 255, 255), anchor="ls")
            main_bbs.append(ink_bbox(tmp))
    if main_bbs:
        ref_cy = sum((b[1] + b[3]) for b in main_bbs) / (2 * len(main_bbs))
        for ch, f, x in ops:
            if ch in "《》":
                tmp = Image.new("RGBA", strip.size, (0, 0, 0, 0))
                ImageDraw.Draw(tmp).text((pad + x, top), ch, font=f,
                                         fill=(255, 255, 255, 255), anchor="ls")
                bb = ink_bbox(tmp)
                if bb:
                    dy = round(ref_cy - (bb[1] + bb[3]) / 2)
                    # erase original bracket area then redraw shifted
                    d.rectangle((pad + x - 4, top - f.size * 2, pad + x + f.getlength(ch) + 4,
                                 top + f.size), fill=(0, 0, 0, 0))
                    d.text((pad + x, top + dy), ch, font=f,
                           fill=(255, 255, 255, 255), anchor="ls")
    return strip


def recolor(strip, color):
    out = Image.new("RGBA", strip.size, (0, 0, 0, 0))
    a = strip.getchannel("A")
    solid = Image.new("RGBA", strip.size, color + (255,))
    out.paste(solid, (0, 0), a)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="+", default=[])
    args = ap.parse_args()
    results = {}
    if QA_DATA.exists():
        try:
            results.update(json.loads(QA_DATA.read_text(encoding="utf-8")))
        except Exception:
            pass
    for cid in (args.only or CANDIDATES):
        qa = compose(cid)
        if qa:
            results[cid] = qa
            print(cid, "main", qa["main_size"], "hook", qa["hook_size"],
                  {k: v.get("safe_ok") for k, v in qa["items"].items()})
    QA_DATA.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
