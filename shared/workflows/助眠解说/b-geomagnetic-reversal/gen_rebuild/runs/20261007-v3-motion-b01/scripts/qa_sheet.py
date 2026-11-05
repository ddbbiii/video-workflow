"""CPU QA: frame strip + temporal metrics for videos. usage: qa_sheet.py out.jpg video1 [video2 ...]"""
import json, subprocess, sys, shutil
from pathlib import Path
import numpy as np, cv2
FF = shutil.which('ffmpeg')
def frames(p, w=480, h=270):
    pr = subprocess.run([FF, '-v', 'error', '-i', str(p), '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-vf', f'scale={w}:{h}', '-'], capture_output=True, check=True)
    return np.frombuffer(pr.stdout, np.uint8).reshape(-1, h, w, 3)
out = Path(sys.argv[1]); rows = []; metrics = {}
for v in sys.argv[2:]:
    f = frames(v); n = len(f)
    g = f.astype(np.float32).mean(axis=3)
    diff = np.abs(np.diff(g, axis=0)).mean(axis=(1, 2)) if n > 1 else np.zeros(1)
    lum = g.mean(axis=(1, 2)); jump = np.abs(np.diff(lum)) if n > 1 else np.zeros(1)
    metrics[Path(v).name] = dict(frames=n, mean_absdiff=round(float(diff.mean()), 3), p95_absdiff=round(float(np.percentile(diff, 95)), 3), max_absdiff=round(float(diff.max()), 3),
                                 max_luma_jump=round(float(jump.max()), 3), first_last_absdiff=round(float(np.abs(g[0] - g[-1]).mean()), 3))
    pick = [0, n // 4, n // 2, 3 * n // 4, n - 1]
    row = np.concatenate([f[i] for i in pick], axis=1).copy()
    cv2.putText(row, Path(v).stem[:60], (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    rows.append(row)
Path(out).write_bytes(cv2.imencode('.jpg', np.concatenate(rows, axis=0), [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tobytes())  # non-ASCII-safe
out.with_suffix('.json').write_text(json.dumps(metrics, indent=1), encoding='utf-8')
print(json.dumps(metrics))
