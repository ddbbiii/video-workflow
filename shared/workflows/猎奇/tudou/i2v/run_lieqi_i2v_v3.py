# lieqi tudou v3 i2v: same runner/settings as i2v\run_lieqi_i2v.py (LTX-2.3 two-stage, 480x832, steps 11, seed 42,
# frames from audio length) with: first frames = firstframes\plot_grids_v2\frame_map_v3.json, audio = voice\seed42_v2,
# private ComfyUI dirs under i2v\v3, clips -> clips_v3. Lock owner 'lieqi:i2v-v3' (same JSON format, same wait rules as i2v_cmp).
import sys, os, json, time, shutil, wave
sys.path.insert(0, r'E:\program\1project\video\shared\workflows\猎奇\tudou\i2v')  # i2v_cmp.py（原在 C:\...\Temp，2026-10-08 改指同目录）
import i2v_cmp as m
BASE=r'E:\program\1project\video\projects\猎奇\episodes\tudou'
SCR=os.path.join(BASE,'i2v','v3'); m.SCR=SCR
for d in ('in','out','logs'): os.makedirs(os.path.join(SCR,d),exist_ok=True)
m.LOGF=os.path.join(BASE,'logs','i2v_v3','lieqi_i2v_v3.log'); m.RESF=os.path.join(BASE,'logs','i2v_v3','results_v3.json')
if not os.path.exists(os.path.join(SCR,'extra_model_paths_diffusion.yaml')):
    shutil.copy2(r'E:\program\1project\video\shared\workflows\猎奇\tudou\i2v\extra_model_paths_diffusion.yaml',os.path.join(SCR,'extra_model_paths_diffusion.yaml'))
m.NEG='text, letters, subtitles, watermark, logo, cartoon, anime, plastic, extra limbs, extra fingers, deformed hands, scene change, hard cut, camera shake, flicker, melting, warping, blood, gore, wounds'
OWNER='lieqi:i2v-v3'
def acquire_lock():
    waited=0
    while True:
        holder=None
        if os.path.exists(m.LOCK):
            try:
                holder=json.load(open(m.LOCK,encoding='utf-8'))
                if holder.get('pid')==os.getpid() or not m.pid_alive(holder.get('pid',0)):
                    m.log('stale gpu.lock (%s) -> taking over'%holder); holder=None
            except Exception:
                holder={'unreadable':True}
        t=m.tts_procs(); g=m.other_gpu_python()
        if not holder and not t and not g: break
        if waited%300==0: m.log('WAIT gpu busy: lock=%s tts=%s cuda=%s'%(holder,[x[:120] for x in t],g))
        time.sleep(30); waited+=30
    json.dump(dict(pid=os.getpid(),owner=OWNER,started=time.strftime('%Y-%m-%dT%H:%M:%S+08:00')),open(m.LOCK,'w',encoding='utf-8'))
    m.log('gpu.lock acquired for %s (waited %ds)'%(OWNER,waited))
def run_batch():
    frames=json.load(open(os.path.join(BASE,'image','plot_grids_v2','frame_map_v3.json'),encoding='utf-8'))
    shots=json.load(open(os.path.join(BASE,'storyboard','shotlist_v1.json'),encoding='utf-8'))['shots']
    by={s['id']:s for s in shots}
    audio=os.path.join(BASE,'audio','vo_seed42_v2')
    clips=os.path.join(BASE,'video','clips'); os.makedirs(clips,exist_ok=True)
    resp_old=os.path.exists(m.RESF) and json.load(open(m.RESF,encoding='utf-8')) or []
    records=[r for r in resp_old if r.get('ok')]
    done={r['id'] for r in records}
    for sid in [f's{i:02d}' for i in range(1,37)]:
        if sid not in by: continue
        wav=os.path.join(audio,sid+'.wav')
        if os.path.exists(wav):
            with wave.open(wav,'rb') as w: dur=w.getnframes()/w.getframerate()
        else:
            dur=float(by.get(sid,{}).get('duration_hint_sec') or 2.0)
        f=max(49, int(round(dur*24/8))*8+1)
        out=os.path.join(clips,sid+'.mp4')
        if os.path.exists(out) and os.path.getsize(out)>10000:
            if sid not in done: records.append({'id':sid,'ok':True,'skipped':True,'duration_audio':dur,'frames':f,'file':out})
            continue
        src=frames[sid]['upscaled']
        dst=os.path.join(SCR,'in',sid+'.png')
        shutil.copy2(src,dst); m.IMAGE=sid+'.png'
        s=by.get(sid,{})
        motion=s.get('motion_prompt_en') or s.get('camera','') or 'subtle natural cinematic motion'
        m.PROMPT=('Photoreal live-action vertical 9:16 vegetable-headed character scene. '+motion+'. Preserve the exact first-frame characters, faces, clothing, hands, lighting and background. Smooth restrained motion, no scene change, no text.')
        g=m.g_ltx(480,832,f,11,'i2v-lieqi-v3/'+sid)
        g['5']['inputs']['text']='text, letters, subtitles, watermark, logo, cartoon, anime, plastic, deformed objects, camera shake, flicker, scene change'
        try:
            m.http('/free', {'unload_models':False,'free_memory':True}); time.sleep(1)
        except Exception: pass
        tag='ltx_'+sid
        json.dump(g,open(os.path.join(BASE,'logs','i2v_v3','graph_'+tag+'.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=1)
        t0=time.time(); rec={'id':sid,'duration_audio':dur,'frames':f,'first_frame':src}
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
            if not rec['ok']: rec['status']=entry.get('status')
            cand=[]
            for root,_,fs in os.walk(os.path.join(SCR,'out')):
                for fn in fs:
                    if fn.startswith(sid+'_') and fn.lower().endswith(('.mp4','.webm','.mov')): cand.append(os.path.join(root,fn))
            if cand and rec['ok']:
                latest=max(cand,key=os.path.getmtime); shutil.copy2(latest,out); rec['file']=out; rec['source']=latest
            elif rec['ok']:
                rec['ok']=False; rec['error']='no output file found'
            rec['elapsed_s']=round(time.time()-t0,1)
        except Exception as e:
            rec.update(ok=False,error=str(e),elapsed_s=round(time.time()-t0,1)); m.log('%s FAIL %s'%(sid,e))
        records.append(rec); json.dump(records,open(m.RESF,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
        m.log('%s done ok=%s %.0fs'%(sid,rec.get('ok'),rec['elapsed_s']))
        if not rec.get('ok'): break
if __name__=='__main__':
    try:
        acquire_lock()
        m.start_comfy('portable','lieqi-v3')
        run_batch()
    finally:
        m.stop_comfy(); m.release_lock()
