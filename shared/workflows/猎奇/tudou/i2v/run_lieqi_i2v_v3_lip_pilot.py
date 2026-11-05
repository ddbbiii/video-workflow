# lieqi tudou LIP PILOT: LTX i2v with real VO (LoadAudio+LTXVAudioVAEEncode) instead of LTXVEmptyLatentAudio.
# Does NOT touch clips_v3 or finalize. Outputs -> clips_v3_lip_pilot/. Uses private Comfy dirs under i2v\v3_lip_pilot.
import sys, os, json, time, shutil, wave, subprocess
sys.path.insert(0, r'E:\program\1project\video\shared\workflows\猎奇\tudou\i2v')  # i2v_cmp.py（原在 C:\...\Temp，2026-10-08 改指同目录）
import i2v_cmp as m

BASE = r'E:\program\1project\video\projects\猎奇\episodes\tudou'
SCR = r'E:\program\1project\video\projects\猎奇\drafts\tudou-lip-pilot-ltx'
m.SCR = SCR
for d in ('in', 'out', 'logs', 'temp'):
    os.makedirs(os.path.join(SCR, d), exist_ok=True)
m.LOGF = os.path.join(SCR, 'logs', 'lip_pilot.log')
m.RESF = os.path.join(SCR, 'results_lip_pilot.json')
yaml_src = r'E:\program\1project\video\shared\workflows\猎奇\tudou\i2v\extra_model_paths_diffusion.yaml'
yaml_dst = os.path.join(SCR, 'extra_model_paths_diffusion.yaml')
if not os.path.exists(yaml_dst):
    shutil.copy2(yaml_src, yaml_dst)

m.NEG = ('text, letters, subtitles, watermark, logo, cartoon, anime, plastic, extra limbs, '
         'extra fingers, deformed hands, scene change, hard cut, camera shake, flicker, '
         'melting, warping, blood, gore, wounds')
OWNER = 'lieqi:i2v-lip-pilot'
PILOT_SHOTS = ['s01', 's02', 's25']  # 番茄千金 / 土豆近景(唇抖) / 番茄千金近景
CLIPS = r'E:\program\1project\video\projects\猎奇\drafts\tudou-lip-pilot-ltx'
AUDIO_DIR = os.path.join(BASE, 'audio', 'vo_seed42_v2')
os.makedirs(CLIPS, exist_ok=True)


def acquire_lock():
    waited = 0
    while True:
        holder = None
        if os.path.exists(m.LOCK):
            try:
                holder = json.load(open(m.LOCK, encoding='utf-8'))
                if holder.get('pid') == os.getpid() or not m.pid_alive(holder.get('pid', 0)):
                    m.log('stale gpu.lock (%s) -> taking over' % holder)
                    holder = None
            except Exception:
                holder = {'unreadable': True}
        t = m.tts_procs()
        g = m.other_gpu_python()
        if not holder and not t and not g:
            break
        if waited % 300 == 0:
            m.log('WAIT gpu busy: lock=%s tts=%s cuda=%s' % (holder, [x[:120] for x in t], g))
        time.sleep(30)
        waited += 30
    json.dump(dict(pid=os.getpid(), owner=OWNER, started=time.strftime('%Y-%m-%dT%H:%M:%S+08:00')),
              open(m.LOCK, 'w', encoding='utf-8'))
    m.log('gpu.lock acquired for %s (waited %ds)' % (OWNER, waited))


def patch_ltx_real_audio(g, wav_basename):
    """Replace LTXVEmptyLatentAudio with LoadAudio + LTXVAudioVAEEncode; mux real wav into CreateVideo."""
    g['14a'] = {'class_type': 'LoadAudio', 'inputs': {'audio': wav_basename}}
    g['14'] = {
        'class_type': 'LTXVAudioVAEEncode',
        'inputs': {'audio': ['14a', 0], 'audio_vae': ['13', 0]},
    }
    # Drop LTX-generated audio decode; attach the same VO wav to the saved mp4.
    if '34' in g:
        del g['34']
    if 'cv' in g and 'inputs' in g['cv']:
        g['cv']['inputs']['audio'] = ['14a', 0]
    return g


def mux_vo(src_mp4, wav, dst_mp4, dur):
    cmd = [
        'ffmpeg', '-y', '-i', src_mp4, '-i', wav, '-t', '%.3f' % dur,
        '-map', '0:v:0', '-map', '1:a:0',
        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '1',
        '-shortest', dst_mp4,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError('ffmpeg mux failed: ' + (r.stderr or '')[-800:])


def run_pilot():
    frames = json.load(open(os.path.join(BASE, 'image', 'plot_grids_v2', 'frame_map_v3.json'), encoding='utf-8'))
    shots = json.load(open(os.path.join(BASE, 'storyboard', 'shotlist_v1.json'), encoding='utf-8'))['shots']
    by = {s['id']: s for s in shots}
    records = []
    if os.path.exists(m.RESF):
        try:
            records = [r for r in json.load(open(m.RESF, encoding='utf-8')) if r.get('ok')]
        except Exception:
            records = []
    done = {r['id'] for r in records}

    for sid in PILOT_SHOTS:
        if sid not in by:
            m.log('SKIP %s not in shotlist' % sid)
            continue
        out = os.path.join(CLIPS, sid + '.mp4')
        if os.path.exists(out) and os.path.getsize(out) > 10000 and sid in done:
            m.log('SKIP %s already ok' % sid)
            continue
        wav = os.path.join(AUDIO_DIR, sid + '.wav')
        if not os.path.exists(wav):
            raise RuntimeError('missing wav ' + wav)
        with wave.open(wav, 'rb') as w:
            dur = w.getnframes() / float(w.getframerate())
        f = max(49, int(round(dur * 24 / 8)) * 8 + 1)

        # first frame + wav into Comfy input dir
        src_img = frames[sid]['upscaled']
        dst_img = os.path.join(SCR, 'in', sid + '.png')
        shutil.copy2(src_img, dst_img)
        wav_name = sid + '.wav'
        shutil.copy2(wav, os.path.join(SCR, 'in', wav_name))
        m.IMAGE = sid + '.png'

        s = by.get(sid, {})
        motion = s.get('motion_prompt_en') or s.get('camera', '') or 'subtle natural cinematic motion'
        m.PROMPT = (
            'Photoreal live-action vertical 9:16 vegetable-headed character scene. '
            + motion
            + '. Preserve the exact first-frame characters, faces, clothing, hands, lighting and background. '
              'Smooth restrained motion, no scene change, no text. Accurate lip sync to the spoken dialogue.'
        )
        g = m.g_ltx(480, 832, f, 11, 'i2v-lieqi-lip/' + sid)
        g['5']['inputs']['text'] = (
            'text, letters, subtitles, watermark, logo, cartoon, anime, plastic, deformed objects, '
            'camera shake, flicker, scene change'
        )
        patch_ltx_real_audio(g, wav_name)

        try:
            m.http('/free', {'unload_models': False, 'free_memory': True})
            time.sleep(1)
        except Exception:
            pass

        tag = 'ltx_lip_' + sid
        json.dump(g, open(os.path.join(SCR, 'logs', 'graph_' + tag + '.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        t0 = time.time()
        rec = {
            'id': sid, 'duration_audio': dur, 'frames': f, 'first_frame': src_img,
            'audio_wav': wav, 'graph_patch': 'LoadAudio+LTXVAudioVAEEncode',
        }
        try:
            resp = json.loads(m.http('/prompt', {'prompt': g, 'client_id': 'lip-' + sid}).decode())
            pid = resp['prompt_id']
            m.log('%s queued %s dur=%.2f f=%d REAL_AUDIO=%s' % (sid, pid, dur, f, wav_name))
            entry = None
            while True:
                time.sleep(10)
                if m.PROC.poll() is not None:
                    raise RuntimeError('comfy died')
                hist = m.jget('/history/' + pid, timeout=30)
                if pid in hist:
                    entry = hist[pid]
                    break
                if time.time() - t0 > 3600:
                    raise RuntimeError('timeout')
            rec['ok'] = entry.get('status', {}).get('status_str') == 'success'
            if not rec['ok']:
                rec['status'] = entry.get('status')
                # surface node errors if present
                try:
                    rec['messages'] = entry.get('status', {}).get('messages')
                except Exception:
                    pass
            cand = []
            for root, _, fs in os.walk(os.path.join(SCR, 'out')):
                for fn in fs:
                    if fn.startswith(sid + '_') and fn.lower().endswith(('.mp4', '.webm', '.mov')):
                        cand.append(os.path.join(root, fn))
            if cand and rec['ok']:
                latest = max(cand, key=os.path.getmtime)
                raw = os.path.join(CLIPS, sid + '_raw_comfy.mp4')
                shutil.copy2(latest, raw)
                # Remux again explicitly with VO (CreateVideo already attached 14a; ensure AAC + shortest)
                mux_vo(raw, wav, out, dur)
                rec['file'] = out
                rec['source'] = latest
                rec['raw'] = raw
            elif rec['ok']:
                rec['ok'] = False
                rec['error'] = 'no output file found'
            rec['elapsed_s'] = round(time.time() - t0, 1)
        except Exception as e:
            rec.update(ok=False, error=str(e), elapsed_s=round(time.time() - t0, 1))
            m.log('%s FAIL %s' % (sid, e))
        records = [r for r in records if r.get('id') != sid] + [rec]
        json.dump(records, open(m.RESF, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        m.log('%s done ok=%s %.0fs' % (sid, rec.get('ok'), rec['elapsed_s']))
        if not rec.get('ok'):
            break
    return records


if __name__ == '__main__':
    try:
        acquire_lock()
        m.start_comfy('portable', 'lieqi-lip-pilot')
        recs = run_pilot()
        ok_n = sum(1 for r in recs if r.get('ok') and r.get('id') in PILOT_SHOTS)
        m.log('PILOT FINISH ok=%d/%d' % (ok_n, len(PILOT_SHOTS)))
    finally:
        try:
            m.stop_comfy()
        except Exception as e:
            m.log('stop_comfy err %s' % e)
        try:
            m.release_lock()
        except Exception as e:
            # fallback release if pid matches
            try:
                if os.path.exists(m.LOCK):
                    h = json.load(open(m.LOCK, encoding='utf-8'))
                    if h.get('owner') == OWNER:
                        os.remove(m.LOCK)
                        m.log('gpu.lock force-released for %s' % OWNER)
            except Exception as e2:
                m.log('lock release fallback err %s / %s' % (e, e2))