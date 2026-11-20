from produce import EP,request,save,run_queue
from PIL import Image,ImageOps
from pathlib import Path
import json,shutil,sys,hashlib
P=json.loads((EP/'storyboard/SHOT_PLAN.json').read_text())
REFS=EP/'image/anchors-round';REFS.mkdir(exist_ok=True)
STYLE='''Hand-drawn 2D narrative illustration. All humans have pale grey-white bald round heads, NO nose or hair, tiny close-set C ears, SMALL BLACK VERTICAL OVAL EYES with no large circular white sclera, thin expressive brows, simple closed or slightly open mouth as action requires. Compact clothed bodies about 3.25 heads tall, narrow sloped shoulders, complete volumetric sleeves and trouser legs, small solid hands and shoes. NOT black rod limbs, NOT white stick figures, NOT realistic humans, NOT anime hair or cute babies. Dark grey-brown organic drawn outlines, flat painted shapes with one restrained cool grey soft shadow and reflected room light, grounded contact shadows. Clothes have a few broad folds and localized work dirt. Characters MUST match supplied identity references in face, proportions and clothes. Background retains detailed existing hand-painted materials, space, waste state and daylight. No text, symbols, comic marks, UI, logos, panels or cats. '''
CHARS={'worker':'experienced cleaner in blue-grey zip hooded work jacket, charcoal trousers, yellow rubber gloves, dark work shoes','partner':'assistant cleaner in muted burnt-orange zip hooded work jacket, charcoal trousers, pale-blue rubber gloves, dark work shoes, slightly narrower frame than worker','landlord':'landlord in muted plum-purple ordinary collared jacket, dark trousers, small bare pale grey hands, brown shoes, slightly wider torso'}
def setup():
 approved=EP/'image/character-current/清理垃圾屋_主角_圆头手绘_v2.png'
 shutil.copyfile(approved,REFS/'worker.png')
 def make(key,index):
  out=REFS/f'{key}.png'
  if out.exists():return
  prompt=STYLE+' Attached image is the USER APPROVED worker design. Create a NEW separate '+key+' reference in SAME cartoon drawing language and 3.25 heads proportions. Exactly ONE full-body character only, entire head and shoes visible with margin, quiet light grey-green painted background and soft grounded shadow, no room clutter. Identity: '+CHARS[key]+'. Match approved small black oval eyes, tiny ear, round head and compact fully clothed body; relaxed slightly sloped shoulders and knees, one hand at side and other loosely bent, calm neutral observant expression. No duplicate approved worker. Do not copy worker yellow gloves or blue-grey clothing. No text, labels, panels, extra people.'
  src=request('round-anchor-'+key,prompt,index,approved,dict(stage='character-reference',character_id=key,approved_worker=str(approved),fact=CHARS[key],cast=key));shutil.copyfile(src,out)
 with __import__('concurrent.futures').futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda x:make(*x),[('partner',0),('landlord',1)]))
def composite(scene,ids,tag):
 canvas=Image.new('RGB',(2800,1400),(111,119,121));im=ImageOps.contain(Image.open(scene).convert('RGB'),(1920,1400));canvas.paste(im,((1920-im.width)//2,(1400-im.height)//2))
 for i,k in enumerate(ids):
  im=Image.open(REFS/f'{k}.png').convert('RGB')
  if k=='worker':im=im.crop((int(im.width*.24),int(im.height*.05),int(im.width*.51),int(im.height*.98)))
  im=ImageOps.contain(im,(880,1400//len(ids)));canvas.paste(im,(1920+(880-im.width)//2,i*(1400//len(ids))+(1400//len(ids)-im.height)//2))
 out=EP/'image/references'/f'{tag}.png';canvas.save(out);return out

def shot(row,index):
 sid=row['id'];tag='round-'+sid;out=EP/'image/final'/f'{sid}.png'
 log=EP/'logs/requests'/f'{tag}.json'
 if log.exists() and json.loads(log.read_text()).get('applied'):return out
 old=json.loads((EP/'logs/requests'/f'{sid}.json').read_text())
 # Source scene is current final, preserving corrected stage and exact action.
 ids=row['character_ids'];source=EP/'image/references'/f'{tag}-scene.png'
 if not source.exists():shutil.copyfile(out,source)
 ref=composite(source,ids,tag)
 prompt=STYLE+' Attached composite LEFT shows exact scene, factual stage, action, actors count and framing to retain; RIGHT identity references in order: '+', '.join(ids)+'. Output ONE full-frame 16:9 illustration with NO panels or reference strip. REPLACE EVERY OLD THIN STICK PERSON in LEFT with new approved round-headed fully clothed cartoon characters from RIGHT. No thin old person may remain. Reconstruct natural compact anatomy and poses; keep same camera and environment state, furniture, dirt, tools and factual action. Exact people count '+str(len(ids))+'. '+' '.join(k+': '+CHARS[k]+'.' for k in ids)+' Required action: '+row['visual']+'. Required factual scene state: '+row['environment_state']+'. Character state: '+row['character_state']+'. Preserve corrected furniture placement: iron bed and folding table remain when present, sofa stays absent after removal. Cleaning stage must not reset. Do not copy upright neutral pose from identity reference; show held moment of required work. Tiny ears, small black eyes, restrained expressions, pale head softly shaded by room light. No giant hands or feet. Bottom fifth not used for key evidence.'
 meta=dict(**row,stage='approved-roundhead-restyle',environment_master=old['metadata']['environment_master'],source_scene=str(source),reference_roles={str(source):'current scene facts/action/state only',**{str(REFS/f'{k}.png'):'approved identity/proportion/style only' for k in ids}})
 src=request(tag,prompt,index,ref,meta)
 with Image.open(src) as im:ImageOps.fit(im.convert('RGB'),(1920,1080),method=Image.Resampling.LANCZOS).save(out)
 d=json.loads(log.read_text());d['applied']=True;save(log,d);save(EP/'logs/requests'/f'{sid}.json',d)
 print('APPLIED',sid,flush=True);return out

def intro():
 s=json.loads((EP/'storyboard/INTRO_PLAN.json').read_text())['shots'][0];source=EP/'image/intro/v1/人生体验_清理垃圾屋_引入_01_v1.png';ref=composite(source,['partner'],'round-intro')
 prompt=STYLE+' LEFT is exact kitchen scene and released-box cockroach action, RIGHT is new partner identity. Output single full scene, replace old thin orange person with new compact round-headed orange-clothed partner. Preserve cardboard box tilted onto rubbish foreground left, realistic small cockroaches scattering along exposed cabinet-wall seam. Orange partner right recoils with shoulders raised, knees soft and hands pulled away, simple startled eyebrows and small open mouth. Exactly ONE person, complete cloth sleeves and trousers, pale-blue gloves, small oval black eyes. Match approved compact head/body proportions. Preserve kitchen geometry, dirt and light. No text, panel, motion line or surprise symbol.'
 src=request('round-intro-01',prompt,1,ref,dict(stage='intro-restyle',cast='partner',fact=s['fact'],environment_master=str(EP/'image/backgrounds/kitchen-full.png'),cue=s['cue']))
 dest=EP/'image/intro/v2';dest.mkdir(exist_ok=True)
 with Image.open(src) as im:ImageOps.fit(im.convert('RGB'),(1920,1080),method=Image.Resampling.LANCZOS).save(dest/'人生体验_清理垃圾屋_引入_01_v2.png')
 shutil.copyfile(EP/'image/intro/v1/人生体验_清理垃圾屋_引入_02_v1.png',dest/'人生体验_清理垃圾屋_引入_02_v2.png')
if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='anchors':setup()
 elif mode=='intro':intro()
 else:
  selected=[s for s in P['shots'] if s['character_ids']]
  if mode=='pilot':selected=[s for s in selected if s['id'] in ['S02','S35','S45']]
  run_queue(list(enumerate(selected)),shot)
