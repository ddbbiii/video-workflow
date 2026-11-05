# -*- coding: utf-8 -*-
import json
from pathlib import Path

def t2i(job_id, shot, index, seed, text, prefix):
    return {
        "id": job_id, "shot": shot, "index": index, "cand": 1, "round": 1,
        "seed": seed, "provider": "comfyui", "workflow": "qwen_t2i_lightning",
        "w": 928, "h": 1664, "text": text, "clip_text": text,
        "composition": "event first, no face ref", "extra": [], "allow_text": False,
        "character": None, "shot_size": "medium", "refs_win": [],
        "project": "a-space-cat", "negative": None, "instance": "comfy-stills",
        "prompt": {
            "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen_image_2512_fp8_e4m3fn.safetensors", "weight_dtype": "default"}},
            "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image", "device": "default"}},
            "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
            "4": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": "Qwen-Image-2512-Lightning-4steps-V1.0-bf16.safetensors", "strength_model": 1.0}},
            "5": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["4", 0], "shift": 3.1}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": text}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": "低分辨率，低画质，肢体畸形，画面过饱和，蜡像感，过度光滑，画面具有AI感。构图混乱。文字，水印，碗，盆，盘子"}},
            "8": {"class_type": "EmptySD3LatentImage", "inputs": {"width": 928, "height": 1664, "batch_size": 1}},
            "9": {"class_type": "KSampler", "inputs": {"model": ["5", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["8", 0], "seed": seed, "steps": 4, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
            "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}},
            "99": {"class_type": "SaveImage", "inputs": {"images": ["10", 0], "filename_prefix": prefix}},
        },
    }

s06 = (
    "Cinematic realistic film still, vertical composition. Warm afternoon living room, wooden floor, beige sofa. "
    "A round beige plush cat bed is dissolving into empty air: half the cushion is already gone, a clear gap of nothing where the softness was. "
    "A small silver shaded British Shorthair stays curled with eyes closed, body just starting to drop into that gap. "
    "Medium shot. The vanishing bed is the subject. The cat is small and does not fill the frame, not a face portrait. "
    "No bowl, no food dish, no plate. No text, no letters, no watermark."
)
s39 = (
    "Cinematic realistic film still, vertical composition. Dim cold spacecraft cabin, faint blue Earth through a high round porthole. "
    "A small silver shaded British Shorthair sits in the lower third, head tilted up, mouth slightly open, waiting. "
    "The space above its head is empty, where a bowl would be handed from, and nothing is there. "
    "The floor is completely bare. No water bowl, no food bowl, no dish, no plate, no container anywhere in the frame. "
    "The empty space above the cat is the subject. Not a face close-up. No text, no letters, no watermark."
)
doc = {
    "kind": "kepu-stills",
    "tag": "a-space-cat_plot_event_v1",
    "project": "a-space-cat",
    "raw_dir": r"E:\program\1project\video\projects\创意\episodes\a-space-cat\image\stills-raw\plot_event_v1",
    "instance": "comfy-stills",
    "pull_zip": r"E:\program\1project\video\shared\exchange\pipeline\stills\a-space-cat_plot_event_v1.zip",
    "shutdown_after": False,
    "refs": [],
    "jobs": [
        t2i("s06_event_c1", "s06", 6, 88101, s06, "stills/a-space-cat/s06_event_c1"),
        t2i("s39_event_c1", "s39", 39, 88102, s39, "stills/a-space-cat/s39_event_c1"),
    ],
}
out = Path(r"E:\program\1project\video\shared\workflows\创意\a-space-cat\stills-jobs\plot_event_v1.json")
out.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
print(out, out.stat().st_size)
