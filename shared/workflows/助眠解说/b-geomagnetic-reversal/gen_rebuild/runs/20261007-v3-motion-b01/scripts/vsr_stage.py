"""VSR stage (GPU, run via gpu_job.py under request zhumian-geomag-v3-vsr-i2v-20261007).
1) c04 single-shot validation with shared/video-restoration/run_vsr_streaming.py (unmodified), new dir each attempt, max 3 attempts.
2) only if c04 exit 0 and qa_status != fail: serial batch over I2V clips that passed I2V QA (run_vsr_batch.py).
Otherwise write vsr/VSR_ABANDONED.json -> assemble falls back to Lanczos."""
import json, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; RUN = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\video\clips')  # 2026-10-08 迁移：原批次 20261007-v3-motion-b01 根目录，现为单集 video\clips
ROOT = Path(r'E:\program\1project\video')
PY = ROOT / 'shared/runtime/comfy/installs/portable/python_embeded/python.exe'
VSR = ROOT / 'shared/video-restoration/run_vsr_streaming.py'
SRC = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\archive\gen_rebuild\runs\20261007-ltx-cinematic-retry-c04')
out = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\archive\gen_rebuild\runs\20261007-v3-motion-b01') / 'vsr'; out.mkdir(exist_ok=True)
def log(*a): print(time.strftime('[%H:%M:%S]'), *a, flush=True)
rec = []
ok = False
for n in range(1, 4):
    od = out / f'c04-validate-{n:02d}'
    if od.exists(): log('exists, skip attempt', od.name); continue
    cmd = [str(PY), str(VSR), '--input', str(SRC / 'ch1-c04-v2-01-raw-1280x704.mp4'), '--baseline', str(SRC / 'ch1-c04-v2-01-1920x1080-hq.mp4'),
           '--output-dir', str(od), '--shot-id', 'ch1-c04-v2-01', '--lock-owner', 'zhumian-geomag-v3-vsr', '--output-size', '1920x1080']
    while True:
        t = time.time(); log('c04 attempt', n); p = subprocess.run(cmd)
        if p.returncode == 4 and not od.exists(): log('lock busy, wait 60s'); time.sleep(60); continue
        break
    mf = od / 'manifest.json'; m = json.loads(mf.read_text(encoding='utf-8')) if mf.exists() else {}
    r = dict(attempt=n, run_dir=str(od), exit=p.returncode, seconds=round(time.time() - t, 1), status=m.get('status'), qa_status=m.get('qa_status'),
             failed_stage=m.get('failed_stage'), error=m.get('error_summary'))
    rec.append(r); log('c04 result', r)
    (out / 'c04_validate.json').write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding='utf-8')
    if p.returncode == 0 and r['qa_status'] != 'fail': ok = True; break
if not ok:
    (out / 'VSR_ABANDONED.json').write_text(json.dumps(dict(reason='c04 单镜验证 3 次内未通过，放弃 VSR，I2V 使用 Lanczos 版', attempts=rec), ensure_ascii=False, indent=2), encoding='utf-8')
    log('VSR abandoned'); sys.exit(2)
log('c04 passed -> batch')
p = subprocess.run([sys.executable, str(HERE / 'run_vsr_batch.py')])
log('batch exit', p.returncode); sys.exit(p.returncode)
