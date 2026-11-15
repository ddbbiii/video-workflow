# -*- coding: utf-8 -*-
"""悬疑线「生图」小批试生：8 张静帧样图（A 环境空镜 / B 人物中景 / C 证据特写 / D 空间异常）。

规则来源（不在这里手写风格块，避免与规则漂移）：
- `rules/悬疑/visual.md` §二 STYLE_POS / STYLE_NEG / CEL_BOOST 整段解析；
- §4.2 逐镜提示词顺序 = STYLE_POS (+CEL_BOOST) → 构图语法 → 主体与姿态 → 三层物件 → 光线 →
  证据位置与占比 → 本镜禁止项 → `Avoid: STYLE_NEG`；
- §三 每镜 ≥2 损耗 + ≥1 生活痕迹，写在前景/焦平面；
- 通道路由读 `shared/image-api/channel-policy.json` 的 active 策略，不写死通道。

产物：raw/（原图+响应）、crops/（100% 裁切）、anchors/（人物镜参考图）、
manifest.json、contact-sheet.png、REPORT.md。
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
import uuid
import winreg
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
RULES = REPO / "rules" / "悬疑" / "visual.md"
POLICY = REPO / "shared" / "image-api" / "channel-policy.json"
CHARS = REPO / "assets" / "悬疑" / "characters"
UA = "OpenAI/Python/1.60.0"
TIMEOUT_S = 900
RAW, CROPS, ANCH = HERE / "raw", HERE / "crops", HERE / "anchors"
MAX_ATTEMPTS = 2

# 人物锚点：按镜选参考格，拼成横排参考图（不喂 2×2 拼版，避免模型照抄网格）
ANCHORS = {
    "zhouxu": {
        "front": CHARS / "zhouxu-20261110-pool" / "front.png",
        "side": CHARS / "zhouxu-20261110-pool" / "side.png",
        "back": CHARS / "zhouxu-20261110-pool" / "back.png",
        "face": CHARS / "zhouxu-20261110-pool" / "face.png",
    },
}

CHAR_PREAMBLE = (
    "Character reference sheet attached: the same character shown from several angles, same outfit. "
    "Keep his exact design — thin 14-year-old Chinese boy, short slightly messy black hair with a side part, "
    "narrow dark brown eyes, straight brows, low nose bridge, thin lips, fair skin, navy-blue zip-up school "
    "jacket with white piping, white crew-neck T-shirt, grey straight trousers, white canvas sneakers, "
    "no glasses, no backpack, no accessories. Render ONE new single scene as described below; do not redraw "
    "the reference sheet, do not repeat its layout, no panels, no multiple views, no text."
)

SHOTS = [
    # ---------------- A 环境空镜（无人物） ----------------
    {
        "tag": "A1", "kind": "A 环境空镜", "shot_type": "E", "scene_id": "corridor-4f",
        "title": "老楼道：四层走廊，尽头窗",
        "character_ids": [], "evidence_id": "",
        "anchor": "",
        "comp": ("camera: medium position, eye level, standing at the stair landing looking down the corridor; "
                 "lens: 24mm wide-angle, deep focus, near and far both readable; "
                 "composition: the corridor recedes along the right third line, off-center, never symmetrical; "
                 "foreground: a rusted steel door frame and the peeling dark-green edge of its door press the left quarter"),
        "subject": ("no people, an empty fourth-floor corridor of an old six-storey walk-up in a southern Chinese city"),
        "layers": ("foreground: the door frame with a strip of grey duct tape across its corner; "
                   "middle ground: a yellowed plastic stool beside a taped-over electrical junction box, a folded drying "
                   "rack with two dark shirts hanging on it; "
                   "background: the far window at the corridor end, its frame swollen and repainted three times, cold grey "
                   "dusk light beyond it"),
        "decay": ("peeling green paint along the skirting, a dark water stain spreading down from the window frame, rust "
                  "bleeding from the door hinge, scuffed skirting board"),
        "light": ("cold grey window light from the far end, one single warm practical light leaking under one closed door "
                  "on the left as the only warm spot in frame"),
        "evidence": "",
        "ban": ("no people, no readable text, no printed signs, no door numbers, no posters, no UI, no glitch bars"),
    },
    {
        "tag": "A2", "kind": "A 环境空镜", "shot_type": "E", "scene_id": "room-rental-302",
        "title": "出租屋室内：折叠桌、床、窗",
        "character_ids": [], "evidence_id": "",
        "anchor": "",
        "comp": ("camera: medium position, slightly low, from the doorway looking into the room; "
                 "lens: 24mm wide-angle, deep focus; "
                 "composition: the bed sits on the right third line, the door opening on the left, off-center; "
                 "foreground: a faded floral fabric door curtain hangs on the left edge, its hem taped to the frame, "
                 "pressing the left fifth"),
        "subject": "no people, one rented single room, lived in",
        "layers": ("foreground: the curtain hem and two strips of clear repair tape on the frame; "
                   "middle ground: a folding square table with two upside-down bowls and a stainless thermos, a plastic "
                   "stool pushed under it, one pair of worn slippers beside the bed; "
                   "background: a steel-framed window with a clothes-hanging rod outside, cold overcast light through "
                   "dusty glass"),
        "decay": ("wallpaper lifting in a corner above the bed, cracked tile at the threshold, a ring of water stain "
                  "around the window sill"),
        "light": ("cold overcast window light from the right, one single warm desk lamp on the table as the only warm spot"),
        "evidence": "",
        "ban": ("no people, no readable text, no wall calendar, no posters, no packaging with lettering, no UI"),
    },
    # ---------------- B 人物中景（周叙） ----------------
    {
        "tag": "B1", "kind": "B 人物中景", "shot_type": "M", "scene_id": "room-rental-302",
        "title": "门口：周叙侧背身扶门框，往屋内看",
        "character_ids": ["zhouxu-20261110-pool"], "evidence_id": "",
        "anchor": "zhouxu:front,side,face",
        "comp": ("camera: medium position, eye level, from the corridor four metres back, the whole door frame visible "
                 "from floor to top; "
                 "lens: 28mm wide-angle, deep focus; "
                 "composition: he stands in the doorway on the left third line, the hall behind him readable, the door "
                 "frame about half the frame height and the boy about one third of the frame height — his height about "
                 "0.6 of the door height, not centered, not shrunk; "
                 "foreground: a hanging plaid curtain on the right edge presses the right quarter"),
        "subject": ("one person, a thin 14-year-old Chinese boy in a navy zip-up school jacket with white piping, grey "
                    "straight trousers and white canvas sneakers, standing in the doorway seen from behind and side, his right "
                    "hand on the door frame, head turned slightly toward the dark room, face not fully visible"),
        "layers": ("foreground: the door frame edge and the curtain, both in sharp focus; "
                   "middle ground: the boy, the scuffed door leaf with a taped repair along its edge, a pair of slippers "
                   "just inside the threshold; "
                   "background: the dark hallway inside with one bathroom door ajar, cold light from a small window beyond"),
        "decay": "peeling paint on the door frame, a water stain on the wall beside it, a chipped tile at the threshold",
        "light": ("cold corridor light from behind him, one single warm light from the half-open bathroom door as the only "
                  "warm spot"),
        "evidence": "",
        "ban": ("no readable text, no badges, no lettering on the jacket, no extra people, no UI"),
    },
    {
        "tag": "B2", "kind": "B 人物中景", "shot_type": "M", "scene_id": "corridor-4f",
        "title": "走廊尽端：周叙背影，望向半开的安全门",
        "character_ids": ["zhouxu-20261110-pool"], "evidence_id": "",
        "anchor": "zhouxu:back,side,face",
        "comp": ("camera: far position, eye level, from the far end of the same corridor; "
                 "lens: 24mm wide-angle, deep focus; "
                 "composition: he stands on the right third line near the corridor end, his height about 0.6 of the door "
                 "height, not centered; "
                 "foreground: a laundry pole with two dark garments crosses the top left, a metal railing clips the bottom "
                 "left corner"),
        "subject": ("one person, the same thin 14-year-old Chinese boy in the navy school jacket, grey trousers and white "
                    "canvas sneakers, back three-quarters to camera, looking toward the half-open steel safety door"),
        "layers": ("foreground: the laundry pole, the hanging garments and the railing, all in sharp focus; "
                   "middle ground: the boy, a stack of cardboard boxes and a plastic stool against the wall; "
                   "background: the half-open steel safety door at the corridor end, cold light beyond it, the stairwell "
                   "edge further out"),
        "decay": ("peeling wall paint, a long water stain along the ceiling edge, rust on the electrical meter box"),
        "light": ("cold light through the safety door, one single warm bulb above a door on the left as the only warm spot"),
        "evidence": "",
        "ban": ("no readable text, no signs, no lettering on the boxes, no extra people, no UI"),
    },
    # ---------------- C 证据特写（CEL_BOOST） ----------------
    {
        "tag": "C1", "kind": "C 证据特写", "shot_type": "C", "scene_id": "room-rental-302",
        "title": "桌面证据：黄铜钥匙 + 褪色红绳",
        "character_ids": [], "evidence_id": "TEST-KEY-01",
        "anchor": "",
        "comp": ("camera: close position, camera slightly above table height, looking down from the window side; "
                 "lens: 28mm wide-angle, deep focus; "
                 "composition: the key lies on the left third line, off-center, the key itself at least one sixth of the "
                 "frame width; "
                 "foreground: the corner of a woven placemat and the table edge press the bottom right"),
        "subject": ("one old brass door key with a worn bow and a short length of faded red cord tied through it, lying alone "
                    "on the table, no people"),
        "layers": ("foreground: the placemat corner and the table edge in sharp focus; "
                   "middle ground: the bare wooden table top with a ring-shaped water stain and a cigarette burn, a single "
                   "chipped enamel mug; "
                   "background: the dark kitchen doorway with one cold window beyond"),
        "decay": ("scratched and water-ringed table top, cracked floor tile behind, chipped enamel on the mug"),
        "light": ("cold grey window light from the right, one single warm bulb above the table as the only warm spot"),
        "evidence": ("the evidence is the brass key: it sits at the left third line, fully visible, uncovered by foreground, "
                     "at least one sixth of the frame width"),
        "ban": ("no readable text, no engraving, no numbers, no label on the key, no UI"),
    },
    {
        "tag": "C2", "kind": "C 证据特写", "shot_type": "C", "scene_id": "room-rental-302",
        "title": "手部持物：周叙的手捏着同一把钥匙",
        "character_ids": ["zhouxu-20261110-pool"], "evidence_id": "TEST-KEY-02",
        "anchor": "zhouxu:front,face",
        "comp": ("camera: close position, slightly above, looking down; "
                 "lens: 28mm wide-angle, deep focus; "
                 "composition: the hand enters from the bottom right, the key held up between thumb and forefinger at the "
                 "right third line, the key itself at least one quarter of the frame width, off-center; "
                 "foreground: the edge of the fabric curtain presses the top left corner"),
        "subject": ("one hand, the right hand of the same 14-year-old boy, fair skin, short clean nails, holding the old "
                    "brass key between thumb and forefinger, the key long and clearly shaped with its bow and teeth fully "
                    "visible, the back of the hand toward camera, forearm entering from the bottom right"),
        "layers": ("foreground: the curtain edge in sharp focus; "
                   "middle ground: the hand and the large key, the scratched table top, a stainless thermos lying on its side; "
                   "background: the dark kitchen doorway"),
        "decay": ("water stains on the table, a taped repair on the table edge, chipped enamel on the thermos"),
        "light": ("cold window light from the left, one single warm bulb above the hand as the only warm spot"),
        "evidence": ("the evidence is the key between his fingers: at the right third line, at least one quarter of the frame "
                     "width, uncovered, large in frame"),
        "ban": ("no readable text, no engraving, no numbers, no rings, no nail polish, no extra fingers, no tiny key, no UI"),
    },
    # ---------------- D 空间异常（固定机位长镜） ----------------
    {
        "tag": "D1", "kind": "D 空间异常", "shot_type": "E", "scene_id": "corridor-4f",
        "title": "走廊尽头：本该是窗，却是一道半开的门，门后又是同一条走廊",
        "character_ids": [], "evidence_id": "",
        "anchor": "",
        "comp": ("camera: far position, locked-off tripod at chest height, facing the corridor end, the corridor axis "
                 "sits left of centre; "
                 "lens: 28mm wide-angle, deep focus; "
                 "composition: the corridor recedes along the left third, the right third blocked by the railing, never "
                 "symmetrical; "
                 "foreground: a rusted iron railing and a rolled bamboo blind leaning at the right edge press the right quarter"),
        "subject": ("no people, a fixed wide shot down an old corridor"),
        "layers": ("foreground: the railing and the rolled blind in sharp focus; "
                   "middle ground: worn floor tiles, a mop leaning against the wall, a plastic bucket; "
                   "background: at the corridor end, where a window should be, a door stands wide open, and through it the "
                   "same corridor continues — the same tiled floor, the same four doors on the same sides, another window at "
                   "its far end with cold light beyond, an impossible second corridor"),
        "decay": ("cracked floor tiles, a long water stain on the ceiling, scuffed skirting"),
        "light": ("cold daylight from the far end of the duplicate corridor, one single warm light at the left door crack as "
                  "the only warm spot"),
        "evidence": "",
        "ban": ("no people, no shadow of a person, no monster, no glitch bars, no readable text, no door numbers, no meter "
                "boxes, no name plates, no labels, no UI"),
    },
    {
        "tag": "D2", "kind": "D 空间异常", "shot_type": "E", "scene_id": "stairwell",
        "title": "楼梯井：井底平台没有门，却摆着一把凳子和一只碗",
        "character_ids": [], "evidence_id": "",
        "anchor": "",
        "comp": ("camera: far position, locked-off tripod at chest height, at the fifth-floor landing looking down into the "
                 "stairwell; "
                 "lens: 24mm wide-angle, deep focus; "
                 "composition: the stairwell falls along the right third, the left third is railing and a drying cloth, "
                 "off-center; "
                 "foreground: the steel handrail and a towel hanging over it press the left quarter"),
        "subject": "no people, looking straight down an old apartment stairwell",
        "layers": ("foreground: the handrail and the towel in sharp focus; "
                   "middle ground: concrete steps with chipped nosing, a wall-mounted meter box, a mop; "
                   "background: the bottom landing, where a single plastic stool faces the wall with an empty bowl on it, and "
                   "that landing has no door at all"),
        "decay": ("chipped step edges, water stains running down the wall, rust on the handrail"),
        "light": ("cold grey light falling down the well from above, one single warm bulb on the fifth-floor wall as the only "
                  "warm spot"),
        "evidence": "",
        "ban": ("no people, no blood, no graffiti, no readable text, no glitch bars, no UI"),
    },
]


# ---------------- 基础工具 ----------------

def read_block(name: str) -> str:
    text = RULES.read_text(encoding="utf-8")
    match = re.search(rf"(?m)^`{name}`[^\n]*\n\s*```text\s*(.*?)```", text, re.S)
    if not match:
        raise SystemExit(f"找不到 {name} 块：{RULES}")
    return re.sub(r"\s+", " ", match.group(1)).strip()


def key_for(env_name: str) -> str:
    value = os.environ.get(env_name, "").strip()
    if value:
        return value
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, env_name)[0]


def active_channel() -> dict:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    name = policy["active"]
    route = policy["policies"][name]
    channel = dict(policy["channels"][route["default_channel"]])
    channel["name"] = route["default_channel"]
    channel["policy"] = name
    return channel


def font(size: int) -> ImageFont.FreeTypeFont:
    for path in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\arial.ttf"):
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def lap_var(gray: np.ndarray) -> float:
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1]
           + gray[1:-1, :-2] + gray[1:-1, 2:])
    return float(lap.var())


def download(url: str, dest: Path) -> None:
    curl = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "curl.exe"
    if curl.exists():
        result = subprocess.run(
            [str(curl), "-L", "--retry", "3", "--retry-delay", "2", "--max-time", "300",
             "-A", UA, "-o", str(dest), url], capture_output=True, text=True)
        if result.returncode == 0 and dest.exists() and dest.stat().st_size > 0:
            return
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=300) as resp:
        dest.write_bytes(resp.read())


def multipart(fields: dict[str, str], files: dict[str, Path]) -> tuple[bytes, str]:
    boundary = "----dsh" + uuid.uuid4().hex
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for name, path in files.items():
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
                      f'filename="{path.name}"\r\nContent-Type: {ctype}\r\n\r\n'.encode())
        chunks.append(path.read_bytes())
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def build_anchor(spec: str) -> Path:
    """把 `zhouxu:front,side,face` 拼成一张横排参考图（人物镜喂同一套锚点）。"""
    char_id, views = spec.split(":")
    files = [ANCHORS[char_id][v.strip()] for v in views.split(",")]
    height = 640
    tiles = []
    for path in files:
        with Image.open(path) as img:
            rgb = img.convert("RGB")
            tiles.append(rgb.resize((int(rgb.width * height / rgb.height), height), Image.LANCZOS))
    canvas = Image.new("RGB", (sum(t.width for t in tiles) + 20 * (len(tiles) - 1), height), (40, 40, 44))
    x = 0
    for tile_img in tiles:
        canvas.paste(tile_img, (x, 0))
        x += tile_img.width + 20
    out = ANCH / f"{char_id}-{'-'.join(v.strip() for v in views.split(','))}.png"
    canvas.save(out)
    return out


def assemble(pos: str, cel: str, shot: dict) -> str:
    parts = [pos]
    if shot["character_ids"] and shot["anchor"]:
        parts.append(CHAR_PREAMBLE)
    if shot["shot_type"] == "C" or shot["character_ids"]:
        parts.append(cel)
    parts += [shot["comp"], f"subject: {shot['subject']}", f"layers: {shot['layers']}",
              f"decay: {shot['decay']}", f"light: {shot['light']}"]
    if shot["evidence"]:
        parts.append(f"evidence: {shot['evidence']}")
    parts.append(f"hard constraints: {shot['ban']}")
    return ", ".join(parts)


# ---------------- 调用 ----------------

def call(channel: dict, prompt: str, shot: dict, anchor: Path | None, attempt: int) -> dict:
    stem = f"{shot['tag']}-a{attempt}"
    if anchor:
        body, ctype = multipart(
            {"model": channel["model"], "prompt": prompt, "size": channel["size"], "n": "1"},
            {"image": anchor})
        url = f"{channel['base_url']}/images/edits"
    else:
        body = json.dumps({"model": channel["model"], "prompt": prompt,
                           "size": channel["size"], "n": 1}, ensure_ascii=False).encode("utf-8")
        ctype = "application/json"
        url = f"{channel['base_url']}/images/generations"
    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Authorization": f"Bearer {key_for(channel['key_env'])}",
                 "Content-Type": ctype, "Accept": "application/json", "User-Agent": UA})
    started = time.time()
    info = {"shot": shot["tag"], "channel": channel["name"], "attempt": attempt,
            "endpoint": "edits" if anchor else "generations", "prompt": prompt,
            "request_size": channel["size"], "price_cny": channel["price_cny"]}
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read()
    except Exception as exc:  # noqa: BLE001
        info.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        return info
    info["http_status"] = status
    info["elapsed_s"] = round(time.time() - started, 1)
    (RAW / f"{stem}-response.json").write_bytes(raw)
    if status != 200:
        info["ok"] = False
        try:
            info["error"] = json.loads(raw.decode("utf-8"))
        except Exception:
            info["error"] = raw[:400].decode("utf-8", "replace")
        return info
    payload = json.loads(raw.decode("utf-8"))
    item = (payload.get("data") or [{}])[0]
    png = RAW / f"{shot['tag']}.png" if attempt == 1 else RAW / f"{shot['tag']}-a{attempt}.png"
    try:
        if item.get("b64_json"):
            png.write_bytes(base64.b64decode(item["b64_json"]))
            info["delivery"] = "b64_json"
        elif item.get("url"):
            info["delivery"] = "url"
            download(item["url"], png)
        else:
            raise ValueError("no b64_json / url")
    except Exception as exc:  # noqa: BLE001
        info.update({"ok": False, "error": f"download: {type(exc).__name__}: {exc}"})
        return info
    with Image.open(png) as image:
        image.load()
        info["dims"] = list(image.size)
        rgb = image.convert("RGB")
    info["sha256"] = hashlib.sha256(png.read_bytes()).hexdigest()
    info["ok"] = True
    info["file"] = str(png.relative_to(HERE)).replace("\\", "/")
    return info


def measure(path: Path) -> dict:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
    gray = np.asarray(rgb.convert("L"), dtype=np.float64)
    hsv = np.asarray(rgb.convert("HSV"), dtype=np.float64)
    delivery = np.asarray(rgb.resize((1920, 1080), Image.LANCZOS).convert("L"), dtype=np.float64)
    width, height = rgb.size
    crop_w, crop_h = min(1400, width), min(788, height)
    box = ((width - crop_w) // 2, (height - crop_h) // 2, (width + crop_w) // 2, (height + crop_h) // 2)
    rgb.crop(box).save(CROPS / f"{path.stem}-c100.png")
    return {"std_lum": round(float(gray.std()), 1),
            "mean_lum": round(float(gray.mean()), 1),
            "mean_sat": round(float(hsv[:, :, 1].mean()), 1),
            "lap_var": round(lap_var(gray), 1),
            "delivery_lap_var": round(lap_var(delivery), 1)}


def gate(info: dict, channel: dict) -> list[str]:
    problems = []
    size = channel["size"]
    if "x".join(map(str, info.get("dims", []))) != size:
        problems.append(f"size {info.get('dims')} != {size}")
    metrics = info.get("metrics") or {}
    if metrics.get("std_lum", 0) < 18:
        problems.append(f"std_lum {metrics.get('std_lum')} < 18")
    if metrics.get("lap_var", 0) < 60:
        problems.append(f"lap_var {metrics.get('lap_var')} < 60")
    if metrics.get("delivery_lap_var", 0) < 15:
        problems.append(f"delivery_lap_var {metrics.get('delivery_lap_var')} < 15")
    return problems


def tile(path: Path, width: int, height: int, caption: str) -> Image.Image:
    canvas = Image.new("RGB", (width + 16, height + 56), (16, 16, 18))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 6), caption, fill=(235, 235, 235), font=font(22))
    if path.exists():
        with Image.open(path) as image:
            canvas.paste(image.convert("RGB").resize((width, height), Image.LANCZOS), (8, 48))
    else:
        draw.text((16, 70), "NO IMAGE", fill=(230, 120, 120), font=font(28))
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default="", help="只跑指定镜号，逗号分隔")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    only = {x.strip() for x in args.only.split(",") if x.strip()}

    pos, neg, cel = read_block("STYLE_POS"), read_block("STYLE_NEG"), read_block("CEL_BOOST")
    channel = active_channel()
    for directory in (RAW, CROPS, ANCH):
        directory.mkdir(parents=True, exist_ok=True)

    manifest_path = HERE / "manifest.json"
    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.setdefault("shots", {})

    todo = [s for s in SHOTS if not only or s["tag"] in only]
    print(f"channel={channel['name']} policy={channel['policy']} size={channel['size']} "
          f"price={channel['price_cny']} shots={len(todo)}", flush=True)

    def run(shot: dict) -> dict:
        anchor = build_anchor(shot["anchor"]) if shot["anchor"] else None
        prompt = assemble(pos, cel, shot)
        attempts = []
        for attempt in range(1, MAX_ATTEMPTS + 1):
            info = call(channel, prompt, shot, anchor, attempt)
            if info.get("ok"):
                info["metrics"] = measure(RAW / Path(info["file"]).name)
                info["qa"] = gate(info, channel)
            attempts.append(info)
            print(f"  {shot['tag']} a{attempt}: {'OK' if info.get('ok') else 'FAIL'} "
                  f"{info.get('elapsed_s', '-')}s {info.get('dims', '')} {info.get('qa', info.get('error', ''))}", flush=True)
            if info.get("ok") and not info.get("qa"):
                break
        ok = [a for a in attempts if a.get("ok") and not a.get("qa")]
        best = ok[0] if ok else next((a for a in attempts if a.get("ok")), attempts[-1])
        return {
            "tag": shot["tag"], "kind": shot["kind"], "title": shot["title"],
            "shot_type": shot["shot_type"], "scene_id": shot["scene_id"],
            "character_ids": shot["character_ids"], "evidence_id": shot["evidence_id"],
            "anchor": shot["anchor"], "channel": channel["name"], "policy": channel["policy"],
            "attempts": len(attempts), "fallback_from": "", "pass": bool(ok),
            "qa": best.get("qa", []), "metrics": best.get("metrics"),
            "dims": best.get("dims"), "file": best.get("file"), "sha256": best.get("sha256"),
            "prompt": attempts[0]["prompt"], "attempt_log": [
                {k: a.get(k) for k in ("attempt", "ok", "http_status", "elapsed_s", "dims", "qa", "error")}
                for a in attempts],
        }

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for record in pool.map(run, todo):
            manifest["shots"][record["tag"]] = record

    manifest.update({
        "run": HERE.name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "channel_policy": channel["policy"],
        "channel": channel["name"],
        "style_pos": pos, "style_neg": neg, "cel_boost": cel,
        "rule": "rules/悬疑/visual.md §二–§四；rules/shared/shot-composition.md §五",
    })
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    # 联系表 4×2
    order = [s["tag"] for s in SHOTS]
    cell_w, cell_h = 760, 428
    canvas = Image.new("RGB", (4 * (cell_w + 16), 2 * (cell_h + 56)), (10, 10, 12))
    for index, tag in enumerate(order):
        path = RAW / f"{tag}.png"
        block = tile(path, cell_w, cell_h, f"{tag} · {manifest['shots'].get(tag, {}).get('title', '')}")
        canvas.paste(block, ((index % 4) * (cell_w + 16), (index // 4) * (cell_h + 56)))
    canvas.save(HERE / "contact-sheet.png")
    print("DONE", HERE, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
