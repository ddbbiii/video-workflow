from pathlib import Path
import subprocess,json,re,hashlib,sys
EP=Path(__file__).resolve().parents[1];ROOT=EP.parents[3]
V=EP/'video/final/悬疑_如果你还记得这个地方_正文_v1.mp4';S=V.with_suffix('.srt');Q=EP/'qa'

def run(args,output=None):
 p=subprocess.run(args,capture_output=True,text=True)
 if output:Path(output).write_text(p.stdout+p.stderr)
 if p.returncode:raise RuntimeError(p.stderr or p.stdout)
 return p.stdout

raw=run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(V)])
probe=json.loads(raw);stream=probe['streams'][0];n=int(stream['nb_frames']);fps=24
assert len(probe['streams'])==1 and stream['codec_type']=='video'
assert stream['width']==1920 and stream['height']==1080 and stream['avg_frame_rate']=='24/1' and stream['pix_fmt']=='yuv420p'
assert stream['codec_name']=='h264'
lock=json.loads((EP/'story/LOCK.json').read_text())
assert hashlib.sha256((EP/'story'/lock['script']).read_bytes()).hexdigest()==lock['sha256']
# Whole frame, every frame pixel statistics; full decode with errors fatal.
metrics=Q/'pixel-stats.txt'
run(['ffmpeg','-v','error','-xerror','-i',str(V),'-vf',f'signalstats,metadata=mode=print:file={metrics}', '-an','-f','null','-'],Q/'decode.log')
records=[];current=None
for line in metrics.read_text().splitlines():
 if line.startswith('frame:'):
  if current:records.append(current)
  current={'frame':int(re.search(r'frame:(\d+)',line)[1])}
 elif '=' in line and current is not None:
  k,v=line.split('=',1)
  if k.startswith('lavfi.signalstats.'):
   try:current[k.rsplit('.',1)[1]]=float(v)
   except ValueError:pass
if current:records.append(current)
assert len(records)==n,(len(records),n)

def intervals(predicate):
 out=[];start=None
 for i,r in enumerate(records+[{}]):
  yes=i<len(records) and predicate(r)
  if yes and start is None:start=i
  if not yes and start is not None:
   if i-start>=24:out.append({'start_frame':start,'end_frame':i,'duration_s':(i-start)/24})
   start=None
 return out
black=intervals(lambda r:r['YAVG']<=24 and r['YMAX']<=32)
white=intervals(lambda r:r['YAVG']>=230 and r['YMIN']>=220)
# Additional 98%-pixel coverage detector includes frames with a tiny bright/dark exception.
for kind,extra in [('black',[]),('white',['negate'])]:
 filters=','.join(extra+['blackdetect=d=1:pix_th=0.10:pic_th=0.98'])
 out=subprocess.run(['ffmpeg','-v','info','-xerror','-i',str(V),'-vf',filters,'-an','-f','null','-'],capture_output=True,text=True)
 (Q/f'{kind}-98pct.log').write_text(out.stderr);assert out.returncode==0
 found=[{'start_s':float(a),'end_s':float(b),'duration_s':float(c)} for a,b,c in re.findall(r'black_start:([\d.]+) black_end:([\d.]+) black_duration:([\d.]+)',out.stderr) if float(c)>=1]
 if kind=='black':black.extend(found)
 else:white.extend(found)
ptsraw=run(['ffprobe','-v','error','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',str(V)])
pts=[float(x['best_effort_timestamp_time']) for x in json.loads(ptsraw)['frames']]
assert len(pts)==n
maxstep=max(abs((b-a)-1/24) for a,b in zip(pts,pts[1:]))
# Text equality is checked independently from line wrapping.
rows=json.loads((EP/'story/sentences.json').read_text())['rows']
strip=lambda s:''.join(c for c in s if c.isalnum())
text=''.join('\n'.join(b.splitlines()[2:]) for b in re.split(r'\n\s*\n',S.read_text().strip()))
assert strip(text)==strip(''.join(r['text'] for r in rows))
report={'pass':not black and not white and maxstep<.00001,'frames':n,'fps':24,'duration_s':n/24,'decoded_frames':len(records),'pixel_scan':'1920x1080 every frame: signalstats YMIN YMAX YAVG; not sampled thumbnails','black_intervals_ge_1s':black,'white_intervals_ge_1s':white,'cfr_max_step_error_s':maxstep,'narration_exact_match':True,'audio_streams':0,'subtitle_streams':0,'video_sha256':hashlib.sha256(V.read_bytes()).hexdigest(),'srt_sha256':hashlib.sha256(S.read_bytes()).hexdigest()}
(Q/'pixel-and-content.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));assert report['pass'],report
run([sys.executable,str(ROOT/'shared/workflows/body-only/check_delivery.py'),'--video',str(V),'--srt',str(S),'--json',str(Q/'delivery.json')],Q/'delivery-check.log')
print(json.dumps(report,ensure_ascii=False,indent=2))
