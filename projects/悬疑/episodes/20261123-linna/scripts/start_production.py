"""Prepare the locked story and generate the approved two-image introduction."""
from pathlib import Path
import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import re
import tempfile
import os
import threading
import subprocess
import time
import base64

from PIL import Image, ImageOps

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[3]
POLICY = json.loads((ROOT / 'shared/image-api/channel-policy.json').read_text())
ACTIVE = POLICY['policies'][POLICY['active']]
ROUTE_LOCKS = {name: threading.Lock() for name in ACTIVE['parallel_channels']}
DETECTIVE = ('Chinese male detective aged 28, lean build, short straight black hair, '
             'narrow oval face, straight eyebrows, dark brown eyes, light blue short-sleeved '
             'police shirt with plain dark shoulder tabs, charcoal trousers and black shoes. '
             'No readable badge, no lettering, no numbers.')


def curl_call(api, channel, prompt, tag, reference, attempt, folder):
    """Use the system TLS client; credentials go via stdin, never command arguments."""
    start = time.monotonic()
    if reference:
        payload, ctype = api.multipart({'model':channel['model'], 'prompt':prompt,
                                       'size':channel['size'], 'n':'1'}, {'image':reference})
        endpoint = 'edits'
    else:
        payload = json.dumps({'model':channel['model'], 'prompt':prompt,
                              'size':channel['size'], 'n':1}).encode()
        ctype = 'application/json'
        endpoint = 'generations'
    root = Path(folder)
    body = root / 'request.bin'; response = root / 'response.json'
    body.write_bytes(payload)
    key = api.key_for(channel['key_env'])
    conf = '\n'.join([
        'url = '+json.dumps(channel['base_url']+'/images/'+endpoint),
        'header = '+json.dumps('Authorization: Bearer '+key),
        'header = '+json.dumps('Content-Type: '+ctype),
        'header = '+json.dumps('User-Agent: '+api.UA),
        'data-binary = '+json.dumps('@'+str(body)),
        'output = '+json.dumps(str(response)),
        'write-out = "%{http_code}"', 'silent', 'show-error',
        'connect-timeout = 20', 'max-time = 150'])
    run = subprocess.run(['curl','--config','-'],input=conf,text=True,capture_output=True)
    status = int(run.stdout) if run.stdout.isdigit() else 0
    info = dict(shot=tag,channel=channel['name'],model=channel['model'],attempt=attempt,
                endpoint=endpoint,prompt=prompt,request_size=channel['size'],
                price_cny=channel['price_cny'],http_status=status,
                elapsed_s=round(time.monotonic()-start,1),transport='system-curl-tls')
    if run.returncode or status!=200:
        category='curl_or_http_error'
        if response.exists():
            try:
                failure=json.loads(response.read_bytes());error=failure.get('error',{})
                message=str(error.get('message','')).lower() if isinstance(error,dict) else ''
                if '无可用渠道' in message or 'no available channel' in message:category='upstream_no_available_channel'
                elif 'size' in message or 'resolution' in message:category='size_rejected'
                elif 'quota' in message or '额度' in message:category='quota_unavailable'
                elif 'model' in message:category='model_route_error'
            except Exception:pass
        if run.returncode:
            category={6:'dns_resolution_failed',7:'connection_failed',28:'request_timeout',
                      35:'tls_handshake_failed',52:'empty_response',56:'connection_reset',
                      60:'certificate_verification_failed'}.get(run.returncode,'transport_failed')
        return dict(info,ok=False,error=category,curl_exit=run.returncode)
    try:
        data=json.loads(response.read_bytes());item=data['data'][0]
        dest=root/(tag+'.png')
        if item.get('b64_json'):
            dest.write_bytes(base64.b64decode(item['b64_json']))
        elif item.get('url'):
            download_conf='\n'.join(['url = '+json.dumps(item['url']),
                'output = '+json.dumps(str(dest)), 'silent','show-error','location','max-time = 150'])
            download=subprocess.run(['curl','--config','-'],input=download_conf,text=True,capture_output=True)
            if download.returncode:raise ValueError('download_failed')
        else:raise ValueError('missing_image')
        with Image.open(dest) as im:
            im.load();dims=list(im.size)
        return dict(info,ok=True,file=dest.name,dims=dims,
                    sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
    except Exception:
        return dict(info,ok=False,error='response_or_image_invalid')


def prepare():
    for folder in ['story', 'storyboard', 'image/plates', 'image/anchors',
                   'image/intro/v1', 'logs', 'qa', 'video/final']:
        (EP / folder).mkdir(parents=True, exist_ok=True)
    source = ROOT / 'projects/悬疑/planning/林娜案-最小修改标注稿.md'
    text = source.read_text().split('---\n\n', 1)[1].strip()
    text = re.sub(r'【新增[^\n]*】\n?', '', text)
    (EP / 'story/script.md').write_text(text + '\n')
    count = len(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]', re.sub(r'^\d+\.\s*$', '', text, flags=re.M)))
    state = ('# 林娜案｜当前生产状态\n\n'
             '- 正文：用户确认的原文，仅新增信息来源与结案验证两处；禁止主动改写。\n'
             '- 引入：两段已确认，见 story/INTRO.md。\n'
             '- 来源：用户粘贴的网络故事，作者与链接未提供；授权由用户接管，登记为 authorization-pending，不宣称真实案件已核实。\n'
             f'- 正文字数：{count}；按3.6字/秒约{count/216:.2f}分钟。\n'
             '- 时长：等待用户决定是否按约44分钟完整制作；确认前只推进独立引入与人物准备，不删正文、不批量生成正文。\n'
             '- 视觉：本线赛璐璐调查漫画；侵害与杀人不直接展示，以场地、证据和人物反应承载，不改变旁白。\n'
             '- 当前阶段：引入底图与调查者身份参考试生；尚未交付成片。\n'
             '- 交付范围：两张独立引入图＋无音轨、无文字正文MP4＋同基名SRT。\n')
    (EP / 'PROJECT_STATE.md').write_text(state)
    (EP / 'story/INTRO.md').write_text('''# 已确认引入

## 01
一个十三岁女孩死后，村里人都说，她早晚会有这一天。

画面：村巷里几位成年村民围拢议论，旁观者视角；不出现死亡现场，不虚构女孩遗照或葬礼。

## 02
可我们查得越深，越发现，所有人对她的偏见，竟成了凶手最好的掩护。

画面：年轻刑警独坐调查桌前重新检查材料，前景文件形成视觉遮挡；不出现已被识别的凶手、不新增指认照片或决定性证据。

两张1920×1080无字图片，独立交付，不制作引入字幕，不拼入正文。
''')
    (EP / 'story/OUTLINE.md').write_text('''# 原文主线映射

1. 女孩死亡，尸检发现侵害及旧伤；物证：检材。
2. 排查爷爷，访问好友与村民；偏见先于事实出现。
3. 从学校与社交关系寻找嫌疑人，比对未匹配。
4. 发现女孩与退休老师来往及二十万元赔偿；物证：转账流水。
5. 老师说明女孩拒绝诬陷他，重新解释此前的勒索事件。
6. 流水指向父亲赌债；出行记录提示父亲与女孩的异常往来。
7. C城调查未有突破；电话、二百元红包留下未解疑点。
8. 母亲杀夫自首，转述丈夫酒后交代的罪行。
9. 揭示父亲牟利、陈威宏施害；红包与口红购买记录重新解释女孩的高兴。
10. 新增DNA比对与宾馆记录印证供述，接原文判决与结尾。

本文件只映射已确认文本，不调整原文情节顺序，不补充其他剧情。
''')
    (EP / 'story/SUSPENSE_BUDGET.md').write_text('''# 悬念与来源

- 主悬念：谁导致林娜死亡？第15节揭示，第17节新增段落完成证据核实。
- 次悬念：父亲的二十万元与异常带女儿出行有什么关系？第15节回收。
- 认知反转：女孩拒绝诬陷老师；父亲的“保护”实际是牟利；红包背后的侵害。
- 物证：检材、转账流水、出行记录、通话与红包、口红支付记录、结尾新增宾馆记录。
- 文本边界：原文保留；仅两处补充属于已获用户确认的改编内容。
- 叙述：保留原作刑警第一人称，按网络故事改编处理，不声称旁白是实际办案人员。
- 来源：用户粘贴文本；未独立核实作者与真实案情，授权用户接管。
- 预算：原文约9408字，约44分钟；超25分钟是否放行待用户回答。
''')
    (EP / 'storyboard/CHARACTER_LOCK.md').write_text('''# 人物准备

- narrator：A档，新建28岁男性刑警，短黑发、浅蓝短袖警衬衫、深灰裤；仅供本集。参考 image/anchors/narrator-sheet.png；尚未生成验收，未锁定。
- intro-villagers：C档，只在引入议论场景出现的成年村民，无主线关键动作；不把她们画成已确认的嫌疑人。
- 正文其他角色：时长确认后按分镜统计确定档位；当前不批量。
- 池内角色均为儿童，不符合成年刑警身份；新建，不更改年龄套用旧脸。
''')
    (EP / 'storyboard/INTRO_PLAN.json').write_text(json.dumps({'shots': [
        {'id': 'I01', 'line': '悬疑', 'step': 'composite', 'character_ids': ['intro-villagers'],
         'character_closeup': False, 'hands_visible': True, 'evidence_id': '',
         'subject_class': 'character', 'push_ratio': 0, 'needs_2048': False,
         'fact': '村民在女孩死后围拢议论', 'cast': 'intro-villagers', 'shot_type': 'M'},
        {'id': 'I02', 'line': '悬疑', 'step': 'composite', 'character_ids': ['narrator'],
         'character_closeup': False, 'hands_visible': True, 'evidence_id': '',
         'subject_class': 'character', 'push_ratio': 0, 'needs_2048': False,
         'fact': '刑警重新检查调查材料，尚未锁定真凶', 'cast': 'narrator', 'shot_type': 'M'}
    ]}, ensure_ascii=False, indent=2))
    print(f'PREPARED {count} estimated {count / 216:.2f} minutes', flush=True)


def generate(tag, dest, description, assigned, reference=None):
    target = EP / dest
    log = EP / 'logs' / (tag + '.json')
    spec = importlib.util.spec_from_file_location('api_' + tag.replace('-', '_'), ROOT / 'projects/悬疑/visual-tests/20261114-pilot-8shots/gen_pilot.py')
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    api.TIMEOUT_S = 150
    prompt = '\n'.join([api.read_block('STYLE_POS'), api.read_block('CEL_BOOST'),
                        description, 'Clean flat fills describe rendering, not pristine physical condition. '
                        'One full-frame illustration, no words, no watermark, no logo. ',
                        'Avoid: ' + api.read_block('STYLE_NEG')])
    if target.exists() and log.exists():
        prior = json.loads(log.read_text())
        if prior.get('ok') and prior.get('prompt') == prompt:
            return True
    attempts = []
    for name in [assigned, *(n for n in ACTIVE['parallel_channels'] if n != assigned)]:
        if name in os.environ.get('LINNA_UNAVAILABLE_ROUTES', '').split(','):
            attempts.append({'channel': name, 'error': 'route_unavailable_tls_eof'})
            continue
        channel = dict(POLICY['channels'][name], name=name)
        for attempt in range(1, 3):
            with tempfile.TemporaryDirectory(prefix='linna-image-') as folder:
                api.HERE = api.RAW = api.CROPS = Path(folder)
                with ROUTE_LOCKS[name]:
                    result = curl_call(api,channel,prompt,tag,reference,attempt,folder)
                if result.get('ok'):
                    image_path = Path(folder) / result['file']
                    result['metrics'] = api.measure(image_path)
                    findings = api.gate(result, channel)
                    if findings and tag.startswith('char-') and 'sheet' not in str(dest):
                        native_metrics=result['metrics']
                        with Image.open(image_path) as original:
                            original=original.convert('RGB')
                            for ratio in [.75,.60]:
                                w,h=original.size
                                crop=original.crop((int(w*(1-ratio)/2),0,
                                    int(w*(1+ratio)/2),int(h*ratio)))
                                crop.resize((w,h),Image.Resampling.LANCZOS).save(image_path)
                                result['metrics']=api.measure(image_path)
                                findings=api.gate(result,channel)
                                if not findings:
                                    result['reference_crop']={'ratio':ratio,'native_metrics':native_metrics,
                                        'purpose':'remove neutral margins; preserve face and clothing without another generation'}
                                    break
                    if not findings:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(image_path.read_bytes())
                        result.update(file=dest, fallback_from=assigned if name != assigned else None,
                                      policy=POLICY['active'], attempts=attempts)
                        log.write_text(json.dumps(result, ensure_ascii=False, indent=2))
                        print(tag, name, 'READY', result['dims'], flush=True)
                        return True
                    result['error'] = 'quality_gate'
                    review=EP/f'image/review/{tag}-{name}-a{attempt}.png'
                    review.parent.mkdir(parents=True,exist_ok=True)
                    review.write_bytes(image_path.read_bytes())
                    result['gate_findings']=findings
                safe = {k: result.get(k) for k in ['channel', 'http_status', 'elapsed_s', 'dims']}
                safe['error'] = 'quality_gate' if result.get('error') == 'quality_gate' else 'request_failed'
                if result.get('error') in ['upstream_no_available_channel','size_rejected','quota_unavailable','model_route_error']:
                    safe['error']=result['error']
                if result.get('curl_exit'):
                    safe.update(error=result['error'],curl_exit=result['curl_exit'])
                if result.get('gate_findings'):
                    safe.update(metrics=result['metrics'],gate_findings=result['gate_findings'])
                attempts.append(safe)
                print(tag, name, attempt, safe['http_status'], safe['error'], flush=True)
                if result.get('http_status') in (401, 403):
                    break
    log.write_text(json.dumps({'ok': False, 'attempts': attempts, 'prompt': prompt}, ensure_ascii=False, indent=2))
    return False


VILLAGE = ('A present-day Chinese mountain village lane in summer, seen from beside a chipped '
           'grey courtyard doorway in left foreground. Right side a faded green metal door, '
           'a scuffed low concrete wall, hanging cotton laundry and a yellow plastic stool. '
           'Two enamel basins beside a doorstep; damp stain beneath a window. '
           'Deep focus, cool daylight, restrained small warm light inside doorway. '
           'ZERO people, no body, no memorial portrait, no coffin, no crime-scene tape. '
           'Leave usable foreground space along the wall for a later small group. No text.')
OFFICE = ('A modest Chinese county police investigation office in summer, view over the '
          'near corner of a scratched wood desk, slightly elevated eye-level 28mm deep focus. '
          'Desk sits right of center under one warm desk lamp: several open plain paper folders, '
          'loose blank sheets, dark unlit phone, enamel mug. A pushed-in dark chair; '
          'background steel cabinet, peeling wall paint and scuffed skirting, cool daylight '
          'from a barred side window. ZERO people. No writing, portraits, diagrams or screens. '
          'Keep the chair and working desk available for a seated investigator.')


def assets():
    # First call is also the required live preflight. No bulk calls if both routes fail.
    if not generate('preflight-village', 'image/plates/village.png', VILLAGE, 'new2'):
        raise SystemExit('IMAGE_PREFLIGHT_FAILED')
    rows = [
        ('office-plate', 'image/plates/office.png', OFFICE, 'new2'),
        ('narrator-sheet', 'image/anchors/narrator-sheet.png',
         'Character design reference on neutral grey background. One same adult character '
         'in FOUR equal quadrants: top-left front full body; top-right strict side full body; '
         'bottom-left back full body; bottom-right front face close view. Same face, '
         'same hairstyle and outfit in all views. No border or labels. ' + DETECTIVE, 'dkl-b')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda row: generate(*row), rows))
    if not all(results):
        raise SystemExit('ASSET_GENERATION_INCOMPLETE')
    with Image.open(EP / 'image/anchors/narrator-sheet.png') as image:
        w, h = image.size
        for name, box in {'front': (4, 4, w//2-4, h//2-4),
                          'side': (w//2+4, 4, w-4, h//2-4),
                          'back': (4, h//2+4, w//2-4, h-4),
                          'face': (w//2+4, h//2+4, w-4, h-4)}.items():
            image.crop(box).save(EP / 'image/anchors' / ('narrator-' + name + '.png'))


def introduction():
    # Inspect the source assets and identity first, then run this stage explicitly.
    plate = Image.open(EP / 'image/plates/office.png').convert('RGB')
    face = Image.open(EP / 'image/anchors/narrator-face.png').convert('RGB')
    front = Image.open(EP / 'image/anchors/narrator-front.png').convert('RGB')
    canvas = Image.new('RGB', (1800, 650), (80, 80, 85))
    canvas.paste(ImageOps.contain(plate, (1050, 650)), (0, 0))
    canvas.paste(ImageOps.contain(front, (360, 650)), (1070, 0))
    canvas.paste(ImageOps.contain(face, (350, 650)), (1440, 0))
    ref = EP / 'image/anchors/intro-reference.png'
    canvas.save(ref)
    rows = [
        ('intro-01', 'image/intro/source-01.png',
         'Use attached village ONLY as architecture reference. Make a SINGLE new illustration, '
         'not a montage. ' + VILLAGE.replace('ZERO people', 'Add exactly five ADULT villagers') +
         ' Five Chinese adult villagers aged 40 to 65, two men and three women in different '
         'faded grey, brown and muted plum cotton summer clothing, uneven clustered spacing '
         'near the wall, facing inward and talking to each other. Three-quarter close medium '
         'view from outside their circle. Nearest cropped shoulder presses left edge, one '
         'woman on right speaking with dismissive pursed lips and a small lowered hand gesture, '
         'others listen with indifferent or judging expressions, no smiles. Natural asymmetric '
         'group, no lineup, no accusing finger pointed at camera. The group visually blocks '
         'the narrow lane. Their conversation carries social pressure, not supernatural horror. '
         'No girl, no police, no known perpetrator, no body or violence.',
         'new2', EP / 'image/plates/village.png'),
        ('intro-02', 'image/intro/source-02.png',
         'Attached strip: LEFT is office architecture, CENTER and RIGHT are the SAME detective '
         'body and face references. Render one new full-frame scene, no panels. ' + DETECTIVE +
         ' He sits alone at the right side of the worn investigation desk, three-quarter face '
         'visible, concentrating with narrowed eyes and tired brows on loose case sheets; '
         'one hand holds a paper edge, the other rests near an open folder. Medium-close '
         'view from the opposite desk corner, near folder edge occludes the lower left. '
         'Preserve the room and furniture, cool grey-blue office light, small amber lamp '
         'illuminates his face and papers, hard cel shadow makes his concern readable. '
         'Papers are blank or turned away, no suspect portrait, no readable writing, no '
         'diagrams or invented decisive clues. A single investigation moment of reconsidering '
         'the available material; no split screen, no extra people, no weapons.',
         'dkl-b', ref)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda row: generate(*row), rows))
    if not all(results):
        raise SystemExit('INTRO_INCOMPLETE')
    for n in [1, 2]:
        with Image.open(EP / f'image/intro/source-{n:02}.png') as image:
            ImageOps.fit(image.convert('RGB'), (1920, 1080), method=Image.Resampling.LANCZOS).save(
                EP / f'image/intro/v1/悬疑_林娜案_引入_{n:02}_v1.png')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['prepare', 'assets', 'intro'])
    args = parser.parse_args()
    {'prepare': prepare, 'assets': assets, 'intro': introduction}[args.stage]()
