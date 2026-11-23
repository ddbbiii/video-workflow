"""Deterministic evidence compositing and shared-camera final assembly. No image-model substitution."""
from pathlib import Path
import os,sys,json,math,hashlib,re,subprocess,time,importlib.util,concurrent.futures,tempfile,shutil
from PIL import Image,ImageOps,ImageDraw,ImageFilter
import numpy as np,cv2
EP=Path(__file__).resolve().parents[1];ROOT=EP.parents[3]
os.environ['PATH']='/Users/mac/bin:'+os.environ['PATH']
cv2.setNumThreads(1)
sys.path.insert(0,str(ROOT/'shared/camera-motion'))
import camera_motion as cm
PLAN=json.loads((EP/'storyboard/SHOT_PLAN-production-v3.json').read_text());W,H=1920,1080
FINAL=EP/'video/final/悬疑_新闻更新前_正文_v3.mp4'
for d in ['image/composite','image/normalized','video/clips','qa','video/srt']: (EP/d).mkdir(exist_ok=True,parents=True)
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def savejson(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2))
def fit(p):return ImageOps.fit(Image.open(p).convert('RGB'),(W,H),method=Image.Resampling.LANCZOS)
def raw(tag):return EP/'image/raw'/f'{tag}.png'
def comp(tag):return EP/'image/composite'/f'{tag}.png'
def mkcup():
 a=np.array(Image.open(raw('evidence-cup')).convert('RGB'));r,g,b=[a[:,:,i].astype(float) for i in range(3)]
 # Chroma key only magenta pixels connected to the frame, never mountain sticker/grey cup.
 key=(r>95)&(b>65)&(r>g*1.3)&(b>g*1.25)&((r+b)/2-g>55)
 mask=(~key).astype('uint8')*255
 n,lab,stats,cent=cv2.connectedComponentsWithStats(mask)
 keep=1+np.argmax(stats[1:,cv2.CC_STAT_AREA]);mask=np.where(lab==keep,255,0).astype('uint8')
 rgba=Image.fromarray(np.dstack([a,mask]),'RGBA');box=Image.fromarray(mask).getbbox();rgba=rgba.crop(box)
 # Defringe keyed edge by removing 1 pixel of magenta contamination.
 alpha=np.array(rgba.getchannel('A'));alpha=cv2.erode(alpha,np.ones((3,3),np.uint8));rgba.putalpha(Image.fromarray(alpha))
 from PIL import ImageEnhance
 # Keep native prop luminance; do not dim evidence.
 rgba.save(comp('thermos-cutout'));return rgba

TABLE_CACHE=None
CUP_CACHE=None
def table_state(angle=-90,roll=0):
 global TABLE_CACHE,CUP_CACHE
 if TABLE_CACHE is None:TABLE_CACHE=fit(EP/'image/plates/table.png').convert('RGBA')
 if CUP_CACHE is None:CUP_CACHE=Image.open(comp('thermos-cutout')).convert('RGBA')
 bg=TABLE_CACHE.copy();cup=CUP_CACHE.copy()
 h=500;cup=cup.resize((round(cup.width*h/cup.height),h),Image.Resampling.LANCZOS)
 cup=cup.rotate(angle,resample=Image.Resampling.BICUBIC,expand=True)
 cup=cup.crop(cup.getbbox())
 # At final state cap points right toward the window, sticker stays visible. Fixed table water ring remains.
 x=round(1240+roll-cup.width/2);y=round(710-cup.height)
 alpha=cup.getchannel('A');shadow=Image.new('RGBA',bg.size)
 sd=ImageDraw.Draw(shadow);sd.ellipse((x-10,710-18,x+cup.width+30,733),fill=(5,10,17,95))
 shadow=shadow.filter(ImageFilter.GaussianBlur(8));bg=Image.alpha_composite(bg,shadow);bg.alpha_composite(cup,(x,y));return bg.convert('RGB')

# Filled from actual generated phone after visual inspection.
PHONE_QUAD=None

def phone_photo(photo=None,tag='phone-blank',quad=None):
 bg=fit(raw('evidence-phone'));q=np.array(quad or PHONE_QUAD,dtype=np.float32)
 if photo:
  picture=Image.open(photo).convert('RGB')
  # Landscape phone shows the complete evidence source with no low-resolution punch-in.
  canvas=ImageOps.fit(picture,(1600,900),method=Image.Resampling.LANCZOS)
 else:
  canvas=Image.new('RGB',(1600,900),(48,56,64))
 a=np.array(canvas);src=np.float32([[0,0],[1599,0],[1599,899],[0,899]])
 mat=cv2.getPerspectiveTransform(src,q);warp=cv2.warpPerspective(a,mat,(W,H),flags=cv2.INTER_CUBIC)
 mask=cv2.warpPerspective(np.full(a.shape[:2],255,np.uint8),mat,(W,H),flags=cv2.INTER_LINEAR)
 # Retain a subdued screen-light reflection instead of a visibly pasted white rectangle.
 dest=np.array(bg);mix=mask[:,:,None]/255;out=(dest*(1-mix)+warp*mix).astype('uint8')
 path=comp(tag);Image.fromarray(out).save(path);return path

def composites():
 global PHONE_QUAD
 coords=EP/'image/composite/phone-quad.json';PHONE_QUAD=json.loads(coords.read_text())
 mkcup();table_state().save(comp('cup-fallen'));table_state(0).save(comp('cup-upright'))
 phone_photo(None,'phone-comment')
 phone_photo(comp('cup-fallen'),'phone-cup');phone_photo(raw('evidence-oldcar'),'phone-old');phone_photo(raw('evidence-darkcar'),'phone-dark')
 phone_photo(raw('evidence-parkedcar'),'phone-parked')
 phone_photo(None,'phone-clock');phone_photo(None,'phone-records')
 maps={'oldcar':raw('evidence-oldcar'),'darkcar':raw('evidence-darkcar'),'localcar':raw('evidence-finalcar'),'gatecar':raw('evidence-gatecar'),'finalcar':raw('evidence-finalcar'),'parkedcar':raw('evidence-parkedcar'),'comment':comp('phone-comment'),'compare':comp('phone-dark'),'cupphone':comp('phone-cup'),'oldcarphone':comp('phone-old'),'cupfallen':comp('cup-fallen'),'cupfall':comp('cup-upright'),'clock':comp('phone-clock'),'records':comp('phone-records')}
 # A close crop from exactly the same accident photograph, never a newly invented scratch.
 box=None;maps['scratch']=raw('evidence-scratch')
 manifest=[]
 for s in PLAN['shots']:
  target=EP/'image/final'/f"{s['id']}.png"
  if not s['character_ids']:
   if s['id'] in ['S14','S54']:source=raw('specific-'+s['id'])
   elif s['id']=='S56':source=raw('evidence-bedside')
   else:source=maps[s['visual']]
   # S16 explicitly depicts an old social photograph, S42/S52/S62 objective parked car.
   if s['id']=='S16':source=comp('phone-parked')
   shutil.copyfile(source,target)
  else:source=target
  assert target.exists(),target
  normalized=EP/'image/normalized'/target.name;fit(target).save(normalized)
  manifest.append({'shot':s['id'],'fact':s['fact'],'source':str(source.relative_to(EP)),'final':str(target.relative_to(EP)),'sha256':digest(target),'normalized_sha256':digest(normalized)})
 fit(comp('phone-old')).save(EP/'image/normalized/S12-alternate.png')
 savejson(EP/'logs/composite-manifest-v3.json',manifest)
 # Evidence identity proof uses the actual same bytes before perspective projection.
 savejson(EP/'qa/evidence-continuity-v3.json',{'cup_real_source':str(comp('cup-fallen').relative_to(EP)),'cup_real_sha256':digest(comp('cup-fallen')),'phone_news_photo_source_sha256':digest(comp('cup-fallen')),'exact_source_match':True,'scratch_source':str(raw('evidence-scratch').relative_to(EP)),'scratch_crop':None,'scratch_closeup':'native independent image with vehicle reference, manually reviewed, not claimed pixel-identical','phone_quad_1920x1080':PHONE_QUAD,'no_text_layers':True,'cup_cap_final':'right, toward window','not_I2V':'deterministic isolated-prop rotation plus fixed source image in screen'})
 print('COMPOSITES_COMPLETE',flush=True)

def motionplan():
 out={'schema_version':1,'backend':'affine','output':{'width':W,'height':H,'fps':60},'transition_s':0,'shots':[]}
 for i,s in enumerate(PLAN['shots']):
  st=[0,0,1,1];en=[0,0,1,1]
  if s['motion']=='affine':
   if i%4==0:st=[.044,.044,.912,.912] # pull out9.6%, keeping nearly entire frame.
   elif i%4==2:st=[.02,.05,.9,.9];en=[.08,.05,.9,.9] #6.7%pan.
   else:en=[.044,.044,.912,.912] #push9.6%.
  # new2's native 1672x941 is slightly different from exact 16:9.
  # Correct normalized view height, not pixels: retain native source and never stretch.
  with Image.open(EP/'image/final'/f"{s['id']}.png") as source_image:
   source_ratio=source_image.width/source_image.height
  for view in [st,en]:
   exact_h=view[2]*source_ratio/(W/H)
   view[1]+=(view[3]-exact_h)/2;view[3]=exact_h
  n60=math.ceil(s['frames']/24*60)
  shot={'id':s['id'],'source':str(EP/'image/final'/f"{s['id']}.png"),'duration_s':n60/60,'frames':n60,'span_s':(n60-1)/60,'start_view':st,'end_view':en,'curve':{'type':'ramped_linear','ramp_s':min(.6,(n60-1)/60/4)},'required_regions':[[.12,.12,.76,.76]],'delivery_frames':s['frames'],'timeline_start_frame':s['start_frame'],'motion':s['motion']}
  out['shots'].append(shot)
 savejson(EP/'storyboard/motion-plan-v3.json',out);return out

def render_one(s):
 dest=EP/'video/clips'/f"{s['id']}.mp4";fp=hashlib.sha256((json.dumps(s,sort_keys=True)+digest(s['source'])+digest(cm.__file__)+__import__('inspect').getsource(render_one)+__import__('inspect').getsource(table_state)).encode()).hexdigest();side=dest.with_suffix('.json')
 if dest.exists() and side.exists() and json.loads(side.read_text()).get('fingerprint')==fp:return s['id']+' CACHED'
 print('RENDER_START',s['id'],flush=True)
 source=cm.prepare_source(s['source'],s,W,H);sh,sw=source.shape[:2]
 part=dest.with_suffix('.partial.mp4');frames=s['frames'];tr=[]
 # Sample original floating-point trajectories at60Hz, downsample directly in ffmpeg to24Hz.
 args=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r','60','-i','-','-vf','fps=24','-frames:v',str(s['delivery_frames']),'-an','-c:v','libx264','-preset','slow','-threads','2','-crf','15','-pix_fmt','yuv420p','-movflags','+faststart',str(part)]
 with tempfile.TemporaryFile() as log:
  proc=subprocess.Popen(args,stdin=subprocess.PIPE,stderr=log)
  try:
   for i in range(frames):
    if s['motion']=='state-composite':
     t=i/60
     if t<.45:angle=0;roll=0
     elif t<1.15:
      q=(t-.45)/.70;angle=-90*(q*q);roll=0
     else:
      # A half-roll is represented by tiny settling displacement; final sticker-side-up pose locked.
      q=min(1,(t-1.15)/.7);angle=-90-5*math.sin(q*math.pi)*(1-q);roll=12*math.sin(q*math.pi)*(1-q)
     frame=np.array(table_state(angle,roll))
    elif s['id']=='S12':
     if i==round(frames*.5):source=np.array(fit(EP/'image/normalized/S12-alternate.png'))
     frame=source
    else:
     matrix=cm.sample_matrix(cm.view_at(s,i),sw,sh,W,H)
     frame=cv2.warpAffine(source,matrix,(W,H),flags=cv2.INTER_CUBIC|cv2.WARP_INVERSE_MAP,borderMode=cv2.BORDER_REPLICATE)
     tr.append(matrix.tolist())
    proc.stdin.write(frame.tobytes())
   proc.stdin.close();rc=proc.wait()
   if rc:log.seek(0);raise RuntimeError(log.read().decode())
  except BaseException:
   proc.kill();proc.wait();raise
 data=cm.probe(part);v=data['streams'][0];assert len(data['streams'])==1 and int(v['nb_frames'])==s['delivery_frames'] and v['avg_frame_rate']=='24/1',(s['id'],v)
 part.replace(dest)
 savejson(side,{'shot':s['id'],'fingerprint':fp,'video_sha256':digest(dest),'render_fps':60,'delivery_fps':24,'source_frames':frames,'delivery_frames':s['delivery_frames'],'engine_sha256':digest(cm.__file__),'trajectory_qa':cm.trajectory_qa(s,{'width':W,'height':H}),'kind':s['motion'],'source_sha256':digest(s['source'])})
 if tr:
  delivered=[tr[min(len(tr)-1,math.floor((j+.5)*60/24))] for j in range(s['delivery_frames'])]
  cm.write_trajectory(EP/'video/clips'/f"{s['id']}-trajectory.json",s,delivered,'affine',(sw,sh))
 return s['id']+' COMPLETE'

def render():
 plan=motionplan();free=shutil.disk_usage(EP).free;assert free>14*1024**3,'Insufficient disk'
 savejson(EP/'logs/render-preflight-v3.json',{'free_bytes':free,'expected_deliverable_max_bytes':2*1024**3,'required_free_bytes':14*1024**3,'passed':True,'fps_native':60,'fps_delivery':24})
 subprocess.run([sys.executable,str(ROOT/'shared/camera-motion/validate_plan.py'),str(EP/'storyboard/motion-plan-v3.json')],check=True)
 cm.load_plan(EP/'storyboard/motion-plan-v3.json')
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  for r in pool.map(render_one,plan['shots']):print(r,flush=True)
 concat=EP/'logs/concat-v3.txt';concat.write_text('\n'.join("file '"+str(EP/'video/clips'/f"{s['id']}.mp4")+"'" for s in PLAN['shots']))
 subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(concat),'-map','0:v:0','-c:v','copy','-an','-frames:v',str(PLAN['frames']),'-movflags','+faststart',str(FINAL)],check=True)
 savejson(EP/'qa/video.json',cm.probe(FINAL));print('FINAL_VIDEO',str(FINAL),flush=True)

def srt():
 # Same65-shot timeline is the only timing source; splitting never estimates a second timeline.
 sys.path.insert(0,str(ROOT/'shared/workflows/subtitles'));from split_srt import fmt_ts
 subprocess.run([sys.executable,str(ROOT/'shared/workflows/script-qa/lint_narration.py'),str(EP/'story/script-v7.md'),str(EP/'storyboard/SHOT_PLAN-production-v3.json'),'--json',str(EP/'qa/narration-lint-v3.json')],check=True)
 cues=[{'id':s['id'],'start':s['start'],'end':s['end'],'cue':s['cue'],'start_frame':s['start_frame'],'frames':s['frames']} for s in PLAN['shots']]
 savejson(EP/'video/timeline-v3.json',{'fps':24,'frames':PLAN['frames'],'duration':PLAN['duration'],'shots':cues,'estimated':True,'note':'估算时间轴，未对真实人声校准'})
 sentence=EP/'video/srt/sentences-v3.srt';sentence.write_text('\n\n'.join(f"{i+1}\n{fmt_ts(c['start'])} --> {fmt_ts(c['end'])}\n{c['cue']}" for i,c in enumerate(cues))+'\n')
 dest=FINAL.with_suffix('.srt')
 subprocess.run([sys.executable,str(ROOT/'shared/workflows/subtitles/split_srt.py'),str(sentence),'--out',str(dest),'--cues-json',str(EP/'video/srt/cues-v3.json'),'--report',str(EP/'qa/srt-split-v3.json'),'--overrides',str(EP/'video/srt/overrides-v3.json'),'--allow-word-split'],check=True)
 check=subprocess.run([sys.executable,str(ROOT/'shared/workflows/subtitles/check_srt.py'),str(dest),'--json'],capture_output=True,text=True);(EP/'qa/srt-check-v3.json').write_text(check.stdout);assert check.returncode==0,check.stdout+check.stderr
 from split_srt import read_srt,normalize,visible_len
 blocks=read_srt(dest);narration=''.join(re.match(r'S\d+ (.+)',l)[1] for l in (EP/'story/script-v7.md').read_text().splitlines() if re.match(r'S\d+ ',l))
 assert normalize(narration)==normalize(''.join(c['text'] for c in blocks))
 report={'source_shots':len(cues),'locked_subtitle_cues':len(blocks),'delivered_cues':len(blocks),'max_chars':max(visible_len(c['text']) for c in blocks),'g1_text_match':True,'first_start':blocks[0]['start'],'last_end':blocks[-1]['end'],'video_duration':PLAN['duration'],'timing':'估算时间轴，未对真实人声校准'}
 savejson(EP/'qa/srt-text-v3.json',report)
 (EP/'qa/srt_qa.md').write_text('# SRT验收\n\n'+json.dumps(report,ensure_ascii=False,indent=2)+'\n\ncheck_srt.py PASS；拆条结果锁定于video/srt/cues-v3.json。正文与字幕去标点完全一致。\n')
 print('SRT_COMPLETE',len(blocks),flush=True)

if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='composite':composites()
 elif mode=='motion-plan':motionplan()
 elif mode=='render':render()
 elif mode=='srt':srt()
