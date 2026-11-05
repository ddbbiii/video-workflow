"""Crop grid raws into cells by actual pixel size; Lanczos to 1920x1080 (interpolation, not AI SR)."""
import argparse, json, hashlib
from pathlib import Path
from PIL import Image
import numpy as np
RUN = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\image\stills\20261007-v3-stills-b01')  # 2026-10-08 迁移：脚本移到 shared\workflows，数据仍在单集 image\stills
POS = ['左上', '右上', '左下', '右下']

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def detect_band(prof_mean, prof_std, c, span=20):
    lo, hi = c - span, c + span
    base = np.median(np.r_[prof_mean[lo-30:lo], prof_mean[hi:hi+30]])
    band = [i for i in range(lo, hi) if abs(prof_mean[i] - base) > 40 or prof_std[i] < 10]
    return (min(band), max(band)) if band else None

def to1080(im):
    w, h = im.size
    if abs(w / h - 16 / 9) > 1e-3:
        if w / h > 16 / 9:
            nw = round(h * 16 / 9); x = (w - nw) // 2; box = (x, 0, x + nw, h)
        else:
            nh = round(w * 9 / 16); y = (h - nh) // 2; box = (0, y, w, y + nh)
        im = im.crop(box)
    else:
        box = (0, 0, w, h)
    return im.resize((1920, 1080), Image.LANCZOS), list(box)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--names', nargs='+', required=True)  # raw base names e.g. g01 ch1-c04 g01_r1
    ap.add_argument('--inset', type=int, default=6)
    a = ap.parse_args()
    m = json.loads((RUN / 'grid-manifest.json').read_text(encoding='utf-8'))
    jobs = {j['job_id']: j for j in m['jobs']}
    for d in ('crops', 'lanczos1080', 'post'): (RUN / d).mkdir(exist_ok=True)
    for name in a.names:
        raw = RUN / 'raw' / (name + '.png')
        res = json.loads((RUN / 'results' / (name + '.json')).read_text(encoding='utf-8'))
        job = jobs[res['job_id']]
        im = Image.open(raw).convert('RGB'); W, H = im.size
        post = {'name': name, 'raw': str(raw), 'raw_size': [W, H], 'outputs': []}
        if job['kind'] == 'grid2x2':
            mx, my = W // 2, H // 2
            L = np.asarray(im.convert('L')).astype(float)
            bx = detect_band(L.mean(0), L.std(0), mx); by = detect_band(L.mean(1), L.std(1), my)
            x0, x1 = (bx[0] - 3, bx[1] + 4) if bx else (mx - a.inset, mx + a.inset)
            y0, y1 = (by[0] - 3, by[1] + 4) if by else (my - a.inset, my + a.inset)
            post['divider_band_x'] = list(bx) if bx else None; post['divider_band_y'] = list(by) if by else None
            boxes = [(0, 0, x0, y0), (x1, 0, W, y0), (0, y1, x0, H), (x1, y1, W, H)]
            suffix = name[len(job['job_id']):]
            for cell, box, pos in zip(job['cells'], boxes, POS):
                c = im.crop(box); cp = RUN / 'crops' / (cell['shot'] + suffix + '.png'); c.save(cp)
                l, cb = to1080(c); lp = RUN / 'lanczos1080' / (cell['shot'] + suffix + '.png'); l.save(lp)
                post['outputs'].append({'shot': cell['shot'], 'position': pos, 'crop_box': list(box), 'crop': str(cp), 'crop_size': list(c.size), 'crop_sha256': sha(cp),
                    'lanczos1080': str(lp), 'lanczos_note': 'Lanczos interpolation upscale %dx%d->1920x1080 after center-crop %s to 16:9; not AI super-resolution' % (c.size[0], c.size[1], cb), 'lanczos_sha256': sha(lp)})
        else:
            l, cb = to1080(im); lp = RUN / 'lanczos1080' / (name + '.png'); l.save(lp)
            post['outputs'].append({'shot': job['shot'], 'position': 'single', 'crop': None, 'raw_size': [W, H], 'lanczos1080': str(lp),
                'lanczos_note': 'Lanczos resample %dx%d->1920x1080 (downscale; single full-frame image)' % (W, H), 'lanczos_sha256': sha(lp)})
        (RUN / 'post' / (name + '.json')).write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(post, ensure_ascii=False))

if __name__ == '__main__':
    main()
