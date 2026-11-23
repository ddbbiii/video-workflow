from render_images import *
import cv2,numpy as np

def composite_photo(content,dest,tag):
 platepath=EP/'image/backgrounds/photo-old.png'
 background=cv2.imread(str(platepath));im=cv2.imread(str(content));h,w=im.shape[:2]
 # Precisely measured inner corners of the physical print, clockwise TL TR BR BL.
 src=np.float32([[0,0],[w-1,0],[w-1,h-1],[0,h-1]])
 quad=np.float32([[748,116],[1802,328],[1639,996],[499,688]])
 H=cv2.getPerspectiveTransform(src,quad)
 warped=cv2.warpPerspective(im,H,(2048,1152),flags=cv2.INTER_CUBIC)
 mask=cv2.warpPerspective(np.full((h,w),255,np.uint8),H,(2048,1152),flags=cv2.INTER_LINEAR)
 alpha=mask[:,:,None].astype(np.float32)/255
 result=np.clip(warped*alpha+background*(1-alpha),0,255).astype(np.uint8)
 cv2.imwrite(str(dest),result)
 info={'ok':True,'file':str(dest.relative_to(EP)),'operation':'deterministic planar photograph composite','content':str(content.relative_to(EP)),'content_sha256':hashlib.sha256(content.read_bytes()).hexdigest(),'surface':str(platepath.relative_to(EP)),'surface_sha256':hashlib.sha256(platepath.read_bytes()).hexdigest(),'homography':H.tolist(),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'metrics':api.measure(dest)}
 prior=json.loads(MANIFEST.read_text()).get(tag,{})
 info.update({k:prior.get(k) for k in ['fact','character_ids','evidence_id','channel','model','base_url']})
 save_record(tag,info)

if __name__=='__main__':
 # Fix reveal direction; already generated environment master retained.
 f=draw('S07B-r1',POS+'. '+COMMON+' Use the attached rural road environment for hillside, rail material and weather continuity. Turn view 90 degrees to face ACROSS the guardrail: rusted rail crosses bottom 15 percent, empty dry field fills middle 65 percent, same low ridge on horizon. No car or asphalt road in frame, no town, no roofs, wires, poles, foundation, people, truck or tree silhouettes. Foreground rail rust and repair tape in sharp focus. Avoid: '+NEG,EP/'image/backgrounds/road.png',1)
 shutil.copyfile(f,EP/'image/final/S07B.png')
 m=json.loads(MANIFEST.read_text());m['S07B']=dict(m['S07B-r1']);m['S07B']['fact']='View across continuous guardrail reveals bare ground without the former town';MANIFEST.write_text(json.dumps(m,ensure_ascii=False,indent=2))
 # Preserve before-image from original generation, without adding a second AI change to its pose.
 contents=EP/'image/evidence-content';contents.mkdir(exist_ok=True)
 old=contents/'photo-before.png';shutil.copyfile(EP/'image/raw/S09B-dkl-b.png',old)
 ref=reference(old,'protagonist','photo-content-repair')
 prompt=STYLE+'. '+COMMON+' Attached LEFT 75 percent is the original family snapshot content, RIGHT strip is same man identity. Produce ONE full-frame altered snapshot CONTENT, no printed border or tabletop, not a photograph lying on a table. Keep the man at exact same coordinates, same height, face, olive clothing, right arm and dangling hand pose, left hand in pocket. Remove mother and the white plate entirely, remove EVERY part of the entire kitchen, all walls, windows, cupboards, doorframes, cups and tables from edge to edge. Behind and beside man is ONLY continuous bare dry earth and low brown treeless ridge under grey sky. Where mother stood at right is unoccupied ground. No human outline, no sand woman, no fragments, no monster, no extra people. Maintain original right-arm bend as if still around absent mothers shoulder. Avoid: '+NEG
 new=draw('photo-after-content-r1',prompt,ref,1);shutil.copyfile(new,contents/'photo-after.png')
 composite_photo(old,EP/'image/final/S09B.png','S09B')
 composite_photo(contents/'photo-after.png',EP/'image/final/S10A.png','S10A')
 sheet([EP/'image/final'/f'{s}.png' for s in ['S07B','S09B','S10A']],EP/'qa/evidence-repairs.jpg')
 print('REPAIRS COMPLETE',flush=True)
