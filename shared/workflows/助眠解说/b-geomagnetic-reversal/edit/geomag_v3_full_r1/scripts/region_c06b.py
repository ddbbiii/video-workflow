"""Build the new ch1-c06b region frames (12f xfade from c06a, new c06b, 11f xfade into c07), same blend as stitch_r1.py."""
import json, subprocess
from pathlib import Path
import numpy as np, cv2
P = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal')  # 2026-10-08 迁移：原 legacy-source\zhumian\b-geomagnetic-reversal，现为单集目录
C06 = P/'video'/'clips'/'full_r1_c06b'; FR = P/'video'/'clips'/'final_r2'
BODY = P/'video'/'source'/'geomag_v3_body_r1.mp4'; W, H = 1920, 1080
def frames(p, start=0, n=None):
    vf = f"select='gte(n\\,{start})'" + (f",select='lt(n\\,{start+n})'" if n else '')
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-vf', vf, '-vsync', '0', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3)
a = frames(FR/'ch1-c06a.mp4', 214, 12); b = frames(C06/'affine_c06b'/'ch1-c06b.mp4'); c = frames(FR/'ch1-c07.mp4', 0, 11)
assert len(a) == 12 and len(b) == 110 and len(c) == 11, (len(a), len(b), len(c))
out = []
for j in range(12): p = (j+1)/13; out.append(cv2.addWeighted(a[j], 1-p, b[j], p, 0))
out += list(b[12:110-11])
for j in range(11): p = (j+1)/12; out.append(cv2.addWeighted(b[110-11+j], 1-p, c[j], p, 0))
assert len(out) == 110
dst = C06/'region_c06b_r1.mkv'; assert not dst.exists()
enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-n', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', '30', '-i', '-', '-c:v', 'ffv1', '-pix_fmt', 'yuv420p', str(dst)], stdin=subprocess.PIPE)
for f in out: enc.stdin.write(f.tobytes())
enc.stdin.close(); assert enc.wait() == 0
# QA: rebuild two old blended frames from old clips and compare with locked body
def psnr(x, y): m = np.mean((x.astype(np.float32)-y.astype(np.float32))**2); return 99.0 if m == 0 else float(10*np.log10(255**2/m))
ob = frames(FR/'ch1-c06b.mp4', 0, 187); bodyf = frames(BODY, 667, 12); bodyg = frames(BODY, 843, 11)
q1 = [psnr(cv2.addWeighted(a[j], 1-(j+1)/13, ob[j], (j+1)/13, 0), bodyf[j]) for j in (0, 6, 11)]
q2 = [psnr(cv2.addWeighted(ob[176+j], 1-(j+1)/12, c[j], (j+1)/12, 0), bodyg[j]) for j in (0, 5, 10)]
q3 = psnr(ob[0], b[0])
r = dict(region_frames=110, psnr_rebuild_old_xfade_in=q1, psnr_rebuild_old_xfade_out=q2, psnr_new_c06b_f0_vs_old_f0=q3)
(C06/'region_qa.json').write_text(json.dumps(r, indent=1), encoding='utf-8'); print(r)