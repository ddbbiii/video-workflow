"""Offline, reproducible music analysis for the A/B review (not downbeat detection)."""
from pathlib import Path
import hashlib
import json
import platform
import subprocess
import sys

import librosa
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / '20261123-sand-rings/assets/music/game-music-loop-rising.mp3'
OUT = ROOT / 'analysis'
DURATION = 34.566667
SR = 22050
HOP = 256


def analyze():
    OUT.mkdir(exist_ok=True, parents=True)
    # Decode exactly as a zero-origin soundtrack. No silence trimming / normalization.
    command = ['ffmpeg', '-v', 'error', '-i', str(SOURCE), '-t', str(DURATION),
               '-ar', str(SR), '-ac', '1', '-f', 'f32le', 'pipe:1']
    y = np.frombuffer(subprocess.check_output(command), dtype='<f4').copy()
    onset = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP)
    tempo, frames = librosa.beat.beat_track(onset_envelope=onset, sr=SR,
                                           hop_length=HOP, start_bpm=120,
                                           tightness=100, trim=True)
    bpm = float(np.asarray(tempo).reshape(-1)[0])
    beats = librosa.frames_to_time(frames, sr=SR, hop_length=HOP)
    onsets = librosa.onset.onset_detect(onset_envelope=onset, sr=SR,
                                       hop_length=HOP, units='time')
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=HOP)[0]
    feature_times = librosa.frames_to_time(np.arange(len(onset)), sr=SR, hop_length=HOP)
    ac = librosa.autocorrelate(onset, max_size=min(len(onset), int(8*SR/HOP)))
    ac /= max(float(ac[0]), 1e-12)
    tempo_hypotheses = []
    for factor in [0.5, 1.0, 2.0]:
        target = bpm*factor
        target_lag = 60*SR/(HOP*target)
        lag = int(round(target_lag))
        constrained_bpm, constrained = librosa.beat.beat_track(
            onset_envelope=onset, sr=SR, hop_length=HOP,
            bpm=target, tightness=100, trim=True)
        tempo_hypotheses.append({
            'bpm': target, 'relative_to_default': factor,
            'onset_autocorrelation_at_period': float(ac[lag]),
            'constrained_beat_count': len(constrained),
            'mean_onset_strength_at_beats': float(np.mean(onset[constrained])),
            'note': 'Algorithmic evidence only; no meter or downbeat confirmation.',
        })
    transitions = []
    for name, time in [('remaining_10_percent', 30.065833333333334),
                       ('remaining_3_percent', 32.50083333333333)]:
        future = beats[beats >= time]
        aligned = float(future[0]) if len(future) else None
        nearest = float(beats[np.argmin(abs(beats-time))])
        transitions.append({'name': name, 'original_seconds': time,
                            'next_beat_seconds': aligned,
                            'delay_seconds': aligned-time if aligned is not None else None,
                            'nearest_beat_seconds': nearest,
                            'nearest_beat_error_seconds': nearest-time})
    report = {
        'source': str(SOURCE.relative_to(ROOT.parent)),
        'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'duration_seconds': len(y)/SR,
        'requested_duration_seconds': DURATION,
        'versions': {'python': platform.python_version(), 'librosa': librosa.__version__,
                     'numpy': np.__version__, 'scipy': scipy.__version__,
                     'matplotlib': matplotlib.__version__},
        'parameters': {'sample_rate': SR, 'mono': True, 'hop_length': HOP,
                       'rms_frame_length': 2048, 'start_bpm': 120, 'tightness': 100,
                       'trim': True, 'time_origin_seconds': 0,
                       'time_stretch': False, 'normalization': False,
                       'decoder_command': command},
        'estimated_tempo_bpm': bpm,
        'beat_times_seconds': beats.tolist(),
        'onset_times_seconds': onsets.tolist(),
        'feature_times_seconds': feature_times.tolist(),
        'onset_strength': onset.tolist(),
        'rms': rms.tolist(),
        'rms_times_seconds': librosa.frames_to_time(np.arange(len(rms)), sr=SR, hop_length=HOP).tolist(),
        'tempo_hypotheses': tempo_hypotheses,
        'transitions': transitions,
        'limitations': ['No downbeat or musical phrase detection performed.',
                       'Half-time/double-time beat grids can both be musically reasonable.',
                       'Onsets are sound attacks, not necessarily beats.',
                       'Analysis frame spacing is 11.61 ms; perceptual accuracy is not guaranteed by resolution.',
                       'No human listening verification is claimed.'],
    }
    (OUT/'music-analysis.json').write_text(json.dumps(report, indent=2)+'\n')
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False,
                          'axes.spines.right': False, 'figure.facecolor':'#f7f8fb'})
    fig, axes = plt.subplots(3, 1, figsize=(12, 7), gridspec_kw={'height_ratios':[1,1,1.5]})
    rms_time = librosa.frames_to_time(np.arange(len(rms)), sr=SR, hop_length=HOP)
    axes[0].plot(rms_time, rms, color='#355cbd', lw=1)
    axes[0].set(xlim=(0,DURATION), ylabel='RMS energy', title=f'Same soundtrack / same physics — beat analysis ({bpm:.2f} BPM estimate)')
    axes[1].plot(feature_times, onset, color='#566575', lw=.8)
    axes[1].vlines(beats, 0, max(onset)*.6, color='#14a07a', alpha=.5, lw=.7)
    axes[1].set(xlim=(0,DURATION), ylabel='Attack strength')
    axes[2].plot(feature_times, onset, color='#566575', lw=1, label='Sound attacks')
    axes[2].vlines(beats, 0, max(onset), color='#14a07a', alpha=.3, lw=1, label='Estimated beats')
    for i,t in enumerate(transitions):
        axes[2].axvline(t['original_seconds'], color='#d16b2f', lw=2, ls='--', label='A: progress threshold' if i==0 else None)
        axes[2].axvline(t['next_beat_seconds'], color='#355cbd', lw=2, label='B: next estimated beat' if i==0 else None)
        axes[2].annotate(f"{t['delay_seconds']*1000:.0f} ms later", xy=(t['next_beat_seconds'], max(onset)*(.8-i*.22)), xytext=(t['next_beat_seconds']+.12,max(onset)*(.8-i*.22)), fontsize=10)
    axes[2].set(xlim=(28.8,34.566667), ylabel='Ending detail', xlabel='Seconds from soundtrack start')
    axes[2].legend(loc='upper right', fontsize=8, ncol=2)
    fig.text(.5,.01,'Beat estimates are not verified downbeats. Audio and physical events are not retimed.',ha='center',fontsize=9,color='#586475')
    fig.tight_layout(rect=(0,.035,1,1))
    fig.savefig(OUT/'music-analysis.png',dpi=150)
    print(json.dumps({k:report[k] for k in ['estimated_tempo_bpm','tempo_hypotheses','transitions']},indent=2))


if __name__ == '__main__':
    analyze()
