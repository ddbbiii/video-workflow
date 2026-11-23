import json
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


HERE = Path(__file__).resolve().parent
EPISODE = HERE.parent.parent
TRACE = json.loads((EPISODE / "simulation" / "trace.json").read_text())
OUTPUT = EPISODE / "video" / "candidates" / "escape-rings-pillow-reversal.mp4"
WIDTH, HEIGHT = TRACE["width"], TRACE["height"]
FPS = TRACE["fps"]
CENTER = TRACE["center"]
RINGS = TRACE["rings"]
STATES = TRACE["states"]
EVENTS = TRACE["events"]
BALL_RADIUS = TRACE["ball_radius"]


def make_background():
    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH]
    dx = xx - CENTER["x"]
    dy = yy - CENTER["y"]
    distance = np.sqrt(dx * dx + dy * dy)
    falloff = np.clip(1 - distance / (HEIGHT * 0.55), 0, 1) ** 2
    base = np.array([9, 12, 18], dtype=np.float32)
    glow = np.array([16, 23, 34], dtype=np.float32)
    rgb = base + falloff[:, :, None] * glow
    return Image.fromarray(np.uint8(np.clip(rgb, 0, 255)), "RGB")


BACKGROUND = make_background()


def draw_ring_glow(frame, ring, angle, gap_width, alpha=105, blur=13):
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    color = tuple(bytes.fromhex(ring["color"].lstrip("#")))
    start = math.degrees(angle + gap_width / 2)
    end = math.degrees(angle + math.tau - gap_width / 2)
    box = (
        CENTER["x"] - ring["radius"],
        CENTER["y"] - ring["radius"],
        CENTER["x"] + ring["radius"],
        CENTER["y"] + ring["radius"],
    )
    draw.arc(box, start=start, end=end, fill=(*color, alpha), width=ring["thickness"] + 9)
    frame.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))
    solid = ImageDraw.Draw(frame)
    solid.arc(box, start=start, end=end, fill=(*color, 245), width=ring["thickness"])
    inset = ring["thickness"] * 0.22
    inner = (box[0] + inset, box[1] + inset, box[2] - inset, box[3] - inset)
    solid.arc(inner, start=start + 1.5, end=end - 1.5, fill=(236, 247, 255, 140), width=2)


def seeded_unit(seed, index):
    value = (seed ^ ((index + 1) * 0x9E3779B1)) & 0xFFFFFFFF
    value ^= value >> 16
    value = (value * 0x7FEB352D) & 0xFFFFFFFF
    value ^= value >> 15
    value = (value * 0x846CA68B) & 0xFFFFFFFF
    value ^= value >> 16
    return value / 0x100000000


def render_frame(frame_index):
    state = STATES[frame_index]
    frame = BACKGROUND.convert("RGBA")
    alive = set(state["alive_ring_ids"])
    for ring in sorted(RINGS, key=lambda item: item["radius"], reverse=True):
        if ring["id"] not in alive:
            continue
        angle = ring["gap_angle"] + ring["rotate_speed"] * (frame_index / FPS)
        draw_ring_glow(frame, ring, angle, ring.get("gap_width", TRACE.get("gap_width", 0)))

    draw = ImageDraw.Draw(frame, "RGBA")
    for event in EVENTS:
        age = frame_index - event["frame"]
        if age < 0 or age > 20:
            continue
        ring = next(item for item in RINGS if item["id"] == event["ring_id"])
        color = tuple(bytes.fromhex(ring["color"].lstrip("#")))
        is_hit = event.get("type") == "ring_hit"
        life = 10 if is_hit else 20
        if age > life:
            continue
        strength = 1 - age / (life + 1)
        radius = (12 if is_hit else 22) + age * (11 if is_hit else 8)
        draw.arc((event["x"] - radius, event["y"] - radius, event["x"] + radius, event["y"] + radius),
                 start=-26, end=115, fill=(*color, int((170 if is_hit else 110) * strength)), width=max(2, int((8 if is_hit else 6) * strength)))
        for particle in range(7 if is_hit else 9):
            angle = seeded_unit(TRACE["seed"] ^ (event["ring_id"] * 0x9E3779B1) ^ event["frame"], particle) * math.tau
            speed = (16 if is_hit else 9) + seeded_unit(TRACE["seed"] + event["frame"], particle + 19) * (48 if is_hit else 34)
            distance = speed * age * 0.42
            x = event["x"] + math.cos(angle) * distance
            y = event["y"] + math.sin(angle) * distance
            size = max(2, (3.5 + seeded_unit(TRACE["seed"] + event["ring_id"], particle + 38) * 4.5) * strength)
            draw.ellipse((x - size / 2, y - size / 2, x + size / 2, y + size / 2), fill=(*color, int(230 * strength)))

    for offset in range(11, 0, -1):
        prior = STATES[max(0, frame_index - offset)]
        alpha = int((1 - offset / 12) * 56)
        radius = 2.5 + (1 - offset / 11) * 4.5
        x, y = prior["x"], prior["y"]
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(159, 219, 240, alpha))

    x, y = state["x"], state["y"]
    radius = BALL_RADIUS
    for expansion, alpha in ((2.8, 20), (2.0, 27), (1.4, 42)):
        spread = radius * expansion
        draw.ellipse((x - spread, y - spread, x + spread, y + spread), fill=(156, 223, 255, alpha))
    ball_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    ball = ImageDraw.Draw(ball_layer)
    for step in range(24, 0, -1):
        t = step / 24
        inset = radius * (1 - t)
        color = (int(111 + 140 * t), int(141 + 112 * t), int(155 + 100 * t), 255)
        ball.ellipse((x - radius + inset, y - radius + inset, x + radius - inset, y + radius - inset), fill=color)
    ball.ellipse((x - radius * 0.49, y - radius * 0.60, x - radius * 0.18, y - radius * 0.15), fill=(255, 255, 255, 215))
    frame.alpha_composite(ball_layer)
    return frame.convert("RGB")


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-", "-an",
        "-frames:v", str(TRACE["duration_frames"]), "-c:v", "libx264", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUTPUT),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    start = time.perf_counter()
    try:
        for frame_index in range(TRACE["duration_frames"]):
            process.stdin.write(render_frame(frame_index).tobytes())
            if (frame_index + 1) % 100 == 0:
                print(f"Rendered {frame_index + 1}/{TRACE['duration_frames']}", flush=True)
    finally:
        process.stdin.close()
    status = process.wait()
    if status:
        raise SystemExit(status)
    print(json.dumps({"output": str(OUTPUT), "render_seconds": round(time.perf_counter() - start, 2)}))


if __name__ == "__main__":
    main()
