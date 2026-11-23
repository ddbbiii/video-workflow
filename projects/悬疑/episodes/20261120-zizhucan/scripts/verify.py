from pathlib import Path
import os,sys,json,subprocess,re,hashlib,math
from PIL import Image,ImageDraw,ImageOps
EP=Path(__file__).resolve().parents[1];ROOT=EP.parents[3];os.environ['PATH']='/Users/mac/bin:'+os.environ['PATH']
V=EP/'video/final/悬疑_你先吃我马上回来_正文_v2.mp4';S=V.with_suffix('.srt');Q=EP/'qa';P=json.loads((EP/'storyboard/SHOT_PLAN.json').read_text())
def save(n,d):(Q/n).write_text(json.dumps(d,ensure_ascii=False,indent=2))
def sheets():
 for start in range(0,len(P['shots']),18):
  group=P['shots'][start:start+18];out=Image.new('RGB',(1440,math.ceil(len(group)/3)*295),(30,34,40));d=ImageDraw.Draw(out)
  for i,s in enumerate(group):
   p=EP/'image/final'/f"{s['id']}.png"
   if not p.exists():continue
   im=ImageOps.fit(Image.open(p),(480,270),method=Image.Resampling.LANCZOS);x=i%3*480;y=i//3*295;out.paste(im,(x,y+25));d.text((x+5,y+5),s['id']+' '+s['scene_id'],fill='white')
  out.save(Q/f'contact-{start//18+1}.jpg',quality=95)
 print('CONTACT_SHEETS_READY',flush=True)
def final():
 subprocess.run([sys.executable,str(ROOT/'shared/workflows/body-only/check_delivery.py'),'--video',str(V),'--srt',str(S),'--json',str(Q/'delivery.json')],check=True)
 stat=Q/'signalstats.txt';log=Q/'decode-scan.log'
 with log.open('w') as f:
  subprocess.run(['ffmpeg','-v','warning','-xerror','-i',str(V),'-map','0:v:0','-vf',f'signalstats,metadata=print:file={stat}','-an','-f','null','-'],stdout=f,stderr=f,check=True)
 text=stat.read_text();frames=[]
 for m in re.finditer(r'frame:(\d+)\s+pts:\S+\s+pts_time:([\d.]+)\n(.*?)(?=frame:|\Z)',text,re.S):
  vals=dict(re.findall(r'lavfi.signalstats.([A-Z]+)=([\d.]+)',m[3]));frames.append(dict(frame=int(m[1]),pts=float(m[2]),min=float(vals['YMIN']),max=float(vals['YMAX']),mean=float(vals['YAVG'])))
 assert len(frames)==P['frames'],(len(frames),P['frames'])
 def intervals(predicate):
  groups=[];start=None
  for i,d in enumerate(frames+[dict(min=100,max=100,mean=100)]):
   if i<len(frames) and predicate(d):
    if start is None:start=i
   elif start is not None:
    if i-start>=24:groups.append(dict(start_frame=start,end_frame_exclusive=i,seconds=(i-start)/24))
    start=None
  return groups
 black=intervals(lambda d:d['mean']<25 and d['max']<40);white=intervals(lambda d:d['mean']>240 and d['min']>230)
 maxerr=max(abs(d['pts']-d['frame']/24) for d in frames);steps=[frames[i+1]['pts']-frames[i]['pts'] for i in range(len(frames)-1)]
 cfr=maxerr<.0006 and min(steps)>.0410 and max(steps)<.0423
 report=dict(decoded_frames=len(frames),expected_frames=P['frames'],full_decode_success=True,pixel_stats='full-resolution luma, every decoded frame',black_intervals_ge_1s=black,white_intervals_ge_1s=white,max_pts_error_s=maxerr,step_min_s=min(steps),step_max_s=max(steps),cfr_uniform=cfr,passed=not black and not white and cfr)
 save('pixel_scan.json',report);assert report['passed'],report
 streams=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(V)]));save('video.json',streams)
 v=streams['streams'][0];assert len(streams['streams'])==1 and v['codec_name']=='h264' and v['pix_fmt']=='yuv420p' and v['width']==1920 and v['height']==1080 and v['avg_frame_rate']=='24/1' and int(v['nb_frames'])==P['frames']
 data=V.read_bytes();assert 0<data.find(b'moov')<data.find(b'mdat')
 intro=list((EP/'image/intro/v2').glob('*.png'));assert len(intro)==2
 for p in intro:
  with Image.open(p) as im:assert im.size==(1920,1080)
 save('final-integrity.json',dict(mp4_sha256=hashlib.sha256(data).hexdigest(),srt_sha256=hashlib.sha256(S.read_bytes()).hexdigest(),faststart=True,duration_s=P['duration'],frames=P['frames'],fps=24,technical_delivery='PASS',visual_review_record='qa/visual-review.md',intro_images=[dict(file=str(p.relative_to(EP)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in intro],intro_separate=True,no_audio_subtitle_streams=True))
 print('FINAL_QA_PASS',flush=True)
if __name__=='__main__':
 if sys.argv[1]=='sheets':sheets()
 else:final()
