from produce import *
api.TIMEOUT_S=240
PLAN=json.loads((EP/'storyboard/SHOT_PLAN-v1.json').read_text())
# new2 returned repeated HTTP 502 across both tested assets; drain unstarted requests to active peer, per policy.
DISABLED={'new2'}
UNAVAILABLE.update(DISABLED)
original_generate=generate

def draw(tag,prompt,ref=None,index=0):
 # Keep original assigned channel in log, but do not keep hitting a demonstrably unavailable service.
 desired=channels[index%2]['name']
 actual=index if desired not in DISABLED else next(i for i,c in enumerate(channels) if c['name'] not in DISABLED)
 out=original_generate(tag,prompt,ref,actual)
 m=json.loads(MANIFEST.read_text());m[tag]['assigned_channel']=desired
 if desired in DISABLED:m[tag]['fallback_from']=desired;m[tag]['fallback_reason']='channel unavailable: repeated HTTP 502 on preflight'
 MANIFEST.write_text(json.dumps(m,ensure_ascii=False,indent=2))
 return out

STYLE=POS+', '+CEL
COMMON='Single 16:9 image, sharp black contour linework, deep focus, no soft airbrush shading, at most three flat colors per surface. Composition off center, 28mm spatial staging, a foreground object clips one corner only, clearly readable foreground middle ground and background. Keep two visible surface wear details and one ordinary used household object. No printed or handwritten symbols, no lettering, no text, no numbers, no signs, no UI, no split panels, no captions, no borders or watermarks.'

def plate(scene,index):
 # Rental side view is a camera angle of the same room, not a new architectural master.
 if scene=='room-side': return plate('desk',index)
 target=EP/'image/backgrounds'/f'{scene}.png'
 if target.exists():return target
 prompt=POS+'. '+COMMON+' Empty environment master: '+PLAN['scenes'][scene]+' No people, no faces or hands, no figures in photographs. Avoid: '+NEG
 f=draw('plate-'+scene,prompt,index=index);shutil.copyfile(f,target);return target

def reference(bg,cast,tag):
 refs=[]
 if 'protagonist' in cast or cast=='hand':refs=[EP/'image/anchors/protagonist-front.png',EP/'image/anchors/protagonist-face.png']
 if 'mother' in cast:refs.extend([EP/'image/anchors/mother.png',EP/'image/anchors/mother-face.png'])
 if 'chen' in cast:refs.append(EP/'image/anchors/chen.png')
 if 'young' in cast:refs.append(EP/'image/anchors/protagonist-back.png')
 if tag.startswith('S') and tag[1:3].isdigit() and int(tag[1:3])>=31 and (EP/'image/evidence-content/photo-after.png').exists():refs.append(EP/'image/evidence-content/photo-after.png')
 canvas=Image.new('RGB',(2560,1440),(94,96,99))
 main=ImageOps.contain(Image.open(bg).convert('RGB'),(1920,1440));canvas.paste(main,((1920-main.width)//2,(1440-main.height)//2))
 if refs:
  cellh=1440//len(refs)
  for i,r in enumerate(refs):
   im=ImageOps.contain(Image.open(r).convert('RGB'),(640,cellh));canvas.paste(im,(1920+(640-im.width)//2,i*cellh+(cellh-im.height)//2))
 out=EP/'image/references'/f'{tag}.png';canvas.save(out);return out

def shot(s,index):
 dest=EP/'image/final'/f"{s['id']}.png"
 if dest.exists():return dest
 # Exact evidence callbacks reuse the approved physical object, not a freshly reimagined one.
 callbacks={'S34A':'S01A','S34B':'S10A'}
 if s['id'] in callbacks:
  parent=EP/'image/final'/f"{callbacks[s['id']]}.png"
  if not parent.exists():raise FileNotFoundError(parent)
  shutil.copyfile(parent,dest)
  save_record(s['id'],dict(ok=True,file=str(dest.relative_to(EP)),derived_from=callbacks[s['id']],reason='same evidence object at opening/ending callback',sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),fact=s['fact'],character_ids=s['character_ids'],evidence_id=s['evidence_id']))
  return dest
 bg=plate(s['scene_id'],index)
 if s['cast']=='none':
  # Recompose from actual plate for an exact evidence state; no identity needed.
  ref=bg
  intro='Use attached environment master as continuity reference. Produce ONE full-frame new composition with the same space and props. '
 else:
  ref=reference(bg,s['cast'],s['id'])
  intro='Attached reference layout: LEFT 75 percent is the empty environment master, RIGHT strip contains identity-only references. OUTPUT ONE FULL-FRAME SCENE, no reference strip, no panels. Retain environment materials, prop designs, light direction and architecture. Add only the specified people, matching reference faces, hair, physique and exact clothing. Do not copy standing reference poses. '
  if s['cast']=='hand':intro+='Show only the specified adult hand with olive sleeve cuff, no full person, hand anatomy correct, five fingers. '
  if 'young' in s['cast']:intro+='Child is an age9 memory state: small body with blue jacket and plain schoolbag, back view, do not put an adult in a childs body. '
  if s['scene_id'].startswith('photo'):intro+='Actors exist INSIDE the photographic image ONLY; do not insert a giant person into the surrounding tabletop. '
 parents={'S14B':'S14A','S20B':'S20A','S21B':'S19B','S27B':'S27A','S28A':'S27B','S28B':'S28A'}
 if s['id'] in parents:
  ref=reference(EP/'image/final'/f"{parents[s['id']]}.png",s['cast'],s['id'])
  intro+='Left reference is the immediately connected previous scene state: keep all existing actors exact identity, clothes, relative height, set and prop positions; change only specified gestures or expressions. '
 if 13<=int(s['id'][1:3])<31:intro+='At this present-day stage do not add ANY recognizable family portrait or mothers face to desk photographs. If incidental print appears, it contains only bare brown ground and the lone man, mother completely absent. '
 if int(s['id'][1:3])>=31:intro+='The lowest right reference is the exact altered family snapshot PROP, not an extra live actor: copy that photo image only onto any small print on desk. Do not add mother or extra person to the missing-mother snapshot. '
 if s['id']=='S07B':intro+='Change camera angle to look ACROSS the guardrail. Guardrail crosses lower foreground horizontally; bare dry field occupies 70 percent frame, ridge at upper third. Car and roadway entirely OUTSIDE image. No buildings, poles, foundations, branches or figures. '
 if s['id']=='S10A':
  parent=EP/'image/final/S09B.png'
  ref=reference(parent,s['cast'],s['id'])
  intro+='The LEFT reference is the BEFORE physical snapshot. Keep the tabletop, bent photo border, exact framing and mans EXACT pose, face and arm unchanged. Change only inside the print: remove the mother and plate completely and replace kitchen by empty brown hillside. No removal silhouette, fragments, sand human, ghost, second man or UI. '
 if s['id']=='S17A':
  ref=reference(EP/'image/final/S15B.png',s['cast'],s['id'])
  intro+='Keep the same physical certificate dimensions, ruled field layout and folded paper from the LEFT reference; only move the finger away so empty field is exposed in morning light. '
 if 'mother' in s['cast']:intro+='Mother is 58 with visibly mature narrow eyes and facial lines, short loose dark-grey hair, grey temples, NO bun, NO large youthful eyes; match close face reference, no age reduction. '
 prompt=STYLE+'. '+intro+COMMON+' Required visible state: '+s['visual']+' Preserve ordinary worn state; no exaggerated distress faces. Avoid: '+NEG
 rev=json.loads((EP/'image/revisions.json').read_text()) if (EP/'image/revisions.json').exists() else {}
 tag=s['id']+rev.get(s['id'],'')
 f=draw(tag,prompt,ref,index);shutil.copyfile(f,dest)
 m=json.loads(MANIFEST.read_text());m[s['id']]=dict(m[tag]);m[s['id']].update({k:s[k] for k in ['fact','character_ids','evidence_id','scene_id','cast']});MANIFEST.write_text(json.dumps(m,ensure_ascii=False,indent=2))
 return dest

def intro_images():
 for number,src in [(1,'S10A'),(2,'S31B')]:
  s=next(s for s in PLAN['shots'] if s['id']==src)
  f=shot(s,PLAN['shots'].index(s));dest=EP/'image/intro'/f'intro-{number:02}.png';shutil.copyfile(f,dest)
 # Intro use the exact story evidence and recording composition, not extra unrelated art.
 (EP/'image/intro/manifest.json').write_text(json.dumps({'intro-01.png':{'source_shot':'S10A','paragraph':'我回到故乡，却发现整座镇子不见了。连合影里的母亲，也变成了一片荒漠。'},'intro-02.png':{'source_shot':'S31B','paragraph':'直到认识我十年的朋友问我是谁，我才决定录下这条视频。'},'included_in_body_video':False},ensure_ascii=False,indent=2))

if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='pilot':ids=['S01A','S01B','S02A','S02B','S03A','S04A']
 elif mode=='range':ids=[s['id'] for s in PLAN['shots'][int(sys.argv[2]):int(sys.argv[3])]]
 elif mode=='intros':intro_images();sys.exit(0)
 else:raise ValueError(mode)
 paths=[]
 for sid in ids:
  s=next(s for s in PLAN['shots'] if s['id']==sid);paths.append(shot(s,PLAN['shots'].index(s)))
 sheet(paths,EP/'qa'/f'contact-{mode}-{ids[0]}-{ids[-1]}.jpg',3)
 print('BATCH COMPLETE',ids[0],ids[-1],flush=True)
