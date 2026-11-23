from pathlib import Path
import importlib.util,sys,json,shutil,concurrent.futures
from PIL import Image
EP=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('zg',EP/'scripts/generate.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
FIXES={
'S13':'Preserve exact two men, poses, faces and architecture. Add one conspicuous stack of SIX small EMPTY white plates with a few sauce marks on tabletop by exhausted OLIVE-shirt Zhou, away from pots. Chen holds exactly TWO transparent plastic tumblers containing DARK RED-BROWN plum juice; never opaque ceramic mugs or orange juice. No new person or other change.',
'S14':'Change ONLY the two foreground ceramic mugs into TWO clear transparent plastic tumblers of DARK RED-BROWN plum juice matching S12. Preserve exhausted Zhou, the horizontal phone EXACT position and current screen corners, table architecture and empty plate stack. No handles on cups. No other change.',
'S21':'Change ONLY drinks and pots: exactly TWO transparent plastic tumblers of DARK RED-BROWN plum juice, NOT orange or yellow juice. Restore exactly TWO small stainless hotpots in the two visible induction rings. Preserve men, urgent sleeve-grip and all architecture. No new people.',
'S24':'Remove ONLY the rectangular white sheet of paper at front-right tabletop; reveal same worn brown tabletop beneath it. Keep phone, men, exact wrist grip, two small hotpots and scene. No new props or text.',
'S25':'Preserve men and their exact action, but the ONE white plate held by Chen in NAVY jacket must be COMPLETELY EMPTY, no food. Two transparent DARK RED-BROWN plum juice cups remain on table, no ceramic mug. No extra plate in hands. No other change.',
'S32':'Change ONLY meat on the single white plate held by young NAVY-jacket man: rigid curled RAW PINK frozen beef rolls, clearly coated with fine WHITE FROST. NOT dark brown, cooked, green, leafy or steaming food. Preserve man, service counter, folder, landline and architecture. No other change.',
'S31':'Change ONLY the food on ONE white oval plate: a SMALL pile of exactly the same pink FROZEN CURLED BEEF ROLLS as earlier shots, clear white frost. No solid steak or large slab, no garnish or cooked meat. Keep the plate position, ledge, mall, escalator and all architecture unchanged.',
'S35':'Change ONLY the middle-aged man HAIR: very short close-cropped crew cut black hair, grey strands at temples; match exact attached identity reference, no long side part, no pompadour, no fringe, no beard. Keep same broad oval face and mole beside LEFT eyebrow. He is Zhou43, NOT the younger fluffy-haired Chen. Keep charcoal jacket over olive shirt, exact fingers touching frosted plate, counter and camera unchanged.'}

def one(pair):
 i,(sid,change)=pair
 reference=EP/'image/final'/f'{sid}.png'
 if sid=='S35':
  # Single full-frame reference prevents copying a reference strip into panels.
  reference=EP/'image/raw/S35.png'
 p=g.generate(('repair2-' if sid=='S35' else 'repair-')+sid,'First reference is exact scene edit target; any further image ONLY identifies the face/hair, never copy its pose or background. Edit this EXACT full frame locally. Same crisp cel technique and color. '+change,reference,True,g.CHANNELS[i%2])
 shutil.copyfile(p,EP/'image/final'/f'{sid}.png')
 info=json.loads((EP/'logs'/f"{'repair2-' if sid=='S35' else 'repair-'}{sid}.json").read_text());info['repair']=change;info['file']=f'image/final/{sid}.png';g.save(EP/'logs'/f'{sid}.json',info)
 return sid
if __name__=='__main__':
 rows=list(enumerate(FIXES.items()))
 def lane(n):
  for row in rows[n::2]:print('REPAIRED',one(row),flush=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
  for f in [ex.submit(lane,n) for n in range(2)]:f.result()
 g.sheet([('repair2-' if s=='S35' else 'repair-')+s for s in FIXES],'repairs.jpg')
