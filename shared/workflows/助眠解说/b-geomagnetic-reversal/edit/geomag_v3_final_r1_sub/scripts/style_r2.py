import re, subprocess, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
P=Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal')  # 2026-10-08 迁移：原 legacy-source\zhumian\b-geomagnetic-reversal，现为单集目录
O=P/'audio'/'subtitles'/'body_r1'; BODY=P/'video'/'source'/'geomag_v3_body_r1.mp4'; S=P/'audio'/'subtitles'/'style_r2'; S.mkdir(exist_ok=True)
src=O/'geomag_v3_body_r1-subtitles.ass'; dst=S/'geomag_v3_body_r1-subtitles-style_r2.ass'
t=src.read_text(encoding='utf-8-sig'); L=t.split('\n')
for i,l in enumerate(L):
    if l.startswith('Style: B,'):
        f=l.split(','); assert f[2]=='48' and f[5]=='&H99101010'
        f[2]='56'; f[5]=f[6]='&HCC101010'; L[i]=','.join(f); print('style', L[i])
if not dst.exists(): dst.write_text('\n'.join(L),encoding='utf-8-sig')
# safe-area check: measure each line at 56px with YaHei
fnt=ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc',56); over=[]; mx=(0,'')
for l in L:
    if l.startswith('Dialogue:'):
        tx=l.split(',',9)[9]; w=fnt.getlength(tx)+2*14
        if w>mx[0]: mx=(w,tx)
        if w>1920*0.9: over.append((round(w),tx))
print('max line width px', round(mx[0]), mx[1]); print('over 90% safe width', over)
out=S/'geomag_v3_sub_style_r2_first10s.mp4'
if not out.exists():
    subprocess.run(['ffmpeg','-v','error','-n','-i',str(BODY),'-t','10','-vf','ass='+dst.name,'-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',out.name],cwd=str(S),check=True)
old=P/'archive'/'edit'/'geomag_v3_final_r1_sub'/'geomag_v3_body_r1-burned-subtitles.mp4'; lab=ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc',30); rows=[]
for tm in (2.2,5.5,7.6):
    pair=[]
    for nm,v in (('旧样式 48px / 底条约40%',old),('新样式 r2 56px / 底条约20%',out)):
        j=S/f'cmp_{nm[:3]}_{tm}.jpg'
        if not j.exists(): subprocess.run(['ffmpeg','-v','error','-n','-ss',str(tm),'-i',str(v),'-frames:v','1','-vf','scale=960:540',str(j)],check=True)
        im=Image.open(j).convert('RGB'); c=Image.new('RGB',(960,590),(15,15,15)); c.paste(im,(0,50)); ImageDraw.Draw(c).text((10,6),f'{nm}  t={tm}s',font=lab,fill=(255,220,90)); pair.append(c)
    rows.append(pair)
sh=Image.new('RGB',(1920,590*3)); [sh.paste(c,(k*960,r*590)) for r,p in enumerate(rows) for k,c in enumerate(p)]
cs=S/'geomag_v3_sub_style_r2_compare.jpg'
if not cs.exists(): sh.save(cs,quality=90)
print(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,width,height','-of','csv=p=0',str(out)],capture_output=True,text=True).stdout)
U=Path(r'C:\Users\10060\geomag_v3_sub_out\style_r2'); U.mkdir(exist_ok=True)
for f in (out,cs,dst):
    if not (U/f.name).exists(): shutil.copy2(f,U/f.name)
print('done')
