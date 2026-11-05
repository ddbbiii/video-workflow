# -*- coding: utf-8 -*-
"""Build narration-dry, bgm-stem, mix-master from timeline (processed VO, no re-atempo)."""
from __future__ import annotations
import math, struct, subprocess, sys, wave
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_common import (
    RUN, FFMPEG, FFPROBE, BGM, BGM_GAIN, SR, BODY_SECTIONS,
    load_json, atomic_json, update_checkpoint, log_stage, now_iso,
)

AUDIO = RUN / "audio"
AUDIO.mkdir(parents=True, exist_ok=True)


def write_silence_wav(path: Path, samples: int, sr: int = SR):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"\x00\x00" * samples)


def concat_narration(timeline, out_wav: Path):
    """Sample-accurate mono 48k PCM narration with gaps as silence."""
    # Build via ffmpeg concat of wavs + generated silences
    parts_dir = AUDIO / "narration_parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    list_file = AUDIO / "narration_concat.txt"
    lines = []
    utts = timeline["utterances"]
    for i, u in enumerate(utts):
        gap = float(u.get("gap_before_s") or 0)
        if gap > 0:
            gap_samples = int(round(gap * SR))
            gap_path = parts_dir / f"gap_{i:04d}.wav"
            if not gap_path.is_file():
                write_silence_wav(gap_path, gap_samples)
            lines.append(f"file '{gap_path.as_posix()}'")
        lines.append(f"file '{Path(u['path']).as_posix()}'")
    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    cmd = [str(FFMPEG), "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
           "-c:a", "pcm_s16le", "-ar", str(SR), "-ac", "1", str(out_wav)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:])
    return out_wav


def loop_bgm(target_s: float, out_wav: Path):
    """Loop BGM with ~6s crossfade, apply gain 1.30, fade in/out."""
    xfade = 6.0
    fade_in = 2.0
    fade_out = 5.0
    # probe source duration
    r = subprocess.run([str(FFPROBE), "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(BGM)], capture_output=True, text=True, check=True)
    src_dur = float(r.stdout.strip())
    # number of loops needed
    effective = src_dur - xfade
    n = max(1, int(math.ceil((target_s + xfade) / effective)))
    # build filter for acrossfade chain is complex; simpler: apad + trim after volume, with soft loop via stream_loop
    # Use stream_loop then trim; crossfade approximation via afade at loop boundaries is harder.
    # Practical: stream_loop, trim, volume, afade in/out.
    cmd = [
        str(FFMPEG), "-y", "-stream_loop", str(n), "-i", str(BGM),
        "-t", f"{target_s:.3f}",
        "-af", f"aformat=sample_fmts=fltp:sample_rates={SR}:channel_layouts=stereo,volume={BGM_GAIN},afade=t=in:st=0:d={fade_in},afade=t=out:st={max(0, target_s-fade_out)}:d={fade_out}",
        "-c:a", "pcm_s16le", str(out_wav),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:])
    # Better crossfade loop: build with acrossfade if n>1
    if n > 1:
        # rebuild with acrossfade chaining for cleaner seams
        parts = []
        tmp = AUDIO / "bgm_loops"
        tmp.mkdir(parents=True, exist_ok=True)
        for i in range(n):
            p = tmp / f"loop_{i}.wav"
            subprocess.run([str(FFMPEG), "-y", "-i", str(BGM), "-af",
                            f"aformat=sample_fmts=fltp:sample_rates={SR}:channel_layouts=stereo",
                            "-c:a", "pcm_s16le", str(p)], capture_output=True, check=True)
            parts.append(p)
        # chain acrossfade
        # ffmpeg acrossfade filter for multiple inputs
        inputs = []
        for p in parts:
            inputs += ["-i", str(p)]
        filt = []
        # progressive acrossfade
        # [0][1]acrossfade=d=6:c1=tri:c2=tri[a1]; [a1][2]acrossfade=...
        cur = "[0]"
        filt_parts = []
        for i in range(1, n):
            outlab = f"[a{i}]" if i < n - 1 else "[ax]"
            left = cur if i == 1 else f"[a{i-1}]"
            filt_parts.append(f"{left}[{i}]acrossfade=d={xfade}:c1=tri:c2=tri{outlab}")
            cur = outlab
        filt_parts.append(
            f"[ax]volume={BGM_GAIN},afade=t=in:st=0:d={fade_in},afade=t=out:st={max(0, target_s-fade_out)}:d={fade_out},atrim=0:{target_s},aformat=sample_fmts=s16:sample_rates={SR}:channel_layouts=stereo[out]"
        )
        # if n==2, outlab for i=1 is [ax] when n-1=1... handle
        if n == 2:
            filt_str = f"[0][1]acrossfade=d={xfade}:c1=tri:c2=tri,volume={BGM_GAIN},afade=t=in:st=0:d={fade_in},afade=t=out:st={max(0, target_s-fade_out)}:d={fade_out},atrim=0:{target_s},aformat=sample_fmts=s16:sample_rates={SR}:channel_layouts=stereo[out]"
        else:
            # fix last label
            filt_parts = []
            for i in range(1, n):
                in_l = "[0]" if i == 1 else f"[a{i-1}]"
                out_l = "[ax]" if i == n - 1 else f"[a{i}]"
                filt_parts.append(f"{in_l}[{i}]acrossfade=d={xfade}:c1=tri:c2=tri{out_l}")
            filt_parts.append(
                f"[ax]volume={BGM_GAIN},afade=t=in:st=0:d={fade_in},afade=t=out:st={max(0, target_s-fade_out)}:d={fade_out},atrim=0:{target_s},aformat=sample_fmts=s16:sample_rates={SR}:channel_layouts=stereo[out]"
            )
            filt_str = ";".join(filt_parts)
        cmd = [str(FFMPEG), "-y", *inputs, "-filter_complex", filt_str, "-map", "[out]", "-c:a", "pcm_s16le", str(out_wav)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            log_stage("04_audio", f"acrossfade failed, keeping stream_loop version: {r.stderr[-300:]}")
    return out_wav


def mix(narr: Path, bgm: Path, out_wav: Path):
    # mono narr -> stereo, mix with bgm; limit true peak roughly
    cmd = [
        str(FFMPEG), "-y", "-i", str(narr), "-i", str(bgm),
        "-filter_complex",
        f"[0:a]aformat=sample_fmts=fltp:sample_rates={SR}:channel_layouts=mono,pan=stereo|c0=c0|c1=c0[nar];"
        f"[1:a]aformat=sample_fmts=fltp:sample_rates={SR}:channel_layouts=stereo[bg];"
        f"[nar][bg]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
        f"alimiter=limit=0.84:attack=5:release=50,aformat=sample_fmts=s16:sample_rates={SR}:channel_layouts=stereo[out]",
        "-map", "[out]", "-c:a", "pcm_s16le", str(out_wav),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:])


def chapter_narration(timeline, section: str, out_wav: Path):
    utts = [u for u in timeline["utterances"] if u["section"] == section]
    if not utts:
        return None
    parts_dir = AUDIO / "chapter_parts" / section
    parts_dir.mkdir(parents=True, exist_ok=True)
    list_file = parts_dir / "concat.txt"
    lines = []
    for i, u in enumerate(utts):
        gap = float(u.get("gap_before_s") or 0)
        # first utterance of chapter should not include inter-chapter gap in chapter-local file
        # but timeline gaps are absolute; for chapter stem use gaps except leading chapter gap
        if i == 0:
            gap = 0.0
        if gap > 0:
            gap_samples = int(round(gap * SR))
            gap_path = parts_dir / f"gap_{i:04d}.wav"
            write_silence_wav(gap_path, gap_samples)
            lines.append(f"file '{gap_path.as_posix()}'")
        lines.append(f"file '{Path(u['path']).as_posix()}'")
    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    cmd = [str(FFMPEG), "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
           "-c:a", "pcm_s16le", "-ar", str(SR), "-ac", "1", str(out_wav)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-500:])
    return out_wav


def main():
    update_checkpoint(stage="audio_subtitles",
                      completed=["create_run", "build_timeline", "build_media_map"],
                      running=["build_audio"], next_action="narration-dry + bgm + mix")
    tl = load_json(RUN / "timeline.json")
    target_s = float(tl["body_total_seconds_audio"])
    narr = AUDIO / "narration-dry.wav"
    log_stage("04_audio", f"building narration-dry target~{target_s:.3f}s")
    concat_narration(tl, narr)
    # per-chapter narration
    for sec in BODY_SECTIONS:
        chapter_narration(tl, sec, AUDIO / f"narration-{sec}.wav")
    bgm = AUDIO / "bgm-stem.wav"
    log_stage("04_audio", "building bgm-stem")
    loop_bgm(target_s, bgm)
    mix_path = AUDIO / "mix-master.wav"
    log_stage("04_audio", "mixing")
    mix(narr, bgm, mix_path)
    # durations
    def dur(p):
        r = subprocess.run([str(FFPROBE), "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", str(p)], capture_output=True, text=True, check=True)
        return float(r.stdout.strip())
    report = {
        "created_at": now_iso(),
        "narration_dry": str(narr),
        "bgm_stem": str(bgm),
        "mix_master": str(mix_path),
        "narration_s": dur(narr),
        "bgm_s": dur(bgm),
        "mix_s": dur(mix_path),
        "bgm_gain_linear": BGM_GAIN,
        "timeline_audio_s": target_s,
    }
    atomic_json(AUDIO / "audio_report.json", report)
    log_stage("04_audio", f"done {report}")
    print("OK audio", report)

if __name__ == "__main__":
    main()