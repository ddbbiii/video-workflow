"""Repair only story-critical visual states; candidates require visual review."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image
import produce as p

EP = p.EP
OUT = EP / 'image/review'
OUT.mkdir(exist_ok=True)
TASKS = {
 'S03': ('S05', 'Reframe to an actual CLOSE VIEW of this exact effigy, from its hat to its folded paper waist, filling two thirds of image height. Preserve its face and hat design exactly. Stool edge at bottom, worn bedroom wall behind. Do not simplify into a different cartoon doll. No people.'),
 'S08': ('S08', 'Precise object edit: REMOVE the effigy from the wooden stool, leaving the stool EMPTY. Place that same effigy standing on the FLOOR immediately beside the bed. Preserve the ordinary flesh human hand on quilt in foreground, the shut door and latch. Exactly one effigy, 45 cm tall.'),
 'S09': ('S10', 'Reframe to a CLOSE evidence view of the same effigy on the PILLOW: its folded paper face fills the right third, with one black ink-water streak down its cheek from the ink-dot eye. A tiny fresh black circular droplet mark on the pillow directly below the cheek is clearly visible. White pillow fills lower third. Same hat and red green folded paper robe. No stool or second effigy.'),
 'S11': ('S10', 'Precise object edit: the same small effigy is STANDING UPRIGHT on the QUILT beside the pillow, its FACE points RIGHT toward the wooden DOOR AT THE RIGHT EDGE. Show its left side profile with head turned to the RIGHT, one foot forward to the RIGHT. Do not sit. Do not face the left wall. Preserve exactly the same size. The wooden stool at the bed foot is EMPTY. No second effigy. Keep room layout.'),
 'S13': ('S13', 'Precise object edit: REMOVE the effigy from the stool, leave stool EMPTY. Place it on the PILLOW at the head of the bed on the left, still exactly 45 cm tall. Preserve the nearly closed door at right with the narrow light gap and released latch. Exactly one effigy.'),
 'S15': ('S15', 'Use this image as an EDIT TARGET. REMOVE the separate standing effigy from the stool: there must be NO separate doll or person anywhere in the room. Reframe much closer downward to the two foreground hands. They are SMALL HOLLOW FOLDED WHITE PAPER HANDS with angular folded paper fingers, split paper wrists exposing thin tan BAMBOO RIBS, attached to red green PAPER SLEEVES. They are not human hands or gloves. Both hands must occupy the lower HALF of the frame, resting on a large adult pillow and quilt. Viewpoint is now tiny, at pillow height. Empty stool and worn room only in upper background. Clear paper fibers, creases and open wrist seams. Same flat cel ink style.'),
 'S16': ('S15', 'EDIT TARGET: end scene from the tiny paper protagonist viewpoint. No separate effigy or person in the room. Two very small folded WHITE PAPER HANDS occupy the lower third, angular paper fingers, broken paper wrist seams with visible thin bamboo ribs, red green paper sleeves; hands rest on pillow. Upper half shows same old room and the now OPEN wooden door with EMPTY dark hallway. Stool EMPTY. Clear still unresolved composition, no text. Hands MUST be visible, not cropped out.'),
}

def run(sid):
    source_id, detail = TASKS[sid]
    ref = EP / 'image/final' / (source_id + '.png')
    if sid == 'S16' and (OUT/'S15.png').exists():
        ref = OUT/'S15.png'
    shot = next(s for s in p.PLAN['shots'] if s['id'] == sid)
    assigned = shot['channel_assigned']
    prompt = '\n'.join([p.POS, p.CEL, 'Input image is the edit target and identity/style reference. Change only the requested state or framing. Single complete 16:9 image.', detail, 'Preserve peeling paint, water stains, worn quilt and thermos; cold grey blue with the same single warm lamp. Use clean linework and hard edged flat color. No captions.', p.AVOID])
    for name in [assigned] + [n for n in p.ACTIVE['parallel_channels'] if n != assigned]:
        ch = dict(p.POLICY['channels'][name], name=name, policy=p.POLICY['active'])
        for attempt in (1,2):
            with p.LOCKS[name]:
                info = p.api.call(ch,prompt,{'tag':sid+'-repair'},ref,attempt)
            if info.get('ok'):
                path = EP/info['file']
                info['metrics'] = p.api.measure(path)
                issues = p.api.gate(info,ch)
                info['issues'] = issues
                if not issues:
                    (OUT/(sid+'.png')).write_bytes(path.read_bytes())
                    info.update(reference=str(ref.relative_to(EP)),assigned_channel=assigned,model=ch['model'],qa='technical-pass-awaiting-visual')
                    p.save_json(OUT/(sid+'.json'), info)
                    print(sid, name, 'candidate ready',flush=True)
                    return
            p.save_json(OUT/(sid+'-attempt.json'),info)
    raise RuntimeError(sid+' repair unavailable or below quality gate')

if __name__ == '__main__':
    ids = sys.argv[1].split(',')
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(run,ids))
