import json,sys
from pathlib import Path
from PIL import Image, ImageDraw
M=Path(sys.argv[1]); man=json.load(open(M/'inputs_clean'/'clean_manifest.json',encoding='utf-8'))
rows=[]
for e in man:
    a=Image.open(e['source']).convert('RGB'); b=Image.open(e['output']).convert('RGB'); W,H=a.size
    for r in e['regions']:
        if 'ring' in r: cx,cy,rx,ry,_=r['ring']; box=[cx-rx*1.15,cy-ry*1.15,cx+rx*1.15,cy+ry*1.15]
        elif 'rect' in r: box=r['rect']
        else: xs=[p[0] for p in r['poly']]; ys=[p[1] for p in r['poly']]; box=[min(xs),min(ys),max(xs),max(ys)]
        bx=[max(0,box[0])*W,max(0,box[1])*H,min(1,box[2])*W,min(1,box[3])*H]
        ca=a.crop(bx); cb=b.crop(bx); s=380/max(1,ca.height); ca=ca.resize((max(1,int(ca.width*s)),380)); cb=cb.resize(ca.size)
        t=Image.new('RGB',(ca.width*2+10,410),(20,20,20)); t.paste(ca,(0,30)); t.paste(cb,(ca.width+10,30)); ImageDraw.Draw(t).text((5,5),e['shot']+' '+r['why'],fill=(255,255,0))
        if t.width>1400: t=t.resize((1400,int(410*1400/t.width)))
        rows.append(t)
H=sum(r.height for r in rows); sheet=Image.new('RGB',(1400,H),(0,0,0)); y=0
for r in rows: sheet.paste(r,(0,y)); y+=r.height
sheet.save(M/'qa'/'clean_compare.jpg',quality=85); print(sheet.size)
