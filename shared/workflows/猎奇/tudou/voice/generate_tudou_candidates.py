"""Generate 5x3 VoxCPM2 voice-design candidates for 《土豆退婚流》.
This is a standalone script; it does not touch any existing pipeline or registry.
"""
import json
import math
import os
import shutil
import time
import traceback
from datetime import datetime, timezone, timedelta

import numpy as np
import soundfile as sf
import torch

from voxcpm import VoxCPM

ROOT = r"E:\program\1project\video\projects\猎奇\episodes\tudou\archive\audio"
OUT = os.path.join(ROOT, "voice-candidates")
AUDITION = r"E:\program\1project\video\shared\runtime\engines\tts\voice-assets\_audition\lieqi-tudou"
MODEL = r"E:\program\1project\video\shared\runtime\engines\tts\voxcpm\pretrained_models\VoxCPM2"
SEEDS = [7, 42, 123]
CFG = 2.0
STEPS = 10
TAIL = "句尾干净利落不拖不压，没有气泡音和沙哑感"

# Candidate test text is deliberately representative and roughly 10-15 seconds.
# Potato is restricted to Act 1 as requested; the cucumber scream is omitted.
ROLES = [
    {
        "role": "potato",
        "label": "土豆小伙",
        "desc": "20岁出头的年轻男性，诚实、委屈，正常语速，" + TAIL,
        "text": "小红，我们不是从小一个菜园子长大的吗？你说过不嫌弃我的。伯父，我虽然土，但我实在，煎炒烹炸样样都行。你是谁？好。今日之辱，我记下了。三年之后，我让你们番茄家高攀不起！",
    },
    {
        "role": "tomato-heiress",
        "label": "番茄千金",
        "desc": "20多岁的女性，尖刻、嚣张、阴阳怪气，语速快但不尖细，" + TAIL,
        "text": "土豆，这婚我退了！你看看你，浑身是泥，还发芽，丢不丢人！那是小时候！现在我是番茄家千金，要上米其林沙拉的！还是黄瓜哥哥清爽。土豆，滚回你的地里去吧！",
    },
    {
        "role": "cucumber",
        "label": "黄瓜大少",
        "desc": "20多岁的男性，油腻、自鸣得意、轻佻有玩笑感，语速快，音高和土豆明显不同，" + TAIL,
        "text": "哟，这就是那颗土豆啊？浑身疙瘩，比我还丑。我？黄瓜大少，冷链进口，天天冰镇，顶花带刺！小红，以后跟我。别提了，冰箱断电，我都快蔫了。求您给口饭吃！",
    },
    {
        "role": "tomato-dad",
        "label": "番茄老爹",
        "desc": "50岁左右的男性，中低音，暴发户拖腔，势利、摆谱，" + TAIL,
        "text": "听见没？我们番茄家，红得发亮！你一个埋土里的，配吗？土就是土！这是你家给的彩礼？两袋化肥？拿回去！谁啊，这么大排场……这，这不是土豆吗？你怎么削皮了？",
    },
    {
        "role": "onion-secretary",
        "label": "洋葱秘书",
        "desc": "20多岁的女性，始终带着哭腔，抽抽搭搭但每个音节清晰，" + TAIL,
        "text": "总裁，番茄家到了。呜……我没哭，是我自己辣眼睛。没错。番茄家欠了一屁股债，这块地，我们总裁已经收购了。黄瓜味薯片，上线！",
    },
]


def median_f0(path, sample_rate):
    """Lightweight autocorrelation F0 estimate; returns median voiced F0 in Hz."""
    y, sr = sf.read(path, dtype="float32")
    if y.ndim > 1:
        y = y.mean(axis=1)
    if sr != sample_rate:
        sample_rate = sr
    frame = max(256, int(sample_rate * 0.040))
    hop = max(128, int(sample_rate * 0.010))
    lo = max(1, int(sample_rate / 500.0))
    hi = min(frame - 2, int(sample_rate / 70.0))
    vals = []
    if len(y) < frame or hi <= lo:
        return None
    for start in range(0, len(y) - frame + 1, hop):
        x = y[start:start + frame].astype(np.float64)
        x -= x.mean()
        rms = math.sqrt(float(np.mean(x * x)))
        if rms < 0.004:
            continue
        x *= np.hamming(frame)
        ac = np.correlate(x, x, mode="full")[frame - 1:]
        if ac[0] <= 1e-10:
            continue
        region = ac[lo:hi + 1]
        lag = lo + int(np.argmax(region))
        peak = float(ac[lag] / ac[0])
        if peak < 0.28:
            continue
        # Parabolic sub-sample correction around the correlation maximum.
        delta = 0.0
        if 1 <= lag < len(ac) - 1:
            a, b, c = float(ac[lag - 1]), float(ac[lag]), float(ac[lag + 1])
            den = a - 2.0 * b + c
            if abs(den) > 1e-12:
                delta = 0.5 * (a - c) / den
                delta = max(-0.5, min(0.5, delta))
        f0 = float(sample_rate / (lag + delta))
        if 70.0 <= f0 <= 500.0:
            vals.append(f0)
    return round(float(np.median(vals)), 1) if vals else None


def now_cn():
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).isoformat(timespec="seconds")


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(AUDITION, exist_ok=True)
    started = time.time()
    print("START", now_cn(), flush=True)
    print("MODEL", MODEL, flush=True)
    print("PARAMS", json.dumps({"cfg": CFG, "steps": STEPS, "optimize": False, "denoiser": False, "normalize": False, "sr": 48000, "seeds": SEEDS}, ensure_ascii=False), flush=True)
    print("ROLES", [r["role"] for r in ROLES], flush=True)
    load_t = time.time()
    model = VoxCPM.from_pretrained(MODEL, load_denoiser=False, optimize=False)
    load_s = round(time.time() - load_t, 1)
    sr = int(model.tts_model.sample_rate)
    print("LOADED", json.dumps({"load_s": load_s, "sample_rate": sr, "torch": torch.__version__, "cuda": torch.cuda.is_available()}), flush=True)

    results = []
    gpu_s = 0.0
    for role in ROLES:
        for seed in SEEDS:
            name = f"{role['role']}_{seed}.wav"
            out_path = os.path.join(OUT, name)
            audition_path = os.path.join(AUDITION, name)
            print("GENERATING", role["role"], seed, flush=True)
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)
                torch.cuda.synchronize()
            t0 = time.time()
            # Voice-design mode: no reference/prompt wav; description is in parentheses.
            wav = model.generate(
                text=f"({role['desc']}){role['text']}",
                cfg_value=CFG,
                inference_timesteps=STEPS,
                normalize=False,
                denoise=False,
            )
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            gen_s = time.time() - t0
            gpu_s += gen_s
            sf.write(out_path, wav, sr)
            shutil.copy2(out_path, audition_path)
            dur = float(len(wav) / sr)
            f0 = median_f0(out_path, sr)
            rec = {"file": name, "role": role["role"], "label": role["label"], "seed": seed, "description": role["desc"], "duration_s": round(dur, 2), "median_f0_hz": f0, "generation_s": round(gen_s, 1), "sample_rate": sr}
            results.append(rec)
            print("RESULT", json.dumps(rec, ensure_ascii=False), flush=True)

    total_wall = round(time.time() - started, 1)
    gpu_s = round(gpu_s, 1)
    meta = {"generated_at": now_cn(), "engine": "VoxCPM2", "model": MODEL, "cfg_value": CFG, "inference_timesteps": STEPS, "optimize": False, "denoiser": False, "normalize": False, "sample_rate": sr, "seeds": SEEDS, "load_s": load_s, "generation_total_s": gpu_s, "wall_total_s": total_wall, "results": results}
    with open(os.path.join(OUT, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    lines = [
        "# 土豆退婚流 VoxCPM2 voice-design candidates",
        "",
        f"Generated: {meta['generated_at']} (UTC+8)",
        "Engine: VoxCPM2 local voice design; no reference audio; no paid service.",
        f"Params: cfg={CFG}, steps={STEPS}, optimize=False, denoiser=False, normalize=False, sample_rate={sr} Hz.",
        f"Seeds: {', '.join(map(str, SEEDS))}; GPU generation time: {gpu_s:.1f} s; wall time: {total_wall:.1f} s; model load: {load_s:.1f} s.",
        "Scream line omitted from cucumber test text; potato uses Act 1 lines only.",
        "",
        "| file | role | seed | description | duration (s) | median F0 (Hz) |",
        "|---|---|---:|---|---:|---:|",
    ]
    for x in results:
        desc = x["description"].replace("|", "\\|")
        f0 = "n/a" if x["median_f0_hz"] is None else f"{x['median_f0_hz']:.1f}"
        lines.append(f"| `{x['file']}` | {x['label']} (`{x['role']}`) | {x['seed']} | {desc} | {x['duration_s']:.2f} | {f0} |")
    lines += ["", "Automated F0 is a lightweight autocorrelation median over voiced frames; listen for vocal fry/hoarseness before selection.", ""]
    md = "\n".join(lines)
    for md_path in [os.path.join(OUT, "candidates.md"), os.path.join(AUDITION, "candidates.md")]:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md)
    print("ALL_DONE", json.dumps({"files": len(results), "generation_total_s": gpu_s, "wall_total_s": total_wall}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR", type(exc).__name__, str(exc), flush=True)
        traceback.print_exc()
        raise
