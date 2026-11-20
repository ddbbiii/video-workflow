"""本集图片生产：读取当前通道策略，分层参考，逐请求留存事实与提示词。"""
from pathlib import Path
import base64, hashlib, importlib.util, json, os, shutil, sys, threading, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageOps, ImageDraw

EP=Path(__file__).resolve().parents[1]
ROOT=EP.parents[3]
spec=importlib.util.spec_from_file_location('multipart_helper',ROOT/'projects/悬疑/visual-tests/20261114-pilot-8shots/gen_pilot.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
POLICY=json.loads((ROOT/'shared/image-api/channel-policy.json').read_text())
ACTIVE=POLICY['policies'][POLICY['active']]
CHANNELS={k:POLICY['channels'][k] for k in ACTIVE['parallel_channels']}
LOCKS={k:threading.Lock() for k in CHANNELS}
DISABLED=set()
for d in ['image/anchors','image/backgrounds','image/references','image/final','logs/requests','qa','video/final','storyboard']:(EP/d).mkdir(parents=True,exist_ok=True)
STYLE='Two-layer hand-drawn 2D story illustration, 16:9. Detailed painted backgrounds with material texture, restrained gradients, ambient occlusion, clear spatial depth and motivated daylight. Characters alone are minimal B-style round-head thin-limb people: pure flat white round heads, two dot eyes and short line mouths, no nose, ears, hair strands, face volume or shading. Five to six heads tall, thin narrow limbs, simple small round or hook hands, simple clothing color blocks and dark blue-grey contours. No realistic anatomy or 3D shading on characters. Flat rendering does not mean physically clean: preserve all story-required dirt, wet waste and damage. No text, letters, numbers, signs, logos, watermarks, UI, borders, split panels or comic symbols. Keep key evidence above bottom fifth. No live or dead cats; the cats have already been taken away.'
CHARS={
 'worker':'experienced cleaner, simple flat teal-blue tunic-shaped work shirt without pockets or folds, extremely thin black rod-like legs and arms as in supplied style reference, tiny mustard-yellow circular mitten gloves, tiny black oval shoes, white round head with dot eyes and short line mouth',
 'partner':'cleaning partner, simple flat muted orange tunic-shaped work shirt without pockets or folds, extremely thin black rod-like legs and arms as in supplied style reference, tiny pale-blue circular mitten gloves, tiny black oval shoes, white round head with dot eyes and short line mouth',
 'landlord':'landlord, simple flat plum-purple tunic-shaped shirt without pockets or folds, extremely thin black rod-like legs and arms as in supplied style reference, tiny empty white circular hands, tiny brown oval shoes, white round head with dot eyes and short line mouth'
}
BASE=ROOT/'projects/人生体验/visual-tests/20261118-minimal-characters-fixed-background/B-round-thin-limbs-edit.png'

def save(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2))

def request(tag,prompt,index=0,reference=None,metadata=None):
 meta_path=EP/'logs/requests'/f'{tag}.json'
 if meta_path.exists():
  old=json.loads(meta_path.read_text())
  if old.get('ok') and (EP/old['file']).exists():return EP/old['file']
 assigned=list(CHANNELS)[index%len(CHANNELS)]
 attempts=[]
 for name in [assigned]+[k for k in CHANNELS if k!=assigned]:
  if name in DISABLED:continue
  cfg=CHANNELS[name]
  for attempt in range(ACTIVE['retry']['same_channel_max']):
   row=dict(tag=tag,assigned=assigned,channel=name,model=cfg['model'],policy=POLICY['active'],prompt=prompt,prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),price_cny=cfg['price_cny'],references=[str(reference)] if reference else [],metadata=metadata or {},fallback_from=assigned if name!=assigned else None)
   started=time.time()
   try:
    key=os.environ.get(cfg['key_env'])
    if not key:raise RuntimeError('configured credential unavailable')
    if reference:
     data,ctype=helper.multipart({'model':cfg['model'],'prompt':prompt,'size':cfg['size'],'n':'1'},{'image':reference});endpoint=cfg['base_url']+'/images/edits'
    else:
     data=json.dumps(dict(model=cfg['model'],prompt=prompt,size=cfg['size'],n=1)).encode();ctype='application/json';endpoint=cfg['base_url']+'/images/generations'
    row['endpoint']=endpoint
    with LOCKS[name]:
     req=urllib.request.Request(endpoint,data=data,headers={'Authorization':'Bearer '+key,'Content-Type':ctype,'User-Agent':'OpenAI/Python/1.60.0','Accept':'application/json'})
     with urllib.request.urlopen(req,timeout=180) as response:
      payload=json.load(response);row['request_id']=response.headers.get('x-request-id');row['http_status']=response.status
    item=payload['data'][0];out=EP/'image'/f'{tag}.png'
    if item.get('b64_json'):out.write_bytes(base64.b64decode(item['b64_json']))
    else:
     with urllib.request.urlopen(urllib.request.Request(item['url'],headers={'User-Agent':'OpenAI/Python/1.60.0'}),timeout=120) as response:out.write_bytes(response.read())
    with Image.open(out) as im:
     im.load();row['dimensions']=list(im.size)
     expected=tuple(map(int,cfg['size'].split('x')))
     if im.size!=expected:raise RuntimeError(f'image size mismatch {im.size} expected {expected}')
    row.update(ok=True,file=str(out.relative_to(EP)),sha256=hashlib.sha256(out.read_bytes()).hexdigest(),qa='完整解码、尺寸通过；待目检',elapsed_s=round(time.time()-started,1))
    attempts.append(row);row['attempts']=attempts[:-1];save(meta_path,row)
    print(tag,name,'OK',row['elapsed_s'],flush=True);return out
   except Exception as e:
    if isinstance(e,urllib.error.HTTPError):row.update(http_status=e.code,error=e.read(1000).decode(errors='replace'))
    else:row['error']=type(e).__name__+': '+str(e)
    row.update(ok=False,elapsed_s=round(time.time()-started,1));attempts.append(row);save(meta_path,dict(ok=False,attempts=attempts));print(tag,name,'FAIL',row.get('http_status',row['error'][:80]),flush=True)
  DISABLED.add(name)
 raise RuntimeError('Both configured image channels unavailable; see request logs')

def anchor(key,index):
 out=EP/'image/anchors'/f'{key}.png'
 if out.exists():return out
 style_crop=EP/'image/anchors/style-crop.png'
 p=STYLE+' Match the attached minimal character EXACTLY in proportion, especially the extremely thin black stick-like arms and legs. Limbs are thin solid black strokes; NO filled trouser legs, NO thick sleeves, NO boots, NO cuffs, NO fingers, NO anatomy. Small colored trapezoid torso, white circular head, legs longer than torso. One isolated full-body front-three-quarter figure on plain pale blue-grey background. ONE person only, neutral standing pose, all limbs visible. Character: '+CHARS[key]+'. Do not copy background. No panels.'
 src=request('anchor-'+key+'-thin',p,index,style_crop,dict(stage='character-reference',character_id=key));shutil.copyfile(src,out);return out

def sheet(paths,out,cols=4):
 w,h=400,225;can=Image.new('RGB',(cols*w,((len(paths)+cols-1)//cols)*(h+24)),(36,39,42));draw=ImageDraw.Draw(can)
 for i,p in enumerate(paths):
  im=ImageOps.fit(Image.open(p).convert('RGB'),(w,h));x=i%cols*w;y=i//cols*(h+24);can.paste(im,(x,y));draw.text((x+5,y+h+4),p.stem,fill='white')
 can.save(out)

def plate(scene,index):
 out=EP/'image/backgrounds'/f'{scene}.png'
 if out.exists():return out
 concept=ROOT/'projects/人生体验/visual-tests/20261120-trash-room'
 approved={'living-full':'01-room-wide.png','kitchen-full':'03-kitchen-roaches.png'}
 if scene in approved:
  shutil.copyfile(concept/approved[scene],out)
  save(EP/'logs/requests'/f'plate-{scene}.json',dict(ok=True,file=str(out.relative_to(EP)),derived_from=str(concept/approved[scene]),stage='approved-environment-master',qa='用户已认可环境小样，原图复用'))
  return out
 plan=json.loads((EP/'storyboard/SHOT_PLAN.json').read_text())
 ref=concept/('03-kitchen-roaches.png' if scene.startswith('kitchen') else '01-room-wide.png')
 envstyle='Detailed hand-painted 2D environment, same material textures, outlines and motivated natural daylight as supplied image; spatial depth, restrained gradients and ambient occlusion, readable midtones, local dirt only, no overall brown or green filter. 16:9. No text, numbers, logos, UI, borders or split panels. NO people, heads, arms, hands, human shapes or cats anywhere.'
 prompt=envstyle+' Preserve supplied apartment architecture and furniture designs as continuity reference. Generate ONE full-frame EMPTY environment master in the required later state. Required state: '+plan['scenes'][scene]+'. Do not keep removed garbage or sofa merely because present in source. Preserve unrepaired material damage. No tools acting by themselves.'
 src=request('plate-'+scene,prompt,index,ref,dict(stage='environment',scene_id=scene,cast='none',environment_state=plan['scenes'][scene]));shutil.copyfile(src,out);return out

def composite_reference(bg,cast,tag):
 ids=[] if cast=='none' else cast.split('+')
 if not ids:return bg
 canvas=Image.new('RGB',(2560,1440),(112,120,126))
 im=ImageOps.contain(Image.open(bg).convert('RGB'),(1920,1440));canvas.paste(im,((1920-im.width)//2,(1440-im.height)//2))
 for i,k in enumerate(ids):
  ref=EP/'image/anchors'/f'{k}.png'
  if not ref.exists():raise FileNotFoundError(ref)
  ch=1440//len(ids);im=ImageOps.contain(Image.open(ref).convert('RGB'),(640,ch));canvas.paste(im,(1920+(640-im.width)//2,i*ch+(ch-im.height)//2))
 out=EP/'image/references'/f'{tag}.png';canvas.save(out);return out

def shot(row,index):
 out=EP/'image/final'/f"{row['id']}.png"
 if out.exists():return out
 bg=EP/'image/backgrounds'/f"{row['scene_id']}.png"
 if not bg.exists():raise FileNotFoundError(bg)
 master=bg
 if row['shot_type']=='C':
  crops={'S03':(0,.1,.35,.95),'S05':(.05,.22,.55,.75),'S06':(.58,.45,1,1),'S13':(.25,.48,.82,.95),'S15':(.4,.5,.95,1),'S22':(.62,.45,1,1),'S24':(.5,.55,1,1),'S39':(.08,.1,.9,.95),'S43':(.2,.25,.9,1),'S48':(.35,.55,.95,1),'S53':(.4,.55,.95,1),'S55':(.35,.55,.95,1),'S64':(.5,.5,1,1)}
  box=crops[row['id']];im=Image.open(bg).convert('RGB');w,h=im.size
  bg=EP/'image/references'/f"{row['id']}-detail-environment.png";im.crop(tuple(round(v*d) for v,d in zip(box,[w,h,w,h]))).save(bg)
 ref=composite_reference(bg,row['cast'],row['id'])
 ids=row['character_ids']
 if ids:
  intro='Attached composite: LEFT 75 percent is the exact environment master; RIGHT strip has identity-only character references top to bottom: '+', '.join(ids)+'. Output ONE full-frame scene, remove reference strip and panels. Preserve room geometry, furniture colors and state. Repose people to the required action, not the neutral reference pose. Exactly '+str(len(ids))+' people in the final image. '
  people=' '.join(k+': '+CHARS[k]+'. ' for k in ids)
 else:
  intro='Attached image is the exact environment master. Output one full-frame newly framed evidence/environment scene; no reference strip. NO people or human body parts. '
  people=''
 camera={'E':'Wide environmental composition, 24mm equivalent, readable room orientation, foreground doorframe or table edge at one side.','M':'Medium view from 3-4 metres, 35mm equivalent, off-center actors, action and surrounding objects both readable.','C':'MANDATORY TIGHT PHYSICAL EVIDENCE CLOSE-UP, camera 30-60 cm from object. Evidence fills most of image, architecture only as cropped context. Do NOT show the full room, window, whole bed or whole sofa. Change camera framing radically from master, preserve materials and required state. Clear spatial contact, no abstract symbols, no isolated icon.'}[row['shot_type']]
 style=STYLE if ids else 'Detailed hand-painted 2D environment/evidence illustration, same outlines, material textures, spatial depth, ambient occlusion and motivated daylight as supplied environment master. Full-frame 16:9. NO people, human heads, hands, limbs, figures, cats, text, numbers, logos, panels or watermark.'
 actor_state=(' Character physical state: '+row['character_state']+' Characters have thin black rod arms/legs, tiny round hands, no fingers, no filled trousers or bulky boots. Physical tasks shown as held poses, not duplicated motion trails.') if ids else ' This is a strictly unoccupied room or object view. No humans or body parts anywhere.'
 prompt=style+' '+intro+people+camera+' Required visible action or evidence: '+row['visual']+' Environment at this exact story stage: '+row['environment_state']+actor_state+' Preserve: '+row['preserve']+' Avoid: '+row['avoid']+' Do not brighten or clean away remaining dirt, do not add repaired surfaces, no scene reset.'
 src=request(row['id'],prompt,index,ref,dict(**row,stage='character-composite' if ids else 'environment-single',environment_master=str(master),detail_environment=str(bg) if master!=bg else None,reference_roles={str(bg):'architecture, furniture, light and current state',**{str(EP/'image/anchors'/f'{k}.png'):'character identity and proportions only' for k in ids}}))
 with Image.open(src) as im:
  ImageOps.fit(im.convert('RGB'),(1920,1080),method=Image.Resampling.LANCZOS).save(out)
 return out

def run_queue(items,fn):
 results=[]
 # One worker per channel, so a queued call never occupies another channel's slot.
 def worker(seq):
  for i,item in seq:results.append(fn(item,i))
 with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(worker,[[(i,x) for i,x in items if i%2==q] for q in range(2)]))
 return results

def repair_plates():
 fixes=[('bedside','Keep the blue-grey sofa PRESENT at center-left, its seat still buried under takeaway rubbish. Keep large heaps across left and middle room; do NOT clear the whole room. ONLY remove a few boxes immediately beside the bed at rear right, exposing half the bed and cardboard cat nest; overturned dirty litter tray near bed. Same original room geometry, window and folding table. No people.',0),('bathroom-full','Make the bathroom visibly blocked by numerous old clothes and full and empty dirty cat-litter sacks, a collapsed cardboard cat nest in the entry, thick hair and sand around partly clogged floor drain. Door opens only half way against clutter. Show cramped old tiled bathroom from doorway. Do not create a mostly empty room. No people.',1)]
 for scene,change,index in fixes:
  ref=ROOT/'projects/人生体验/visual-tests/20261120-trash-room/01-room-wide.png' if scene=='bedside' else EP/'image/backgrounds/bathroom-full.png'
  prompt='Detailed hand-painted 2D environment matching supplied scene and materials, 16:9, readable neutral daylight, NO people, heads, hands, cats, text, logos or panels. Correct only the stated story-state error. '+change
  src=request('plate-'+scene+'-state-fix',prompt,index,ref,dict(stage='environment-correction',scene_id=scene,cast='none',reason='纠正场地提前清空与沙发提前消失' if scene=='bedside' else '加强门后阻挡，确保未清理状态可见'))
  shutil.copyfile(src,EP/'image/backgrounds'/f'{scene}.png')

def corrections():
 plan=json.loads((EP/'storyboard/SHOT_PLAN.json').read_text())
 todo=[('S43','The blue-grey sofa has been SLID FORWARD away from back wall. Tight close-up of the NOW EXPOSED strip of floor behind sofa: broad compressed mat of grey cat hair, clumped litter, brown cat feces, torn paper, clear furniture footprint. Sofa edge only at near left, never covering the exposed contamination.',0),('S57','Restore the same iron bed underneath the rear-right window, and the same folding table at left, absent sofa stays absent. Exactly teal and orange cleaners work adjacent floor sections in foreground. Keep the already visible partial clean floor and dirty residual section.',1),('S58','Restore the same iron bed beneath rear-right window and the folding table at left. Purple landlord stands BESIDE the bed at window, looking toward floor cleaning off-screen. No other people. No missing bed.',2),('S60','This shot takes place INSIDE THE TINY BATHROOM, NOT the living room. Match attached bathroom tiles, small wall sink at left, floor drain toward back right. Teal cleaner with yellow circle gloves bends over cleaning the drain edge using a brush. No bed, sofa, folding table or living room window. Remove loose obstructing sacks but keep residual dirty tiles and drain hair.',3)]
 def fix(item,index):
  sid,change,route=item;s=plan['shots'][int(sid[1:])-1]
  if sid=='S60':bg=EP/'image/backgrounds/bathroom-full.png'
  elif sid=='S43':bg=EP/'image/backgrounds/sofa-exposed.png'
  else:bg=EP/'image/backgrounds/floor-dirty.png'
  ref=composite_reference(bg,s['cast'],sid+'-correction')
  prompt=(STYLE if s['character_ids'] else 'Detailed painted 2D environment evidence view, 16:9, no people or body parts, no text, no panels.')+' Reference LEFT is exact same room architecture, RIGHT identities if any. Output a SINGLE full-frame corrected story scene. '+change+' '+(' '.join(CHARS[k] for k in s['character_ids']))+' Keep white heads unshaded, tiny round hands and black rod limbs. No comic marks, lettering, panels, repaired walls or magical renovation.'
  src=request(sid+'-fact-fix',prompt,route,ref,dict(**s,stage='local-fact-correction',environment_master=str(bg),reason=change))
  out=EP/'image/final'/f'{sid}.png'
  with Image.open(src) as im:ImageOps.fit(im.convert('RGB'),(1920,1080),method=Image.Resampling.LANCZOS).save(out)
  meta=json.loads((EP/'logs/requests'/f'{sid}-fact-fix.json').read_text());save(EP/'logs/requests'/f'{sid}.json',meta)
  return out
 run_queue(list(enumerate(todo)),fix)

if __name__=='__main__':
 if sys.argv[1]=='anchors':
  with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda t:anchor(*t),list(zip(CHARS,range(3)))))
  sheet([EP/'image/anchors'/f'{k}.png' for k in CHARS],EP/'qa/characters.jpg',3)
 elif sys.argv[1]=='plates':
  plan=json.loads((EP/'storyboard/SHOT_PLAN.json').read_text());run_queue(list(enumerate(plan['scenes'])),plate)
  sheet([EP/'image/backgrounds'/f'{k}.png' for k in plan['scenes']],EP/'qa/environments.jpg')
 elif sys.argv[1]=='repair-plates':repair_plates()
 elif sys.argv[1]=='corrections':corrections()
 elif sys.argv[1] in ['pilot','batch']:
  plan=json.loads((EP/'storyboard/SHOT_PLAN.json').read_text())
  if sys.argv[1]=='pilot':items=[(j,plan['shots'][i]) for j,i in enumerate([0,1,6,24,44,68,3,10,30,32,46,63])]
  else:
   lo=int(sys.argv[2]) if len(sys.argv)>2 else 0;hi=int(sys.argv[3]) if len(sys.argv)>3 else len(plan['shots']);items=list(enumerate(plan['shots']))[lo:hi]
  paths=run_queue(items,shot);sheet(sorted(paths),EP/'qa'/f"contact-{sys.argv[1]}-{items[0][1]['id']}-{items[-1][1]['id']}.jpg")
