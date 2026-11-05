"""Audio master r1: intro narration (no BGM, intro-node exception) + body narration with SLEEP-BGM-UNIFIED-001 bed.
BGM bed = narration integrated loudness - 10 LU (voice-and-subtitles.md: initial ~50% of narration loudness); seamless loop (3s equal-power xfade, no tempo change).
Final linear gain to -16 LUFS / TP <= -1.5 dBTP (episode chain loudnorm targets, draft_dof_vo_v3/v4)."""
import json, re, subprocess
from pathlib import Path
import numpy as np, soundfile as sf
P = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal')  # 2026-10-08 迁移：原 legacy-source\zhumian\b-geomagnetic-reversal，现为单集目录
A = P/'audio'; T = Path(r'E:\program\1project\video\shared\work\scratch\zhumian-geomag-full_r1-tmp'); T.mkdir(parents=True, exist_ok=True); A.mkdir(exist_ok=True)
BGM = Path(r'E:\program\1project\video\assets\助眠解说\audio\bgm\sleep-unified-v1\leberch-sleep-583079.mp3')
SR = 48000; BGM_LU = -10.0; TARGET_I = -16.0; TP_MAX = -1.5; XF = 3.0; FIN = 2.0; FOUT = 4.0
def dec(p, ch=2):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-f', 'f32le', '-ac', str(ch), '-ar', str(SR), '-'], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).reshape(-1, ch).copy()
def meas(x, tag):
    p = T/f'meas_{tag}.wav'; sf.write(str(p), x, SR, subtype='FLOAT')
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(p), '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True)
    j = json.loads(re.search(r'\{[^{}]*"input_i"[^{}]*\}', r.stderr, re.S).group(0)); return float(j['input_i']), float(j['input_tp'])
nar = dec(P/'video'/'clips'/'full_r1_c06b'/'body_narration_r1.wav'); intro = dec(P/'video'/'intro'/'full_r1_src'/'intro_narration_raw.wav')
nI, nTP = meas(nar, 'body_nar'); iI, iTP = meas(intro, 'intro_raw')
intro *= 10**((nI - iI)/20)
b = dec(BGM); rms = 20*np.log10(np.sqrt(np.convolve(b.mean(1)**2, np.ones(2400)/2400, 'same'))+1e-12)
on = np.where(rms > -50)[0]; b = b[on[0]:on[-1]+1]
bI, _ = meas(b, 'bgm_src')
n = len(nar); xf = int(XF*SR); ang = np.linspace(0, np.pi/2, xf, dtype=np.float32)[:, None]
bed = b.copy(); loops = 1
while len(bed) < n:
    bed = np.concatenate([bed[:-xf], bed[-xf:]*np.cos(ang) + b[:xf]*np.sin(ang), b[xf:]]); loops += 1
bed = bed[:n] * 10**(((nI + BGM_LU) - bI)/20)
fi = int(FIN*SR); fo = int(FOUT*SR)
bed[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)[:, None]; bed[-fo:] *= np.linspace(1, 0, fo, dtype=np.float32)[:, None]
bedI, _ = meas(bed, 'bed')
body = nar + bed; full = np.concatenate([intro, body])
fI, fTP = meas(full, 'full_pre')
g_db = TARGET_I - fI
if fTP + g_db > TP_MAX: g_db = TP_MAX - fTP
g = 10**(g_db/20)
outs = dict(full_mix=full*g, body_mix=body*g, stem_intro_narration=intro*g, stem_body_narration=nar*g, stem_body_bgm=bed*g)
for k, v in outs.items():
    p = A/f'geomag_full_r1_{k}.wav'; assert not p.exists(); sf.write(str(p), v.astype(np.float32), SR, subtype='FLOAT')
FI, FTP = meas(full*g, 'full_post'); BI, BTP = meas(body*g, 'body_post')
rep = dict(body_narration_I=nI, body_narration_TP=nTP, intro_raw_I=iI, intro_gain_db=nI-iI, bgm_source_I=bI, bgm_bed_I=bedI, bgm_rel_LU=bedI-nI,
           bgm_loops=loops, bgm_xfade_s=XF, bgm_fade_in_s=FIN, bgm_fade_out_s=FOUT, bgm_trim_head_s=on[0]/SR,
           final_gain_db=g_db, full_I=FI, full_TP=FTP, body_mix_I=BI, body_mix_TP=BTP, intro_s=len(intro)/SR, body_s=n/SR, full_s=len(full)/SR,
           bgm_asset='SLEEP-BGM-UNIFIED-001 ' + str(BGM))
(A/'mix_report.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8'); print(json.dumps(rep, ensure_ascii=False, indent=1))