from pathlib import Path
import os,sys,json,math,hashlib,re,subprocess,tempfile,concurrent.futures,shutil,inspect
os.environ['PATH']='/Users/mac/bin:'+os.environ['PATH']
sys.path.insert(0,'/tmp/zizhucan-python-deps')
import cv2,numpy as np
from PIL import Image,ImageOps,ImageDraw
cv2.setNumThreads(1)
EP=Path(__file__).resolve().parents[1];ROOT=EP.parents[3]
sys.path.insert(0,str(ROOT/'shared/camera-motion'))
import camera_motion as cm
P=json.loads((EP/'storyboard/SHOT_PLAN.json').read_text());W,H=1920,1080
FINAL=EP/'video/final/悬疑_你先吃我马上回来_正文_v2.mp4'
def save(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2))
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fit(p):return ImageOps.fit(Image.open(p).convert('RGB'),(W,H),method=Image.Resampling.LANCZOS)

def plan(available=False):
 out={'schema_version':1,'backend':'affine','output':{'width':W,'height':H,'fps':60},'transition_s':0,'shots':[]}
 for i,s in enumerate(P['shots']):
  src=EP/'image/final'/f"{s['id']}.png"
  if available and not src.exists():continue
  with Image.open(src) as im:ratio=im.width/im.height
  st=[0,0,1,1];en=[0,0,1,1]
  if s['motion']=='affine':
   if i%3==0:en=[.044,.044,.912,.912]
   elif i%3==1:st=[.044,.044,.912,.912]
   else:st=[.02,.05,.9,.9];en=[.08,.05,.9,.9]
  for v in [st,en]:
   h=v[2]*ratio/(W/H);v[1]+=(v[3]-h)/2;v[3]=h
  n=math.ceil(s['frames']/24*60)
  out['shots'].append(dict(id=s['id'],source=str(src),duration_s=n/60,frames=n,span_s=(n-1)/60,start_view=st,end_view=en,curve={'type':'ramped_linear','ramp_s':min(.6,(n-1)/60/4)},required_regions=[[.14,.14,.72,.72]],delivery_frames=s['frames'],timeline_start_frame=s['start_frame'],motion=s['motion']))
 save(EP/'storyboard/motion-plan.json',out)
 return out

def render_one(s):
 dest=EP/'video/clips'/f"{s['id']}.mp4";side=dest.with_suffix('.json')
 fingerprint=hashlib.sha256((json.dumps(s,sort_keys=True)+digest(s['source'])+digest(cm.__file__)+inspect.getsource(render_one)).encode()).hexdigest()
 if dest.exists() and side.exists() and json.loads(side.read_text()).get('fingerprint')==fingerprint:return s['id']+' CACHED'
 print('RENDER_START',s['id'],flush=True)
 source=cm.prepare_source(s['source'],s,W,H);sh,sw=source.shape[:2]
 part=dest.with_suffix('.partial.mp4');tr=[]
 args=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r','60','-i','-','-vf','fps=24','-frames:v',str(s['delivery_frames']),'-an','-c:v','libx264','-preset','fast','-threads','2','-crf','16','-pix_fmt','yuv420p','-movflags','+faststart',str(part)]
 static=s['start_view']==s['end_view'];fixed=None
 with tempfile.TemporaryFile() as log:
  proc=subprocess.Popen(args,stdin=subprocess.PIPE,stderr=log)
  try:
   for i in range(s['frames']):
    mat=cm.sample_matrix(cm.view_at(s,i),sw,sh,W,H)
    if static:
     if fixed is None:fixed=cv2.warpAffine(source,mat,(W,H),flags=cv2.INTER_CUBIC|cv2.WARP_INVERSE_MAP,borderMode=cv2.BORDER_REPLICATE).tobytes()
     data=fixed
    else:data=cv2.warpAffine(source,mat,(W,H),flags=cv2.INTER_CUBIC|cv2.WARP_INVERSE_MAP,borderMode=cv2.BORDER_REPLICATE).tobytes()
    proc.stdin.write(data)
    # Trajectory kept at final 24Hz to avoid redundant huge logs.
    if i%5==0:tr.append({'frame60':i,'matrix':mat.tolist()})
   proc.stdin.close();rc=proc.wait()
  except Exception:
   proc.kill();proc.wait();log.seek(0);print(log.read().decode()[-1500:],flush=True);raise
  if rc:
   log.seek(0);raise RuntimeError(log.read().decode())
 part.replace(dest)
 info=cm.probe(dest);v=info['streams'][0]
 assert int(v['nb_frames'])==s['delivery_frames'],(s['id'],v['nb_frames'],s['delivery_frames'])
 save(side,dict(id=s['id'],fingerprint=fingerprint,sha256=digest(dest),source_sha256=digest(s['source']),frames=s['delivery_frames'],native_sample_fps=60,delivery_fps=24,source_dimensions=[sw,sh],trajectory_sample=tr))
 return s['id']+' COMPLETE'

def render(samples=False,available=False):
 out=plan(available);free=shutil.disk_usage(EP).free
 assert free>14*1024**3,'Disk preflight requires14GiB'
 save(EP/'logs/render-preflight.json',dict(free_bytes=free,required_bytes=14*1024**3,passed=True))
 subprocess.run([sys.executable,str(ROOT/'shared/camera-motion/validate_plan.py'),str(EP/'storyboard/motion-plan.json')],check=True)
 cm.load_plan(EP/'storyboard/motion-plan.json')
 rows=out['shots']
 if samples:rows=[s for s in rows if s['id'] in ['S06','S19','S35','S44']]
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  for result in pool.map(render_one,rows):print(result,flush=True)
 if samples or available:return
 concat=EP/'logs/concat.txt';concat.write_text('\n'.join("file '"+str(EP/'video/clips'/f"{s['id']}.mp4")+"'" for s in P['shots']))
 subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(concat),'-map','0:v:0','-c:v','copy','-an','-frames:v',str(P['frames']),'-movflags','+faststart',str(FINAL)],check=True)
 print('FINAL_VIDEO',str(FINAL),flush=True)

def srt():
 sys.path.insert(0,str(ROOT/'shared/workflows/subtitles'))
 from split_srt import fmt_ts,read_srt,normalize,visible_len
 subprocess.run([sys.executable,str(ROOT/'shared/workflows/script-qa/lint_narration.py'),str(EP/'story/script.md'),str(EP/'storyboard/SHOT_PLAN.json'),'--json',str(EP/'qa/narration-lint-final.json')],check=True)
 cues=[dict(id=s['id'],start=s['start'],end=s['end'],cue=s['cue'],start_frame=s['start_frame'],frames=s['frames']) for s in P['shots']]
 save(EP/'video/timeline.json',dict(fps=24,frames=P['frames'],duration=P['duration'],shots=cues,estimated=True,note='估算时间轴，未对真实人声校准'))
 sentence=EP/'video/srt/sentences.srt';sentence.write_text('\n\n'.join(f"{i+1}\n{fmt_ts(c['start'])} --> {fmt_ts(c['end'])}\n{c['cue']}" for i,c in enumerate(cues))+'\n')
 dest=FINAL.with_suffix('.srt')
 subprocess.run([sys.executable,str(ROOT/'shared/workflows/subtitles/split_srt.py'),str(sentence),'--out',str(dest),'--cues-json',str(EP/'video/srt/cues.json'),'--report',str(EP/'qa/srt-split.json')],check=True)
 r=subprocess.run([sys.executable,str(ROOT/'shared/workflows/subtitles/check_srt.py'),str(dest),'--json'],capture_output=True,text=True);(EP/'qa/srt-check.json').write_text(r.stdout);assert r.returncode==0,r.stdout+r.stderr
 blocks=read_srt(dest);assert normalize(''.join(s['cue'] for s in P['shots']))==normalize(''.join(c['text'] for c in blocks))
 report=dict(shot_cues=len(cues),locked_subtitle_cues=len(blocks),delivered_cues=len(blocks),max_chars=max(visible_len(c['text']) for c in blocks),text_exact_match=True,first_start=blocks[0]['start'],last_end=blocks[-1]['end'],video_duration=P['duration'],estimated=True)
 save(EP/'qa/srt-text.json',report);(EP/'qa/srt_qa.md').write_text('# SRT验收\n\n'+json.dumps(report,ensure_ascii=False,indent=2)+'\n\n估算时间轴，未对真实人声校准。check_srt.py PASS。\n')
 print('SRT_READY',len(blocks),flush=True)

if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='render':render()
 elif mode=='partial':render(available=True)
 elif mode=='samples':render(True)
 elif mode=='srt':srt()
 elif mode=='plan':plan()
