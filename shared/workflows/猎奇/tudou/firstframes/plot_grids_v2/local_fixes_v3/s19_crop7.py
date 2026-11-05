# Step 0 (2026-10-02, approved): s19 crop 7% from bottom of ORIGINAL panel, UltraSharp to 1080x1920. No API calls.
import json, subprocess
from pathlib import Path
from PIL import Image
G=Path('E:/program/1project/video/projects/猎奇/episodes/tudou/image/plot_grids_v2'); O=G/'local_fixes_v3'; KP=Path('/workspace/kepu-pipeline')
p=Image.open(G/'G3_panels/G3_p7_s19.png'); w,h=p.size; c=round(h*0.07)
p.crop((0,0,w,h-c)).save(O/'s19_G3p7_crop7.png')
subprocess.run([str(KP/'.venv-upscale/bin/python'),str(KP/'scripts/upscale_frame.py'),'--in',str(O/'s19_G3p7_crop7.png'),'--out',str(O/'s19_G3p7_crop7_up.png'),'--method','ultrasharp','--size','1080x1920','--fit','crop','--log',str(O/'upscale_log.jsonl')],check=True,cwd=KP)
log=json.load(open(O/'local_fixes_log.json')); log.append(dict(shot='s19',src='G3_panels/G3_p7_s19.png',out='local_fixes_v3/s19_G3p7_crop7_up.png',op=f'crop bottom {c}px of {h} (7%), panel {w}x{h-c}, upscale ultrasharp 1080x1920 fit=crop'))
json.dump(log,open(O/'local_fixes_log.json','w'),ensure_ascii=False,indent=1); print('done',c,h)
