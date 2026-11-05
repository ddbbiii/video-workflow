import json
import subprocess
from pathlib import Path
import cv2
import numpy as np

base = Path(r'E:\program\1project\video\projects\助眠解说\legacy-source\zhumian\b-geomagnetic-reversal\gen_rebuild\runs\20261007-ltx-cinematic-retry-c04')
out = base.parent / '20261007-vsr-baseline-c04-spatial-full'
source = base / 'ch1-c04-v2-01-raw-1280x704.mp4'
baseline = base / 'ch1-c04-v2-01-1920x1080-hq.mp4'
vsr = out / 'ch1-c04-v2-01-realbasicvsr-streaming-1920x1080.mp4'

def metrics(path):
    cap = cv2.VideoCapture(str(path)); vals=[]; temporal=[]; frames=0; previous=None
    while True:
        ok, f = cap.read()
        if not ok: break
        gray=cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        vals.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
        small=cv2.resize(gray,(320,180),interpolation=cv2.INTER_AREA)
        if previous is not None:
            temporal.append(float(np.mean(cv2.absdiff(small,previous))))
        previous=small
        frames += 1
    cap.release()
    return {'frames': frames, 'median_laplacian': float(np.median(vals)), 'mean_laplacian': float(np.mean(vals)),
            'median_temporal_delta': float(np.median(temporal)) if temporal else 0.0,
            'p95_temporal_delta': float(np.percentile(temporal,95)) if temporal else 0.0}

def stream_info(path):
    ffprobe=r'C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffprobe.exe'
    raw=subprocess.check_output([ffprobe,'-v','error','-show_streams','-show_format','-of','json',str(path)],text=True)
    data=json.loads(raw)
    return {'video_streams':sum(s.get('codec_type')=='video' for s in data.get('streams',[])),
            'audio_streams':sum(s.get('codec_type')=='audio' for s in data.get('streams',[])),
            'duration':float(data.get('format',{}).get('duration',0.0))}

src_cap=cv2.VideoCapture(str(source)); first=src_cap.read()[1]; src_cap.release()
src_gray=cv2.cvtColor(cv2.resize(first,(1920,1080),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2GRAY)
source_metric=float(cv2.Laplacian(src_gray,cv2.CV_64F).var())
report={'source_1920_laplacian': source_metric, 'baseline': metrics(baseline), 'realbasicvsr': metrics(vsr),
        'source_streams': stream_info(source), 'output_streams': stream_info(vsr),
        'notes':['Laplacian is edge energy, not perceptual fidelity.','Temporal delta is a warning signal, not a standalone flicker verdict.','Use playback/contact sheet for deformation and tile seams.']}
report['baseline_ratio']=report['baseline']['median_laplacian']/source_metric
report['realbasicvsr_ratio']=report['realbasicvsr']['median_laplacian']/source_metric
report['checks']={
    'frame_count_matches': report['realbasicvsr']['frames']==report['baseline']['frames'],
    'audio_preserved': report['output_streams']['audio_streams']>=1,
    'duration_delta_s': abs(report['output_streams']['duration']-report['source_streams']['duration']),
    'duration_matches': abs(report['output_streams']['duration']-report['source_streams']['duration']) < 0.1,
    'temporal_warning': report['realbasicvsr']['p95_temporal_delta'] > max(8.0, report['baseline']['p95_temporal_delta'] * 2.5),
}
report['qa_status']='pass' if all(report['checks'][k] for k in ('frame_count_matches','audio_preserved','duration_matches')) else 'needs_review'
(out/'quality-qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
