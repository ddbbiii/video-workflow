# -*- coding: utf-8 -*-
"""Resume remaining missing31 upscales on CUDA if available."""
from __future__ import annotations
import hashlib, json, time, traceback, os
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
LOCK = Path(r"E:\program\1project\video\shared\work\cache\gpu.lock")

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
    use_cuda = torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")
    print("Loading model on", device, flush=True)
    model = ModelLoader().load_from_file(str(MODEL))
    assert isinstance(model, ImageModelDescriptor), type(model)
    model = model.to(device).eval()
    model_sha = sha256_file(MODEL)
    print("model.scale", model.scale, flush=True)

    done = set()
    if LOG.exists():
        for line in LOG.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                j = json.loads(line)
                if j.get("ok") and j.get("shot"):
                    done.add(int(j["shot"]))
            except Exception:
                pass
    print("already done:", sorted(done), flush=True)

    shots = sorted(picks["shots"].items(), key=lambda kv: int(kv[0]))
    ok = fail = 0
    try:
        for key, entry in shots:
            n = int(entry["shot"])
            if n in PROTECTED:
                raise SystemExit(f"REFUSE protected shot {n}")
            out_path = FF / f"shot{n:02d}.png"
            if n in done and out_path.exists():
                print(f"skip shot{n:02d}", flush=True)
                continue
            if out_path.exists() and n not in done:
                raise SystemExit(f"REFUSE overwrite existing {out_path}")

            src = Path(entry["picked_path"])
            t_start = time.time()
            try:
                img = Image.open(src).convert("RGB")
                cropped, crop_box = center_crop_9_16(img)
                cw, ch = cropped.size
                assert abs(cw / ch - 9 / 16) < 0.002, (cw, ch, cw/ch)
                t0 = to_tensor(cropped).unsqueeze(0).to(device)
                with torch.inference_mode():
                    up_t = model(t0).clamp(0, 1)
                    if device.type == "cuda":
                        up_t = up_t.cpu()
                up = to_pil_image(up_t.squeeze(0))
                final = up.resize(OUT_SIZE, Image.Resampling.LANCZOS)
                assert final.size == OUT_SIZE, final.size
                tmp = out_path.with_suffix(".png.tmp")
                final.save(tmp, format="PNG")
                tmp.replace(out_path)
                meta = {
                    "ok": True, "shot": n, "pick": entry["pick"], "src": str(src),
                    "src_size": list(img.size), "fit": "crop", "crop_box": crop_box,
                    "method": "realesrgan-anime", "model": MODEL.name, "model_sha256": model_sha,
                    "intermediate": list(up.size), "out": str(out_path), "out_size": list(final.size),
                    "device": str(device), "sec": round(time.time() - t_start, 1),
                    "bytes": out_path.stat().st_size, "reason": entry["reason"], "resume": True,
                }
                with LOG.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(meta, ensure_ascii=False) + "\n")
                ok += 1
                print(f"OK shot{n:02d} pick={entry['pick']} {meta['sec']}s device={device}", flush=True)
            except Exception as e:
                meta = {"ok": False, "shot": n, "pick": entry.get("pick"), "src": str(src),
                        "error": str(e), "trace": traceback.format_exc(), "sec": round(time.time()-t_start,1)}
                with LOG.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(meta, ensure_ascii=False) + "\n")
                fail += 1
                print(f"FAIL shot{n:02d}: {e}", flush=True)
        print(f"ALLDONE ok={ok} fail={fail}", flush=True)
    finally:
        # release lock only if we own it
        try:
            if LOCK.exists():
                txt = LOCK.read_text(encoding="utf-8")
                if "a-space-cat" in txt and "missing31" in txt:
                    LOCK.unlink()
                    print("RELEASED LOCK", flush=True)
        except Exception as e:
            print("lock release err", e, flush=True)

if __name__ == "__main__":
    main()
