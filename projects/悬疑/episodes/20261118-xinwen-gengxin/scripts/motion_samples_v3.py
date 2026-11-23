from pathlib import Path
import json,sys,cv2,numpy as np,math
EP=Path(__file__).resolve().parents[1];ROOT=EP.parents[3];sys.path.insert(0,str(ROOT/'shared/camera-motion'));from verify_motion import ecc
cv2.setNumThreads(1)
P=json.loads((EP/'storyboard/motion-plan-v3.json').read_text());results=[]
# Encoded checks cover all moving still shots at separated timestamps, not just planned matrices.
for s in P['shots']:
 if s['start_view']==s['end_view']:continue
 path=EP/'video/clips'/f"{s['id']}.mp4";meta=json.loads((EP/'video/clips'/f"{s['id']}-trajectory.json").read_text());mat=np.array(meta['inverse_sample_matrices']);cap=cv2.VideoCapture(str(path));n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));samples=[]
 for f in sorted(set([max(1,round((n-2)*q)) for q in [.2,.5,.8]])):
  cap.set(cv2.CAP_PROP_POS_FRAMES,f);ok,a=cap.read();ok2,b=cap.read();assert ok and ok2
  # Half resolution registration retains scale and robustly measures dominant texture.
  a=cv2.resize(a,(960,540));b=cv2.resize(b,(960,540));a=cv2.cvtColor(a,cv2.COLOR_BGR2GRAY).astype('float32')/255;b=cv2.cvtColor(b,cv2.COLOR_BGR2GRAY).astype('float32')/255
  score,m=ecc(a,b)
  if m is None:samples.append({'frame':f,'status':'indeterminate','reason':'ecc_failed'});continue
  p0=np.vstack([mat[f],[0,0,1]]);p1=np.vstack([mat[f+1],[0,0,1]]);expected=np.linalg.inv(p1)@p0;c=np.array([960,540,1.]);obs=m@np.array([480,270,1.])-np.array([480,270]);ex=(expected@c)[:2]-c[:2];res=float(np.linalg.norm(obs*2-ex))
  samples.append({'frame':f,'correlation':score,'center_residual_px':res,'status':'pass' if score>.98 and res<.15 else 'indeterminate'})
 cap.release();results.append({'id':s['id'],'samples':samples,'status':'pass' if all(t['status']=='pass' for t in samples) else 'indeterminate'})
report={'method':'encoded adjacent-frame ECC,3 pairs/ordinary moving shot at20/50/80%, registration at half resolution; compare to60Hz source matrices selected for24fps output','shots':results,'passed_shots':sum(s['status']=='pass' for s in results),'indeterminate_shots':[s['id'] for s in results if s['status']!='pass'],'limitation':'Sampled encoded motion validation; full-frame decode/CFR and actual transition frame inspection are separate checks. No internal-character animation claimed.'}
(EP/'qa/encoded-motion-samples-v3.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='shots'},ensure_ascii=False),flush=True)
