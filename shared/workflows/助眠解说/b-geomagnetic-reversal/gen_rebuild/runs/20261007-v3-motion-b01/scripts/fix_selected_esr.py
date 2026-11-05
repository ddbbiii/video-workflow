"""One-off: correct superres note for ESRGAN candidates that use cleaned-v2 input (ch6-c02, ch6-c03) in MOTION_SELECTED.md + final_manifest.json."""
import json
from pathlib import Path
RUN = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\video\clips')  # 2026-10-08 迁移：原批次 20261007-v3-motion-b01 根目录，现为单集 video\clips
NEW = '无（RealESRGAN 候选，队列未放行，原图推拉）；输入为去伪字 v2'
md = (RUN / 'MOTION_SELECTED.md').read_text(encoding='utf-8').splitlines()
for i, l in enumerate(md):
    if l.startswith('| ch6-c02 |') or l.startswith('| ch6-c03 |'): md[i] = l.replace('无（输入为去伪字 v2）', NEW)
    if l.startswith('> 状态'): md[i] = l.replace('RealESRGAN 候选 13 镜', 'RealESRGAN 候选 15 镜')
(RUN / 'MOTION_SELECTED.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
fm = json.loads((RUN / 'final' / 'final_manifest.json').read_text(encoding='utf-8'))
for r in fm:
    if r['shot'] in ('ch6-c02', 'ch6-c03'): r['superres_vsr'] = NEW
(RUN / 'final' / 'final_manifest.json').write_text(json.dumps(fm, ensure_ascii=False, indent=1), encoding='utf-8')
print('fixed')
