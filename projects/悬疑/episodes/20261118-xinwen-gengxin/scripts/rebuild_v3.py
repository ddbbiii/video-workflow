"""画质重制：独立整幅生成、参考驱动，不改变锁定旁白。"""
from pathlib import Path
import sys, json, threading, shutil, hashlib, concurrent.futures, time, math, importlib.util
from PIL import Image, ImageOps, ImageDraw
EP=Path(__file__).resolve().parents[1];ROOT=EP.parents[3]
spec=importlib.util.spec_from_file_location('image_api',ROOT/'projects/悬疑/visual-tests/20261114-pilot-8shots/gen_pilot.py')
api=importlib.util.module_from_spec(spec);sys.modules[spec.name]=api;spec.loader.exec_module(api)
api.HERE=EP;api.RAW=EP/'image/raw';api.CROPS=EP/'image/crops'
api.TIMEOUT_S=150
POLICY=json.loads((ROOT/'shared/image-api/channel-policy.json').read_text())
POS,NEG,CEL=[api.read_block(n) for n in ['STYLE_POS','STYLE_NEG','CEL_BOOST']]
PLAN=json.loads((EP/'storyboard/SHOT_PLAN-production-v3.json').read_text())
LOCKS={x:threading.Lock() for x in ['new2','dkl-b']}
STATELOCK=threading.Lock()
DISABLED=set()
QUALITY=('One full-frame 16:9 illustration, no collage, no grid. Crisp deliberate ink contours, '
 'large controlled flat cel color regions, no soft airbrush shading or texture veil. '
 'Readable midtones on faces, hands, props and room surfaces even at night. '
 'Maintain distinct dark values; do not crush shadows or apply a dark wash. '
 'Use cold grey-blue ambient fill and a single small warm lamp. '
 'Clean flat fills describe rendering technique, not pristine physical condition. '
 'Keep the specified worn surfaces as restrained hard-edged shapes. '
 'No lettering, letters, digits, captions, signage, interface icons, watermark, blood, ghosts or extra people.')
VISUAL=json.loads((EP/'storyboard/visual-plan-v3.json').read_text())
CHAR=VISUAL['CHAR'];SCENES=dict(VISUAL['SCENES'])
SCENES['living']=SCENES['living'].replace('No people, no phones, no text.', 'No people, no phones, no text. Preserve room layout across all angles; make the scratched table and sofa sharply legible.')

def write(path,data):
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2))

def reference(tag,paths):
 tiles=[]
 for p in paths:
  im=Image.open(p).convert('RGB'); im.thumbnail((1600,1000),Image.Resampling.LANCZOS); tiles.append(im)
 out=Image.new('RGB',(sum(t.width for t in tiles),1000),(70,76,84));x=0
 for t in tiles:out.paste(t,(x,(1000-t.height)//2));x+=t.width
 p=EP/'image/references'/f'{tag}.png';out.save(p);return p

def gen(tag,content,refs=None,cel=True,assigned='new2'):
 target=EP/'image/raw'/f'{tag}.png'; side=EP/'logs'/f'{tag}.json'
 if target.exists() and side.exists() and json.loads(side.read_text()).get('ok'):return target
 empty='EMPTY ENVIRONMENT ONLY. ZERO PEOPLE, ZERO HUMAN FIGURES OR PORTRAITS. Draw only furniture, architecture and the requested objects.' if not cel else ''
 prompt='\n'.join([empty,POS,CEL if cel else '',QUALITY,content,empty,'Avoid: '+NEG])
 names=[assigned, 'dkl-b' if assigned=='new2' else 'new2']; fallback=None
 for name in names:
  if name in DISABLED:continue
  # Two distinct live edit failures already prove this endpoint unavailable for reference work.
  if name=='new2' and refs:
   failures=[]
   for log in (EP/'logs').glob('*new2-attempt*.json'):
    rec=json.loads(log.read_text())
    if rec.get('endpoint')=='edits' and not rec.get('ok'):failures.append(rec)
   if len(failures)>=2:
    fallback='new2 reference edits: repeated live HTTP502';continue
  channel=dict(POLICY['channels'][name],name=name,policy=POLICY['active'])
  for attempt in range(1,3):
   with LOCKS[name]:
    if name in DISABLED:break
    print('REQUEST',tag,name,attempt,flush=True)
    info=api.call(channel,prompt,{'tag':tag+'-'+name},refs,attempt)
   info.update(policy=POLICY['active'],model=channel['model'],request_id=None,
    endpoint_url=channel['base_url']+'/images/'+('edits' if refs else 'generations'),
    assigned_channel=assigned,fallback_from=fallback,
    references=[str(refs.relative_to(EP))] if refs else [],full_frame_single=True,
    reference_role='scene structure and locked character identity only; draw the specified new shot')
   if info.get('ok'):
    source=EP/info['file'];im=Image.open(source);expected=tuple(map(int,channel['size'].split('x')))
    if im.size!=expected:
     info.update(ok=False,error='Unexpected native dimensions')
    else:
     shutil.copyfile(source,target);info['native_size']=list(im.size);info['source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
     info['metrics']=api.measure(target); info['file']=str(target.relative_to(EP))
     write(side,info)
     print('READY',tag,name,im.size,round(info.get('elapsed_s',0),1),flush=True)
     return target
   write(EP/'logs'/f'{tag}-{name}-attempt{attempt}.json',info)
   print('FAILED',tag,name,info.get('http_status'),str(info.get('error'))[:140],flush=True)
   if info.get('http_status') in [401,403]:
    DISABLED.add(name);break
  fallback=name
  if name==assigned:
   DISABLED.add(name)
   print('CHANNEL_UNAVAILABLE',name,'remaining requests use the other active channel',flush=True)
 raise RuntimeError('Both configured image channels unavailable: '+tag)

def channel(i):return ['new2','dkl-b'][i%2]

def lanes(items,func):
 indexed=list(enumerate(items))
 def run(lane):return [func(pair) for pair in indexed[lane::2]]
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:list(ex.map(run,[0,1]))

def plates(names=None):
 names=names or list(SCENES)
 def one(pair):
  i,name=pair;ref=None
  if name in ['window','door','table'] and (EP/'image/plates/living.png').exists():ref=EP/'image/plates/living.png'
  if name=='bedroom-day' and (EP/'image/plates/bedroom.png').exists():ref=EP/'image/plates/bedroom.png'
  if ref:ref=reference('plate-'+name,[ref])
  p=gen('plate-'+name,SCENES[name],ref,False,channel(i));shutil.copyfile(p,EP/'image/plates'/f'{name}.png');return name
 lanes(names,one)

def shot(s,i):
 ids=s['character_ids'];scene=s['scene_id'];refpaths=[EP/'image/plates'/f'{scene}.png']
 for n in ids:
  if n=='zhouning':refpaths.extend([EP/'image/anchors/zhouning-front.png',EP/'image/anchors/zhouning-face.png'])
  elif n=='chenyi':refpaths.append(EP/'image/anchors/chenyi-front.png')
 ref=reference(s['id'],refpaths)
 desc='; '.join(CHAR.get(n,'one adult Chinese woman police officer in plain navy uniform' if n=='officer' else 'one middle-aged Chinese woman doctor in plain white coat') for n in ids)
 framing={'E':'Wide room or environmental view, foreground doorway edge, people in natural adult proportions, full setting clear, no tiny people.',
 'M':'Medium shot, adult bodies in natural proportions, clear hand and face silhouettes, background furniture visible, foreground table corner or door edge.',
 'C':'Close three-quarter composition, expressive restrained adult face or the specified hands and prop, crisp eyes and contours, no cropped chin.'}[s['shot_type']]
 state=''
 if scene in ['living','window','door']:
  curtain='partly open' if int(s['id'][1:])<=20 else 'fully closed'
  if int(s['id'][1:])>=53:curtain='partly open in daytime'
  state+=f' Curtains {curtain}.'
 if scene=='living':
  cup='upright' if int(s['id'][1:])<=30 or int(s['id'][1:])>=53 else 'lying on its side, navy cap toward window at image right, mountain sticker facing up'
  state+=f' Exactly one pale-grey thermos with navy screw cap and one wordless blue mountain travel sticker on coffee table: {cup}. No other cups except the two tiny drinking glasses from dinner.'
 action=s['visual'].replace('Zhouning','Zhouning (dark-red cardigan, shoulder-length black hair)').replace('Chenyi','Chenyi (IVORY sweater, black ponytail)')
 content=('Attached reference strip: first image is EMPTY scene architecture, following images are locked character identities. '
  'Draw ONE new complete scene, never copy reference-strip layout. Preserve faces, hair, clothes and room structure; change pose and expression exactly as requested. '
  +framing+' Camera eye-level or slightly above, deep focus, subject on a third line. '
  +'EXACT CAST: '+desc+'. '+SCENES[scene]
  .replace('No people,','').replace('No people.','').replace('no phones,','')
  +' ACTION OVERRIDES REFERENCE POSES AND INITIAL PROP STATES: '+action+' '+state
  +' Preserve the scene wear: scratched furniture and scuffed skirting or chipped paint, plus lived-in furniture; do not turn room into a ruin. '
  'No extra person, intruder, extra phone, duplicated limbs or cups. Any phone display is blank neutral grey without writing. '
  'Story fact to depict (do not write it in the image): '+s['fact'])
 if s['id']=='S06':content+=' Exactly ONE thermos: held by Chenyi in ivory sweater, being lowered to table. No second thermos on the table. Zhouning wears red and holds no cup.'
 if s['id']=='S02':content+=' Chenyi in ivory sweater is the ONLY phone holder and author of the post. Zhouning in red has empty hands.'
 # Descriptions at the start specify exact cast; environment reference must not erase them.
 content=content.replace('No driver visible, no people,','No driver visible,')
 p=gen(s['id'],content,ref,True,channel(i));shutil.copyfile(p,EP/'image/final'/f"{s['id']}.png")
 return s['id']

def characters(pilot=False):
 rows=[s for s in PLAN['shots'] if s['character_ids']]
 if pilot:rows=rows[:6]
 if not pilot and len(sys.argv)>2:
  lo,hi=map(int,sys.argv[2:4]);rows=[s for s in rows if lo<=int(s['id'][1:])<=hi]
 lanes(rows,lambda pair:shot(pair[1],pair[0]))

def sheet(tags,name):
 out=Image.new('RGB',(1440,math.ceil(len(tags)/3)*295),(35,40,48));d=ImageDraw.Draw(out)
 for i,t in enumerate(tags):
  p=EP/'image/raw'/f'{t}.png'
  if not p.exists():continue
  im=ImageOps.fit(Image.open(p).convert('RGB'),(480,270),method=Image.Resampling.LANCZOS)
  x=i%3*480;y=i//3*295;out.paste(im,(x,y+25));d.text((x+8,y+5),t,fill='white')
 out.save(EP/'qa'/name,quality=95)

def evidence():
 def task(tag,content,ref=None,i=0):return gen('evidence-'+tag,content,ref,True,channel(i))
 def cars():
  final=task('finalcar','One dark navy compact SUV crashed FRONT-first against a large roadside tree, seen from rear left three-quarter view. Rear fills left-middle frame; crumpled FRONT is at far right. Sharp flat cel geometry. LEFT rear quarter panel has a short pale horizontal scrape, and a small missing paint chip immediately BELOW LEFT taillight. Background ordinary Chinese neighborhood road, chipped curb, worn guardrail, laundry on far balconies. No people, bodies, writing, logos or readable plates.',None,1)
  task('scratch','Exact same dark navy SUV and same LEFT rear light as reference. ONE full-frame HIGH RESOLUTION close view of LEFT rear quarter and taillight; rear panel fills most frame, existing short pale horizontal cosmetic scrape and tiny missing paint chip immediately BELOW LEFT taillight are prominent and match reference positions. Preserve taillight design, body shape and relative marks. Context sliver of worn curb and cold night street. Do not add new damage, hands, people, writing, brands or plates. This is a new close viewpoint, not a collage.',final,1)
  parked=task('parkedcar','Reference is ONLY vehicle design: depict EXACT same dark navy SUV, rear lights, LEFT rear cosmetic scrape and paint chip. NOW parked normally PARALLEL to curb in DAYLIGHT. All wheels sit on flat clear parking pavement. FRONT fully INTACT, no tree touching car, no collision, no bent bonnet. View rear left three-quarter, show entire car including intact front. Background worn apartment facade and balcony laundry; no other cars close to this one. No people, text or brands.',final,0)
  task('gatecar','Attached references: left is exact gatehouse architecture, right is vehicle identity. A single news accident illustration at NIGHT: exact dark navy SUV with crumpled front near tree OUTSIDE neighborhood gate; green roof gatehouse and orange parcel lockers clearly recognizable in background. Match dark navy SUV rear lamp and old left rear scrape. Cracked curb, worn fence, distant balcony laundry. No people or bodies. One full scene, no collage or text.',reference('gate-evidence',[EP/'image/plates/estate.png',final]),1)
 def props():
  task('oldcar','Original anonymous news photo: small pale silver sedan crashed nose-first into a roadside tree, seen from rear left three-quarter. Rural road with old worn fence and chipped curb, distant warm street lamp. Rear nearest viewer; front visibly crumpled against tree. No people, no bodies, no blood, no text or logos.',None,0)
  task('darkcar','Changed news photo: dark grey compact sedan with crumpled front against a tree on a DIFFERENT suburban road, worn low concrete wall, cracked pavement and faded traffic paint. View rear right three-quarter. No people, no bodies or text.',None,1)
  task('cup','Use ONLY reference thermos identity: pale-grey cylinder with dark navy screw cap and one wordless blue mountain travel sticker, one top sticker corner visibly lifted. Show ONE upright thermos isolated, full object LARGE, on perfectly SOLID MAGENTA background. Crisp flat cel edge, no cast shadow, no other object, no writing, lettering, numbers, logo, pattern or scene. Keep exact navy cap and blue mountain sticker.',EP/'image/plates/living.png',0)
  task('phone','ONE smartphone in LANDSCAPE orientation lying diagonally on scratched wooden coffee table. Close view, phone fills nearly entire frame, all four corners visible. Its large landscape screen is a single flat uniform medium-grey quadrilateral (#888888), ABSOLUTELY BLANK without text, UI, symbols, shine, glare, photo or reflection. Bezel dark navy, no logo. Table visible only as narrow margin, chipped wood and old water ring, cold window light and small warm lamp reflection on wood. No hands, people, extra phone, cup or lettering.',None,1)
  task('bedside','Close shot of ONE phone with blank grey display on scratched bedside table beside rumpled grey adult bed. Night, grey curtains fully closed, taped charging cable, chipped tabletop, faint wall water stain. Warm bedside lamp and cold ambient light. No cups, sofa, numbers, letters, icons, interface or people.',EP/'image/plates/bedroom.png',0)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
  for f in [ex.submit(cars),ex.submit(props)]:f.result()
 for i,sid in enumerate(['S14','S54']):
  s=next(s for s in PLAN['shots'] if s['id']==sid)
  text=s['visual']+' Preserve attached room architecture. Exactly ONE grey thermos with navy cap and wordless mountain sticker UPRIGHT. '+('NIGHT, curtains partly open, face-up blank phone on table.' if sid=='S14' else 'DAYTIME days later, curtains partly open, phone FACE DOWN on table. No glowing screen.')+' No people, text, hidden watcher or extra cup. Scratched table, scuffed skirting and dinner bowls remain.'
  p=gen('specific-'+sid,text,EP/'image/plates/living.png',False,channel(i));shutil.copyfile(p,EP/'image/final'/f'{sid}.png')

def repair_masters():
 for name,text,ref in [
  ('bedroom','Use attached EMPTY DAYTIME ROOM for exact architecture. Change ONLY lighting and time to NIGHT: closed grey curtains covering the window, cold ambient light with one warm bedside lamp. Grey rumpled bed and scratched bedside table, tissue box, taped cable and old wall mark remain. Bed is completely EMPTY. No person, face, human silhouette, body or human reflection anywhere.',EP/'image/plates/bedroom-day.png'),
  ('police','Same police-station reception room architecture as reference, but REMOVE the foreground woman entirely. Show ONLY the empty worn reception desk, chairs and water dispenser. No people behind desks or doors, no portraits, silhouettes or human reflections. No lettering or badge symbols.',EP/'image/plates/police.png'),
  ('table','Use attached coffee table for exact worn wood and teal sofa identity. NEW close oblique overhead viewpoint: scratched brown tabletop fills almost entire frame, chipped table edge foreground, one old water ring on right. ONLY a narrow strip of LOWER teal sofa visible behind table. Do not show any window, curtain, lamp or door in this tight composition. Table completely EMPTY: no cup, phone, bowls, glass, hands or people. Hard clean flat geometry with readable wood shape, cold ambient light from right and weak warm spill from left.',EP/'image/plates/table.png')]:
  path=gen('master-fixed-'+name,text,reference('fix-'+name,[ref]),False,'dkl-b')
  shutil.copyfile(path,EP/'image/plates'/f'{name}.png')
  for old in (EP/'image/raw').glob('plate-'+name+'*.png'):old.unlink()
 sheet(['master-fixed-bedroom','master-fixed-police','master-fixed-table'],'master-fixes-v3.jpg')

def repair_frames():
 fixes={
  'S06':'Change ONLY Zhouning (woman in dark-red cardigan): REMOVE the phone and any strap or wire near her gesturing hand. Her hand is EMPTY, fingers relaxed in a casual dismissive gesture, she smiles slightly. Keep Chenyi in ivory sweater lowering the ONE grey thermos, same room and open curtains.',
  'S23':'Change ONLY the window: pull opaque GREY CURTAINS COMPLETELY CLOSED across ALL window glass. No outdoors, gatehouse or blue window pane visible. Keep both women and the phone positions unchanged.',
  'S24':'Change ONLY the window behind them: GREY CURTAINS COMPLETELY CLOSED, no exposed glass or view outside. Keep Zhouning (red) making the call and Chenyi (ivory) using her own phone unchanged.',
  'S25':'Change ONLY the window: GREY CURTAINS COMPLETELY CLOSED, no outdoor view or exposed glass. Preserve the two women, their phones and the locked entry door.',
  'S27':'Correct the phone handoff: Chenyi (woman in IVORY sweater and PONYTAIL, RIGHT side) extends ONE smartphone in HER RIGHT HAND toward Zhouning (woman in DARK-RED CARDIGAN, LEFT side). Zhouning has BOTH HANDS EMPTY, lowered, and leans away slightly. ONLY ivory-sweater woman holds the phone. Keep grey curtains fully closed, room and faces unchanged.',
  'S30':'Correct actor roles and pre-collision action. Zhouning (DARK-RED cardigan, shoulder-length hair) is STANDING CLOSEST to the table right edge and TURNING, her ELBOW just above and approaching the ONE UPRIGHT grey thermos with navy cap and blue mountain sticker. Her hands hold NOTHING. Chenyi (IVORY sweater, PONYTAIL) stands FARTHER BEHIND holding ONE phone, not touching the thermos. Grey curtains fully closed. Show the elbow and cup relationship clearly. Do not show the cup already falling.',
  'S32':'Correct actor roles: Zhouning (RED cardigan, LEFT) bends toward fallen cup, one EMPTY HAND paused above tabletop; she holds NO PHONE. Chenyi (IVORY sweater, RIGHT) extends ONE PHONE in HER RIGHT HAND toward Zhouning face, stopping her from picking up cup. Exactly one phone and one fallen thermos. Navy cup cap points RIGHT; sticker faces UP. Keep room, table and fully closed curtains.',
  'S36':'Change ONLY thermos orientation. The ONE grey thermos remains LYING ON ITS SIDE at table edge: dark NAVY CAP must be at its RIGHT END toward the window on image right, pale grey BASE at LEFT, wordless mountain sticker UPWARD. No upright cup. Keep two women checking room and fully closed curtains.'}
 for sid,change in fixes.items():
  p=gen('repair-'+sid,'Edit attached scene, preserve full native detail, adult faces, exact clothing and geometry. '+change+' One full-frame scene, no panels or writing.',EP/'image/final'/f'{sid}.png',True,'dkl-b')
  shutil.copyfile(p,EP/'image/final'/f'{sid}.png');shutil.copyfile(p,EP/'image/raw'/f'{sid}.png')
  d=json.loads((EP/'logs'/f'repair-{sid}.json').read_text());d['file']=f'image/raw/{sid}.png';d['repair']=change;write(EP/'logs'/f'{sid}.json',d)
 sheet(list(fixes),'frame-fixes-v3.jpg')

def final_frame_fixes():
 fixes={
 'S30':'Change only RED-cardigan woman pose: she is TURNING AWAY to her LEFT, her RIGHT FOREARM folded UPWARD against her chest and RIGHT HAND near her collarbone. Her RIGHT ELBOW protrudes sideways at waist height, immediately NEXT TO the upright thermos upper side, about to knock it. Her HAND MUST NOT hover above or touch the thermos. Ivory-sweater woman stands behind holding phone. ONE upright thermos, grey curtains closed. Clear elbow-to-cup relationship, realistic adult arm anatomy.',
 'S41':'Keep exact room, people and fallen cup. RED-cardigan woman holds smartphone near chest. IVORY-sweater woman stands BESIDE her and points with index finger at LOWER PART OF THE PHONE in red woman hand, both looking at that phone. She must NOT point at the coffee table or cup. Grey curtains fully closed. One phone, one fallen thermos navy cap RIGHT, mountain sticker UP.',
 'S53':'Keep exact women examining router and room layout, but change time decisively to DAYTIME several days later. Window shows bright overcast DAYLIGHT and pale exterior buildings; curtains partly open. Broad cold daylight fills room and faces. Lamp is OFF. No blue-black night window. Thermos now UPRIGHT, no new person or text.'}
 for sid,text in fixes.items():
  p=gen('final-fix-'+sid,'Precise scene edit, preserve native sharp detail, faces, clothes and room. '+text,EP/'image/final'/f'{sid}.png',True,'dkl-b')
  shutil.copyfile(p,EP/'image/final'/f'{sid}.png');shutil.copyfile(p,EP/'image/raw'/f'{sid}.png')
  d=json.loads((EP/'logs'/f'final-fix-{sid}.json').read_text());d['file']=f'image/raw/{sid}.png';d['repair']=text;write(EP/'logs'/f'{sid}.json',d)
 sheet(list(fixes),'final-frame-fixes-v3.jpg')

if __name__=='__main__':
 import math
 mode=sys.argv[1]
 if mode=='preflight':plates(['living','estate'])
 elif mode=='plates':plates()
 elif mode=='text-plates':
  for name in ['corridor','car','bedroom']:
   p=gen('plate-'+name,SCENES[name],None,False,'new2');shutil.copyfile(p,EP/'image/plates'/f'{name}.png')
 elif mode=='pilot':characters(True);sheet([s['id'] for s in PLAN['shots'] if s['character_ids']][:6],'pilot-v3.jpg')
 elif mode=='characters':characters()
 elif mode=='evidence':evidence()
 elif mode=='repair-masters':repair_masters()
 elif mode=='repair-frames':repair_frames()
 elif mode=='final-frame-fixes':final_frame_fixes()
