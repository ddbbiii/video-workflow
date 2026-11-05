import subprocess, numpy as np, json
from pathlib import Path
P = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal')  # 2026-10-08 迁移：原 legacy-source\zhumian\b-geomagnetic-reversal，现为单集目录
B = P/'video'/'source'/'geomag_v3_body_r1.mp4'
def get(f, ss, d=12, sr=8000):
    r = subprocess.run(['ffmpeg','-v','error','-ss',f'{ss:.4f}','-i',str(f),'-t',str(d),'-ac','1','-ar',str(sr),'-f','f32le','-'],capture_output=True,check=True)
    return np.frombuffer(r.stdout,np.float32)
out = {}
for name, f in [('clean', P/'video'/'geomag_v3_full_r1_clean.mp4'), ('subtitled', P/'video'/'geomag_v3_full_r1_subtitled.mp4')]:
    for tb in [5.0, 60.0, 700.0, 1160.0, 1380.0]:
        tf = tb - 2.5667 + 13.9667 if tb > 28 else tb + 13.9667
        a = get(f, tf); b = get(B, tb)
        n = min(len(a), len(b)); a=a[:n]-a[:n].mean(); b=b[:n]-b[:n].mean()
        c = np.fft.irfft(np.fft.rfft(a, 2*n)*np.conj(np.fft.rfft(b, 2*n)))
        lag = int(np.argmax(np.abs(c))); lag = lag-2*n if lag > n else lag
        out[f'{name}@body{tb}'] = dict(lag_ms=round(lag/8, 2), corr=round(float(c.max()/np.sqrt((a*a).sum()*(b*b).sum())), 3))
print(json.dumps(out, indent=1)); (P/'video'/'qa'/'av_sync_xcorr.json').write_text(json.dumps(out, indent=1))