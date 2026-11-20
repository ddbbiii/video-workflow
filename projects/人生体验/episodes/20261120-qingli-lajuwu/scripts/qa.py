from pathlib import Path
import hashlib,json,re,subprocess,sys,unicodedata
from produce import EP,ROOT,save
from render import P,OUT

def images():
 import cv2
 import numpy as np
 rows=[];errors=[]
 for s in P['shots']:
  path=EP/'image/final'/f"{s['id']}.png"
  if not path.exists():errors.append([s['id'],'missing']);continue
  meta=json.loads((EP/'logs/requests'/f"{s['id']}.json").read_text());native=EP/meta['file']
  image=cv2.imread(str(path));gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY);ng=cv2.imread(str(native),cv2.IMREAD_GRAYSCALE)
  dims=[image.shape[1],image.shape[0]]
  stats=dict(id=s['id'],dimensions=dims,std_lum=round(float(gray.std()),2),mean_lum=round(float(gray.mean()),2),native_lap_var=round(float(cv2.Laplacian(ng,cv2.CV_64F).var()),2),delivery_lap_var=round(float(cv2.Laplacian(gray,cv2.CV_64F).var()),2),source_sha256=hashlib.sha256(native.read_bytes()).hexdigest(),normalized_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
  if dims!=[1920,1080] or stats['std_lum']<18 or stats['native_lap_var']<60 or stats['delivery_lap_var']<15:errors.append([s['id'],'technical image thresholds',stats])
  if meta['prompt_sha256']!=hashlib.sha256(meta['prompt'].encode()).hexdigest():errors.append([s['id'],'prompt hash'])
  if not meta['metadata'].get('environment_master'):errors.append([s['id'],'missing environment stage'])
  rows.append(stats)
 save(EP/'qa/images.json',dict(shots=len(rows),errors=errors,passed=not errors,metrics=rows));assert not errors,errors
 print('IMAGE_TECHNICAL_QA_PASS',len(rows))

def subtitles():
 subprocess.run([sys.executable,str(ROOT/'shared/workflows/script-qa/lint_narration.py'),str(EP/'story/script-v1-locked.md'),str(EP/'video/timeline.json'),'--json',str(EP/'qa/narration-final.json')],check=True)
 def ts(frame):
  ms=round(frame/30*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000);return f'{h:02}:{m:02}:{s:02},{ms:03}'
 folder=EP/'subtitles';folder.mkdir(exist_ok=True)
 raw=folder/'sentences.srt';raw.write_text('\n'.join(f"{i}\n{ts(s['start_frame'])} --> {ts(s['end_frame'])}\n{s['cue']}\n" for i,s in enumerate(P['shots'],1)))
 # 用户要求原文不改；锁定句存在无标点长分句，按SRT规则允许在词边界拆条并披露。
 subprocess.run([sys.executable,str(ROOT/'shared/workflows/subtitles/split_srt.py'),str(raw),'--out',str(OUT.with_suffix('.srt')),'--cues-json',str(folder/'cues.json'),'--report',str(EP/'qa/split-report.json'),'--allow-word-split'],check=True)
 checked=subprocess.run([sys.executable,str(ROOT/'shared/workflows/subtitles/check_srt.py'),str(OUT.with_suffix('.srt')),'--json'],capture_output=True,text=True,check=True)
 (EP/'qa/srt.json').write_text(checked.stdout);print(checked.stdout,flush=True)
 raw_text=OUT.with_suffix('.srt').read_text();texts=[]
 for block in re.split(r'\n\s*\n',raw_text.strip()):
  lines=block.splitlines();at=next(i for i,x in enumerate(lines) if '-->' in x);texts.extend(lines[at+1:])
 norm=lambda text:''.join(c for c in text if unicodedata.category(c)[0] in 'LN')
 assert norm(''.join(texts))==norm(''.join(s['cue'] for s in P['shots']))
 save(EP/'qa/text-integrity.json',dict(passed=True,locked_paragraphs=76,visible_chars=2597,srt_cues=len(texts),note='估算时间轴，未对真实人声校准；拆条拼接与锁定原文一致。'))

def final():
 subprocess.run([sys.executable,str(ROOT/'shared/workflows/body-only/check_delivery.py'),'--video',str(OUT),'--srt',str(OUT.with_suffix('.srt')),'--json',str(EP/'qa/delivery.json')],check=True)
 stats=EP/'qa/signalstats.txt'
 with (EP/'qa/decode.log').open('w') as log:subprocess.run(['ffmpeg','-v','warning','-xerror','-i',str(OUT),'-map','0:v:0','-vf',f'signalstats,metadata=print:file={stats}','-an','-f','null','-'],stdout=log,stderr=log,check=True)
 frames=[]
 for m in re.finditer(r'frame:(\d+)\s+pts:\S+\s+pts_time:([\d.]+)\n(.*?)(?=frame:|\Z)',stats.read_text(),re.S):
  v=dict(re.findall(r'lavfi.signalstats.([A-Z]+)=([\d.]+)',m[3]));frames.append(dict(index=int(m[1]),pts=float(m[2]),low=float(v['YMIN']),high=float(v['YMAX']),mean=float(v['YAVG'])))
 assert len(frames)==P['frames'],(len(frames),P['frames'])
 def intervals(pred):
  result=[];start=None
  for i in range(len(frames)+1):
   if i<len(frames) and pred(frames[i]):
    if start is None:start=i
   elif start is not None:
    if i-start>=30:result.append(dict(start_frame=start,end_frame=i,seconds=(i-start)/30))
    start=None
  return result
 black=intervals(lambda x:x['mean']<25 and x['high']<40);white=intervals(lambda x:x['mean']>240 and x['low']>230)
 err=max(abs(x['pts']-x['index']/30) for x in frames);steps=[b['pts']-a['pts'] for a,b in zip(frames,frames[1:])];cfr=err<.0006 and min(steps)>.0325 and max(steps)<.0342
 report=dict(decoded_frames=len(frames),expected_frames=P['frames'],full_decode_success=True,pixel_stats='Full resolution every frame luma',black_intervals_ge_1s=black,white_intervals_ge_1s=white,max_pts_error_s=err,step_min_s=min(steps),step_max_s=max(steps),cfr_uniform=cfr,passed=not black and not white and cfr)
 save(EP/'qa/pixel-scan.json',report);assert report['passed']
 probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(OUT)]));save(EP/'qa/ffprobe.json',probe)
 v=probe['streams'][0];assert len(probe['streams'])==1 and v['codec_name']=='h264' and v['pix_fmt']=='yuv420p' and v['width']==1920 and v['height']==1080 and v['avg_frame_rate']=='30/1' and int(v['nb_frames'])==P['frames']
 data=OUT.read_bytes();assert 0<data.find(b'moov')<data.find(b'mdat')
 save(EP/'qa/integrity.json',dict(mp4_sha256=hashlib.sha256(data).hexdigest(),srt_sha256=hashlib.sha256(OUT.with_suffix('.srt').read_bytes()).hexdigest(),duration_s=P['duration_s'],frames=P['frames'],faststart=True,technical_qa='PASS'))
 stats.unlink();print('FINAL_QA_PASS',flush=True)

if __name__=='__main__':
 if sys.argv[1]=='subtitles':subtitles()
 elif sys.argv[1]=='images':images()
 else:final()
