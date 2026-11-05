# a-space-cat LTX-2.3 draft i2v (VO-aligned lip path). Adapted from lieqi tudou lip pilot.
# Authority: 视频号规划 approved firstframes (51) + LTX-2.3 draft; H3 later for key shots only — NOT started here.
# Outputs -> clips_v6_ltx_draft\ (non-overwriting). Does NOT finalize. Discards LTX baked audio; muxes final VO.
import sys, os, json, time, shutil, wave, subprocess
sys.path.insert(0, r'C:\Users\10060\AppData\Local\Temp')
import i2v_cmp as m

BASE = r'E:\program\1project\video\projects\创意\episodes\a-space-cat'
SCR = os.path.join(BASE, 'archive', 'i2v_raw', 'ltx_draft')
m.SCR = SCR
for d in ('in', 'out', 'logs', 'temp'):
    os.makedirs(os.path.join(SCR, d), exist_ok=True)
m.LOGF = os.path.join(BASE, 'logs', 'i2v_ltx_draft', 'a_space_cat_ltx_draft.log')
m.RESF = os.path.join(BASE, 'qa', 'i2v_ltx_draft', 'results_ltx_draft.json')
yaml_src = r'E:\program\1project\video\shared\workflows\创意\a-space-cat\i2v\extra_model_paths_diffusion.yaml'
yaml_dst = os.path.join(SCR, 'extra_model_paths_diffusion.yaml')
if not os.path.exists(yaml_dst):
    shutil.copy2(yaml_src, yaml_dst)

m.NEG = (
    'text, letters, subtitles, watermark, logo, cartoon, anime, plastic, extra limbs, '
    'extra fingers, deformed hands, scene change, hard cut, camera shake, flicker, '
    'melting, warping, blood, gore, wounds, deformed cat, extra ears, extra tails'
)
OWNER = 'i2v:a-space-cat_ltx_draft'
CLIPS = os.path.join(BASE, 'video', 'clips', 'ltx_draft')
FF_DIR = os.path.join(BASE, 'image', 'firstframes')
AUDIO_DIR = os.path.join(BASE, 'audio', 'vo_v6_final')
SHOTLIST = os.path.join(BASE, 'storyboard', 'shotlist_v6.json')
STATUS = os.path.join(BASE, 'logs', 'i2v_ltx_draft_status.txt')
os.makedirs(CLIPS, exist_ok=True)
os.makedirs(os.path.join(BASE, 'logs'), exist_ok=True)


def write_status(msg, extra=None):
    lines = [
        '# a-space-cat LTX-2.3 draft i2v 状态',
        '',
        '更新时间：' + time.strftime('%Y-%m-%d %H:%M:%S') + '（UTC+8）',
        '锁所有者：' + OWNER,
        '锁路径：' + m.LOCK,
        '输出目录：' + CLIPS,
        '工作目录：' + SCR,
        '结果 JSON：' + m.RESF,
        '日志：' + m.LOGF,
        '模型：LTX-2.3 two-stage draft（480×832，steps 蒸馏档，seed 42）；未启动 H3',
        '音频：VO 对齐 LoadAudio+LTXVAudioVAEEncode；成片 mux 最终 VO，丢弃 LTX 生成音',
        '状态：' + msg,
    ]
    if extra:
        lines.append('')
        lines.extend(extra if isinstance(extra, list) else [str(extra)])
    open(STATUS, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')


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
            write_status('等待 GPU：lock=%s' % holder, ['等待秒数：%d' % waited])
        time.sleep(30)
        waited += 30
    payload = dict(
        pid=os.getpid(),
        owner=OWNER,
        started=time.strftime('%Y-%m-%dT%H:%M:%S+08:00'),
        project='chuangyi/a-space-cat',
        purpose='ltx-2.3 draft i2v all 51 shots VO-aligned',
    )
    json.dump(payload, open(m.LOCK, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    m.log('gpu.lock acquired for %s (waited %ds)' % (OWNER, waited))
    return waited


def patch_ltx_real_audio(g, wav_basename):
    g['14a'] = {'class_type': 'LoadAudio', 'inputs': {'audio': wav_basename}}
    g['14'] = {
        'class_type': 'LTXVAudioVAEEncode',
        'inputs': {'audio': ['14a', 0], 'audio_vae': ['13', 0]},
    }
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


def run_batch():
    shots = json.load(open(SHOTLIST, encoding='utf-8'))['shots']
    by = {s['id']: s for s in shots}
    records = []
    if os.path.exists(m.RESF):
        try:
            records = [r for r in json.load(open(m.RESF, encoding='utf-8')) if r.get('ok')]
        except Exception:
            records = []
    done = {r['id'] for r in records}
    order = [f's{i:02d}' for i in range(1, 52)]

    for sid in order:
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

        n = int(sid[1:])
        src_img = os.path.join(FF_DIR, by[sid].get('firstframe') or ('shot%02d.png' % n))
        if not os.path.exists(src_img):
            raise RuntimeError('missing firstframe ' + src_img)
        dst_img = os.path.join(SCR, 'in', sid + '.png')
        shutil.copy2(src_img, dst_img)
        wav_name = sid + '.wav'
        shutil.copy2(wav, os.path.join(SCR, 'in', wav_name))
        m.IMAGE = sid + '.png'

        motion = (
            by[sid].get('motion_prompt_en')
            or by[sid].get('camera')
            or 'subtle natural cinematic micro-motion, soft breathing, gentle fur movement, restrained camera drift'
        )
        m.PROMPT = (
            'Cinematic realistic vertical 9:16 film still of a silver-gradient British Shorthair cat in a space / science what-if scene. '
            + motion
            + '. Preserve the exact first-frame cat identity, face, fur color and pattern, costume/props, lighting and background. '
              'Smooth restrained motion, no scene change, no text. Accurate lip / mouth motion synced to the spoken narration when the face is visible.'
        )
        g = m.g_ltx(480, 832, f, 11, 'i2v-space-cat-draft/' + sid)
        g['5']['inputs']['text'] = (
            'text, letters, subtitles, watermark, logo, cartoon, anime, plastic, deformed objects, '
            'camera shake, flicker, scene change, deformed cat'
        )
        patch_ltx_real_audio(g, wav_name)

        try:
            m.http('/free', {'unload_models': False, 'free_memory': True})
            time.sleep(1)
        except Exception:
            pass

        tag = 'ltx_draft_' + sid
        json.dump(g, open(os.path.join(BASE, 'logs', 'i2v_ltx_draft', 'graph_' + tag + '.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        t0 = time.time()
        rec = {
            'id': sid, 'duration_audio': dur, 'frames': f, 'first_frame': src_img,
            'audio_wav': wav, 'graph_patch': 'LoadAudio+LTXVAudioVAEEncode', 'tier': 'ltx23_480x832_draft',
        }
        try:
            resp = json.loads(m.http('/prompt', {'prompt': g, 'client_id': 'sc-' + sid}).decode())
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
                try:
                    rec['messages'] = entry.get('status', {}).get('messages')
                except Exception:
                    pass
            cand = []
            for root, _, fs in os.walk(os.path.join(SCR, 'out')):
                for fn in fs:
                    if (fn.startswith(sid + '_') or ('/' + sid) in ('/' + fn) or fn.startswith(sid)) and fn.lower().endswith(('.mp4', '.webm', '.mov')):
                        if sid in fn:
                            cand.append(os.path.join(root, fn))
            # Prefer SaveVideo prefix match i2v-space-cat-draft/sid
            if not cand:
                for root, _, fs in os.walk(os.path.join(SCR, 'out')):
                    for fn in fs:
                        if sid in fn and fn.lower().endswith(('.mp4', '.webm', '.mov')):
                            cand.append(os.path.join(root, fn))
            if cand and rec['ok']:
                latest = max(cand, key=os.path.getmtime)
                raw = os.path.join(CLIPS, sid + '_raw_comfy.mp4')
                shutil.copy2(latest, raw)
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
        ok_n = sum(1 for r in records if r.get('ok'))
        write_status(
            '进行中 %s 完成 ok=%s 累计成功 %d/51' % (sid, rec.get('ok'), ok_n),
            [
                '当前镜：%s 耗时 %.0fs frames=%d' % (sid, rec.get('elapsed_s', 0), f),
                '监控：Get-Content -Tail 40 "%s"' % m.LOGF,
                '结果：%s' % m.RESF,
                '成片目录：%s' % CLIPS,
                '未 finalize；未启动 H3',
            ],
        )
        m.log('%s done ok=%s %.0fs cumulative_ok=%d' % (sid, rec.get('ok'), rec['elapsed_s'], ok_n))
        if not rec.get('ok'):
            break
    return records


if __name__ == '__main__':
    try:
        write_status('启动中：准备抢锁并拉起 portable ComfyUI（8191）')
        waited = acquire_lock()
        write_status('已抢到 gpu.lock，正在启动 ComfyUI portable', ['等待秒数：%d' % waited, 'owner：' + OWNER])
        m.start_comfy('portable', 'space-cat-ltx-draft')
        write_status('ComfyUI 已就绪，开始 51 镜 LTX-2.3 draft 批跑')
        recs = run_batch()
        ok_n = sum(1 for r in recs if r.get('ok'))
        fail = [r for r in recs if not r.get('ok')]
        write_status(
            '批跑结束 成功 %d/51' % ok_n,
            [
                '失败：' + (', '.join(r['id'] + ':' + str(r.get('error') or r.get('status'))[:80] for r in fail) if fail else '无'),
                '成片：' + CLIPS,
                '未 finalize；未启动 H3',
            ],
        )
        m.log('BATCH FINISH ok=%d/51' % ok_n)
    finally:
        try:
            m.stop_comfy()
        except Exception as e:
            m.log('stop_comfy err %s' % e)
        try:
            m.release_lock()
        except Exception as e:
            try:
                if os.path.exists(m.LOCK):
                    h = json.load(open(m.LOCK, encoding='utf-8'))
                    if h.get('owner') == OWNER:
                        os.remove(m.LOCK)
                        m.log('gpu.lock force-released for %s' % OWNER)
            except Exception as e2:
                m.log('lock release fallback err %s / %s' % (e, e2))