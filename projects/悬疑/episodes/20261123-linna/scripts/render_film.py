"""Shared affine rendering, exact-frame assembly and technical QA."""
from pathlib import Path
import argparse, concurrent.futures, hashlib, inspect, json, math, os, re, shutil, subprocess, sys, tempfile

import cv2
import numpy as np

EP=Path(__file__).resolve().parents[1]
ROOT=EP.parents[3]
os.environ['PATH']='/Users/mac/bin:'+os.environ['PATH']
sys.path.insert(0,str(ROOT/'shared/camera-motion'))
import camera_motion as cm

cv2.setNumThreads(1)
W,H=1920,1080


def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2))


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def load(part):return json.loads((EP/f'storyboard/{part}_SHOT_PLAN.json').read_text())


def motion_plan(part,available=False):
    p=load(part)
    out={'schema_version':1,'backend':'affine','output':{'width':W,'height':H,'fps':60},'transition_s':0,'shots':[]}
    for i,s in enumerate(p['shots']):
        source=EP/f'image/raw/{s["id"]}.png'
        if available and not source.exists():continue
        start=[0,0,1,1];end=[0,0,1,1]
        if s['motion']=='affine':
            if i%3==0:end=[.044,.044,.912,.912]
            elif i%3==1:start=[.044,.044,.912,.912]
            else:start=[.015,.05,.9,.9];end=[.085,.05,.9,.9]
        # Both active routes yield approximately 16:9, fit the precise ratio explicitly.
        if source.exists():
            from PIL import Image
            with Image.open(source) as im:ratio=im.width/im.height
        else:ratio=W/H
        for view in [start,end]:
            newh=view[2]*ratio/(W/H);view[1]+=(view[3]-newh)/2;view[3]=newh
        native=math.ceil(s['frames']/24*60)
        out['shots'].append(dict(id=s['id'],source=str(source),duration_s=native/60,frames=native,
            span_s=(native-1)/60,start_view=start,end_view=end,
            curve={'type':'ramped_linear','ramp_s':min(.6,(native-1)/240)},
            required_regions=[[.15,.15,.70,.70]],delivery_frames=s['frames'],
            timeline_start_frame=s['start_frame'],motion=s['motion']))
    path=EP/f'storyboard/{part}_motion-plan.json';save(path,out)
    subprocess.run([sys.executable,str(ROOT/'shared/camera-motion/validate_plan.py'),str(path)],check=True)
    return out


def render_one(s):
    dest=EP/f'video/clips/{s["id"]}.mp4';side=dest.with_suffix('.json')
    dest.parent.mkdir(parents=True,exist_ok=True)
    fingerprint=hashlib.sha256((json.dumps(s,sort_keys=True)+digest(Path(s['source']))+
                               digest(Path(cm.__file__))+inspect.getsource(render_one)).encode()).hexdigest()
    if dest.exists() and side.exists() and json.loads(side.read_text()).get('fingerprint')==fingerprint:
        return s['id']+' CACHED'
    print('RENDER_START',s['id'],flush=True)
    part=dest.with_suffix('.partial.mp4')
    static=s['start_view']==s['end_view']
    matrices=[]
    if static:
        subprocess.run(['ffmpeg','-v','error','-y','-loop','1','-framerate','24','-i',s['source'],
            '-vf','scale=1920:1080:flags=lanczos','-frames:v',str(s['delivery_frames']),
            '-an','-c:v','libx264','-preset','fast','-threads','2','-crf','17',
            '-pix_fmt','yuv420p','-movflags','+faststart',str(part)],check=True)
    else:
        source=cm.prepare_source(s['source'],s,W,H);sh,sw=source.shape[:2]
        command=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080',
            '-r','60','-i','-','-vf','fps=24','-frames:v',str(s['delivery_frames']),'-an',
            '-c:v','libx264','-preset','fast','-threads','2','-crf','17','-pix_fmt','yuv420p',
            '-movflags','+faststart',str(part)]
        with tempfile.TemporaryFile() as log:
            proc=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=log)
            try:
                for i in range(s['frames']):
                    matrix=cm.sample_matrix(cm.view_at(s,i),sw,sh,W,H)
                    image=cv2.warpAffine(source,matrix,(W,H),flags=cv2.INTER_CUBIC|cv2.WARP_INVERSE_MAP,
                                         borderMode=cv2.BORDER_REPLICATE)
                    proc.stdin.write(image.tobytes())
                    if i%5==0:matrices.append(dict(frame60=i,matrix=matrix.tolist()))
                proc.stdin.close();rc=proc.wait()
            except BaseException:
                proc.kill();proc.wait();raise
            if rc:
                log.seek(0);raise RuntimeError(log.read().decode()[-1200:])
    part.replace(dest)
    media=cm.probe(dest);v=media['streams'][0]
    assert int(v['nb_frames'])==s['delivery_frames'],(s['id'],v['nb_frames'],s['delivery_frames'])
    save(side,dict(id=s['id'],fingerprint=fingerprint,sha256=digest(dest),source_sha256=digest(Path(s['source'])),
        frames=s['delivery_frames'],native_sample_fps=24 if static else 60,delivery_fps=24,
        motion=s['motion'],trajectory_sample=matrices))
    return s['id']+' COMPLETE'


def render(part,only=None,available=False):
    free=shutil.disk_usage(EP).free
    assert free>18*1024**3,'Insufficient encoding space'
    save(EP/'qa/render-preflight.json',dict(free_bytes=free,required_bytes=18*1024**3,passed=True))
    p=motion_plan(part,available)
    rows=[s for s in p['shots'] if not only or s['id'] in only]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(render_one,rows):print(result,flush=True)


def assemble(part):
    p=load(part)
    clips=[EP/f'video/clips/{s["id"]}.mp4' for s in p['shots']]
    assert all(x.exists() for x in clips),'Missing rendered shots'
    manifest=[]
    for s,clip in zip(p['shots'],clips):
        meta=json.loads(clip.with_suffix('.json').read_text())
        source=EP/f'image/raw/{s["id"]}.png'
        assert meta['source_sha256']==digest(source), ('Stale rendered source',s['id'])
        assert meta['frames']==s['frames'], ('Stale rendered duration',s['id'])
        manifest.append(dict(id=s['id'],start_frame=s['start_frame'],frames=s['frames'],cue=s['cue'],
            source=str(source),source_sha256=meta['source_sha256'],clip=str(clip),clip_sha256=meta['sha256'],
            motion=s['motion']))
    concat=EP/f'logs/{part}-concat.txt'
    concat.write_text('\n'.join("file '"+str(x)+"'" for x in clips))
    dest=EP/f'video/final/悬疑_林娜案{part}_正文_v1.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(concat),
        '-map','0:v:0','-c:v','copy','-an','-frames:v',str(p['frames']),'-movflags','+faststart',str(dest)],check=True)
    save(EP/f'logs/{part}-assembly-manifest.json',dict(video=str(dest),sha256=digest(dest),
        fps=24,frames=p['frames'],intro_included=False,audio_included=False,subtitles_embedded=False,
        timing='estimated 3.6 visible characters per second; no recorded voice alignment',shots=manifest))
    print('VIDEO_READY_FOR_REVIEW',part,str(dest),flush=True)


def scan(part):
    p=load(part);video=EP/f'video/final/悬疑_林娜案{part}_正文_v1.mp4'
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)]))
    num,den=map(int,probe['streams'][0]['time_base'].split('/'))
    stat=EP/f'qa/{part}-signalstats.txt';log=EP/f'qa/{part}-decode.log'
    with log.open('w') as f:
        subprocess.run(['ffmpeg','-v','warning','-xerror','-i',str(video),'-map','0:v:0',
             '-vf',f'signalstats,metadata=print:file={stat}','-an','-f','null','-'],stdout=f,stderr=f,check=True)
    data=stat.read_text();frames=[]
    for m in re.finditer(r'frame:(\d+)\s+pts:(\d+)\s+pts_time:([\d.]+)\n(.*?)(?=frame:|\Z)',data,re.S):
        values=dict(re.findall(r'lavfi.signalstats.([A-Z]+)=([\d.]+)',m[4]))
        frames.append(dict(frame=int(m[1]),pts=int(m[2])*num/den,min=float(values['YMIN']),
                           max=float(values['YMAX']),mean=float(values['YAVG'])))
    assert len(frames)==p['frames'],(len(frames),p['frames'])
    def intervals(predicate):
        spans=[];begin=None
        for i,d in enumerate(frames+[dict(min=100,max=100,mean=100)]):
            if i<len(frames) and predicate(d):
                if begin is None:begin=i
            elif begin is not None:
                if i-begin>=24:spans.append(dict(start_frame=begin,end_frame=i,seconds=(i-begin)/24))
                begin=None
        return spans
    black=intervals(lambda d:d['mean']<25 and d['max']<40)
    white=intervals(lambda d:d['mean']>240 and d['min']>230)
    error=max(abs(d['pts']-d['frame']/24) for d in frames)
    steps=[frames[i+1]['pts']-frames[i]['pts'] for i in range(len(frames)-1)]
    uniform=error<.0006 and min(steps)>.0410 and max(steps)<.0423
    report=dict(decoded_frames=len(frames),expected_frames=p['frames'],full_decode_success=True,
        pixel_stats='full-resolution luma, every decoded frame',black_intervals_ge_1s=black,
        white_intervals_ge_1s=white,max_pts_error_s=error,cfr_uniform=uniform,
        passed=not black and not white and uniform)
    save(EP/f'qa/{part}-pixel-scan.json',report)
    assert report['passed'],report
    save(EP/f'qa/{part}-video.json',probe)
    v=probe['streams'][0]
    assert len(probe['streams'])==1 and v['codec_type']=='video' and v['codec_name']=='h264'
    assert v['width']==1920 and v['height']==1080 and v['avg_frame_rate']=='24/1'
    assert int(v['nb_frames'])==p['frames']
    print('PIXEL_SCAN_PASS',part,flush=True)


if __name__=='__main__':
    import re
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['render','assemble','scan'])
    parser.add_argument('part',choices=['上集','下集']);parser.add_argument('--only',default='')
    parser.add_argument('--available',action='store_true');args=parser.parse_args()
    if args.stage=='render':render(args.part,set(args.only.split(',')) if args.only else None,args.available)
    elif args.stage=='assemble':assemble(args.part)
    else:scan(args.part)
