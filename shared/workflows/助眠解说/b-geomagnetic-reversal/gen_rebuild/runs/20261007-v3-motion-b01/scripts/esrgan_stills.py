"""RealESRGAN x4plus on the 15 registered still candidates (GPU; run only via gpu_job.py after the queue grants)."""
import json, sys, time, hashlib
from pathlib import Path
import numpy as np, torch
from PIL import Image
HERE = Path(__file__).resolve().parent; RUN = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\video\clips')  # 2026-10-08 迁移：原批次 20261007-v3-motion-b01 根目录，现为单集 video\clips
ROOT = Path(r'E:\program\1project\video')
sys.path.insert(0, str(ROOT / 'shared' / 'camera-motion'))
from blender_backend import acquire_gpu_lock, release_gpu_lock
from spandrel import ModelLoader
STILLS = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\image\stills\20261007-v3-stills-b01')
MODEL = ROOT / 'shared/runtime/comfy/models/models/upscale_models/RealESRGAN_x4plus.pth'
sel = json.loads((STILLS / 'selected.json').read_text(encoding='utf-8'))
cands = [s for s in sel if s['realesrgan'] == '是']
out = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\image\stills') / 'esrgan_x4'; out.mkdir(exist_ok=True)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def upscale(model, img, tile=512, pad=24):
    x = torch.from_numpy(np.asarray(img).astype(np.float32) / 255.).permute(2, 0, 1)[None].cuda().half()
    _, _, H, W = x.shape; S = 4
    res = torch.zeros((1, 3, H * S, W * S), dtype=torch.float16, device='cuda')
    for y0 in range(0, H, tile):
        for x0 in range(0, W, tile):
            y1, x1 = min(y0 + tile, H), min(x0 + tile, W)
            ya, xa, yb, xb = max(0, y0 - pad), max(0, x0 - pad), min(H, y1 + pad), min(W, x1 + pad)
            with torch.no_grad():
                o = model(x[:, :, ya:yb, xa:xb])
            res[:, :, y0*S:y1*S, x0*S:x1*S] = o[:, :, (y0-ya)*S:(y0-ya)*S+(y1-y0)*S, (x0-xa)*S:(x0-xa)*S+(x1-x0)*S]
    return Image.fromarray((res[0].float().clamp(0, 1).permute(1, 2, 0).cpu().numpy() * 255 + .5).astype(np.uint8))
def main():
    lock = acquire_gpu_lock(owner='zhumian-geomag-v3-esrgan-stills', timeout_s=600)
    log = []
    try:
        model = ModelLoader().load_from_file(str(MODEL)).model.cuda().eval().half()
        for s in cands:
            cl2 = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\image\stills') / 'inputs_clean_v2' / (s['shot'] + '_clean.png'); cl = cl2 if cl2.exists() else Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\image\stills') / 'inputs_clean' / (s['shot'] + '_clean.png')
            src = cl if cl.exists() else STILLS / s['final_file']
            t = time.time(); img = Image.open(src).convert('RGB')
            up = upscale(model, img); dst = out / (s['shot'] + '_x4.png'); up.save(dst)
            log.append(dict(shot=s['shot'], input=str(src), input_size=list(img.size), output=str(dst), output_size=list(up.size), output_sha256=sha(dst),
                            model='RealESRGAN_x4plus (spandrel, fp16, tile 512/pad 24)', seconds=round(time.time() - t, 1)))
            print(s['shot'], img.size, '->', up.size, '%.1fs' % (time.time() - t), flush=True)
            (out / 'esrgan_manifest.json').write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding='utf-8')
    finally:
        release_gpu_lock(lock)
    print('DONE', len(log))
if __name__ == '__main__':
    main()
