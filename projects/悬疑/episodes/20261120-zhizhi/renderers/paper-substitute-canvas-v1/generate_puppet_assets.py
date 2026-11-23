import base64, json, os, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'puppet-raw-v2'
OUT = ROOT / 'puppet-assets-v2'
RAW.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)
BASE = os.environ.get('IMAGE_API_BASE_URL_XXC', 'https://xxcapi.com/v1')
KEY = os.environ.get('IMAGE_API_KEY_XXC')
MODEL = 'AZ-gpt-image-2.5-sunburst'
if not KEY:
    raise SystemExit('IMAGE_API_KEY_XXC is not set')

STYLE = ('mature 2D cutout animation concept art, hand-inked outlines, restrained cel shading, '
         'cold blue-grey night palette with one warm oil-lamp light, textured handmade paper, '
         'slightly imperfect editorial illustration, cinematic horror storyboard, no text, no watermark')
COMMON = ('same paper effigy design: white folded paper face, black ink-dot eyes, round red cheeks, '
          'black paper hair in a small top knot, red and muted green folded robe, bamboo splints, '
          'visible paper creases and uneven handmade edges, front three-quarter view, isolated on a '
          'perfectly flat pure chroma green background #00ff00, no cast shadow, no other body parts')

PROMPTS = {
  'head': STYLE + '. ' + COMMON + '. ONLY the head, hair and short paper neck, centered and large, clean silhouette.',
  'torso': STYLE + '. ' + COMMON + '. ONLY the torso from shoulders to robe hem, no head, no arms, no legs, centered and large.',
  'upper-arm-r': STYLE + '. ' + COMMON + '. ONLY the right upper arm from shoulder seam to elbow, red sleeve over muted green under-sleeve, bamboo elbow wrap, neutral downward angle, centered and large.',
  'forearm-r': STYLE + '. ' + COMMON + '. ONLY the right forearm from elbow to wrist, muted green paper sleeve with bamboo wrist wrap, neutral downward angle, centered and large.',
  'hand-r': STYLE + '. ' + COMMON + '. ONLY one small paper hand with two simple folded fingers, no arm, centered and large.',
  'bg-bedside': STYLE + '. A NEW close medium shot of the same rural Chinese old-house bedroom: oil lamp and bedside table on the left, paper effigy standing beside the bed but absent from frame, cracked plaster wall, folded quilt, moonlit window edge, strong foreground/middle/background separation, vertical 9:16 composition, no people, no text.',
  'bg-latch': STYLE + '. A NEW close-up shot of the same cracked wooden bedroom door and horizontal iron latch, cold moonlight leaking through the frame, rough plaster and wood grain readable, shallow perspective, vertical 9:16 composition, no people, no text.',
  'bg-face': STYLE + '. A NEW tight atmospheric shot of the bedroom window and hanging woven wall basket behind an empty patch of dark space where a paper face can be composited, moonlight rim, oil-lamp warmth from below, vertical 9:16 composition, no people, no text.'
}

def generate(name, prompt):
    payload = json.dumps({'model': MODEL, 'prompt': prompt, 'size': '1024x1024', 'n': 1}, ensure_ascii=False).encode()
    req = urllib.request.Request(BASE + '/images/generations', data=payload, method='POST', headers={'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json', 'User-Agent': 'OpenAI/Python 1.60.0'})
    with urllib.request.urlopen(req, timeout=180) as resp:
        item = json.loads(resp.read())['data'][0]
    out = RAW / f'{name}.png'
    if item.get('b64_json'):
        out.write_bytes(base64.b64decode(item['b64_json']))
    else:
        with urllib.request.urlopen(item['url'], timeout=600) as resp:
            out.write_bytes(resp.read())
    print(json.dumps({'generated': name, 'path': str(out)}, ensure_ascii=False))

for name, prompt in PROMPTS.items():
    if not (RAW / f'{name}.png').exists():
        generate(name, prompt)
print(json.dumps({'raw': str(RAW), 'next': 'run ffmpeg chromakey on the five puppet parts into puppet-assets-v2'}, ensure_ascii=False))
