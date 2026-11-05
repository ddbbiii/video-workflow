import sys, os, json, time, shutil, wave
from pathlib import Path
sys.path.insert(0, r'E:\program\1project\video\shared\workflows\猎奇\tudou\i2v')  # i2v_cmp.py（原在 C:\...\Temp，2026-10-08 改指同目录）
import i2v_cmp as m
BASE=r'E:\program\1project\video\projects\猎奇\episodes\tudou'
SCR=os.path.join(BASE,'i2v'); m.SCR=SCR
m.LOGF=os.path.join(BASE,'logs','i2v_v1','lieqi_i2v.log'); m.RESF=os.path.join(BASE,'logs','i2v_v1','results.json')
# ComfyUI input/output are private to this batch; no web UI.
os.makedirs(os.path.join(SCR,'in'),exist_ok=True); os.makedirs(os.path.join(SCR,'out'),exist_ok=True); os.makedirs(os.path.join(SCR,'logs'),exist_ok=True)
# generic vegetable-motion prompt/negative; per-shot motion is appended.
m.NEG='text, letters, subtitles, watermark, logo, cartoon, anime, plastic, extra limbs, extra fingers, deformed hands, scene change, hard cut, camera shake, flicker, melting, warping, blood, gore, wounds'
def run_batch():
    frames=json.load(open(os.path.join(BASE,'archive','image','firstframes_v1','frame_map.json'),encoding='utf-8'))
    shots=json.load(open(os.path.join(BASE,'storyboard','shotlist_v1.json'),encoding='utf-8'))['shots']
    by={s['id']:s for s in shots}
    audio=os.path.join(BASE,'archive','audio','voxcpm2-shots')
    clips=os.path.join(BASE,'archive','video','clips_v1'); os.makedirs(clips,exist_ok=True)
    # skip already successful outputs for resumability
    records=[]
    for sid in [f's{i:02d}' for i in range(1,37)]:
        wav=os.path.join(audio,sid+'.wav')
        dur=2.0
        if os.path.exists(wav):
            with wave.open(wav,'rb') as w: dur=w.getnframes()/w.getframerate()
        else:
            dur=float(by.get(sid,{}).get('duration_hint_sec') or 2.0)
        # 480x832 LTX is the documented fallback tier; final compose upscales to 1080x1920.
        f=max(49, int(round(dur*24/8))*8+1)
        out=os.path.join(clips,sid+'.mp4')
        if os.path.exists(out) and os.path.getsize(out)>10000:
            records.append({'id':sid,'ok':True,'skipped':True,'duration_audio':dur,'frames':f,'file':out}); continue
        src=frames[sid]['upscaled'].replace('/workspace/lieqi/tudou/firstframes', os.path.join(BASE,'archive','image','firstframes_v1')).replace('/', '\\')
        dst=os.path.join(SCR,'in',sid+'.png')
        shutil.copy2(src,dst); m.IMAGE=sid+'.png'
        s=by.get(sid,{})
        motion=s.get('motion_prompt_en') or s.get('camera','') or 'subtle natural cinematic motion'
        m.PROMPT=('Photoreal live-action vertical 9:16 vegetable-headed character scene. '+motion+'. Preserve the exact first-frame characters, faces, clothing, hands, lighting and background. Smooth restrained motion, no scene change, no text.')
        # Build graph at 480p fallback, then remove generated LTX audio; final mix uses registered VoxCPM2.
        g=m.g_ltx(480,832,f,11,'i2v-lieqi/'+sid)
        g['5']['inputs']['text']='text, letters, subtitles, watermark, logo, cartoon, anime, plastic, deformed objects, camera shake, flicker, scene change'
        # run through API using the same tested runner logic
        try:
            m.http('/free', {'unload_models':False,'free_memory':True}); time.sleep(1)
        except Exception: pass
        tag='ltx_'+sid
        m.json.dump(g,open(os.path.join(BASE,'logs','i2v_v1','graph_'+tag+'.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=1)
        smp=m.Sampler(m.PROC.pid,tag); t0=time.time(); rec={'id':sid,'duration_audio':dur,'frames':f}
        try:
            resp=json.loads(m.http('/prompt',{'prompt':g,'client_id':sid}).decode()); pid=resp['prompt_id']; m.log('%s queued %s dur=%.2f f=%d'%(sid,pid,dur,f))
            entry=None
            while True:
                time.sleep(10)
                if m.PROC.poll() is not None: raise RuntimeError('comfy died')
                hist=m.jget('/history/'+pid,timeout=30)
                if pid in hist: entry=hist[pid]; break
                if time.time()-t0>3600: raise RuntimeError('timeout')
            rec['ok']=entry.get('status',{}).get('status_str')=='success'
            files=[]
            for n in entry.get('outputs',{}).values():
                for v in n.get('gifs',[])+n.get('videos',[]):
                    if v.get('filename'): files.append(os.path.join(v.get('subfolder',''),v['filename']))
            # SaveVideo normally reports files under SCR/out; locate newest matching sid if history shape differs.
            cand=[]
            for root,_,fs in os.walk(os.path.join(SCR,'out')):
                for fn in fs:
                    if sid in fn and fn.lower().endswith(('.mp4','.webm','.mov')): cand.append(os.path.join(root,fn))
            if cand:
                latest=max(cand,key=os.path.getmtime); shutil.copy2(latest,out); rec['file']=out; rec['source']=latest
            rec['files']=files; rec['elapsed_s']=round(time.time()-t0,1)
        except Exception as e:
            rec.update(ok=False,error=str(e),elapsed_s=round(time.time()-t0,1)); m.log('%s FAIL %s'%(sid,e))
        rec.update(m.smp.finish() if False else {})
        records.append(rec); json.dump(records,open(m.RESF,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
        if not rec.get('ok'): break
    # caller handles stop/release in finally

if __name__=='__main__':
    try:
        os.makedirs(SCR,exist_ok=True)
        m.acquire_lock('lieqi-i2v')
        # start_comfy reads this config from SCR for model locations
        if not os.path.exists(os.path.join(SCR,'extra_model_paths_diffusion.yaml')):
            raise RuntimeError('missing extra_model_paths_diffusion.yaml in '+SCR)
        m.start_comfy('portable','lieqi')
        run_batch()
    finally:
        m.stop_comfy(); m.release_lock()
