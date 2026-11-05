"""Splice new ch1-c06b narration into the locked body narration (CPU). No re-dub of other shots.
Body ch1 convention (draft_dof_vo_v3/_tools/embed_ch1_b2_v3.py): raw take at 1x, shot len = take len, acrossfade 0.4s tri, linear loudnorm."""
import json, subprocess, sys
from pathlib import Path
import numpy as np, soundfile as sf
P = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal')  # 2026-10-08 迁移：原 legacy-source\zhumian\b-geomagnetic-reversal，现为单集目录
C06 = P/'video'/'clips'/'full_r1_c06b'  # 原批次 full_r1\body\
BODY = P/'video'/'source'/'geomag_v3_body_r1.mp4'
OLDT = P/'archive'/'tts'/'ch1_b2_v1'/'takes-seed7-final'; NEWT = P/'audio'/'vo-raw'/'full_r1'/'takes-seed7-final'
SR = 44100; F = 0.4; FPS = 30
def dec(src, ch, extra=()):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(src), *extra, '-f', 'f32le', '-ac', str(ch), '-ar', str(SR), '-'], capture_output=True, check=True)
    a = np.frombuffer(r.stdout, np.float32); return a.reshape(-1, ch) if ch > 1 else a
body = dec(BODY, 2, ['-map', '0:a:0']).copy(); mono = body.mean(1)
oldb = dec(OLDT/'c06b.wav', 1); c07 = dec(OLDT/'c07.wav', 1); newb = dec(NEWT/'c06b.wav', 1)
def locate(sig, t0, t1):
    seg = mono[int(t0*SR):int(t1*SR)]; n = len(seg) + len(sig)
    N = 1 << (n-1).bit_length()
    xc = np.fft.irfft(np.fft.rfft(seg, N) * np.conj(np.fft.rfft(sig, N)), N)[:len(seg)]
    k = int(np.argmax(xc)); return (int(t0*SR) + k), xc[k] / (np.linalg.norm(sig)**2 + 1e-12)
ob, gb = locate(oldb, 20.5, 25.0); oc, gc = locate(c07, 26.0, 31.0)
F_n = int(round(F*SR))
slot_old = oc + F_n - ob
solo = slice(F_n, min(len(oldb), slot_old - F_n))
x = oldb[solo]; y = mono[ob+solo.start: ob+solo.stop]
g = float(np.dot(x, y) / np.dot(x, x)); res = y - g*x
res_db = 10*np.log10(np.mean(res**2) / np.mean(y**2))
# video-synced new slot: c06b clip frames
n_old = 187; n_new = int(round(len(newb)/SR*FPS))
delta_v = (n_new - n_old)/FPS
slot_new = slot_old + int(round(delta_v*SR))
nb = np.zeros(slot_new, np.float32); L = min(slot_new, len(newb)); nb[:L] = newb[:L]
trim_tail = len(newb) - slot_new
tailrms = 20*np.log10(np.sqrt(np.mean(newb[slot_new:]**2))+1e-12) if trim_tail > 0 else None
ob_full = np.zeros(slot_old, np.float32); ob_full[:min(slot_old, len(oldb))] = oldb[:slot_old]
fi = np.linspace(0, 1, F_n, endpoint=False, dtype=np.float32)[:, None]; fo = 1 - fi
head = body[:ob+F_n].copy(); head[ob:ob+F_n] -= g*ob_full[:F_n, None]*fi
tail = body[oc:].copy(); tail[:F_n] -= g*ob_full[slot_old-F_n:, None]*fo
nb2 = (g*nb)[:, None].repeat(2, 1)
new = np.concatenate([head[:ob], head[ob:ob+F_n] + nb2[:F_n]*fi, nb2[F_n:slot_new-F_n], tail[:F_n] + nb2[slot_new-F_n:]*fo, tail[F_n:]])
out = C06/'body_narration_r1.wav'
assert not out.exists(); sf.write(str(out), new, SR, subtype='FLOAT')
info = dict(body_audio_s=len(body)/SR, new_audio_s=len(new)/SR, c06b_old_start_s=ob/SR, c07_old_start_s=oc/SR, corr_c06b=float(gb), corr_c07=float(gc),
            gain_linear=g, gain_db=20*np.log10(g), solo_residual_db=float(res_db), slot_old_s=slot_old/SR, slot_new_s=slot_new/SR,
            new_take_s=len(newb)/SR, new_take_trimmed_tail_samples=int(trim_tail), trimmed_tail_rms_db=tailrms,
            n_frames_old=n_old, n_frames_new=n_new, delta_s=(slot_new-slot_old)/SR, delta_frames=n_new-n_old,
            shift_from_old_s=oc/SR, note='audio after c07 start shifted by delta_s; equals video shift delta_frames/30')
(C06/'splice.json').write_text(json.dumps(info, indent=1), encoding='utf-8'); print(json.dumps(info, indent=1))