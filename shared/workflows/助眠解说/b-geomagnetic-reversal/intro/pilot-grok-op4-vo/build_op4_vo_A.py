"""One-off intro example A (CPU render). Narration b2 seed7 takes, atempo 0.88; r4 subtitles; art text only in last scene."""
import json, subprocess, shutil, math
from pathlib import Path
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter
P = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal')  # 2026-10-08 迁移：原 legacy-source\zhumian\b-geomagnetic-reversal，现为单集目录
O = P/'video'/'intro'/'op4_vo_A'; T = Path(r'E:\program\1project\video\shared\work\scratch\zhumian-geomag-op4_vo_A-tmp'); T.mkdir(parents=True, exist_ok=True); R = O/'render'; FD = Path(r'E:\program\1project\video\assets\助眠解说\intro\fonts')
RAW = P/'image'/'stills'/'20261007-v3-stills-b01'/'raw'; BODY = P/'video'/'source'/'geomag_v3_body_r1.mp4'
R4 = P/'audio'/'subtitles'/'style_r4'
W, H, FPS, SR = 1920, 1080, 30, 48000
LINES = ['八十万年前，罗盘标着北的一端，会指向南方', '地球磁场的南北，翻转过很多次', '接下来的二十三分钟，我们来讲讲地球磁场']
def run(*a, **k): subprocess.run([str(x) for x in a], check=True, **k)
def new(p):
    assert not Path(p).exists(), f'exists: {p}'; return p
# ---- audio ----
segs = []
for i in ('i01', 'i02', 'i03'):
    x, sr = sf.read(str(P/'audio'/'vo-raw'/'op4_vo_A'/'takes-seed7'/f'{i}.wav'))
    x = x.mean(1) if x.ndim > 1 else x; fr = int(0.02*sr)
    db = 20*np.log10(np.array([np.sqrt(np.mean(x[k:k+fr]**2)+1e-12) for k in range(0, len(x)-fr, fr)]))
    idx = np.where(db > -45)[0]; a = max(0, idx[0]*fr - int(0.10*sr)); b = min(len(x), (idx[-1]+1)*fr + int(0.15*sr))
    tr = T/f'{i}_trim.wav'; sf.write(str(tr), x[a:b], sr)
    pc = T/f'{i}_paced.wav'
    if not pc.exists(): run('ffmpeg', '-v', 'error', '-n', '-i', tr, '-af', 'atempo=0.88', '-ar', SR, '-ac', 1, pc)
    y, _ = sf.read(str(pc)); segs.append(y)
HEAD, GAP, TAIL = 0.4, 0.45, 0.8
t = HEAD; times = []
for y in segs: times.append((t, t+len(y)/SR)); t += len(y)/SR + GAP
TI = times[-1][1] + TAIL; NI = round(TI*FPS); TI = NI/FPS
nar = np.zeros(int(round(TI*SR)))
for (s, e), y in zip(times, segs): i0 = int(round(s*SR)); nar[i0:i0+len(y)] += y
NAR = O/'op4_vo_A_narration.wav'
if not NAR.exists(): sf.write(str(NAR), nar.astype(np.float32), SR, subtype='PCM_16')
print('times', [(round(s,3), round(e,3)) for s, e in times], 'intro', TI)
# ---- subtitles (r4 style) ----
hdr = (R4/'geomag_v3_body_r1-subtitles-style_r4.ass').read_text(encoding='utf-8-sig').split('[Events]')[0]
def ta(x): h=int(x//3600); m=int(x%3600//60); s=x%60; return '%d:%02d:%05.2f'%(h,m,s)
def ts(x): h=int(x//3600); m=int(x%3600//60); s=x%60; return ('%02d:%02d:%06.3f'%(h,m,s)).replace('.',',')
cues = []
for k, ((s, e), txt) in enumerate(zip(times, LINES)):
    nxt = times[k+1][0]-0.05 if k+1 < len(times) else TI
    cues.append((s, min(e+0.3, nxt), txt))
ASS = O/'op4_vo_A.ass'; SRT = O/'op4_vo_A.srt'
if not ASS.exists(): ASS.write_text(hdr + '[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n' + ''.join('Dialogue: 0,%s,%s,B,,0,0,0,,%s\n'%(ta(s),ta(e),x) for s,e,x in cues), encoding='utf-8-sig')
if not SRT.exists(): SRT.write_text(''.join('%d\n%s --> %s\n%s\n\n'%(i+1,ts(s),ts(e),x) for i,(s,e,x) in enumerate(cues)), encoding='utf-8')
# 2026-10-08：字体改用 assets（思源黑体在 subtitles\style-r4\fonts，马善政在 intro\fonts），不再复制到批次 fonts\
# ---- picture ----
def cover(im, w, h):
    s = max(w/im.width, h/im.height); im = im.resize((round(im.width*s), round(im.height*s)), Image.LANCZOS)
    x, y = (im.width-w)//2, (im.height-h)//2; return im.crop((x, y, x+w, y+h))
def load(n, w=W, h=H): return cover(Image.open(RAW/n).convert('RGB'), w, h)
def ease_io(u): u = min(1, max(0, u)); return u*u*(3-2*u)
def ease_out_back(u, s=0.8): u = min(1, max(0, u)) - 1; return 1 + (s+1)*u**3 + s*u**2
def push(im, u, z1, zin=True):
    z = 1 + z1*(ease_io(u) if zin else 1-ease_io(u)); cw, ch = round(W/z), round(H/z); x, y = (W-cw)//2, (H-ch)//2
    return im.crop((x, y, x+cw, y+ch)).resize((W, H), Image.BILINEAR)
full = {n: load(n) for n in ['ch1-c10.png', 'ch2-c02.png', 'ch3-c08.png', 'ch4-c06.png', 'ch1-c13_r1.png', 'ch4-c04_r1.png']}
PAN = ['ch1-c10.png', 'ch2-c02.png', 'ch2-c09.png', 'ch4-c08.png']
LAY = [((560, 330), (860, 484), -1), ((1360, 330), (860, 484), 1), ((560, 760), (860, 484), -1), ((1360, 760), (860, 484), 1)]
pans = [load(n, *LAY[i][1]) for i, n in enumerate(PAN)]
s1, e1 = times[0]; s2, e2 = times[1]; s3, e3 = times[2]
B1 = s2 - 0.25; B2 = s3 - 0.25          # scene boundaries just before each sentence
CE, EXP = 1.6, 0.5                      # collage until 1.6s, expand ch1-c10 to full over 0.5s
DIS1 = CE + EXP + max(0.8, (B1 - CE - EXP)*0.45)   # dissolve ch1-c10 -> ch2-c02
fnt_art = ImageFont.truetype(str(FD/'MaShanZheng-Regular.ttf'), 300)
ART = '地球磁场'; d0 = ImageDraw.Draw(Image.new('RGB', (10, 10))); bb = d0.textbbox((0, 0), ART, font=fnt_art)
size = round(300 * (W*0.65) / (bb[2]-bb[0])); fnt_art = ImageFont.truetype(str(FD/'MaShanZheng-Regular.ttf'), size)
def art_layer(alpha, scale):
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); bb = d.textbbox((0, 0), ART, font=fnt_art, stroke_width=8)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]; x = (W-tw)/2 - bb[0]; y = H*0.43 - th/2 - bb[1]
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).text((x+6, y+8), ART, font=fnt_art, fill=(0, 0, 0, 170), stroke_width=8, stroke_fill=(0, 0, 0, 170))
    sh = sh.filter(ImageFilter.GaussianBlur(10)); lay.alpha_composite(sh)
    d.text((x, y), ART, font=fnt_art, fill=(250, 238, 205, 255), stroke_width=8, stroke_fill=(20, 16, 10, 255))
    if scale != 1: lay = lay.resize((round(W*scale), round(H*scale)), Image.BICUBIC).crop(((round(W*scale)-W)//2, (round(H*scale)-H)//2, (round(W*scale)-W)//2+W, (round(H*scale)-H)//2+H))
    a = np.asarray(lay).copy(); a[..., 3] = (a[..., 3]*alpha).astype(np.uint8); return Image.fromarray(a), (tw, th)
ART_IN = max(s3 + 1.6, TI - 2.4); artinfo = None
def frame(f):
    global artinfo
    tt = f/FPS
    if tt < B1:
        if tt < CE + EXP:
            can = Image.new('RGB', (W, H), (0, 0, 0))
            for i, (pim, ((x0, y0), (pw, ph), dr)) in enumerate(zip(pans, LAY)):
                st = i*3
                if f < st: continue
                sc = 0.2 + 0.8*ease_out_back((f-st)/12)
                sl = dr*1.2*max(0, f-12)
                cx = W/2 + (x0 + sl - W/2)*sc; cy = H/2 + (y0 - H/2)*sc; w, h = max(8, round(pw*sc)), max(8, round(ph*sc))
                if i == 0 and tt >= CE:   # expand panel 0 to full frame
                    u = ease_io((tt-CE)/EXP); cx = cx + (W/2-cx)*u; cy = cy + (H/2-cy)*u; w = round(w + (W-w)*u); h = round(h + (H-h)*u)
                p = pim.resize((w, h), Image.BILINEAR) if not (i == 0 and tt >= CE) else full[PAN[0]].resize((w, h), Image.BILINEAR)
                bw = 4; fr_ = Image.new('RGB', (w+2*bw, h+2*bw), (236, 236, 236)); fr_.paste(p, (bw, bw))
                al = min(1, (f-st)/8)
                if i != 0 and tt >= CE: al *= max(0, 1-(tt-CE)/EXP)
                order_last = (i == 0 and tt >= CE)
                if not order_last: can.paste(fr_, (round(cx-fr_.width/2), round(cy-fr_.height/2)), Image.new('L', fr_.size, round(255*al)))
            if tt >= CE:
                i = 0; (x0, y0), (pw, ph), dr = LAY[0]; sc = 1; sl = dr*1.2*max(0, f-12); u = ease_io((tt-CE)/EXP)
                cx = x0+sl; cy = y0; cx += (W/2-cx)*u; cy += (H/2-cy)*u; w = round(pw+(W-pw)*u); h = round(ph+(H-ph)*u)
                bw = round(4*(1-u)); p = full[PAN[0]].resize((w, h), Image.BILINEAR); fr_ = Image.new('RGB', (w+2*bw, h+2*bw), (236, 236, 236)); fr_.paste(p, (bw, bw))
                can.paste(fr_, (round(cx-fr_.width/2), round(cy-fr_.height/2)))
            return can
        a = push(full['ch1-c10.png'], (tt-CE-EXP)/(B1-CE-EXP), 0.025)
        if tt >= DIS1:
            b = push(full['ch2-c02.png'], (tt-DIS1)/(B1-DIS1), 0.03, zin=False)
            return Image.blend(a, b, min(1, (tt-DIS1)/0.3))
        return a
    if tt < B2:
        shots = ['ch3-c08.png', 'ch4-c06.png', 'ch1-c13_r1.png']; L = (B2-B1)/3; k = min(2, int((tt-B1)//L)); u = (tt-B1-k*L)/L
        im = push(full[shots[k]], u, 0.03, zin=(k % 2 == 0))
        if tt-B1-k*L < 0.2:
            prev = push(full['ch2-c02.png'], 1, 0.03, zin=False) if k == 0 else push(full[shots[k-1]], 1, 0.03, zin=((k-1) % 2 == 0))
            im = Image.blend(prev, im, (tt-B1-k*L)/0.2)
        return im
    im = push(full['ch4-c04_r1.png'], (tt-B2)/(TI-B2), 0.04)
    if tt < B2 + 0.2: im = Image.blend(push(full['ch1-c13_r1.png'], 1, 0.03), im, (tt-B2)/0.2)
    if tt >= ART_IN:
        u = min(1, (tt-ART_IN)/0.6); lay, artinfo = art_layer(ease_io(u), 0.97 + 0.03*ease_io(u))
        im = im.convert('RGBA'); im.alpha_composite(lay); im = im.convert('RGB')
    return im
CLEAN = T/'intro_clean.mp4'
if not CLEAN.exists():
    pr = subprocess.Popen(['ffmpeg', '-v', 'error', '-n', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-i', str(NAR),
        '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-ac', '2', '-ar', str(SR), '-t', '%.3f' % TI, str(CLEAN)], stdin=subprocess.PIPE)
    for f in range(NI): pr.stdin.write(frame(f).tobytes())
    pr.stdin.close(); assert pr.wait() == 0
SUBV = T/'intro_sub.mp4'
if not SUBV.exists(): run('ffmpeg', '-v', 'error', '-n', '-i', CLEAN, '-vf', f'ass={ASS.name}:fontsdir=../../../../../../../assets/助眠解说/subtitles/style-r4/fonts', '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', '-c:a', 'copy', SUBV, cwd=str(O))
BH = T/'body_head2s.mp4'
if not BH.exists(): run('ffmpeg', '-v', 'error', '-n', '-i', BODY, '-t', '2', '-vf', 'fps=30,scale=1920:1080', '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-ar', str(SR), '-ac', '2', BH)
def cat(a, out):
    if out.exists(): return
    run('ffmpeg', '-v', 'error', '-n', '-i', a, '-i', BH, '-filter_complex', '[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]', '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out)
OUTV = O/'op4_vo_A.mp4'; cat(SUBV, OUTV); cat(CLEAN, O/'op4_vo_A_clean.mp4')
# contact sheet
CS = O/'op4_vo_A_contact.jpg'
if not CS.exists():
    tdir = T/'cs'; tdir.mkdir(exist_ok=True)
    run('ffmpeg', '-v', 'error', '-n', '-i', OUTV, '-vf', 'fps=5,scale=320:180', str(tdir/'f%04d.png'))
    fs = sorted(tdir.glob('f*.png')); lab = ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc', 16)
    sheet = Image.new('RGB', (320*8, 180*math.ceil(len(fs)/8)))
    for k, p in enumerate(fs):
        im = Image.open(p).convert('RGB'); ImageDraw.Draw(im).text((4, 2), '%.1fs' % (k/5), font=lab, fill=(255, 230, 0), stroke_width=2, stroke_fill=(0, 0, 0)); sheet.paste(im, ((k % 8)*320, (k//8)*180))
    sheet.save(CS, quality=85)
man = dict(video=str(OUTV), clean=str(O/'op4_vo_A_clean.mp4'), intro_s=TI, body_head_s=2.0, narration=str(NAR), voice='b2-warm-male VoxCPM2 seed7 cfg2 10steps, trim lead/trail, atempo 0.88',
    sentence_times=times, cues=cues, scenes=dict(line1=dict(collage=PAN, expand='ch1-c10', then='ch2-c02', collage_end=CE, expand_s=EXP, dissolve_at=DIS1),
    line2=['ch3-c08', 'ch4-c06', 'ch1-c13_r1'], line3='ch4-c04_r1', art_in=ART_IN), art=dict(text=ART, font='Ma Shan Zheng 2.003 (SIL OFL 1.1, google/fonts)', size=size, width_px=artinfo[0] if artinfo else None, width_ratio=round(artinfo[0]/W, 3) if artinfo else None),
    subtitles=dict(style='style_r4', ass=str(ASS), srt=str(SRT)), sfx='none', bgm='none')
mp = O/'manifest.json'
if not mp.exists(): mp.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(man['art'], ensure_ascii=False), 'intro', TI)