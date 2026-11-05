"""Build motion_plan.json, affine plan configs and MOTION_PLAN.md (read-only on old timeline / stills)."""
import json, os, sys
from pathlib import Path
from PIL import Image
HERE = Path(__file__).resolve().parent; RUN = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\video\clips')  # 2026-10-08 迁移：原批次 20261007-v3-motion-b01 根目录，现为单集 video\clips
sys.path.insert(0, str(HERE)); import shots
P = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal')  # b-geomagnetic-reversal 单集目录
STILLS = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\image\stills\20261007-v3-stills-b01')
TL = P / 'audio' / 'draft_dof_vo_v4'; TLA = P / 'archive' / 'edit' / 'draft_dof_vo_v4'  # inventory 在 audio，shots 在 archive
FPS = 30
sel = {s['shot']: s for s in json.loads((STILLS / 'selected.json').read_text(encoding='utf-8'))}
inv = json.loads((TL / 'inventory.json').read_text(encoding='utf-8'))
dur = {s['shot']: s['out_dur'] for s in inv['shots']}
old_treat = {s['shot']: s['treatment'] for s in inv['shots']}
def _keys(n): return set(k for k in json.loads((HERE / n).read_text(encoding='utf-8')) if not k.startswith('_'))
clean = _keys('clean_regions.json')
clean_v2 = _keys('clean_regions_v2.json') if (HERE / 'clean_regions_v2.json').exists() and (Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\image\stills') / 'inputs_clean_v2').exists() else set()
def clean_path(s):  # v2 (wider dial blur) wins over v1
    return Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\image\stills') / ('inputs_clean_v2' if s in clean_v2 else 'inputs_clean') / (s + '_clean.png')
ESR = [s for s in sel if sel[s]['realesrgan'] == '是']
ESR_MODE = '--esrgan' in sys.argv
PLAN_ONLY = '--plan-only' in sys.argv          # rewrite motion_plan.json only
SUBSET = sys.argv[sys.argv.index('--subset') + 1].split(',') if '--subset' in sys.argv else None
OUTNAME = sys.argv[sys.argv.index('--name') + 1] if '--name' in sys.argv else None
def clamp(v, a, b): return max(a, min(b, v))
def views(W, H, typ, fx, fy, d, lowres):
    ar = 16 / 9; ia = W / H
    fw, fh = (ar / ia, 1.0) if ia > ar else (1.0, ia / ar)   # full 16:9 box (normalized)
    def box(scale, cx, cy):
        w, h = fw * scale, fh * scale
        x = clamp(cx - w / 2, 0, 1 - w); y = clamp(cy - h / 2, 0, 1 - h)
        return [round(x, 6), round(y, 6), round(w, 6), round(h, 6)]
    if typ in ('in', 'out'):
        z = 1.04 if d < 2.5 else clamp(1.04 + 0.012 * d, 1.05, 1.12 if lowres else 1.18)
        a = box(0.97, 0.5, 0.5); b = box(0.97 / z, fx, fy)
        s, e = (a, b) if typ == 'in' else (b, a)
        mag = 'zoom x%.3f' % z
    else:
        sh = clamp(0.03 + 0.004 * d, 0.035, 0.09)   # fraction of output width
        sc = 0.90; w = fw * sc
        span = sh * w
        cx0 = clamp(fx - span / 2, w / 2, 1 - w / 2); cx1 = clamp(cx0 + span, w / 2, 1 - w / 2); cx0 = cx1 - span
        a = box(sc, cx0, fy); b = box(sc, cx1, fy)
        s, e = (a, b) if typ == 'pan_r' else (b, a)
        mag = 'pan %.1f%% of frame width' % (100 * sh)
    return s, e, mag
plan = []; affine_shots = []
for sp in sel.values():
    s = sp['shot']; method, typ, fx, fy, why = shots.S[s]
    d = dur[s]; frames = round(d * FPS); dq = frames / FPS
    still = STILLS / sp['final_file']
    src = clean_path(s) if s in clean else still
    esr_out = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\image\stills') / 'esrgan_x4' / (s + '_x4.png')
    use_esr = ESR_MODE and s in ESR and esr_out.exists()
    aff_src = esr_out if use_esr else src
    W, H = Image.open(aff_src).size
    lowres = W < 1500
    sv, ev, mag = views(W, H, typ, fx, fy, dq, lowres)
    entry = dict(shot=s, method=method, motion=typ, focus=[fx, fy], reason=why, old_duration_s=d, frames_30fps=frames, duration_s=dq,
                 old_timeline_shot=str(TLA / 'shots' / (s + '.mp4')), old_treatment=old_treat[s],
                 still_selected=str(still), still_verdict=sp['verdict'], cleaned_input=str(src) if s in clean else None,
                 realesrgan_candidate=s in ESR, affine_input=str(aff_src), affine_input_size=[W, H], affine_magnitude=mag,
                 start_view=sv, end_view=ev)
    if method == 'i2v':
        loop, prompt = shots.I2V_PROMPTS[s]
        entry.update(i2v_engine='LTX-2.3 distilled (ManualSigmas, portable ComfyUI 8191)', i2v_input=str(src), i2v_prompt=prompt, i2v_negative=shots.NEGATIVE,
                     i2v_spec='1280x704, 121 frames @24fps (~5.0s), seed 42', loop_mode=loop, vsr='RealBasicVSR x4 (shared/video-restoration) on 16:9 crop 1248x702', fallback='affine (same motion/focus)')
    plan.append(entry)
    if ((not ESR_MODE) or use_esr) and (SUBSET is None or s in SUBSET):
        affine_shots.append({"id": s, "source": os.path.relpath(aff_src, RUN / 'affine_cfg'), "duration_s": dq, "start_view": sv, "end_view": ev,
                             "curve": {"type": "ramped_linear", "ramp_s": round(min(0.75, 0.2 * dq), 3)}})
(RUN / 'affine_cfg').mkdir(exist_ok=True)
cfg = {"schema_version": 1, "backend": "affine", "output": {"width": 1920, "height": 1080, "fps": FPS}, "overview": False, "transition_s": 0, "shots": affine_shots}
name = OUTNAME or ('affine_esrgan.json' if ESR_MODE else 'affine_all.json')
if not PLAN_ONLY:
    if (RUN / 'affine_cfg' / name).exists(): sys.exit('refuse to overwrite affine_cfg/' + name)
    (RUN / 'affine_cfg' / name).write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding='utf-8')
if not ESR_MODE and SUBSET is None:
    (RUN / 'motion_plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding='utf-8')
print(name, len(affine_shots), 'i2v', sum(1 for p in plan if p['method'] == 'i2v'), 'total_s', round(sum(p['duration_s'] for p in plan), 2))
