"""Memory-bounded RealBasicVSR inference for one video.

ModelScope's stock pipeline concatenates all 4x outputs before writing them.
This runner keeps the same model and temporal chunk size, but writes each
chunk immediately so long/high-resolution clips do not exhaust CPU memory.
"""
import gc
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import cv2
import numpy as np
import torch
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
INPUT = PROJECT / "projects/助眠解说/legacy-source/zhumian/b-geomagnetic-reversal/gen_rebuild/runs/20261007-ltx-cinematic-retry-c04"
OUTPUT = Path(os.environ.get("VSR_OUTPUT_DIR", str(INPUT.parent / "20261007-vsr-baseline-c04-streaming")))
MODEL_ID = "damo/cv_realbasicvsr_video-super-resolution_videolq"
VIDEO = INPUT / "ch1-c04-v2-01-raw-1280x704.mp4"
BASELINE = INPUT / "ch1-c04-v2-01-1920x1080-hq.mp4"
FFMPEG = shutil.which("ffmpeg") or r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"
CHUNK_SIZE = int(os.environ.get("VSR_CHUNK_SIZE", "2"))
TILE_H = int(os.environ["VSR_TILE_H"]) if "VSR_TILE_H" in os.environ else None
TILE_W = int(os.environ["VSR_TILE_W"]) if "VSR_TILE_W" in os.environ else None
TILE_OVERLAP = int(os.environ.get("VSR_TILE_OVERLAP", "32"))
MAX_FRAMES = int(os.environ.get("VSR_MAX_FRAMES", "0"))


def run(cmd):
    subprocess.run(cmd, check=True)


def _starts(length, tile, overlap):
    if tile >= length:
        return [0]
    step = max(1, tile - overlap)
    values = list(range(0, length - tile + 1, step))
    if values[-1] != length - tile:
        values.append(length - tile)
    return values


def _blend_window(height, width, overlap, device):
    # A small non-zero floor avoids seams while keeping the center dominant.
    edge = max(1, overlap)
    wy = torch.ones(height, device=device)
    wx = torch.ones(width, device=device)
    ramp_y = torch.linspace(1.0 / (edge + 1), 1.0, edge, device=device)
    ramp_x = torch.linspace(1.0 / (edge + 1), 1.0, edge, device=device)
    wy[:edge] = ramp_y
    wy[-edge:] = torch.flip(ramp_y, dims=[0])
    wx[:edge] = ramp_x
    wx[-edge:] = torch.flip(ramp_x, dims=[0])
    return (wy[:, None] * wx[None, :])[None, None]


def infer_spatial_tiles(model, tensor, device):
    """Run a temporal chunk as overlapping spatial tiles and blend x4 output."""
    _, frames, channels, height, width = tensor.shape
    scale = 4
    out_h, out_w = height * scale, width * scale
    accum = torch.zeros((1, frames, channels, out_h, out_w), device=device)
    weights = torch.zeros((1, frames, 1, out_h, out_w), device=device)
    ys = _starts(height, TILE_H, TILE_OVERLAP)
    xs = _starts(width, TILE_W, TILE_OVERLAP)
    with torch.inference_mode():
        for y in ys:
            for x in xs:
                tile = tensor[:, :, :, y:y + min(TILE_H, height), x:x + min(TILE_W, width)]
                th, tw = tile.shape[-2:]
                pad_h = (8 - th % 8) % 8
                pad_w = (8 - tw % 8) % 8
                if pad_h or pad_w:
                    tile = torch.nn.functional.pad(tile, (0, pad_w, 0, pad_h), mode="reflect")
                result = model._inference_forward(tile)["output"].clamp(0, 1)
                result = result[..., :th * scale, :tw * scale]
                window = _blend_window(th * scale, tw * scale, TILE_OVERLAP * scale, device)
                oy, ox = y * scale, x * scale
                accum[..., oy:oy + th * scale, ox:ox + tw * scale] += result * window
                weights[..., oy:oy + th * scale, ox:ox + tw * scale] += window
                del tile, result, window
    return accum / weights.clamp_min(1e-6)


def configure_tiles(device):
    """Choose conservative tiles from VRAM unless the operator overrides them."""
    global TILE_H, TILE_W
    if TILE_H is not None and TILE_W is not None:
        return
    if device.type != "cuda":
        TILE_H, TILE_W = 176, 320
        return
    vram_gb = torch.cuda.get_device_properties(device).total_memory / (1024 ** 3)
    if vram_gb <= 10:
        TILE_H, TILE_W = 176, 320
    elif vram_gb <= 18:
        TILE_H, TILE_W = 352, 640
    else:
        TILE_H, TILE_W = 512, 768


def main():
    if not VIDEO.exists() or not BASELINE.exists():
        raise FileNotFoundError("source or Lanczos baseline is missing")
    OUTPUT.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    configure_tiles(device)
    manifest = {"id": "zhumian-vsr-baseline-c04-streaming-20261007", "model": MODEL_ID,
                "input": str(VIDEO), "baseline": str(BASELINE),
                "output_directory": str(OUTPUT), "chunk_size": CHUNK_SIZE,
                "spatial_tiling": {"tile_h": TILE_H, "tile_w": TILE_W, "overlap": TILE_OVERLAP},
                "max_frames": MAX_FRAMES, "status": "running"}
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    pipe = pipeline(Tasks.video_super_resolution, model=MODEL_ID)
    # ModelScope may leave the model wrapper on CPU even when CUDA is visible.
    # Move the actual model explicitly so input and weights share one device.
    pipe.model.to(device)
    pipe.model.eval()
    cap = cv2.VideoCapture(str(VIDEO))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    sr_raw = OUTPUT / "ch1-c04-v2-01-realbasicvsr-streaming-raw.mp4"
    writer = None
    frames = 0
    chunk = []
    with torch.inference_mode():
        while True:
            ok, frame = cap.read()
            if ok and MAX_FRAMES and frames + len(chunk) >= MAX_FRAMES:
                ok = False
            if ok:
                chunk.append(frame)
            if len(chunk) < CHUNK_SIZE and ok:
                continue
            if not chunk:
                break
            rgb = np.stack([f[:, :, ::-1] for f in chunk]).astype(np.float32) / 255.0
            tensor = torch.from_numpy(rgb).permute(0, 3, 1, 2).unsqueeze(0).to(device)
            output = infer_spatial_tiles(pipe.model, tensor, device).cpu()
            for i in range(output.shape[1]):
                image = (output[0, i].permute(1, 2, 0).numpy() * 255.0).round().astype(np.uint8)
                image = image[:, :, ::-1]
                if writer is None:
                    h, w = image.shape[:2]
                    writer = cv2.VideoWriter(str(sr_raw), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
                    if not writer.isOpened():
                        raise RuntimeError("cannot open VSR output writer")
                writer.write(image)
                frames += 1
            del tensor, output, rgb, chunk
            chunk = []
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            if not ok:
                break
    cap.release()
    if writer is not None:
        writer.release()
    if frames == 0:
        raise RuntimeError("no frames were produced")

    sr_hq = OUTPUT / "ch1-c04-v2-01-realbasicvsr-streaming-1920x1080.mp4"
    run([FFMPEG, "-v", "error", "-y", "-i", str(sr_raw), "-i", str(VIDEO), "-map", "0:v:0", "-map", "1:a?", "-vf", "scale=1920:1080:flags=lanczos,setsar=1", "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(sr_hq)])
    for path in (VIDEO, BASELINE, sr_raw, sr_hq):
        run([FFMPEG, "-v", "error", "-i", str(path), "-f", "null", "-"])
    manifest.update({"status": "completed", "frames": frames, "fps": fps,
                     "realbasicvsr_raw": str(sr_raw), "realbasicvsr_1920x1080": str(sr_hq),
                     "audio_source": str(VIDEO), "decode_ok": True, "elapsed_s": round(time.monotonic() - started, 1),
                     "visual_qa": "pending_playback"})
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    lock = PROJECT / "shared/work/cache/gpu.lock"
    if (PROJECT / "shared/runtime/comfy/cache/gpu.lock").exists():
        raise RuntimeError("Shared GPU lock exists")
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("x", encoding="utf-8") as handle:
        json.dump({"owner": "zhumian-vsr-baseline-c04-streaming-20261007", "pid": os.getpid()}, handle)
    try:
        main()
    finally:
        if lock.exists() and json.loads(lock.read_text(encoding="utf-8")).get("pid") == os.getpid():
            lock.unlink()
