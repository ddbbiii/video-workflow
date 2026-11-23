from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,'/tmp/zizhucan-python-deps')
import cv2,numpy as np
from PIL import Image,ImageOps
EP=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def project(bgpath,source,quad):
 bg=np.array(Image.open(bgpath).convert('RGB'));h,w=bg.shape[:2]
 src=np.array(ImageOps.fit(Image.open(source).convert('RGB'),(1200,750),method=Image.Resampling.LANCZOS))
 mat=cv2.getPerspectiveTransform(np.float32([[0,0],[1199,0],[1199,749],[0,749]]),np.float32(quad))
 warped=cv2.warpPerspective(src,mat,(w,h),flags=cv2.INTER_CUBIC)
 mask=cv2.warpPerspective(np.full((750,1200),255,np.uint8),mat,(w,h),flags=cv2.INTER_LINEAR)
 # Only inside the existing paper photo or display, never touch the bezel, hand or paper.
 alpha=mask[:,:,None].astype(float)/255
 result=np.clip(bg*(1-alpha)+warped*alpha,0,255).astype('uint8')
 Image.fromarray(result).save(bgpath)
 return dict(target=str(bgpath.relative_to(EP)),source=str(source.relative_to(EP)),source_sha256=sha(source),quad=quad,result_sha256=sha(bgpath),operation='wordless exact-source perspective inset; no UI or text layer')
def main():
 paths=[('S14',EP/'image/final/S15.png',[[974,965],[1194,944],[1261,1036],[1009,1060]]),
 ('S33',EP/'image/anchors/chen-face.png',[[831,495],[1030,478],[1109,553],[894,575]]),
 ('S38',EP/'image/anchors/chen-face.png',[[983,642],[1112,628],[1195,706],[1063,721]])]
 records=[]
 for sid,src,q in paths:records.append(project(EP/'image/final'/f'{sid}.png',src,q))
 (EP/'logs/evidence-composites.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
 print('EXACT_SOURCE_EVIDENCE_INSERTS',len(records))
if __name__=='__main__':main()
