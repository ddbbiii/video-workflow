# -*- coding: utf-8 -*-
"""Cover background generation for siffre-beyond-time covers.

Concept: darkness with one warm light (episode motif 2 - the lamp).
Near-black deep teal-blue space, single amber light point kept LOW in frame
(horizontal: below the title block; vertical: lower third), text zones dark.

API: gpt-image-2.5-sunburst @ https://dklapi.com/v1/images/generations
Key: IMAGE_RELAY_KEY_1V if present, else IMAGE_RELAY_KEY_1K (repo-wide key
used by runs/20261018-sbt-b01/scripts/07_gen_stills.py on the same endpoint).
HARD BUDGET: <= 6 API calls total (4 planned + up to 2 remedial).

Usage:
  python gen_bg.py --dry-run        # show job plan + prompts, no API
  python gen_bg.py                  # generate pending jobs (serial)
  python gen_bg.py --retry h-a      # force one remedial regeneration
Idempotent: a bg with an OK manifest entry and existing file is skipped.

Outputs (relative to covers/):
  bg/<id>.png / bg/<id>.json (raw API payload) / bg/<id>.qa.json
  bg/manifest.json  (calls used, per-job QA)
"""
from __future__ import annotations
import argparse, base64, json, os, sys, time, urllib.error, urllib.request
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageStat

COVERS = Path(__file__).resolve().parent
BG = COVERS / "bg"
MANIFEST = BG / "manifest.json"
MODEL = "gpt-image-2.5-sunburst"
BASE_URL = os.environ.get("IMAGE_API_BASE_URL", "https://dklapi.com/v1").rstrip("/")
MAX_CALLS = 6  # hard budget from task brief
TIMEOUT_S = 600
RATIO_TOL = 0.03

# aspect targets: horizontal 16:9 -> final 1920x1080; vertical 9:16 -> 1080x1920
JOBS = {
    "h-a": {
        "size": "2048x1152", "orient": "h", "ratio": 16 / 9,
        "prompt": (
            "Cinematic minimal dark poster background, 16:9 widescreen. Interior of a vast "
            "glacier ice cave at night, near-black deep teal-blue palette. A single tiny warm "
            "amber light - a small camp lantern - glows in the lower right third of the frame, "
            "surrounded by a soft amber halo and faint blue volumetric haze. Ice walls barely "
            "visible as dark textured silhouettes along the edges. The upper two thirds of the "
            "frame are almost pure deep-blue darkness, empty and quiet, generous negative space. "
            "Photorealistic ice texture, subtle reflections, filmic soft light falloff, premium "
            "dreamlike science-documentary mood. Strictly no text, no letters, no numbers, no "
            "watermark, no logo, no signature. Keep the light low in the frame."
        ),
    },
    "h-b": {
        "size": "2048x1152", "orient": "h", "ratio": 16 / 9,
        "prompt": (
            "Cinematic minimal dark poster background, 16:9 widescreen. Night snowfield under a "
            "near-black deep teal-blue sky with a faint cold gradient. Far in the lower left "
            "third, one tiny warm amber light - a small expedition tent lamp - with a gentle "
            "warm pool on dark rippled snow. Everything else is vast calm darkness with delicate "
            "snow texture and thin volumetric blue haze, huge negative space above. Photorealistic, "
            "filmic, quiet dreamlike documentary mood, high-end minimal composition. Strictly no "
            "text, no letters, no numbers, no watermark, no logo. Keep the light low in the frame."
        ),
    },
    "v-a": {
        "size": "1152x2048", "orient": "v", "ratio": 9 / 16,
        "prompt": (
            "Cinematic minimal dark vertical poster background, 9:16 portrait. A deep vertical "
            "glacier crevasse at night, near-black deep teal-blue ice and rock walls fading into "
            "darkness. One small warm amber light - a tiny camp lantern - glows in the lower "
            "third of the frame, near center, with a soft halo and faint volumetric mist. Above "
            "the light the tall space is almost empty deep blue-black, calm and vast, generous "
            "negative space in the upper two thirds. Photorealistic textures, filmic soft "
            "falloff, premium minimalism, dreamlike science-documentary mood. Strictly no text, "
            "no letters, no numbers, no watermark, no logo. Light stays in the lower third."
        ),
    },
    "v-b": {
        "size": "1152x2048", "orient": "v", "ratio": 9 / 16,
        "prompt": (
            "Cinematic minimal dark vertical poster background, 9:16 portrait. Looking down a "
            "dark tunnel carved inside a glacier at night, near-black deep teal-blue palette, "
            "faint icy wall texture receding upward into blackness. A single small warm amber "
            "lantern light glows in the lower third, slightly off center, casting a soft warm "
            "pool and long gentle shadows. The upper two thirds are deep quiet darkness and "
            "empty air, subtle volumetric haze. Photorealistic, calm dreamlike documentary mood, "
            "high-end minimal composition, abundant negative space. Strictly no text, no letters, "
            "no numbers, no watermark, no logo. Light stays in the lower third."
        ),
    },
}

# QA thresholds
MIN_STDDEV = 4.0        # below -> flat image (fatal)
MAX_MEAN_LUM = 100      # whole image must stay dark (fatal above)
MAX_TEXTZONE_LUM = 95   # region reserved for typography must be near-black (fatal above)
LIGHT_Y_RANGE = {"h": (0.55, 0.93), "v": (0.55, 0.93)}  # brightest-pixel centroid band


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def load_manifest():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {"model": MODEL, "base_url": BASE_URL, "created": datetime.now().isoformat(timespec="seconds"),
            "meta": {"api_calls": 0}, "items": {}}


def save_manifest(m):
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    m["updated"] = datetime.now().isoformat(timespec="seconds")
    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")


def get_key():
    for name in ("IMAGE_RELAY_KEY_1V", "IMAGE_RELAY_KEY_1K"):
        key = os.environ.get(name)
        if key:
            return name, key
    return None, None


def call_api(prompt, size, out_png, out_json, meter):
    keyname, key = get_key()
    if not key:
        raise RuntimeError("no relay key: neither IMAGE_RELAY_KEY_1V nor IMAGE_RELAY_KEY_1K is set")
    if meter["api_calls"] + 1 > MAX_CALLS:
        raise RuntimeError(f"budget exhausted: {meter['api_calls']}/{MAX_CALLS} calls already used")
    payload = json.dumps({"model": MODEL, "prompt": prompt, "size": size, "n": 1},
                         ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE_URL + "/images/generations", data=payload,
                                 headers={"Authorization": "Bearer " + key,
                                          "Content-Type": "application/json"}, method="POST")
    meter["api_calls"] += 1
    started = time.time()
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        raw = r.read()
    elapsed = round(time.time() - started, 1)
    out_json.write_bytes(raw)
    data = json.loads(raw.decode("utf-8"))
    item = (data.get("data") or [{}])[0]
    if item.get("b64_json"):
        out_png.write_bytes(base64.b64decode(item["b64_json"]))
    elif item.get("url"):
        with urllib.request.urlopen(item["url"], timeout=TIMEOUT_S) as r2:
            out_png.write_bytes(r2.read())
    else:
        raise RuntimeError("response has neither b64_json nor url")
    with Image.open(out_png) as im:
        im.load()
        dims = im.size
    return {"elapsed_s": elapsed, "dims": list(dims), "key": keyname, "size": size}


def qa_image(path, orient, expect_ratio):
    """Programmatic QA. Fatal: unopenable / bad ratio / flat / too bright overall
    or in the typography zone. Light-centroid out of band is a warning only."""
    qa = {"path": str(path)}
    flags, warns = [], []
    try:
        with Image.open(path) as im:
            im.load()
            w, h = im.size
            rgb = im.convert("RGB")
            gray = rgb.convert("L")
            stddev = ImageStat.Stat(gray).stddev[0]
            mean = ImageStat.Stat(gray).mean[0]
    except Exception as exc:
        qa.update(passed=False, flags=["unopenable"], error=str(exc)[:200])
        return qa
    qa.update(dims=[w, h], ratio=round(w / h, 4), stddev=round(stddev, 2),
              mean_lum=round(mean, 1), bytes=path.stat().st_size)
    # typography zone: h -> top 62%; v -> top 55% (text sits mid-upper, light low)
    tz_frac = 0.62 if orient == "h" else 0.55
    tz = gray.crop((0, 0, w, round(h * tz_frac)))
    tz_mean = ImageStat.Stat(tz).mean[0]
    qa["textzone_lum"] = round(tz_mean, 1)
    # light centroid: brightest 1.5% of pixels
    thresh = sorted(gray.getdata())[max(0, round(w * h * 0.985) - 1)]
    px = gray.load()
    sx = sy = n = 0
    step = 4  # sample every 4th pixel
    for y in range(0, h, step):
        for x in range(0, w, step):
            if px[x, y] >= thresh:
                sx += x; sy += y; n += 1
    if n:
        cx, cy = sx / n / w, sy / n / h
    else:
        cx, cy = 0.5, 0.5
    qa["light_centroid"] = [round(cx, 3), round(cy, 3)]
    if abs(qa["ratio"] - expect_ratio) > RATIO_TOL:
        flags.append("bad_aspect")
    if stddev < MIN_STDDEV:
        flags.append("flat_image")
    if mean > MAX_MEAN_LUM:
        flags.append("too_bright")
    if tz_mean > MAX_TEXTZONE_LUM:
        flags.append("textzone_too_bright")
    lo, hi = LIGHT_Y_RANGE[orient]
    if not (lo <= cy <= hi):
        warns.append(f"light_y={cy:.2f} outside [{lo},{hi}]")
    qa["flags"], qa["warnings"] = flags, warns
    qa["passed"] = not flags
    return qa


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="+", default=[])
    ap.add_argument("--retry", nargs="+", default=[], help="job ids to force regenerate (counts against budget)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    m = load_manifest()
    meter = m["meta"]
    todo = []
    for jid, job in JOBS.items():
        if args.only and jid not in args.only:
            continue
        entry = m["items"].get(jid, {})
        png = BG / f"{jid}.png"
        if jid in args.retry or not (entry.get("status") == "ok" and png.exists()):
            todo.append(jid)

    print(f"budget used {meter['api_calls']}/{MAX_CALLS}; pending: {todo or 'none'}")
    if args.dry_run:
        for jid in todo:
            print(f"--- {jid} size={JOBS[jid]['size']}\n{JOBS[jid]['prompt']}\n")
        return 0

    BG.mkdir(parents=True, exist_ok=True)
    for jid in todo:
        job = JOBS[jid]
        png, resp = BG / f"{jid}.png", BG / f"{jid}.json"
        try:
            info = call_api(job["prompt"], job["size"], png, resp, meter)
            qa = qa_image(png, job["orient"], job["ratio"])
            m["items"][jid] = {"status": "ok" if qa["passed"] else "qa_failed",
                               "info": info, "qa": qa, "generated": datetime.now().isoformat(timespec="seconds")}
            log(f"{'OK ' if qa['passed'] else 'QA-FAIL '}{jid} {info['elapsed_s']}s dims={info['dims']} "
                f"mean={qa.get('mean_lum')} tz={qa.get('textzone_lum')} light_y={qa.get('light_centroid', [0,0])[1]} "
                f"flags={qa.get('flags')} warns={qa.get('warnings')}")
        except Exception as exc:
            m["items"][jid] = {"status": "failed", "error": str(exc)[:300],
                               "generated": datetime.now().isoformat(timespec="seconds")}
            log(f"FAIL {jid}: {str(exc)[:200]}")
        save_manifest(m)  # persist call count after every call
    log(f"done. budget used {meter['api_calls']}/{MAX_CALLS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
