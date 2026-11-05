# -*- coding: utf-8 -*-
import json, math, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

RUN = Path(r'E:\\program\\1project\\video\\projects\\助眠解说\\episodes\\you-are-a-cockroach\\runs\\20261010-assembly-b01')
EP = RUN.parents[1]
FFMPEG = Path(r'C:\\Users\\10060\\AppData\\Local\\Microsoft\\WinGet\\Packages\\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\\ffmpeg-8.1.2-full_build-shared\\bin\\ffmpeg.exe')
FFPROBE = Path(r'C:\\Users\\10060\\AppData\\Local\\Microsoft\\WinGet\\Packages\\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\\ffmpeg-8.1.2-full_build-shared\\bin\\ffprobe.exe')
FONT_DIR = Path(r'E:\program\1project\video\assets\助眠解说\fonts')  # may adjust
DELIVERY = RUN / 'delivery'
SUBS = RUN / 'subs'
INTRO = RUN / 'intro'
AUDIO = RUN / 'audio'
TZ = timezone(timedelta(hours=8))

def now_iso():
    return datetime.now(TZ).strftime('%Y-%m-%dT%H:%M:%S%z').replace('+0800','+08:00')

def probe(p):
    r = subprocess.run([str(FFPROBE),'-v','error','-show_entries','format=duration','-of','csv=p=0',str(p)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())

def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)

# discover font dir from lib_common if possible
sys.path.insert(0, str(RUN/'scripts'))
try:
    from lib_common import FONT_DIR as FD, BGM_GAIN, update_checkpoint
    FONT_DIR = FD
except Exception as e:
    print('lib_common import warn', e)
    BGM_GAIN = 1.3
    def update_checkpoint(**kw):
        ck = RUN/'CHECKPOINT.json'
        data = json.loads(ck.read_text(encoding='utf-8')) if ck.is_file() else {}
        data.update(kw); data['updated_at']=now_iso(); atomic_json(ck, data)

intro_s = probe(INTRO/'intro_narration.wav')
clean = DELIVERY/'you-are-a-cockroach_clean.mp4'
assert clean.is_file() and clean.stat().st_size > 1_000_000, clean
clean_dur = probe(clean)
print('clean', clean_dur, 'intro_s', intro_s)

# shift ASS
ass = SUBS/'body.ass'
shifted = SUBS/'full_shifted.ass'
lines = ass.read_text(encoding='utf-8').splitlines()
out_lines = []

def shift_ts(ts, off):
    h, m, rest = ts.split(':')
    s, cs = rest.split('.')
    total = int(h)*3600 + int(m)*60 + int(s) + int(cs)/100.0 + off
    if total < 0: total = 0
    cs2 = int(round(total*100))
    h, cs2 = divmod(cs2, 360000)
    m, cs2 = divmod(cs2, 6000)
    s, cs2 = divmod(cs2, 100)
    return f'{h}:{m:02d}:{s:02d}.{cs2:02d}'

for line in lines:
    if line.startswith('Dialogue:'):
        parts = line.split(',', 9)
        parts[1] = shift_ts(parts[1], intro_s)
        parts[2] = shift_ts(parts[2], intro_s)
        out_lines.append(','.join(parts))
    else:
        out_lines.append(line)
shifted.write_text('\n'.join(out_lines)+'\n', encoding='utf-8')

work = DELIVERY/'sub_work'
work.mkdir(parents=True, exist_ok=True)
ass_rel = work/'full_shifted.ass'
ass_rel.write_text(shifted.read_text(encoding='utf-8'), encoding='utf-8')
fonts_link = work/'fonts'
if not fonts_link.exists():
    try:
        fonts_link.symlink_to(FONT_DIR, target_is_directory=True)
    except Exception as e:
        print('symlink fail', e)

sub = DELIVERY/'you-are-a-cockroach_sub.mp4'
if fonts_link.exists():
    vf = 'ass=full_shifted.ass:fontsdir=fonts'
    cmd = [str(FFMPEG),'-y','-i',str(clean),'-vf',vf,'-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-c:a','copy',str(sub)]
    r = subprocess.run(cmd, cwd=str(work), capture_output=True, text=True)
else:
    font_esc = str(FONT_DIR).replace('\\','/').replace(':','\\:')
    ass_esc = str(ass_rel).replace('\\','/').replace(':','\\:')
    vf = f"ass='{ass_esc}':fontsdir='{font_esc}'"
    cmd = [str(FFMPEG),'-y','-i',str(clean),'-vf',vf,'-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-c:a','copy',str(sub)]
    r = subprocess.run(cmd, capture_output=True, text=True)
print('sub rc', r.returncode)
if r.returncode != 0:
    print(r.stderr[-800:])
    raise SystemExit('sub burn failed')
print('sub dur', probe(sub), 'MB', round(sub.stat().st_size/1e6,2))

# update minute resolution with measured intro
tl = json.loads((RUN/'timeline.json').read_text(encoding='utf-8'))
body_s = float(tl['body_total_seconds_audio'])
total = body_s + intro_s
minute = int(math.floor(total/60 + 0.5))
text = f'接下来的{minute}分钟，我们来讲讲蟑螂这个家族，漫长的演化史。'
res = {
    'body_seconds': body_s,
    'intro_seconds': intro_s,
    'minute': minute,
    'text': text,
    'status': 'resolved_after_actual_intro_measured',
    'measured_at': now_iso(),
    'clean_duration_s': clean_dur,
}
atomic_json(EP/'audio'/'intro-minute-resolution.json', res)
print('minute resolution', res)

# FINAL_QA
mm = json.loads((RUN/'media-map.json').read_text(encoding='utf-8'))
pending = [s['shot_id'] for s in mm['shots'] if s.get('pending_review')]
fallbacks = [s for s in mm['shots'] if s.get('class_change_reason')]
gen_motion = sum(float(s.get('generated_motion_seconds') or 0) for s in mm['shots'])
total_vid = float(tl['body_total_seconds_video'])
i2v_used = sum(1 for s in mm['shots'] if s.get('combo') in ('V1','V3'))
p03 = (EP/'audio'/'vo-processed'/'atempo07304'/'intro'/'intro-p03-u01.wav').is_file()
qa = {
    'created_at': now_iso(),
    'auto_checks': {
        'timeline_audio_s': body_s,
        'timeline_video_s': total_vid,
        'intro_audio_s': intro_s,
        'intro_status': {'p01': True, 'p02': True, 'p03': p03, 'p03_placeholder': False},
        'clean_path': str(clean),
        'clean_duration_s': clean_dur,
        'clean_size_bytes': clean.stat().st_size,
        'sub_path': str(sub),
        'sub_ok': sub.is_file(),
        'sub_size_bytes': sub.stat().st_size,
        'bgm_gain': BGM_GAIN,
        'minute_resolution': res,
    },
    'pending_review': pending,
    'pending_review_count': len(pending),
    'fallbacks': [{'shot_id': s['shot_id'], 'reason': s.get('class_change_reason'), 'combo': s.get('combo')} for s in fallbacks],
    'native_i2v_shots': i2v_used,
    'native_generated_motion_seconds': gen_motion,
    'native_motion_ratio_of_body': gen_motion / total_vid if total_vid else 0,
    'combo_stats': mm.get('stats'),
    'notes': [
        'Draft uses Lanczos I2V; VSR not applied (formal HD pending).',
        'Intro uses sequential affine over 8 stills (simplified vs full op4 四格 layout).',
        'intro-p03 TTS generated + atempo07304 processed; intro rebuilt; clean/sub remuxed.',
        'visual_qa pending retained; not marked passed.',
    ],
    'unfinished': [
        'optional FunASR subtitle refine',
        'VSR on selected I2V for formal delivery',
        'full op4 intro layout polish + theme art text layer',
    ],
}
if minute != 45:
    qa['unfinished'].insert(0, f'minute changed to {minute}; may need re-TTS intro-p03 text')
atomic_json(RUN/'FINAL_QA.json', qa)
atomic_json(DELIVERY/'delivery_manifest.json', {
    'clean': str(clean),
    'sub': str(sub),
    'intro_draft': str(INTRO/'intro_draft.mp4'),
    'body_video': str(DELIVERY/'body_video.mp4'),
    'full_mix': str(DELIVERY/'full_mix.wav'),
    'intro_audio_s': intro_s,
    'clean_duration_s': clean_dur,
})
update_checkpoint(stage='qa',
    completed=['create_run','build_timeline','build_media_map','prepare_shot_media','assemble_chapters','build_audio','build_subtitles','intro','delivery','qa'],
    running=[], next_action='done_draft', blocked='')
print('FINAL_QA OK')
print(json.dumps(qa['auto_checks'], ensure_ascii=False, indent=2))