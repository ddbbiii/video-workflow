"""LTX-2.3 distilled I2V for the selected natural-motion shots (GPU; run only via gpu_job.py after the queue grants).
Based on gen_rebuild/run_i2v_cinematic_test01.py (copied pattern, original untouched)."""
import json, shutil, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; RUN = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\video\clips')  # 2026-10-08 迁移：原批次 20261007-v3-motion-b01 根目录，现为单集 video\clips
P = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal'); ROOT = Path(r'E:\program\1project\video')
HELPER = P / 'archive/i2v/select_v1/_work'
sys.path.insert(0, str(HELPER)); import i2v_cmp as m
sys.path.insert(0, str(ROOT / 'shared/camera-motion'))
from blender_backend import acquire_gpu_lock, release_gpu_lock
sys.path.insert(0, str(HERE)); import shots
FF = shutil.which('ffmpeg')
plan = json.loads((RUN / 'motion_plan.json').read_text(encoding='utf-8'))
JOBS = [p for p in plan if p['method'] == 'i2v']
if len(sys.argv) > 1: JOBS = [p for p in JOBS if p['shot'] in sys.argv[1:]]
WORK = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\archive\gen_rebuild\runs\20261007-v3-motion-b01') / 'i2v'  # 原 i2v 结果已归档在此；重跑会写进去
def post(raw, shot):
    crop = WORK / 'crop' / f'{shot}-ltx-1248x702.mp4'; base = WORK / 'lanczos' / f'{shot}-ltx-lanczos-1920x1080.mp4'
    subprocess.run([FF, '-v', 'error', '-y', '-i', str(raw), '-an', '-vf', 'crop=1248:702,setsar=1', '-c:v', 'libx264', '-preset', 'slow', '-crf', '10', '-pix_fmt', 'yuv420p', str(crop)], check=True)
    subprocess.run([FF, '-v', 'error', '-y', '-i', str(crop), '-an', '-vf', 'scale=1920:1080:flags=lanczos,setsar=1', '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p', str(base)], check=True)
    for p in (raw, crop, base): subprocess.run([FF, '-v', 'error', '-i', str(p), '-f', 'null', '-'], check=True)
    return crop, base
def main():
    for d in ('in', 'out', 'logs', 'temp', 'raw', 'crop', 'lanczos'): (WORK / d).mkdir(parents=True, exist_ok=True)
    shutil.copy2(HELPER / 'extra_model_paths_diffusion.yaml', WORK / 'extra_model_paths_diffusion.yaml')
    m.SCR = str(WORK); m.LOGF = str(WORK / 'logs/runner.log')
    mf = WORK / 'i2v_manifest.json'
    results = json.loads(mf.read_text(encoding='utf-8')) if mf.exists() else []
    done = {r['shot'] for r in results if r.get('ok')}
    lock = acquire_gpu_lock(owner='zhumian-geomag-v3-i2v-ltx', timeout_s=600)
    try:
        m.start_comfy('portable', 'geomag_v3_i2v')
        for job in JOBS:
            shot = job['shot']
            if shot in done: m.log(f'{shot} already ok, skip'); continue
            r = dict(shot=shot, engine='LTX-2.3 22B dev fp8 + distilled LoRA 0.5, ManualSigmas 2-stage', w=1280, h=704, frames=121, fps=24, seed=42,
                     input=job['i2v_input'], prompt=job['i2v_prompt'], negative=shots.NEGATIVE, started=time.strftime('%Y-%m-%d %H:%M:%S'))
            t0 = time.monotonic()
            try:
                if m.PROC is None or m.PROC.poll() is not None:
                    m.log('comfy not running -> restart'); m.PROC = None; m.start_comfy('portable', 'geomag_v3_i2v_re')
                shutil.copy2(job['i2v_input'], WORK / 'in' / f'{shot}.png')
                m.IMAGE, m.PROMPT = f'{shot}.png', job['i2v_prompt']
                g = m.g_ltx(1280, 704, 121, 11, 'geomag-v3/' + shot)
                g['19']['inputs']['noise_seed'] = 42; g['30']['inputs']['noise_seed'] = 42
                g['5']['inputs']['text'] = shots.NEGATIVE
                (WORK / 'logs' / f'{shot}-graph.json').write_text(json.dumps(g, ensure_ascii=False, indent=1), encoding='utf-8')
                pid = json.loads(m.http('/prompt', {'prompt': g, 'client_id': shot}))['prompt_id']
                m.log(f'{shot} queued {pid}')
                while True:
                    time.sleep(5)
                    if m.PROC.poll() is not None: raise RuntimeError('ComfyUI exited')
                    h = m.jget('/history/' + pid)
                    if pid in h: entry = h[pid]; break
                    if time.monotonic() - t0 > 2400: m.http('/interrupt', {}); raise TimeoutError(shot)
                if entry.get('status', {}).get('status_str') != 'success': raise RuntimeError(str(entry.get('status'))[:500])
                raw0 = max((WORK / 'out/geomag-v3').glob(shot + '_*.mp4'), key=lambda p: p.stat().st_mtime)
                raw = WORK / 'raw' / f'{shot}-ltx-raw-1280x704.mp4'; shutil.copy2(raw0, raw)
                crop, base = post(raw, shot)
                r.update(ok=True, raw=str(raw), crop_1248x702=str(crop), lanczos_1920x1080=str(base), gen_s=round(time.monotonic() - t0, 1), decode_ok=True, visual_qa='pending')
                m.http('/free', {'unload_models': False, 'free_memory': True})
            except Exception as e:
                r.update(ok=False, error=repr(e)[:800], gen_s=round(time.monotonic() - t0, 1)); m.log(f'{shot} FAILED {e!r}')
            r['ended'] = time.strftime('%Y-%m-%d %H:%M:%S')
            results = [x for x in results if x['shot'] != shot] + [r]
            mf.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
            print(shot, 'ok' if r.get('ok') else 'FAILED', r['gen_s'], flush=True)
    finally:
        m.stop_comfy(); release_gpu_lock(lock)
    bad = [r['shot'] for r in results if not r.get('ok')]
    print('DONE ok=%d failed=%s' % (sum(1 for r in results if r.get('ok')), bad))
    sys.exit(1 if len(bad) == len(results) else 0)
if __name__ == '__main__':
    main()
