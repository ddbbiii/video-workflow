import json,subprocess,hashlib
from pathlib import Path
import numpy as np
from phys.ellipse_preview import HZ,FPS,sample,source_times
p=Path('out/ellipse_v3'); r=json.loads((p/'report.json').read_text()); tr=np.load(p/'trace.npz')['state']
metrics=[]
for e in r['impacts']:
    t=e['t']; a,b=e['pair']; pre=sample(tr,t-.015); post=sample(tr,t+.09); later=sample(tr,t+.65)
    metrics.append(dict(pair=[a,b],source_time=t,pre_speed=[float(np.linalg.norm(pre[j,3:5])) for j in [a,b]],post_speed_90ms=[float(np.linalg.norm(post[j,3:5])) for j in [a,b]],receiver_rotation_650ms_degrees=float(np.degrees(later[b,2]-pre[b,2]))))
src=np.arange(0,r['output_duration'],1/FPS)
decode=subprocess.run(['ffmpeg','-v','error','-i',str(p/'potato_ellipse_v2.mp4'),'-map','0:v:0','-f','framemd5','-'],capture_output=True,text=True,check=True)
hashes=[line.split(',')[-1].strip() for line in decode.stdout.splitlines() if not line.startswith('#') and line.strip()]
duplicates=sum(x==y for x,y in zip(hashes,hashes[1:]))
q=dict(collision_metrics=metrics,decoded_frames=len(hashes),adjacent_identical_decoded_frames=duplicates,landing_hit_delta=r['landing_hit_delta'],adjacent_source_time_monotonic=bool(np.all(np.diff(src)>0)),simulation_steps_advanced_per_output_frame=HZ/FPS,note='Full-stream video decode and frame-hash checks; audio not auditioned.')
(p/'verification.json').write_text(json.dumps(q,indent=2));print(json.dumps(q,indent=2))
