"""Two reproducible short SFX, scheduled from actual simulation events."""
from pathlib import Path
import json, wave
import numpy as np

root=Path(__file__).resolve().parents[1]
trace=json.loads((root/'simulation/trace.json').read_text())
sr=48000
duration=trace['output']['duration']
mix=np.zeros((round(duration*sr),2),dtype=np.float64)
rng=np.random.default_rng(20261124)
cues=[]

for event in trace['events']:
    kind=event['type']
    if kind not in ['bounce','pass']: continue
    length=.055 if kind=='bounce' else .085
    t=np.arange(round(length*sr))/sr
    attack=np.minimum(t/.0015,1)
    release=np.minimum((length-t)/.012,1)
    if kind=='bounce':
        # Low wooden tick: body + a small reproducible, filtered noise attack.
        phase=2*np.pi*(270*t-750*t*t)
        noise=rng.standard_normal(len(t))
        noise=np.convolve(noise,np.ones(7)/7,mode='same')
        signal=(np.sin(phase)*np.exp(-t*65)+.32*noise*np.exp(-t*170))*attack*release
        gain=.13+.15*min(1,event['normalImpulse']/1100)
    else:
        # Bright glass ping, fixed pitch so it does not become a random melody.
        signal=(np.sin(2*np.pi*1320*t)+.25*np.sin(2*np.pi*2640*t))*np.exp(-t*45)*attack*release
        gain=.20
    index=round(event['time']*sr)
    count=min(len(t),len(mix)-index)
    assert count==len(t), 'Last SFX tail truncated'
    # Small world-position pan; both channels always audible.
    pan=np.clip(event['x']/400,-.65,.65)
    left=np.sqrt((1-pan)/2);right=np.sqrt((1+pan)/2)
    mix[index:index+count,0]+=signal[:count]*gain*left
    mix[index:index+count,1]+=signal[:count]*gain*right
    cues.append({'type':kind,'id':event['id'],'time':event['time'],'sample':index,
                 'duration':length,'gain':gain,'pan':float(pan),
                 'quantization_error_seconds':index/sr-event['time']})

peak=float(np.max(abs(mix)))
gain=.76/max(peak,1e-9)
mix*=gain
pcm=np.int16(np.clip(mix,-1,1)*32767)
with wave.open(str(root/'audio/mix.wav'),'wb') as f:
    f.setnchannels(2);f.setsampwidth(2);f.setframerate(sr);f.writeframes(pcm.tobytes())
maximum_overlap=max(sum(x['time']<=c['time']<x['time']+x['duration'] for x in cues) for c in cues)
report={'sample_rate':sr,'duration':duration,'passes':sum(c['type']=='pass' for c in cues),
        'bounces':sum(c['type']=='bounce' for c in cues),'maximum_overlap':maximum_overlap,
        'global_gain':gain,'pcm_peak_dbfs':20*np.log10(float(np.max(abs(mix)))),
        'max_scheduling_error_seconds':max(abs(c['quantization_error_seconds']) for c in cues),
        'music':False,'voiceover':False,'source':'Procedurally synthesized; no external recording.',
        'collision_policy':'One sound for each recorded bounce event (simulation records at most one per 25ms).',
        'cues':cues}
assert report['passes']==300 and report['bounces']==trace['result']['bounces']
(root/'audio/cues.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print({k:v for k,v in report.items() if k!='cues'})
