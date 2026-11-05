"""Pick one final motion clip per shot -> final/<shot>.mp4 (copy, never overwrite) + final/final_manifest.json + MOTION_SELECTED.md.
Priority: I2V assembled clip with QA verdict pass/note -> affine on ESRGAN input -> affine on cleaned-v2 input -> affine all_v1."""
import json, shutil, subprocess, sys, hashlib
from pathlib import Path
RUN = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\video\clips')  # 2026-10-08 迁移：原批次 20261007-v3-motion-b01 根目录，现为单集 video\clips
plan = json.loads((RUN / 'motion_plan.json').read_text(encoding='utf-8'))
def J(p, d):
    p = RUN / p
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else d
i2v_qa = J('qa/i2v_qa.json', {})               # {shot: {verdict: pass|note|reject, notes: ...}}
asm = {a['shot']: a for a in J('i2v/assembled/i2v_assemble.json', [])}
vsr = {v['shot']: v for v in J('vsr/vsr_batch.json', [])}
esr_aff = {q['shot']: q for q in J('qa/affine_qa_esrgan_v1.json', []) if q['ok']}
v2_aff = {q['shot']: q for q in J('qa/affine_qa_cleanv2_v1.json', []) if q['ok']}
all_aff = {q['shot']: q for q in J('qa/affine_qa_all_v1.json', []) if q['ok']}
FD = sys.argv[1] if len(sys.argv) > 1 else 'final'   # later rounds: final_r2 ...
SEL = 'MOTION_SELECTED.md' if FD == 'final' else 'MOTION_SELECTED_%s.md' % FD
if (RUN / SEL).exists(): sys.exit('refuse to overwrite ' + SEL)
out = RUN / FD; out.mkdir(exist_ok=True)
def probe(p):
    r = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries', 'stream=width,height,r_frame_rate,nb_read_packets', '-of', 'json', str(p)], capture_output=True, text=True).stdout)['streams'][0]
    return int(r['nb_read_packets']), r['width'], r['height'], r['r_frame_rate']
rows = []
for p in plan:
    s = p['shot']; q = i2v_qa.get(s, {}); a = asm.get(s)
    if p['method'] == 'i2v' and a and a.get('decode_ok') and q.get('verdict') in ('pass', 'note'):
        src = Path(a['output']); meth = 'I2V LTX-2.3 + 循环(%s) + 轻推近' % p['loop_mode']
        sr = a['source_kind'] if a['source_kind'].startswith('VSR') else 'Lanczos 放大（VSR 未完成/未通过）'
        qa = 'I2V %s：%s' % (q['verdict'], q.get('notes', ''))
    else:
        if s in esr_aff: src = Path(esr_aff[s]['file']); sr = 'RealESRGAN x4 静帧'
        elif s in v2_aff: src = Path(v2_aff[s]['file']); sr = ('无（RealESRGAN 候选，队列未放行，原图推拉）；' if p['realesrgan_candidate'] else '无；') + '输入为去伪字 v2'
        else:
            src = Path(all_aff[s]['file'])
            sr = ('无（RealESRGAN 候选，队列未放行，原图推拉）' if p['realesrgan_candidate'] else '无') + ('；输入为去伪字 v1' if p['cleaned_input'] else '')
        meth = '推拉 affine：%s %s' % ({'in': '推近', 'out': '拉远', 'pan_r': '右移', 'pan_l': '左移'}[p['motion']], p['affine_magnitude'])
        if p['method'] == 'i2v':
            why = q.get('notes') if q.get('verdict') == 'reject' else 'I2V 未运行（GPU 队列未放行）'
            meth += '（原计划 I2V，退回：%s）' % why
        qa = '帧数/尺寸校验 OK，首中尾帧目检 OK'
    dst = out / (s + '.mp4')
    if dst.exists(): sys.exit('refuse to overwrite ' + str(dst))
    shutil.copy2(src, dst)
    n, w, h, fr = probe(dst)
    ok = n == p['frames_30fps'] and (w, h, fr) == (1920, 1080, '30/1')
    rows.append(dict(shot=s, file=str(dst), source=str(src), method=meth, duration_s=round(n / 30, 3), frames=n, expected_frames=p['frames_30fps'],
                     superres_vsr=sr, qa=qa + ('' if ok else '；帧数/规格不符！'), ok=ok))
(out / 'final_manifest.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding='utf-8')
L = ['# MOTION_SELECTED — 《地球的磁场会翻转》 v3 动态阶段', '', '每镜一条最终动态片段（1920x1080@30，H.264），时长 = 旧口播时间轴 draft_dof_vo_v4 对应镜头时长（30fps 取整帧）。',
     '文件位于本批次 `' + FD + '/<镜头>.mp4`（从下列来源复制，来源保留）。未做拼接、未加标注层、未补帧。', '',
     '| 镜头 | 文件 | 方法 | 时长 s | 超分/VSR | QA |', '|---|---|---|---|---|---|']
for r in rows:
    L.append('| %s | `%s/%s.mp4` | %s | %.3f | %s | %s |' % (r['shot'], FD, r['shot'], r['method'], r['duration_s'], r['superres_vsr'], r['qa']))
pend = [r['shot'] for r in rows if 'I2V 未运行' in r['method']]; esp = [r['shot'] for r in rows if '队列未放行' in r['superres_vsr']]
if pend or esp:
    L[2:2] = ['> 状态：暂定版。GPU 队列请求未获 granted：原计划 I2V 的 %d 镜（%s）暂用同参数推拉；RealESRGAN 候选 %d 镜暂用原图推拉。放行并完成后另出 final_r2/，本目录不覆盖。' % (len(pend), '、'.join(pend), len(esp)), '']
L += ['', '合计 %d 镜，%.1f s；规格全部 OK：%s' % (len(rows), sum(r['duration_s'] for r in rows), all(r['ok'] for r in rows))]
(RUN / SEL).write_text('\n'.join(L) + '\n', encoding='utf-8')
print(len(rows), 'ok', sum(r['ok'] for r in rows), 'i2v', sum(1 for r in rows if r['method'].startswith('I2V')))
