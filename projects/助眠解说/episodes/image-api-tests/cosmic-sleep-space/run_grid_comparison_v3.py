import json
import time
from pathlib import Path

from PIL import Image, ImageDraw
import run_api_test_v1 as api


ROOT = Path(__file__).resolve().parent
BASELINE = ROOT / 'runs' / '20261005-172652-independent-v2'
OUT = ROOT / 'runs' / (time.strftime('%Y%m%d-%H%M%S') + '-grid-comparison-v3')


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    api.OUT = OUT
    crops = OUT / 'crops'
    crops.mkdir()
    manifest = {'model': api.MODEL, 'size': api.SIZE, 'baseline': str(BASELINE),
                'reference_images': [], 'no_retry': True, 'ai_upscale': False,
                'results': [], 'mappings': []}
    for label, grid, count in [('B', 2, 4), ('C', 3, 9)]:
        first = (BASELINE / 'A01-prompt.txt').read_text(encoding='utf-8')
        common = first.split('\n\n行星晨昏线')[0]
        common = common.replace('单幅电脑横屏画面，目标严格 16:9，不是拼图、联系表或分镜网格。', '')
        prompt = (f'生成一张严格等分的{grid}x{grid}网格图，总画幅16:9，每格也为横屏16:9。'
                  '格子没有间距、装饰边框、文字或编号；不同场景只能在各自格子内，不能跨格。'
                  '以下位置和编号只用于指令，不要画到图中。\n' + common)
        for idx in range(count):
            scene = f'A{idx + 1:02d}'
            original = (BASELINE / f'{scene}-prompt.txt').read_text(encoding='utf-8')
            body = original.split('\n\n', 1)[1]
            prompt += f'\n\n第{idx // grid + 1}行第{idx % grid + 1}列：\n{body}'
        (OUT / f'{label}-prompt.txt').write_text(prompt, encoding='utf-8')
        print(f'Requesting {label}: {grid}x{grid}, one call', flush=True)
        try:
            result = api.call(label, prompt)
        except Exception as exc:
            result = {'label': label, 'ok': False, 'error_type': type(exc).__name__, 'error': 'no retry'}
        manifest['results'].append(result)
        (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if not result.get('ok'):
            return 1
        with Image.open(result['image']) as im:
            width, height = im.size
            for idx in range(count):
                scene = f'A{idx + 1:02d}'
                col, row = idx % grid, idx // grid
                box = (round(col * width / grid), round(row * height / grid),
                       round((col + 1) * width / grid), round((row + 1) * height / grid))
                image = im.crop(box)
                target = crops / f'{label}-{scene}.png'
                image.save(target)
                manifest['mappings'].append({'batch': label, 'baseline': str(BASELINE / f'{scene}.png'),
                                             'crop': str(target), 'box': box, 'size': image.size})
        (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    preview = OUT / 'comparison-previews'
    preview.mkdir()
    for idx in range(1, 10):
        scene = f'A{idx:02d}'
        paths = [('A independent', BASELINE / f'{scene}.png')]
        if idx <= 4:
            paths.append(('B 2x2 crop', crops / f'B-{scene}.png'))
        paths.append(('C 3x3 crop', crops / f'C-{scene}.png'))
        sheet = Image.new('RGB', (960, 574 * len(paths)), '#202020')
        draw = ImageDraw.Draw(sheet)
        for row, (name, path) in enumerate(paths):
            with Image.open(path) as image:
                draw.text((12, row * 574 + 8), f'{scene}: {name} | native {image.width}x{image.height} | preview 960x540 Lanczos', fill='white')
                sheet.paste(image.convert('RGB').resize((960, 540), Image.Resampling.LANCZOS), (0, row * 574 + 34))
        sheet.save(preview / f'{scene}-comparison.jpg', quality=94)
    print(f'Completed: {OUT}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
