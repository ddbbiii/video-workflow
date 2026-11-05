"""Render a silent sentence-card intro from existing video clips (CPU FFmpeg)."""
import argparse
import json
from pathlib import Path
import random
import subprocess
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def render_smooth(source, start, frames, duration, motion, zoom_amount,
                  text, font_path, fade_ms, text_start, text_end, part,
                  width=1280, height=720, fps=30, crf=19, fade_out_ms=1000):
    # Rasterize once at 2x resolution; animate the whole layout, not individual glyphs.
    canvas = Image.new('RGBA', (width * 2, height * 2))
    draw = ImageDraw.Draw(canvas)
    factor = height / 720
    font = ImageFont.truetype(str(font_path), round(144 * factor))
    spacing, stroke = round(30 * factor), round(6 * factor)
    box = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing, stroke_width=stroke)
    pos = ((width * 2 - (box[2] - box[0])) / 2 - box[0],
           (height * 2 - (box[3] - box[1])) / 2 - box[1])
    draw.multiline_text(pos, text, font=font, spacing=spacing, align='center',
                        fill='white', stroke_width=stroke, stroke_fill=(8, 16, 24, 255))
    layer = cv2.resize(np.asarray(canvas), (width, height), interpolation=cv2.INTER_AREA)
    alpha = layer[:, :, 3:4].astype(np.float32) / 255
    premultiplied = np.concatenate((layer[:, :, :3].astype(np.float32) * alpha, alpha), axis=2)
    decoder = subprocess.Popen([
        'ffmpeg', '-v', 'error', '-ss', str(start), '-i', str(source),
        '-vf', f'scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,crop={width}:{height},setsar=1,fps={fps}',
        '-frames:v', str(frames), '-an', '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1'
    ], stdout=subprocess.PIPE)
    encoder = subprocess.Popen([
        'ffmpeg', '-v', 'error', '-n', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
        '-s', f'{width}x{height}', '-r', str(fps), '-i', 'pipe:0', '-an', '-c:v', 'libx264',
        '-preset', 'fast', '-crf', str(crf), '-pix_fmt', 'yuv420p', str(part)
    ], stdin=subprocess.PIPE)
    try:
        for index in range(frames):
            raw = decoder.stdout.read(width * height * 3)
            if len(raw) != width * height * 3:
                raise RuntimeError(f'Source ended at frame {index}: {source}')
            frame = np.frombuffer(raw, np.uint8).reshape(height, width, 3)
            p = index / max(1, frames - 1)
            eased = p * p * (3 - 2 * p)
            zoom = 1 + zoom_amount * (eased if motion == 'push' else 1 - eased)
            if zoom_amount:
                matrix = cv2.getRotationMatrix2D(((width - 1) / 2, (height - 1) / 2), 0, zoom)
                frame = cv2.warpAffine(frame, matrix, (width, height), flags=cv2.INTER_CUBIC,
                                       borderMode=cv2.BORDER_REPLICATE)
            frame = frame.astype(np.float32)
            frame *= 0.88
            scale = (text_start + (text_end - text_start) * eased) / 100
            matrix = cv2.getRotationMatrix2D(((width - 1) / 2, (height - 1) / 2), 0, scale)
            overlay = cv2.warpAffine(premultiplied, matrix, (width, height), flags=cv2.INTER_LINEAR)
            fade_p = min(1, index / fps / max(fade_ms / 1000, 0.001))
            remaining = (frames - 1 - index) / fps
            fade_out_p = min(1, remaining / max(fade_out_ms / 1000, 0.001))
            opacity = (fade_p * fade_p * (3 - 2 * fade_p)
                       * fade_out_p * fade_out_p * (3 - 2 * fade_out_p))
            result = frame * (1 - overlay[:, :, 3:4] * opacity) + overlay[:, :, :3] * opacity
            encoder.stdin.write(np.clip(result, 0, 255).astype(np.uint8).tobytes())
        encoder.stdin.close()
        decoder.stdout.close()
        if decoder.wait() or encoder.wait():
            raise RuntimeError('Video decode/encode failed')
    finally:
        for process in (decoder, encoder):
            if process.poll() is None:
                process.kill()
                process.wait()


def run(args, cwd=None):
    subprocess.run(args, cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    width, height = config.get('resolution', [1280, 720])
    fps = int(config.get('fps', 30))
    crf = int(config.get('crf', 19))
    root = Path(config['workspace'])
    output = root / config['output']
    output.mkdir(parents=True, exist_ok=True)
    candidates = sorted((root / config['clip_directory']).glob('*.mp4'))
    rng = random.Random(config['seed'])
    probes = {}
    selected = []
    for card in config['sentences']:
        remaining = [p for p in candidates if p not in selected]
        rng.shuffle(remaining)
        for candidate in remaining:
            if candidate not in probes:
                probes[candidate] = json.loads(subprocess.check_output([
                    'ffprobe', '-v', 'error', '-show_format', '-show_streams',
                    '-of', 'json', str(candidate)
                ]))
            if float(probes[candidate]['format']['duration']) >= float(card['duration']):
                selected.append(candidate)
                break
        else:
            raise ValueError('No unused video long enough for this sentence')
    fonts = root / 'assets/助眠解说/subtitles/style-r4/fonts'
    parts = []
    records = []
    for i, (source, card) in enumerate(zip(selected, config['sentences']), 1):
        probe = probes[source]
        duration = float(card['duration'])
        frames = round(duration * fps)
        motion = card.get('camera', 'none')
        zoom_amount = float(config.get('camera_zoom', 0))
        fade_ms = int(config.get('text_fade_ms', 1000))
        fade_out_ms = int(config.get('text_fade_out_ms', 1000))
        # Short cards reserve more than one second for fully opaque text.
        fade_budget = max(0, duration - 1.1) * 1000
        if fade_ms + fade_out_ms > fade_budget:
            ratio = fade_budget / max(1, fade_ms + fade_out_ms)
            fade_ms, fade_out_ms = round(fade_ms * ratio), round(fade_out_ms * ratio)
        text_start = float(config.get('text_scale_start', 92))
        text_end = float(config.get('text_scale_end', 104))
        available = float(probe['format']['duration'])
        if available < duration:
            raise ValueError(f'Clip too short: {source}')
        start = min(0.6, (available - duration) / 2)
        text = card['text'].replace('\n', r'\N')
        ass = output / f'card-{i:02}.ass'
        end = f'0:00:{duration:05.2f}'
        ass.write_text(
            '[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n'
            'WrapStyle: 2\nScaledBorderAndShadow: yes\n[V4+ Styles]\n'
            'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n'
            'Style: Intro,Source Han Sans SC Heavy,156,&H00FFFFFF,&H00FFFFFF,&H00181008,&H80000000,0,0,0,0,100,100,0,0,1,3,2,5,140,140,0,1\n'
            '[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
            f'Dialogue: 0,0:00:00.00,{end},Intro,,0,0,0,,{{\\pos(960,540)\\fad({fade_ms},{fade_out_ms})\\fscx{text_start}\\fscy{text_start}\\t(0,{round(duration * 1000)},\\fscx{text_end}\\fscy{text_end})}}{text}\n',
            encoding='utf-8')
        part = output / f'part-{i:02}.mp4'
        render_smooth(source, start, frames, duration, motion, zoom_amount,
                      card['text'], fonts / 'SourceHanSansSC-Heavy.otf',
                      fade_ms, text_start, text_end, part, width, height, fps, crf, fade_out_ms)
        parts.append(part)
        records.append({'source': str(source), 'start': start, **card,
                        'camera': motion, 'camera_zoom': zoom_amount,
                        'text_fade_ms': fade_ms, 'text_fade_out_ms': fade_out_ms,
                        'text_scale': [text_start, text_end],
                        'source_video': [{k: s.get(k) for k in ('width', 'height', 'avg_frame_rate')}
                                         for s in probe['streams'] if s['codec_type'] == 'video']})
    listing = output / 'concat.txt'
    listing.write_text(''.join(f"file '{p.name}'\n" for p in parts), encoding='utf-8')
    final = output / 'sentence-intro-preview.mp4'
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-n', '-f', 'concat', '-safe',
         '0', '-i', listing.name, '-c', 'copy', '-an', '-sn', '-movflags', '+faststart',
         str(final)], cwd=output)
    metadata = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(final)
    ]))
    if any(s['codec_type'] != 'video' for s in metadata['streams']):
        raise ValueError('Preview must contain video only')
    (output / 'manifest.json').write_text(json.dumps({
        'status': 'visual-preview-not-approved', 'seed': config['seed'],
        'output': str(final), 'sources': records, 'probe': metadata,
        'settings': {'resolution': [width, height], 'fps': fps, 'crf': crf,
                     'interpolation': 'none; source frames repeated, transforms evaluated every output frame'},
        'renderer': 'opencv-subpixel-affine-fixed-text-layout-smoothstep',
        'ass_files': 'Reference text/timing only; rendering uses a fixed raster text layer.',
        'note': 'Existing video only; no generated images, audio, or GPU inference.'
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print(final)


if __name__ == '__main__':
    main()
