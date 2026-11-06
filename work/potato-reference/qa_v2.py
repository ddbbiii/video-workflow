import subprocess,json
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np
base=Path(r'E:/program/1project/video/projects/unassigned/potato-staircase-test/out/ellipse_v2')
out=base/'qa';out.mkdir(exist_ok=True)
video=base/'potato_ellipse_v2.mp4'
def frame(t):
    b=subprocess.check_output(['ffmpeg','-v','error','-ss',str(t),'-i',str(video),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
    return Image.fromarray(np.frombuffer(b,np.uint8).reshape(1920,1080,3))
def sheet(times,name,detail=False):
    w,h=(200,200) if detail else (180,320)
    cols=6 if detail else 4
    rows=(len(times)+cols-1)//cols
    im=Image.new('RGB',(w*cols,(h+20)*rows),(20,20,20))
    for j,t in enumerate(times):
        f=frame(t)
        if detail:f=f.crop((220,650,860,1290))
        f=f.resize((w,h))
        x,y=(j%cols)*w,(j//cols)*(h+20)
        im.paste(f,(x,y+20));ImageDraw.Draw(im).text((x+4,y+3),f'{t:.3f}s',fill='white')
    im.save(out/name,quality=88)
sheet([0,.5,1,1.4,1.8,2.4,3.4,3.9,4.3,4.9,5.8,7.3],'overview.jpg')
sheet([1.25+k/60 for k in range(24)],'contact_1.jpg',True)
sheet([3.75+k/60 for k in range(24)],'contact_2.jpg',True)
print(out)
