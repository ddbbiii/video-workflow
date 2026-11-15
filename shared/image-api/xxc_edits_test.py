# -*- coding: utf-8 -*-
"""Does xxcapi (AZ model) support reference-image /images/edits?

Needed to decide whether "局部修 / 参考图链" steps can run on NEW2 or must stay on OLD.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import time
import urllib.error
import urllib.request
import uuid
import winreg
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
RUN = ROOT / "runs" / "20261109-081500-xxc-edits"
REF = ROOT / "runs" / "20261109-063916-grid2x2-ab" / "raw" / "old-grid.png"
BASE = "https://xxcapi.com/v1"
MODEL = "AZ-gpt-image-2.5-sunburst"
UA = "OpenAI/Python 1.60.0"
PROMPT = ("Rewrite this exact image as a high-contrast black-and-white ink sketch on white paper: "
          "keep the same four-panel composition, same subjects in the same places, remove all colour.")


def key() -> str:
    value = os.environ.get("XXC_API_KEY")
    if value:
        return value
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, "IMAGE_API_KEY_XXC")[0]


def multipart(fields: dict[str, str], files: dict[str, Path]) -> tuple[bytes, str]:
    boundary = "----dsh" + uuid.uuid4().hex
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for name, path in files.items():
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
                      f'filename="{path.name}"\r\nContent-Type: {ctype}\r\n\r\n'.encode())
        chunks.append(path.read_bytes())
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def main() -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    body, ctype = multipart({"model": MODEL, "prompt": PROMPT, "size": "1672x941", "n": "1"},
                            {"image": REF})
    request = urllib.request.Request(
        f"{BASE}/images/edits", data=body, method="POST",
        headers={"Authorization": f"Bearer {key()}", "Content-Type": ctype,
                 "Accept": "application/json", "User-Agent": UA})
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            raw, status = response.read(), response.status
    except urllib.error.HTTPError as exc:
        raw, status = exc.read(), exc.code
    elapsed = round(time.time() - started, 1)
    (RUN / "response.json").write_bytes(raw)
    result = {"http_status": status, "elapsed_s": elapsed}
    if status != 200:
        result["error"] = raw[:300].decode("utf-8", "replace")
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return 1
    data = json.loads(raw.decode("utf-8"))
    item = (data.get("data") or [{}])[0]
    png = RUN / "edits-out.png"
    if item.get("b64_json"):
        png.write_bytes(base64.b64decode(item["b64_json"]))
    else:
        with urllib.request.urlopen(item["url"], timeout=600) as response:
            png.write_bytes(response.read())
    with Image.open(png) as image:
        dims = list(image.size)
        sat = float((__import__("numpy").asarray(image.convert("HSV"))[:, :, 1]).mean())
    result.update({"ok": True, "dims": dims, "mean_sat": round(sat, 1), "bytes": png.stat().st_size})
    (RUN / "report.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
