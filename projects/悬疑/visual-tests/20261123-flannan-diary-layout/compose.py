"""从共享灯室底图重建三版静帧及对照图。"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
FRAME = (1920, 1080)
FONTS = Path("/System/Library/Fonts")
SONG = FONTS / "Supplemental/Songti.ttc"
SANS = FONTS / "Hiragino Sans GB.ttc"
MONO = FONTS / "Menlo.ttc"
DATE = "1900年12月14日"
BODY = ("灯室上方又有脚步声。", "可这上面已经没有楼层了。")
TIME = "01:13:26"
LAYOUTS = (
    dict(file="A-small.png", label="左下小页", effect="淡时间码", width=550, x=94, y=702,
         angle=1.7, time_size=33, time_y=75, time_opacity=185, grade=.07, scan=0),
    dict(file="B-medium.png", label="左侧中页", effect="细扫描线", width=705, x=102, y=399,
         angle=.7, time_size=42, time_y=971, time_opacity=226, grade=.23, scan=.036),
    dict(file="C-large.png", label="下方大页", effect="取景角标与亮时间码", width=834, x=425, y=560,
         angle=-1.4, time_size=53, time_y=84, time_opacity=249, grade=.40, scan=.063),
)


def paper_layer() -> Image.Image:
    width, height = 1000, 498
    rng = np.random.default_rng(1900)
    edge = [(13, 11), (143, 15), (268, 11), (472, 16), (704, 10), (891, 14),
            (980, 8), (984, 61), (978, 174), (983, 291), (981, 419), (991, 479),
            (970, 484), (829, 480), (612, 487), (418, 480), (209, 488), (17, 484),
            (16, 438), (21, 416), (10, 398), (13, 347), (16, 282), (11, 239),
            (17, 186), (10, 141), (14, 95), (7, 57)]
    alpha = Image.new("L", (width, height))
    ImageDraw.Draw(alpha).polygon(edge, fill=255)
    distance = np.asarray(alpha.filter(ImageFilter.GaussianBlur(13)), dtype=np.float32) / 255
    clouds = Image.fromarray(rng.integers(32, 218, (15, 30), dtype=np.uint8))
    clouds = np.asarray(clouds.resize((width, height), Image.Resampling.BICUBIC), dtype=np.float32)
    variation = (clouds - 128) * .093 + rng.normal(0, 1.5, (height, width))
    variation -= 24 * (1 - distance) ** 1.5
    colors = np.array([218, 205, 175]) + variation[..., None]
    canvas = Image.fromarray(np.clip(colors, 0, 255).astype(np.uint8)).convert("RGBA")
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.line(edge + [edge[0]], fill=(115, 97, 72), width=2)
    for y in (113, 185, 257, 329, 401):
        draw.line((30, y, 961, y), fill=(177, 166, 144), width=2)
    for x in (99, 106):
        draw.line((x, 24, x, 476), fill=(182, 148, 130), width=1)
    for y in (154, 289, 420):
        draw.ellipse((24, y, 33, y + 10), fill=(156, 136, 104))
    draw.text((137, 113), DATE, font=ImageFont.truetype(SONG, 43, index=6),
              fill=(66, 56, 44), anchor="ls")
    for line, y in zip(BODY, (254, 326)):
        draw.text((135, y), line, font=ImageFont.truetype(SONG, 64, index=6),
                  fill=(46, 43, 39), anchor="ls")
    canvas.putalpha(alpha.filter(ImageFilter.GaussianBlur(.65)))
    return canvas


def composite(base: Image.Image, paper: Image.Image, layout: dict) -> Image.Image:
    grey = np.asarray(base.convert("L"), dtype=np.float32)
    cold = grey[..., None] * np.array([.94, 1.015, 1.06]) + np.array([1, 4, 6])
    rgb = np.asarray(base, dtype=np.float32)
    # Protect the one amber practical light while cooling the surrounding room.
    cool_strength = layout["grade"] * (1 - .70 * np.clip((rgb[..., 0] - rgb[..., 2]) / 65, 0, 1))
    filtered = rgb + (cold - rgb) * cool_strength[..., None]
    frame = Image.fromarray(np.clip(filtered, 0, 255).astype(np.uint8)).convert("RGBA")

    width = layout["width"]
    page = paper.resize((width, round(width * paper.height / paper.width)),
                        Image.Resampling.LANCZOS)
    page = page.rotate(layout["angle"], expand=True, resample=Image.Resampling.BICUBIC)
    x, y = layout["x"], layout["y"]
    shadow = Image.new("L", FRAME)
    shadow.paste(page.getchannel("A").point(lambda a: a * .59), (x + 5, y + 13))
    umbra = Image.new("RGBA", FRAME, (10, 16, 22))
    umbra.putalpha(shadow.filter(ImageFilter.GaussianBlur(17)))
    frame.alpha_composite(umbra)
    frame.alpha_composite(page, (x, y))

    # The scan pattern is fixed to the full output, above both image layers.
    if layout["scan"]:
        pattern = np.ones((FRAME[1], 1, 1), dtype=np.float32)
        pattern[::5] -= layout["scan"]
        frame = Image.fromarray((np.asarray(frame.convert("RGB")) * pattern).astype(np.uint8)).convert("RGBA")

    overlay = Image.new("RGBA", FRAME)
    draw = ImageDraw.Draw(overlay)
    right = 1836 if layout["scan"] < .05 else 1823
    if layout["scan"] >= .05:
        for bx, by, dx, dy in ((59, 59, 1, 1), (1860, 59, -1, 1),
                               (59, 1020, 1, -1), (1860, 1020, -1, -1)):
            draw.line(((bx, by + dy * 26), (bx, by), (bx + dx * 26, by)),
                      fill=(210, 226, 232, 155), width=2)
    font = ImageFont.truetype(MONO, layout["time_size"], index=int(layout["scan"] >= .05))
    left, top, edge, bottom = draw.textbbox((right, layout["time_y"]), TIME, font=font, anchor="ra")
    if layout["scan"] >= .05:
        draw.rectangle((left - 13, top - 8, edge + 13, bottom + 8), fill=(18, 28, 36, 122))
    draw.text((right + 1, layout["time_y"] + 2), TIME, font=font, anchor="ra", fill=(14, 20, 24, 213))
    draw.text((right, layout["time_y"]), TIME, font=font, anchor="ra",
              fill=(219, 232, 234, layout["time_opacity"]))
    return Image.alpha_composite(frame, overlay).convert("RGB")


def comparison(frames: list[Image.Image]) -> None:
    width, margin, preview_h, strip = 1040, 32, 549, 62
    inside = width - 2 * margin
    sheet = Image.new("RGB", (width, 108 + 3 * (preview_h + strip + 22)), (16, 22, 28))
    draw = ImageDraw.Draw(sheet)
    title = ImageFont.truetype(SANS, 33, index=2)
    label = ImageFont.truetype(SANS, 25, index=2)
    detail = ImageFont.truetype(SANS, 22)
    tag = ImageFont.truetype(MONO, 20, index=1)
    draw.text((margin, 25), "第四位守塔人", font=title, fill=(230, 233, 233))
    draw.text((margin, 70), "灯室 · 日记页与监控时间码", font=detail, fill=(167, 183, 192))
    for i, (frame, layout) in enumerate(zip(frames, LAYOUTS)):
        y = 108 + i * (preview_h + strip + 22)
        sheet.paste(frame.resize((inside, preview_h), Image.Resampling.LANCZOS), (margin, y + strip))
        draw.rectangle((margin, y + 18, margin + 33, y + 49), fill=(210, 190, 151))
        draw.text((margin + 16, y + 34), "ABC"[i], font=tag, fill=(25, 31, 35), anchor="mm")
        draw.text((margin + 48, y + 17), layout["label"], font=label, fill=(233, 236, 236))
        draw.text((width - margin, y + 32), layout["effect"], font=detail,
                  fill=(168, 184, 193), anchor="rm")
    sheet.save(HERE / "comparison.jpg", quality=93, subsampling=0, optimize=True)


def main() -> None:
    with Image.open(HERE / "lamp-room.png") as source:
        base = ImageOps.fit(source.convert("RGB"), FRAME, method=Image.Resampling.LANCZOS)
    paper = paper_layer()
    paper.save(HERE / "diary-page.png")
    frames = [composite(base, paper, layout) for layout in LAYOUTS]
    for frame, layout in zip(frames, LAYOUTS):
        frame.save(HERE / layout["file"])
    comparison(frames)


if __name__ == "__main__":
    main()
