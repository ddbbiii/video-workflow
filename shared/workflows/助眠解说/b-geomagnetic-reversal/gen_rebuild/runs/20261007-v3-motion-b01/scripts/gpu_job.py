"""Run a GPU job only if its queue request is granted; record running/pid/log, then completed/failed (submitter fields only)."""
import json, os, subprocess, sys, time
from pathlib import Path
Q = Path(r'E:\program\1project\video\shared\gpu-queue\requests')
def now(): return time.strftime('%Y-%m-%dT%H:%M:%S+08:00')
def upd(rid, **kw):
    p = Q / f'{rid}.json'; d = json.loads(p.read_text(encoding='utf-8')); d.update(kw)
    tmp = p.with_suffix('.tmp'); tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8'); os.replace(tmp, p)
rid, log = sys.argv[1], sys.argv[2]; cmd = sys.argv[3:]
st = json.loads((Q / f'{rid}.json').read_text(encoding='utf-8'))['status']
if st != 'granted':
    print('refuse: request %s status=%s (need granted)' % (rid, st)); sys.exit(3)
with open(log, 'a', encoding='utf-8') as lf:
    pr = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, cwd=str(Path(cmd[1]).parent))
    upd(rid, status='running', pid=pr.pid, wrapper_pid=os.getpid(), log_path=log, started_at=now())
    rc = pr.wait()
upd(rid, status='completed' if rc == 0 else 'failed', exit_code=rc, finished_at=now())
print('exit', rc)
