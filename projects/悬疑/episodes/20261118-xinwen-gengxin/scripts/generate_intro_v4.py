"""死亡预告单张引入：使用现有图片 API 与角色参考，不改正文。"""
from pathlib import Path
import importlib.util, json, hashlib
from PIL import Image, ImageOps
EP=Path(__file__).resolve().parents[1]
ROOT=EP.parents[3]
OUT=EP/'image/intro/v4'
OUT.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('intro_api',ROOT/'projects/悬疑/visual-tests/20261114-pilot-8shots/gen_pilot.py')
api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
api.HERE=OUT;api.RAW=OUT;api.TIMEOUT_S=180
policy=json.loads((ROOT/'shared/image-api/channel-policy.json').read_text())
channel=dict(policy['channels']['dkl-b'],name='dkl-b',policy=policy['active'])
refs=[EP/'image/anchors/zhouning-face.png',EP/'image/anchors/zhouning-front.png',EP/'image/raw/evidence-parkedcar.png']
tiles=[]
for p in refs:
 im=Image.open(p).convert('RGB');im.thumbnail((1100,700));tiles.append(im)
strip=Image.new('RGB',(sum(i.width for i in tiles),700),(60,65,72));x=0
for im in tiles:strip.paste(im,(x,0));x+=im.width
ref=OUT/'reference.png';strip.save(ref)
content='''ONE continuous full-frame illustration, not a collage or split screen. Adult Chinese woman Zhouning with the EXACT face, shoulder-length center-parted black hair, dark red cardigan and charcoal shirt in references 1 and 2. Reference 3 specifies her dark navy compact SUV only. A disturbing illustration for the idea: seeing your own death in the news before it happens.
Tight over-the-shoulder view beside an apartment window at night. Living woman's partial face in left foreground, her eye, nose and cheek distinctly visible in three-quarter profile, frozen in recognition, mouth closed, staring DOWN RIGHT into her phone. She holds ONE smartphone horizontally with anatomically correct hands. The phone is physically close to the viewer, filling approximately HALF THE WHOLE IMAGE, with visible dark bezel and all four corners, its screen facing the viewer enough to see its contents clearly.
INSIDE THE PHONE DISPLAY ONLY: a stark accident-scene image, the referenced dark navy SUV with crushed front against a roadside tree. View into shattered driver-side window: the SAME adult woman, unmistakably identical facial identity and red cardigan, motionless in the driver seat with seat belt tight across her chest. Her head hangs sharply sideways against her shoulder at an unsettling angle, pale ash-grey skin, lips slightly parted, BOTH EYES OPEN and staring straight out of the screen at the living woman/viewer. The dead woman's face is LARGE and sharply readable, occupying at least a third of the phone display. Non-graphic death, no exposed wounds or excessive blood. Angular shattered glass and folded metal surround her. Cold white emergency illumination, a small amber roadside lamp behind.
OUTSIDE THE PHONE: through the real window in upper-right background, the same navy SUV is entirely intact, parked below at the curb. Supporting background detail, keep phone face the main focal point. Real room has chipped window paint, water-stained sill, worn curtain and one pair of slippers. Cold grey-blue room, phone light illuminating living face and stiff fingers; retain enough midtone to read both faces. Dark ominous atmosphere, clean ink linework and hard cel shadows. One living woman in room, her dead double ONLY in phone image. No ghost standing in room, no extra face outside phone, no smiling, no screaming, no supernatural glowing eyes, no white pupil-less eyes. NO written text, no headlines, no interface, no letters or symbols. Phone contains accident image edge to edge. Do not copy reference layout.'''
prompt='\n'.join([api.read_block('STYLE_POS'),api.read_block('CEL_BOOST'),content,'Avoid: '+api.read_block('STYLE_NEG')])
(OUT/'prompt.txt').write_text(prompt)
info=api.call(channel,prompt,{'tag':'intro-death'},ref,1)
(OUT/'generation.json').write_text(json.dumps(info,ensure_ascii=False,indent=2))
print(json.dumps({k:info.get(k) for k in ['ok','http_status','dims','elapsed_s','file']},ensure_ascii=False),flush=True)
if not info.get('ok'):raise SystemExit('Image generation failed; see generation.json')
source=OUT/info['file']
final=OUT/'悬疑_新闻更新前_引入_01_v4.png'
ImageOps.fit(Image.open(source).convert('RGB'),(1920,1080),method=Image.Resampling.LANCZOS).save(final)
(OUT/'manifest.json').write_text(json.dumps([{'number':'01','cue':'你有没有想过，自己会先在新闻里，看见自己的死讯？','file':str(final.relative_to(EP)),'sha256':hashlib.sha256(final.read_bytes()).hexdigest(),'standalone':True,'included_in_body_video':False,'visual_exaggeration':'用户批准：手机事故画面里死去的自己睁眼与现实中的自己对视；正文未展示死者面容。','channel':'dkl-b','native_size':info['dims'],'qa':'pending visual review'}],ensure_ascii=False,indent=2))
print(str(final),flush=True)
