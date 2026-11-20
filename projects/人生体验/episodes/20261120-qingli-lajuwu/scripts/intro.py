from pathlib import Path
import json,hashlib
from concurrent.futures import ThreadPoolExecutor
from PIL import Image,ImageOps
from produce import EP,STYLE,CHARS,request,composite_reference,save
OUT=EP/'image/intro/v1';OUT.mkdir(parents=True,exist_ok=True)
ROWS=[dict(id='INTRO01',cue='纸箱刚挪开，一群蟑螂就沿着墙脚散了。搭档猛地松手，箱子又砸回了垃圾堆。',scene_id='kitchen-full',cast='partner',fact='橙衣搭档松手后仰，纸箱一角已落回垃圾，露出的墙脚有多只蟑螂散开。',shot_type='M',visual='Low oblique medium view, camera near kitchen floor looking diagonally along the cabinet plinth. Foreground left a single collapsed wet cardboard box has just landed tilted against garbage, revealing a dark filthy gap behind it. A conspicuous cluster of realistically SMALL cockroaches, about 2-4 cm long, fans out along the newly exposed floor-wall seam, sharp readable silhouettes, not giant insects, no swarm in the air. Midground right ONE orange-shirt partner has recoiled backwards with both small pale-blue mitten hands RELEASED and held away from box, body leaning back, startled short open mouth and dot eyes. Capture ONE frozen moment after release, not a sequence. Cockroaches and exposed seam in central lower-middle above bottom fifth. Keep cupboard, dirty sea-green wall tiles, crowded stove and sink consistent; room still full of waste. No surprise symbols or motion marks.'),dict(id='INTRO02',cue='你们才刚清到厨房。外面那张被垃圾埋住的沙发，还等着你们往外挪。',scene_id='living-full',cast='none',fact='同一客厅蓝灰沙发被垃圾埋住，仅露出半截靠背，铁床和窗户作为场地锚点；无人。',shot_type='M',visual='A compelling tight medium environmental shot of the SAME blue-grey sofa almost buried in takeaway waste, camera just above rubbish height in living room, angled diagonally toward sofa back. The partially exposed stained blue-grey backrest dominates center, the whole seat and base remain buried beneath mounds of leaking takeaway bags, greasy white food containers, damp collapsed cardboard and tangled cat hair, litter and small dried feces among local floor debris. Framing feels blocked and suffocating by layered close foreground rubbish; sofa back recognizable ABOVE bottom fifth. Preserve peeling wall, same iron bed and rear-right window partly visible behind sofa as continuity anchors. This is BEFORE sofa moved: no cleared floor, no revealed sofa underside, no clean corridor. NO people, heads, hands or body parts, no cats. Daylight makes dirt readable, no global brown filter.')]
def generate(pair):
 index,row=pair;bg=EP/'image/backgrounds'/f"{row['scene_id']}.png";ref=composite_reference(bg,row['cast'],row['id'])
 if row['cast']=='none':
  style='Detailed hand-painted 2D environment, same materials, contours, depth, ambient occlusion and natural daylight as attached scene. Full frame 16:9, no text, panels, UI, logos or watermarks. NO people or body parts.'
  roles={str(bg):'exact room geometry, sofa design, pre-cleaning waste state and light'}
 else:
  style=STYLE+' Reference LEFT is exact kitchen environment, RIGHT is partner identity and thin-limb proportions only. Output one full-frame scene without reference strip. Exactly one person: '+CHARS['partner']+'. White head must be flat and unshaded, black rod limbs, small round gloves with no individual fingers.'
  roles={str(bg):'exact kitchen layout, clutter, materials and light',str(EP/'image/anchors/partner.png'):'partner identity and proportions only'}
 prompt=style+' Required scene: '+row['visual']+' Do not add letters, comic symbols, duplicate body parts, dramatic colored filters or unrelated props.'
 src=request('intro-01' if index==0 else 'intro-02',prompt,index,ref,dict(**row,stage='intro-character-composite' if index==0 else 'intro-environment-single',environment_master=str(bg),reference_roles=roles,approved_option=1))
 out=OUT/f'人生体验_清理垃圾屋_引入_{index+1:02}_v1.png'
 with Image.open(src) as im:ImageOps.fit(im.convert('RGB'),(1920,1080),method=Image.Resampling.LANCZOS).save(out)
 return dict(**row,file=str(out.relative_to(EP)),sha256=hashlib.sha256(out.read_bytes()).hexdigest(),request_log=f'logs/requests/intro-{index+1:02}.json')
if __name__=='__main__':
 with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(generate,enumerate(ROWS)))
 save(EP/'storyboard/INTRO_PLAN.json',dict(approved_option=1,delivery='两张独立引入图，无文字，未剪入正文成片',shots=rows))
 print('INTRO_IMAGES_READY',flush=True)
