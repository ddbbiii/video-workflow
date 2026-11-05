"""Stitch geomag v3 body (CPU). Strictly follows old timeline edit/draft_dof_vo_v4 (read-only):
- shot order/frame counts = old shots/*.mp4; shot xfade 0.4s (12f), chapter xfade 0.5s (15f), fade transition;
- cut points re-derived the way embed_select_v1_v4.py chained ffmpeg xfade (offset = max(vdur, adur) - fade, frame-ceil),
  then pinned to the real old chapter frame counts (residual frames spread over the chapter's last cuts);
- audio = original v4 full mix (ch1-6_dof_vo_v4.mp4 a:0) stream-copied: no re-dub, no re-mix, no new BGM; no subtitles/text/overlays.
usage: stitch_r1.py <final_dir_name> [--plan-only] [--max-frames N]"""
import json, math, subprocess, sys, time, shutil
from pathlib import Path
import numpy as np, cv2
HERE = Path(__file__).resolve().parent; RUN = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\video\clips')  # 2026-10-08 迁移：原批次 20261007-v3-motion-b01 根目录，现为单集 video\clips
P = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal')
OLD = P / 'audio' / 'draft_dof_vo_v4'; OLDA = P / 'archive' / 'edit' / 'draft_dof_vo_v4'; OUT = P / 'video' / 'source'  # inventory/chapters 在 audio，shots/整片在 archive
FD = RUN / sys.argv[1]; PLAN_ONLY = '--plan-only' in sys.argv
MAXF = int(sys.argv[sys.argv.index('--max-frames') + 1]) if '--max-frames' in sys.argv else 0
W, H, FPS = 1920, 1080, 30
FF = shutil.which('ffmpeg'); FP = shutil.which('ffprobe')
def log(*a):
    s = time.strftime('[%H:%M:%S] ') + ' '.join(map(str, a)); print(s, flush=True)
def pj(*a): return json.loads(subprocess.run([FP, '-v', 'error', *a, '-of', 'json'], capture_output=True, text=True, check=True).stdout)
def vframes(p): return int(pj('-select_streams', 'v:0', '-count_packets', '-show_entries', 'stream=nb_read_packets', str(p))['streams'][0]['nb_read_packets'])
def adur(p): return float(pj('-select_streams', 'a:0', '-show_entries', 'stream=duration', str(p))['streams'][0]['duration'])
def fdur(p): return float(pj('-show_entries', 'format=duration', str(p))['format']['duration'])
inv = json.loads((OLD / 'inventory.json').read_text(encoding='utf-8'))['shots']
chaps = []
for s in inv:
    c = s['shot'].split('-')[0]
    if not chaps or chaps[-1][0] != c: chaps.append((c, []))
    chaps[-1][1].append(s['shot'])
def chain(items, fade_f, target):
    """items: [(frames, audio_s)] -> start frames list; residual vs target spread over last cuts."""
    fade = fade_f / FPS; starts = [0]; Vf = items[0][0]; A = items[0][1]
    for f, a in items[1:]:
        off = round(max(0.05, max(Vf / FPS, A) - fade), 3); of = math.ceil(off * FPS - 1e-6)
        starts.append(of); Vf = of + f; A = A + a - fade
    res = target - Vf
    if res:
        k = min(abs(res), len(starts) - 1); step = 1 if res > 0 else -1
        for j in range(k):
            for i in range(len(starts) - 1 - j, len(starts)): starts[i] += step
        Vf += step * k
        if abs(res) > k: raise SystemExit('residual too large %s' % res)
    return starts, Vf, res
segs = []; report = dict(chapters=[], shots=[])
ch_items = []
for c, shots in chaps:
    items = []
    for s in shots:
        items.append((vframes(OLDA / 'shots' / f'{s}.mp4'), adur(OLDA / 'shots' / f'{s}.mp4')))
    cf = OLD / 'chapters' / f'{c}_dof_vo_v4.mp4'; target = vframes(cf)
    st, L, res = chain(items, 12, target)
    report['chapters'].append(dict(chapter=c, old_chapter_frames=target, simulated_residual_frames=res))
    ch_items.append((c, shots, items, st, target, max(target / FPS, adur(cf))))
full = OLDA / 'ch1-6_dof_vo_v4.mp4'; full_frames = vframes(full)
cst, CL, cres = chain([(t, a) for _, _, _, _, t, a in ch_items], 15, full_frames)
report.update(old_full=str(full), old_full_frames=full_frames, chapter_residual_frames=cres)
for (c, shots, items, st, target, _), c0 in zip(ch_items, cst):
    for s, (f, a), s0 in zip(shots, items, st):
        clip = FD / f'{s}.mp4'; n = vframes(clip)
        if n != f: raise SystemExit(f'{s}: new clip {n} frames != old {f}')
        segs.append(dict(shot=s, chapter=c, start=c0 + s0, frames=n, file=str(clip)))
for i, g in enumerate(segs):
    g['overlap_next'] = (segs[i + 1]['start'] - (g['start'] + g['frames'])) * -1 if i + 1 < len(segs) else 0
    g['start_s'] = round(g['start'] / FPS, 3)
report['shots'] = segs; TOT = full_frames if not MAXF else min(MAXF, full_frames)
OUT.mkdir(parents=True, exist_ok=True)
tag = 'geomag_v3_body_r1' + ('' if not MAXF else f'_smoke{MAXF}')
(OUT / f'{tag}_timeline.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
log('segments', len(segs), 'total frames', TOT, 'chapter starts', cst, 'overlaps', sorted(set(g['overlap_next'] for g in segs)))
if PLAN_ONLY: sys.exit(0)
dst = OUT / f'{tag}.mp4'
if dst.exists(): raise SystemExit('refuse to overwrite ' + str(dst))
class Reader:
    def __init__(s, g):
        s.g = g; s.i = -1; s.last = None
        s.p = subprocess.Popen([FF, '-v', 'error', '-i', g['file'], '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], stdout=subprocess.PIPE, bufsize=W * H * 3 * 4)
    def get(s, k):
        while s.i < k:
            b = s.p.stdout.read(W * H * 3)
            if len(b) < W * H * 3: break
            s.last = np.frombuffer(b, np.uint8).reshape(H, W, 3); s.i += 1
        return s.last
    def close(s):
        try: s.p.stdout.close(); s.p.kill()
        except Exception: pass
enc = subprocess.Popen([FF, '-v', 'error', '-n', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                        '-i', str(full), '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
                        '-c:a', 'copy', '-t', f'{TOT / FPS:.6f}', '-movflags', '+faststart', str(dst)], stdin=subprocess.PIPE)
readers = {}; t0 = time.time()
for k in range(TOT):
    act = [i for i, g in enumerate(segs) if g['start'] <= k < g['start'] + g['frames']]
    if not act:  # gap (should not happen): hold the nearest previous segment's last frame
        act = [max(i for i, g in enumerate(segs) if g['start'] <= k)]
    for i in list(readers):
        if i not in act and i < min(act): readers.pop(i).close()
    fr = []
    for i in act:
        if i not in readers: readers[i] = Reader(segs[i])
        fr.append((i, readers[i].get(min(k - segs[i]['start'], segs[i]['frames'] - 1))))
    if len(fr) == 1: out = fr[0][1]
    else:
        (ia, a), (ib, b) = fr[0], fr[-1]
        ov = segs[ia]['start'] + segs[ia]['frames'] - segs[ib]['start']
        p = (k - segs[ib]['start'] + 1) / (ov + 1)
        out = cv2.addWeighted(a, 1 - p, b, p, 0)
    enc.stdin.write(out.tobytes())
    if k % 900 == 0: log('frame', k, '/', TOT, '%.1f fps' % ((k + 1) / (time.time() - t0)))
for r in readers.values(): r.close()
enc.stdin.close(); rc = enc.wait()
log('encode exit', rc, dst)
sys.exit(rc)
