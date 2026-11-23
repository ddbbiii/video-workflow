"""Episode wrapper using repository camera_motion affine engine; no zoompan/I2V/audio."""
from pathlib import Path
import json,sys,importlib.util,subprocess,hashlib,shutil,time,copy
from concurrent.futures import ThreadPoolExecutor
import cv2
from PIL import Image
EP=Path(__file__).resolve().parents[1];ROOT=EP.parents[3]
spec=importlib.util.spec_from_file_location('cm',ROOT/'shared/camera-motion/camera_motion.py');cm=importlib.util.module_from_spec(spec);spec.loader.exec_module(cm)
P=json.loads((EP/'storyboard/SHOT_PLAN-v1.json').read_text());OUT=EP/'video/final/悬疑_如果你还记得这个地方_正文_v1.mp4'
CLIPS=EP/'video/clips';CLIPS.mkdir(exist_ok=True)

def build(available=False):
 shots=[]
 for s in P['shots']:
  path=EP/'image/final'/f"{s['id']}.png"
  if not path.exists():
   if available:continue
   raise FileNotFoundError(path)
  with Image.open(path) as im:w,h=im.size
  vh=min(1,w/(h*(16/9)));vw=vh*h*(16/9)/w
  base=[(1-vw)/2,(1-vh)/2,vw,vh]
  end=[base[0]+.05*vw,base[1]+.05*vh,.9*vw,.9*vh] if s['motion']=='affine_push' else base
  shots.append(dict(id=s['id'],source=str(path),duration_s=s['frames']/24,start_view=base,end_view=end,curve={'type':'ramped_linear','ramp_s':.7},required_regions=[[.12,.12,.76,.76]],cue=s['cue'],fact=s['fact'],frames=s['frames'],start_frame=s['start_frame'],end_frame=s['end_frame'],source_sha256=cm.digest(path),motion=s['motion']))
 plan=dict(schema_version=1,backend='affine',output=dict(width=1920,height=1080,fps=24),transition_s=0,shots=shots)
 path=EP/('video/partial_motion_plan.json' if available else 'video/motion_plan.json');path.write_text(json.dumps(plan,ensure_ascii=False,indent=2))
 (EP/('video/partial_timeline.json' if available else 'video/timeline.json')).write_text(json.dumps(dict(fps=24,frames=P['frames'],duration=P['duration_s'],note='估算时间轴，未对真实人声校准',shots=shots),ensure_ascii=False,indent=2))
 subprocess.run([sys.executable,str(ROOT/'shared/camera-motion/validate_plan.py'),str(path)],check=True)
 cm.load_plan(path)
 return plan

def render(s):
 out=CLIPS/f"{s['id']}.mp4";log=CLIPS/f"{s['id']}.json"
 if out.exists() and log.exists() and json.loads(log.read_text()).get('source_sha256')==s['source_sha256']:return out
 n=s['frames'];start=time.time()
 if s['motion']=='static':
  src=cm.prepare_source(s['source'],s,1920,1080);h,w=src.shape[:2]
  frame=cv2.warpAffine(src,cm.sample_matrix(s['start_view'],w,h,1920,1080),(1920,1080),flags=cv2.INTER_CUBIC|cv2.WARP_INVERSE_MAP,borderMode=cv2.BORDER_REPLICATE)
  png=CLIPS/f"{s['id']}-static.png";Image.fromarray(frame).save(png)
  subprocess.run(['ffmpeg','-v','error','-y','-loop','1','-framerate','24','-i',str(png),'-frames:v',str(n),'-an','-c:v','libx264','-preset','fast','-threads','4','-crf','18','-pix_fmt','yuv420p',str(out)],check=True)
  png.unlink();report={'backend':'affine-static','render_fps':24,'matrix':cm.sample_matrix(s['start_view'],w,h,1920,1080).tolist()}
 else:
  # Float subpixel engine renders movement at 60fps. Exact planned 24fps count enforced on conversion.
  mov=copy.deepcopy(s);mov['frames']=round(s['duration_s']*60);mov['duration_s']=mov['frames']/60;mov['span_s']=(mov['frames']-1)/60
  intermediate=CLIPS/f"{s['id']}-60.mp4"
  mats,report=cm.render_affine(mov,intermediate,dict(width=1920,height=1080,fps=60))
  subprocess.run(['ffmpeg','-v','error','-y','-i',str(intermediate),'-vf','tpad=stop_mode=clone:stop_duration=0.05,fps=24','-frames:v',str(n),'-an','-c:v','libx264','-preset','fast','-threads','4','-crf','18','-pix_fmt','yuv420p',str(out)],check=True)
  report.update(render_fps=60,matrix_start=mats[0],matrix_end=mats[-1]);intermediate.unlink()
 probe=cm.probe(out)['streams'][0];assert int(probe['nb_frames'])==n,(s['id'],probe['nb_frames'],n)
 report.update(id=s['id'],frames=n,duration_s=n/24,source_sha256=s['source_sha256'],video_sha256=cm.digest(out),elapsed_s=round(time.time()-start,2))
 log.write_text(json.dumps(report,ensure_ascii=False,indent=2));print('RENDER',s['id'],n,report['elapsed_s'],flush=True)
 return out

def assemble(plan):
 free=shutil.disk_usage(EP).free
 if free<12*1024**3:raise RuntimeError('disk preflight less than 12GB')
 (EP/'logs/encoding-preflight.json').write_text(json.dumps({'free_bytes':free,'estimated_outputs_bytes':1024**3,'minimum_bytes':12*1024**3,'pass':True},indent=2))
 ls=CLIPS/'concat.txt';ls.write_text(''.join("file '"+str(CLIPS/f"{s['id']}.mp4").replace("'","'\\''")+"'\n" for s in plan['shots']))
 subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(ls),'-vf','eq=saturation=0.96:contrast=1.015,colorbalance=bs=0.008:rs=-0.004','-an','-sn','-c:v','libx264','-preset','medium','-threads','6','-crf','18','-pix_fmt','yuv420p','-r','24','-movflags','+faststart',str(OUT)],check=True)
 probe=cm.probe(OUT);(EP/'qa/final-ffprobe.json').write_text(json.dumps(probe,ensure_ascii=False,indent=2));assert int(probe['streams'][0]['nb_frames'])==P['frames']
 print('FINAL',OUT,flush=True)

if __name__=='__main__':
 partial=len(sys.argv)>1 and sys.argv[1]=='partial'
 plan=build(partial)
 if len(sys.argv)>1 and sys.argv[1]=='plan':sys.exit(0)
 with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(render,plan['shots']))
 if not partial:assemble(plan)
