# a-space-cat H3 key-shot upgrade. Adapted from run_a_space_cat_i2v_ltx_draft.py + i2v_cmp.g_h3.
# Authority: PRODUCTION-MOTION-ROUTING.md (关键动态 -> MiniMax H3 @8189); H3-HYBRID-OPS.md draft defaults.
# Only KEY_SHOTS; remaining clips stay clips_v6_ltx_draft. Does NOT finalize.
# Outputs -> clips_v6_h3\ (mux final VO, discard H3 baked audio).
import sys, os, json, time, shutil, wave, subprocess
sys.path.insert(0, r'C:\Users\10060\AppData\Local\Temp')
import i2v_cmp as m

BASE = r'E:\program\1project\video\projects\创意\episodes\a-space-cat'
SCR = os.path.join(BASE, 'archive', 'i2v_raw', 'h3_key')
m.SCR = SCR
for d in ('in', 'out', 'logs', 'temp'):
    os.makedirs(os.path.join(SCR, d), exist_ok=True)
m.LOGF = os.path.join(BASE, 'logs', 'i2v_h3_key', 'a_space_cat_h3_key.log')
m.RESF = os.path.join(BASE, 'qa', 'i2v_h3_key', 'results_h3_key.json')

# Face / climax key shots (no doc list — narrative peaks + face-visible; prefer <=~5.2s for single H3 window)
KEY_SHOTS = ['s01', 's09', 's13', 's25', 's30', 's35', 's42', 's48', 's51']

OWNER = 'i2v:a-space-cat_h3'
CLIPS = os.path.join(BASE, 'video', 'clips', 'h3')
FF_DIR = os.path.join(BASE, 'image', 'firstframes')
AUDIO_DIR = os.path.join(BASE, 'audio', 'vo_v6_final')
SHOTLIST = os.path.join(BASE, 'storyboard', 'shotlist_v6.json')
STATUS = os.path.join(BASE, 'logs', 'i2v_h3_key_status.txt')
os.makedirs(CLIPS, exist_ok=True)
os.makedirs(os.path.join(BASE, 'logs'), exist_ok=True)

# Vertical 480p fallback from i2v_cmp PLAN (16GB safe); EasyCache ON inside g_h3
H3_W, H3_H, H3_STEPS = 480, 864, 20
H3_MAX_FRAMES = 124  # H3-SEGMENT-PLAYBOOK short window


def write_status(msg, extra=None):
    lines = [
        '# a-space-cat MiniMax H3 key-shot 状态',
        '',
        '更新时间：' + time.strftime('%Y-%m-%d %H:%M:%S') + '（UTC+8）',
        '锁所有者：' + OWNER,
        '锁路径：' + m.LOCK,
        '输出目录：' + CLIPS,
        '工作目录：' + SCR,
        '结果 JSON：' + m.RESF,
        '日志：' + m.LOGF,
        '模型：MiniMax H3 I2V（%dx%d，steps=%d，EasyCache ON，seed 42）；关键镜 %s' % (H3_W, H3_H, H3_STEPS, ','.join(KEY_SHOTS)),
        '音频：丢弃 H3 生成音，mux 最终 VO',
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
        purpose='minimax-h3 key shots ' + ','.join(KEY_SHOTS),
    )
    json.dump(payload, open(m.LOCK, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    m.log('gpu.lock acquired for %s (waited %ds)' % (OWNER, waited))
    return waited


def mux_vo(src_mp4, wav, dst_mp4, dur):
    # Pad/trim video to VO length: if H3 shorter, tpad freeze last frame; then mux VO
    tmp = dst_mp4 + '.tmp.mp4'
    cmd = [
        'ffmpeg', '-y', '-i', src_mp4, '-i', wav,
        '-filter_complex',
        '[0:v]fps=24,scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:(ow-iw)/2:(oh-ih)/2,setsar=1,tpad=stop_mode=clone:stop_duration=30[v]' % (H3_W, H3_H, H3_W, H3_H),
        '-map', '[v]', '-map', '1:a:0',
        '-t', '%.3f' % dur,
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
        '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '1',
        '-shortest', dst_mp4,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError('ffmpeg mux failed: ' + (r.stderr or '')[-800:])


def frames_for(dur):
    # Match VO @24fps but cap at H3 short window; keep odd-ish length near 8k+1 style when possible
    f = max(25, int(round(dur * 24)))
    f = min(f, H3_MAX_FRAMES)
    return f


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

    for sid in KEY_SHOTS:
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
        f = frames_for(dur)

        n = int(sid[1:])
        src_img = os.path.join(FF_DIR, by[sid].get('firstframe') or ('shot%02d.png' % n))
        if not os.path.exists(src_img):
            raise RuntimeError('missing firstframe ' + src_img)
        dst_img = os.path.join(SCR, 'in', sid + '.png')
        shutil.copy2(src_img, dst_img)
        m.IMAGE = sid + '.png'

        text_zh = by[sid].get('text') or ''
        motion = (
            'subtle natural cinematic micro-motion of a silver-gradient British Shorthair cat, '
            'soft breathing, gentle fur movement, restrained camera drift, emotional storytelling beat'
        )
        m.PROMPT = (
            'Cinematic realistic vertical 9:16 film of a silver-gradient British Shorthair cat in a space / science what-if scene. '
            + motion
            + '. Narrative beat (for motion mood only, do not render text): '
            + text_zh
            + '. Preserve the exact first-frame cat identity, face, fur color and pattern, costume/props, lighting and background. '
              'Smooth restrained motion, no scene change, no text, no subtitles.'
        )

        g = m.g_h3(H3_W, H3_H, f, H3_STEPS, 'i2v-space-cat-h3/' + sid)
        # Replace candle audio cue baked into g_h3
        g['5']['inputs']['prompt'] = (
            'The scene from <Picture 1>. ' + m.PROMPT
            + ' Audio: quiet spacecraft cabin ambience, soft cat breathing, no music, no speech.'
        )

        try:
            m.http('/free', {'unload_models': False, 'free_memory': True})
            time.sleep(1)
        except Exception:
            pass

        tag = 'h3_key_' + sid
        json.dump(g, open(os.path.join(BASE, 'logs', 'i2v_h3_key', 'graph_' + tag + '.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        t0 = time.time()
        rec = {
            'id': sid, 'duration_audio': dur, 'frames': f, 'first_frame': src_img,
            'audio_wav': wav, 'tier': 'h3_480x864_key', 'w': H3_W, 'h': H3_H, 'steps': H3_STEPS,
        }
        try:
            resp = json.loads(m.http('/prompt', {'prompt': g, 'client_id': 'sc-h3-' + sid}).decode())
            pid = resp['prompt_id']
            m.log('%s queued %s dur=%.2f f=%d' % (sid, pid, dur, f))
            entry = None
            while True:
                time.sleep(10)
                if m.PROC.poll() is not None:
                    raise RuntimeError('comfy died')
                hist = m.jget('/history/' + pid, timeout=30)
                if pid in hist:
                    entry = hist[pid]
                    break
                if time.time() - t0 > 5400:
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
        ok_n = sum(1 for r in records if r.get('ok') and r.get('id') in KEY_SHOTS)
        write_status(
            '进行中 %s 完成 ok=%s 累计成功 %d/%d' % (sid, rec.get('ok'), ok_n, len(KEY_SHOTS)),
            [
                '当前镜：%s 耗时 %.0fs frames=%d' % (sid, rec.get('elapsed_s', 0), f),
                '监控：Get-Content -Tail 40 "%s"' % m.LOGF,
                '结果：%s' % m.RESF,
                '成片目录：%s' % CLIPS,
            ],
        )
        m.log('%s done ok=%s %.0fs cumulative_ok=%d/%d' % (sid, rec.get('ok'), rec['elapsed_s'], ok_n, len(KEY_SHOTS)))
        if not rec.get('ok'):
            break
    return records


if __name__ == '__main__':
    try:
        write_status('启动中：准备抢锁并拉起 H3 ComfyUI（8189）')
        waited = acquire_lock()
        write_status('已抢到 gpu.lock，正在启动 H3 ComfyUI', ['等待秒数：%d' % waited, 'owner：' + OWNER])
        m.start_comfy('h3', 'space-cat-h3-key')
        write_status('ComfyUI H3 已就绪，开始关键镜批跑', ['关键镜：' + ','.join(KEY_SHOTS)])
        recs = run_batch()
        ok_n = sum(1 for r in recs if r.get('ok') and r.get('id') in KEY_SHOTS)
        fail = [r for r in recs if r.get('id') in KEY_SHOTS and not r.get('ok')]
        write_status(
            '批跑结束 成功 %d/%d' % (ok_n, len(KEY_SHOTS)),
            [
                '失败：' + (', '.join(r['id'] + ':' + str(r.get('error') or r.get('status'))[:80] for r in fail) if fail else '无'),
                '成片：' + CLIPS,
                '下一步：finalize_a_space_cat_v6.py',
            ],
        )
        m.log('BATCH FINISH ok=%d/%d' % (ok_n, len(KEY_SHOTS)))
        # exit code 0 only if all key shots ok
        sys.exit(0 if ok_n == len(KEY_SHOTS) and not fail else 2)
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
