"""共享浮点运镜引擎；60fps逐帧渲染后按统一时间线转换30fps。"""
from pathlib import Path
import copy,importlib.util,json,shutil,subprocess,sys,time
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from produce import EP,ROOT,save
spec=importlib.util.spec_from_file_location('cm',ROOT/'shared/camera-motion/camera_motion.py');cm=importlib.util.module_from_spec(spec);spec.loader.exec_module(cm)
P=json.loads((EP/'storyboard/SHOT_PLAN.json').read_text())
OUT=EP/'video/final/人生体验_清理垃圾屋_正文_v2.mp4'
CLIPS=EP/'video/clips';CLIPS.mkdir(exist_ok=True)

def plan(available=False):
 shots=[]
 for row in P['shots']:
  src=EP/'image/final'/f"{row['id']}.png"
  if not src.exists():
   if available:continue
   raise FileNotFoundError(src)
  full=[0.,0.,1.,1.];closer=[.045,.045,.91,.91]
  start,end=(closer,full) if row['motion']=='affine_pull' else (full,closer)
  if row['motion']=='static':start=end=full
  s=copy.deepcopy(row);s.update(source=str(src),source_sha256=cm.digest(src),start_view=start,end_view=end,curve=dict(type='ramped_linear',ramp_s=.6),required_regions=[[.06,.06,.88,.88]])
  shots.append(s)
 p=dict(schema_version=1,backend='affine',output=dict(width=1920,height=1080,fps=30),transition_s=0,shots=shots)
 path=EP/'video'/('partial_motion_plan.json' if available else 'motion_plan.json');save(path,p)
 subprocess.run([sys.executable,str(ROOT/'shared/camera-motion/validate_plan.py'),str(path)],check=True)
 p=cm.load_plan(path)
 if not available:save(EP/'video/timeline.json',dict(fps=30,frames=P['frames'],duration_s=P['duration_s'],note=P['note'],shots=p['shots']))
 return p

def render(s):
 out=CLIPS/f"{s['id']}.mp4";report_path=CLIPS/f"{s['id']}.json"
 if out.exists() and report_path.exists():
  old=json.loads(report_path.read_text())
  if old.get('source_sha256')==s['source_sha256'] and old.get('frames')==s['frames']:return out
 start=time.time();n=s['frames']
 if s['motion']=='static':
  subprocess.run(['ffmpeg','-v','error','-y','-loop','1','-framerate','30','-i',s['source'],'-frames:v',str(n),'-an','-sn','-c:v','libx264','-preset','fast','-threads','3','-crf','18','-pix_fmt','yuv420p',str(out)],check=True)
  report=dict(backend='static',render_fps=30)
 else:
  mov=copy.deepcopy(s);mov.update(frames=n*2,span_s=(n*2-1)/60,duration_s=n/30)
  temp=CLIPS/f"{s['id']}-60.mp4";mats,report=cm.render_affine(mov,temp,dict(width=1920,height=1080,fps=60))
  subprocess.run(['ffmpeg','-v','error','-y','-i',str(temp),'-vf','fps=30','-frames:v',str(n),'-an','-sn','-c:v','libx264','-preset','fast','-threads','3','-crf','18','-pix_fmt','yuv420p',str(out)],check=True)
  report.update(render_fps=60,matrix_start=mats[0],matrix_end=mats[-1]);temp.unlink()
 v=cm.probe(out)['streams'][0];assert int(v['nb_frames'])==n
 report.update(id=s['id'],frames=n,source_sha256=s['source_sha256'],video_sha256=cm.digest(out),elapsed_s=round(time.time()-start,1));save(report_path,report);print('RENDER',s['id'],report['elapsed_s'],flush=True);return out

def assemble(p):
 free=shutil.disk_usage(EP).free;minimum=12*1024**3
 save(EP/'logs/encoding-preflight.json',dict(free_bytes=free,estimated_outputs_bytes=1024**3,required_bytes=minimum,passed=free>=minimum));assert free>=minimum
 ls=CLIPS/'concat.txt';ls.write_text(''.join("file '"+str(CLIPS/f"{s['id']}.mp4")+"'\n" for s in p['shots']))
 subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(ls),'-map','0:v:0','-c:v','copy','-an','-sn','-movflags','+faststart',str(OUT)],check=True)
 probe=cm.probe(OUT);save(EP/'qa/ffprobe.json',probe);assert int(probe['streams'][0]['nb_frames'])==P['frames'];print('FINAL',OUT,flush=True)

if __name__=='__main__':
 partial=len(sys.argv)>1 and sys.argv[1]=='partial';p=plan(partial)
 with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(render,p['shots']))
 if not partial:assemble(p)
