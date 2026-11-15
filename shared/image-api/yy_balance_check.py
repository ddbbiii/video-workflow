# -*- coding: utf-8 -*-
"""Free/cheap checks on the yy relay: billing endpoints + one alternative-model call.

Distinguishes an empty account balance (all models fail) from a model group that
this key cannot use. Key from IMAGE_API_KEY_YY; never printed.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

BASE = os.environ.get("YY_BASE", "https://yy.shagentai.com/v1").rstrip("/")
UA = "OpenAI/Python 1.60.0"


def get(path: str) -> None:
    req = urllib.request.Request(f"{BASE}{path}",
                                 headers={"Authorization": f"Bearer {os.environ['IMAGE_API_KEY_YY']}",
                                          "User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            print(f"GET {path} -> HTTP {response.status}\n{response.read()[:600].decode('utf-8', 'replace')}")
    except urllib.error.HTTPError as exc:
        print(f"GET {path} -> HTTP {exc.code}\n{exc.read()[:600].decode('utf-8', 'replace')}")
    except Exception as exc:  # noqa: BLE001
        print(f"GET {path} -> {type(exc).__name__}: {exc}")


def gen(model: str) -> None:
    payload = json.dumps({"model": model, "prompt": "a plain grey test card, no text",
                          "size": "1024x1024", "n": 1}).encode("utf-8")
    req = urllib.request.Request(f"{BASE}/images/generations", data=payload, method="POST",
                                 headers={"Authorization": f"Bearer {os.environ['IMAGE_API_KEY_YY']}",
                                          "Content-Type": "application/json", "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            print(f"POST {model} -> HTTP {response.status} (would charge)")
    except urllib.error.HTTPError as exc:
        print(f"POST {model} -> HTTP {exc.code} {exc.read()[:300].decode('utf-8', 'replace')}")
    except Exception as exc:  # noqa: BLE001
        print(f"POST {model} -> {type(exc).__name__}: {exc}")


get("/dashboard/billing/subscription")
get("/dashboard/billing/usage")
for model in ("gpt-image-2-cdn", "nano-banana-2"):
    gen(model)
