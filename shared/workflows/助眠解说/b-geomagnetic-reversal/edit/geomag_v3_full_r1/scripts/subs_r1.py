"""Subtitles r1 (style_r4, rules/助眠解说/subtitles.md): FunASR char timestamps (CPU) for the new intro lines and new c06b;
old body cues reused; cues after c06b shifted by the splice delta; full = intro + body + intro length."""
import json, re, difflib, subprocess, sys
from pathlib import Path
import numpy as np, soundfile as sf
from PIL import ImageFont
P = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal')  # 2026-10-08 迁移：原 legacy-source\zhumian\b-geomagnetic-reversal，现为单集目录
C06 = P/'video'/'clips'/'full_r1_c06b'; S = P/'audio'/'subtitles'/'full_r1'; T = Path(r'E:\program\1project\video\shared\work\scratch\zhumian-geomag-full_r1-tmp'); T.mkdir(parents=True, exist_ok=True)
R4 = P/'audio'/'subtitles'/'style_r4'/'geomag_v3_body_r1-subtitles-style_r4.ass'
sp = json.loads((C06/'splice.json').read_text(encoding='utf-8')); im = json.loads((P/'video'/'intro'/'full_r1_src'/'intro_manifest_partial.json').read_text(encoding='utf-8'))
TI = im['intro_s']; DELTA = sp['delta_s']; OB = sp['c06b_old_start_s']; OC = sp['c07_old_start_s']
FONT = ImageFont.truetype(str(Path(r'E:\program\1project\video\assets\助眠解说\subtitles\style-r4\fonts')/'SourceHanSansSC-Heavy.otf'), 66)  # libass em = 96/1.448
def width(t):
    b = FONT.getbbox(t, stroke_width=5); return (b[2]-b[0])
PUN = '，。！？、；：,.!?;:'
from funasr import AutoModel
m = AutoModel(model='iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch', disable_update=True)
def asr(x, sr, tag):
    p = T/f'asr_{tag}.wav'
    if sr != 16000:
        sf.write(str(T/f'asr_{tag}_src.wav'), x, sr); subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(T/f'asr_{tag}_src.wav'), '-ar', '16000', '-ac', '1', str(p)], check=True)
    else: sf.write(str(p), x, sr)
    r = m.generate(input=str(p))[0]; toks = r['text'].replace(' ', ''); ts = r.get('timestamp', [])
    chars = [c for c in toks]; 
    if len(ts) != len(chars):  # fall back: token split by spaces
        chars = r['text'].split()
    return chars, [(a/1000, b/1000) for a, b in ts], r['text']
def align(text, chars, ts, off):
    core = [c for c in text if c not in PUN]; hyp = ''.join(chars)
    sm = difflib.SequenceMatcher(None, ''.join(core), hyp, autojunk=False); tm = [None]*len(core)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n): tm[a+k] = (ts[b+k][0]+off, ts[b+k][1]+off)
    for i in range(len(tm)):  # interpolate few gaps
        if tm[i] is None:
            prv = next((tm[j] for j in range(i-1, -1, -1) if tm[j]), None); nxt = next((tm[j] for j in range(i+1, len(tm)) if tm[j]), None)
            tm[i] = (prv[1] if prv else nxt[0], nxt[0] if nxt else prv[1])
    return core, tm, sum(1 for a, b, n in sm.get_matching_blocks() for _ in range(n))
def cues_for(text, tm):
    parts = [text.rstrip(PUN)]
    if width(parts[0]) > 1728: parts = [p for p in re.split('[，、；：]', text.rstrip(PUN)) if p]
    out = []; k = 0
    for p in parts:
        n = sum(1 for c in p if c not in PUN); out.append([tm[k][0], tm[k+n-1][1], p]); k += n
    return out
rep = dict(asr={}, widths={})
# intro: per-sentence ASR on paced segments
icues = []
for i, (tag, line) in enumerate(zip(['i01', 'i02', 'i03'], im['lines'])):
    x, sr = sf.read(str(T/f'intro_{tag}_paced.wav')); s0 = im['sentence_times'][i][0]
    ch, ts, raw = asr(x, sr, f'intro_{tag}'); core, tm, hit = align(line, ch, ts, s0)
    rep['asr'][tag] = dict(hyp=raw, matched=hit, total=len(core)); icues += cues_for(line, tm)
# c06b in new body narration
nb, sr = sf.read(str(C06/'body_narration_r1.wav')); w0 = OB - 0.2; w1 = OB + sp['slot_new_s'] + 0.2
ch, ts, raw = asr(nb[int(w0*sr):int(w1*sr)].mean(1), sr, 'c06b'); L06 = '我们从六个问题，慢慢走近这个谜'
core, tm, hit = align(L06, ch, ts, w0); rep['asr']['c06b'] = dict(hyp=raw, matched=hit, total=len(core)); c06 = cues_for(L06, tm)
# verify old line gone: ASR wide window c06a end .. c07 head
v0, v1 = OB - 3.0, OB + sp['slot_new_s'] + 3.0; ch2, ts2, raw2 = asr(nb[int(v0*sr):int(v1*sr)].mean(1), sr, 'verify')
rep['verify_window_s'] = [v0, v1]; rep['verify_hyp'] = raw2; rep['old_phrase_absent'] = ('三十' not in raw2.replace(' ', '') and '拆开' not in raw2.replace(' ', ''))
# old body cues
def tsec(s): h, mm, ss = s.split(':'); return int(h)*3600 + int(mm)*60 + float(ss)
lines = R4.read_text(encoding='utf-8-sig').splitlines(); hdr = []; body = []
for l in lines:
    if l.startswith('Dialogue:'):
        f = l.split(',', 9); body.append([tsec(f[1]), tsec(f[2]), f[9]])
    elif not body: hdr.append(l)
removed = [c for c in body if OB <= c[0] < OC]; keep = [c for c in body if not (OB <= c[0] < OC)]
nbody = []
for c in keep:
    if c[0] >= OC: nbody.append([c[0]+DELTA, c[1]+DELTA, c[2]])
    else: nbody.append(list(c))
nbody += [[a, b, t] for a, b, t in c06]; nbody.sort(key=lambda c: c[0])
def finish(cs):  # end = last char + 0.3, <= next start - 0.04, min 0.7 (not overlapping)
    out = []
    for i, (a, b, t) in enumerate(cs):
        e = b
        if i+1 < len(cs): e = min(e, cs[i+1][0] - 0.04)
        out.append([a, e, t])
    return out
icues = finish([[a, b+0.3, t] for a, b, t in icues]); icues[-1][1] = min(icues[-1][1], TI)
new_c06 = set(t for _, _, t in c06)
nbody = [[a, (b+0.3 if t in new_c06 else b), t] for a, b, t in nbody]; nbody = finish(nbody)
full = [[a, b, t] for a, b, t in icues] + [[a+TI, b+TI, t] for a, b, t in nbody]
for a, b, t in icues + [c for c in nbody if c[2] in new_c06]: rep['widths'][t] = width(t)
def ta(x): h = int(x//3600); mm = int(x % 3600//60); s = x % 60; return '%d:%02d:%05.2f' % (h, mm, s)
def ts_(x): x = max(0, x); h = int(x//3600); mm = int(x % 3600//60); s = x % 60; return ('%02d:%02d:%06.3f' % (h, mm, s)).replace('.', ',')
H = '\n'.join(hdr).rstrip() + '\n'
def write(name, cs):
    for ext in ('ass', 'srt'):
        p = S/f'{name}.{ext}'
        assert not p.exists(), p
    (S/f'{name}.ass').write_text(H + ''.join('Dialogue: 0,%s,%s,B,,0,0,0,,%s\n' % (ta(a), ta(b), t) for a, b, t in cs), encoding='utf-8-sig')
    (S/f'{name}.srt').write_text(''.join('%d\n%s --> %s\n%s\n\n' % (i+1, ts_(a), ts_(b), t) for i, (a, b, t) in enumerate(cs)), encoding='utf-8')
write('geomag_full_r1_intro', icues); write('geomag_full_r1_body', nbody); write('geomag_full_r1', full)
rep.update(intro_cues=icues, c06b_cues=c06, removed_old_cues=removed, kept_before=[c for c in nbody if c[0] < OB][-1:],
           first_shifted=[c for c in nbody if c[0] >= OC + DELTA][:2], delta_s=DELTA, intro_s=TI, n_full=len(full), n_body=len(nbody), n_old_body=len(body),
           max_width_new=max(rep['widths'].values()), overlaps=sum(1 for i in range(len(full)-1) if full[i][1] > full[i+1][0]+1e-6))
(S/'subs_report.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8'); print(json.dumps(rep, ensure_ascii=False, indent=1))