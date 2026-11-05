import subprocess, shutil, re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
P=Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal')  # 2026-10-08 迁移：原 legacy-source\zhumian\b-geomagnetic-reversal，现为单集目录
O=P/'audio'/'subtitles'/'body_r1'; BODY=P/'video'/'source'/'geomag_v3_body_r1.mp4'; S=P/'audio'/'subtitles'/'style_r4'; FD=Path(r'E:\program\1project\video\assets\助眠解说\subtitles\style-r4\fonts')
src=O/'geomag_v3_body_r1-subtitles.ass'; dst=S/'geomag_v3_body_r1-subtitles-style_r4.ass'
FONT=FD/'SourceHanSansSC-Heavy.otf'; REF=S/'douyin_reference.png'
SIZE,OUTL,SHAD,MV=96,5,2,118
STYLE='Style: B,Source Han Sans SC Heavy,%d,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,%d,%d,2,96,96,%d,1'%(SIZE,OUTL,SHAD,MV)
L=src.read_text(encoding='utf-8-sig').split('\n')
for i,l in enumerate(L):
    if l.startswith('Style: B,'): L[i]=STYLE
assert not dst.exists(); dst.write_text('\n'.join(L),encoding='utf-8-sig'); print(STYLE)
# overflow check: libass em = size*upm/(winAsc+winDesc) = size/1.448
EM=SIZE*1000/1448; f=ImageFont.truetype(str(FONT),round(EM)); SAFE=1920*0.9
isw=lambda c:bool(re.match(r'[\u4e00-\u9fffA-Za-z0-9]',c))
rows=[]
for l in L:
    if l.startswith('Dialogue:'):
        tx=l.split(',',9)[9]; rows.append((f.getlength(tx)+2*OUTL,tx,sum(map(isw,tx))))
over=sorted([r for r in rows if r[0]>SAFE],reverse=True); rows.sort(reverse=True)
print('em px',round(EM,1),'cues',len(rows),'over90%',len(over))
for w,t,n in rows[:8]: print(' %d px  %d字  %s'%(w,n,t))
print('plan1 >16字 需重断行的条数',sum(1 for r in rows if r[2]>16))
print('plan2 需单独缩小字号的条数',len(over),'最小缩放', round(min([SAFE/r[0] for r in over],default=1),3),'→ 最小字号',round(SIZE*min([SAFE/r[0] for r in over],default=1)))
import collections; print('字数分布',sorted(collections.Counter(r[2] for r in rows).items()))
out=S/'geomag_v3_sub_style_r4_first10s.mp4'; assert not out.exists()
subprocess.run(['ffmpeg','-v','error','-n','-i',str(BODY),'-t','10','-vf','ass=%s:fontsdir=../../../../../../../assets/助眠解说/subtitles/style-r4/fonts'%dst.name,'-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',out.name],cwd=str(S),check=True)
frames=[]
for k,tm in enumerate((2.2,5.5)):
    j=S/('geomag_v3_sub_style_r4_frame_%.1fs_1080p.png'%tm); assert not j.exists()
    subprocess.run(['ffmpeg','-v','error','-n','-ss',str(tm),'-i',str(out),'-frames:v','1',str(j)],check=True); frames.append(j)
import numpy as np
a=np.asarray(Image.open(frames[0]).convert('L')).astype(int)[700:,:]; ys,xs=np.where(a>245); print('frame2.2 white ink x',xs.min(),xs.max(),'y',ys.min()+700,ys.max()+700,'center y %.1f%%'%((ys.min()+ys.max())/2/10.8+700/10.8))
ref=Image.open(REF).convert('RGB'); rv=ref.crop((0,0,ref.width,round(ref.width*9/16))).resize((960,540),Image.LANCZOS)
ou=Image.open(frames[0]).convert('RGB').resize((960,540),Image.LANCZOS)
lab=ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc',26); cs=Image.new('RGB',(1920,584),(15,15,15)); cs.paste(rv,(0,44)); cs.paste(ou,(960,44)); d=ImageDraw.Draw(cs)
d.text((10,8),'参考：抖音截图（裁 16:9 视频区，缩到 960 宽）',font=lab,fill=(255,220,90)); d.text((970,8),'style_r4：思源黑体 Heavy %d / 描边 %d / 阴影 %d，t=2.2s'%(SIZE,OUTL,SHAD),font=lab,fill=(255,220,90))
c=S/'geomag_v3_sub_style_r4_compare.jpg'; assert not c.exists(); cs.save(c,quality=92)
print(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,width,height','-of','csv=p=0',str(out)],capture_output=True,text=True).stdout)
U=Path(r'C:\Users\10060\geomag_v3_sub_out\style_r4'); U.mkdir(exist_ok=True)
for x in [out,c,dst,*frames]:
    if not (U/x.name).exists(): shutil.copy2(x,U/x.name)
print('done')
