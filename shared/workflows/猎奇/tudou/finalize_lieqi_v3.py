# lieqi tudou v3 compose: same method as finalize_lieqi.py (normalize each shot to 1080x1920/24fps, swap in VoxCPM2 audio,
# t1/t2 static frames with silence, concat; no subtitles). Inputs: clips_v3, voice\seed42_v2, frame_map_v3. Old final kept.
import os,json,time,subprocess,shutil
from pathlib import Path
BASE=Path(r'E:\program\1project\video\projects\猎奇\episodes\tudou'); clips=BASE/'video'/'clips'; audio=BASE/'audio'/'vo_seed42_v2'
frames=json.loads((BASE/'image'/'plot_grids_v2'/'frame_map_v3.json').read_text(encoding='utf-8'))
shots=json.loads((BASE/'storyboard'/'shotlist_v1.json').read_text(encoding='utf-8'))['shots']
out=BASE/'video'; work=BASE/'video'/'clips'/'compose_v3'; out.mkdir(exist_ok=True); work.mkdir(exist_ok=True)
ids=[s['id'] for s in shots]
def dur(sid,s):
 w=audio/(sid+'.wav')
 if w.exists():
  q=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(w)],capture_output=True,text=True)
  try:return float(q.stdout.strip())
  except:pass
 return float(s.get('duration_hint_sec') or 2.0)
missing=[sid for sid in ids if sid.startswith('s') and not (clips/(sid+'.mp4')).exists()]
if missing: raise SystemExit('missing clips: %s'%missing)
lst=[]
for s in shots:
 sid=s['id']; d=dur(sid,s); seg=work/(sid+'.mp4'); lst.append(seg)
 if seg.exists(): continue
 vf='scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=24,format=yuv420p'
 if sid.startswith('s'):
  src=clips/(sid+'.mp4'); wav=audio/(sid+'.wav')
  cmd=['ffmpeg','-y','-i',str(src),'-i',str(wav),'-t',f'{d:.3f}','-vf',vf,'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','veryfast','-crf','20','-c:a','aac','-b:a','192k','-ar','48000','-ac','1','-shortest',str(seg)]
 else:
  src=Path(frames[sid]['upscaled'])
  cmd=['ffmpeg','-y','-loop','1','-i',str(src),'-f','lavfi','-i','anullsrc=r=48000:cl=mono','-t',f'{d:.3f}','-vf',vf,'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','veryfast','-crf','20','-c:a','aac','-b:a','192k','-ar','48000','-ac','1',str(seg)]
 r=subprocess.run(cmd,capture_output=True,text=True)
 if r.returncode: raise RuntimeError(sid+' normalize failed '+r.stderr[-1000:])
 print('SEG',sid,d,flush=True)
concat=work/'concat.txt'; concat.write_text('\n'.join("file '"+str(x).replace("'","'\\''")+"'" for x in lst),encoding='utf-8')
final=out/'lieqi_tudou_final_v3.mp4'; subprocess.run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(final)],check=True)
shutil.copy2(Path(frames['s01']['upscaled']),BASE/'image'/'cover_v3.png')   # TITLES.txt unchanged (not rewritten)
subprocess.run(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,width,height,r_frame_rate','-of','compact',str(final)],check=False)
print('FINAL',final,flush=True)
