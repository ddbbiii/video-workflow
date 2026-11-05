from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import random, math, hashlib, json

OUT = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\image\covers\geomag-poster-r1')  # 2026-10-08 迁移：脚本移到 shared\workflows，输出仍写回单集封面目录
P = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal')
SRC = P / 'image/stills/20261007-v3-stills-b01/raw/ch1-c04_r1.png'
FONTS_SUB = Path(r'E:\program\1project\video\assets\助眠解说\subtitles\style-r4\fonts'); FONTS_INTRO = Path(r'E:\program\1project\video\assets\助眠解说\intro\fonts')
def _font(n): return (FONTS_INTRO if n.startswith('MaShanZheng') else FONTS_SUB) / n
random.seed(20261008)

def stars(w, h):
    im = Image.new('RGB', (w,h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        t=y/h
        d.line((0,y,w,y), fill=(int(4+3*t),int(12+9*t),int(24+12*t)))
    for _ in range(1100):
        x=random.randrange(w); y=random.randrange(h); r=random.choice([1,1,1,2])
        c=random.randrange(45,120)
        d.ellipse((x-r,y-r,x+r,y+r),fill=(c//2,c*3//4,c))
    return im

def text(im, value, xy, size, fontname, color, glow=False):
    font=ImageFont.truetype(str(_font(fontname)),size)
    layer=Image.new('RGBA', im.size)
    d=ImageDraw.Draw(layer)
    d.text(xy,value,font=font,fill=color,stroke_width=1,stroke_fill=color)
    if glow:
        im.alpha_composite(layer.filter(ImageFilter.GaussianBlur(size/22)))
    im.alpha_composite(layer)

def centered(im, value, y, size, name, color, glow=False):
    f=ImageFont.truetype(str(_font(name)),size)
    x=(im.width-f.getlength(value))/2
    text(im,value,(int(x),y),size,name,color,glow)

original=Image.open(SRC).convert('RGB')
horizontal=ImageOps.mirror(original).resize((3840,2160),Image.Resampling.LANCZOS).convert('RGBA')
shade=Image.new('RGBA',horizontal.size)
sd=ImageDraw.Draw(shade)
for x in range(3840):
    a=int(185*max(0,1-x/2550)**1.5)
    sd.line((x,0,x,2160),fill=(3,10,22,a))
horizontal.alpha_composite(shade)
text(horizontal,'助眠科学解说',(245,305),74,'SourceHanSansSC-Heavy.otf',(146,184,192,255))
text(horizontal,'地球磁场',(230,510),335,'MaShanZheng-Regular.ttf',(246,229,191,255),True)
text(horizontal,'南北翻转的漫长往事',(250,970),100,'SourceHanSansSC-Heavy.otf',(219,229,230,255))
text(horizontal,'《地球磁场》',(255,1800),62,'SourceHanSansSC-Heavy.otf',(155,181,192,255))

vertical=stars(2160,3840).convert('RGBA')
# The entire source remains visible: independently composed placement, no portrait crop.
scene=original.resize((2160,1215),Image.Resampling.LANCZOS).convert('RGBA')
mask=Image.new('L',scene.size,255); md=ImageDraw.Draw(mask)
for y in range(scene.height):
    edge=min(y/170,(scene.height-1-y)/220,1)
    md.line((0,y,2160,y),fill=int(255*max(0,edge)))
vertical.paste(scene,(0,1770),mask)
centered(vertical,'助眠科学解说',570,70,'SourceHanSansSC-Heavy.otf',(146,184,192,255))
centered(vertical,'地球',840,345,'MaShanZheng-Regular.ttf',(246,229,191,255),True)
centered(vertical,'磁场',1180,345,'MaShanZheng-Regular.ttf',(246,229,191,255),True)
centered(vertical,'南北翻转的漫长往事',1580,82,'SourceHanSansSC-Heavy.otf',(219,229,230,255))
centered(vertical,'《地球磁场》',3270,60,'SourceHanSansSC-Heavy.otf',(155,181,192,255))

outputs=[]
for label,im in [('horizontal',horizontal),('vertical',vertical)]:
    rgb=im.convert('RGB'); file=OUT/f'geomag-cover-{label}-r1.png'; rgb.save(file)
    rgb.save(OUT/f'geomag-cover-{label}-r1.jpg',quality=95,subsampling=0)
    preview=rgb.copy(); preview.thumbnail((960,960)); preview.save(OUT/f'{label}-preview.jpg',quality=90)
    outputs.append({'file':str(file),'dimensions':list(rgb.size),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'purpose':label+' episode cover'})
board=Image.new('RGB',(1300,1000),(17,22,30))
h=horizontal.convert('RGB'); h.thumbnail((900,600)); board.paste(h,(15,220))
v=vertical.convert('RGB'); v.thumbnail((340,970)); board.paste(v,(945,15))
board.save(OUT/'contact-sheet.jpg',quality=90)
manifest={'source':str(SRC),'source_dimensions':list(original.size),'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'method':'deterministic Pillow typography/compositing; Lanczos enlargement, not AI super-resolution','horizontal':'mirrored source, left gradient for type','vertical':'full source placed at y=1770, feathered into procedural star backdrop; no crop','texts':['地球磁场','南北翻转的漫长往事','助眠科学解说','《地球磁场》'],'fonts':['MaShanZheng-Regular.ttf','SourceHanSansSC-Heavy.otf'],'outputs':outputs,'qa':'pending visual review','next':'user review'}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(outputs,ensure_ascii=False))
