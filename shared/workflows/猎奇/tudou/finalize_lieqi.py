import os,json,time,subprocess,shutil
from pathlib import Path
BASE=Path(r'E:\program\1project\video\projects\猎奇\episodes\tudou'); clips=BASE/'archive'/'video'/'clips_v1'; audio=BASE/'archive'/'audio'/'voxcpm2-shots'; frames=json.loads((BASE/'archive'/'image'/'firstframes_v1'/'frame_map.json').read_text(encoding='utf-8')); shots=json.loads((BASE/'storyboard'/'shotlist_v1.json').read_text(encoding='utf-8'))['shots']; out=BASE/'archive'/'final_v1'; work=BASE/'archive'/'final_v1'/'compose_work'; out.mkdir(exist_ok=True); work.mkdir(exist_ok=True)
ids=[s['id'] for s in shots]
def dur(sid,s):
 w=audio/(sid+'.wav')
 if w.exists():
  q=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(w)],capture_output=True,text=True)
  try:return float(q.stdout.strip())
  except:pass
 return float(s.get('duration_hint_sec') or 2.0)
while True:
 missing=[sid for sid in ids if sid.startswith('s') and not (clips/(sid+'.mp4')).exists()]
 if not missing: break
 print('WAIT clips',len(missing),missing[:4],flush=True); time.sleep(60)
# create normalized segments, replacing any model-generated audio with registered voice
lst=[]
for s in shots:
 sid=s['id']; d=dur(sid,s); seg=work/(sid+'.mp4'); lst.append(seg)
 if seg.exists(): continue
 vf='scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=24,format=yuv420p'
 if sid.startswith('s'):
  src=clips/(sid+'.mp4'); wav=audio/(sid+'.wav')
  cmd=['ffmpeg','-y','-i',str(src),'-i',str(wav),'-t',f'{d:.3f}','-vf',vf,'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','veryfast','-crf','20','-c:a','aac','-b:a','192k','-ar','48000','-ac','1','-shortest',str(seg)]
 else:
  src=Path(frames[sid]['upscaled'].replace('/workspace/lieqi/tudou/firstframes',str(BASE/'archive'/'image'/'firstframes_v1')).replace('/', '\\'))
  cmd=['ffmpeg','-y','-loop','1','-i',str(src),'-f','lavfi','-i','anullsrc=r=48000:cl=mono','-t',f'{d:.3f}','-vf',vf,'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','veryfast','-crf','20','-c:a','aac','-b:a','192k','-ar','48000','-ac','1',str(seg)]
 r=subprocess.run(cmd,capture_output=True,text=True)
 if r.returncode: raise RuntimeError(sid+' normalize failed '+r.stderr[-1000:])
 print('SEG',sid,d,flush=True)
concat=work/'concat.txt'; concat.write_text('\n'.join("file '"+str(x).replace("'","'\\''")+"'" for x in lst),encoding='utf-8')
final=out/'lieqi_tudou_final.mp4'; subprocess.run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(final)],check=True)
# cover and titles
cover=Path(frames['s01']['upscaled'].replace('/workspace/lieqi/tudou/firstframes',str(BASE/'archive'/'image'/'firstframes_v1')).replace('/', '\\')); shutil.copy2(cover,out/'cover.png')
(out/'TITLES.txt').write_text('1. 《土豆退婚流：三年之后，让你们番茄家高攀不起！》\n2. 番茄千金退婚后，土豆总裁杀回来了\n3. 黄瓜味薯片上线：蔬菜豪门的离谱修罗场\n',encoding='utf-8')
subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(final)],check=False)
print('FINAL',final,flush=True)
