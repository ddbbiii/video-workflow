import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from PIL import Image


ROOT = Path(__file__).resolve().parent
PROMPT_PACK = ROOT / "prompt-pack-independent-v2.md"
OUT = ROOT / "runs" / (time.strftime("%Y%m%d-%H%M%S") + "-independent-v2")
SIZE = "2048x1152"
BASE_URL = os.environ.get("IMAGE_API_BASE_URL", "https://dklapi.com/v1").rstrip("/")
MODEL = "gpt-image-2.5-sunburst"


def section(text, start, end=None):
    a = text.index(start)
    b = text.index(end, a) if end else len(text)
    return text[a:b].strip()


def call(label, prompt):
    key = os.environ.get("IMAGE_RELAY_KEY_1K")
    if not key:
        raise RuntimeError("IMAGE_RELAY_KEY_1K is missing")
    payload = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "size": SIZE,
        "n": 1,
    }).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + "/images/generations",
        data=payload,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=600) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        status = exc.code
    elapsed = round(time.time() - started, 2)
    response_path = OUT / f"{label}-response.json"
    response_path.write_bytes(raw)
    if status < 200 or status >= 300:
        return {"label": label, "status": status, "elapsed_s": elapsed, "ok": False, "response": str(response_path)}

    data = json.loads(raw.decode("utf-8"))
    item = (data.get("data") or [{}])[0]
    output = OUT / f"{label}.png"
    if item.get("b64_json"):
        output.write_bytes(base64.b64decode(item["b64_json"]))
    elif item.get("url"):
        with urllib.request.urlopen(item["url"], timeout=600) as image_response:
            output.write_bytes(image_response.read())
    else:
        return {"label": label, "status": status, "elapsed_s": elapsed, "ok": False, "response": str(response_path), "error": "no image URL or b64_json"}
    with Image.open(output) as img:
        img.load()
        dimensions = img.size
    size_ok = dimensions == (2048, 1152)
    return {"label": label, "status": status, "elapsed_s": elapsed, "ok": size_ok, "image": str(output), "response": str(response_path), "bytes": output.stat().st_size, "dimensions": dimensions, "error": None if size_ok else "returned size differs from requested 2048x1152"}


def main():
    text = PROMPT_PACK.read_text(encoding="utf-8")
    common = section(text, "## 每张请求都附带的共同约束", "尺寸：")
    matches = list(re.finditer(r"^### ([ABC]\d{2}) ([^\n]+)\n([^#]+)", text, re.MULTILINE))
    prompts = {m.group(1): common + "\n\n" + m.group(2) + "\n" + m.group(3).strip() for m in matches}
    if len(prompts) != 12:
        raise RuntimeError("expected exactly 12 independent prompts")
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    manifest = {
        "batch": "9+2+1",
        "base_url": BASE_URL,
        "model": MODEL,
        "size": SIZE,
        "n_per_call": 1,
        "calls_requested": 12,
        "no_retry": True,
        "reference_images": [],
        "prompt_pack": str(PROMPT_PACK),
        "results": results,
    }
    for label, prompt in prompts.items():
        (OUT / f"{label}-prompt.txt").write_text(prompt, encoding="utf-8")
        print(f"Requesting {label}", flush=True)
        try:
            result = call(label, prompt)
        except Exception as exc:
            result = {"label": label, "ok": False, "error_type": type(exc).__name__, "error": "request/download/decode failed; no automatic retry"}
        results.append(result)
        (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if not result.get("ok"):
            break
    if len(results) != 12 or not all(item.get("ok") for item in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
