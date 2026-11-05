import hashlib
import json
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw
from spandrel import ModelLoader

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'runs' / '20261006-013437-grid-comparison-v3'
BASE = ROOT / 'runs' / '20261005-172652-independent-v2'
MODEL = ROOT.parents[3] / 'comfy' / 'models' / 'models' / 'upscale_models' / 'RealESRGAN_x4plus.pth'
OUT = ROOT / 'runs' / (time.strftime('%Y%m%d-%H%M%S') + '-upscale-v4')


def upscale(image, model):
    arr = np.asarray(image).copy()
    height, width = arr.shape[:2]
    result = np.empty((height * 4, width * 4, 3), dtype=np.uint8)
    # Context overlap is discarded, leaving non-overlapping output cores.
    with torch.inference_mode():
        for y in range(0, height, 128):
            for x in range(0, width, 128):
                right, bottom = min(x + 128, width), min(y + 128, height)
                x0, y0 = max(0, x - 16), max(0, y - 16)
                x1, y1 = min(width, right + 16), min(height, bottom + 16)
                tile = torch.from_numpy(arr[y0:y1, x0:x1].copy()).permute(2, 0, 1).unsqueeze(0).float().cuda() / 255
                prediction = model(tile).clamp(0, 1)
                pixels = (prediction[0].permute(1, 2, 0).cpu().numpy() * 255).round().astype(np.uint8)
                result[y*4:bottom*4, x*4:right*4] = pixels[(y-y0)*4:(bottom-y0)*4, (x-x0)*4:(right-x0)*4]
    return Image.fromarray(result)


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    model = ModelLoader().load_from_file(str(MODEL)).cuda().eval()
    assert model.scale == 4
    records = []
    manifest = {'model': str(MODEL), 'model_sha256': hashlib.sha256(MODEL.read_bytes()).hexdigest(),
                'target': [1920, 1080], 'tile': 128, 'overlap': 16, 'device': 'cuda',
                'no_api': True, 'results': records}
    for scene in ['A02', 'A03', 'A05']:
        with Image.open(BASE / f'{scene}.png') as img:
            img.convert('RGB').resize((1920, 1080), Image.Resampling.LANCZOS).save(OUT / f'{scene}-A-reference.png')
        for batch in ['B', 'C']:
            src = SOURCE / 'crops' / f'{batch}-{scene}.png'
            if not src.exists():
                continue
            with Image.open(src) as img:
                image = img.convert('RGB')
            lanczos = OUT / f'{scene}-{batch}-lanczos.png'
            image.resize((1920, 1080), Image.Resampling.LANCZOS).save(lanczos)
            start = time.time()
            torch.cuda.reset_peak_memory_stats()
            intermediate = upscale(image, model)
            intermediate.save(OUT / f'{scene}-{batch}-realesrgan-native4x.png')
            output = OUT / f'{scene}-{batch}-realesrgan-1080.png'
            intermediate.resize((1920, 1080), Image.Resampling.LANCZOS).save(output)
            rec = {'scene': scene, 'batch': batch, 'source': str(src), 'source_size': list(image.size),
                   'lanczos': str(lanczos), 'output': str(output), 'intermediate_size': list(intermediate.size),
                   'seconds': round(time.time()-start, 2), 'peak_allocated_mb': round(torch.cuda.max_memory_allocated()/1048576, 1)}
            records.append(rec)
            (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps(rec), flush=True)
    del model
    torch.cuda.empty_cache()
    for scene in ['A02', 'A03', 'A05']:
        paths = [OUT / f'{scene}-A-reference.png']
        for batch in ['B', 'C']:
            paths += [p for p in [OUT / f'{scene}-{batch}-lanczos.png', OUT / f'{scene}-{batch}-realesrgan-1080.png'] if p.exists()]
        sheet = Image.new('RGB', (960, 564 * len(paths)), '#202020')
        draw = ImageDraw.Draw(sheet)
        for idx, path in enumerate(paths):
            draw.text((8, idx*564+4), path.stem, fill='white')
            with Image.open(path) as im:
                sheet.paste(im.resize((960, 540), Image.Resampling.LANCZOS), (0, idx*564+24))
        sheet.save(OUT / f'{scene}-overview.jpg', quality=94)
    print('OUT=' + str(OUT), flush=True)


if __name__ == '__main__':
    main()
