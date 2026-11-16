from pathlib import Path
import importlib.util
import json
import hashlib
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
spec = importlib.util.spec_from_file_location('cover_api', REPO / 'projects/悬疑/visual-tests/20261114-pilot-8shots/gen_pilot.py')
gp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gp)
gp.HERE = HERE
gp.RAW = HERE / 'shadow-v1-raw'
gp.RAW.mkdir(exist_ok=True)
policy = json.loads((REPO / 'shared/image-api/channel-policy.json').read_text(encoding='utf-8'))
channel = dict(policy['channels']['dkl-b'], name='dkl-b')
pos, neg, cel = [gp.read_block(k) for k in ['STYLE_POS', 'STYLE_NEG', 'CEL_BOOST']]
scene = '''Horror cover artwork communicating: a navigation app brought something home.
An ordinary Chinese apartment entrance late at night, viewed from inside the home toward the open door.
Exactly ONE real adult Chinese man, 30, short black hair, charcoal commuter jacket, light grey shirt,
black trousers, worn black shoes. He stands frozen just inside the threshold in three-quarter back view,
holding a luminous blue smartphone low in his right hand. His face is mostly unseen.
The main unmistakable abnormal evidence: TWO enormous human silhouettes cast onto the pale grey interior wall,
although there is only ONE physical man. One normal shadow corresponds to him. The OTHER is a much taller,
pitch-black human shadow with a tilted head, hunched shoulders and a long arm already reaching into the home,
its fingers hooked around the inside edge of the doorway, independent of the man's relaxed arm.
The second silhouette is only a flat cast shadow on the wall, NOT a physical second person, no eyes or face.
The disconnected shadow dominates the image and extends above the man's head like a silent intruder.
Old water-stained wall, peeling paint on doorframe, scuffed tiles, slippers at threshold, ordinary inhabited home.
Very oppressive narrow doorway, heavy dark foreground frame, cold grey-blue ambient tones,
one small weak warm corridor bulb behind the man. Keep the wall bright enough that both shadow outlines
read immediately even at thumbnail size. Large stark graphic shadow shapes, restrained red accent on door latch.
No gore, no ghost woman, no glowing eyes, no additional physical humans, no floating objects,
no text anywhere, no typography, no logos, no watermark, no collage, no panels.
The phone screen is blank dark blue; navigation graphics will be added deterministically later.'''

def generate(kind):
    portrait = kind == 'portrait'
    ch = dict(channel, size='1152x2048' if portrait else '2048x1152')
    composition = ('VERTICAL 9:16 final canvas overrides the generic aspect-ratio style token. '
                   'Man in lower-middle, giant shadow visible on wall above and right. Reserve top 24 percent '
                   'as dark uncluttered wall for title, all key shadow evidence between 28 and 83 percent height.'
                   if portrait else
                   'WIDE 16:9 poster. Man on right third, giant abnormal shadow on right half. '
                   'Reserve left 40 percent as dark empty wall for title; preserve complete head, hand and shadow on right.')
    prompt = '\n'.join([pos, cel, scene, composition, 'Avoid: ' + neg])
    (HERE / f'shadow-{kind}-v1.prompt.txt').write_text(prompt, encoding='utf-8')
    info = gp.call(ch, prompt, {'tag': f'shadow-{kind}-v1'}, None, 1)
    (HERE / f'shadow-{kind}-v1.generation.json').write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
    if not info.get('ok'):
        raise RuntimeError(f'{kind} generation failed, see local generation record')
    print(f'GENERATED {kind} {info["dims"]}', flush=True)
    return kind, info

def compose(kind, info):
    portrait = kind == 'portrait'
    size = (1080,1920) if portrait else (1920,1080)
    im = ImageOps.fit(Image.open(HERE / info['file']).convert('RGB'),size,method=Image.Resampling.LANCZOS)
    overlay = Image.new('RGBA',size)
    d = ImageDraw.Draw(overlay)
    if portrait:
        for y in range(600):
            d.line([(0,y),(size[0],y)],fill=(5,9,16,int(190*max(0,1-y/600))))
        x,y,fs = 65,95,114
    else:
        for x0 in range(1000):
            d.line([(x0,0),(x0,size[1])],fill=(5,9,16,int(190*max(0,1-x0/1000))))
        x,y,fs=115,320,128
    im=Image.alpha_composite(im.convert('RGBA'),overlay)
    d=ImageDraw.Draw(im)
    font=ImageFont.truetype('C:/Windows/Fonts/simhei.ttf',fs)
    d.text((x,y),'导航把谁',font=font,fill=(231,233,230),stroke_width=2,stroke_fill=(9,14,21))
    d.text((x,y+int(fs*1.22)),'带回了家',font=font,fill=(187,42,37),stroke_width=2,stroke_fill=(18,10,14))
    out=HERE / f'导航把谁带回了家-shadow-v1-{kind}-{size[0]}x{size[1]}.png'
    im.convert('RGB').save(out)
    return {'file':str(out),'dimensions':list(size),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),
            'source':info['file'],'text_layers':['导航把谁','带回了家'],'font':'simhei.ttf',
            'generation':{'channel':channel['name'],'model':channel['model'],'policy':policy['active']},
            'qa':'pending visual inspection','next_step':'preview and inspect shadow relation and text safety'}

if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(generate,['landscape','portrait']))
    records=[compose(*r) for r in results]
    (HERE/'shadow-v1-manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    sheet=Image.new('RGB',(1100,720),(17,21,28))
    for rec,box in zip(records,[(0,95,740,512),(755,0,1100,615)]):
        img=Image.open(rec['file']); img.thumbnail((box[2]-box[0],box[3]-box[1]))
        sheet.paste(img,(box[0],box[1]))
    sheet.save(HERE/'shadow-v1-preview.jpg',quality=88)
    print('DONE',flush=True)
