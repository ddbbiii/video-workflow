"""Serial RealBasicVSR on the I2V crops via shared/video-restoration/run_vsr_streaming.py (each run takes/releases the shared lock itself).
Run only via gpu_job.py after the queue grants. Stops the batch on first failure (VSR batch rule)."""
import json, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; RUN = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\video\clips')  # 2026-10-08 迁移：原批次 20261007-v3-motion-b01 根目录，现为单集 video\clips
ROOT = Path(r'E:\program\1project\video')
PY = ROOT / 'shared/runtime/comfy/installs/portable/python_embeded/python.exe'
VSR = ROOT / 'shared/video-restoration/run_vsr_streaming.py'
res = json.loads((Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\archive\gen_rebuild\runs\20261007-v3-motion-b01') / 'i2v' / 'i2v_manifest.json').read_text(encoding='utf-8'))
keep = json.loads((RUN / 'qa' / 'i2v_qa.json').read_text(encoding='utf-8')) if (RUN / 'qa' / 'i2v_qa.json').exists() else {}
out = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\archive\gen_rebuild\runs\20261007-v3-motion-b01') / 'vsr'; out.mkdir(exist_ok=True)
mf = out / 'vsr_batch.json'; log = json.loads(mf.read_text(encoding='utf-8')) if mf.exists() else []
done = {x['shot'] for x in log if x['exit'] == 0}
for r in res:
    s = r['shot']
    if not r.get('ok') or s in done: continue
    if keep and keep.get(s, {}).get('verdict') == 'reject': print(s, 'skip (I2V rejected -> affine)'); continue
    n = 1
    while (out / f'{s}-vsr{n:02d}').exists(): n += 1
    od = out / f'{s}-vsr{n:02d}'
    cmd = [str(PY), str(VSR), '--input', r['crop_1248x702'], '--baseline', r['lanczos_1920x1080'], '--output-dir', str(od), '--shot-id', s,
           '--lock-owner', 'zhumian-geomag-v3-vsr', '--output-size', '1920x1080']
    t = time.time(); print('RUN', s, flush=True)
    p = subprocess.run(cmd)
    log.append(dict(shot=s, run_dir=str(od), exit=p.returncode, seconds=round(time.time() - t, 1), ended=time.strftime('%Y-%m-%d %H:%M:%S')))
    mf.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding='utf-8')
    print(s, 'exit', p.returncode, flush=True)
    if p.returncode not in (0, 5): print('STOP batch on failure'); sys.exit(1)
print('DONE')
