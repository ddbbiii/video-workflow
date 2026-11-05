# cut grid into 9 cells, upscale per-cell method, build contact sheet. No API calls.
import sys, json, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
G=Path('E:/program/1project/video/projects/猎奇/episodes/tudou/image/plot_grids_v2'); KP=Path('/workspace/kepu-pipeline')
CELLS={
 'G1':[('s01','ultrasharp'),('s02','ultrasharp'),('s03','ultrasharp'),('s04','ultrasharp'),('s05','ultrasharp'),('s06','lanczos'),('s01alt','ultrasharp'),('s06alt','lanczos'),('s04alt','ultrasharp')],
 'G2':[('s07','ultrasharp'),('s08','ultrasharp'),('s09','ultrasharp'),('s10','lanczos'),('s11','lanczos'),('s12','ultrasharp'),('s13','ultrasharp'),('s13alt','ultrasharp'),('s11alt','lanczos')],
 'G3':[('t1alt','lanczos'),('s14','ultrasharp'),('s15','ultrasharp'),('s16','ultrasharp'),('s17','ultrasharp'),('s18','ultrasharp'),('s19','ultrasharp'),('s20','ultrasharp'),('s15alt','ultrasharp')],
 'G4':[('s21','ultrasharp'),('s22','lanczos'),('s23','ultrasharp'),('s24alt','lanczos'),('s25','ultrasharp'),('s26','lanczos'),('s22alt','lanczos'),('s23alt','ultrasharp'),('s26alt','lanczos')],
 'G5':[('s27','lanczos'),('s28','ultrasharp'),('s29','ultrasharp'),('s30','ultrasharp'),('s31','ultrasharp'),('s32','ultrasharp'),('s33','ultrasharp'),('t2alt','lanczos'),('s34','lanczos')],
}
def cut(g):
    im=Image.open(G/f'{g}_grid.png').convert('RGB'); a=np.asarray(im)
    white=(a.min(2)>235)&((a.max(2)-a.min(2))<12); out=[]
    for axis in (0,1):
        c=white.mean(axis=axis); ix=np.where(c>.55)[0]; groups=[]
        for x in ix:
            if not groups or x>groups[-1][-1]+1: groups.append([x])
            else: groups[-1].append(x)
        out.append([(int(g0[0]),int(g0[-1])) for g0 in groups])
    cols,rows=out
    def spans(gs,n):
        gs=[x for x in gs if 0<x[0] and x[1]<n-1 and 0.2*n<x[0]<0.8*n]
        return [(0,gs[0][0])]+[(gs[i][1]+1,gs[i+1][0]) for i in range(len(gs)-1)]+[(gs[-1][1]+1,n)]
    xs=spans(cols,a.shape[1]); ys=spans(rows,a.shape[0])
    if len(xs)!=3 or len(ys)!=3:
        print('gutter detect fallback', g, cols, rows); xs=[(0,339),(343,683),(687,1024)]; ys=[(0,510),(514,1020),(1024,1536)]
    d=G/f'{g}_panels'; d.mkdir(exist_ok=True); meta=[]; n=0
    for y0,y1 in ys:
        for x0,x1 in xs:
            shot,m=CELLS[g][n]; c=im.crop((x0,y0,x1,y1)); f=d/f'{g}_p{n+1}_{shot}.png'; c.save(f)
            meta.append(dict(cell=n+1,shot=shot,method=m,box=[x0,y0,x1,y1],size=list(c.size),panel=f.name)); n+=1
    json.dump(meta,open(d/'cells.json','w'),indent=1); return meta
def upscale(g,meta):
    u=G/f'{g}_upscaled'; u.mkdir(exist_ok=True)
    for m in meta:
        src=G/f'{g}_panels'/m['panel']; dst=u/m['panel']
        if dst.exists(): continue
        subprocess.run([str(KP/'.venv-upscale/bin/python'),str(KP/'scripts/upscale_frame.py'),'--in',str(src),'--out',str(dst),'--method',m['method'],'--size','1080x1920','--fit','crop','--log',str(u/'upscale_log.jsonl')],check=True,cwd=KP)
def contact(g,meta):
    tw,th,pad,lab=360,640,10,34; W=3*tw+4*pad; H=3*(th+lab)+4*pad
    s=Image.new('RGB',(W,H),'white'); d=ImageDraw.Draw(s)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',20)
    for i,m in enumerate(meta):
        r,c=divmod(i,3); x=pad+c*(tw+pad); y=pad+r*(th+lab+pad)
        s.paste(Image.open(G/f'{g}_upscaled'/m['panel']).convert('RGB').resize((tw,th),Image.LANCZOS),(x,y+lab))
        d.text((x+4,y+6),f"cell {m['cell']} -> {m['shot']} [{m['method']}]",fill='black',font=font)
    s.save(G/f'{g}_contact.png')
if __name__=='__main__':
    for g in sys.argv[1:]:
        if g=='G1':
            meta=json.load(open(G/'G1_panels/cells.json'))
            for m,(shot,meth) in zip(meta,CELLS['G1']): m['method']=meth; m['panel']=Path(m['file']).name; m.pop('file',None)
            json.dump(meta,open(G/'G1_panels/cells.json','w'),indent=1)
        else:
            meta=cut(g); upscale(g,meta)
        contact(g,meta); print(g,'done',[(m['cell'],m['shot'],m['method'],m['size']) for m in meta])
