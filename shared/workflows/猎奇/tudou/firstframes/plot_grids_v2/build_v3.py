# Build frame_map_v3.json (v2 kept) and final_firstframes_v3_contact.png. No API calls.
import json, copy
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
G=Path('E:/program/1project/video/projects/猎奇/episodes/tudou/image/plot_grids_v2'); BOX='E:/program/1project/video/projects/猎奇/episodes/tudou'; WIN='E:\\program\\1project\\video\\projects\\猎奇\\episodes\\tudou'
def win(rel): return WIN+'\\image\\plot_grids_v2\\'+rel.replace('/','\\')
def box(w): return w.replace(WIN,BOX).replace('\\','/')
v2=json.load(open(G/'frame_map_v2.json')); v3=copy.deepcopy(v2)
def cellset(shot,grid,cell,name,method,alts,note):
    v3[shot]=dict(source='plot_grid_cell',grid=grid,cell=cell,panel=win(f'{grid}_panels/{name}'),upscaled=win(f'{grid}_upscaled/{name}'),method=method,alternates=alts,note=note,v2_upscaled=v2[shot]['upscaled'])
def local(shot,rel,method,alts,note,src):
    v3[shot]=dict(source='local_fix',from_=src,upscaled=win(rel),method=method,alternates=alts,note=note,v2_upscaled=v2[shot]['upscaled'])
U=lambda g,n: win(f'{g}_upscaled/{n}')
cellset('s01','R2',1,'R2_p1_s01.png','ultrasharp',[U('R2','R2_p6_s01alt.png')],'R2 重画：宾客全是蔬菜头，替换 G1 格1（有正常人头宾客）。')
cellset('s02','R2',2,'R2_p2_s02.png','ultrasharp',[U('G1','G1_p2_s02.png')],'二选一选 R2：背景宾客能看出是蔬菜头（G1 格2 背景人群糊成一片、认不出是什么头）；R2 的表情、泥土质感和 G1 一样好，大厅的光和 R2 其他格一致。')
cellset('s04','R2',3,'R2_p3_s04.png','ultrasharp',[U('R2','R2_p7_s04alt.png')],'R2 重画：衬衫扣好、肚子盖住，替换 G1 格4。')
cellset('s05','R2',4,'R2_p4_s05.png','ultrasharp',[U('R2','R2_p9_s05alt.png'),U('G1','G1_p5_s05.png')],'二选一选 R2：背景是清楚的蔬菜头宾客（G1 格5 右边有个模糊的人头）；掰手指的动作和讨好的笑都在。')
cellset('s06','R2',5,'R2_p5_s06.png','lanczos',[U('R2','R2_p8_s06alt.png')],'R2 重画：老爹衬衫扣好，宾客是蔬菜头，替换 G1 格6。')
v3['s03']['note']='保留 G1 格3：背景只有舞台、花和蛋糕，没有宾客，不受新规则影响。'
local('s19','local_fixes_v3/s19_G3p7_crop4_up.png','ultrasharp',[v2['s19']['upscaled']],'本地修：原格从下边裁掉 4%（20 px），重新用 UltraSharp 放大到 1080×1920，去掉最下边那点衬衫缝。',win('G3_panels/G3_p7_s19.png'))
cellset('s21','R1',1,'R1_p1_s21.png','ultrasharp',[U('R1','R1_p6_s21alt.png')],'R1 重画：地面是干的（跟 G3 一致），替换 G4 格1。')
cellset('s22','R1',2,'R1_p2_s22.png','lanczos',[U('R1','R1_p4_s22alt.png')],'R1 重画：高机位俯拍，从总裁肩膀后上方往下看，地面干，替换 G4 格2。')
local('s23','local_fixes_v3/s23_G4p3_warm.png','ultrasharp（原放大）+ 调暖色',[v2['s23']['upscaled']],'本地调暖色（gamma 1.06，RGB 增益 1.04/0.99/0.86），让天空从灰蓝变成跟 G3 一样偏暖的阴天。',v2['s23']['upscaled'])
v3['s24']=dict(source='plot_grid_cell',grid='G4',cell=4,panel=win('G4_panels/G4_p4_s24alt.png'),upscaled=U('G4','G4_p4_s24alt.png'),method='lanczos',alternates=[v2['s24']['upscaled']],note='按批复换用 G4 格4：落魄土豆在下雨的泥地里滚、背对镜头、闪回灰色调；原来的空菜园场景图留作备选。',v2_upscaled=v2['s24']['upscaled'])
local('s25','local_fixes_v3/s25_G4p5_warm.png','ultrasharp（原放大）+ 调暖色',[v2['s25']['upscaled']],'本地调暖色（gamma 1.04，RGB 增益 1.03/0.99/0.90），跟 G3 的暖色阴天对上。',v2['s25']['upscaled'])
cellset('s26','R1',3,'R1_p3_s26.png','lanczos',[U('R1','R1_p5_s26alt.png'),U('G4','G4_p9_s26alt.png')],'R1 重画：总裁背对镜头抬手一摆，秘书在后面含泪做「请」，地面干。注意：他身体背对镜头，脸却几乎整个转向镜头（脖子扭得有点不自然）；备选格5 也一样。')
cellset('s34','R1',7,'R1_p7_s34.png','lanczos',[U('R1','R1_p8_s34alt.png')],'R1 重画：咬的是金黄色、起泡的炸薯片，不再像生黄瓜片；绿边很细，放大后才隐约看得到。')
v3['t2']=dict(source='plot_grid_cell',grid='R1',cell=9,panel=win('R1_panels/R1_p9_t2.png'),upscaled=U('R1','R1_p9_t2.png'),method='lanczos',alternates=[v2['t2']['upscaled'],U('G5','G5_p8_t2alt.png')],note='R1 重画：金黄色薯片带明显的绿边，落进炸篮和素色绿袋，没有人物，替换复用的旧场景图（旧图薯片没有绿边）。',v2_upscaled=v2['t2']['upscaled'])
for k in v3:
    if 'from_' in v3[k]: v3[k]['from']=v3[k].pop('from_')
order=list(v2.keys()); assert len(order)==36
missing=[k for k in order if not Path(box(v3[k]['upscaled'])).exists()]
assert not missing, missing
json.dump({k:v3[k] for k in order},open(G/'frame_map_v3.json','w'),ensure_ascii=False,indent=2)
# contact: 6 cols x 6 rows
tw,th,pad,lab=240,427,8,30; cols=6; rows=6
W=cols*tw+(cols+1)*pad; H=rows*(th+lab)+(rows+1)*pad+50
s=Image.new('RGB',(W,H),'white'); d=ImageDraw.Draw(s)
fb=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',20); fs=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',13)
d.text((pad,12),'tudou first frames v3 (frame_map_v3.json), shot order',fill='black',font=fb)
for i,k in enumerate(order):
    r,c=divmod(i,cols); x=pad+c*(tw+pad); y=50+pad+r*(th+lab+pad)
    im=Image.open(box(v3[k]['upscaled'])).convert('RGB'); assert im.size==(1080,1920),(k,im.size)
    s.paste(im.resize((tw,th),Image.LANCZOS),(x,y+lab))
    e=v3[k]; src=e.get('grid') and f"{e['grid']} c{e['cell']}" or ('local fix' if e['source']=='local_fix' else 'scene ref')
    changed=e['upscaled']!=v2[k]['upscaled']
    d.text((x+2,y+4),k,fill='red' if changed else 'black',font=fb); d.text((x+62,y+9),src+(' (new)' if changed else ''),fill='black',font=fs)
s.save(G/'final_firstframes_v3_contact.png'); print('ok', s.size, 'changed:',[k for k in order if v3[k]['upscaled']!=v2[k]['upscaled']])
