import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import camera_motion as cm
import verify_motion as vm

try:
    import blender_backend as bb
except Exception:  # pragma: no cover
    bb = None


class CameraTests(unittest.TestCase):
    def test_ramp_endpoints_and_velocity(self):
        curve = {'type': 'ramped_linear', 'ramp_s': 0.5}
        self.assertEqual(cm.progress(0, 5, curve), 0)
        self.assertEqual(cm.progress(5, 5, curve), 1)
        samples = np.array([cm.progress(t, 5, curve) for t in np.linspace(0, 5, 501)])
        self.assertTrue(np.all(np.diff(samples) >= 0))
        self.assertLess(np.std(np.diff(samples)[60:440]), 1e-12)

    def test_subpixel_translation(self):
        source = np.random.default_rng(12).integers(0, 256, (180, 320), dtype=np.uint8)
        source = cv2.GaussianBlur(source, (0, 0), 3)
        first = cv2.warpAffine(source, np.array([[1., 0, 0], [0, 1., 0]]), (320, 180))
        second = cv2.warpAffine(source, np.array([[1., 0, .13], [0, 1., .07]]), (320, 180), flags=cv2.INTER_CUBIC)
        _, affine = cv2.findTransformECC(first[10:-10, 10:-10], second[10:-10, 10:-10], np.eye(2, 3, dtype=np.float32), cv2.MOTION_TRANSLATION)
        self.assertLess(abs(float(affine[0, 2]) - .13), .04)
        self.assertLess(abs(float(affine[1, 2]) - .07), .04)

    def test_reject_stretch_and_out_of_bounds(self):
        with self.assertRaises(ValueError):
            cm.validate_rect([0, 0, 1, 1], 16/9, [800, 800])
        with self.assertRaises(ValueError):
            cm.validate_rect([.1, 0, 1, 1], 16/9, [1600, 900])

    def test_identity_pixel_centers(self):
        np.testing.assert_allclose(cm.sample_matrix([0, 0, 1, 1], 320, 180, 320, 180), [[1, 0, 0], [0, 1, 0]])

    def test_unknown_backend_no_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.fromarray(np.zeros((180, 320, 3), dtype=np.uint8)).save(root / 'a.png')
            plan = {'schema_version': 1, 'backend': 'mystery', 'output': {'width': 320, 'height': 180, 'fps': 24},
                    'shots': [{'id': 'x', 'source': 'a.png', 'duration_s': 1, 'start_view': [0, 0, 1, 1], 'end_view': [0, 0, 1, 1]}]}
            path = root / 'p.json'
            path.write_text(json.dumps(plan))
            with self.assertRaises(ValueError) as ctx:
                cm.load_plan(path)
            self.assertIn('No silent fallback', str(ctx.exception))

    def test_blender_missing_exe_fails_hard(self):
        if bb is None:
            self.skipTest('blender_backend missing')
        with self.assertRaises(bb.BlenderUnavailable):
            bb.resolve_blender_exe(plan={}, explicit=Path('Z:/definitely/missing/blender.exe'))

    def test_render_landscape_portrait_resume_and_variable_duration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, dims in [('wide', (640, 360)), ('tall', (360, 640))]:
                Image.fromarray(np.random.default_rng(1).integers(0, 256, (dims[1], dims[0], 3), dtype=np.uint8)).save(root / (name + '.png'))
                width, height = (320, 180) if name == 'wide' else (180, 320)
                plan = {'schema_version': 1, 'backend': 'affine', 'output': {'width': width, 'height': height, 'fps': 24}, 'overview': True, 'transition_s': .125,
                        'shots': [{'id': 'pan', 'source': name+'.png', 'duration_s': 1, 'start_view': [.02, .05, .9, .9], 'end_view': [.08, .05, .9, .9], 'curve': {'type': 'ramped_linear', 'ramp_s': .2}},
                                  {'id': 'push', 'source': name+'.png', 'duration_s': .5, 'start_view': [.05, .05, .9, .9], 'end_view': [.08, .08, .84, .84]}]}
                path = root / (name+'.json')
                path.write_text(json.dumps(plan))
                out = root / name
                command = [sys.executable, str(Path(cm.__file__)), str(path), '--out', str(out)]
                subprocess.run(command, check=True, capture_output=True)
                checked = vm.actual_motion(out / 'pan.mp4', out / 'pan-trajectory.json')
                self.assertEqual(checked['decoded_frames'], 24)
                self.assertEqual(checked['measured_count'], 23)
                self.assertLess(checked['residual_rms_px'], .08)
                before = cm.digest(out / 'pan.mp4')
                resumed = subprocess.run(command + ['--resume'], check=True, capture_output=True, text=True)
                self.assertIn('Resume verified: pan', resumed.stdout)
                self.assertEqual(before, cm.digest(out / 'pan.mp4'))
                info = cm.probe(out / 'overview.mp4')
                self.assertAlmostEqual(float(info['format']['duration']), 1.375, places=2)
                plan['shots'][0]['end_view'] = [.07, .05, .9, .9]
                path.write_text(json.dumps(plan))
                changed = subprocess.run(command + ['--resume'], capture_output=True)
                self.assertNotEqual(changed.returncode, 0)

    def test_blender_smoke_if_available(self):
        if bb is None:
            self.skipTest('blender_backend missing')
        exe = os.environ.get('CAMERA_MOTION_BLENDER')
        if not exe or not Path(exe).is_file():
            try:
                exe = str(bb.resolve_blender_exe({}))
            except bb.BlenderUnavailable:
                self.skipTest('Blender not installed')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Checkerboard for UV/direction verification
            img = np.zeros((180, 320, 3), dtype=np.uint8)
            img[::20, :, :] = 255
            img[:, ::20, :] = 255
            img[:40, :40] = (255, 0, 0)  # top-left red marker
            img[-40:, -40:] = (0, 255, 0)  # bottom-right green
            Image.fromarray(img).save(root / 'c.png')
            plan = {
                'schema_version': 1, 'backend': 'blender', 'blender_engine': 'CYCLES', 'blender_use_gpu': False,
                'output': {'width': 160, 'height': 90, 'fps': 12},
                'shots': [{
                    'id': 'pan', 'source': 'c.png', 'duration_s': 0.5,
                    'start_view': [0.0, 0.0, 1.0, 1.0],
                    'end_view': [0.05, 0.0, 0.95, 0.95],
                    'curve': {'type': 'linear'},
                }],
            }
            path = root / 'p.json'
            path.write_text(json.dumps(plan))
            out = root / 'out'
            cmd = [sys.executable, str(Path(cm.__file__)), str(path), '--out', str(out), '--blender', exe]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.fail(result.stdout + '\n' + result.stderr)
            traj = json.loads((out / 'pan-trajectory.json').read_text(encoding='utf-8'))
            self.assertEqual(traj['backend'], 'blender')
            self.assertEqual(traj['coordinate_system'], 'source_pixels_after_exif_top_left_origin')
            self.assertEqual(len(traj['inverse_sample_matrices']), 6)
            manifest = json.loads((out / 'manifest.json').read_text(encoding='utf-8'))
            report = manifest['shots'][0]['timing']['blender_report']
            self.assertLess(report['max_projection_boundary_error_source_px'], .005)
            self.assertEqual(report['samples'], 4)
            # Marker check on lossless cache frame 0 (encoded video may soft-clamp).
            import blender_backend as bb2
            png = next((out / 'frame_cache' / 'pan').glob('*/frames/frame_00000.png'))
            frame = cv2.imread(str(png))
            self.assertIsNotNone(frame)
            tl = frame[2:18, 2:18]
            br = frame[-18:-2, -18:-2]
            # BGR: red TL => channel 2 high; green BR => channel 1 high
            self.assertGreater(float(tl[:, :, 2].mean()), 150)
            self.assertGreater(float(tl[:, :, 2].mean()), float(tl[:, :, 1].mean()))
            self.assertGreater(float(br[:, :, 1].mean()), 150)

    def test_frame_cache_validates_png_and_dimensions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'frame_00000.png'
            path.write_bytes(b'corrupt')
            self.assertFalse(bb.complete_frames(Path(directory), 1, (32, 18)))
            Image.new('RGB', (32, 18)).save(path)
            self.assertTrue(bb.complete_frames(Path(directory), 1, (32, 18)))
            self.assertFalse(bb.complete_frames(Path(directory), 1, (18, 32)))

    def test_copy_plan_preserves_relative_source(self):
        import compare_backends as compare
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'original').mkdir()
            source = root / 'original' / 'plan.json'
            source.write_text(json.dumps({'shots': [{'source': '../image.png'}]}))
            destination = root / 'copy.json'
            compare.copy_plan_resolving_sources(source, destination)
            self.assertEqual(json.loads(destination.read_text())['shots'][0]['source'], str((root / 'image.png').resolve()))

    def test_configured_blender_path_does_not_fall_through(self):
        with self.assertRaises(bb.BlenderUnavailable):
            bb.resolve_blender_exe({'blender_exe': 'definitely-missing-blender.exe'})

    def test_gpu_lock_unknown_or_same_pid_is_not_reclaimed(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / 'gpu.lock'
            for payload in ('', '{bad', json.dumps({'pid': os.getpid(), 'owner': 'other'})):
                lock.write_text(payload)
                with self.assertRaises(TimeoutError):
                    bb.acquire_gpu_lock({'gpu_lock': str(lock)}, timeout_s=-1)
                self.assertEqual(lock.read_text(), payload)

    def test_render_engine_failure_does_not_switch_engine(self):
        import blender_scene
        class Render:
            class Settings:
                pass
            image_settings = Settings()
            @property
            def engine(self):
                return 'CYCLES'
            @engine.setter
            def engine(self, value):
                raise ValueError('engine unavailable')
        class Scene:
            render = Render()
        with self.assertRaisesRegex(RuntimeError, 'requested render engine'):
            blender_scene.configure_render(Scene(), 320, 180, 'BLENDER_EEVEE_NEXT', False)


if __name__ == '__main__':
    unittest.main()
