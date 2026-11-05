# 2026-10-02 01:1x: s19 -> 7% crop (Step 0), s26 -> R3 cell 5 (老大 01:08). Keeps previous choices as alternates/notes.
import json, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
G=Path('E:/program/1project/video/projects/猎奇/episodes/tudou/image/plot_grids_v2'); WIN='E:\\program\\1project\\video\\projects\\猎奇\\episodes\\tudou'
win=lambda rel: WIN+'\\image\\plot_grids_v2\\'+rel.replace('/','\\')
m=json.load(open(G/'frame_map_v3.json'))
old19=m['s19']['upscaled']; old26=m['s26']['upscaled']
m['s19'].update(upscaled=win('local_fixes_v3/s19_G3p7_crop7_up.png'),method='ultrasharp',
  alternates=[old19]+m['s19']['alternates'],
  note='本地修（02:0x 前改 7%）：原格从下边裁掉 7%（36 px，512→476），重新用 UltraSharp 放大到 1080×1920，衬衫缝完全去掉。之前用的是裁 4% 的版本（'+old19+'），还剩一条很窄的缝。')
m['s19']['from']=win('G3_panels/G3_p7_s19.png')
m['s26']=dict(source='plot_grid_cell',grid='R3',cell=5,panel=win('R3_panels/R3_p5_s26v5.png'),upscaled=win('R3_upscaled/R3_p5_s26v5.png'),method='lanczos',
  alternates=[win('R3_upscaled/R3_p2_s26v2.png'),old26]+[a for a in m['s26']['alternates'] if a!=old26],
  note='R3 重画（老大 2026-10-02 01:08 批）：总裁身体和头一起背对镜头，没有扭头，手举过肩送客；秘书含泪（拿手帕）鞠躬做「请」；地面干。之前用的是 R1 格3（'+old26+'），身体背对但头几乎转了 180°。',
  v2_upscaled=m['s26'].get('v2_upscaled'))
json.dump(m,open(G/'frame_map_v3.json','w'),ensure_ascii=False,indent=2)
v2=json.load(open(G/'frame_map_v2.json'))
box=lambda w: w.replace(WIN,'E:/program/1project/video/projects/猎奇/episodes/tudou').replace('\\','/')
old=G/'final_firstframes_v3_contact.png'
if old.exists() and not (G/'final_firstframes_v3_contact_0059.png').exists(): shutil.move(old,G/'final_firstframes_v3_contact_0059.png')
order=list(v2.keys()); tw,th,pad,lab=240,427,8,30; cols=6
W=cols*tw+(cols+1)*pad; H=6*(th+lab)+7*pad+50
s=Image.new('RGB',(W,H),'white'); d=ImageDraw.Draw(s)
fb=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',20); fs=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',13)
d.text((pad,12),'tudou first frames v3 (frame_map_v3.json, incl. R3 s26 + s19 crop7), shot order',fill='black',font=fb)
for i,k in enumerate(order):
    r,c=divmod(i,cols); x=pad+c*(tw+pad); y=50+pad+r*(th+lab+pad); e=m[k]
    im=Image.open(box(e['upscaled'])).convert('RGB'); assert im.size==(1080,1920),k
    s.paste(im.resize((tw,th),Image.LANCZOS),(x,y+lab))
    src=e.get('grid') and f"{e['grid']} c{e['cell']}" or ('local fix' if e['source']=='local_fix' else 'scene ref')
    ch=e['upscaled']!=v2[k]['upscaled']
    d.text((x+2,y+4),k,fill='red' if ch else 'black',font=fb); d.text((x+62,y+9),src+(' (new)' if ch else ''),fill='black',font=fs)
s.save(G/'final_firstframes_v3_contact.png'); print('ok')
