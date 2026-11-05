"""QA of affine renders (CPU): frame count/size/fps vs plan + first/mid/last thumbnails sheets.
args: render_dir [tag]   -> qa/affine_qa_<tag>.json, qa/affine_contact_<tag>_N.jpg"""
import json, subprocess, sys
from pathlib import Path
import cv2, numpy as np
RUN = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\video\clips')  # 2026-10-08 迁移：原批次 20261007-v3-motion-b01 根目录，现为单集 video\clips
D = Path(sys.argv[1]); tag = sys.argv[2] if len(sys.argv) > 2 else D.name
plan = {p['shot']: p for p in json.loads((RUN / 'motion_plan.json').read_text(encoding='utf-8'))}
res = []; rows = []
for v in sorted(D.glob('*.mp4')):
    s = v.stem; pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries',
            'stream=width,height,r_frame_rate,nb_read_packets,codec_name,pix_fmt', '-of', 'json', str(v)], capture_output=True, text=True).stdout)['streams'][0]
    n = int(pr['nb_read_packets']); exp = plan[s]['frames_30fps']
    cap = cv2.VideoCapture(str(v)); th = []; lum = []
    for f in (0, n // 2, n - 1):
        cap.set(cv2.CAP_PROP_POS_FRAMES, f); ok, im = cap.read()
        if not ok: im = np.zeros((1080, 1920, 3), np.uint8)
        lum.append(float(im.mean())); th.append(cv2.resize(im, (384, 216), interpolation=cv2.INTER_AREA))
    cap.release()
    ok = n == exp and pr['width'] == 1920 and pr['height'] == 1080 and pr['r_frame_rate'] == '30/1'
    res.append(dict(shot=s, file=str(v), frames=n, expected=exp, size=[pr['width'], pr['height']], fps=pr['r_frame_rate'], codec=pr['codec_name'], pix_fmt=pr['pix_fmt'],
                    luma_first_mid_last=[round(x, 1) for x in lum], ok=ok))
    row = np.concatenate(th, 1); lab = np.zeros((24, row.shape[1], 3), np.uint8)
    cv2.putText(lab, '%s %s %d/%d %s' % (s, plan[s]['method'], n, exp, 'OK' if ok else 'MISMATCH'), (4, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255) if ok else (0, 0, 255), 1)
    rows.append(np.concatenate([lab, row], 0))
(RUN / 'qa' / ('affine_qa_%s.json' % tag)).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
for i in range(0, len(rows), 16):
    (RUN / 'qa' / ('affine_contact_%s_%d.jpg' % (tag, i // 16 + 1))).write_bytes(cv2.imencode('.jpg', np.concatenate(rows[i:i + 16], 0), [cv2.IMWRITE_JPEG_QUALITY, 80])[1].tobytes())  # imencode: cv2.imwrite fails on non-ASCII paths
print(tag, len(res), 'ok', sum(r['ok'] for r in res), 'bad', [r['shot'] for r in res if not r['ok']])
