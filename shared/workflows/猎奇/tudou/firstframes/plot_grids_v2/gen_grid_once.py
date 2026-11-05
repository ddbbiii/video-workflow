# Plot-segment grid: EXACTLY ONE API call per invocation, no retry. Same method as gen_G1_once.py.
# usage: python3 gen_grid_once.py G2|G3|G4|G5
import base64, json, os, sys, time, urllib.error, urllib.request, uuid
from pathlib import Path
BASE='https://dklapi.com/v1/images/edits'; MODEL='gpt-image-2.5-sunburst'; SIZE='1024x1536'
OUT=Path('E:/program/1project/video/projects/猎奇/episodes/tudou/image/plot_grids_v2')
TV='E:/program/1project/video/assets/猎奇/characters/tudou-threeview/'
R={'heiress':TV+'step3-cast/tomato_heiress_1.png','poor':TV+'step1b/tudou_ugly_C2.png','dad':TV+'step3-cast/tomato_dad_2.png',
   'cucumber':TV+'step3-cast/cucumber_heir_3_plain.png','ceo':TV+'step2-ceo/tudou_ceo_2.png','onion':TV+'step3-cast/onion_secretary_2.png'}
ID={
 'heiress':'THE TOMATO HEIRESS: head is a glossy ripe red tomato with a green calyx on top, uncanny human face with heavy makeup, arched brows, false lashes, bright red lips, pearl drop earrings; skinny body in a fitted hot-pink satin mini dress with a ruffled collar, hot-pink high heels.',
 'poor':'THE POOR POTATO YOUTH: head is a real dirty lumpy raw potato with caked mud, pits, dark blemishes and pale sprouting shoots, uncanny hyper-realistic human face (wet human eyes, thick brows, crooked yellowish teeth); skinny real human body with veiny dirty hands, ragged patched burlap vest, rolled-up patched grey trousers, straw sandals, mud splatters.',
 'dad':'THE TOMATO DAD: head is an overripe wrinkled slightly cracked big tomato with a curly green stem, uneven droopy mustache and a snobbish sideways glare; potbellied body in a glossy burgundy suit, dark shirt FULLY BUTTONED with the belly covered exactly as in his three-view (never an open shirt, no bare belly), oversized gold chain, red pocket square, black loafers.',
 'cucumber':'THE CUCUMBER HEIR: head is a long bumpy spiky green cucumber with a small yellow cucumber flower on top, tinted oval sunglasses, smug lopsided grin; skinny body in a PLAIN black zip-up tracksuit with only simple thin white piping on the sleeves and legs exactly as in his three-view, plain black sneakers; absolutely no logos, no letters, no monogram, no prints, no patterns, no brand marks on clothes or shoes.',
 'cucumber_wilted':'THE CUCUMBER HEIR, NOW WILTED (same character as his three-view): his cucumber head is soft, wrinkled, slightly yellowed and drooping to one side, the yellow flower on top limp and brown at the edges, one sunglasses lens cracked; the same PLAIN black zip-up tracksuit with thin white piping, now dirty and creased, scuffed plain black sneakers; absolutely no logos, letters, prints or brand marks.',
 'ceo':'THE CEO POTATO: uncanny human face, head is a PEELED smooth pale-yellow potato with a moist sheen and a few small peeling gouges, slicked-back glossy black hair; skinny body in a sharp black suit, white shirt, red tie, big gold watch, shiny black leather shoes.',
 'onion':'THE ONION SECRETARY: head is a red onion with papery peeling brown outer skin and purple-white layers, round gold glasses, constantly teary trembling wet eyes with tear streaks, resigned pout; skinny body in a deep plum skirt suit, cream blouse, small pearl brooch, plum heels.',
}
LOC={
 'L1':'a tacky over-the-top Chinese engagement banquet hall in red and gold: crystal chandeliers, round tables with red tablecloths and gold chair covers, a red carpet aisle, a stage with a plain red-and-gold floral backdrop with NO symbols or characters on it, a tiered cake topped with cherry tomatoes; background guests only soft and out of focus.',
 'L2':'the gate of the tomato family mansion: a red-painted European-style villa behind a gilded wrought-iron gate with tomato-shaped finials, but visibly in decline (peeling red paint, weeds in the driveway, a dry fountain); a line of glossy black luxury sedans without badges or plates parked outside; overcast golden afternoon light.',
 'L3':'a huge bright modern potato-chip factory floor: gleaming stainless-steel conveyor belts, a giant washing drum, a fryer line with golden light and steam, an elevated steel catwalk with railings, a control panel with one big plain red button (no labels); sacks and piles of potatoes.',
 'L3b':'close detail of an industrial slicing machine at the end of the conveyor: a polished steel hopper and an enclosed blade housing (blades never visible), a chute where thin round chips shoot out into a fryer basket and a plain green chip bag.',
 'L4':'a muddy rural vegetable garden plot in drizzling rain: furrows of wet dark soil, puddles, a few potato plants, a broken wooden fence, grey sky; desaturated flashback look.',
}
GRIDS={
 'G2':dict(refs=['cucumber','heiress','poor'], story='the engagement banquet: a rich cucumber heir struts in, mocks the poor potato and takes the bride; the humiliated potato swears revenge', loc=['L1'], panels=[
  'Medium shot of the cucumber heir strutting in through the banquet hall entrance toward camera, hands in pockets, sunglasses on, smug lopsided grin, looking someone up and down; chandeliers behind him.',
  'Close-up of the poor potato youth looking up blankly, confused wide wet eyes, mouth slightly open, sprouts on his head.',
  'Low-angle close-up of the cucumber heir pulling his sunglasses down his nose with one finger, thumb pointing at himself, cold white frost mist curling around his bumpy spiky cucumber head, very full of himself.',
  'Medium two-shot in the banquet hall, both fully visible: the cucumber heir throws his arm around the tomato heiress\'s shoulders, she leans into him giggling coyly.',
  'Medium two-shot, both fully visible: the tomato heiress clings to the cucumber heir\'s arm and sniffs him dreamily with closed eyes, about to whip her head toward camera; he smirks behind his sunglasses.',
  'Close-up of the poor potato youth with his head bowed, tears welling in his realistic human eyes, jaw clenched, muddy fists tightening at the bottom of the frame; the banquet hall\'s red light behind him dim and blurred.',
  'Extreme close-up of the poor potato youth snapping his head up to stare straight into the camera, fierce burning determined eyes, mud-caked lumpy potato skin in macro detail, pale sprouts on top trembling, strong red rim light from behind.',
  'Alternate take of panel 7: extreme close-up of the poor potato youth glaring straight into the camera with fierce determined eyes, slightly different angle, strong red rim light, sprouts trembling.',
  'Alternate take of panel 5: medium two-shot of the tomato heiress hugging the cucumber heir\'s arm, now snapping her head toward camera and flicking one hand dismissively, the cucumber heir smirking beside her.']),
 'G3':dict(refs=['onion','ceo','dad'], story='three years later at the shabby tomato mansion gate: a black motorcade arrives, the onion secretary opens the car door, the CEO potato steps out and hands a gold card to the stunned tomato dad, and the secretary announces the takeover', loc=['L2'], panels=[
  'EMPTY SCENE, NO CHARACTERS AT ALL: wide shot of the tomato family mansion gate on an overcast golden afternoon: three glossy black luxury sedans without badges glide up the weedy driveway and stop in front of the gilded wrought-iron gate; the red villa behind looks shabby with peeling paint.',
  'Medium shot of the onion secretary holding open the rear door of a black sedan in front of the mansion gate, bowing slightly, tears streaming down her onion face behind round glasses, dabbing her eyes with a handkerchief.',
  'Low-angle medium shot of the CEO potato stepping out of the black sedan in front of the mansion gate, shiny black shoe on the ground, adjusting his gold watch, smug raised eyebrow, peeled pale-yellow potato head gleaming.',
  'Medium shot of the tomato dad behind the gilded iron gate of the shabby mansion, shading his eyes with one hand and squinting toward the motorcade, burgundy suit a bit faded, shirt buttoned.',
  'Close-up of the tomato dad gaping in shock, jaw dropped, droopy mustache quivering, eyes bulging out of his wrinkled tomato face.',
  'Medium close-up of the CEO potato at the mansion gate giving a mock-polite slight bow while holding out a completely blank gold business card between two fingers, smug half smile, eyebrow raised.',
  'Close-up of the tomato dad holding a completely blank gold business card in both trembling hands, eyes wide and greedy, gold chain shaking.',
  'Medium shot of the onion secretary stepping forward at the mansion gate, holding up an open leather document folder with a contract page that has no readable text (only blank or blurred lines), sniffling with tears running, glasses slightly fogged, but chin up officially.',
  'Alternate take of panel 3: low-angle shot from ground level of the CEO potato\'s shiny black shoe stepping out of the black sedan onto the weedy driveway, him adjusting his gold watch with a smug raised eyebrow.']),
 'G4':dict(refs=['heiress','ceo','onion'], story='at the mansion gate the tomato heiress begs the CEO potato to take her back; he refuses coldly and his onion secretary shows her out', loc=['L2','L4 (panel 4 only)'], panels=[
  'Medium shot of the tomato heiress running out of the mansion gate toward camera in her hot-pink dress, wobbling on high heels, arms reaching out, mascara running down her tomato face.',
  'High-angle medium two-shot at the mansion gate, both visible: the tomato heiress kneels on the driveway hugging the CEO potato\'s suit leg and looking up pleadingly, mascara streaked; he looks down at her coldly.',
  'Low-angle close-up from the kneeling heiress\'s point of view: the CEO potato looks down coldly, a thin cold smirk, slicked hair, peeled potato skin with a moist sheen, overcast sky behind.',
  'FLASHBACK, different location (L4), desaturated grey colours: wide shot of a muddy vegetable garden in drizzling rain: a poor muddy lumpy potato-headed youth in a ragged burlap vest and patched grey trousers rolls sideways through the wet dark furrows, covered in mud, his potato head and pale sprouts caked with soil, face turned away from camera (face not visible).',
  'Close-up of the kneeling tomato heiress holding up a small plain white dish of ketchup like an offering, fluttering her false lashes coyly, tear-streaked makeup, forced flirtatious smile.',
  'Medium shot at the mansion gate: the CEO potato turns away, raising one hand in a dismissive wave over his shoulder, cool and bored; behind him the teary onion secretary bows and gestures toward the gate.',
  'Alternate take of panel 2: high-angle two-shot, the tomato heiress on her knees clutching the CEO potato\'s trouser leg and wailing up at him, he looks down at her with cold contempt.',
  'Alternate take of panel 3: low-angle close-up of the CEO potato looking down with a cold thin smirk, overcast sky behind, slightly different angle.',
  'Alternate take of panel 6: medium shot, the CEO potato walking away with a dismissive backhand wave, the teary onion secretary bowing deeply and gesturing toward the gate behind him.']),
 'G5':dict(refs=['cucumber','ceo','onion'], story='at the potato-chip factory the wilted cucumber heir begs the CEO potato for a job; the CEO decides on a new flavour, the onion secretary presses the button, and the cucumber is carried by the conveyor into the slicing machine; the CEO ends eating a green-edged chip', loc=['L3','L3b'], panels=[
  'Medium-wide shot on the bright potato-chip factory floor: the wilted cucumber heir runs in between stainless-steel conveyor belts waving both arms desperately, droopy soft cucumber head bent to one side, dirty tracksuit, one shoe missing.',
  'Low-angle medium shot of the CEO potato standing on the steel catwalk above the factory floor, arms crossed, one eyebrow raised, amused smirk, conveyor belts and steam behind him.',
  'Close-up of the wilted cucumber heir begging with hands pressed together, his soft wrinkled yellowing cucumber head drooping, limp flower on top, one cracked sunglasses lens, tearful pathetic face.',
  'Medium shot of the CEO potato on the catwalk smiling slyly and glancing sideways at the conveyor line behind him, where thin potato slices travel toward the fryer.',
  'Close-up of the onion secretary at the factory control panel, teary but determined, slamming her palm down on one big plain red button with no label.',
  'Medium shot of the wilted cucumber heir sitting on a moving stainless-steel conveyor belt among potatoes, looking around confused, carried toward the end of the line.',
  'Close-up of the wilted cucumber heir on the conveyor right at the polished steel hopper of a big industrial slicing machine with an enclosed blade housing, sunglasses flying off, screaming in comic terror with eyes bulging; no blades visible, no injury.',
  'EMPTY SCENE, NO CHARACTERS AT ALL: close-up of the chute of an industrial slicing machine: thin round golden chips with green cucumber-skin edges shoot out in a cascade into a fryer basket and a completely plain green chip bag; steam and golden light; machinery and chips only.',
  'Medium shot of the CEO potato on the factory catwalk crunching a green-edged potato chip and looking straight into the camera with a smug wink; beside him the teary onion secretary hugs a completely plain green chip bag with no print.']),
}
def build(g):
    c=GRIDS[g]; names={'cucumber':'cucumber','heiress':'heiress','poor':'poor','dad':'dad','ceo':'ceo','onion':'onion'}
    idk=[('cucumber_wilted' if (g=='G5' and k=='cucumber') else k) for k in c['refs']]
    reflines='\n'.join(f'- Image {i+1} = {ID[k]}' for i,k in enumerate(idk))
    if g=='G5': reflines+='\n  (Image 1 shows the cucumber heir fresh; in every panel here draw him WILTED as described, same face and same plain tracksuit.)'
    locs='\n'.join(f'- {l}: {LOC[l.split()[0]]}' for l in c['loc'])
    panels='\n'.join(f'({i+1}) {p}' for i,p in enumerate(c['panels']))
    return f'''Create exactly ONE composite image: a clean 3x3 grid of nine separate vertical 9:16 live-action film-still panels, separated by thin uniform pure-white gutters. Read panels left to right, top to bottom. This is one continuous story segment ({c['story']}), so the same characters, costumes, props, set and lighting stay consistent across all panels.

Reference images (character turnaround sheets; each sheet shows ONE character from front, side and back - draw that character only ONCE per panel, never as three copies):
{reflines}
Match each character's face, head shape, skin texture and outfit to its reference sheet exactly. Never swap features between characters.

Setting:
{locs}

Panels:
{panels}

Rules for every panel:
- Only the characters named in that panel appear in the foreground; no extra unrequested characters in the foreground or midground.
- Any background guests, bystanders, chauffeurs, workers or extras must ALSO be vegetable-headed people (assorted real vegetable heads), small and out of focus; absolutely NO normal human heads anywhere in the image.
- If the tomato dad appears, his dark shirt is fully buttoned and his belly covered, as in his three-view.
- The cucumber heir always wears the PLAIN black tracksuit with thin white piping only: no logos, no letters, no prints.

Style: Photoreal live-action film still. Real vegetable heads with macro skin texture and uncanny hyper-realistic human faces on skinny realistic human bodies with real hands; creepy macro realism, ugly-funny, absurd comedy. Cinematic lighting, shallow depth of field.
Strictly: NO text, no letters, no numbers, no Chinese characters, no 囍 symbol anywhere, no subtitles, no captions, no panel numbers, no labels, no signs, no license plates, no logos, no brand marks, no watermark. No blood, no gore, no wounds. No cartoon, anime, plush or clay look; no extra limbs or fingers.'''

def multipart(prompt,refs):
    b='----kepu'+uuid.uuid4().hex; parts=[]
    def field(k,v): parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    field('model',MODEL); field('prompt',prompt); field('size',SIZE); field('n','1')
    for ref in refs:
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="image[]"; filename="{Path(ref).name}"\r\nContent-Type: image/png\r\n\r\n'.encode())
        parts.append(Path(ref).read_bytes()); parts.append(b'\r\n')
    parts.append(f'--{b}--\r\n'.encode())
    return b''.join(parts), f'multipart/form-data; boundary={b}'

def main(g):
    refs=[R[k] for k in GRIDS[g]['refs']]; prompt=build(g)
    (OUT/f'{g}_prompt.txt').write_text(prompt,encoding='utf-8')
    if '--dry' in sys.argv: print(prompt); return
    key=os.environ.get('IMAGE_RELAY_KEY_1K')
    res={'grid':g,'model_requested':MODEL,'size_requested':SIZE,'endpoint':BASE,'refs':refs,'n_calls':1}
    if not key: res.update(kind='config',error='IMAGE_RELAY_KEY_1K missing'); print(json.dumps(res)); sys.exit(1)
    body,ctype=multipart(prompt,refs)
    req=urllib.request.Request(BASE,data=body,method='POST',headers={'Authorization':'Bearer '+key,'Content-Type':ctype,'Accept':'application/json'})
    t0=time.time(); res['started']=time.strftime('%Y-%m-%d %H:%M:%S %z')
    def fail(**kw):
        res.update(**kw); res['elapsed']=round(time.time()-t0,1)
        (OUT/f'{g}_api_result.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)); print(json.dumps(res,ensure_ascii=False)); sys.exit(1)
    try:
        with urllib.request.urlopen(req,timeout=600) as r: status=r.status; raw=r.read()
    except urllib.error.HTTPError as e: status=e.code; raw=e.read()
    except Exception as e: fail(kind='network',error=f'{type(e).__name__}: {e}')
    text=raw.decode('utf-8','replace')
    try: data=json.loads(text)
    except Exception: data=None
    res['status']=status
    if not (200<=status<300 and isinstance(data,dict) and isinstance(data.get('data'),list) and data['data']): fail(kind='http',body=text[:4000])
    item=data['data'][0]
    try:
        if item.get('b64_json'): img=base64.b64decode(item['b64_json'])
        elif item.get('url'):
            with urllib.request.urlopen(urllib.request.Request(item['url'],headers={'Accept':'image/*'}),timeout=600) as r: img=r.read()
        else: raise RuntimeError('no url or b64_json')
    except Exception as e: fail(kind='download',error=f'{type(e).__name__}: {e}',data_keys=list(item.keys()))
    (OUT/f'{g}_grid.png').write_bytes(img)
    res.update(kind='ok',elapsed=round(time.time()-t0,1),finished=time.strftime('%Y-%m-%d %H:%M:%S %z'),bytes=len(img),response_meta={k:v for k,v in data.items() if k!='data'},data_keys=list(item.keys()))
    (OUT/f'{g}_api_result.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)); print(json.dumps(res,ensure_ascii=False))
main(sys.argv[1])
