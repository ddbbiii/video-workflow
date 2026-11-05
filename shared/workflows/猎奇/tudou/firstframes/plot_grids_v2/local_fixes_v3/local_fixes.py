# Free local fixes approved 2026-10-02 00:09: warm grade s23/s25 toward G3 look; s19 bottom crop 4% + re-upscale. No API calls.
import json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image
G=Path('E:/program/1project/video/projects/猎奇/episodes/tudou/image/plot_grids_v2'); O=G/'local_fixes_v3'; KP=Path('/workspace/kepu-pipeline')
def warm(src,dst,gain,gamma=1.0,sat=1.0):
    a=np.asarray(Image.open(src).convert('RGB')).astype(np.float32)/255
    a=a**gamma
    a=a*np.array(gain,np.float32)
    l=(0.299*a[...,0]+0.587*a[...,1]+0.114*a[...,2])[...,None]
    a=l+(a-l)*sat
    Image.fromarray((np.clip(a,0,1)*255+0.5).astype(np.uint8)).save(dst)
log=[]
warm(G/'G4_upscaled/G4_p3_s23.png',O/'s23_G4p3_warm.png',(1.04,0.99,0.86),gamma=1.06,sat=1.04); log.append(dict(shot='s23',src='G4_upscaled/G4_p3_s23.png',out='local_fixes_v3/s23_G4p3_warm.png',op='warm grade: gamma 1.06, RGB gain 1.04/0.99/0.86, sat 1.04'))
warm(G/'G4_upscaled/G4_p5_s25.png',O/'s25_G4p5_warm.png',(1.03,0.99,0.90),gamma=1.04,sat=1.02); log.append(dict(shot='s25',src='G4_upscaled/G4_p5_s25.png',out='local_fixes_v3/s25_G4p5_warm.png',op='warm grade: gamma 1.04, RGB gain 1.03/0.99/0.90, sat 1.02'))
# s19: crop 4% from bottom of the ORIGINAL panel, then re-upscale (UltraSharp, single-face close-up) to 1080x1920
p=Image.open(G/'G3_panels/G3_p7_s19.png'); w,h=p.size; c=round(h*0.04)
p.crop((0,0,w,h-c)).save(O/'s19_G3p7_crop4.png')
subprocess.run([str(KP/'.venv-upscale/bin/python'),str(KP/'scripts/upscale_frame.py'),'--in',str(O/'s19_G3p7_crop4.png'),'--out',str(O/'s19_G3p7_crop4_up.png'),'--method','ultrasharp','--size','1080x1920','--fit','crop','--log',str(O/'upscale_log.jsonl')],check=True,cwd=KP)
log.append(dict(shot='s19',src='G3_panels/G3_p7_s19.png',out='local_fixes_v3/s19_G3p7_crop4_up.png',op=f'crop bottom {c}px of {h} (4%), panel {w}x{h-c}, upscale ultrasharp 1080x1920 fit=crop'))
json.dump(log,open(O/'local_fixes_log.json','w'),ensure_ascii=False,indent=1); print(json.dumps(log,ensure_ascii=False))
