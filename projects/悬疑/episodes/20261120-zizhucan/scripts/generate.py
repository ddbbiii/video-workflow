from pathlib import Path
import sys,json,re,threading,shutil,hashlib,concurrent.futures,importlib.util,time,math,os
from PIL import Image,ImageOps,ImageDraw
EP=Path(__file__).resolve().parents[1];ROOT=EP.parents[3]
spec=importlib.util.spec_from_file_location('zizhu_api',ROOT/'projects/悬疑/visual-tests/20261114-pilot-8shots/gen_pilot.py')
api=importlib.util.module_from_spec(spec);sys.modules[spec.name]=api;spec.loader.exec_module(api)
api.HERE=EP;api.RAW=EP/'image/raw';api.CROPS=EP/'qa/crops';api.CROPS.mkdir(exist_ok=True);api.TIMEOUT_S=140
POL=json.loads((ROOT/'shared/image-api/channel-policy.json').read_text())
CHANNELS=POL['policies'][POL['active']]['parallel_channels']
POS,NEG,CEL=[api.read_block(n) for n in ['STYLE_POS','STYLE_NEG','CEL_BOOST']]
PLAN=json.loads((EP/'storyboard/SHOT_PLAN.json').read_text())
LOCKS={c:threading.Lock() for c in CHANNELS};DISABLED=set();STATE=threading.Lock()
SCENES={
'mall':'Ordinary older Chinese shopping mall basement concourse: wide escalator at left, dark stone plinth with one chipped corner, steel railing at right, shopfront at back. Not a ruin. Worn tile grout, scratched railing and stacked shopping baskets. Only one small warm light at shop entrance, grey-blue ambient. No people, text, logos or readable signs.',
'entrance':'Older Chinese self-service personal hotpot entrance, compact cashier counter at left with group-buy scanner, stacked plain trays, freezer row visible beyond right, a faded yellow square pillar with rectangular peeled tape scar. Scratched counter, yellowed plastic and stacked bowls. No people, text or labels.',
'table':'The SAME two-seat booth in a small Chinese self-service hotpot restaurant. Teal vinyl seats facing each other across scratched brown laminate square table; exactly two small round steel hotpots recessed in black induction plates, TWO small white dipping bowls, one white oval meat plate. Yellow square support pillar with a rectangular pale tape scar LEFT of booth; frosted glass partition at RIGHT. Through a gap in distant freezer row see red handles of juice dispenser. Two real adult scale seats. Scuffed floor tiles, chipped table edge and water rings, stacked bowls in background. Grey-blue ambient with one warm overhead lamp. No people or words.',
'counter':'Chinese self-service hotpot buffet aisle, brushed steel chest freezers filled with plain small trays of curled frozen beef and white fish balls, red-handled translucent plum juice dispenser farther left, yellow square pillar with pale rectangular tape scar at right bend. Foreground scratched steel freezer rim, chipped grey floor tile, wet mop bucket and stacked white bowls. Grey-blue deep focus, one warm ceiling lamp. No people, lettering or labels.',
'drinks':'Chinese buffet self-service plum-juice station: TWO red pull handles on transparent rectangular drink reservoirs containing dark red-brown juice, grey plastic stirring paddle inside, steel drip tray below. Foreground scratched steel edge, yellowed plastic, stacked translucent tumblers, pale tape scar on yellow pillar behind. No people or any writing.',
'threshold':'Unusual but mundane-looking glass doorway from older Chinese buffet aisle into shopping mall. Foreground chipped grey jamb and scratched freezer rim, middle glass doorway, beyond escalator and worn shopping baskets, grey-blue interior with one warm practical light. No people, time portal effects, text, ruins or monster.',
'service':'Chinese shopping mall service desk, worn pale wood counter with chipped corner and scratched surface, grey metal landline handset and plain thick folder, dark stone plinth with chipped corner behind, modern pharmacy shelves far right with plain packages without writing. Two chairs front of desk, shopping baskets underneath, grey-blue ambient with one warm desk lamp. No people, uniforms, logos, banners or words.',
'noodle':'Modest Chinese street noodle shop at night, small scratched pale laminate table with TWO ceramic bowls of noodle soup, two wooden stools, black vinegar bottle on distant counter, chipped floor tile, taped fan cable, basket of plain chopstick sleeves. Grey-blue ambient and one warm overhead light. No people, text, lettering or food posters.'}
CHAR={
'chen':'Chen Mo: exactly one 32-year-old Chinese man, slim average build, angular oval face, straight eyebrows, narrow dark eyes, short slightly tousled black hair with a shallow left side part, no glasses, no facial hair. Wears plain NAVY zip-front casual jacket, off-white crewneck T-shirt, charcoal straight trousers, pale grey sneakers. Never age him, never add grey hair. Tiny beige sesame-sauce stain on RIGHT navy cuff after S04.',
'zhou':'Zhou: exactly one 32-year-old Chinese man, slightly stockier than Chen, broad oval face, straight flat eyebrows, short close-cropped black hair, small mole beside LEFT eyebrow, no glasses or beard. Wears plain OLIVE overshirt over grey T-shirt, dark trousers, black shoes. Young, no grey hair. From S13 red-rimmed eyes and fatigue; from S16 LEFT ankle swollen, loosened left shoe, slight limp. No blood.',
'zhou_old':'The SAME Zhou eleven years later, now exactly 43 years old (middle-aged, NOT elderly): recognizable broad oval face, same small mole beside LEFT eyebrow, restrained crow feet, a few grey strands at both temples, thinner cheeks. CHARCOAL casual jacket over the same style OLIVE shirt, dark trousers, black shoes. Slight LEFT leg limp. No beard, no extreme wrinkles, no full white hair.'}
QUALITY='One complete full-frame image; never reproduce reference-strip layout. Sharp ink contours and controlled hard-edged cel shadows, flat areas, no soft gradients or texture veil. Readable midtones. No text, letters, digits, logos, UI, charts, watermarks, borders, montage, ghost, blood or extra person. Clean flat fills describe rendering technique, not pristine physical condition. Maintain specified wear as restrained shapes.'

def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2))
def refstrip(tag,paths):
 ims=[]
 for p in paths:
  im=Image.open(p).convert('RGB');im.thumbnail((1280,800),Image.Resampling.LANCZOS);ims.append(im)
 out=Image.new('RGB',(sum(im.width for im in ims),800),(70,76,84));x=0
 for im in ims:out.paste(im,(x,(800-im.height)//2));x+=im.width
 p=EP/'image/references'/f'{tag}.png';out.save(p);return p

def generate(tag,content,refs=None,cel=True,assigned='new2'):
 target=EP/'image/raw'/f'{tag}.png';side=EP/'logs'/f'{tag}.json'
 if target.exists() and side.exists() and json.loads(side.read_text()).get('ok'):return target
 prompt='\n'.join([POS,CEL if cel else '',QUALITY,content,'Avoid: '+NEG])
 failure=None
 for name in [assigned]+[n for n in CHANNELS if n!=assigned]:
  if name in DISABLED:continue
  c=dict(POL['channels'][name],name=name,policy=POL['active'])
  for attempt in range(1,3):
   with LOCKS[name]:
    if name in DISABLED:break
    print('REQUEST',tag,name,attempt,flush=True)
    info=api.call(c,prompt,{'tag':tag+'-'+name},refs,attempt)
   info.update(assigned_channel=assigned,model=c['model'],policy=POL['active'],fallback_from=failure,
     endpoint_url=c['base_url']+'/images/'+('edits' if refs else 'generations'),
     references=[str(refs.relative_to(EP))] if refs else [],reference_roles='empty scene architecture first; locked character identity next; action overrides reference pose',
     request_id=None,scene_state_in_prompt=True)
   if info.get('ok'):
    src=EP/info['file'];im=Image.open(src)
    if im.size!=tuple(map(int,c['size'].split('x'))):info.update(ok=False,error='native-size mismatch')
    else:
     if src!=target:shutil.copyfile(src,target)
     info['file']=str(target.relative_to(EP));info['metrics']=api.measure(target);info['sha256']=hashlib.sha256(target.read_bytes()).hexdigest();save(side,info)
     print('READY',tag,name,im.size,info.get('elapsed_s'),flush=True);return target
   save(EP/'logs'/f'{tag}-{name}-failed-{attempt}.json',info)
   err=info.get('error');code=err.get('error',{}).get('code') if isinstance(err,dict) and isinstance(err.get('error'),dict) else ''
   print('FAILED',tag,name,info.get('http_status'),str(code or err)[:160],flush=True)
   if info.get('http_status') in [401,403]:break
  with STATE:DISABLED.add(name)
  failure=name
  print('CHANNEL_UNAVAILABLE',name,'remaining work assigned other active channel',flush=True)
 raise RuntimeError('Both configured image channels failed: '+tag)

def anchors():
 # Existing reuse pool contains only children: adult role cannot reuse either face.
 text=('Character model sheet only. 2x2 layout with four equally sized panels and no visible borders, plain grey ground. '
  'Top left: FRONT full body, arms relaxed, entire shoes visible. Top right: exact 90-degree SIDE full body. '
  'Bottom left: BACK full body. Bottom right: FRONT face close-up with exact same eyes and hair. '
  'Every panel depicts the SAME one adult, same clothes, scale consistent, no chair, food or scene. '+CHAR['chen'])
 p=generate('anchor-chen-sheet',text,None,True,'new2');shutil.copyfile(p,EP/'image/anchors/chen-sheet.png')
 im=Image.open(p);w,h=im.size
 for view,(x0,y0,x1,y1) in dict(front=(4,4,w//2-4,h//2-4),side=(w//2+4,4,w-4,h//2-4),back=(4,h//2+4,w//2-4,h-4),face=(w//2+4,h//2+4,w-4,h-4)).items():im.crop((x0,y0,x1,y1)).save(EP/'image/anchors'/f'chen-{view}.png')
 p=generate('anchor-zhou','ONE single adult character three-quarter full body, grey ground, arms relaxed, whole shoes visible. No furniture, props, other person, split panels or writing. '+CHAR['zhou'],None,True,'dkl-b');shutil.copyfile(p,EP/'image/anchors/zhou.png')
 p=generate('anchor-zhou-old','Age attached man by ELEVEN YEARS ONLY. ONE single 43-year-old man three-quarter full body, plain grey ground. Keep mole, skull and eye geometry. Change clothes to CHARCOAL jacket over OLIVE shirt. Grey strands only at temples, crow feet and leaner cheeks. Not elderly. '+CHAR['zhou_old'],EP/'image/anchors/zhou.png',True,'new2');shutil.copyfile(p,EP/'image/anchors/zhou_old.png')
 asset=ROOT/'assets/悬疑/characters/chenmo-20261120-zizhucan';asset.mkdir(parents=True,exist_ok=True)
 for v in ['front','side','back','face','sheet']:shutil.copyfile(EP/'image/anchors'/f'chen-{v}.png',asset/('three-view.png' if v=='sheet' else v+'.png'))
 (asset/'CHARACTER_SPEC.md').write_text('# 陈默角色锚点\n\ncharacter_id: chenmo-20261120-zizhucan\n档位: A\n身份: 当代中国城市32岁男性，普通上班族。\n固定形象: '+CHAR['chen']+'\nreuse-policy: soft\nreuse-mode: face-only\n批准范围: episode-only；用户授权自主制作，2026-11-20由本轮目检锁定。\n系列复用候选: series-reusable（未来仍须契合度检查）。\n模型、通道与实际参考见本集logs/anchor-chen-sheet.json。禁止漂移发型、脸型、年龄、海军蓝外套、灰裤与鞋。\n')
 (EP/'storyboard/CHARACTER_LOCK.md').write_text('# 人物锁定\n\n复用检查：现有REUSE_POOL两位主角为14岁男孩及8岁女孩，硬条件年龄不符；本集新建成人角色。\n\nA 陈默32岁：image/anchors/chen-front.png、side/back/face；整集不老化。\nB 老周32岁：image/anchors/zhou.png；S04起日常；S13起疲劳；S16起左脚踝伤。\nB 老周43岁状态：image/anchors/zhou_old.png；S34-S36、S39、S41、S43-S44及两张引入图；原脸保留，炭灰外套配橄榄内衬，少量鬓白、轻跛。\n逐镜具体出现列表以SHOT_PLAN.json character_ids为准。\n每次含角色生成均喂场景+相应人物锚点，不用文字替代参考；批量前检查首三个正式含主角镜。\n')
 sheet(['anchor-chen-sheet','anchor-zhou','anchor-zhou-old'],'anchors.jpg')

def lanes(items,fn):
 indexed=list(enumerate(items))
 def lane(n):
  for i,item in indexed[n::2]:fn(i,item)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
  futures=[ex.submit(lane,n) for n in range(2)]
  for f in futures:f.result()

def plates():
 def one(i,name):
  p=generate('plate-'+name,'EMPTY ENVIRONMENT ONLY. ZERO PEOPLE OR FIGURES. '+SCENES[name],None,False,CHANNELS[i%2]);shutil.copyfile(p,EP/'image/plates'/f'{name}.png')
 lanes(list(SCENES),one)
 sheet(['plate-'+n for n in SCENES],'plates.jpg')

def shot(i,s):
 target=EP/'image/final'/f"{s['id']}.png"
 if target.exists():return
 ids=s['character_ids'];scene=s['scene_id']
 paths=[EP/'image/plates'/f'{scene}.png']
 for cid in ids:
  paths+=[EP/'image/anchors/chen-front.png',EP/'image/anchors/chen-face.png'] if cid=='chen' else [EP/'image/anchors'/f'{cid}.png']
 ref=refstrip(s['id'],paths)
 kind={'E':'Wide establishing deep-focus view from doorway with foreground counter edge, natural adult proportions.', 'M':'Medium eye-level 28mm deep-focus view from 3m, persons on thirds, foreground table or freezer edge, architecture readable.', 'C':'Close three-quarter 28mm deep-focus evidence view, prop large and unobstructed, hands anatomically clear.'}[s['shot_type']]
 # Architecture context must not override the exact props or actor states of the shot.
 context=SCENES[scene].replace('No people','Scene reference is empty').replace('TWO small white dipping bowls, one white oval meat plate.','')
 cast=' EXACT CAST '+str(len(ids))+': '+'; '.join(CHAR[c].split('From S')[0] for c in ids) if ids else ' EXACTLY ZERO PEOPLE, no hands or human silhouettes anywhere.'
 if 'zhou' in ids:
  num=int(s['id'][1:]);cast+=' Zhou current state: '+('ordinary relaxed healthy complexion, eyes not red, both shoes fully on, no ankle injury.' if num<13 else 'tired red eyes; '+('left ankle injury, left shoelace loosened.' if num>=16 else 'no ankle injury yet.'))
 content=('First reference is EMPTY scene architecture, subsequent references are exact character designs. Draw ONE new full scene from requested viewpoint; do not draw reference strip, panels or sheet. '+kind+' '+context+' '+cast+
  ' ACTION AND PROP STATE OVERRIDE INITIAL PLATE: '+s['visual']+' Main fact to depict, NOT to write: '+s['fact']+'. '
  'Only draw people specified by exact cast. No generic staff or background customers. Keep table yellow pillar tape scar LEFT and frosted partition RIGHT when visible. '+
  'Phone and paper must have no characters, icons, lines of pseudo-text or numeric UI. Paper photos may be wordless portraits. No speech balloons.')
 p=generate(s['id'],content,ref,bool(ids) or s['shot_type']=='C',CHANNELS[i%2]);shutil.copyfile(p,target)

def shots(mode):
 rows=PLAN['shots']
 if mode=='pilot':rows=[s for s in rows if s['character_ids']][:6]
 elif len(sys.argv)>2:
  lo,hi=map(int,sys.argv[2:4]);rows=[s for s in rows if lo<=int(s['id'][1:])<=hi]
 lanes(rows,shot)
 sheet([s['id'] for s in rows],mode+'.jpg')

def intro():
 import runpy
 runpy.run_path(str(EP/'scripts/intro_horror.py'),run_name='__main__')

def sheet(tags,name):
 w=1440;cols=3;h=math.ceil(len(tags)/cols)*295
 out=Image.new('RGB',(w,h),(30,35,43));d=ImageDraw.Draw(out)
 for i,t in enumerate(tags):
  p=EP/'image/raw'/f'{t}.png'
  if not p.exists():continue
  im=ImageOps.fit(Image.open(p).convert('RGB'),(480,270),method=Image.Resampling.LANCZOS);x=i%3*480;y=i//3*295
  out.paste(im,(x,y+25));d.text((x+8,y+5),t,fill='white')
 out.save(EP/'qa'/name,quality=94)

if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='anchors':anchors()
 elif mode=='plates':plates()
 elif mode in ['pilot','shots']:shots(mode)
 elif mode=='intro':intro()
 elif mode=='sheet':sheet([s['id'] for s in PLAN['shots']],'all-shots.jpg')
