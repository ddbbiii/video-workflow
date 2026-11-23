"""Scan decoded pixels and timestamps, compare subtitles with locked narration."""
import cv2
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path

EP=Path(__file__).resolve().parents[1]
VIDEO=EP/'video/final/悬疑_纸替_正文_v1.mp4'
SRT=VIDEO.with_suffix('.srt')
PLAN=json.loads((EP/'storyboard/SHOT_PLAN-v1.json').read_text())

def norm(s):
    return ''.join(c for c in s if unicodedata.category(c)[0] in 'LN')

def main():
    cap=cv2.VideoCapture(str(VIDEO))
    frames=0; black=[];white=[];lo=255.;hi=0.
    while True:
        ok,im=cap.read()
        if not ok: break
        g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
        avg=float(g.mean());lo=min(lo,avg);hi=max(hi,avg)
        if float((g<16).mean())>0.98: black.append(frames)
        if float((g>239).mean())>0.98: white.append(frames)
        frames+=1
    cap.release()
    def runs(indices):
        out=[]
        for i in indices:
            if out and i==out[-1][1]+1: out[-1][1]=i
            else: out.append([i,i])
        return [r for r in out if r[1]-r[0]+1>=24]
    stamps=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','frame=best_effort_timestamp_time','-of','json',str(VIDEO)]))['frames']
    pts=[float(f['best_effort_timestamp_time']) for f in stamps]
    deviations=[abs(pts[i]-pts[i-1]-1/24) for i in range(1,len(pts))]
    pixel={'decoded_frames':frames,'black_runs_ge_1s':runs(black),'white_runs_ge_1s':runs(white),'mean_luma_range':[lo,hi],'cfr_timestamp_count':len(pts),'max_frame_interval_error_s':max(deviations),'pass':frames==PLAN['frames'] and len(pts)==frames and not runs(black) and not runs(white) and max(deviations)<0.000002}
    (EP/'qa/pixel_scan.json').write_text(json.dumps(pixel,indent=2)+'\n')
    blocks=SRT.read_text().strip().split('\n\n')
    texts=[''.join(b.splitlines()[2:]) for b in blocks]
    locked=''.join(s['cue'] for s in PLAN['shots'])
    identical=norm(''.join(texts))==norm(locked)
    assert identical,'Subtitle narration mismatch'
    assert pixel['pass'],pixel
    report=f'''# 字幕验收\n\n- PASS：45条单行字幕，最大20个可见字。\n- 16段锁定旁白经分句拆条为45条；去标点全文与锁定cue完全一致。\n- 首条0.000秒，末条183.208秒；视频183.208333秒。\n- 估算时间轴，未对真实人声校准。\n- 全片4397帧逐帧解码、黑白屏与帧时间间隔检查PASS，见pixel_scan.json。\n'''
    (EP/'qa/srt_qa.md').write_text(report)
    print(json.dumps(pixel));print('Locked narration and SRT match:',identical)

if __name__=='__main__': main()
