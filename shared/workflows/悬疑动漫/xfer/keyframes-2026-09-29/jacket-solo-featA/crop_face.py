from PIL import Image
from pathlib import Path
src = Path(r"E:\program\1project\video\xfer\charb-jacket-smoke-stylelock-v2\V2-SL1-front-half.png")
out = Path(r"E:\program\1project\video\xfer\keyframes-2026-09-29\jacket-solo-featA\v4-face-jacket-V2-SL1-facecrop.png")
im = Image.open(src).convert("RGB")
w, h = im.size
print("src", w, h)
face = im.crop((int(w * 0.28), int(h * 0.08), int(w * 0.72), int(h * 0.52)))
out.parent.mkdir(parents=True, exist_ok=True)
face.save(out)
print("crop", face.size, "->", out)
