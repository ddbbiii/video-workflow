"""Local FunASR (seaco paraformer large + fsmn vad, CPU) char-level timestamps. Timing only; text is never used for display.
usage: asr_run.py full <wav16k> <out.json> | asr_run.py windows <wav16k> <windows.json> <out.json>"""
import json, sys, time
import numpy as np, soundfile as sf
from funasr import AutoModel
H = r'C:\Users\10060\.cache\modelscope\hub\iic'
ASR = H + r'\speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch'
VAD = H + r'\speech_fsmn_vad_zh-cn-16k-common-pytorch'
def toks(r):
    t = r.get('text', ''); ts = r.get('timestamp', []) or []
    ch = t.split() if ' ' in t.strip() else list(t.replace(' ', ''))
    if len(ch) != len(ts):  # fall back: drop non-CJK / align lengths
        ch = [c for c in t if not c.isspace()]
    n = min(len(ch), len(ts))
    return [dict(c=ch[i], s=ts[i][0] / 1000, e=ts[i][1] / 1000) for i in range(n)], len(ch), len(ts)
mode = sys.argv[1]
if mode == 'full':
    m = AutoModel(model=ASR, vad_model=VAD, device='cpu', disable_update=True, log_level='ERROR')
    t = time.time(); res = m.generate(input=sys.argv[2], batch_size_s=300)
    out = []; info = []
    for r in res:
        tk, a, b = toks(r); out += tk; info.append(dict(chars=a, stamps=b))
    json.dump(dict(model=ASR, vad=VAD, seconds=round(time.time() - t, 1), info=info, tokens=out), open(sys.argv[3], 'w', encoding='utf-8'), ensure_ascii=False)
    print('tokens', len(out), 'sec', round(time.time() - t, 1))
else:
    m = AutoModel(model=ASR, device='cpu', disable_update=True, log_level='ERROR')
    x, sr = sf.read(sys.argv[2], dtype='float32'); W = json.load(open(sys.argv[3], encoding='utf-8')); out = []
    for w in W:
        a, b = int(w['t0'] * sr), int(w['t1'] * sr)
        r = m.generate(input=x[a:b], batch_size_s=300)
        tk = []
        for rr in r: tk += toks(rr)[0]
        for k in tk: k['s'] += w['t0']; k['e'] += w['t0']
        out.append(dict(w, tokens=tk))
    json.dump(out, open(sys.argv[4], 'w', encoding='utf-8'), ensure_ascii=False); print('windows', len(out))
