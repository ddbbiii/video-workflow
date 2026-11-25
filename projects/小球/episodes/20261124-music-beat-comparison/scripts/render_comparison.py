"""Controlled music A/B: identical video and PCM SFX; only ramp anchors differ."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / '20261123-sand-rings'
OUT = ROOT / 'video'
QA = ROOT / 'qa'
OUT.mkdir(exist_ok=True)
QA.mkdir(exist_ok=True)

def run(args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout

analysis = json.loads((ROOT / 'analysis/music-analysis.json').read_text())
beats = analysis['beat_times_seconds']
old = [30.065833333333334, 32.50083333333333]
aligned = [next(b for b in beats if b >= t) for t in old]
duration = 2074 / 60
complete = 33.48666666666667
assert old[0] <= aligned[0] < aligned[1] < complete
trace = json.loads((SOURCE / 'simulation/trace.json').read_text())
start = next(e['time'] for e in trace['events'] if e['type'] == 'pass')
tail = complete + .32
video = SOURCE / 'video/candidates/sand-rings-1000-music-preview.mp4'
sfx = SOURCE / 'audio/pass-sfx.wav'
music = SOURCE / 'assets/music/game-music-loop-rising.mp3'

report = {
    'scope': 'Music timing experiment; not a final episode or SRT.',
    'duration': duration, 'frames': 2074, 'fps': 60,
    'changes': 'Only the two ramp anchor times differ between A and B.',
    'source_video': str(video.relative_to(ROOT.parent)),
    'source_sfx_sha256': hashlib.sha256(sfx.read_bytes()).hexdigest(),
    'source_music_sha256': hashlib.sha256(music.read_bytes()).hexdigest(),
    'complete_seconds': complete,
    'shared_processing': 'Original PCM SFX; continuous music; no stretching; same gain endpoints and limiter with latency compensation; no per-variant loudness normalization.',
    'subjective_listening_performed': False,
    'variants': {},
}

for name, anchors in [('A_进度渐强', old), ('B_拍点渐强', aligned)]:
    first, second = anchors
    # Same piecewise-linear envelope topology and gain endpoints in both variants.
    bed = (f'if(lt(t,{start}),0.42*t/{start},if(lt(t,{first}),0.42,'
           f'if(lt(t,{second}),0.42+0.16*(t-{first})/{second-first},'
           f'if(lt(t,{complete}),0.58+0.14*(t-{second})/{complete-second},'
           f'if(lt(t,{tail}),0.72,0.72*(1-(t-{tail})/{duration-tail}))))))')
    air = (f'if(lt(t,{first}),0,if(lt(t,{second}),0.035*(t-{first})/{second-first},'
           f'if(lt(t,{complete}),0.035+0.045*(t-{second})/{complete-second},'
           f'if(lt(t,{tail}),0.08,0.08*(1-(t-{tail})/{duration-tail})))))')
    filters = ';'.join([
        f'[2:a]atrim=duration={duration},asetpts=PTS-STARTPTS,aresample=48000,asplit=2[bed0][air0]',
        f"[bed0]volume='{bed}':eval=frame[bed]",
        f"[air0]highpass=f=1800,lowpass=f=8000,volume='{air}':eval=frame[air]",
        '[1:a][bed][air]amix=inputs=3:duration=first:normalize=0,alimiter=limit=0.92:attack=5:release=80:latency=1[a]',
    ])
    output = OUT / f'{name}.mp4'
    run(['ffmpeg','-v','error','-y','-i',str(video),'-i',str(sfx),'-i',str(music),
         '-filter_complex',filters,'-map','0:v:0','-map','[a]','-c:v','copy',
         '-c:a','aac','-b:a','256k','-t',str(duration),'-movflags','+faststart',
         '-metadata','comment=Game Music Loop - Rising by HorrorPen, CC BY 3.0; see README.md',str(output)])
    probe = json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output)]))
    check = subprocess.run(['ffmpeg','-hide_banner','-i',str(output),'-af','ebur128=peak=true',
                           '-vf','blackdetect=d=1:pix_th=0.05,fps=60','-f','null','-'],capture_output=True,text=True)
    (QA / f'{name}-decode.txt').write_text(check.stderr)
    if check.returncode: raise RuntimeError(check.stderr[-1500:])
    v = next(s for s in probe['streams'] if s['codec_type']=='video')
    assert (v['width'],v['height'],v['r_frame_rate'],int(v['nb_frames'])) == (1080,1920,'60/1',2074)
    fingerprint = run(['ffmpeg','-v','error','-i',str(output),'-map','0:v:0','-c','copy','-f','hash','-hash','sha256','-']).strip()
    report['variants'][name] = {'ramp_start_seconds': first,'second_stage_seconds': second,
        'delays_seconds': [a-b for a,b in zip(anchors,old)],
        'second_stage_to_escape_seconds': complete-second,
        'video_packet_hash': fingerprint,'streams': probe['streams'], 'full_decode_passed': True}
    print(name, anchors, flush=True)

assert len({x['video_packet_hash'] for x in report['variants'].values()}) == 1

# Short ending reference: A's final 6.5667s followed by B's same interval.
cut = 28.0
filters = ('[0:v]trim=start=28,setpts=PTS-STARTPTS,scale=540:960,fps=30[v0];'
           '[1:v]trim=start=28,setpts=PTS-STARTPTS,scale=540:960,fps=30[v1];'
           '[0:a]atrim=start=28,asetpts=PTS-STARTPTS[a0];'
           '[1:a]atrim=start=28,asetpts=PTS-STARTPTS[a1];'
           '[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]')
run(['ffmpeg','-v','error','-y','-i',str(OUT/'A_进度渐强.mp4'),'-i',str(OUT/'B_拍点渐强.mp4'),
     '-filter_complex',filters,'-map','[v]','-map','[a]','-c:v','libx264','-crf','20',
     '-preset','fast','-pix_fmt','yuv420p','-c:a','aac','-b:a','256k','-movflags','+faststart',str(OUT/'结尾对照_先A后B.mp4')])
report['ending_reference'] = {'source_start_seconds':cut,'order':['A','B'],'switch_seconds':duration-cut}
(QA/'comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('Done', flush=True)
