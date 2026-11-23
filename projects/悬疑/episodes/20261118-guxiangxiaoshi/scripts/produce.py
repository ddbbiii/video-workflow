"""Episode-local image production; credentials remain environment-only."""
from pathlib import Path
import importlib.util,json,sys,hashlib,threading,time,shutil
from concurrent.futures import ThreadPoolExecutor,as_completed
from PIL import Image,ImageOps,ImageEnhance,ImageDraw

EP=Path(__file__).resolve().parents[1]
ROOT=EP.parents[3]
spec=importlib.util.spec_from_file_location('image_api',ROOT/'projects/悬疑/visual-tests/20261114-pilot-8shots/gen_pilot.py')
api=importlib.util.module_from_spec(spec);sys.modules[spec.name]=api;spec.loader.exec_module(api)
api.HERE=EP;api.RAW=EP/'image/raw';api.CROPS=EP/'image/crops';api.RULES=ROOT/'rules/悬疑/visual.md'
for d in [api.RAW,api.CROPS,EP/'image/anchors',EP/'image/references',EP/'image/final',EP/'image/backgrounds']:
 d.mkdir(parents=True,exist_ok=True)
policy=json.loads((ROOT/'shared/image-api/channel-policy.json').read_text())
route=policy['policies'][policy['active']]
channels=[dict(policy['channels'][k],name=k,policy=policy['active']) for k in route['parallel_channels']]
locks={c['name']:threading.Lock() for c in channels}
mutex=threading.Lock()
UNAVAILABLE=set()
POS,NEG,CEL=[api.read_block(k) for k in ['STYLE_POS','STYLE_NEG','CEL_BOOST']]
MANIFEST=EP/'image/manifest.json'

def call_record(tag,info,channel,attempt):
 info.update(model=channel['model'],base_url=channel['base_url'],request_id=info.get('request_id','not-returned-by-relay'))
 target=EP/'logs'/f"{tag}-{channel['name']}-a{attempt}-meta.json"
 target.write_text(json.dumps(info,ensure_ascii=False,indent=2))

def save_record(tag,info):
 with mutex:
  m=json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
  m[tag]=info
  MANIFEST.write_text(json.dumps(m,ensure_ascii=False,indent=2))

def generate(tag,prompt,reference=None,index=0):
 m=json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
 if tag in m and m[tag].get('ok') and (EP/m[tag]['file']).exists():return EP/m[tag]['file']
 records=[]
 for offset in range(2):
  channel=channels[(index+offset)%2]
  if channel['name'] in UNAVAILABLE: continue
  for attempt in range(1,3):
   safe_tag=f'{tag}-{channel["name"]}'
   with locks[channel['name']]:
    info=api.call(channel,prompt,{'tag':safe_tag},reference,attempt)
   records.append({k:info.get(k) for k in ['channel','ok','http_status','elapsed_s','error','dims']})
   if info.get('ok'):
    f=EP/info['file'];info['metrics']=api.measure(f);info['qa']=api.gate(info,channel)
    info['ok']=not info['qa']
    if info['ok']:
     info.update(attempts=records,reference=str(reference.relative_to(EP)) if reference else None,
                 fallback_from=channels[index%2]['name'] if offset else None,policy=policy['active'])
     call_record(tag,info,channel,attempt)
     save_record(tag,info)
     print(tag,'OK',channel['name'],info['dims'],info['elapsed_s'],flush=True)
     return f
   call_record(tag,info,channel,attempt)
   print(tag,'attempt failed',channel['name'],info.get('http_status'),str(info.get('qa',info.get('error')))[:240],flush=True)
   if info.get('http_status') in (401,403):break
 save_record(tag,{'ok':False,'attempts':records})
 raise RuntimeError(f'{tag}: available channel attempts exhausted; see manifest')

CHARACTERS={
 'protagonist':'one Chinese man aged 30, lean average adult build, short black side-parted hair, narrow dark eyes, straight brows, muted olive overshirt jacket, light grey crew-neck shirt, dark charcoal trousers, worn black shoes, no jewelry, no glasses',
 'mother':'one Chinese woman aged 58, short dark hair with grey at temples, narrow dark eyes, muted maroon cardigan over grey blouse, dark navy trousers, ordinary cloth shoes, no jewelry',
 'chen':'one Chinese man aged 32, average stocky build, short slightly spiky black hair, rounder face, muted tan zip jacket over dark blue shirt, black trousers, no glasses, no jewelry',
}

def anchor(name,index):
 p=f'{POS}, {CEL}, character design reference of {CHARACTERS[name]}. '
 if name=='protagonist':
  p+='Exactly four separate reference views in a 2x2 sheet: top left front full body standing, top right ninety degree side full body, bottom left back full body, bottom right front face. Same design and outfit across all four. '
 else:p+='Single full-body three-quarter front standing reference, one person only. '
 p+='Plain grey background, flat unshaded color areas, each surface at most three flat colors, hard shadow boundaries, no gradients. No labels, no text. Avoid: '+NEG
 f=generate('anchor-'+name,p,index=index)
 dest=EP/'image/anchors'/f'{name}.png';shutil.copyfile(f,dest)
 if name=='protagonist':
  im=Image.open(f);w,h=im.size
  for v,box in {'front':(4,4,w//2-4,h//2-4),'side':(w//2+4,4,w-4,h//2-4),'back':(4,h//2+4,w//2-4,h-4),'face':(w//2+4,h//2+4,w-4,h-4)}.items():im.crop(box).save(EP/'image/anchors'/f'protagonist-{v}.png')
 return dest

def sheet(paths,out,cols=3):
 cw,ch=520,294
 canvas=Image.new('RGB',(cols*cw,((len(paths)+cols-1)//cols)*(ch+28)),(24,27,32));d=ImageDraw.Draw(canvas)
 for i,p in enumerate(paths):
  im=ImageOps.fit(Image.open(p).convert('RGB'),(cw,ch));x=i%cols*cw;y=i//cols*(ch+28)
  canvas.paste(im,(x,y+28));d.text((x+4,y+6),Path(p).stem,fill=(240,240,240))
 canvas.save(out)

if __name__=='__main__':
 if sys.argv[1]=='anchors':
  # The first anchor is also the required real balance/availability probe.
  anchor('protagonist',0)
  with ThreadPoolExecutor(max_workers=2) as pool:
   list(pool.map(lambda t:anchor(*t),[('mother',1),('chen',0)]))
  sheet([EP/'image/anchors'/f'{n}.png' for n in CHARACTERS],EP/'qa/anchors.jpg')
