"""Intro r1 for geomag full film (CPU). Structure = intro-node.md (2026-10-08) / op4_vo_A reference implementation.
Copy text = intro/script-revision-20261008/INTRO_COPY.md. Narration: b2 seed7 takes, trim(-45dB,20ms,+0.10/+0.15) -> atempo 0.88 -> head 0.40 / gap 0.45 / tail 0.80."""
import json, subprocess, math
from pathlib import Path
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter
P = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal')  # 2026-10-08 迁移：原 legacy-source\zhumian\b-geomagnetic-reversal，现为单集目录
I = P/'video'/'intro'/'full_r1_src'; T = Path(r'E:\program\1project\video\shared\work\scratch\zhumian-geomag-full_r1-tmp'); T.mkdir(parents=True, exist_ok=True); FD = Path(r'E:\program\1project\video\assets\助眠解说\intro\fonts')
ST = P/'image'/'stills'/'20261007-v3-stills-b01'; RAW = ST/'raw'; CROP = ST/'crops'
TK = P/'audio'/'vo-raw'/'full_r1'/'takes-seed7-final'
W, H, FPS, SR = 1920, 1080, 30, 48000
LINES = ['岩石冷却时，会留下地球磁场的方向', '这些古老的记录里，藏着南北翻转的往事', '接下来的二十三分钟，我们来讲讲地球磁场']
def run(*a, **k): subprocess.run([str(x) for x in a], check=True, **k)
segs = []
for i in ('i01', 'i02', 'i03'):
    x, sr = sf.read(str(TK/f'{i}.wav')); x = x.mean(1) if x.ndim > 1 else x; fr = int(0.02*sr)
    db = 20*np.log10(np.array([np.sqrt(np.mean(x[k:k+fr]**2)+1e-12) for k in range(0, len(x)-fr, fr)]))
    idx = np.where(db > -45)[0]; a = max(0, idx[0]*fr - int(0.10*sr)); b = min(len(x), (idx[-1]+1)*fr + int(0.15*sr))
    tr = T/f'intro_{i}_trim.wav'; sf.write(str(tr), x[a:b], sr)
    pc = T/f'intro_{i}_paced.wav'
    if not pc.exists(): run('ffmpeg', '-v', 'error', '-n', '-i', tr, '-af', 'atempo=0.88', '-ar', SR, '-ac', 1, pc)
    y, _ = sf.read(str(pc)); segs.append(y)
HEAD, GAP, TAIL = 0.4, 0.45, 0.8
t = HEAD; times = []
for y in segs: times.append((t, t+len(y)/SR)); t += len(y)/SR + GAP
TI = times[-1][1] + TAIL; NI = round(TI*FPS); TI = NI/FPS
nar = np.zeros(int(round(TI*SR)))
for (s, e), y in zip(times, segs): i0 = int(round(s*SR)); nar[i0:i0+len(y)] += y
NAR = I/'intro_narration_raw.wav'
if not NAR.exists(): sf.write(str(NAR), nar.astype(np.float32), SR, subtype='FLOAT')
print('times', [(round(s, 3), round(e, 3)) for s, e in times], 'intro', TI, NI)
def cover(im, w, h):
    s = max(w/im.width, h/im.height); im = im.resize((round(im.width*s), round(im.height*s)), Image.LANCZOS)
    x, y = (im.width-w)//2, (im.height-h)//2; return im.crop((x, y, x+w, y+h))
def src(n): return RAW/n if (RAW/n).exists() else CROP/n
def load(n, w=W, h=H): return cover(Image.open(src(n)).convert('RGB'), w, h)
def ease_io(u): u = min(1, max(0, u)); return u*u*(3-2*u)
def ease_out_back(u, s=0.8): u = min(1, max(0, u)) - 1; return 1 + (s+1)*u**3 + s*u**2
def push(im, u, z1, zin=True):
    z = 1 + z1*(ease_io(u) if zin else 1-ease_io(u)); cw, ch = round(W/z), round(H/z); x, y = (W-cw)//2, (H-ch)//2
    return im.crop((x, y, x+cw, y+ch)).resize((W, H), Image.BILINEAR)
PAN = ['ch2-c02.png', 'ch2-c09.png', 'ch2-c01.png', 'ch5-c02.png']      # TL expands: magnetite in cooled basalt / lava
THEN = 'ch2-c09.png'                                                    # mid-ocean ridge lava cooling
L2 = ['ch3-c07_r1.png', 'ch2-c04.png', 'ch5-c05_r1.png']                # ancient strata+core / reversed basalt record / weak multi-lobe field
L3 = 'ch4-c04_r1.png'
full = {n: load(n) for n in set([PAN[0], THEN, L3] + L2)}
LAY = [((560, 330), (860, 484), -1), ((1360, 330), (860, 484), 1), ((560, 760), (860, 484), -1), ((1360, 760), (860, 484), 1)]
pans = [load(n, *LAY[i][1]) for i, n in enumerate(PAN)]
s1, e1 = times[0]; s2, e2 = times[1]; s3, e3 = times[2]
B1 = round((s2 - 0.25)*FPS)/FPS; B2 = round((s3 - 0.25)*FPS)/FPS
CE, EXP = 1.6, 0.5
DIS1 = CE + EXP + max(0.8, (B1 - CE - EXP)*0.45)
ART = '地球磁场'; fp = str(FD/'MaShanZheng-Regular.ttf')
f300 = ImageFont.truetype(fp, 300); bb = ImageDraw.Draw(Image.new('RGB', (10, 10))).textbbox((0, 0), ART, font=f300)
size = round(300 * (W*0.65) / (bb[2]-bb[0])); fnt_art = ImageFont.truetype(fp, size)
def art_layer(alpha, scale):
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); bb = d.textbbox((0, 0), ART, font=fnt_art, stroke_width=8)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]; x = (W-tw)/2 - bb[0]; y = H*0.43 - th/2 - bb[1]
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).text((x+6, y+8), ART, font=fnt_art, fill=(0, 0, 0, 170), stroke_width=8, stroke_fill=(0, 0, 0, 170))
    sh = sh.filter(ImageFilter.GaussianBlur(10)); lay.alpha_composite(sh)
    d.text((x, y), ART, font=fnt_art, fill=(250, 238, 205, 255), stroke_width=8, stroke_fill=(20, 16, 10, 255))
    if scale != 1:
        sw, shh = round(W*scale), round(H*scale); lay = lay.resize((sw, shh), Image.BICUBIC)
        nl = Image.new('RGBA', (W, H), (0, 0, 0, 0)); nl.paste(lay, ((W-sw)//2, (H-shh)//2)); lay = nl
    a = np.asarray(lay).copy(); a[..., 3] = (a[..., 3]*alpha).astype(np.uint8); return Image.fromarray(a), (tw, th, y + bb[1])
ART_IN = max(s3 + 1.6, TI - 2.4); artinfo = None
def frame(f):
    global artinfo
    tt = f/FPS
    if tt < B1:
        if tt < CE + EXP:
            can = Image.new('RGB', (W, H), (0, 0, 0))
            for i, (pim, ((x0, y0), (pw, ph), dr)) in enumerate(zip(pans, LAY)):
                st = i*3
                if f < st or (i == 0 and tt >= CE): continue
                sc = 0.2 + 0.8*ease_out_back((f-st)/12); sl = dr*1.2*max(0, f-12)
                cx = W/2 + (x0 + sl - W/2)*sc; cy = H/2 + (y0 - H/2)*sc; w, h = max(8, round(pw*sc)), max(8, round(ph*sc))
                p = pim.resize((w, h), Image.BILINEAR); bw = 4; fr_ = Image.new('RGB', (w+2*bw, h+2*bw), (236, 236, 236)); fr_.paste(p, (bw, bw))
                al = min(1, (f-st)/8)
                if i != 0 and tt >= CE: al *= max(0, 1-(tt-CE)/EXP)
                can.paste(fr_, (round(cx-fr_.width/2), round(cy-fr_.height/2)), Image.new('L', fr_.size, round(255*al)))
            if tt >= CE:
                (x0, y0), (pw, ph), dr = LAY[0]; sl = dr*1.2*max(0, f-12); u = ease_io((tt-CE)/EXP)
                cx = x0+sl; cy = y0; cx += (W/2-cx)*u; cy += (H/2-cy)*u; w = round(pw+(W-pw)*u); h = round(ph+(H-ph)*u)
                bw = round(4*(1-u)); p = cover(full[PAN[0]], w, h); fr_ = Image.new('RGB', (w+2*bw, h+2*bw), (236, 236, 236)); fr_.paste(p, (bw, bw))
                can.paste(fr_, (round(cx-fr_.width/2), round(cy-fr_.height/2)))
            return can
        a = push(full[PAN[0]], (tt-CE-EXP)/(B1-CE-EXP), 0.025)
        if tt >= DIS1:
            b = push(full[THEN], (tt-DIS1)/(B1-DIS1), 0.03, zin=False)
            return Image.blend(a, b, min(1, (tt-DIS1)/0.3))
        return a
    if tt < B2:
        L = (B2-B1)/3; k = min(2, int((tt-B1)//L)); u = (tt-B1-k*L)/L
        im = push(full[L2[k]], u, 0.03, zin=(k % 2 == 0))
        if tt-B1-k*L < 0.2:
            prev = push(full[THEN], 1, 0.03, zin=False) if k == 0 else push(full[L2[k-1]], 1, 0.03, zin=((k-1) % 2 == 0))
            im = Image.blend(prev, im, (tt-B1-k*L)/0.2)
        return im
    im = push(full[L3], (tt-B2)/(TI-B2), 0.04)
    if tt < B2 + 0.2: im = Image.blend(push(full[L2[2]], 1, 0.03), im, (tt-B2)/0.2)
    if tt >= ART_IN:
        u = min(1, (tt-ART_IN)/0.6); lay, artinfo = art_layer(ease_io(u), 0.97 + 0.03*ease_io(u))
        im = im.convert('RGBA'); im.alpha_composite(lay); im = im.convert('RGB')
    return im
VID = I/'intro_video_r1.mkv'
if not VID.exists():
    pr = subprocess.Popen(['ffmpeg', '-v', 'error', '-n', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-c:v', 'ffv1', '-pix_fmt', 'yuv420p', str(VID)], stdin=subprocess.PIPE)
    for f in range(NI): pr.stdin.write(frame(f).tobytes())
    pr.stdin.close(); assert pr.wait() == 0
else: frame(NI-1)
man = dict(copy_source=str(P/'story'/'script-revision-20261008'/'INTRO_COPY.md'), lines=LINES, intro_s=TI, intro_frames=NI, sentence_times=times,
    narration_raw=str(NAR), voice='b2-warm-male VoxCPM2 ultimate seed7 cfg2 10steps; trim -45dB/20ms +0.10/+0.15s -> atempo 0.88 -> head 0.40/gap 0.45/tail 0.80',
    scenes=dict(line1=dict(collage=PAN, expand=PAN[0], then=THEN, collage_end=CE, expand_s=EXP, dissolve_at=DIS1, B1=B1), line2=dict(shots=L2, B2=B2, each_s=(B2-B1)/3), line3=dict(shot=L3, art_in=ART_IN)),
    stills_dir=str(ST), stills_verdict='全部取 selected.json verdict=pass',
    art=dict(text=ART, font='Ma Shan Zheng 2.003 (SIL OFL 1.1, google/fonts)', size=size, width_px=artinfo[0], width_ratio=round(artinfo[0]/W, 3), top_px=round(artinfo[2]), bottom_px=round(artinfo[2]+artinfo[1])),
    sfx='none', bgm='none (intro-node 2026-10-08 局部例外)')
(I/'intro_manifest_partial.json').write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(man['art'], ensure_ascii=False))