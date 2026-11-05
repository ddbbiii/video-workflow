# -*- coding: utf-8 -*-
"""c2-s11 黑屏修复(2026-10-20 v3):重生成静帧 + 16:9 裁切 + YAVG 门禁。

背景: v2 中 c2-s11(420.867-445.067s)为准纯黑(YAVG≈22,blackdetect 24.2s 命中)。
设计意图是"近黑但电话线轮廓与微弱反光可读"。

流程(调用方式与 07_gen_stills.py 完全一致, single 模式):
  1. 读 visual/SHOT_PLAN.json 的 c2-s11 image_prompt(已由剧本侧改稿);
  2. gpt-image-2.5-sunburst 1536x1024,最多 3 次生成;
  3. 每次生成后按 11_prepare_16x9 口径中心裁 1536x864 -> LANCZOS 1920x1080;
  4. 门禁: ffmpeg signalstats 实测 YAVG(全幅 -> tv 限量程,与 20_qa_scan 视频
     口径一致)须 35 <= YAVG_tv <= 60;优先取 46-60(同时满足全幅口径 35-51);
  5. 通过后落盘 image/stills/{png,jpg} + image/stills_16x9/c2-s11.jpg,
     并回写 stills_manifest.json 的 c2-s11 条目;
  6. 结果写入 media/blackfix_c2s11/gen_result.json。

退出码: 0=有合格帧; 2=3 次仍不合格(报告后停止)。
"""
from __future__ import annotations
import base64, json, os, subprocess, sys, time, urllib.error, urllib.request
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageStat

EP = Path(__file__).resolve().parents[3]
RUN = EP / "runs" / "20261018-sbt-b01"
STILLS = EP / "image" / "stills"
STILLS169 = EP / "image" / "stills_16x9"
WORK = RUN / "media" / "blackfix_c2s11"
MANIFEST_PATH = RUN / "manifests" / "stills_manifest.json"
MODEL = "gpt-image-2.5-sunburst"
SIZE_SINGLE = "1536x1024"
BASE_URL = os.environ.get("IMAGE_API_BASE_URL", "https://dklapi.com/v1").rstrip("/")
BACKOFFS = [60]                 # 与 07 一致:瞬态错误 60s 后重试一次
MAX_GEN = 3
GATE_LO, GATE_HI = 35.0, 60.0   # YAVG_tv 门禁(视频同口径)
PREF_LO, PREF_HI = 46.0, 60.0   # 优先带(同时满足全幅口径 35-51)
TRANSIENT_MARKERS = (b"rate_limit", b"overloaded", b"upstream_error",
                     b"upstream rate limit", b"upstream unavailable",
                     b"account selection is busy", b"fail_to_fetch_task",
                     b"deadlock")

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def call_api(prompt, out_response, out_image):
    key = os.environ.get("IMAGE_RELAY_KEY_1K")
    if not key:
        raise RuntimeError("IMAGE_RELAY_KEY_1K is missing")
    payload = json.dumps({"model": MODEL, "prompt": prompt, "size": SIZE_SINGLE, "n": 1},
                         ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE_URL + "/images/generations", data=payload,
                                 headers={"Authorization": "Bearer " + key,
                                          "Content-Type": "application/json"}, method="POST")
    started, attempts, api_calls = time.time(), 0, 0
    raw, status = b"", None
    for attempt, delay in enumerate([0] + BACKOFFS):
        if delay:
            time.sleep(delay)
        attempts += 1; api_calls += 1
        try:
            with urllib.request.urlopen(req, timeout=600) as response:
                raw, status = response.read(), response.status
            break
        except urllib.error.HTTPError as exc:
            raw, status = exc.read(), exc.code
            low = raw.lower()
            is_rate = (status in (408, 429, 502, 503, 504)
                       or any(m in low for m in TRANSIENT_MARKERS))
            if is_rate and attempt < len(BACKOFFS):
                continue
            out_response.write_bytes(raw)
            raise RuntimeError(f"HTTP {status}: {raw[:300]!r}")
        except urllib.error.URLError as exc:
            if attempt < len(BACKOFFS):
                continue
            raise RuntimeError(f"URLError: {exc}")
    elapsed = round(time.time() - started, 2)
    out_response.write_bytes(raw)
    data = json.loads(raw.decode("utf-8"))
    item = (data.get("data") or [{}])[0]
    if item.get("b64_json"):
        out_image.write_bytes(base64.b64decode(item["b64_json"]))
    elif item.get("url"):
        with urllib.request.urlopen(item["url"], timeout=600) as r:
            out_image.write_bytes(r.read())
    else:
        raise RuntimeError("no image URL or b64_json in response")
    with Image.open(out_image) as im:
        im.load(); dims = im.size
    return {"elapsed_s": elapsed, "dims": list(dims), "bytes": out_image.stat().st_size,
            "attempts": attempts, "api_calls": api_calls, "status": status}

def crop_16x9(src_png):
    """11_prepare_16x9 同口径: 中心裁 16:9 -> LANCZOS 1920x1080,返回临时 jpg 路径。"""
    with Image.open(src_png) as im:
        w, h = im.size
        nw = w; nh = round(w * 9 / 16)
        if nh > h:
            nh = h; nw = round(h * 16 / 9)
        left, top = (w - nw) // 2, (h - nh) // 2
        im2 = im.crop((left, top, left + nw, top + nh)).convert("RGB")
        if im2.size != (1920, 1080):
            im2 = im2.resize((1920, 1080), Image.Resampling.LANCZOS)
        out = Path(src_png).with_suffix(".16x9.jpg")
        im2.save(out, quality=95, optimize=True)
    return out

def yavg_of(jpg):
    """ffmpeg signalstats YAVG: 全幅(jpeg 原生)与 tv 限量程(视频/20_qa_scan 同口径)。"""
    def run(vf):
        r = subprocess.run(["ffmpeg", "-nostats", "-i", str(jpg), "-vf", vf + ",signalstats,metadata=print:file=-",
                            "-f", "null", "-"], capture_output=True, text=True)
        out = r.stdout.splitlines()
        for line in reversed(out):
            if "YAVG=" in line:
                return float(line.strip().split("YAVG=")[1])
        raise RuntimeError("signalstats YAVG not found: " + (r.stderr or "")[-200:])
    full = run("scale=160:90")
    # tv 口径: 显式 jpeg->mpeg 限量程换算(swtich 后须 format 触发实际转换;
    # 实测标定: 旧静帧 full 6.51 -> tv 21.88,与 v2 视频 YAVG 22.2 一致)
    tv = run("scale=160:90:in_range=jpeg:out_range=mpeg,format=yuv420p")
    return {"full": round(full, 2), "tv": round(tv, 2)}

def main():
    WORK.mkdir(parents=True, exist_ok=True)
    plan = json.loads((EP / "visual" / "SHOT_PLAN.json").read_text(encoding="utf-8"))
    shot = next(s for s in plan["shots"] if s["id"] == "c2-s11")
    prompt = shot["image_prompt"]
    log(f"prompt ({len(prompt)} chars) mode={shot['image_mode']}")

    attempts, best = [], None   # best: (pref_rank, tv, attempt_idx)
    api_calls_total = 0
    for i in range(1, MAX_GEN + 1):
        png = WORK / f"attempt{i}.png"
        resp = WORK / f"attempt{i}.json"
        try:
            info = call_api(prompt, resp, png)
        except Exception as exc:
            log(f"attempt{i} API FAIL: {exc}")
            attempts.append({"attempt": i, "error": str(exc)[:300]})
            api_calls_total += 1
            raise SystemExit(2)          # API 失败立即报告,不猜
        api_calls_total += info["api_calls"]
        jpg169 = crop_16x9(png)
        y = yavg_of(jpg169)
        with Image.open(png) as im:
            stddev = ImageStat.Stat(im.convert("L")).stddev[0]
        rec = {"attempt": i, "yavg": y, "stddev": round(stddev, 2), **info}
        attempts.append(rec)
        log(f"attempt{i}: dims={info['dims']} YAVG full={y['full']} tv={y['tv']} "
            f"stddev={rec['stddev']} elapsed={info['elapsed_s']}s calls={info['api_calls']}")
        ok_gate = GATE_LO <= y["tv"] <= GATE_HI and stddev >= 4.0 and info["dims"] == [1536, 1024]
        pref = PREF_LO <= y["tv"] <= PREF_HI and ok_gate
        if ok_gate and (best is None or pref):
            best = {"attempt": i, "png": png, "jpg169": jpg169, "yavg": y, "pref": pref}
        if pref:
            log(f"attempt{i} 在优先带 {PREF_LO}-{PREF_HI},提前通过")
            break

    if best is None:
        (WORK / "gen_result.json").write_text(json.dumps(
            {"status": "fail", "attempts": attempts, "api_calls": api_calls_total},
            ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"3 次生成均未达门禁 YAVG_tv∈[{GATE_LO},{GATE_HI}]: "
            + "; ".join(f"#{a['attempt']}: tv={a['yavg']['tv']}" for a in attempts if 'yavg' in a))
        return 2

    # 落盘:替换 stills / stills_16x9(旧件已备份于 media/blackfix_backup/)
    i = best["attempt"]
    shutil_src = best["png"]
    import shutil
    shutil.copyfile(shutil_src, STILLS / "c2-s11.png")
    with Image.open(shutil_src) as im:
        im.convert("RGB").save(STILLS / "c2-s11.jpg", quality=95, optimize=True)
    shutil.copyfile(best["jpg169"], STILLS169 / "c2-s11.jpg")
    log(f"accepted attempt{i} -> image/stills/c2-s11.{png,jpg} + image/stills_16x9/c2-s11.jpg")

    # 回写 stills_manifest(c2-s11 条目替换,保留其余不动)
    man = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    with Image.open(STILLS / "c2-s11.jpg") as im:
        w, h = im.size
        stddev = ImageStat.Stat(im.convert("L")).stddev[0]
    entry = {"id": "c2-s11", "section": shot.get("section"), "beat": shot.get("beat"),
             "mode": "single", "status": "ok", "source_path": str(STILLS / "c2-s11.jpg"),
             "grid_batch": None, "grid_cell": None,
             "elapsed_s": attempts[i - 1].get("elapsed_s"),
             "attempts": attempts[i - 1].get("attempts"),
             "api_dims": attempts[i - 1].get("dims"),
             "qa": {"path": str(STILLS / "c2-s11.jpg"), "dims": [w, h],
                    "stddev": round(stddev, 2), "bytes": (STILLS / "c2-s11.jpg").stat().st_size,
                    "ratio": round(w / h, 4), "flags": [],
                    "yavg_16x9": best["yavg"], "passed": True},
             "note": "2026-10-20 黑屏修复重生成(v3): single 模式替换原 2x2_tile 版; "
                     "旧件备份于 runs/20261018-sbt-b01/media/blackfix_backup/"}
    man["items"] = [x for x in man["items"] if x["id"] != "c2-s11"]
    man["items"].append(entry)
    man["meta"]["api_calls"] = man["meta"].get("api_calls", 0) + api_calls_total
    man["updated_at"] = datetime.now().isoformat(timespec="seconds")
    MANIFEST_PATH.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")

    result = {"status": "ok", "accepted_attempt": i, "yavg_16x9": best["yavg"],
              "gate": [GATE_LO, GATE_HI], "preferred": best["pref"],
              "api_calls": api_calls_total, "attempts": attempts}
    (WORK / "gen_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
    log(f"gen_result -> {WORK / 'gen_result.json'} (api_calls={api_calls_total})")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
