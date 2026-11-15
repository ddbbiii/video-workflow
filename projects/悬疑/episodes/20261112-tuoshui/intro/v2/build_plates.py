# -*- coding: utf-8 -*-
"""Build the post-production UI plates for 《脱水超重》 intro v2.

Outputs (intro/v2/plates):
  phone_screen.png  1080x1920  app screen (all text drawn here, never by the image model)
  phone_mock.png    1200x2080  phone body + screen
  shot1_phone.png   1920x1080  phone in the dark bathroom (warm screen glow = only warm light)
  shot3_pair.png    1920x1080  app reading vs. medical form, two 65.0 aligned
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

EP = Path(r"E:\program\1project\video\projects\悬疑\episodes\20261112-tuoshui")
PLATES = EP / "intro" / "v2" / "plates"
PLATES.mkdir(parents=True, exist_ok=True)
BG_MACHINE = EP / "image" / "final-v2" / "bg_machine2.png"

SANS = r"C:\Windows\Fonts\NotoSansSC-VF.ttf"
SERIF = r"C:\Windows\Fonts\NotoSerifSC-VF.ttf"

INK = (232, 237, 240)
MUTED = (124, 134, 143)
RED = (178, 42, 42)
BG = (9, 12, 14)


def font(path, size, weight=None):
    f = ImageFont.truetype(path, size)
    if weight:
        f.set_variation_by_name(weight)
    return f


def tw(draw, s, f):
    b = draw.textbbox((0, 0), s, font=f)
    return b[2] - b[0], b[3] - b[1], b


def gradient(w, h, top, bottom):
    a = np.zeros((h, w, 3), dtype=np.float32)
    for i, (t, b) in enumerate(zip(top, bottom)):
        a[:, :, i] = np.linspace(t, b, h, dtype=np.float32)[:, None]
    return Image.fromarray(a.astype(np.uint8), "RGB")


def radial_glow(w, h, color, alpha, radius, center):
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt((xx - center[0]) ** 2 + (yy - center[1]) ** 2) / radius
    a = np.clip(1 - d, 0, 1) ** 2 * alpha
    layer = np.zeros((h, w, 4), dtype=np.uint8)
    layer[:, :, 0], layer[:, :, 1], layer[:, :, 2] = color
    layer[:, :, 3] = a.astype(np.uint8)
    return Image.fromarray(layer, "RGBA")


def vignette(img, strength=0.55):
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    mask = np.clip(1 - (d - 0.55) * strength * 2.2, 0.25, 1)
    arr = np.asarray(img, dtype=np.float32) * mask[:, :, None]
    return Image.fromarray(arr.astype(np.uint8), "RGB")


# ---------------------------------------------------------------- phone screen
def build_phone_screen():
    W, H = 1080, 1920
    img = gradient(W, H, (14, 18, 21), (7, 9, 11)).convert("RGB")
    d = ImageDraw.Draw(img)

    # subtle top light
    img.paste(radial_glow(W, H, (255, 255, 255), 18, 900, (540, -260)), (0, 0), radial_glow(W, H, (255, 255, 255), 18, 900, (540, -260)))

    f_time = font(SANS, 40, "DemiLight")
    f_small = font(SANS, 30, "Light")
    f_title = font(SANS, 56, "Medium")
    f_date = font(SANS, 34, "Light")
    f_num = font(SANS, 336, "Light")
    f_unit = font(SANS, 88, "Light")
    f_badge = font(SANS, 46, "Medium")
    f_sub = font(SANS, 34, "Light")
    f_cap = font(SANS, 30, "Light")
    f_card = font(SANS, 40, "Medium")

    d.text((70, 92), "23:47", font=f_time, fill=(214, 221, 226))
    # status icons
    x = 848
    for i, hgt in enumerate((12, 19, 26, 33)):
        d.rounded_rectangle((x + i * 16, 128 - hgt, x + i * 16 + 9, 128), 2, fill=(210, 217, 222))
    # wifi
    for r in (9, 19, 29):
        d.arc((960 - r, 120 - r, 960 + r, 120 + r), 222, 318, fill=(210, 217, 222), width=5)
    d.ellipse((954, 112, 966, 124), fill=(210, 217, 222))
    # battery
    d.rounded_rectangle((1006, 98, 1046, 126), 5, outline=(210, 217, 222), width=3)
    d.rectangle((1048, 105, 1052, 119), fill=(210, 217, 222))
    d.rounded_rectangle((1010, 102, 1034, 122), 3, fill=(210, 217, 222))

    d.text((70, 220), "体重记录", font=f_title, fill=INK)
    d.text((1010, 238), "同步", font=f_small, fill=(138, 148, 156), anchor="ra")
    d.text((70, 312), "11月12日 周二", font=f_date, fill=MUTED)

    # big reading
    num = "65.0"
    d.text((540, 700), num, font=f_num, fill=(243, 246, 248), anchor="ms")
    wnum = d.textbbox((0, 0), num, font=f_num)[2]
    d.text((540 + wnum / 2 + 26, 700), "kg", font=f_unit, fill=(196, 205, 211), anchor="ls")

    # red over-weight badge
    bw, bh = 224, 78
    d.rounded_rectangle((540 - bw / 2, 782, 540 + bw / 2, 782 + bh), 39, fill=(166, 38, 38))
    d.text((540, 782 + bh / 2), "超重", font=f_badge, fill=(255, 244, 240), anchor="mm")

    d.text((540, 918), "较昨日 0.0 kg", font=f_sub, fill=(146, 156, 164), anchor="mm")
    d.text((540, 976), "目标 68.0 kg", font=f_cap, fill=(96, 105, 112), anchor="mm")

    # chart
    top, bot, left, right = 1080, 1330, 80, 1000
    for i in range(4):
        y = top + (bot - top) * i / 3
        d.line((left, y, right, y), fill=(28, 34, 38), width=2)
    pts = [(left, 1218), (260, 1212), (420, 1224), (580, 1208), (740, 1216), (right, 1210)]
    d.line(pts, fill=(122, 136, 146), width=5, joint="curve")
    for p in pts[-2:]:
        d.ellipse((p[0] - 8, p[1] - 8, p[0] + 8, p[1] + 8), fill=(180, 194, 203))
    d.text((80, 1360), "近 7 天", font=f_cap, fill=(96, 105, 112))
    d.text((1000, 1360), "平均 65.0 kg", font=f_cap, fill=(96, 105, 112), anchor="ra")

    # bottom card
    d.rounded_rectangle((70, 1480, 1010, 1720), 34, fill=(18, 23, 27))
    d.text((110, 1520), "最近一次称重", font=f_cap, fill=(120, 130, 138))
    d.text((110, 1564), "今天 23:46", font=f_card, fill=(226, 232, 236))
    d.text((110, 1632), "设备已连接 · HX-02", font=f_cap, fill=(110, 120, 128))
    d.ellipse((950, 1540, 986, 1576), outline=(150, 60, 60), width=3)
    d.ellipse((958, 1548, 978, 1568), fill=(150, 60, 60))

    # home indicator
    d.rounded_rectangle((400, 1866, 680, 1874), 4, fill=(70, 78, 84))
    return img


def build_phone_mock(screen):
    W, H = 1200, 2080
    body = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(body)
    d.rounded_rectangle((4, 4, W - 4, H - 4), 96, fill=(5, 6, 7, 255), outline=(46, 51, 55, 255), width=3)
    d.rounded_rectangle((24, 24, W - 24, H - 24), 78, outline=(16, 18, 20, 255), width=6)
    # side buttons
    d.rounded_rectangle((-4, 470, 6, 620), 5, fill=(30, 33, 36, 255))
    d.rounded_rectangle((-4, 660, 6, 780), 5, fill=(30, 33, 36, 255))
    d.rounded_rectangle((1194, 560, 1204, 760), 5, fill=(30, 33, 36, 255))
    body.paste(screen, (60, 80))
    # dynamic island
    d.rounded_rectangle((390, 108, 810, 168), 30, fill=(0, 0, 0, 255))
    d.ellipse((744, 124, 768, 148), fill=(18, 22, 26, 255))
    # glass highlight
    hl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl)
    hd.line((90, 200, 90, 1880), fill=(255, 255, 255, 26), width=3)
    body.alpha_composite(hl)
    return body


# ---------------------------------------------------------------- medical form
def build_form():
    W, H = 1240, 1754
    paper = np.zeros((H, W, 3), dtype=np.float32)
    base = np.array([220, 225, 226], dtype=np.float32)
    paper[:, :] = base
    rng = np.random.default_rng(7)
    paper += rng.normal(0, 2.2, (H, W, 1))
    yy = np.linspace(0, 1, H)[:, None]
    paper *= (0.97 + 0.03 * (1 - yy))[:, :, None]
    img = Image.fromarray(np.clip(paper, 0, 255).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(img)

    f_head = font(SERIF, 92, "SemiBold")
    f_sub = font(SANS, 30, "Light")
    f_section = font(SANS, 34, "Medium")
    f_label = font(SANS, 32, "Light")
    f_value = font(SANS, 42, "Regular")
    f_big = font(SANS, 62, "Medium")
    f_note = font(SANS, 30, "Light")
    f_stamp = font(SERIF, 34, "SemiBold")
    ink = (29, 36, 39)
    grey = (92, 102, 106)
    line = (150, 160, 164)

    d.text((620, 96), "职工健康体检表", font=f_head, fill=ink, anchor="ma")
    d.text((620, 208), "2026 年度 · 设备科 · 编号 0417", font=f_sub, fill=grey, anchor="ma")
    d.line((70, 262, 1170, 262), fill=line, width=2)

    # photo box
    d.rectangle((950, 292, 1150, 512), outline=line, width=2)
    d.text((1050, 402), "照 片", font=f_sub, fill=(120, 130, 134), anchor="mm")

    def row(y, l1, v1, l2, v2, h=96, big=None):
        d.line((70, y, 1170, y), fill=(176, 184, 188), width=2)
        d.text((96, y + h * 0.55), l1, font=f_label, fill=grey, anchor="lm")
        d.text((246, y + h * 0.55), v1, font=big or f_value, fill=ink, anchor="lm")
        if l2:
            d.text((700, y + h * 0.55), l2, font=f_label, fill=grey, anchor="lm")
            d.text((850, y + h * 0.55), v2, font=big or f_value, fill=ink, anchor="lm")

    d.text((70, 318), "一、基本信息", font=f_section, fill=ink)
    row(390, "姓　名", "李　维", "性　别", "男")
    row(486, "年　龄", "34 岁", "工　号", "0417")
    row(582, "科　室", "设备科", "身　高", "178 cm")
    d.line((70, 678, 1170, 678), fill=(176, 184, 188), width=2)

    d.text((70, 712), "二、体格检查", font=f_section, fill=ink)
    row(780, "血　压", "118/76", "心　率", "72 次/分")
    row(876, "体　重", "65.0 kg", "体　质", "偏瘦", big=f_big)
    # weight highlight
    d.rectangle((228, 888, 640, 962), outline=(168, 44, 44), width=2)
    d.line((70, 972, 1170, 972), fill=(176, 184, 188), width=2)

    d.text((96, 1010), "体检结论", font=f_label, fill=grey)
    d.text((246, 1010), "未见明显异常", font=f_value, fill=ink)
    d.text((96, 1090), "建议", font=f_label, fill=grey)
    d.text((246, 1090), "规律作息，三个月后复查", font=f_note, fill=ink)

    d.line((70, 1580, 500, 1580), fill=line, width=2)
    d.text((70, 1596), "体检医师签名", font=f_note, fill=grey)
    d.line((700, 1580, 1170, 1580), fill=line, width=2)
    d.text((700, 1596), "日期　2026-11-12", font=f_note, fill=grey)

    # red stamp
    stamp = Image.new("RGBA", (260, 260), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stamp)
    sd.ellipse((8, 8, 252, 252), outline=(168, 44, 44, 120), width=7)
    sd.text((130, 104), "体检专用章", font=f_stamp, fill=(168, 44, 44, 130), anchor="mm")
    sd.text((130, 168), "2026.11.12", font=font(SANS, 28, "Regular"), fill=(168, 44, 44, 130), anchor="mm")
    stamp = stamp.rotate(-12, resample=Image.BICUBIC, expand=False)
    img.paste(stamp, (900, 1250), stamp)
    return img


def build_form_panel():
    """960x1080 close-up of the medical form; weight baseline exactly at y=560."""
    W, H = 960, 1080
    paper = np.zeros((H, W, 3), dtype=np.float32)
    paper[:, :] = np.array([220, 225, 226], dtype=np.float32)
    rng = np.random.default_rng(11)
    paper += rng.normal(0, 2.0, (H, W, 1))
    yy = np.linspace(0, 1, H)[:, None]
    paper *= (0.96 + 0.04 * (1 - yy))[:, :, None]
    img = Image.fromarray(np.clip(paper, 0, 255).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(img)

    f_head = font(SERIF, 62, "SemiBold")
    f_sub = font(SANS, 22, "Light")
    f_label = font(SANS, 25, "Light")
    f_value = font(SANS, 34, "Regular")
    f_big = font(SANS, 58, "Medium")
    f_note = font(SANS, 24, "Light")
    ink = (29, 36, 39)
    grey = (92, 102, 106)
    line = (168, 177, 181)

    d.text((480, 44), "职工健康体检表", font=f_head, fill=ink, anchor="ma")
    d.text((480, 116), "2026 年度 · 设备科 · 编号 0417", font=f_sub, fill=grey, anchor="ma")
    d.line((48, 152, 912, 152), fill=line, width=2)

    def row(base, l1, v1, l2, v2, big=None):
        d.line((48, base + 22, 912, base + 22), fill=(190, 198, 202), width=1)
        d.text((60, base), l1, font=f_label, fill=grey, anchor="ls")
        d.text((178, base), v1, font=big or f_value, fill=ink, anchor="ls")
        if l2:
            d.text((520, base), l2, font=f_label, fill=grey, anchor="ls")
            d.text((636, base), v2, font=big or f_value, fill=ink, anchor="ls")

    row(220, "姓　名", "李　维", "性　别", "男")
    row(288, "年　龄", "34 岁", "工　号", "0417")
    row(356, "科　室", "设备科", "身　高", "178 cm")
    row(466, "血　压", "118/76", "心　率", "72 次/分")
    row(560, "体　重", "65.0 kg", "体　质", "偏瘦", big=f_big)
    d.rectangle((168, 486, 470, 574), outline=(168, 44, 44), width=2)
    d.line((48, 620, 912, 620), fill=line, width=2)

    d.text((60, 636), "体检结论", font=f_label, fill=grey)
    d.text((178, 636), "未见明显异常", font=f_value, fill=ink)
    d.text((60, 700), "建　议", font=f_label, fill=grey)
    d.text((178, 700), "规律作息，三个月后复查", font=f_note, fill=ink)

    stamp = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stamp)
    sd.ellipse((6, 6, 194, 194), outline=(168, 44, 44, 110), width=6)
    sd.text((100, 84), "体检专用章", font=font(SERIF, 26, "SemiBold"), fill=(168, 44, 44, 125), anchor="mm")
    sd.text((100, 130), "2026.11.12", font=font(SANS, 20, "Regular"), fill=(168, 44, 44, 125), anchor="mm")
    stamp = stamp.rotate(-12, resample=Image.BICUBIC, expand=False)
    img.paste(stamp, (700, 820), stamp)

    d.line((48, 990, 380, 990), fill=line, width=1)
    d.text((48, 1002), "体检医师签名", font=f_note, fill=grey)
    d.line((560, 990, 912, 990), fill=line, width=1)
    d.text((560, 1002), "日期　2026-11-12", font=f_note, fill=grey)
    return img


def build_pair(phone_screen, form_panel):
    """Full-bleed split: app reading (left) / medical form (right), both 65.0 on one baseline."""
    W, H = 1920, 1080
    # phone: 960x1080 crop, number baseline 700 -> y 560 (crop y0 = 140)
    left = phone_screen.crop((60, 140, 1020, 1220)).resize((960, 1080), Image.LANCZOS)
    right = form_panel

    img = Image.new("RGB", (W, H), (0, 0, 0))
    img.paste(left, (0, 0))
    img.paste(right, (960, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((956, 0, 963, H), fill=(0, 0, 0))

    d.text((28, 24), "手机 App · 读数", font=font(SANS, 26, "Light"), fill=(150, 160, 168))
    d.text((1892, 24), "职工体检表 · 体重栏", font=font(SANS, 26, "Light"), fill=(74, 84, 88), anchor="ra")

    return vignette(img, 0.55)


def build_phone_scene(phone_mock):
    W, H = 1920, 1080
    base = Image.open(BG_MACHINE).convert("RGB").resize((W, H), Image.LANCZOS)
    base = base.filter(ImageFilter.GaussianBlur(26))
    arr = np.asarray(base, dtype=np.float32) * 0.32
    arr[:, :, 2] *= 1.06
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    img.paste(radial_glow(W, H, (255, 158, 84), 70, 620, (960, 560)), (0, 0), radial_glow(W, H, (255, 158, 84), 70, 620, (960, 560)))

    ph = phone_mock.resize((int(1200 * 980 / 2080), 980), Image.LANCZOS)
    ph = ph.rotate(-3.0, resample=Image.BICUBIC, expand=True)
    shadow = Image.new("RGBA", (ph.width + 120, ph.height + 120), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((60, 60, 60 + ph.width, 60 + ph.height), 80, fill=(0, 0, 0, 200))
    shadow = shadow.filter(ImageFilter.GaussianBlur(32))
    cx, cy = W // 2, H // 2
    pos = (cx - ph.width // 2, cy - ph.height // 2)
    img.paste(shadow, (pos[0] - 60, pos[1] - 50), shadow)

    # cool rim light around the body, then the phone
    rim = Image.new("RGBA", ph.size, (0, 0, 0, 0))
    rim.putalpha(ph.split()[3].filter(ImageFilter.GaussianBlur(16)))
    rim_col = Image.new("RGBA", ph.size, (176, 200, 218, 110))
    rim_col.putalpha(rim.split()[3])
    img.paste(rim_col, pos, rim_col)
    img.paste(ph, pos, ph)
    return vignette(img, 0.8)


if __name__ == "__main__":
    screen = build_phone_screen()
    screen.save(PLATES / "phone_screen.png")
    mock = build_phone_mock(ImageEnhance.Brightness(screen).enhance(1.12))
    mock.save(PLATES / "phone_mock.png")
    form = build_form()
    form.save(PLATES / "form.png")
    panel = build_form_panel()
    panel.save(PLATES / "form_panel.png")
    build_phone_scene(mock).save(PLATES / "shot1_phone.png")
    build_pair(screen, panel).save(PLATES / "shot3_pair.png")
    print("plates done", PLATES)


