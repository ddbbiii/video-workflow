# -*- coding: utf-8 -*-
"""Repeat sampling for the dkl-new vs new2 question (2026-11-12).

3 extra samples per channel per prompt (G-grid, S-grid) on the same run directory,
so each cell has 4 samples total including the first pass. Old is left out on
purpose: the question is new2 vs dkl-new, and old costs 0.16/call.

Outputs:
  raw/<tag>-<prompt>-s2..s4.png + -response.json
  cells/<tag>-<prompt>-s<n>-p1..p4.png
  report-repeats.json (incremental)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import compare_dkl_new_three as base  # noqa: E402

RUN = Path(r"E:\program\1project\video\shared\image-api\runs\20261112-114824-dkl3way-2x2")
RAW, CELLS = RUN / "raw", RUN / "cells"
CHANNELS = [c for c in base.CHANNELS if c["tag"] in ("dkl-new", "new2")]
PROMPTS = base.PROMPTS
SAMPLES = [2, 3, 4]
STATE = RUN / "report-repeats.json"


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    CELLS.mkdir(parents=True, exist_ok=True)
    results = []
    for prompt in PROMPTS:
        for sample in SAMPLES:
            for channel in CHANNELS:
                stem = f"{channel['tag']}-{prompt['tag']}-s{sample}"
                png = RAW / f"{stem}.png"
                dims = None
                if png.exists() and png.stat().st_size > 200_000:
                    try:
                        with base.Image.open(png) as image:
                            image.load()
                            dims = list(image.size)
                    except Exception:  # noqa: BLE001
                        png.unlink(missing_ok=True)
                if dims:
                    print(f"skip {stem} (exists)", flush=True)
                    info = {"channel": channel["tag"], "prompt": prompt["tag"],
                            "sample": sample, "ok": True, "reused": True, "dims": dims}
                else:
                    _, key = base.key_for(channel["key_env"])
                    print(f"[{prompt['tag']} s{sample}] {channel['tag']}", flush=True)
                    payload = {"model": channel["model"], "prompt": prompt["prompt"],
                               "size": channel["size"], "n": 1}
                    info = {"channel": channel["tag"], "prompt": prompt["tag"],
                            "sample": sample, "request": payload}
                    try:
                        status, raw, elapsed = base.post_json(
                            f"{channel['base']}/images/generations", key, payload)
                        (RAW / f"{stem}-response.json").write_bytes(raw)
                        info.update({"http_status": status, "elapsed_s": elapsed})
                        if status != 200:
                            info["ok"] = False
                            info["error"] = raw[:300].decode("utf-8", "replace")
                        else:
                            body = json.loads(raw.decode("utf-8"))
                            item = (body.get("data") or [{}])[0]
                            if item.get("b64_json"):
                                import base64
                                png.write_bytes(base64.b64decode(item["b64_json"]))
                                info["delivery"] = "b64_json"
                            elif item.get("url"):
                                info["delivery"] = "url"
                                base.download(item["url"], png)
                            else:
                                raise RuntimeError("no b64_json / url")
                            with base.Image.open(png) as image:
                                image.load()
                                info["dims"] = list(image.size)
                            info.update({"ok": True, "bytes": png.stat().st_size})
                    except Exception as exc:  # noqa: BLE001
                        info.update({"ok": False,
                                     "error": f"{type(exc).__name__}: {exc}"[:300]})
                print("  " + json.dumps({k: info.get(k) for k in
                                         ("ok", "http_status", "dims", "elapsed_s", "error")
                                         if k in info}, ensure_ascii=False), flush=True)
                results.append(info)
                STATE.write_text(json.dumps({"results": results}, ensure_ascii=False, indent=1),
                                 encoding="utf-8")

                if info.get("ok"):
                    cell_info = []
                    with base.Image.open(png) as grid:
                        grid.load()
                        width, height = grid.size
                        half_w, half_h = width // 2, height // 2
                        boxes = [(4, 4, half_w - 4, half_h - 4),
                                 (half_w + 4, 4, width - 4, half_h - 4),
                                 (4, half_h + 4, half_w - 4, height - 4),
                                 (half_w + 4, half_h + 4, width - 4, height - 4)]
                        for index, box in enumerate(boxes, start=1):
                            cell_path = CELLS / f"{stem}-p{index}.png"
                            grid.crop(box).save(cell_path)
                            m = base.metrics(cell_path)
                            m["panel"] = index
                            cell_info.append(m)
                    info["cells"] = cell_info
                STATE.write_text(json.dumps({"results": results}, ensure_ascii=False, indent=1),
                                 encoding="utf-8")
    print(f"done: {len(results)} samples", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
