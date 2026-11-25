"""Resumable, reference-guided production for the two approved parts."""
from pathlib import Path
import argparse, hashlib, json, os, shutil

from PIL import Image, ImageOps, ImageDraw

from start_production import EP, ROOT, generate
from build_storyboard import CHARACTERS, GENERIC

SCENES = {
 'village': 'A narrow present-day Chinese mountain village lane in summer. Grey courtyard wall, faded green metal doors, hanging cotton laundry, yellow plastic stool, two enamel basins, cultivated hills beyond. Chipped wall corner and damp stain below window.',
 'street': 'Ordinary small Chinese town shopping street in summer, closed unmarked shop shutters, a plain parked emergency van without markings in far distance, scratched bicycle rack, chipped paving and plastic stool at doorstep.',
 'office': 'Modest Chinese county police office, scratched wooden working desk on right, one warm desk lamp, plain case folders and dark-screen phone, enamel mug, steel cabinet behind, cool barred window on left, peeling pale wall paint and scuffed skirting.',
 'home': 'Lived-in Chinese village home in summer, small wooden table, two rice bowls, two mismatched chairs, schoolbag by window, slippers at threshold, chipped enamel cup and patched table edge, no memorial.',
 'station': 'Chinese county police station corridor, pale blue lower walls, closed plain wooden office doors, worn metal waiting bench, thermos on small table, chipped threshold and scuffed skirting. No emblems, numbers or signs.',
 'meeting': 'Chinese county police meeting room with long rectangular scratched wood table, six plain chairs, plain closed folders and enamel cups, cool window left and one restrained warm desk lamp, peeling paint and scuffed floor.',
 'lab': 'Modest forensic laboratory workbench, capped opaque sample tubes in rack, sealed paper envelopes, closed plain report folders, enamel cup on distant side desk, chipped painted stool and scratched bench rim. No exposed specimens or biological material, no anatomy.',
 'interview': 'Chinese police interview room, a rectangular scratched wooden desk separating interviewee chair on right from two investigator chairs on left, barred window on back wall, plain closed folders and water cups, chipped blue lower wall and taped chair repair. No restraints or interrogation devices.',
 'zhanghome': 'Lived-in village home with low wooden table, worn sofa, muted floral curtain, schoolbag and small travel bag beside doorway, thermos and two plain cups, chipped floor tile and scratched table edge.',
 'school': 'Modest Chinese town middle school courtyard, two-storey classroom building, open walkway, old painted steel railings, a bicycle stand and worn bench, chipped stair edges and patched wall paint. No school name, signs, flags or symbols.',
 'schooloffice': 'Modest middle-school teachers office, scratched desk with plain exercise books and a pencil cup, two chairs, book cabinet, cool window and small warm lamp, chipped enamel mug and worn floor. No writing or posters.',
 'classroom': 'Ordinary empty Chinese middle-school classroom, rows of worn wooden desks and chairs, plain dark board without writing, cool window to left, closed exercise book and pencil case on a desk, chipped desk edges and rubbed floor.',
 'restaurant': 'Modest Chinese town noodle shop, scratched square tables, stacked bowls, plain chopsticks and enamel thermos, service counter at rear right, chipped floor tiles and faded wall paint, no menus or lettering.',
 'hospital': 'Ordinary county hospital waiting corridor, closed examination-room door, plain metal linked chairs, small closed report folder and schoolbag on chair, chipped skirting and scuffed doorframe, no medical procedure, anatomy, signs or writing.',
 'stationlobby': 'Chinese county police station waiting lobby with plain reception desk, old metal bench, pale blue lower walls and outer glass entrance, scratched desk rim and taped chair repair, enamel thermos behind reception. No signs, lettering or emblems.',
 'liuhome': 'Retired teachers modest apartment, plain brown wooden entrance door, cloth grocery bag by threshold, shelf of unmarked books, small study desk with exercise book and folded reading glasses, two tea cups and slippers, scuffed wooden chair and patched table corner.',
 'shop': 'Small Chinese town general-goods shop, low service counter, shelves of plain ceramic trinkets and stationery, two small broken ceramic fragments on counter corner, scratched laminate and chipped tile, plastic stool, no brand or writing.',
 'casino': 'Worn backroom of a small Chinese city gaming venue, square green-topped table and ordinary chairs, plain unmarked face-down card backs, closed ledger, thermos and plastic stool, faded wall paint and chipped table corner. No betting instructions or visible numbers.',
 'stationplatform': 'Ordinary Chinese intercity railway platform, distant passenger train, two worn metal benches, plain wheelie suitcase near bench, chipped platform tile and scuffed bench legs. No signs, destination names or lettering.',
 'factory': 'Small Chinese light-industry factory workshop entrance, idle sewing tables beyond, worn navy work gloves on scratched lunch table, two enamel lunch tins and plain visitor ledger, chipped paint on doorframe and scuffed concrete floor.',
 'winterhome': 'Modest Chinese winter living room on lunar new-year eve, worn grey sofa with sunken cushion near dark old television, low wood dining table with simple dishes and two sets of bowls, adult slippers, patched sofa seam and scratched floor, dark cold window. No festive writing, person or body.',
 'hotel': 'Empty ordinary small-city hotel corridor, plain closed brown room doors, worn blue carpet and scratched skirting, small plain wheeled suitcase beside wall. Cool ceiling light with one weak warm wall lamp, no room number or signs.',
 'snowstreet': 'Chinese county-town lane on a snowy winter night, closed shop doors and distant plain police-station entrance light, slush along kerb, scuffed concrete wall and a parked bicycle under eave. No signs or writing.',
 'court': 'Empty modest Chinese courtroom viewed from back row, dark wooden benches and raised plain judicial desk, window daylight, worn chair edges, scratched wood and plain water cup. No emblem, seals, flags, symbols or any lettering.'
}


def shots():
    return json.loads((EP / 'storyboard/SHOT_PLAN.json').read_text())['shots']


def characters():
    manifest = []
    for i, (key, desc) in enumerate(CHARACTERS.items()):
        sheet = key in ['narrator', 'linna']
        dest = f'image/anchors/{key}-sheet.png' if sheet else f'image/anchors/{key}.png'
        if (EP / dest).exists():
            ok = True
        else:
            layout = ('FOUR equal quadrants of ONE SAME person on neutral grey background: '
                      'top-left front full body; top-right strict side full body; '
                      'bottom-left back full body; bottom-right front face close view. '
                      'Same face, hair, outfit and body proportions in all views. '
                      'No divider, label or writing. ') if sheet else (
                      'ONE single character reference, front three-quarter head-to-knees portrait on neutral grey background, '
                      'the figure large in frame, face clearly readable, standing posture with relaxed lowered hands, '
                      'no story action, no additional person, no character sheet or panels. ')
            ok = generate('char-' + key, dest, layout + desc, ['new2', 'dkl-b'][i%2])
        if not ok:
            raise SystemExit('CHARACTER_INCOMPLETE_' + key)
        if sheet:
            with Image.open(EP / dest) as image:
                w,h = image.size
                for view,box in {'front':(4,4,w//2-4,h//2-4), 'side':(w//2+4,4,w-4,h//2-4),
                                 'back':(4,h//2+4,w//2-4,h-4), 'face':(w//2+4,h//2+4,w-4,h-4)}.items():
                    image.crop(box).save(EP / f'image/anchors/{key}-{view}.png')
        spec=EP/f'image/anchors/{key}-CHARACTER_SPEC.md'
        spec.write_text('# '+key+'｜本集身份参考\n\n- 档位：'+('A' if sheet else 'B')+
                        '\n- 复用范围：episode-only；本集新建，不与其他单集建立人物关系。\n- 设定：'+desc+
                        '\n- 参考：'+dest+'\n- 禁止漂移：年龄、脸型、发型、基础服装主色。冬季按镜头加外套，身份不变。\n')
        ids = [s['id'] for s in shots() if key in s['character_ids']]
        manifest.append(dict(character_id=key, grade='A' if sheet else 'B', reference=dest,
                             definition=desc, shots=ids, sha256=hashlib.sha256((EP/dest).read_bytes()).hexdigest(),
                             status='generated_pending_visual_review', reuse='episode-only'))
        (EP / 'storyboard/CHARACTER_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    montage('characters', [EP/x['reference'] for x in manifest], [x['character_id'] for x in manifest], 4)


def plates():
    for i,(scene, desc) in enumerate(SCENES.items()):
        dest = f'image/plates/{scene}.png'
        if scene in ['village','office'] and (EP / dest).exists():
            continue
        if not generate('plate-'+scene, dest, 'Architecture and props only. ZERO PEOPLE, no human silhouettes or reflections. '+desc,
                        ['new2','dkl-b'][i%2]):
            raise SystemExit('PLATE_INCOMPLETE_' + scene)
    montage('plates', [EP/f'image/plates/{k}.png' for k in SCENES], list(SCENES), 4)


def reference(shot):
    scene=shot['scene_id']
    refs=[EP/f'image/plates/{scene}.png']
    roles=['architecture reference, change camera angle according to the requested shot']
    for key in shot['character_ids']:
        if key in GENERIC:
            continue
        path=EP/f'image/anchors/{key}-front.png' if key in ['narrator','linna'] else EP/f'image/anchors/{key}.png'
        assert path.exists(),(shot['id'],key)
        refs.append(path)
        roles.append(key+': identity and basic clothing only, action and season come from this shot')
    height=650
    tiles=[]
    for i,path in enumerate(refs):
        with Image.open(path) as im:
            tiles.append(ImageOps.contain(im.convert('RGB'), (1080 if i==0 else 430,height)))
    canvas=Image.new('RGB',(sum(im.width for im in tiles)+20*(len(tiles)-1),height),(80,80,85))
    x=0
    for im in tiles:
        canvas.paste(im,(x,0));x+=im.width+20
    dest=EP/f'image/references/{shot["id"]}.png'
    dest.parent.mkdir(parents=True,exist_ok=True);canvas.save(dest)
    return dest,roles


def frames(only=None):
    plan=shots()
    for i,s in enumerate(plan):
        if only and s['id'] not in only:
            continue
        if s['id']=='S001' and (EP/'image/final/S001.png').exists():
            reuse_log=EP/'logs/S001.json'
            if reuse_log.exists() and json.loads(reuse_log.read_text()).get('ok'):
                continue
        ref,roles=reference(s)
        definitions='\n'.join(key+': '+(CHARACTERS.get(key) or GENERIC[key]) for key in s['character_ids'])
        winter=s['section'] in [14,16] or s['section']==17 and s['id'] not in ['S133','S138','S139','S140'] or s['section']==15 and int(s['id'][1:])>=125
        season=('Winter present-day scene: adult mother wears burgundy padded jacket over grey blouse; other recurring adult workers may wear a plain dark padded jacket over their base shirt; keep faces unchanged. '
                if winter else 'Summer or earlier memory as described; keep normal base clothing. ')
        if not s['character_ids']:
            season='Winter setting, no people. ' if winter else 'Summer or earlier memory setting as described, no people. '
        people=('Exactly the listed story characters, with identities from the reference strip, no extra person. '+definitions) if s['character_ids'] else 'ZERO PEOPLE, no hands, faces, silhouettes, portraits or human reflections.'
        if s['id']=='S095':
            people+=' A large OPEN plain ledger is the central prop on the table between the manager and detectives, filling at least one third of the picture width. Its pages have no words or numbers. Manager slides the book itself toward them with one hand at its edge. NO playing cards, chips or gambling action anywhere in this shot.'
        if s['id']=='S102':
            people+=' It is late NIGHT on a snowy winter evening. Through every exterior window and entrance pane, show dark blue-black sky and dim snow lit by the station light; there is no daylight, sun or bright outdoor landscape. Interior faces remain readable under one warm practical light.'
        if s['id']=='S103':
            people+=' The empty room is clearly readable, with the single warm lamp illuminating the table, bowls and front sofa cushion. A chipped dark wooden doorframe fills the left foreground fifth, with crisp ink contours; near table edges, chair rails, mug rim and patched sofa seams have sharp black linework and hard flat shadow boundaries. Do not soften, haze or blur these furniture edges. Outside the window stays dark winter night. No person, body, human shape or injury.'
        if s['id'] in ['S123','S124']:
            people+=' A CLOSED OPAQUE grey metal cash box with a visible handle and latch is the main foreground object under the table, fully visible and one third of the frame width. Camera is low beside the table leg, looking directly at this locked box. All contents hidden; no money visible. No playing cards or chips.'
        if s['id']=='S126':
            people+=' The father holds ONE plain unlabelled glass liquor bottle upright in his hand beside his knee, clearly visible against his dark trousers. Mother sits separately by the meal. Winter indoor clothes; father has a plain dark padded vest over his khaki workshirt. No child or violence.'
        if s['id']=='S127':
            people+=' Camera is at FLOOR LEVEL. Main subject is ONE smashed ordinary clear glass bottle in FIVE large irregular pieces on the floor immediately beside the sofa leg, sharply drawn across the foreground lower half. The table and meal appear only behind it. No person, body, blood or injury. Do not show the bottle whole.'
        if s['id']=='S138':
            people+=' It is NIGHT. All window panes show deep blue-black outside with no daylight or sunbeams. The only interior warm lamp illuminates the detective and folder, his face readable in profile.'
        if len(s['character_ids'])==1 and s['character_ids'][0] not in GENERIC:
            people+=' Only ONE visible person in the entire frame. All other chairs are empty. No interviewer, companion or background person may be added; any conversational partner is completely beyond the frame, without shoulder or silhouette.'
        prompt=('Reference strip roles in order from LEFT: '+'; '.join(roles)+'. '
                'Render ONE new full-frame scene, never reproduce the strip, sheet or multiple views. '
                +SCENES[s['scene_id']]+'\n'+s['visual']+'\n'+s['framing']+'\n'+people+'\n'+season+
                'Foreground partial doorframe, chair edge or tabletop provides asymmetric depth without hiding the key action. '
                'Keep the key object or face in the inner seventy percent so a gentle camera move stays readable. '
                'Physical wear is modest chipped edges and scuffed surfaces plus the specified daily-use cup, stool or clothing, not a ruined building. '
                'Do not add clues, cash, marked papers, visible writing, phones with UI, photos, wall emblems, insignia, seals, anatomical details, injury, intimate contact, physical abuse, exposed bodies or supernatural phenomena. '
                'All young people, when explicitly listed, are fully clothed in ordinary everyday clothes and shown only in respectful daily-life or nonviolent interview scenes. '
                'Keep age differences and clothing colors distinct; no identity mixing. Faces are drawn with flat two-dimensional cel shadows, no soft airbrushed gradients.')
        if not generate(s['id'],f'image/raw/{s["id"]}.png',prompt,['new2','dkl-b'][i%2],ref):
            raise SystemExit('SHOT_INCOMPLETE_'+s['id'])
        target=EP/f'image/final/{s["id"]}.png';target.parent.mkdir(parents=True,exist_ok=True)
        with Image.open(EP/f'image/raw/{s["id"]}.png') as im:
            ImageOps.fit(im.convert('RGB'),(1920,1080),method=Image.Resampling.LANCZOS).save(target)
        if (i+1)%12==0:
            start=(i//12)*12
            montage(f'shots-{start+1:03}-{i+1:03}',[EP/f'image/final/{r["id"]}.png' for r in plan[start:i+1]],
                    [r['id'] for r in plan[start:i+1]],4)


def montage(name,paths,labels,cols):
    w,h=420,236
    rows=(len(paths)+cols-1)//cols
    out=Image.new('RGB',(cols*w,rows*(h+24)),(25,25,29));draw=ImageDraw.Draw(out)
    for i,(path,label) in enumerate(zip(paths,labels)):
        x=(i%cols)*w;y=(i//cols)*(h+24)
        draw.text((x+8,y+5),label,fill=(235,235,235))
        if path.exists():
            with Image.open(path) as im:out.paste(ImageOps.contain(im.convert('RGB'),(w,h)),(x,y+24))
    dest=EP/f'qa/{name}.jpg';out.save(dest,quality=90)
    print('REVIEW',name,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['characters','plates','pilot','frames'])
    parser.add_argument('--only',default='')
    args=parser.parse_args()
    if args.stage=='characters':characters()
    elif args.stage=='plates':plates()
    elif args.stage=='pilot':frames({'S002','S004','S007','S005','S010','S019'})
    else:frames(set(args.only.split(',')) if args.only else None)
