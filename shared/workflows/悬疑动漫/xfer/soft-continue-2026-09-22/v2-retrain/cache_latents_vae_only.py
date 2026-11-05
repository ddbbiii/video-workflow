"""VAE-only SDXL latent pre-cache for soft hoodie-male v2 (avoids UNet+TE RAM spike)."""
import os, sys, glob
import numpy as np
from PIL import Image
import torch

ROOT = r"E:\program\1project\video\shared\project-tools\lora\sd-scripts"
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from library import model_util, sdxl_model_util
from diffusers import AutoencoderKL
from safetensors.torch import load_file

CKPT = r"E:\program\1project\video\shared\runtime\comfy\models\models\checkpoints\animagine-xl-4.0-opt.safetensors"
IMG_DIR = r"E:\program\1project\video\shared\project-tools\lora\charb-hoodie-male-v2\dataset\img\10_charb_hoodie_male"
# Match train bucket: (W, H) = (896, 1152)
TARGET_W, TARGET_H = 896, 1152
LATENT_H, LATENT_W = TARGET_H // 8, TARGET_W // 8  # 144x112
KEY_SUFFIX = f"_{LATENT_H}x{LATENT_W}"
DEVICE = "cuda"
DTYPE = torch.float16

def load_vae_only(ckpt, device, dtype):
    print("loading state dict (mmap)...", flush=True)
    if ckpt.endswith(".safetensors"):
        state_dict = load_file(ckpt)
    else:
        state_dict = torch.load(ckpt, map_location="cpu")
        if "state_dict" in state_dict:
            state_dict = state_dict["state_dict"]
    print("building VAE...", flush=True)
    vae_config = model_util.create_vae_diffusers_config()
    vae = AutoencoderKL(**vae_config)
    converted = model_util.convert_ldm_vae_checkpoint(state_dict, vae_config)
    del state_dict
    missing, unexpected = vae.load_state_dict(converted, strict=False)
    print(f"VAE load missing={len(missing)} unexpected={len(unexpected)}", flush=True)
    del converted
    vae.to(device=device, dtype=dtype)
    vae.eval()
    return vae

def resize_center(img: Image.Image, tw, th):
    # same spirit as bucket: cover then crop
    w, h = img.size
    scale = max(tw / w, th / h)
    nw, nh = int(round(w * scale)), int(round(h * scale))
    img = img.resize((nw, nh), Image.LANCZOS)
    left = max(0, (nw - tw) // 2)
    top = max(0, (nh - th) // 2)
    img = img.crop((left, top, left + tw, top + th))
    # crop_ltrb relative to original resized? kohya uses original_size + crop
    # For already-correct aspect images this is identity-ish.
    return img, [w, h], [left, top, left + tw, top + th]

def main():
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    vae = load_vae_only(CKPT, DEVICE, DTYPE)
    paths = sorted(glob.glob(os.path.join(IMG_DIR, "*.png")))
    print(f"images={len(paths)} target={TARGET_W}x{TARGET_H}", flush=True)
    ok = 0
    with torch.no_grad():
        for p in paths:
            img = Image.open(p).convert("RGB")
            orig_w, orig_h = img.size
            # If already exact bucket size, no resize
            if (orig_w, orig_h) == (TARGET_W, TARGET_H):
                cropped = img
                original_size = [orig_w, orig_h]
                crop_ltrb = [0, 0, TARGET_W, TARGET_H]
            else:
                cropped, original_size, crop_ltrb = resize_center(img, TARGET_W, TARGET_H)
            arr = np.array(cropped).astype(np.float32) / 127.5 - 1.0
            t = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).to(DEVICE, dtype=DTYPE)
            latents = vae.encode(t).latent_dist.sample()
            # SDXL scale
            latents = latents * sdxl_model_util.VAE_SCALE_FACTOR
            latents = latents.squeeze(0).float().cpu()
            stem = os.path.splitext(p)[0]
            npz_path = f"{stem}_{TARGET_W:04d}x{TARGET_H:04d}_sdxl.npz"
            key = "latents" + KEY_SUFFIX
            kwargs = {
                key: latents.numpy(),
                "original_size" + KEY_SUFFIX: np.array(original_size),
                "crop_ltrb" + KEY_SUFFIX: np.array(crop_ltrb),
                # also store unsuffixed for old readers
                "latents": latents.numpy(),
                "original_size": np.array(original_size),
                "crop_ltrb": np.array(crop_ltrb),
            }
            np.savez(npz_path, **kwargs)
            ok += 1
            print(f"cached {os.path.basename(npz_path)} shape={tuple(latents.shape)}", flush=True)
            del t, latents
            torch.cuda.empty_cache()
    print(f"DONE cached={ok}", flush=True)

if __name__ == "__main__":
    main()