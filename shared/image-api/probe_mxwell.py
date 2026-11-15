# -*- coding: utf-8 -*-
"""Probe a candidate image relay before switching the production endpoint.

Default target: mxwell relay (https://api.mxwell.ai) with the repo's usual
models. Reads the key from the environment or HKCU\\Environment, never prints
or writes it.

Probes (serial, no retry, hard cap 3 calls unless --allow-more):
  P1 generations  gpt-image-2.5-sunburst  1024x1024   smoke: auth/model/billing
  P2 generations  gpt-image-2.5-sunburst  2048x1152   production shape + zh prompt
  P3 edits        gpt-image-2.5-sunburst  2048x1152   reference-image upload path

Usage:
  python probe_mxwell.py --base-url https://api.mxwell.ai/v1
  python probe_mxwell.py --only P1 --base-url ...
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
import winreg
from datetime import datetime
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
DEFAULT_BASE = "https://api.mxwell.ai/v1"
MODEL = "gpt-image-2.5-sunburst"
KEY_ENV_NAMES = ("MXWELL_API_KEY",)
KEY_REG_NAMES = ("IMAGE_API_KEY_MX", "MXWELL_API_KEY")
TIMEOUT_S = 600
USER_AGENT = "OpenAI/Python 1.60.0"

PROMPT_SMOKE = (
    "A single tiny warm amber lantern glowing in near-black deep teal-blue darkness, "
    "photorealistic, volumetric haze, minimal composition, huge negative space, "
    "cinematic, no text, no watermark."
)
PROMPT_ZH = (
    "电影感极简深色封面底图，16:9 横屏。夜晚冰川洞穴内部，近黑的深青蓝色调；"
    "画面下方三分之一处有一盏很小的暖琥珀色营地灯，光晕柔和，周围是淡蓝色体积雾；"
    "上方三分之二几乎全黑，留出大量负空间。写实冰面质感，胶片般柔和的光线衰减，"
    "高级、安静、梦幻的科普纪录片氛围。画面中禁止出现任何文字、字母、数字、水印或标志。"
)

PROBES = [
    {"id": "P1", "kind": "images/generations", "size": "1024x1024", "prompt": PROMPT_SMOKE},
    {"id": "P2", "kind": "images/generations", "size": "2048x1152", "prompt": PROMPT_ZH},
    {"id": "P3", "kind": "images/edits", "size": "2048x1152", "source": "P2", "prompt": PROMPT_ZH},
]


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def preflight(base: str, key: str) -> dict:
    """Free read-only checks: does the key authenticate, and what models exist."""
    request = urllib.request.Request(
        f"{base}/models",
        headers={"Authorization": f"Bearer {key}", "User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    return {"models": sorted(m["id"] for m in data.get("data", [])), "http_status": 200}


def get_key() -> tuple[str | None, str | None]:
    for name in KEY_ENV_NAMES:
        value = os.environ.get(name)
        if value:
            return name, value
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
            for name in KEY_REG_NAMES:
                try:
                    return name, winreg.QueryValueEx(handle, name)[0]
                except FileNotFoundError:
                    continue
    except OSError:
        pass
    return None, None


def redact(text: str, key: str) -> str:
    return text.replace(key, "[redacted]") if key else text


def multipart(fields: dict[str, str], files: dict[str, Path]) -> tuple[bytes, str]:
    boundary = "----dsh" + uuid.uuid4().hex
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode("utf-8")
        )
    for name, path in files.items():
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'
            f"Content-Type: {ctype}\r\n\r\n".encode("utf-8")
        )
        chunks.append(path.read_bytes())
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def call(base: str, key: str, probe: dict, out: Path) -> dict:
    url = f"{base}/{probe['kind']}"
    started = time.time()
    if probe["kind"] == "images/edits":
        fields = {"model": MODEL, "prompt": probe["prompt"], "size": probe["size"], "n": "1"}
        body, ctype = multipart(fields, {"image": out / f"{probe['source']}.png"})
    else:
        body = json.dumps(
            {"model": MODEL, "prompt": probe["prompt"], "size": probe["size"], "n": 1},
            ensure_ascii=False,
        ).encode("utf-8")
        ctype = "application/json"
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": ctype,
            "Accept": "application/json",
            # Cloudflare on api.mxwell.ai rejects the default "Python-urllib/3.11"
            # signature with Error 1010, so identify like the official SDK.
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            raw, status, headers = response.read(), response.status, dict(response.headers)
    except urllib.error.HTTPError as exc:
        raw, status, headers = exc.read(), exc.code, dict(exc.headers)
    except Exception as exc:  # network / DNS / reset
        return {"id": probe["id"], "ok": False, "stage": "transport",
                "error": f"{type(exc).__name__}: {redact(str(exc), key)[:300]}"}

    elapsed = round(time.time() - started, 2)
    (out / f"{probe['id']}-response.json").write_bytes(raw)
    result = {
        "id": probe["id"], "kind": probe["kind"], "model": MODEL, "size_requested": probe["size"],
        "http_status": status, "elapsed_s": elapsed,
        "request_id": headers.get("x-request-id") or headers.get("X-Request-Id"),
        "content_type": headers.get("Content-Type"),
    }
    if not 200 <= status < 300:
        try:
            result["error_body"] = json.loads(raw.decode("utf-8"))
        except Exception:
            result["error_body"] = redact(raw[:800].decode("utf-8", "replace"), key)
        result["ok"] = False
        code = ""
        if isinstance(result["error_body"], dict):
            code = str((result["error_body"].get("error") or {}).get("code") or "")
        if code == "insufficient_user_quota":
            result["blocked"] = "quota"
        return result

    data = json.loads(raw.decode("utf-8"))
    item = (data.get("data") or [{}])[0]
    png = out / f"{probe['id']}.png"
    if item.get("b64_json"):
        png.write_bytes(base64.b64decode(item["b64_json"]))
        result["delivery"] = "b64_json"
    elif item.get("url"):
        result["delivery"] = "url"
        result["image_url_host"] = item["url"].split("/")[2]
        with urllib.request.urlopen(item["url"], timeout=TIMEOUT_S) as image_response:
            png.write_bytes(image_response.read())
    else:
        result["ok"] = False
        result["error"] = "response has neither b64_json nor url"
        return result

    with Image.open(png) as image:
        image.load()
        dims = image.size
        fmt = image.format
    result.update({
        "ok": dims == tuple(int(v) for v in probe["size"].split("x")),
        "dims": list(dims), "format": fmt, "bytes": png.stat().st_size,
        "sha256": hashlib.sha256(png.read_bytes()).hexdigest(),
        "revised_prompt_present": "revised_prompt" in item,
        "usage": data.get("usage"),
        "top_level_keys": sorted(data.keys()),
    })
    if not result["ok"]:
        result["error"] = f"returned {dims[0]}x{dims[1]}, requested {probe['size']}"
    return result


def main() -> int:
    global MODEL
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--only", nargs="+", default=[])
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--check", action="store_true", help="free preflight only: auth + model list")
    args = parser.parse_args()
    MODEL = args.model
    base = (args.base_url or os.environ.get("IMAGE_API_BASE_URL_MX") or DEFAULT_BASE).rstrip("/")

    key_name, key = get_key()
    if not key:
        print("FATAL: no key; set MXWELL_API_KEY or HKCU\\Environment IMAGE_API_KEY_MX", flush=True)
        return 2

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = ROOT / "runs" / f"{stamp}-mxwell-probe"
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "probe": "mxwell", "base_url": base, "model": MODEL, "key_source": key_name,
        "started": datetime.now().isoformat(timespec="seconds"), "results": [],
    }
    results: list[dict] = manifest["results"]
    log(f"probe dir {out}")
    try:
        info = preflight(base, key)
        manifest["preflight"] = info
        log(f"auth ok; models: {', '.join(info['models'])}")
    except Exception as exc:
        log(f"preflight failed: {type(exc).__name__}: {redact(str(exc), key)[:200]}")
        manifest["preflight"] = {"error": f"{type(exc).__name__}: {redact(str(exc), key)[:200]}"}
        (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
        return 2

    if args.check:
        return 0

    for probe in PROBES:
        if args.only and probe["id"] not in args.only:
            continue
        if probe.get("source") and not (out / f"{probe['source']}.png").exists():
            log(f"skip {probe['id']}: source image {probe['source']}.png missing")
            continue
        log(f"call {probe['id']} {probe['kind']} {probe['size']}")
        try:
            result = call(base, key, probe, out)
        except Exception as exc:
            result = {"id": probe["id"], "ok": False, "error": f"{type(exc).__name__}: {str(exc)[:300]}"}
        results.append(result)
        (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
        log(json.dumps(result, ensure_ascii=False))
        if not result.get("ok") and probe["id"] != "P3":
            break
    if any(r.get("blocked") == "quota" for r in results):
        log("BLOCKED: relay account quota is 0 — top up on the provider dashboard, then rerun this probe")
        return 3
    return 0 if results and all(r.get("ok") for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
