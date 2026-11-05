"""CPU: build final I2V shot clips at the old timeline duration (30 fps, 1920x1080).
Source = VSR delivery (if completed & QA not fail) else Lanczos baseline. 121 native frames are played 1:1 at 30 fps,
extended by ping-pong or cross-faded loop, plus a gentle push toward the focus (<=6%)."""
import json, subprocess, sys, shutil
from pathlib import Path
import numpy as np, cv2
HERE = Path(__file__).resolve().parent; RUN = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\video\clips')  # 2026-10-08 迁移：原批次 20261007-v3-motion-b01 根目录，现为单集 video\clips
FF = shutil.which('ffmpeg'); FPS = 30; W, H = 1920, 1080
plan = {p['shot']: p for p in json.loads((RUN / 'motion_plan.json').read_text(encoding='utf-8'))}
i2v = {r['shot']: r for r in json.loads((Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\archive\gen_rebuild\runs\20261007-v3-motion-b01') / 'i2v' / 'i2v_manifest.json').read_text(encoding='utf-8'))}
vsrb = json.loads((Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\archive\gen_rebuild\runs\20261007-v3-motion-b01') / 'vsr' / 'vsr_batch.json').read_text(encoding='utf-8')) if (Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\archive\gen_rebuild\runs\20261007-v3-motion-b01') / 'vsr' / 'vsr_batch.json').exists() else []
def vsr_for(s):
    for x in reversed(vsrb):
        if x['shot'] == s and x['exit'] == 0:
            d = Path(x['run_dir']); f = list(d.glob('*-realbasicvsr-1920x1080.mp4'))
            if f: return f[0]
    return None
def read_frames(p):
    pr = subprocess.run([FF, '-v', 'error', '-i', str(p), '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-vf', f'scale={W}:{H}:flags=lanczos', '-'], capture_output=True, check=True)
    a = np.frombuffer(pr.stdout, np.uint8); return a.reshape(-1, H, W, 3)
def ramp(t, r=0.12):
    # ramped-linear progress 0..1 with r fraction ease at both ends
    if t <= 0: return 0.0
    if t >= 1: return 1.0
    v = 1 / (1 - r)
    if t < r: return v * t * t / (2 * r)
    if t > 1 - r: return 1 - v * (1 - t) ** 2 / (2 * r)
    return v * (t - r / 2)
def build(s, fr, n, mode, k=18):
    L = len(fr); idx = []
    if mode == 'pingpong':
        cyc = list(range(L)) + list(range(L - 2, 0, -1))
        while len(idx) < n: idx += cyc
        return [fr[i] for i in idx[:n]]
    out = list(fr)
    while len(out) < n:
        tail = out[-k:]; head = fr[:k]
        blend = [cv2.addWeighted(tail[j], 1 - (j + 1) / (k + 1), head[j], (j + 1) / (k + 1), 0) for j in range(k)]
        out = out[:-k] + blend + list(fr[k:])
    return out[:n]
def main(only=None):
    (Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\archive\gen_rebuild\runs\20261007-v3-motion-b01') / 'i2v' / 'assembled').mkdir(parents=True, exist_ok=True); rep = []
    for s, p in plan.items():
        if p['method'] != 'i2v' or (only and s not in only): continue
        r = i2v.get(s)
        if not r or not r.get('ok'): print(s, 'no i2v'); continue
        src = vsr_for(s); kind = 'VSR RealBasicVSR x4 -> 1920x1080'
        if src is None: src = Path(r['lanczos_1920x1080']); kind = 'Lanczos 1248x702->1920x1080 (no VSR)'
        fr = read_frames(src); n = p['frames_30fps']
        seq = build(s, fr, n, p['loop_mode'])
        fx, fy = p['focus']; z1 = 1.0 + min(0.06, 0.0025 * p['duration_s'])
        dst = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\archive\gen_rebuild\runs\20261007-v3-motion-b01') / 'i2v' / 'assembled' / f'{s}-i2v-1920x1080.mp4'
        if dst.exists(): print(s, 'exists, skip (no overwrite)'); continue
        enc = subprocess.Popen([FF, '-v', 'error', '-n', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                                '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(dst)], stdin=subprocess.PIPE)
        for i, f in enumerate(seq):
            z = 1 + (z1 - 1) * ramp(i / max(1, n - 1))
            cx, cy = W * (0.5 + (fx - 0.5) * (1 - 1 / z)), H * (0.5 + (fy - 0.5) * (1 - 1 / z))
            M = np.float32([[z, 0, W / 2 - z * cx], [0, z, H / 2 - z * cy]])
            enc.stdin.write(cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE).tobytes())
        enc.stdin.close(); enc.wait()
        pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-show_entries', 'stream=nb_read_frames,width,height,avg_frame_rate', '-of', 'json', str(dst)], capture_output=True, text=True).stdout)['streams'][0]
        ok = int(pr['nb_read_frames']) == n and pr['width'] == W
        rep.append(dict(shot=s, source=str(src), source_kind=kind, loop_mode=p['loop_mode'], native_frames=len(fr), frames=n, duration_s=p['duration_s'], push_zoom=round(z1, 4), output=str(dst), decode_ok=ok))
        print(s, kind, n, ok, flush=True)
    (Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\archive\gen_rebuild\runs\20261007-v3-motion-b01') / 'i2v' / 'assembled' / 'i2v_assemble.json').write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding='utf-8')
if __name__ == '__main__':
    main(sys.argv[1:] or None)
