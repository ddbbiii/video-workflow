"""Focused, reproducible geometry/sampling review; writes only new run assets."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--blender', required=True)
    parser.add_argument('--probe', action='store_true')
    parser.add_argument('--samples', type=int, default=16)
    parser.add_argument('--pairs', default='matrix_land_same,matrix_port_same,matrix_cross_land_to_port,matrix_cross_port_to_land,matrix_materials_land,matrix_materials_port')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    pairs = args.pairs.split(',')
    summary = []
    for name in pairs:
        plan = json.loads((ROOT / 'testdata' / 'configs' / (name + '_blender.json')).read_text())
        shots = [s for s in plan['shots'] if ('2s' in s['id'] and ('push' in s['id'] or 'pull' in s['id'] or 'combo' in s['id']))
                 or ('combo' in s['id'] and ('cross' in name or 'port_same' in name))]
        if 'materials' in name:
            shots = [s for s in shots if 'stars' in s['id']]
        if not shots:
            continue
        plan['shots'] = shots
        plan['blender_samples'] = args.samples
        for shot in shots:
            shot['source'] = str((ROOT / 'testdata' / 'configs' / shot['source']).resolve())
            if args.probe:
                shot['duration_s'] = .4
                shot['curve'] = {'type': 'linear'}
        plan['overview'] = False
        config = args.out / (name + '.json')
        config.write_text(json.dumps(plan, indent=2))
        output = args.out / name
        subprocess.run([sys.executable, str(ROOT / 'camera_motion.py'), str(config), '--out', str(output), '--blender', args.blender], check=True)
        subprocess.run([sys.executable, str(ROOT / 'verify_motion.py'), str(output)], check=True)
        qa = json.loads((output / 'qa.json').read_text())
        manifest = json.loads((output / 'manifest.json').read_text())
        for shot in qa['shots']:
            timing = next(s['timing'] for s in manifest['shots'] if s['id'] == shot['id'])
            summary.append({'pair': name, 'id': shot['id'], 'status': shot['status'],
                            'rms': shot['motion']['residual_rms_px'], 'ecc_min': shot['motion']['ecc_min'],
                            'render_s': timing['render_s'], 'total_s': timing['total_s']})
        (args.out / 'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
