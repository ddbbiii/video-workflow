import subprocess
from pathlib import Path
root=Path(r'E:/program/1project/video/projects/小球/episodes/potato-staircase-test')
for name,t in [('first',1.2),('middle',7.8),('late',17.2)]:
 out=root/'qa/reference-analysis'/f'continuous_{name}_{t:.1f}s.jpg'
 vf="scale=180:320,drawtext=fontfile='C\\:/Windows/Fonts/consola.ttf':text='%{n}':x=5:y=5:fontsize=16:fontcolor=yellow:box=1:boxcolor=black@0.7,tile=6x4"
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss',str(t),'-i',str(root/'refs/douyin_original.mp4'),'-vf',vf,'-frames:v','1',str(out)],check=True)
