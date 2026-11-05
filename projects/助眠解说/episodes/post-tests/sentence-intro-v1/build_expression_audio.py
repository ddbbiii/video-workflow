import json
from pathlib import Path
import subprocess
import wave
import argparse
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('--directory', default='voice-expression')
args = parser.parse_args()
base = Path(__file__).resolve().parent / args.directory
segments, records = [], []
for i in range(1, 4):
    source = base / 'raw' / f'i{i:02}.wav'
    with wave.open(str(source), 'rb') as w:
        rate = w.getframerate()
        audio = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2')
    step = round(rate * .02)
    active = [j for j in range(0, len(audio), step)
              if np.sqrt(np.mean((audio[j:j+step].astype(float)/32768)**2)) > 10**(-45/20)]
    if not active:
        raise ValueError('Silent output')
    first = max(0, active[0] - round(rate*.1))/rate
    last = min(len(audio), active[-1]+step+round(rate*.15))/rate
    paced = base / f'i{i:02}-paced.wav'
    subprocess.run(['ffmpeg','-v','error','-n','-i',str(source),'-af',
                    f'atrim=start={first}:end={last},asetpts=PTS-STARTPTS,atempo=0.7304',
                    '-ar','48000','-ac','1',str(paced)],check=True)
    with wave.open(str(paced),'rb') as w:
        samples = np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').copy()
    if i == 1:
        segments.append(np.zeros(19200,dtype='<i2'))
    segments.extend([samples,np.zeros(round(48000*(.8 if i == 3 else .45)),dtype='<i2')])
    records.append({'source':str(source),'paced':str(paced),'duration':len(samples)/48000})
output = base / 'expression-preview.wav'
combined = np.concatenate(segments)
with wave.open(str(output),'wb') as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(48000)
    w.writeframes(combined.tobytes())
subprocess.run(['ffmpeg','-v','error','-i',str(output),'-f','null','-'],check=True)
(base/'manifest.json').write_text(json.dumps({'status':'candidate-awaiting-listening',
    'change':args.directory, 'seed':7,
    'speed_applied_once':.7304,'duration':len(combined)/48000,'decode_ok':True,
    'records':records,'output':str(output)},ensure_ascii=False,indent=2),encoding='utf-8')
print(output)
