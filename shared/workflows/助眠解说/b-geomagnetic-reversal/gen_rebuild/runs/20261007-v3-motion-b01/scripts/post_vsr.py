"""Background orchestrator (CPU only): wait VSR job -> assemble I2V -> final_r2 -> stitch body -> film QA -> preview + samples.
Writes PROGRESS.md in the batch dir at every step. Re-runnable: each stage skips if its output already exists. Never overwrites."""
import json, subprocess, sys, time, shutil, os
from pathlib import Path
HERE = Path(__file__).resolve().parent; RUN = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\video\clips')  # 2026-10-08 迁移：原批次 20261007-v3-motion-b01 根目录，现为单集 video\clips
P = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal')
PY = sys.executable; FF = shutil.which('ffmpeg'); FP = shutil.which('ffprobe')
REQ = Path(r'E:\program\1project\video\shared\gpu-queue\requests\zhumian-geomag-v3-vsr-i2v-20261007.json')
OUT = P / 'video' / 'source'; FILM = OUT / 'geomag_v3_body_r1.mp4'
OLD = P / 'archive' / 'edit' / 'draft_dof_vo_v4' / 'ch1-6_dof_vo_v4.mp4'
UH = Path(r'C:\Users\10060'); PREV = UH / 'geomag_v3_final_r1_preview_960x540.mp4'; SAMP = UH / 'geomag_stage' / 'samples_i2v'
LOGF = RUN / 'logs' / 'post_vsr.log'
steps = []
def prog(stage, nxt, extra=''):
    t = time.strftime('%Y-%m-%d %H:%M:%S')
    steps.append(f'- {t} {stage}')
    txt = ['# PROGRESS — geomag v3 动态/成片（自动更新，UTC+8）', '', f'- 当前阶段：{stage}', f'- 下一步：{nxt}', f'- 更新时间：{t}', '']
    if extra: txt += [extra, '']
    txt += ['## 已完成步骤', ''] + steps
    (RUN / 'PROGRESS.md').write_text('\n'.join(txt) + '\n', encoding='utf-8')
def sh(cmd, **kw):
    with open(LOGF, 'a', encoding='utf-8') as lf:
        lf.write(time.strftime('[%H:%M:%S] ') + ' '.join(map(str, cmd)) + '\n'); lf.flush()
        return subprocess.run(list(map(str, cmd)), stdout=lf, stderr=subprocess.STDOUT, **kw).returncode
def vsr_status():
    try: return json.loads(REQ.read_text(encoding='utf-8-sig'))['status']
    except Exception: return '?'
# 1) wait for VSR job
while vsr_status() in ('granted', 'running'):
    b = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\archive\gen_rebuild\runs\20261007-v3-motion-b01') / 'vsr' / 'vsr_batch.json'; done = [x['shot'] for x in json.loads(b.read_text(encoding='utf-8'))] if b.exists() else []
    prog('VSR 整批运行中（GPU）', '等 VSR 结束后自动组装 I2V', 'VSR 已完成：' + ('、'.join(done) or '无')); time.sleep(60)
b = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\archive\gen_rebuild\runs\20261007-v3-motion-b01') / 'vsr' / 'vsr_batch.json'; vb = json.loads(b.read_text(encoding='utf-8')) if b.exists() else []
prog('VSR 结束：请求状态 %s；%s' % (vsr_status(), '，'.join('%s exit %s' % (x['shot'], x['exit']) for x in vb)), '组装 I2V')
# 2) assemble I2V (passed shots only; VSR if exit0 else Lanczos)
asm = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\archive\gen_rebuild\runs\20261007-v3-motion-b01') / 'i2v' / 'assembled' / 'i2v_assemble.json'
if not asm.exists():
    keep = [s for s, v in json.loads((RUN / 'qa' / 'i2v_qa.json').read_text(encoding='utf-8')).items() if v['verdict'] in ('pass', 'note')]
    rc = sh([PY, HERE / 'assemble_i2v.py', *keep], cwd=str(HERE))
    if rc: prog('I2V 组装失败 exit %s' % rc, '人工检查 logs/post_vsr.log'); sys.exit(1)
prog('I2V 组装完成', '生成 final_r2')
# 3) final_r2
if not (RUN / 'MOTION_SELECTED_final_r2.md').exists():
    rc = sh([PY, HERE / 'make_final.py', 'final_r2'], cwd=str(HERE))
    if rc: prog('final_r2 失败 exit %s' % rc, '人工检查'); sys.exit(1)
prog('final_r2 完成（63 镜）', '拼接正文（CPU，约 30–60 分钟）')
# 4) stitch
if not FILM.exists():
    rc = sh([PY, HERE / 'stitch_r1.py', 'final_r2'], cwd=str(HERE))
    if rc: prog('拼接失败 exit %s' % rc, '人工检查'); sys.exit(1)
prog('拼接完成：%s' % FILM, '成片 QA')
# 5) film QA
def pj(*a): return json.loads(subprocess.run([FP, '-v', 'error', *map(str, a), '-of', 'json'], capture_output=True, text=True).stdout)
qa = {}
f = pj('-show_entries', 'format=duration:stream=index,codec_type,codec_name,width,height,r_frame_rate,duration', FILM)
o = pj('-show_entries', 'format=duration:stream=index,codec_type,duration', OLD)
qa['new'] = f; qa['old'] = o
qa['new_video_frames'] = int(pj('-select_streams', 'v:0', '-count_packets', '-show_entries', 'stream=nb_read_packets', FILM)['streams'][0]['nb_read_packets'])
def amd5(p): return subprocess.run([FF, '-v', 'error', '-i', str(p), '-map', '0:a:0', '-c', 'copy', '-f', 'md5', '-'], capture_output=True, text=True).stdout.strip()
qa['audio_md5_new'] = amd5(FILM); qa['audio_md5_old'] = amd5(OLD); qa['audio_identical_to_v4'] = qa['audio_md5_new'] == qa['audio_md5_old']
bd = subprocess.run([FF, '-hide_banner', '-i', str(FILM), '-vf', 'blackdetect=d=0.25:pic_th=0.98:pix_th=0.08', '-an', '-f', 'null', '-'], capture_output=True, text=True).stderr
qa['blackdetect'] = [l.split('] ', 1)[-1] for l in bd.splitlines() if 'black_start' in l]
dec_err = subprocess.run([FF, '-v', 'error', '-i', str(FILM), '-f', 'null', '-'], capture_output=True, text=True).stderr.strip()
qa['decode_errors'] = dec_err[:2000]
nd = float(f['format']['duration']); od = float(o['format']['duration'])
qa['duration_new'] = nd; qa['duration_old'] = od; qa['duration_diff_s'] = round(nd - od, 3)
qa['pass'] = abs(nd - od) < 0.1 and qa['audio_identical_to_v4'] and not qa['blackdetect'] and not dec_err and qa['new_video_frames'] == 41910
(OUT / 'FILM_QA.json').write_text(json.dumps(qa, ensure_ascii=False, indent=1), encoding='utf-8')
prog('成片 QA：%s（时长 %.3fs vs 旧 %.3fs，音轨与 v4 逐字节一致=%s，黑帧段 %d，解码错误=%s）' % ('通过' if qa['pass'] else '未通过', nd, od, qa['audio_identical_to_v4'], len(qa['blackdetect']), bool(dec_err)), '压预览与样片')
# 6) preview + samples
if not PREV.exists():
    sh([FF, '-v', 'error', '-n', '-i', FILM, '-vf', 'scale=960:540', '-c:v', 'libx264', '-preset', 'medium', '-crf', '28', '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', PREV])
SAMP.mkdir(parents=True, exist_ok=True)
for s in ('ch1-c08', 'ch2-c07', 'ch5-c06', 'ch6-c08'):
    src = RUN / 'final_r2' / f'{s}.mp4'; dst = SAMP / f'geomag_v3_i2v_{s}.mp4'
    if src.exists() and not dst.exists():
        sh([FF, '-v', 'error', '-n', '-i', src, '-t', '8', '-vf', 'scale=960:540', '-c:v', 'libx264', '-crf', '26', '-an', '-pix_fmt', 'yuv420p', dst])
prog('全部完成：预览 %s；样片 %s' % (PREV, SAMP), '父会话：CopyToBox 预览与样片、追加 PROJECT_STATE、报告')
