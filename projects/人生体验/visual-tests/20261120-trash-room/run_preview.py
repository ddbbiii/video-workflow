"""Three environment-only concept previews using the workspace image API policy."""
import base64
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import time
import urllib.request

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
POLICY = json.loads((ROOT / 'shared/image-api/channel-policy.json').read_text())
ACTIVE = POLICY['policies'][POLICY['active']]
STYLE_DOC = (ROOT / 'rules/人生体验/style.md').read_text()
STYLE = re.search(r'```text\s*(Two-layer hand-drawn.*?)```', STYLE_DOC, re.S).group(1).strip()

SHOTS = [
    ('01-room-wide', 'E', 'living', '全屋外卖垃圾淹没家具，几乎没有落脚处',
     'Wide establishing view, camera outside the open doorway, eye height, 24mm. Left foreground dark doorframe, middle ground towering irregular mountains of hundreds of crumpled takeaway bags and used food tubs, right rear half-buried sagging blue-grey sofa and iron bed, far wall a visible daylight window. A tiny Chinese rental apartment severely neglected for months, once housed more than ten cats; all cats have already been removed. Trash piles 0.6 to 1.2 meters high bury the sofa seat and almost all the floor. Distinct dirty white meal containers with greasy lids, crushed clear drink cups with dark liquid and mold, leaking translucent delivery bags, cat food tins, flattened damp cardboard. There is a small compressed sleeping hollow on the otherwise buried bed. Multiple overflowing litter trays with recognizable brown cat feces spill into exposed floor patches, broad urine stains at wall bases, tangled mats of cat hair. Peeling plaster corner, folding table buried under takeaway containers. Make this genuinely shocking domestic squalor, overwhelmingly dense but objects remain legible, not decorative clutter or neatly stacked boxes. No clear walking aisle. Daylight reveals everything.'),
    ('02-litter-takeaway', 'C', 'living', '外卖漏液、猫砂结块和猫屎粘连在家具下方',
     'Close environmental evidence shot, 50mm, camera 70cm above the floor looking obliquely down under the edge of the same blue-grey sofa. A severely overflowing rectangular grey cat litter tray occupies middle left. Recognizable irregular dark brown dried cat feces, urine-caked litter clumps and scattered granular litter cover the floor around it. Right foreground ruptured translucent takeaway bags, crushed greasy food boxes with rotting leftovers, dark spilled broth trapped under plastic, tangled clumps of shed fur stuck in wet grime. One cardboard cat nest has a soaked collapsed base adhered to the floor. A few small brown cockroaches with visible antennae crawl along the wall junction, normal insect size. The sofa leg and broad floor stains convey real scale. Window edge visible upper right provides cool daylight and contact shadows. The filth must read as feces, caked litter, greasy food and hair rather than generic brown rubble. Detailed yet graphic hand-drawn treatment, disgusting lived-in domestic neglect, no gore.'),
    ('03-kitchen-roaches', 'M', 'kitchen', '堆满外卖的厨房中，蟑螂聚集在纸箱后和水槽边',
     'Medium-wide environment-only view of a tiny connected rental kitchen, 35mm, slightly elevated camera looking toward sink, stove and back window. Counter completely buried under greasy takeaway tubs, cat food tins and stained bowls. Sink packed with plates in opaque grey stagnant water, dark grease ring around rim. Lower left foreground a collapsed wet cardboard box is tilted away from the wall without any person or hands visible, revealing a dense cluster of many normal-sized brown cockroaches with clearly drawn bodies, legs and antennae along the exposed wall seam; additional insects gather under food tins and around the sink rim, not oversized fantasy insects or a uniform pattern across the whole image. Floor cluttered with tied garbage bags, spilled cat litter, recognizable scattered brown cat feces and cat hair, sticky dark trails at the cabinet base. Fridge door obstructed by garbage. Muted old sea-green tiles, dull metal faucet, peeling cabinet edges, one desaturated red takeout bag. Rear window visible, sufficient cool daylight to see all filth clearly. Shocking long-term sanitation neglect, coherent real apartment proportions. No people, no cats, no gore.')
]

def main():
    (OUT / 'image').mkdir(parents=True, exist_ok=True)
    color = {'plan_version':1,'episode':'清理垃圾屋环境强度小样','chapters':{'入屋':{
        'plate':['#E1E4DE','#99AAA7','#655B50','#7D929C','#292D2E'],
        'accent':'one muted brick-red takeaway bag, no other saturated patches',
        'day_in':'Overcast morning, visible window at rear right, 6000K cool-neutral daylight, readable midtones; dirt is local, no overall brown or green filter',
        'day_out':'N/A','night_in':'N/A','night_out':'N/A'}},
        'locations':{'living':['blue-grey sofa','iron bed','buried folding table','peeling plaster corner','rear window'], 'kitchen':['sea-green wall tiles','blocked fridge','back window','overfilled sink']}}
    (OUT/'image/color-plan.json').write_text(json.dumps(color,ensure_ascii=False,indent=2))
    (OUT/'README.md').write_text('# 清理垃圾屋环境强度小样\n\n用户要求先看几张图，本次只做三张无人环境概念图；不代表剧本锁定，不启动正式静帧批量。猫已带走，只保留生活痕迹。按人生体验现行画风，供判断垃圾密度、污物辨识度与冲击力。\n\n提示词、通道与结果见同名 JSON；色彩计划见 image/color-plan.json。未执行完整影片或人物门禁。指定 audit_color_v3.py 当前未找到，不声称完成色彩审计。\n')
    def generate_one(shot, channel):
        name, kind, scene, fact, visual = shot
        if (OUT/(name+'.png')).exists():
            return json.loads((OUT/(name+'.json')).read_text())
        cfg=POLICY['channels'][channel]
        palette=color['chapters']['入屋']
        prompt=STYLE+'\n\n'+visual+'\n\nColors and lighting: '+palette['day_in']+'. Palette: '+', '.join(palette['plate'])+'. Accent: '+palette['accent']+'. Allow a secondary environmental hue; keep subtle neutral, blue-grey and sea-green differences. No people, human body parts, anthropomorphic characters, living cats, dead animals, text, logos, borders, split panels, photographic rendering, 3D rendering, paper grain or cinematic darkness. Keep key evidence above bottom fifth; bottom fifth may contain nonessential continuing clutter.'
        meta={'name':name,'prompt':prompt,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'shot_type':kind,'scene_id':scene,'has_character':False,'cast':'none','closeup_part':'none','view_angle':'N/A','fact':fact,'cue':'','visual':visual,'references':[], 'stage':'environment-only concept','channel':channel,'model':cfg['model'],'endpoint':cfg['base_url']+'/images/generations','policy':POLICY['active'],'queue':channel,'qa':'pending visual review'}
        side=OUT/(name+'.json')
        side.write_text(json.dumps(meta,ensure_ascii=False,indent=2))
        key=os.environ[cfg['key_env']]
        body=json.dumps({'model':cfg['model'],'prompt':prompt,'size':cfg['size'],'n':1}).encode()
        req=urllib.request.Request(meta['endpoint'],data=body,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','User-Agent':'OpenAI/Python 1.60.0'})
        start=time.time()
        try:
            for attempt in range(ACTIVE['retry']['same_channel_max']+1):
                try:
                    with urllib.request.urlopen(req,timeout=240) as response:
                        data=json.load(response)
                        meta['request_id']=response.headers.get('x-request-id')
                    meta['attempts']=attempt+1
                    break
                except Exception:
                    if attempt>=ACTIVE['retry']['same_channel_max']:raise
                    time.sleep(2)
            item=data['data'][0]
            if item.get('b64_json'): raw=base64.b64decode(item['b64_json'])
            else:
                with urllib.request.urlopen(urllib.request.Request(item['url'],headers={'User-Agent':'OpenAI/Python 1.60.0'}),timeout=120) as response:raw=response.read()
            if raw[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('Expected PNG output')
            dims=struct.unpack('>II',raw[16:24])
            (OUT/(name+'.png')).write_bytes(raw)
            meta.update(status='completed',dimensions=dims,elapsed_s=round(time.time()-start,1),qa='technical PNG decode header checked; visual review pending')
        except Exception as exc:
            meta.update(status='failed',error_type=type(exc).__name__,elapsed_s=round(time.time()-start,1))
        side.write_text(json.dumps(meta,ensure_ascii=False,indent=2))
        print(json.dumps({k:meta.get(k) for k in ['name','status','dimensions','elapsed_s','error_type']},ensure_ascii=False),flush=True)
        return meta
    def queue(channel, shots):
        results=[]
        for s in shots:
            result=generate_one(s,channel)
            if result.get('status')=='failed':
                other=next(c for c in ACTIVE['parallel_channels'] if c!=channel)
                result=generate_one(s,other)
                result['fallback_from']=channel
                (OUT/(s[0]+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
            results.append(result)
        return results
    channels=ACTIVE['parallel_channels']
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(channels)) as pool:
        futures=[pool.submit(queue,c,SHOTS[i::len(channels)]) for i,c in enumerate(channels)]
        for f in futures:f.result()

if __name__=='__main__': main()
