# G1 plot-segment grid test: EXACTLY ONE API call, no retry. Method reused from /tmp/generate_character_grids.py
import base64, json, os, sys, time, urllib.error, urllib.request, uuid
from pathlib import Path
BASE='https://dklapi.com/v1/images/edits'; MODEL='gpt-image-2.5-sunburst'; SIZE='1024x1536'
OUT=Path('E:/program/1project/video/projects/猎奇/episodes/tudou/image/plot_grids_v2'); OUT.mkdir(parents=True, exist_ok=True)
REFS=['E:/program/1project/video/assets/猎奇/characters/tudou-threeview/step3-cast/tomato_heiress_1.png',
      'E:/program/1project/video/assets/猎奇/characters/tudou-threeview/step1b/tudou_ugly_C2.png',
      'E:/program/1project/video/assets/猎奇/characters/tudou-threeview/step3-cast/tomato_dad_2.png']
PROMPT = '''Create exactly ONE composite image: a clean 3x3 grid of nine separate vertical 9:16 live-action film-still panels, separated by thin uniform pure-white gutters. Read panels left to right, top to bottom. This is one continuous story scene (an engagement banquet where the bride breaks off the engagement), so the same three characters, costumes, props, set and lighting stay consistent across all panels.

Reference images (character turnaround sheets; each sheet shows ONE character from front, side and back - draw that character only ONCE per panel, never as three copies):
- Image 1 = THE TOMATO HEIRESS: head is a glossy ripe red tomato with a green calyx on top, uncanny human face with heavy makeup, arched brows, false lashes, bright red lips, pearl drop earrings; skinny body in a fitted hot-pink satin mini dress with a ruffled collar, hot-pink high heels.
- Image 2 = THE POOR POTATO YOUTH: head is a real dirty lumpy raw potato with caked mud, pits, dark blemishes and pale sprouting shoots, uncanny hyper-realistic human face (wet human eyes, thick brows, crooked yellowish teeth); skinny real human body with veiny dirty hands, ragged patched burlap vest, rolled-up patched grey trousers, straw sandals, mud splatters.
- Image 3 = THE TOMATO DAD: head is an overripe wrinkled slightly cracked big tomato with a curly green stem, uneven droopy mustache and a snobbish sideways glare; potbellied body in a glossy burgundy suit, dark shirt, oversized gold chain, red pocket square, black loafers.
Match each character's face, head shape, skin texture and outfit to its reference sheet exactly. Do not swap features between the two tomato characters.

Setting for every panel: a tacky over-the-top Chinese engagement banquet hall in red and gold: crystal chandeliers, round tables with red tablecloths and gold chair covers, a red carpet aisle, a stage with a plain red-and-gold floral backdrop with NO symbols or characters on it, a tiered cake topped with cherry tomatoes; background guests only as soft out-of-focus silhouettes.

Panels:
(1) Over-the-shoulder low angle from behind the poor potato's muddy sprouting head (out of focus in the lower foreground): the tomato heiress stands on the red carpet, jabbing a finger down at him, sneering with one eyebrow raised.
(2) Close-up of the poor potato youth, aggrieved puppy-dog face with wet watery eyes and trembling lips, clutching the hem of his burlap vest with dirty hands, crumbs of mud falling from his head.
(3) Medium shot of the tomato heiress in front of the red-and-gold stage, chin raised high in profile, flicking the green calyx on top of her head like hair, one hand pressed proudly to her chest.
(4) Low-angle medium shot of the tomato dad stepping forward in front of his daughter (the tomato heiress soft and out of focus behind him), belly thrust out, gold chain glinting, polishing his shiny wrinkled tomato head with a red handkerchief, looking down his nose.
(5) Medium close-up of the poor potato youth on the red carpet, earnestly counting on his muddy fingers, forcing a hopeful crooked yellow-toothed smile, sprouts on his head quivering.
(6) Medium two-shot on the red carpet, both characters fully visible: the tomato dad pinches his nose in disgust and kicks two plain white woven fertilizer sacks (no print) back toward the poor potato youth, dark soil spilling onto the red carpet; the potato flinches.
(7) Alternate take of panel 1 from a slightly different angle: the tomato heiress looming over the poor potato youth (back of his muddy head and shoulder in the foreground), pointing down at him and sneering.
(8) Alternate take of panel 6, wider two-shot: the tomato dad mid-kick sending the plain white fertilizer sacks sliding at the poor potato youth's straw sandals, the potato recoiling, soil scattering on the red carpet.
(9) Alternate take of panel 4: closer low-angle shot of the pompous tomato dad rubbing his tomato head shiny with the red handkerchief and pointing downward.

Style: Photoreal live-action film still. Real vegetable heads with macro skin texture and uncanny hyper-realistic human faces on skinny realistic human bodies with real hands; creepy macro realism, ugly-funny, absurd comedy. Cinematic lighting, shallow depth of field.
Strictly: NO text, no letters, no numbers, no Chinese characters, no 囍 symbol anywhere (not on the backdrop, cake, sacks or walls), no subtitles, no captions, no panel numbers, no labels, no logos, no brand marks, no watermark. No blood, no gore, no wounds. No cartoon, anime, plush or clay look; no extra limbs or fingers; no extra main characters beyond those described in each panel.'''

def multipart():
    b='----kepu'+uuid.uuid4().hex; parts=[]
    def field(k,v): parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    field('model',MODEL); field('prompt',PROMPT); field('size',SIZE); field('n','1')
    for ref in REFS:
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="image[]"; filename="{Path(ref).name}"\r\nContent-Type: image/png\r\n\r\n'.encode())
        parts.append(Path(ref).read_bytes()); parts.append(b'\r\n')
    parts.append(f'--{b}--\r\n'.encode())
    return b''.join(parts), f'multipart/form-data; boundary={b}'

def main():
    key=os.environ.get('IMAGE_RELAY_KEY_1K')
    if not key: print(json.dumps({'kind':'config','error':'IMAGE_RELAY_KEY_1K missing'})); sys.exit(1)
    body,ctype=multipart()
    req=urllib.request.Request(BASE,data=body,method='POST',headers={'Authorization':'Bearer '+key,'Content-Type':ctype,'Accept':'application/json'})
    t0=time.time(); started=time.strftime('%Y-%m-%d %H:%M:%S %z')
    res={'started':started,'model_requested':MODEL,'size_requested':SIZE,'endpoint':BASE,'refs':REFS,'n_calls':1}
    try:
        with urllib.request.urlopen(req,timeout=600) as r: status=r.status; raw=r.read()
    except urllib.error.HTTPError as e: status=e.code; raw=e.read()
    except Exception as e:
        res.update(kind='network',error=f'{type(e).__name__}: {e}',elapsed=round(time.time()-t0,1))
        (OUT/'G1_api_result.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)); print(json.dumps(res,ensure_ascii=False)); sys.exit(1)
    text=raw.decode('utf-8','replace')
    try: data=json.loads(text)
    except Exception: data=None
    res.update(status=status,elapsed=round(time.time()-t0,1))
    if not (200<=status<300 and isinstance(data,dict) and isinstance(data.get('data'),list) and data['data']):
        res.update(kind='http',body=text[:4000])
        (OUT/'G1_api_result.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)); print(json.dumps(res,ensure_ascii=False)); sys.exit(1)
    item=data['data'][0]
    try:
        if item.get('b64_json'): img=base64.b64decode(item['b64_json'])
        elif item.get('url'):
            with urllib.request.urlopen(urllib.request.Request(item['url'],headers={'Accept':'image/*'}),timeout=600) as r: img=r.read()
        else: raise RuntimeError('no url or b64_json')
    except Exception as e:
        res.update(kind='download',error=f'{type(e).__name__}: {e}',data_keys=list(item.keys()))
        (OUT/'G1_api_result.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)); print(json.dumps(res,ensure_ascii=False)); sys.exit(1)
    (OUT/'G1_grid.png').write_bytes(img)
    res.update(kind='ok',bytes=len(img),response_meta={k:v for k,v in data.items() if k!='data'},data_keys=list(item.keys()),revised_prompt=item.get('revised_prompt'))
    (OUT/'G1_api_result.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)); print(json.dumps(res,ensure_ascii=False))
main()
