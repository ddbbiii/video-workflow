"""Theme-independent, deterministic still-image camera renderer."""
import argparse
import hashlib
import json
import math
import re
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

ENGINE_VERSION = '1.2'
SUPPORTED_BACKENDS = ('affine', 'blender')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def progress(t, span, curve):
    p = min(1.0, max(0.0, t / span))
    mode = curve.get('type', 'linear')
    if mode == 'linear':
        return p
    if mode == 'smoothstep':
        return p * p * (3 - 2 * p)
    ramp = curve['ramp_s']
    integral = lambda x: x ** 3 - x ** 4 / 2
    if t < ramp:
        distance = ramp * integral(t / ramp)
    elif t > span - ramp:
        distance = span - ramp - ramp * integral((span - t) / ramp)
    else:
        distance = t - ramp / 2
    return distance / (span - ramp)


def validate_rect(rect, aspect, source_size):
    if not isinstance(rect, list) or len(rect) != 4:
        raise ValueError('View must be [x, y, width, height] in normalized source coordinates')
    x, y, w, h = rect
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in rect):
        raise ValueError('View coordinates must be finite numbers')
    if min(x, y) < 0 or min(w, h) <= 0 or x + w > 1 + 1e-9 or y + h > 1 + 1e-9:
        raise ValueError('View extends outside source image')
    sw, sh = source_size
    if not math.isclose(w * sw / (h * sh), aspect, rel_tol=1e-5):
        raise ValueError('View aspect ratio must match output; no image stretching allowed')


def load_plan(path):
    plan = json.loads(path.read_text(encoding='utf-8'))
    if plan.get('schema_version') != 1:
        raise ValueError('Expected schema_version 1')
    backend = plan.get('backend', 'affine')
    if backend not in SUPPORTED_BACKENDS:
        raise ValueError(f'Unknown backend {backend!r}; supported: {SUPPORTED_BACKENDS}. No silent fallback.')
    plan['backend'] = backend
    plan['_plan_dir'] = str(path.parent.resolve())
    width, height = plan['output']['width'], plan['output']['height']
    fps = plan['output']['fps']
    if any(type(v) is not int or v <= 0 for v in (width, height, fps)) or width % 2 or height % 2:
        raise ValueError('Output requires positive even dimensions and integer fps')
    if not plan['shots']:
        raise ValueError('At least one shot is required')
    ids = set()
    for shot in plan['shots']:
        name = shot['id']
        if not re.fullmatch(r'[A-Za-z0-9_-]+', name) or name in ids:
            raise ValueError('Shot IDs must be unique safe filenames')
        ids.add(name)
        source = (path.parent / shot['source']).resolve()
        shot['source'] = str(source)
        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image)
            shot['source_size'] = list(image.size)
        duration = shot['duration_s']
        if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
            raise ValueError('Duration must be finite and positive')
        frames = round(duration * fps)
        if frames < 2 or not math.isclose(duration * fps, frames, abs_tol=1e-6):
            raise ValueError('Duration must contain an integral number of frames, at least two')
        shot['frames'] = frames
        shot['span_s'] = (frames - 1) / fps
        for rect in (shot['start_view'], shot['end_view']):
            validate_rect(rect, width / height, shot['source_size'])
        curve = shot.get('curve', {'type': 'linear'})
        if curve.get('type') not in ('linear', 'smoothstep', 'ramped_linear'):
            raise ValueError('Unknown curve type')
        if curve['type'] == 'ramped_linear':
            ramp = curve.get('ramp_s', 0)
            if not isinstance(ramp, (int, float)) or not math.isfinite(ramp) or not 0 < ramp < shot['span_s'] / 2:
                raise ValueError('ramp_s must be positive and less than half the sampled span')
        shot['curve'] = curve
        # Convex interpolation retains image bounds and each required content rectangle.
        for safe in shot.get('required_regions', []):
            x, y, w, h = safe
            if not all(math.isfinite(v) for v in safe) or min(x, y) < 0 or min(w, h) <= 0 or x+w > 1 or y+h > 1:
                raise ValueError('Invalid required region')
            for vx, vy, vw, vh in (shot['start_view'], shot['end_view']):
                if x < vx - 1e-9 or y < vy - 1e-9 or x+w > vx+vw+1e-9 or y+h > vy+vh+1e-9:
                    raise ValueError(f'{name}: required subject would be cropped')
    transition = plan.get('transition_s', 0)
    if not isinstance(transition, (int, float)) or not math.isfinite(transition) or transition < 0 or transition >= min(s['duration_s'] for s in plan['shots']):
        raise ValueError('Invalid transition duration')
    if not math.isclose(transition * fps, round(transition * fps), abs_tol=1e-6):
        raise ValueError('Transition must align to output frames')
    return plan


def view_at(shot, index):
    p = progress(index * shot['span_s'] / (shot['frames'] - 1), shot['span_s'], shot['curve'])
    return np.array(shot['start_view']) * (1 - p) + np.array(shot['end_view']) * p


def sample_matrix(view, sw, sh, width, height):
    x, y, w, h = view
    sx, sy = w * sw / width, h * sh / height
    # Pixel-center convention avoids half-pixel shifts at identity transforms.
    return np.array([[sx, 0, x * sw + (sx - 1) / 2],
                     [0, sy, y * sh + (sy - 1) / 2]], dtype=np.float64)


def prepare_source(path, shot, width, height):
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert('RGB')
        # Prefilter large reductions once; retain extra source detail for closer views.
        min_w = min(shot['start_view'][2], shot['end_view'][2])
        min_h = min(shot['start_view'][3], shot['end_view'][3])
        scale = min(1.0, max(width / (image.width * min_w), height / (image.height * min_h)))
        if scale < 1:
            image = image.resize((math.ceil(image.width * scale), math.ceil(image.height * scale)), Image.Resampling.LANCZOS)
        return np.array(image)


def probe(path):
    data = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]))
    return data


def render_affine(shot, output, settings):
    width, height, fps = (settings[k] for k in ('width', 'height', 'fps'))
    source = prepare_source(shot['source'], shot, width, height)
    sh, sw = source.shape[:2]
    part = output.with_name(output.stem + '.partial.mp4')
    # File-backed stderr cannot deadlock the encoder's frame input pipe.
    with tempfile.TemporaryFile() as log:
        process = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{width}x{height}', '-r', str(fps), '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(part)], stdin=subprocess.PIPE, stderr=log)
        matrices = []
        try:
            for i in range(shot['frames']):
                matrix = sample_matrix(view_at(shot, i), sw, sh, width, height)
                frame = cv2.warpAffine(source, matrix, (width, height), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
                process.stdin.write(frame.tobytes())
                matrices.append(matrix.tolist())
            process.stdin.close()
            if process.wait() != 0:
                log.seek(0)
                raise RuntimeError(log.read().decode(errors='replace'))
        except BaseException:
            process.kill()
            process.wait()
            part.unlink(missing_ok=True)
            raise
    data = probe(part)
    stream = data['streams'][0]
    if len(data['streams']) != 1 or (stream['width'], stream['height']) != (width, height) or stream['avg_frame_rate'] != f'{fps}/1' or int(stream['nb_frames']) != shot['frames']:
        raise RuntimeError('Encoded stream differs from planned frame count/size/fps')
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(part), '-f', 'null', '-'], check=True, capture_output=True)
    part.replace(output)
    return matrices, {'backend': 'affine', 'source_size_rendered': [sw, sh]}


def trajectory_qa(shot, settings):
    centers, scales = [], []
    width, height = settings['width'], settings['height']
    for i in range(shot['frames']):
        x, y, w, h = view_at(shot, i)
        centers.append([(0.5-x) * width / w, (0.5-y) * height / h])
        scales.append(1 / w)
    return {'source_bounds_checked': True, 'required_regions_checked': True,
            'max_center_step_output_px': float(np.linalg.norm(np.diff(centers, axis=0), axis=1).max()),
            'max_scale_step': float(np.abs(np.diff(scales)).max()),
            'scope': 'Planned trajectory only; encoded motion and visual texture require separate QA'}


def make_overview(entries, plan, dest):
    inputs, filters = [], []
    fps = plan['output']['fps']
    for i, entry in enumerate(entries):
        inputs += ['-i', entry['video']]
        filters.append(f'[{i}:v]settb=AVTB,setpts=PTS-STARTPTS,fps={fps}[v{i}]')
    transition = plan.get('transition_s', 0)
    prior = 'v0'
    elapsed = entries[0]['duration_s']
    if transition:
        for i, entry in enumerate(entries[1:], 1):
            label = f'join{i}'
            filters.append(f'[{prior}][v{i}]xfade=transition=fade:duration={transition}:offset={elapsed-transition}[{label}]')
            prior = label
            elapsed += entry['duration_s'] - transition
    else:
        filters.append(''.join(f'[v{i}]' for i in range(len(entries))) + f'concat=n={len(entries)}:v=1:a=0[join]')
        prior = 'join'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex', ';'.join(filters), '-map', f'[{prior}]', '-an', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(dest)], check=True, capture_output=True)


def write_trajectory(path, shot, matrices, backend, source_size):
    write_json(path, {
        'coordinate_system': 'source_pixels_after_exif_top_left_origin' if backend == 'blender' else 'prepared_source_pixels_top_left_origin',
        'source_size': list(source_size),
        'backend': backend,
        'inverse_sample_matrices': matrices,
        'adjacent_frame_transform': 'inv(P_next) @ P_current',
        'shot': shot,
    })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('plan', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--blender', type=Path, default=None, help='Blender executable (overrides env/plan)')
    args = parser.parse_args()
    plan = load_plan(args.plan.resolve())
    if args.validate_only:
        print(f'Validated {len(plan["shots"])} shots backend={plan["backend"]}')
        return
    if plan['backend'] == 'blender':
        import blender_backend as bb
        blender_exe = bb.resolve_blender_exe(plan, explicit=args.blender)
    else:
        blender_exe = None
    args.out.mkdir(parents=True, exist_ok=True)
    manifest_path = args.out / 'manifest.json'
    if manifest_path.exists() and not args.resume:
        raise ValueError('Output run already exists; choose a new directory or --resume')
    if not manifest_path.exists() and list(args.out.glob('*.mp4')):
        raise ValueError('Directory has untracked videos; choose a new run directory')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {
        'engine_version': ENGINE_VERSION,
        'engine_sha256': digest(__file__),
        'plan': str(args.plan.resolve()),
        'backend': plan['backend'],
        'status': 'running',
        'shots': [],
    }
    planned_ids = {s['id'] for s in plan['shots']}
    if any(s['id'] not in planned_ids for s in manifest['shots']):
        raise ValueError('Resume plan removed existing shots; use a new run directory')
    manifest['status'] = 'running'
    cache_root = args.out / 'frame_cache'
    for shot in plan['shots']:
        destination = args.out / (shot['id'] + '.mp4')
        fingerprint = hashlib.sha256(json.dumps({
            'shot': shot, 'output': plan['output'], 'source_hash': digest(shot['source']),
            'engine': digest(__file__), 'backend': plan['backend'],
            'blender_scene': digest(Path(__file__).with_name('blender_scene.py')) if plan['backend'] == 'blender' else None,
            'blender_backend': digest(Path(__file__).with_name('blender_backend.py')) if plan['backend'] == 'blender' else None,
            'blender_options': {k: plan.get(k) for k in ('blender_engine', 'blender_use_gpu', 'blender_samples', 'blender_interpolation')} if plan['backend'] == 'blender' else None,
            'blender_exe': [str(blender_exe.resolve()), blender_exe.stat().st_mtime_ns, blender_exe.stat().st_size] if blender_exe else None,
        }, sort_keys=True, default=str).encode()).hexdigest()
        previous = next((s for s in manifest['shots'] if s['id'] == shot['id']), None)
        trajectory_path = args.out / (shot['id'] + '-trajectory.json')
        if previous and previous.get('status') == 'complete' and previous.get('fingerprint') == fingerprint and destination.exists() and digest(destination) == previous.get('video_sha256') and trajectory_path.exists() and digest(trajectory_path) == previous.get('trajectory_sha256'):
            print('Resume verified: ' + shot['id'], flush=True)
            continue
        if destination.exists():
            raise ValueError('Existing output differs; use a new run directory')
        entry = {'id': shot['id'], 'fingerprint': fingerprint, 'status': 'running', 'backend': plan['backend']}
        manifest['shots'] = [s for s in manifest['shots'] if s['id'] != shot['id']] + [entry]
        write_json(manifest_path, manifest)
        print(f'Rendering ({plan["backend"]}): ' + shot['id'], flush=True)
        try:
            if plan['backend'] == 'affine':
                matrices, timing = render_affine(shot, destination, plan['output'])
                source_size = timing['source_size_rendered']
            else:
                import blender_backend as bb
                matrices, timing = bb.render_shot(shot, destination, plan['output'], plan, blender_exe, cache_root)
                source_size = shot['source_size']
            write_trajectory(trajectory_path, shot, matrices, plan['backend'], source_size)
            entry.update(
                status='complete', video=str(destination.resolve()), video_sha256=digest(destination),
                duration_s=shot['duration_s'], qa=trajectory_qa(shot, plan['output']), timing=timing,
                trajectory_sha256=digest(trajectory_path),
            )
        except Exception as exc:
            entry.update(status='failed', error=str(exc))
            manifest['status'] = 'failed'
            write_json(manifest_path, manifest)
            raise
        write_json(manifest_path, manifest)
    if plan.get('overview', False):
        dest = args.out / 'overview.mp4'
        ordered = [next(s for s in manifest['shots'] if s['id'] == shot['id']) for shot in plan['shots']]
        make_overview(ordered, plan, dest)
        manifest['overview'] = str(dest.resolve())
    manifest['status'] = 'complete'
    manifest['limitations'] = [
        'Affine sampling uses OpenCV 1/32-pixel interpolation table.',
        'Blender backend uses orthographic camera + emission-textured plane; no parallax.',
        'No invented parallax, internal animation or depth.',
        'Rendered temporal tracking must be verified separately from planned trajectory.',
        'Missing Blender install fails hard; never silent-falls back to affine.',
    ]
    write_json(manifest_path, manifest)


if __name__ == '__main__':
    main()
