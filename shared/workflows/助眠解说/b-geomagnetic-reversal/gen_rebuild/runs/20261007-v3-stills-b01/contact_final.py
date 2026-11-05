"""Final contact sheets from lanczos1080 final-selected versions (read-only on sources)."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
RUN = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\image\stills\20261007-v3-stills-b01')  # 2026-10-08 迁移：脚本移到 shared\workflows，数据仍在单集 image\stills
sel = json.loads((RUN / 'selected.json').read_text(encoding='utf-8'))
def font(sz, bold=False):
    for n in (['arialbd.ttf'] if bold else []) + ['arial.ttf', 'DejaVuSans.ttf']:
        try: return ImageFont.truetype(n, sz)
        except Exception: pass
    return ImageFont.load_default()
F, FB, FH = font(18), font(19, True), font(22, True)
TW, TH, G, LH, HEAD = 470, 264, 8, 30, 64
COL = {'pass': (90, 200, 120), 'note': (235, 190, 70), 'redo': (230, 80, 80)}
pages = [sel[i:i + 16] for i in range(0, len(sel), 16)]
outs = []
for pi, page in enumerate(pages, 1):
    rows = (len(page) + 3) // 4
    H = HEAD + rows * (TH + LH + G) + G
    sheet = Image.new('RGB', (1920, H), (18, 20, 26)); d = ImageDraw.Draw(sheet)
    d.text((G, 10), 'Geomagnetic reversal v3 stills b01 - FINAL selection - sheet %d/%d  (%s .. %s)' % (pi, len(pages), page[0]['shot'], page[-1]['shot']), font=FH, fill=(230, 230, 230))
    d.text((G, 38), 'source: lanczos1080 of final version | PASS green / NOTE yellow | L = needs post controlled layer | B = cleanup blur/mask | E = RealESRGAN candidate | r1 = redo version | grid = 2x2 crop (~1020x572 real px)', font=F, fill=(160, 165, 175))
    for i, s in enumerate(page):
        r, c = divmod(i, 4); x = G + c * (TW + G); y = HEAD + r * (TH + LH + G)
        im = Image.open(RUN / s['lanczos1080']).convert('RGB').resize((TW, TH), Image.LANCZOS)
        sheet.paste(im, (x, y))
        v = s['verdict']; d.rectangle([x, y + TH, x + TW, y + TH + LH], fill=(30, 33, 40))
        d.rectangle([x, y + TH, x + 8, y + TH + LH], fill=COL[v])
        ver = 'r1' if '_r1' in s['final_file'] else ('r2' if '_r2' in s['final_file'] else '')
        src = 'grid' if s['final_file'].startswith('crops/') else 'single'
        d.text((x + 14, y + TH + 5), s['shot'], font=FB, fill=(240, 240, 240))
        d.text((x + 120, y + TH + 5), v.upper(), font=FB, fill=COL[v])
        tags = ' '.join(t for t in [src, ver, 'L' if s['post_layer'] else '', 'B' if s['cleanup'] else '', 'E' if s['realesrgan'] else ''] if t)
        d.text((x + 200, y + TH + 6), tags, font=F, fill=(175, 180, 190))
    p = RUN / ('contact_final_%d.jpg' % pi); sheet.save(p, quality=90); outs.append(str(p))
print('\n'.join(outs))
