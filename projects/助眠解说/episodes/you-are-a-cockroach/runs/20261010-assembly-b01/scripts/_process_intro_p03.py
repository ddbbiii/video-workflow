import wave, struct, math, subprocess, tempfile, os
from pathlib import Path

raw = Path(r'E:\\program\\1project\\video\\projects\\助眠解说\\episodes\\you-are-a-cockroach\\audio\\vo-raw\\seed7-final\\intro\\intro-p03-u01.wav')
out = Path(r'E:\\program\\1project\\video\\projects\\助眠解说\\episodes\\you-are-a-cockroach\\audio\\vo-processed\\atempo07304\\intro\\intro-p03-u01.wav')
ffmpeg = r'C:\\Users\\10060\\AppData\\Local\\Microsoft\\WinGet\\Packages\\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\\ffmpeg-8.1.2-full_build-shared\\bin\\ffmpeg.exe'
ATEMPO = 0.7304
FRAME_MS = 20
THRESH_DB = -45.0
KEEP_HEAD = 0.10
KEEP_TAIL = 0.15
SR_TARGET = 48000

def read_wav(p):
    with wave.open(str(p), 'rb') as w:
        ch, sw, sr, n, _, _ = w.getparams()
        rawb = w.readframes(n)
    assert sw == 2
    samples = list(struct.unpack('<' + 'h'*n*ch, rawb))
    if ch == 2:
        samples = [(samples[i]+samples[i+1])//2 for i in range(0,len(samples),2)]
    return sr, samples

def write_wav(p, sr, samples):
    p.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(p), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(struct.pack('<' + 'h'*len(samples), *samples))

sr, samples = read_wav(raw)
frame = max(1, int(sr * FRAME_MS / 1000))
thresh = 10 ** (THRESH_DB / 20.0) * 32768.0
# RMS per frame
energies = []
for i in range(0, len(samples), frame):
    chunk = samples[i:i+frame]
    if not chunk:
        break
    rms = math.sqrt(sum(x*x for x in chunk) / len(chunk))
    energies.append(rms)

# find first/last frame above thresh
first = next((i for i,e in enumerate(energies) if e >= thresh), 0)
last = len(energies) - 1
for i in range(len(energies)-1, -1, -1):
    if energies[i] >= thresh:
        last = i; break
start = max(0, int(first * frame - KEEP_HEAD * sr))
end = min(len(samples), int((last + 1) * frame + KEEP_TAIL * sr))
trimmed = samples[start:end]
print(f'trim sr={sr} in={len(samples)/sr:.3f}s out={len(trimmed)/sr:.3f}s first_f={first} last_f={last}')

# write temp then atempo via ffmpeg to 48k mono
tmp = out.with_suffix('.trim.wav')
write_wav(tmp, sr, trimmed)
# atempo then resample to 48k
cmd = [ffmpeg, '-y', '-i', str(tmp), '-af', f'atempo={ATEMPO},aformat=sample_rates={SR_TARGET}:channel_layouts=mono', '-c:a', 'pcm_s16le', str(out)]
r = subprocess.run(cmd, capture_output=True, text=True)
print('ffmpeg', r.returncode)
if r.returncode != 0:
    print(r.stderr[-800:])
    raise SystemExit(r.returncode)
# probe
print('OUT', out, 'bytes', out.stat().st_size)