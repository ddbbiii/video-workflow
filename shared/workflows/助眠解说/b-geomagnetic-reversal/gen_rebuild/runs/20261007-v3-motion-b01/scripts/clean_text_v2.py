"""(args: regions_json out_dirname) Light blur of pseudo-text regions -> new files in inputs_clean/ (sources untouched)."""
import json, hashlib, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
RUN = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\video\clips')  # 2026-10-08 迁移：原批次 20261007-v3-motion-b01 根目录，现为单集 video\clips
STILLS = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\image\stills\20261007-v3-stills-b01')
sel = {s['shot']: s for s in json.loads((STILLS / 'selected.json').read_text(encoding='utf-8'))}
regions = json.loads((Path(__file__).parent / (sys.argv[1] if len(sys.argv)>1 else 'clean_regions.json')).read_text(encoding='utf-8'))
out = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\image\stills') / (sys.argv[2] if len(sys.argv)>2 else 'inputs_clean'); out.mkdir(exist_ok=True)
log = []
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
for shot, regs in regions.items():
    if shot.startswith('_'): continue
    src = STILLS / sel[shot]['final_file']
    im = Image.open(src).convert('RGB'); W, H = im.size
    res = im.copy()
    for r in regs:
        m = Image.new('L', (W, H), 0); d = ImageDraw.Draw(m)
        if 'ring' in r:
            cx, cy, rx, ry, inner = r['ring']
            d.ellipse([(cx-rx)*W, (cy-ry)*H, (cx+rx)*W, (cy+ry)*H], fill=255)
            d.ellipse([(cx-rx*inner)*W, (cy-ry*inner)*H, (cx+rx*inner)*W, (cy+ry*inner)*H], fill=0)
        elif 'rect' in r:
            x0, y0, x1, y1 = r['rect']; d.rectangle([x0*W, y0*H, x1*W, y1*H], fill=255)
        else:
            d.polygon([(x*W, y*H) for x, y in r['poly']], fill=255)
        sig = max(1.0, r['sigma'] * W)
        m = m.filter(ImageFilter.GaussianBlur(sig * 1.5))
        blurred = res.filter(ImageFilter.GaussianBlur(sig))
        res = Image.composite(blurred, res, m)
    dst = out / (shot + '_clean.png'); res.save(dst)
    log.append(dict(shot=shot, source=str(src), source_sha256=sha(src), size=[W, H], output=str(dst), output_sha256=sha(dst), regions=regs,
                    note='仅轻模糊伪文字区域；未加任何标注/箭头/文字/地图图层；原图未改动'))
    print(shot, W, H, dst.name)
(out / 'clean_manifest.json').write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding='utf-8')
