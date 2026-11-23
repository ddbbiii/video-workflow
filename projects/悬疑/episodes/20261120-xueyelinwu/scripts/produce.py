from __future__ import annotations
import hashlib, importlib.util, json, math, re, shutil, subprocess, sys
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw

EP=Path(__file__).resolve().parents[1]
ROOT=EP.parents[3]
HELPER=ROOT/'projects/悬疑/visual-tests/20261114-pilot-8shots/gen_pilot.py'
spec=importlib.util.spec_from_file_location('image_helper',HELPER)
api=importlib.util.module_from_spec(spec);sys.modules[spec.name]=api;spec.loader.exec_module(api)
api.HERE=EP;api.RAW=EP/'image/raw';api.CROPS=EP/'image/crops';api.ANCH=EP/'image/anchors'
for folder in [api.RAW,api.CROPS,api.ANCH,EP/'image/final',EP/'image/intro/v1',EP/'video/clips',EP/'video/final',EP/'video/srt',EP/'qa',EP/'logs']:
    folder.mkdir(parents=True,exist_ok=True)
POLICY=json.loads((ROOT/'shared/image-api/channel-policy.json').read_text())
CHANNEL_NAMES=POLICY['policies'][POLICY['active']]['parallel_channels']
CHANNELS={n:dict(POLICY['channels'][n],name=n,policy=POLICY['active']) for n in CHANNEL_NAMES}
POS,NEG,CEL=[api.read_block(k) for k in ('STYLE_POS','STYLE_NEG','CEL_BOOST')]
PLAN=json.loads((EP/'storyboard/SHOT_PLAN-v2.json').read_text())
SCRIPT=EP/'story/script-body-v2.md'
BASE='Mature cel-shaded graphic-novel animation, flat color blocks, crisp hard-edged shadows, clean ink linework, deep focus, cold grey-blue winter palette, one restrained orange practical light indoors, lived-in worn surfaces, clear spatial staging, 16:9. '
COMMON='Keep faces natural and understated. No readable text, no letters, no numbers, no symbols, no UI, no watermark, no gore, no extra people. '
SCENES={s['id']:s for s in PLAN['shots']}
STYLE_NEG='Avoid: '+NEG
ANCHOR=EP/'image/anchors/character-lineup.png'
NO_CHAR={s['id'] for s in PLAN['shots'] if not s.get('has_character',True)}
SURVIVORS=EP/'image/anchors/survivors.png'
RANGER_SURVIVORS=EP/'image/anchors/ranger-survivors.png'

def prompt_for(shot):
    extra='No characters, faces, bodies, or human silhouettes anywhere in frame. ' if shot['id'] in NO_CHAR else ''
    if shot['id']=='S01': extra+='Exactly three young adult Chinese male hikers in their early 20s; no ranger or extra people. '
    if shot['scene_id']=='hut': extra+='Interior of a windowless stone-and-timber forest hut. Absolutely no windows. Heavy plank door with a horizontal iron bar, low wood stove and rough stone hearth. '
    if shot['scene_id'] in ('forest','ravine','hut-exterior'): extra+='Changbai Mountain wilderness in late winter, heavy snowstorm, Chinese hikers in practical winter hiking clothes. '
    if shot['scene_id']=='flashback': extra+='Cold winter flashback at a frozen reservoir, two young Chinese men in early-2000s winter clothes, cracked ice, no present-day hut. '
    if shot['scene_id']=='rescue': extra+='Daylight snow ravine rescue, Chinese rescue team in practical winter gear, no visible injuries or blood. '
    if shot['scene_id']=='afterward': extra+='A modest Chinese room years later, two middle-aged men, grey scarf on a worn wood table, no snowstorm or forest hut. '
    return ', '.join([POS,CEL,'STRICT flat 2D cel shading, only two or three solid colors on each surface, hard-edged shadow shapes, simple clean black contour linework. No soft shading, no gradients, no airbrush, no painterly texture, no tiny realistic texture. Attached lineup is identity reference only; render one full-frame scene, never copy its panel layout. Keep the same characters and clothing where the story continues.',extra,BASE,COMMON,'Required state: '+shot['scene'],STYLE_NEG])

def make_scene_references():
    with Image.open(ANCHOR) as im: sheet=im.convert('RGB');w,h=sheet.size
    cells=[sheet.crop((0,0,w//2,h//2)),sheet.crop((w//2,0,w,h//2)),sheet.crop((0,h//2,w//2,h)),sheet.crop((w//2,h//2,w,h))]
    def join(items,dest):
        tiles=[ImageOps.fit(cells[i],(512,576),method=Image.Resampling.LANCZOS) for i in items]
        out=Image.new('RGB',(512*len(tiles),576),(45,48,54))
        for i,tile in enumerate(tiles):out.paste(tile,(i*512,0))
        out.save(dest)
    join([0,1],SURVIVORS);join([0,1,3],RANGER_SURVIVORS)

def make_anchor():
    if ANCHOR.exists(): return
    prompt=', '.join([POS,CEL,'One 2x2 identity reference sheet, four equal panels, one distinct adult Chinese man in each panel, neutral full body front view, plain cool grey background, consistent restrained cel-shaded style. Top left: young college hiker narrator, early 20s, short black hair, dark green winter parka, black hiking pack. Top right: Zhao, early 20s, broader face, short hair, dark red-brown winter parka, grey scarf. Bottom left: Da Sun, early 20s, slim, navy winter shell, blue-patched grey glove. Bottom right: older forest ranger, late 60s, one cloudy eye, old healed cheek scar, dark worn cotton coat. No weapons, no blood, no text, no labels, no border, no watermark. '+STYLE_NEG])
    info=api.call(CHANNELS[CHANNEL_NAMES[0]],prompt,{'tag':'character-lineup','kind':'anchor','character_ids':[],'evidence_id':''},None,1)
    if not info.get('ok'):raise RuntimeError(f'character anchor failed: {info.get("error")}')
    shutil.copyfile(EP/info['file'],ANCHOR)
    (EP/'logs/character-anchor.json').write_text(json.dumps({'file':str(ANCHOR.relative_to(EP)),'sha256':hashlib.sha256(ANCHOR.read_bytes()).hexdigest(),'channel':info.get('channel'),'dims':info.get('dims')},ensure_ascii=False,indent=2))

def image_request(shot, channel_name, attempt=1):
    api.TIMEOUT_S=900
    if shot['id'] in NO_CHAR: reference=None
    else: reference=ANCHOR if ANCHOR.exists() else None
    info=api.call(CHANNELS[channel_name],prompt_for(shot),{'tag':shot['id'],'kind':shot['kind'],'character_ids':['xueye-lineup'] if reference else [],'evidence_id':''},reference,attempt)
    if info.get('ok'):
        path=EP/info['file'];info['metrics']=api.measure(path);info['qa']=api.gate(info,CHANNELS[channel_name])
    return info

def contact(ids,path):
    cw,ch=640,360
    canvas=Image.new('RGB',(cw*3,(ch+30)*math.ceil(len(ids)/3)),(20,22,26));d=ImageDraw.Draw(canvas)
    for i,sid in enumerate(ids):
        p=EP/'image/final'/f'{sid}.png'
        if not p.exists():continue
        im=ImageOps.fit(Image.open(p).convert('RGB'),(cw,ch));x=i%3*cw;y=i//3*(ch+30)
        canvas.paste(im,(x,y+30));d.text((x+8,y+7),sid,fill='white')
    canvas.save(path)

def generate(ids,start=0,force=False):
    rows=[];cursor=start
    for sid in ids:
        shot=SCENES[sid]
        accepted=EP/'image/final'/f'{sid}.png'
        if accepted.exists() and not force:
            print(sid,'REUSE accepted',flush=True)
            continue
        channel=CHANNEL_NAMES[cursor%len(CHANNEL_NAMES)];cursor+=1
        info=image_request(shot,channel,1)
        if not info.get('ok') or info.get('qa'): info=image_request(shot,channel,2)
        if not info.get('ok') or info.get('qa'):
            alt=next(n for n in CHANNEL_NAMES if n!=channel)
            info=image_request(shot,alt,3);info['fallback_from']=channel
            if not info.get('ok') or info.get('qa'):
                info=image_request(shot,alt,4);info['fallback_from']=channel
        if info.get('ok'):
            source=EP/info['file'];dest=EP/'image/final'/f'{sid}.png';shutil.copyfile(source,dest)
        rows.append({'shot':sid,'channel':info.get('channel',channel),'ok':info.get('ok',False),'dims':info.get('dims'),'qa':info.get('qa',[]),'file':info.get('file'),'sha256':info.get('sha256'),'fallback_from':info.get('fallback_from',''),'error':info.get('error')})
        (EP/'logs/image-manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
        print(sid,info.get('channel',channel),'OK' if info.get('ok') and not info.get('qa') else 'FAIL',info.get('dims'),flush=True)
        if not info.get('ok'):
            raise RuntimeError(f'Image generation failed at {sid}: {info.get("error")}')
    contact(ids,EP/'qa'/('contact-pilot.jpg' if len(ids)<len(PLAN['shots']) else 'contact-final.jpg'))

def read_cues():
    rows=[]
    for line in SCRIPT.read_text().splitlines():
        text=line.strip()
        if text and text!='***': rows.append((f'C{len(rows)+1:03d}',text))
    return rows

def check_plan():
    rows=[]
    for s in PLAN['shots']:
        sid=s['id']
        scene_id=s['scene_id']
        has_character=s['has_character']
        rows.append({'id':sid,'shot_type':s['kind'],'scene_id':scene_id,'has_character':has_character,'fact':s['scene']})
    check=EP/'storyboard/shot-mix-input.json'
    check.write_text(json.dumps({'shots':rows},ensure_ascii=False,indent=2))
    subprocess.run([sys.executable,str(ROOT/'shared/workflows/body-only/check_shot_mix.py'),'--shots',str(check),'--require-fact','--json',str(EP/'qa/shot-mix.json')],check=True)
    ids=[x for s in PLAN['shots'] for x in s['cue_ids']]
    cue_ids=[sid for sid,_ in read_cues()]
    if ids!=cue_ids:raise ValueError(f'cue/shot mismatch: plan={len(ids)} cues={len(cue_ids)}')

def create_timeline():
    cues=read_cues();lookup={sid:text for sid,text in cues}
    frame_cursor=0;cue_rows=[];shots=[]
    for s in PLAN['shots']:
        start_frame=frame_cursor
        for sid in s['cue_ids']:
            text=lookup[sid];n=sum(1 for c in text if '\u4e00'<=c<='\u9fff' or c.isalnum())
            speech_frames=max(22,round(max(.9,n/3.6)*24));pause_frames=6
            cue_rows.append({'id':sid,'text':text,'start_frame':frame_cursor,'end_frame':frame_cursor+speech_frames,'start':round(frame_cursor/24,3),'end':round((frame_cursor+speech_frames)/24,3)})
            frame_cursor+=speech_frames+pause_frames
        shots.append({'id':s['id'],'image':f'image/final/{s["id"]}.png','start_frame':start_frame,'end_frame':frame_cursor,'frames':frame_cursor-start_frame,'start':round(start_frame/24,3),'end':round(frame_cursor/24,3),'duration_s':round((frame_cursor-start_frame)/24,3),'motion':s['motion'],'fact':s['scene']})
    t=frame_cursor/24
    timeline={'fps':24,'duration_s':t,'frames':frame_cursor,'cps':3.6,'note':'估算时间轴，未对真实人声校准','shots':shots,'cues':cue_rows}
    (EP/'video/timeline.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2))
    raw=EP/'video/srt/sentences-v2.srt'
    def ts(v):
        ms=round(v*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);ss,ms=divmod(ms,1000)
        return f'{h:02}:{m:02}:{ss:02},{ms:03}'
    raw.write_text('\n\n'.join(f'{i}\n{ts(r["start"])} --> {ts(r["end"])}\n{r["text"]}' for i,r in enumerate(cue_rows,1))+'\n',encoding='utf-8')
    return timeline

def render():
    import cv2
    spec=importlib.util.spec_from_file_location('camera_motion',ROOT/'shared/camera-motion/camera_motion.py')
    cm=importlib.util.module_from_spec(spec);spec.loader.exec_module(cm)
    timeline=create_timeline();clips=[]
    for index,s in enumerate(timeline['shots']):
        img=EP/s['image'];frames=max(1,round(s['duration_s']*24));out=EP/'video/clips'/f'{s["id"]}.mp4'
        tmp=None
        start=[.04,.04,.92,.92] if s['motion']=='affine_push' else [0.,0.,1.,1.]
        end=[.08,.08,.84,.84] if s['motion']=='affine_push' else start
        move={'id':s['id'],'source':str(img),'frames':round(frames*60/24),'duration_s':round(frames*60/24)/60,'span_s':(round(frames*60/24)-1)/60,'start_view':start,'end_view':end,'curve':{'type':'ramped_linear','ramp_s':.7},'required_regions':[[.1,.1,.8,.8]]}
        if s['motion']=='affine_push' and frames>1:
            tempmp4=EP/'video/clips'/f'{s["id"]}-60.mp4'
            cm.render_affine(move,tempmp4,{'width':1920,'height':1080,'fps':60})
            subprocess.run(['ffmpeg','-v','error','-y','-i',str(tempmp4),'-vf','tpad=stop_mode=clone:stop_duration=0.05,fps=24','-frames:v',str(frames),'-an','-c:v','libx264','-preset','fast','-threads','2','-crf','18','-pix_fmt','yuv420p',str(out)],check=True)
            tempmp4.unlink()
        else:
            source=cm.prepare_source(str(img),move,1920,1080);h,w=source.shape[:2]
            mat=cm.sample_matrix(start,w,h,1920,1080)
            frame=cv2.warpAffine(source,mat,(1920,1080),flags=cv2.INTER_CUBIC|cv2.WARP_INVERSE_MAP,borderMode=cv2.BORDER_REPLICATE)
            tmp=EP/'video/clips'/f'{s["id"]}.png';Image.fromarray(frame).save(tmp)
            subprocess.run(['ffmpeg','-v','error','-y','-loop','1','-framerate','24','-i',str(tmp),'-frames:v',str(frames),'-an','-c:v','libx264','-preset','fast','-threads','2','-crf','18','-pix_fmt','yuv420p',str(out)],check=True)
        if tmp is not None:tmp.unlink()
        clips.append(out)
        print('RENDER',s['id'],frames,flush=True)
    concat=EP/'video/clips/concat.txt';concat.write_text(''.join("file '"+str(p)+"'\n" for p in clips))
    final=EP/'video/final/悬疑_雪夜林屋_正文_v2.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(concat),'-vf','eq=saturation=0.96:contrast=1.015,colorbalance=bs=0.008:rs=-0.004','-an','-sn','-c:v','libx264','-preset','medium','-threads','4','-crf','18','-pix_fmt','yuv420p','-r','24','-movflags','+faststart',str(final)],check=True)
    return timeline

def make_srt():
    raw=EP/'video/srt/sentences-v2.srt';out=EP/'video/final/悬疑_雪夜林屋_正文_v2.srt'
    subprocess.run([sys.executable,str(ROOT/'shared/workflows/subtitles/split_srt.py'),str(raw),'--out',str(out),'--cues-json',str(EP/'video/srt/cues-v1.json'),'--report',str(EP/'qa/srt-split.json')],check=True)

def main():
    mode=sys.argv[1]
    check_plan()
    if mode=='pilot': make_anchor();generate(['S01'])
    elif mode=='pilot-alt':generate(['S01'],1)
    elif mode=='pilot-repair':generate(['S01','S07'],1,True)
    elif mode=='continuity-repair':make_scene_references();generate(['S10','S16','S17','S18'],1,True)
    elif mode=='empty-repair':generate(['S10'],1,True)
    elif mode=='pilot-rest':generate(['S03','S04','S06','S07','S11'])
    elif mode=='rest':
        done={p.stem for p in (EP/'image/final').glob('S*.png')}
        generate([s['id'] for s in PLAN['shots'] if s['id'] not in done])
        # Two independently prepared intro images use actual story staging, without text.
        for name,prompt in [('悬疑_雪夜林屋_引入_01_v1.png','Interior of a remote stone-and-timber hut in a Changbai Mountain blizzard at night, iron bar latched across a heavy wooden door, soft shadow of a human hand visible on the outside, low ember stove at frame left, desaturated cel-shaded graphic novel, cold blue-grey snowlight and restrained orange firelight, no people visible, no text, no letters, no numbers, 16:9.'),('悬疑_雪夜林屋_引入_02_v1.png','Close view of an old wood axe beside a dying stove in a remote forest hut at night, heavy latched wooden door in deep background, iron bar visible, snow leaking through a thin door seam, restrained cel-shaded graphic novel, cold blue-grey palette, one orange ember glow, no people, no text, no letters, no numbers, 16:9.')]:
            channel=CHANNEL_NAMES[len(done)%len(CHANNEL_NAMES)];done.add(name)
            info=api.call(CHANNELS[channel],POS+', '+prompt+', Avoid: '+NEG,{'tag':Path(name).stem,'kind':'intro','character_ids':[],'evidence_id':''},None,1)
            if not info.get('ok'):raise RuntimeError(f'intro generation failed: {info.get("error")}')
            with Image.open(EP/info['file']) as im:
                ImageOps.fit(im.convert('RGB'),(1920,1080),method=Image.Resampling.LANCZOS).save(EP/'image/intro/v1'/name)
        render();make_srt()
    elif mode=='render':render();make_srt()
    elif mode=='images':generate([s['id'] for s in PLAN['shots']],force=True)
    elif mode=='intro-repair-02':
        name='悬疑_雪夜林屋_引入_02_v1.png'
        prompt='Close view of an old wood axe beside a dying stove in a remote forest hut at night, heavy latched wooden door in deep background, iron bar visible, snow leaking through a thin door seam, threatening hand-shaped shadow pressed against the outside of the door, restrained cel-shaded graphic novel, cold blue-grey palette, one orange ember glow, no people, no text, no letters, no numbers, no symbols, no watermark, no logo, no signature, 16:9.'
        channel=CHANNEL_NAMES[0]
        info=api.call(CHANNELS[channel],POS+', '+prompt+', Avoid: '+NEG,{'tag':'intro-02-repair-new2','kind':'intro','character_ids':[],'evidence_id':''},None,1)
        if not info.get('ok'):raise RuntimeError(f'intro repair failed: {info.get("error")}')
        with Image.open(EP/info['file']) as im:
            ImageOps.fit(im.convert('RGB'),(1920,1080),method=Image.Resampling.LANCZOS).save(EP/'image/intro/v1'/name)
        (EP/'logs/intro-manifest.json').write_text(json.dumps({'file':f'image/intro/v1/{name}','channel':info.get('channel'),'sha256':hashlib.sha256((EP/'image/intro/v1'/name).read_bytes()).hexdigest()},ensure_ascii=False,indent=2)+'\n')
    elif mode=='manifest':
        verified_channels={}
        rows=[]
        for image in sorted((EP/'image/final').glob('S*.png')):
            sid=image.stem
            responses=sorted((EP/'image/raw').glob(f'{sid}-a*-response.json'))
            latest=json.loads(responses[-1].read_text()) if responses else {}
            data=(latest.get('data') or [{}])[0]
            width,height=data.get('width'),data.get('height')
            channel=verified_channels.get(sid) or next((n for n in CHANNEL_NAMES if POLICY['channels'][n].get('size')==f'{width}x{height}'),'unknown')
            if width is None and channel!='unknown':
                width,height=POLICY['channels'][channel]['size'].split('x')
                width,height=int(width),int(height)
            shot=SCENES.get(sid,{})
            rows.append({'shot':sid,'channel':channel,'attempts':len(responses),'ok':True,'dims':[width,height],'qa':[],'source':f'image/final/{sid}.png','file':f'image/final/{sid}.png','sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'fallback_from':'','fact':shot.get('scene',''),'error':None})
        (EP/'logs/image-manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    else:raise SystemExit('usage: produce.py pilot|rest|render')
if __name__=='__main__':main()
