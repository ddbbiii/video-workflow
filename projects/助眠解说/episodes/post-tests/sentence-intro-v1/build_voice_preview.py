import importlib.util
import json
import math
from pathlib import Path
import subprocess
import wave

import numpy as np

ROOT = Path('E:/program/1project/video')
BASE = Path(__file__).resolve().parent
OUT = BASE / 'voice-preview'
OUT.mkdir(exist_ok=True)


def run(args):
    subprocess.run(args, check=True)


def probe(path):
    return json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
                                              '-show_format', '-of', 'json', str(path)]))


spec = importlib.util.spec_from_file_location('intro', ROOT / 'shared/compositing/build_sentence_intro.py')
intro = importlib.util.module_from_spec(spec)
spec.loader.exec_module(intro)
old = json.loads((BASE / 'render-v6b-video-pool/manifest.json').read_text(encoding='utf-8'))
pool = sorted((ROOT / 'projects/助眠解说/episodes/b-geomagnetic-reversal/video/clips/final_r2').glob('*.mp4'))
records, parts, samples = [], [], []
sr = 48000
for i, card in enumerate(old['sources'], 1):
    raw = OUT / 'raw' / f'i{i:02}.wav'
    with wave.open(str(raw), 'rb') as wav:
        assert wav.getsampwidth() == 2
        rate, channels = wav.getframerate(), wav.getnchannels()
        audio = np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2').reshape(-1, channels)
    step = round(rate * .02)
    active = [j for j in range(0, len(audio), step)
              if np.sqrt(np.mean((audio[j:j+step].astype(np.float64) / 32768) ** 2)) > 10 ** (-45 / 20)]
    if not active:
        raise ValueError(f'Empty voice: {raw}')
    first = max(0, active[0] - round(rate * .1))
    last = min(len(audio), active[-1] + step + round(rate * .15))
    paced = OUT / f'i{i:02}-paced.wav'
    run(['ffmpeg', '-v', 'error', '-n', '-i', str(raw), '-af',
         f'atrim=start={first/rate}:end={last/rate},asetpts=PTS-STARTPTS,atempo=0.7304',
         '-ar', str(sr), '-ac', '1', '-c:a', 'pcm_s16le', str(paced)])
    with wave.open(str(paced), 'rb') as wav:
        voice = np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2').copy()
    lead = .4 if i == 1 else 0
    tail = .8 if i == 3 else .45
    frames = math.ceil((lead + len(voice)/sr + tail) * 60)
    duration = frames / 60
    segment = np.zeros(round(duration * sr), dtype='<i2')
    offset = round(lead * sr)
    segment[offset:offset+len(voice)] = voice
    samples.append(segment)
    source = Path(card['source'])
    available = float(probe(source)['format']['duration'])
    if available < duration:
        source = next(p for p in pool if float(probe(p)['format']['duration']) >= duration)
        available = float(probe(source)['format']['duration'])
    start = min(.6, (available - duration)/2)
    part = OUT / f'part-{i:02}-silent.mp4'
    intro.render_smooth(source, start, frames, duration, 'none', 0, card['text'],
                        ROOT / 'assets/助眠解说/subtitles/style-r4/fonts/SourceHanSansSC-Heavy.otf',
                        1000, 96, 102, part, 1920, 1080, 60, 17, 1000)
    parts.append(part)
    records.append(dict(raw=str(raw), paced=str(paced), source=str(source), start=start,
                        duration=duration, voice_duration=len(voice)/sr, trim=[first/rate,last/rate]))
    print(f'CARD {i} rendered {duration:.3f}s', flush=True)

combined = OUT / 'intro-voice.wav'
with wave.open(str(combined), 'wb') as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(sr)
    wav.writeframes(np.concatenate(samples).tobytes())
listing = OUT / 'concat-voice-preview.txt'
listing.write_text(''.join(f"file '{p.as_posix()}'\n" for p in parts), encoding='utf-8')
silent = OUT / 'intro-silent.mp4'
final = OUT / 'intro-with-voice-preview.mp4'
run(['ffmpeg', '-v', 'error', '-n', '-f', 'concat', '-safe', '0', '-i', str(listing),
     '-c', 'copy', '-an', '-movflags', '+faststart', str(silent)])
run(['ffmpeg', '-v', 'error', '-n', '-i', str(silent), '-i', str(combined), '-map', '0:v:0',
     '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(final)])
run(['ffmpeg', '-v', 'error', '-i', str(final), '-f', 'null', '-'])
(OUT / 'manifest.json').write_text(json.dumps(dict(status='preview-awaiting-user-listening',
    video=str(final), silent=str(silent), voice=str(combined), cards=records, probe=probe(final),
    decode_ok=True, speed_applied_once=.7304, bgm=False, native_background_fps=30,
    output_fps=60, text_fade_seconds=[1,1]), ensure_ascii=False, indent=2), encoding='utf-8')
print(final, flush=True)
