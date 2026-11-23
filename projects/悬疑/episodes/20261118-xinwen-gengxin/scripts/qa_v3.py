from pathlib import Path
import os,sys,json,subprocess,re,hashlib,math
from PIL import Image,ImageDraw,ImageOps
EP=Path(__file__).resolve().parents[1];ROOT=EP.parents[3];os.environ['PATH']='/Users/mac/bin:'+os.environ['PATH']
V=EP/'video/final/悬疑_新闻更新前_正文_v3.mp4';S=V.with_suffix('.srt');Q=EP/'qa';P=json.loads((EP/'storyboard/SHOT_PLAN-production-v3.json').read_text())
def save(n,d):(Q/n).write_text(json.dumps(d,ensure_ascii=False,indent=2))
def sheets():
 for start in range(0,len(P['shots']),24):
  group=P['shots'][start:start+24];out=Image.new('RGB',(1440,math.ceil(len(group)/4)*230),(30,34,40));draw=ImageDraw.Draw(out)
  for i,s in enumerate(group):
   im=ImageOps.fit(Image.open(EP/'image/normalized'/f"{s['id']}.png"),(360,203),method=Image.Resampling.LANCZOS);x=i%4*360;y=i//4*230;out.paste(im,(x,y+23));draw.text((x+5,y+4),s['id']+' '+s['scene_id'],fill='white')
  out.save(Q/f'contact-v3-{start//24+1}.jpg',quality=94)
 print('SHEETS_READY')
def final():
 subprocess.run([sys.executable,str(ROOT/'shared/workflows/body-only/check_delivery.py'),'--video',str(V),'--srt',str(S),'--json',str(Q/'delivery-v3.json')],check=True)
 # Decode every frame; collect luma statistics from full-size decoded output, no temporal skipping.
 stat=Q/'signalstats-v3.txt';log=Q/'decode-scan-v3.log'
 with log.open('w') as f:
  subprocess.run(['ffmpeg','-v','warning','-xerror','-i',str(V),'-map','0:v:0','-vf',f'signalstats,metadata=print:file={stat}','-an','-f','null','-'],stdout=f,stderr=f,check=True)
 text=stat.read_text();frames=[]
 for m in re.finditer(r'frame:(\d+)\s+pts:\S+\s+pts_time:([\d.]+)\n(.*?)(?=frame:|\Z)',text,re.S):
  vals=dict(re.findall(r'lavfi.signalstats.([A-Z]+)=([\d.]+)',m[3]));frames.append({'frame':int(m[1]),'pts':float(m[2]),'min':float(vals['YMIN']),'max':float(vals['YMAX']),'mean':float(vals['YAVG'])})
 assert len(frames)==P['frames'],(len(frames),P['frames'])
 def intervals(predicate):
  groups=[];start=None
  for i,d in enumerate(frames+[{'min':100,'max':100,'mean':100}]):
   if i<len(frames) and predicate(d):
    if start is None:start=i
   elif start is not None:
    if i-start>=24:groups.append({'start_frame':start,'end_frame_exclusive':i,'seconds':(i-start)/24})
    start=None
  return groups
 black=intervals(lambda d:d['mean']<25 and d['max']<40);white=intervals(lambda d:d['mean']>240 and d['min']>230)
 maxerr=max(abs(d['pts']-d['frame']/24) for d in frames);steps=[frames[i+1]['pts']-frames[i]['pts'] for i in range(len(frames)-1)]
 # metadata uses six significant decimal digits; allow0.6ms formatting precision, <1/60 frame.
 cfr=maxerr<.0006 and min(steps)>.0410 and max(steps)<.0423
 report={'decoded_frames':len(frames),'expected_frames':P['frames'],'full_decode_success':True,'pixel_stats':'full-resolution luma, every decoded frame','black_intervals_ge_1s':black,'white_intervals_ge_1s':white,'max_pts_error_s':maxerr,'step_min_s':min(steps),'step_max_s':max(steps),'cfr_uniform':cfr,'passed':not black and not white and cfr}
 save('pixel_scan.json',report);assert report['passed'],report
 streams=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(V)]));save('video.json',streams)
 v=streams['streams'][0];assert len(streams['streams'])==1 and v['codec_name']=='h264' and v['pix_fmt']=='yuv420p' and v['width']==1920 and v['height']==1080 and v['avg_frame_rate']=='24/1' and int(v['nb_frames'])==P['frames']
 data=V.read_bytes();moov=data.find(b'moov');mdat=data.find(b'mdat');assert 0<moov<mdat
 save('final-integrity-v3.json',{'mp4_sha256':hashlib.sha256(data).hexdigest(),'srt_sha256':hashlib.sha256(S.read_bytes()).hexdigest(),'faststart_moov_before_mdat':True,'duration_s':P['duration'],'frames':P['frames'],'fps':24,'technical_delivery':'PASS','visual_review_record':'qa/visual-review-v3.md','no_audio_subtitle_streams':True,'no_intro_assets':True})
 print('FINAL_QA_PASS',flush=True)
if __name__=='__main__':
 if sys.argv[1]=='sheets':sheets()
 else:final()
