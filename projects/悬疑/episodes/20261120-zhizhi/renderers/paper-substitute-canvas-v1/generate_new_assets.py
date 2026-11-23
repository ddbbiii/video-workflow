import base64, json, os, time, urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent / "new-assets"
OUT.mkdir(parents=True, exist_ok=True)
BASE = os.environ.get("IMAGE_API_BASE_URL_XXC", "https://xxcapi.com/v1")
KEY = os.environ.get("IMAGE_API_KEY_XXC")
MODEL = "AZ-gpt-image-2.5-sunburst"
if not KEY:
    raise SystemExit("IMAGE_API_KEY_XXC is not set")

STYLE = (
    "mature 2D cutout animation concept art, hand-inked clean outlines, restrained cel shading, "
    "cold blue-grey night palette with one warm oil-lamp light, textured painted surfaces, "
    "slightly imperfect editorial illustration, grounded proportions, cinematic 16:9 composition, "
    "no text, no letters, no numbers, no watermark"
)
PROMPTS = {
    "bedroom-new": STYLE + ". A new rural Chinese old-house bedroom at night, no people and no paper figure: rough plaster walls, cracked wooden door with a horizontal latch, moonlit window, old wooden bed in the foreground, small oil lamp on a bedside table, short wooden stool at the foot of the bed, folded quilt, wicker basket, deep corners and readable spatial layers. Wide establishing shot, eye-level camera, leave clear space near the stool.",
    "paper-substitute-new": STYLE + ". A single full-body paper effigy character centered on a completely flat chroma green background (#00ff00), designed for cutout animation: about 45 cm tall, white folded paper face, two black ink-dot eyes, round red cheeks, red and muted green folded paper robe, visible bamboo splints at wrists, elbows and ankles, paper creases and uneven handmade edges, neutral front pose, arms slightly away from body, no shadow cast onto background, no extra characters, no text.",
    "uncle-new": STYLE + ". A single full-body middle-aged Chinese man centered on a completely flat chroma green background (#00ff00), designed for cutout animation: plain dark blue home jacket, loose dark trousers, short black-grey hair, tired face, neutral back-facing pose, arms relaxed, grounded proportions, no shadow cast onto background, no extra characters, no text.",
}

def generate(name, prompt):
    payload = json.dumps({"model": MODEL, "prompt": prompt, "size": "1672x941", "n": 1}, ensure_ascii=False).encode()
    req = urllib.request.Request(BASE + "/images/generations", data=payload, method="POST", headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json", "User-Agent": "OpenAI/Python 1.60.0"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read())
    item = data["data"][0]
    out = OUT / f"{name}.png"
    if item.get("b64_json"):
        out.write_bytes(base64.b64decode(item["b64_json"]))
    else:
        with urllib.request.urlopen(item["url"], timeout=600) as resp:
            out.write_bytes(resp.read())
    print(json.dumps({"name": name, "path": str(out), "bytes": out.stat().st_size}, ensure_ascii=False))

for name, prompt in PROMPTS.items():
    generate(name, prompt)
