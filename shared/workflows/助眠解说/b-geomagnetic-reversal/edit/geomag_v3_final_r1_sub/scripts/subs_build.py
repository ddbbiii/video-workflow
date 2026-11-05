"""Burned-subtitle derivative of geomag_v3_body_r1 (CPU only, local FunASR timing + locked script text).
Rules: rules/shared/audio/voice-and-subtitles.md (2026-10-07 22:32) + video-workflow.md §K/L.
Stages are skip-if-done; writes PROGRESS.md in OUT. Never overwrites existing deliverables."""
import json, re, subprocess, sys, time, shutil, hashlib, difflib, random
from pathlib import Path
P = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal')  # 2026-10-08 迁移：原 legacy-source\zhumian\b-geomagnetic-reversal，现为单集目录
BODY = P / 'video' / 'source' / 'geomag_v3_body_r1.mp4'
OUT = P / 'audio' / 'subtitles' / 'body_r1'; W = OUT / 'work'; W.mkdir(parents=True, exist_ok=True)
VPY = r'E:\program\1project\video\shared\runtime\engines\tts\voxcpm\.venv\Scripts\python.exe'
HERE = Path(__file__).resolve().parent
FF = shutil.which('ffmpeg'); FP = shutil.which('ffprobe')
NAME = 'geomag_v3_body_r1'
SRT = OUT / f'{NAME}-subtitles.srt'; ASS = OUT / f'{NAME}-subtitles.ass'; BURN = OUT / f'{NAME}-burned-subtitles.mp4'
UH = Path(r'C:\Users\10060\geomag_v3_sub_out'); PREV = UH / f'{NAME}-burned-subtitles-preview-960x540.mp4'
MAXC = 22
STYLE = dict(font='Microsoft YaHei', size=48, primary='&H00E6F0FA', box='&H99101010', outline_pad=14, marginv=86)
steps = []
def prog(stage, nxt, extra=''):
    t = time.strftime('%Y-%m-%d %H:%M:%S'); steps.append(f'- {t} {stage}')
    L = ['# PROGRESS — geomag v3 字幕版（UTC+8，自动更新）', '', f'- 当前阶段：{stage}', f'- 下一步：{nxt}', f'- 更新：{t}', '']
    if extra: L += [extra, '']
    (OUT / 'PROGRESS.md').write_text('\n'.join(L + ['## 已完成', ''] + steps) + '\n', encoding='utf-8'); print(t, stage, flush=True)
def run(cmd, **kw):
    with open(W / 'run.log', 'a', encoding='utf-8') as lf:
        lf.write(time.strftime('[%H:%M:%S] ') + ' '.join(map(str, cmd)) + '\n'); lf.flush()
        return subprocess.run(list(map(str, cmd)), stdout=lf, stderr=subprocess.STDOUT, **kw).returncode
def pj(*a): return json.loads(subprocess.run([FP, '-v', 'error', *map(str, a), '-of', 'json'], capture_output=True, text=True).stdout)
def amd5(p): return subprocess.run([FF, '-v', 'error', '-i', str(p), '-map', '0:a:0', '-c', 'copy', '-f', 'md5', '-'], capture_output=True, text=True).stdout.strip()
# ---- 0/1 audio + ASR ----
wav = W / 'body_audio_16k_mono.wav'; asr = W / 'asr_full.json'
if not wav.exists(): run([FF, '-v', 'error', '-n', '-i', BODY, '-map', '0:a:0', '-ac', '1', '-ar', '16000', wav])
prog('抽取正片音轨（16k 单声道，仅供 ASR 取时间）', '本地 FunASR 全片字级时间戳（CPU）')
if not asr.exists():
    rc = run([VPY, HERE / 'asr_run.py', 'full', wav, asr])
    if rc: prog('ASR 失败 exit %s' % rc, '检查 work/run.log'); sys.exit(1)
A = json.loads(asr.read_text(encoding='utf-8'))
prog('ASR 完成：%d 字，%.0f 秒' % (len(A['tokens']), A['seconds']), '解析锁定文稿并对齐')
# ---- 2 locked script text ----
def sections(md):
    L = md.read_text(encoding='utf-8').splitlines(); out = []; i = 0
    while i < len(L):
        if L[i].startswith('#') and '口播全文' in L[i]:
            j = i + 1; buf = []
            while j < len(L) and not L[j].startswith('#') and not L[j].startswith('---'):
                if L[j].strip(): buf.append(L[j].strip())
                j += 1
            out.append(''.join(buf)); i = j
        else: i += 1
    return out
chaps = sections(P / 'story' / 'script_v4_ch1.md') + sections(P / 'story' / 'script_v4_ch2-6.md')
if len(chaps) != 6: prog('文稿解析得到 %d 章（应为 6）' % len(chaps), '停止'); sys.exit(1)
isw = lambda c: bool(re.match(r'[\u4e00-\u9fffA-Za-z0-9]', c))
END = '。！？；'; MID = '，、：'
cues = []; norm = []
for ci, text in enumerate(chaps, 1):
    sent = ''; sents = []
    for c in text:
        sent += c
        if c in END: sents.append(sent); sent = ''
    if sent.strip(): sents.append(sent)
    for s in sents:
        cl = ''; clauses = []
        for c in s:
            cl += c
            if c in MID: clauses.append(cl); cl = ''
        if cl: clauses.append(cl)
        cur = ''
        def flush(x):
            if not x: return
            idx0 = len(norm)
            for c in x:
                if isw(c): norm.append(c)
            cues.append(dict(ch=ci, raw=x, i0=idx0, i1=len(norm) - 1))
        for c in clauses:
            n = sum(map(isw, cur + c))
            if cur and n > MAXC: flush(cur); cur = c
            else: cur += c
            while sum(map(isw, cur)) > MAXC:  # single overlong clause: split evenly
                k = sum(map(isw, cur)); cut = (k + 1) // 2; m = 0
                for p, ch in enumerate(cur):
                    m += isw(ch)
                    if m == cut: break
                flush(cur[:p + 1]); cur = cur[p + 1:]
        flush(cur)
for q in cues:
    t = q['raw'].strip()
    while t and t[-1] in '，。、；：': t = t[:-1]
    q['text'] = t
# ---- 3 align ----
tok = [t for t in A['tokens'] if isw(t['c'][:1])]
a = ''.join(norm); b = ''.join(t['c'][0] for t in tok)
sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
st = [None] * len(a); en = [None] * len(a); matched = 0
for blk in sm.get_matching_blocks():
    for k in range(blk.size):
        st[blk.a + k] = tok[blk.b + k]['s']; en[blk.a + k] = tok[blk.b + k]['e']; matched += 1
# interpolate gaps
known = [i for i in range(len(a)) if st[i] is not None]
for i in range(len(a)):
    if st[i] is None:
        lo = max([k for k in known if k < i], default=None); hi = min([k for k in known if k > i], default=None)
        if lo is None: st[i] = en[i] = st[hi]
        elif hi is None: st[i] = en[i] = en[lo]
        else:
            f = (i - lo) / (hi - lo); t0 = en[lo]; t1 = st[hi]; st[i] = t0 + (t1 - t0) * f; en[i] = st[i] + max(0.0, (t1 - t0) / (hi - lo))
diffs = []
for op, i1, i2, j1, j2 in sm.get_opcodes():
    if op != 'equal' and max(i2 - i1, j2 - j1) >= 2:
        diffs.append(dict(op=op, script=a[i1:i2], asr=b[j1:j2], t=round(st[i1] if i1 < len(a) else 0, 2)))
for k, q in enumerate(cues):
    q['start'] = st[q['i0']]; q['end_speech'] = en[q['i1']]
for k, q in enumerate(cues):
    nxt = cues[k + 1]['start'] if k + 1 < len(cues) else 1397.0
    e = min(q['end_speech'] + 0.3, nxt - 0.04); e = max(e, q['end_speech'])
    if e - q['start'] < 0.7: e = min(q['start'] + 0.7, nxt - 0.04)
    q['end'] = max(e, q['start'] + 0.2)
align = dict(script_chars=len(a), asr_chars=len(b), matched_chars=matched, match_ratio=round(matched / len(a), 4), cues=len(cues), diffs=diffs)
(W / 'align_report.json').write_text(json.dumps(align, ensure_ascii=False, indent=1), encoding='utf-8')
(W / 'cues.json').write_text(json.dumps(cues, ensure_ascii=False, indent=1), encoding='utf-8')
prog('对齐完成：文稿 %d 字，ASR %d 字，逐字匹配 %.1f%%；%d 条字幕；差异片段 %d 处' % (len(a), len(b), 100 * matched / len(a), len(cues), len(diffs)), '写 SRT/ASS')
# ---- write srt/ass (no overwrite) ----
def ts_srt(t): t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60; return '%02d:%02d:%06.3f' % (h, m, s)
def ts_ass(t): t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60; return '%d:%02d:%05.2f' % (h, m, s)
if not SRT.exists():
    SRT.write_text(''.join('%d\n%s --> %s\n%s\n\n' % (i + 1, ts_srt(q['start']).replace('.', ','), ts_srt(q['end']).replace('.', ','), q['text']) for i, q in enumerate(cues)), encoding='utf-8')
if not ASS.exists():
    S = STYLE
    hdr = ['[Script Info]', 'ScriptType: v4.00+', 'PlayResX: 1920', 'PlayResY: 1080', 'WrapStyle: 2', 'ScaledBorderAndShadow: yes', '',
           '[V4+ Styles]', 'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
           'Style: B,%s,%d,%s,&H000000FF,%s,%s,0,0,0,0,100,100,1,0,3,%d,0,2,120,120,%d,1' % (S['font'], S['size'], S['primary'], S['box'], S['box'], S['outline_pad'], S['marginv']), '',
           '[Events]', 'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
    ev = ['Dialogue: 0,%s,%s,B,,0,0,0,,%s' % (ts_ass(q['start']), ts_ass(q['end']), q['text'].replace('{', '（').replace('}', '）')) for q in cues]
    ASS.write_text('\n'.join(hdr + ev) + '\n', encoding='utf-8-sig')
prog('字幕侧车文件已写：%s / %s' % (SRT.name, ASS.name), '烧录（CPU，约 20–30 分钟）')
# ---- 4 burn ----
if not BURN.exists():
    rc = run([FF, '-v', 'error', '-n', '-i', BODY, '-vf', f'ass={ASS.name}', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-movflags', '+faststart', BURN.name], cwd=str(OUT))
    if rc: prog('烧录失败 exit %s' % rc, '检查 work/run.log'); sys.exit(1)
prog('烧录完成：%s' % BURN.name, '字幕 QA（独立窗口 ASR 抽查 + 规格检查 + 联系表）')
# ---- 5 QA ----
qa = {}
samples = []
for ci in range(1, 7):
    cc = [k for k, q in enumerate(cues) if q['ch'] == ci]
    for tag, k in (('开头', cc[0]), ('中段', cc[len(cc) // 2]), ('结尾', cc[-1])): samples.append((ci, tag, k))
wj = W / 'qa_windows.json'; wo = W / 'qa_windows_asr.json'
if not wo.exists():
    wj.write_text(json.dumps([dict(ch=ci, tag=tag, k=k, t0=max(0, cues[k]['start'] - 1.5), t1=min(1397.0, cues[k]['end_speech'] + 1.5)) for ci, tag, k in samples], ensure_ascii=False), encoding='utf-8')
    rc = run([VPY, HERE / 'asr_run.py', 'windows', wav, wj, wo])
    if rc: prog('QA 窗口 ASR 失败', '检查'); sys.exit(1)
rows = []
for w in json.loads(wo.read_text(encoding='utf-8')):
    q = cues[w['k']]; ct = ''.join(c for c in q['text'] if isw(c)); tk = [t for t in w['tokens'] if isw(t['c'][:1])]
    bb = ''.join(t['c'][0] for t in tk); m2 = difflib.SequenceMatcher(None, ct, bb, autojunk=False); bl = [x for x in m2.get_matching_blocks() if x.size]
    if bl:
        ms = tk[bl[0].b]['s'] - (bl[0].a * 0.25 if bl[0].a else 0); me = tk[bl[-1].b + bl[-1].size - 1]['e']
        rows.append(dict(ch=w['ch'], tag=w['tag'], cue=w['k'] + 1, text=q['text'], cue_start=round(q['start'], 3), measured_start=round(ms, 3), start_err=round(q['start'] - ms, 3),
                         speech_end=round(q['end_speech'], 3), measured_end=round(me, 3), end_err=round(q['end_speech'] - me, 3), match=round(sum(x.size for x in bl) / max(1, len(ct)), 2)))
    else: rows.append(dict(ch=w['ch'], tag=w['tag'], cue=w['k'] + 1, text=q['text'], error='window ASR no match'))
qa['sync_samples'] = rows
errs = [abs(r['start_err']) for r in rows if 'start_err' in r] + [abs(r['end_err']) for r in rows if 'end_err' in r]
qa['max_sync_err_s'] = round(max(errs), 3) if errs else None
joined = ''.join(c for q in cues for c in q['text'] if isw(c))
qa['text_identical_to_script'] = joined == ''.join(norm)
qa['max_line_chars'] = max(sum(map(isw, q['text'])) for q in cues); qa['cue_count'] = len(cues)
qa['overlaps'] = sum(1 for k in range(len(cues) - 1) if cues[k]['end'] > cues[k + 1]['start'])
f = pj('-show_entries', 'format=duration:stream=codec_type,width,height,r_frame_rate,duration', BURN)
qa['burned_probe'] = f; qa['duration_s'] = float(f['format']['duration'])
qa['frames'] = int(pj('-select_streams', 'v:0', '-count_packets', '-show_entries', 'stream=nb_read_packets', BURN)['streams'][0]['nb_read_packets'])
qa['audio_md5_burned'] = amd5(BURN); qa['audio_md5_body'] = amd5(BODY); qa['audio_identical'] = qa['audio_md5_burned'] == qa['audio_md5_body']
qa['body_sha256_first16MB'] = hashlib.sha256(open(BODY, 'rb').read(16 << 20)).hexdigest()
qa['style'] = STYLE; qa['max_chars_per_line'] = MAXC; qa['align'] = {k: v for k, v in align.items() if k != 'diffs'}; qa['align_diff_count'] = len(diffs)
qa['pass'] = (qa['max_sync_err_s'] is not None and qa['max_sync_err_s'] <= 0.3 and qa['text_identical_to_script'] and qa['max_line_chars'] <= MAXC
              and abs(qa['duration_s'] - 1397.0) < 0.05 and qa['audio_identical'] and qa['frames'] == 41910 and qa['overlaps'] == 0)
(OUT / 'SUB_QA.json').write_text(json.dumps(qa, ensure_ascii=False, indent=1), encoding='utf-8')
# contact sheet
from PIL import Image, ImageDraw, ImageFont
fnt = ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc', 22); tiles = []
for r in rows:
    q = cues[r['cue'] - 1]; tm = (q['start'] + q['end_speech']) / 2
    jp = W / ('qa_frame_%03d.jpg' % r['cue'])
    if not jp.exists(): run([FF, '-v', 'error', '-n', '-ss', '%.3f' % tm, '-i', BURN, '-frames:v', '1', '-vf', 'scale=640:360', jp])
    im = Image.open(jp).convert('RGB'); c = Image.new('RGB', (640, 420), (15, 15, 15)); c.paste(im, (0, 0)); d = ImageDraw.Draw(c)
    d.text((6, 364), '第%d章 %s #%d  %.2fs  误差 起%+.2f/止%+.2f' % (r['ch'], r['tag'], r['cue'], tm, r.get('start_err', 9), r.get('end_err', 9)), font=fnt, fill=(255, 220, 90))
    d.text((6, 392), '文稿：' + q['text'], font=fnt, fill=(230, 230, 230)); tiles.append(c)
sheet = Image.new('RGB', (640 * 3, 420 * ((len(tiles) + 2) // 3)), (0, 0, 0))
for i, t in enumerate(tiles): sheet.paste(t, ((i % 3) * 640, (i // 3) * 420))
CS = OUT / f'{NAME}-subtitles-qa-contact.jpg'
if not CS.exists(): sheet.save(CS, quality=88)
prog('字幕 QA：%s（最大同步误差 %.3fs，文字与文稿一致=%s，单行最多 %d 字，时长 %.3fs，音轨一致=%s）' % ('通过' if qa['pass'] else '未通过', qa['max_sync_err_s'] or -1, qa['text_identical_to_script'], qa['max_line_chars'], qa['duration_s'], qa['audio_identical']), '压预览并汇总到 C:\\Users\\10060\\geomag_v3_sub_out')
# ---- 6 preview + copies ----
UH.mkdir(exist_ok=True)
if not PREV.exists():
    run([FF, '-v', 'error', '-n', '-i', BURN, '-vf', 'scale=960:540', '-c:v', 'libx264', '-preset', 'medium', '-b:v', '400k', '-maxrate', '600k', '-bufsize', '1200k', '-c:a', 'aac', '-b:a', '64k', '-movflags', '+faststart', PREV])
for src in (SRT, ASS, CS, OUT / 'SUB_QA.json'):
    d = UH / src.name
    if not d.exists(): shutil.copy2(src, d)
prog('全部完成；预览 %.1f MB' % (PREV.stat().st_size / 1e6), '父会话：CopyToBox、追加 PROJECT_STATE、报告')
