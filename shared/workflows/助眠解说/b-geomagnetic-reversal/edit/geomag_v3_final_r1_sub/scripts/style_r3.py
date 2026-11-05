import subprocess, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
P=Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal')  # 2026-10-08 迁移：原 legacy-source\zhumian\b-geomagnetic-reversal，现为单集目录
O=P/'audio'/'subtitles'/'body_r1'; BODY=P/'video'/'source'/'geomag_v3_body_r1.mp4'; R2=P/'audio'/'subtitles'/'style_r2'; S=P/'audio'/'subtitles'/'style_r3'; S.mkdir(exist_ok=True)
src=R2/'geomag_v3_body_r1-subtitles-style_r2.ass'; dst=S/'geomag_v3_body_r1-subtitles-style_r3.ass'
L=src.read_text(encoding='utf-8-sig').split('\n')
for i,l in enumerate(L):
    if l.startswith('Style: B,'):
        f=l.split(','); assert f[2]=='56' and f[5]=='&HCC101010'; f[2]='59'; L[i]=','.join(f); print('style',L[i])
assert not dst.exists(); dst.write_text('\n'.join(L),encoding='utf-8-sig')
fnt=ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc',59); ws=[]
for l in L:
    if l.startswith('Dialogue:'):
        tx=l.split(',',9)[9]; ws.append((fnt.getlength(tx)+2*14,tx))
ws.sort(reverse=True); print('n',len(ws),'widest px',round(ws[0][0]),ws[0][1]); print('top3',[(round(w),t) for w,t in ws[:3]])
print('over 90% (1728px)',[(round(w),t) for w,t in ws if w>1728]); print('over margins (1680px)',[(round(w),t) for w,t in ws if w>1680])
out=S/'geomag_v3_sub_style_r3_first10s.mp4'; assert not out.exists()
subprocess.run(['ffmpeg','-v','error','-n','-i',str(BODY),'-t','10','-vf','ass='+dst.name,'-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',out.name],cwd=str(S),check=True)
r2v=R2/'geomag_v3_sub_style_r2_first10s.mp4'; lab=ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc',30); strips=[]
for tm in (2.2,5.5,7.6):
    for nm,v in (('r2 56px',r2v),('r3 59px',out)):
        j=S/f'cmp_{nm[:2]}_{tm}.png'
        subprocess.run(['ffmpeg','-v','error','-n','-ss',str(tm),'-i',str(v),'-frames:v','1','-vf','crop=1920:220:0:860',str(j)],check=True)
        c=Image.new('RGB',(1920,264),(15,15,15)); c.paste(Image.open(j).convert('RGB'),(0,44)); ImageDraw.Draw(c).text((10,4),f'{nm}  t={tm}s  (原始像素，底部 860–1080 裁切，未缩放)',font=lab,fill=(255,220,90)); strips.append(c)
sh=Image.new('RGB',(1920,264*len(strips))); [sh.paste(c,(0,i*264)) for i,c in enumerate(strips)]
cs=S/'geomag_v3_sub_style_r3_compare.jpg'; assert not cs.exists(); sh.save(cs,quality=92)
print(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,width,height','-of','csv=p=0',str(out)],capture_output=True,text=True).stdout)
U=Path(r'C:\Users\10060\geomag_v3_sub_out\style_r3'); U.mkdir(exist_ok=True)
for f in (out,cs,dst):
    if not (U/f.name).exists(): shutil.copy2(f,U/f.name)
print('done')
