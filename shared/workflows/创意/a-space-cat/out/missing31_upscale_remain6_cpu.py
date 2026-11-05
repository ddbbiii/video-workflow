# -*- coding: utf-8 -*-
from __future__ import annotations
import hashlib, json, time, traceback
from pathlib import Path
import torch
from PIL import Image
from torchvision.transforms.functional import to_tensor, to_pil_image
from spandrel import ImageModelDescriptor, ModelLoader

PICKS = Path(r"E:\program\1project\video\projects\创意\episodes\a-space-cat\qa\missing31_picks.json")
FF = Path(r"E:\program\1project\video\projects\创意\episodes\a-space-cat\image\firstframes")
MODEL = Path(r"C:\Users\10060\agent-tools\shot30\RealESRGAN_x4plus_anime_6B.pth")
LOG = Path(r"E:\program\1project\video\projects\创意\episodes\a-space-cat\logs\missing31_upscale_log.jsonl")
PROTECTED = {2,3,4,8,9,10,13,14,19,21,25,29,30,31,34,38,41,42,45,47}
OUT_SIZE = (1080, 1920)
REMAINING = [44,46,48,49,50,51]

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def center_crop_9_16(img: Image.Image):
    w, h = img.size
    target_ratio = 9 / 16
    cur = w / h
    if abs(cur - target_ratio) < 1e-6:
        return img, [0, 0, w, h]
    if cur > target_ratio:
        new_w = int(round(h * target_ratio))
        left = (w - new_w) // 2
        box = [left, 0, left + new_w, h]
    else:
        new_h = int(round(w / target_ratio))
        top = (h - new_h) // 2
        box = [0, top, w, top + new_h]
    return img.crop(tuple(box)), box

def main():
    picks = json.loads(PICKS.read_text(encoding="utf-8"))
    device = torch.device("cpu")
    print("Loading model on", device, flush=True)
    model = ModelLoader().load_from_file(str(MODEL))
    assert isinstance(model, ImageModelDescriptor)
    model = model.to(device).eval()
    model_sha = sha256_file(MODEL)
    ok = fail = 0
    for n in REMAINING:
        if n in PROTECTED:
            raise SystemExit(f"REFUSE protected {n}")
        entry = picks["shots"][f"{n:02d}"]
        out_path = FF / f"shot{n:02d}.png"
        if out_path.exists():
            print(f"skip existing shot{n:02d}", flush=True)
            continue
        src = Path(entry["picked_path"])
        t_start = time.time()
        try:
            img = Image.open(src).convert("RGB")
            cropped, crop_box = center_crop_9_16(img)
            t0 = to_tensor(cropped).unsqueeze(0).to(device)
            with torch.inference_mode():
                up_t = model(t0).clamp(0, 1).cpu()
            up = to_pil_image(up_t.squeeze(0))
            final = up.resize(OUT_SIZE, Image.Resampling.LANCZOS)
            tmp = out_path.with_suffix(".png.tmp")
            final.save(tmp, format="PNG")
            tmp.replace(out_path)
            meta = {
                "ok": True, "shot": n, "pick": entry["pick"], "src": str(src),
                "src_size": list(img.size), "fit": "crop", "crop_box": crop_box,
                "method": "realesrgan-anime", "model": MODEL.name, "model_sha256": model_sha,
                "intermediate": list(up.size), "out": str(out_path), "out_size": list(final.size),
                "device": "cpu", "sec": round(time.time()-t_start,1),
                "bytes": out_path.stat().st_size, "reason": entry["reason"], "resume": "cpu_after_gpu_oom",
            }
            with LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(meta, ensure_ascii=False) + "\n")
            ok += 1
            print(f"OK shot{n:02d} pick={entry['pick']} {meta['sec']}s", flush=True)
        except Exception as e:
            meta = {"ok": False, "shot": n, "error": str(e), "trace": traceback.format_exc()}
            with LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(meta, ensure_ascii=False) + "\n")
            fail += 1
            print(f"FAIL shot{n:02d}: {e}", flush=True)
    print(f"ALLDONE ok={ok} fail={fail}", flush=True)

if __name__ == "__main__":
    main()
