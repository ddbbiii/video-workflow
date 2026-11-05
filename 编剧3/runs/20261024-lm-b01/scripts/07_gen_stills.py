# -*- coding: utf-8 -*-
"""Life-manual stills via gpt-image-2.5-sunburst (approved remote API).

Ported from newton-to-chaos runs/20261014-ntc-b01/scripts/07_gen_stills.py.
Adapted for this episode: EP/SHOT_PLAN/STILLS/GRIDS/RUN paths, per-shot
manifest + programmatic QA, max 2 API attempts per shot/grid, tile groups
restricted to same-or-adjacent sections, REPORT.md generation.

Usage:
  python 07_gen_stills.py --dry-run          # print job plan only, no API
  python 07_gen_stills.py                    # generate all pending shots (serial)
  python 07_gen_stills.py --only c1-s01 ...  # restrict to given shot ids
  python 07_gen_stills.py --report           # (re)write REPORT.md from manifest

Serial API calls only (concurrency 1, <=2 as required). Idempotent: shots with
existing stills AND an OK manifest entry are skipped, so re-running resumes.
"""
from __future__ import annotations
import argparse, base64, json, os, shutil, sys, time, urllib.error, urllib.request
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageStat

EP = Path(r"E:\program\1project\video\编剧3")
SHOT_PLAN = EP / "visual" / "SHOT_PLAN.json"
STILLS = EP / "image" / "stills"
GRIDS = EP / "image" / "grids"
RUN = EP / "runs" / "20261024-lm-b01"
MANIFEST_PATH = RUN / "manifests" / "stills_manifest.json"
REPORT_PATH = RUN / "REPORT.md"
MODEL = "gpt-image-2.5-sunburst"
SIZE_GRID = "2048x1152"
SIZE_SINGLE = "1536x1024"
BASE_URL = os.environ.get("IMAGE_API_BASE_URL", "https://dklapi.com/v1").rstrip("/")
BACKOFFS = [60]          # retry once after 60s on transient errors -> 2 attempts max
JOB_GAP_S = 2            # pause between jobs (serial, gentle on rate limits)
FAIL_GAP_S = 3
# Transient relay/upstream errors seen from this API (returned as HTTP 400).
# Treated like 429/5xx: eligible for the single in-call retry, never more.
TRANSIENT_MARKERS = (b"rate_limit", b"overloaded", b"upstream_error",
                     b"upstream rate limit", b"upstream unavailable",
                     b"account selection is busy", b"fail_to_fetch_task",
                     b"deadlock")
# QA thresholds
MIN_STDDEV = 4.0         # grayscale stddev below -> failed (pure black/white/flat)
WARN_STDDEV = 12.0       # below -> warning flag only
MIN_JPG_BYTES = 20_000
MAX_JPG_BYTES = 25_000_000
RATIO_TOL = 0.03         # aspect vs expected ratio
RATIO_SINGLE = 1536 / 1024   # raw singles are 3:2 by API design; 16:9 crop happens later
RATIO_TILE = 16 / 9          # grid + crops are strictly 16:9
FATAL_FLAGS = {"bad_aspect", "flat_image", "bad_file_size", "unopenable"}

_log_fh = None


def log(msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    if _log_fh:
        _log_fh.write(line + "\n")
        _log_fh.flush()


def load_plan():
    return json.loads(SHOT_PLAN.read_text(encoding="utf-8"))


def shot_by_id(plan):
    return {s["id"]: s for s in plan["shots"]}


def have_ids():
    return {p.stem for p in STILLS.glob("*.jpg")} | {p.stem for p in STILLS.glob("*.png")}


def load_manifest():
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {"run": str(RUN), "model": MODEL, "base_url": BASE_URL, "episode": "life-manual",
            "meta": {"api_calls": 0, "api_elapsed_s": 0.0, "wall_s": 0.0}, "items": []}


def save_manifest(m):
    m["updated_at"] = datetime.now().isoformat(timespec="seconds")
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")


def qa_image(path, expect_w=None, expect_h=None, expect_ratio=None):
    """Programmatic QA: dims/aspect vs expected, not pure black/white/flat, sane size."""
    qa = {"path": str(path)}
    try:
        with Image.open(path) as im:
            im.load()
            w, h = im.size
            gray = im.convert("L")
            stddev = ImageStat.Stat(gray).stddev[0]
        qa.update(dims=[w, h], stddev=round(stddev, 2), bytes=path.stat().st_size,
                  ratio=round(w / h, 4))
    except Exception as exc:
        qa.update(passed=False, flags=["unopenable"], error=str(exc)[:200])
        return qa
    flags = []
    if expect_ratio and abs(qa["ratio"] - expect_ratio) > RATIO_TOL:
        flags.append("bad_aspect")
    if expect_w and (abs(w - expect_w) > max(4, round(expect_w * 0.02))
                     or abs(h - expect_h) > max(4, round(expect_h * 0.02))):
        flags.append("unexpected_dims")
    if qa["stddev"] < MIN_STDDEV:
        flags.append("flat_image")
    elif qa["stddev"] < WARN_STDDEV:
        flags.append("low_variance")
    if not (MIN_JPG_BYTES <= qa["bytes"] <= MAX_JPG_BYTES):
        flags.append("bad_file_size")
    qa["flags"] = flags
    qa["passed"] = not (set(flags) & FATAL_FLAGS)
    return qa


def call_api(prompt, out_response, out_image, size, meter):
    key = os.environ.get("IMAGE_RELAY_KEY_1K")
    if not key:
        raise RuntimeError("IMAGE_RELAY_KEY_1K is missing")
    payload = json.dumps({"model": MODEL, "prompt": prompt, "size": size, "n": 1},
                         ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE_URL + "/images/generations", data=payload,
                                 headers={"Authorization": "Bearer " + key,
                                          "Content-Type": "application/json"}, method="POST")
    started = time.time()
    attempts = 0
    raw, status = b"", None
    for attempt, delay in enumerate([0] + BACKOFFS):
        if delay:
            time.sleep(delay)
        attempts += 1
        meter["api_calls"] += 1
        try:
            with urllib.request.urlopen(req, timeout=600) as response:
                raw = response.read()
                status = response.status
            break
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            status = exc.code
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
    meter["api_elapsed_s"] += elapsed
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
        im.load()
        dims = im.size
    return {"status": status, "elapsed_s": elapsed, "dims": list(dims),
            "bytes": out_image.stat().st_size, "size": size, "attempts": attempts}


def build_grid_prompt(shots):
    header = ("生成一张严格等分的2x2网格图，总画幅16:9，每格也为横屏16:9。"
              "格子没有间距、装饰边框、文字或编号；不同场景只能在各自格子内，不能跨格。"
              "以下位置和编号只用于指令，不要画到图中。")
    parts = [header]
    for idx, shot in enumerate(shots):
        row, col = divmod(idx, 2)
        parts.append(f"\n\n第{row + 1}行第{col + 1}列（{shot['id']}）：\n{shot['image_prompt']}")
    return "".join(parts)


def gen_single(shot, batch_dir, meter, mode="single"):
    sid = shot["id"]
    out_img = batch_dir / f"{sid}.png"
    out_resp = batch_dir / f"{sid}.json"
    info = call_api(shot["image_prompt"], out_resp, out_img, SIZE_SINGLE, meter)
    png, jpg = STILLS / f"{sid}.png", STILLS / f"{sid}.jpg"
    shutil.copyfile(out_img, png)
    with Image.open(out_img) as im:
        im.convert("RGB").save(jpg, quality=95, optimize=True)
    qa = qa_image(jpg, 1536, 1024, expect_ratio=RATIO_SINGLE)
    entry = {"id": sid, "section": shot.get("section"), "beat": shot.get("beat"),
             "mode": mode, "status": "ok" if qa["passed"] else "failed",
             "source_path": str(jpg), "grid_batch": None, "grid_cell": None,
             "elapsed_s": info["elapsed_s"], "attempts": info["attempts"],
             "api_dims": info["dims"], "qa": qa}
    return entry, {"kind": mode, "id": sid, **info}


def gen_grid(shots, batch_dir, meter):
    first = shots[0]["id"]
    grid_png = batch_dir / f"grid_{first}.png"
    out_resp = batch_dir / f"grid_{first}.json"
    info = call_api(build_grid_prompt(shots), out_resp, grid_png, SIZE_GRID, meter)
    crops_dir = batch_dir / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    with Image.open(grid_png) as im:
        width, height = im.size
        rgb = im.convert("RGB")
        for idx, shot in enumerate(shots):
            sid = shot["id"]
            col, row = idx % 2, idx // 2
            box = (round(col * width / 2), round(row * height / 2),
                   round((col + 1) * width / 2), round((row + 1) * height / 2))
            crop = rgb.crop(box)
            crop.save(crops_dir / f"{sid}.png")
            crop.save(STILLS / f"{sid}.png")
            jpg = STILLS / f"{sid}.jpg"
            crop.save(jpg, quality=95, optimize=True)
            qa = qa_image(jpg, round(width / 2), round(height / 2), expect_ratio=RATIO_TILE)
            entries.append({"id": sid, "section": shot.get("section"), "beat": shot.get("beat"),
                            "mode": "2x2_tile", "status": "ok" if qa["passed"] else "failed",
                            "source_path": str(jpg), "grid_batch": batch_dir.name,
                            "grid_cell": f"r{row + 1}c{col + 1}",
                            "elapsed_s": info["elapsed_s"], "attempts": info["attempts"],
                            "api_dims": info["dims"], "crop_box": list(box), "qa": qa})
    record = {"kind": "grid", "id": f"grid_{first}", "cells": [s["id"] for s in shots],
              "sections": sorted({s["section"] for s in shots}), **info}
    return entries, record


def section_order(shots):
    seen = []
    for s in shots:
        if s["section"] not in seen:
            seen.append(s["section"])
    return seen


def build_tile_groups(tile_shots, order):
    """Group tile shots (story order) into 2x2 grids of 4.

    A grid may only span shots of one section or two adjacent sections
    (bridge counts as adjacent to ch01; epilogue to ch10). Leftovers that
    cannot fill a grid without violating that rule fall back to independent
    single generation (only happens on partial resumes).
    """
    idx = {sec: i for i, sec in enumerate(order)}
    by_sec = {}
    for s in tile_shots:
        by_sec.setdefault(s["section"], []).append(s)
    groups, fallback, carry = [], [], []
    for sec in order:
        cur = by_sec.get(sec, [])
        if carry and cur:
            carry_secs = {x["section"] for x in carry}
            if len(carry_secs) > 1:  # keep carry single-section; flush older part
                earliest = min(carry_secs, key=lambda x: idx[x])
                fallback.extend([x for x in carry if x["section"] == earliest])
                carry = [x for x in carry if x["section"] != earliest]
        pool = carry + cur
        while len(pool) >= 4:
            groups.append(pool[:4])
            pool = pool[4:]
        carry = pool
    fallback.extend(carry)
    for g in groups:  # hard assertion of the adjacency red line
        secs = {idx[x["section"]] for x in g}
        assert len(secs) <= 2 and max(secs) - min(secs) <= 1, f"grid spans sections: {[x['id'] for x in g]}"
    return groups, fallback


def adopt_existing(shot):
    """QA a still that already exists on disk but lacks a manifest entry."""
    sid = shot["id"]
    jpg, png = STILLS / f"{sid}.jpg", STILLS / f"{sid}.png"
    mode = shot.get("image_mode") or "single"
    ew, eh = (1024, 576) if mode == "2x2_tile" else (1536, 1024)
    eratio = RATIO_TILE if mode == "2x2_tile" else RATIO_SINGLE
    path = jpg if jpg.exists() else png
    qa = qa_image(path, ew, eh, expect_ratio=eratio)
    return {"id": sid, "section": shot.get("section"), "beat": shot.get("beat"),
            "mode": mode, "status": "ok" if qa["passed"] else "failed",
            "source_path": str(path), "grid_batch": None, "grid_cell": None,
            "elapsed_s": 0.0, "attempts": 0, "adopted": True, "qa": qa}


def write_report(manifest, plan):
    by_id = shot_by_id(plan)
    order = section_order(plan["shots"])
    items = {it["id"]: it for it in manifest["items"]}
    counts = {"ok": 0, "failed": 0}
    per_sec = {sec: {"total": 0, "ok": 0, "failed": 0} for sec in order}
    for s in plan["shots"]:
        sec, sid = s["section"], s["id"]
        per_sec[sec]["total"] += 1
        it = items.get(sid)
        if it and it.get("status") == "ok":
            counts["ok"] += 1
            per_sec[sec]["ok"] += 1
        elif it and it.get("status") == "failed":
            counts["failed"] += 1
            per_sec[sec]["failed"] += 1
    missing = [s["id"] for s in plan["shots"] if s["id"] not in items]
    failed = [it for it in manifest["items"] if it.get("status") == "failed"]
    warned = [it for it in manifest["items"]
              if it.get("status") == "ok" and it.get("qa", {}).get("flags")]
    meta = manifest.get("meta", {})
    lines = []
    lines.append("# REPORT｜life-manual 静帧生图 run 20261024-lm-b01")
    lines.append("")
    lines.append(f"- 生成时间：{datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- 模型：`{MODEL}` @ `{manifest.get('base_url', BASE_URL)}`")
    lines.append(f"- 计划总镜数：{len(plan['shots'])}（single 67 / 2x2_tile 68，见 SHOT_PLAN counts）")
    lines.append(f"- 成功：**{counts['ok']}**　失败：**{counts['failed']}**　未处理：{len(missing)}")
    lines.append(f"- API 总调用次数（含重试）：{meta.get('api_calls', 0)}　API 累计耗时：{round(meta.get('api_elapsed_s', 0), 1)}s"
                 f"（wall {round(meta.get('wall_s', 0), 1)}s）")
    lines.append("")
    lines.append("## 按章统计")
    lines.append("")
    lines.append("| 章 | 总镜数 | 成功 | 失败 |")
    lines.append("|---|---|---|---|")
    for sec in order:
        d = per_sec[sec]
        lines.append(f"| {sec} | {d['total']} | {d['ok']} | {d['failed']} |")
    lines.append("")
    if failed:
        lines.append("## 失败镜列表（附 beat，供剧本侧参考）")
        lines.append("")
        for it in failed:
            lines.append(f"- `{it['id']}`（{it.get('section')}｜{it.get('beat')}｜{it.get('mode')}"
                         f"｜attempts={it.get('attempts')}）：{str(it.get('error', ''))[:200]}")
        lines.append("")
    else:
        lines.append("## 失败镜列表")
        lines.append("")
        lines.append("- 无（全部成功）")
        lines.append("")
    if missing:
        lines.append("## 未处理镜（本次 run 未覆盖）")
        lines.append("")
        lines.append("- " + ", ".join(f"`{m}`" for m in missing))
        lines.append("")
    lines.append("## QA 警告（通过但带 flags，需人工抽检）")
    lines.append("")
    if warned:
        for it in warned:
            q = it.get("qa", {})
            lines.append(f"- `{it['id']}`：flags={q.get('flags')} stddev={q.get('stddev')} "
                         f"dims={q.get('dims')} bytes={q.get('bytes')}")
    else:
        lines.append("- 无")
    lines.append("")
    lines.append("## 待剧本侧确认")
    lines.append("")
    lines.append("- 本 run 严格按 SHOT_PLAN.json 的 image_prompt 生成，未增删任何描述；"
                 "失败/警告镜是否需要改 prompt，请剧本侧判断后回信。")
    if failed or warned:
        lines.append("- 需要关注：见上方失败镜列表与 QA 警告。")
    lines.append("")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    global _log_fh
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="+", default=[])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    plan = load_plan()
    if args.report:
        write_report(load_manifest(), plan)
        print("report written:", REPORT_PATH)
        return 0

    key = os.environ.get("IMAGE_RELAY_KEY_1K")
    if not key and not args.dry_run:
        print("FATAL: IMAGE_RELAY_KEY_1K is missing; refusing to call any API", flush=True)
        return 2

    manifest = load_manifest()
    done_ok = {it["id"] for it in manifest["items"] if it.get("status") == "ok"}
    have = have_ids()
    pending, adopted = [], []
    for s in plan["shots"]:
        sid = s["id"]
        f_ok = (STILLS / f"{sid}.jpg").exists() or (STILLS / f"{sid}.png").exists()
        if sid in done_ok and f_ok:
            continue
        if f_ok:  # file exists but no OK manifest entry -> adopt via QA, no API call
            adopted.append(s)
            continue
        pending.append(s)
    if args.only:
        only = set(args.only)
        pending = [s for s in pending if s["id"] in only]
        adopted = [s for s in adopted if s["id"] in only]

    order = section_order(plan["shots"])
    singles = [s for s in pending if s.get("image_mode") == "single" and s.get("image_prompt")]
    tiles = [s for s in pending if s.get("image_mode") == "2x2_tile" and s.get("image_prompt")]
    groups, tile_fallback = build_tile_groups(tiles, order)

    est_calls = len(singles) + len(groups) + len(tile_fallback)
    print(f"plan: {len(plan['shots'])} shots | skip(done)={len(plan['shots']) - len(pending) - len(adopted)} "
          f"adopt(existing)={len(adopted)} | jobs: single={len(singles)} grid={len(groups)} "
          f"grid_fallback_single={len(tile_fallback)} | est API calls={est_calls}")
    if args.dry_run:
        for gi, g in enumerate(groups, 1):
            print(f"  grid {gi:02d}: " + " ".join(x["id"] for x in g)
                  + f"  sections={sorted({x['section'] for x in g})}")
        if tile_fallback:
            print("  fallback singles: " + " ".join(x["id"] for x in tile_fallback))
        return 0

    STILLS.mkdir(parents=True, exist_ok=True)
    GRIDS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    batch_dir = GRIDS / f"batch-{stamp}"
    batch_dir.mkdir(parents=True, exist_ok=True)
    (RUN / "logs").mkdir(parents=True, exist_ok=True)
    _log_fh = open(RUN / "logs" / f"gen_stills_{stamp}.log", "a", encoding="utf-8")
    log(f"run start batch={batch_dir} model={MODEL} base={BASE_URL} jobs single={len(singles)} "
        f"grid={len(groups)} fallback={len(tile_fallback)} adopt={len(adopted)}")

    meter = manifest["meta"]
    batch_manifest = {"batch": str(batch_dir), "items": [], "fails": []}
    batch_path = batch_dir / "manifest.json"
    wall_start = time.time()

    def record(entries, batch_rec=None, err=None):
        for e in entries:
            manifest["items"] = [x for x in manifest["items"] if x["id"] != e["id"]]
            manifest["items"].append(e)
        if batch_rec:
            batch_manifest["items"].append(batch_rec)
        if err:
            batch_manifest["fails"].append(err)
        save_manifest(manifest)
        batch_path.write_text(json.dumps(batch_manifest, ensure_ascii=False, indent=1),
                              encoding="utf-8")

    for s in adopted:
        try:
            e = adopt_existing(s)
            record([e])
            log(f"ADOPT {e['id']} status={e['status']} flags={e['qa'].get('flags')}")
        except Exception as exc:
            log(f"ADOPT-FAIL {s['id']}: {exc}")

    def fail_entries(shots_list, mode, exc, calls_used):
        return [{"id": s["id"], "section": s.get("section"), "beat": s.get("beat"),
                 "mode": mode, "status": "failed", "source_path": None,
                 "grid_batch": batch_dir.name if mode == "2x2_tile" else None,
                 "grid_cell": None, "elapsed_s": None, "attempts": calls_used,
                 "error": str(exc)[:300]} for s in shots_list]

    def run_jobs():
        consec_fails = 0

        def fail_gap():
            # ride out relay outage windows without burning jobs; queue still advances
            return min(20 + 20 * consec_fails, 120)

        def handle_fail(label, exc):
            nonlocal consec_fails
            consec_fails += 1
            gap = fail_gap()
            log(f"FAIL {label}: {str(exc)[:200]} (consecutive={consec_fails}, next in {gap}s)")
            time.sleep(gap)

        def handle_ok(label):
            nonlocal consec_fails
            consec_fails = 0
            time.sleep(JOB_GAP_S)

        for shot in singles:
            before = meter["api_calls"]
            try:
                e, rec = gen_single(shot, batch_dir, meter)
                record([e], rec)
                log(f"OK single {e['id']} {e['elapsed_s']}s dims={e['api_dims']} "
                    f"var={e['qa'].get('stddev')} flags={e['qa'].get('flags')}")
                handle_ok(e["id"])
            except Exception as exc:
                record(fail_entries([shot], "single", exc, meter["api_calls"] - before),
                       err=f"single:{shot['id']}: {exc}")
                handle_fail(f"single {shot['id']}", exc)
        for g in groups:
            before = meter["api_calls"]
            label = "grid:" + "+".join(x["id"] for x in g)
            try:
                entries, rec = gen_grid(g, batch_dir, meter)
                record(entries, rec)
                bad = [e["id"] for e in entries if e["status"] != "ok"]
                log(f"OK {label} {entries[0]['elapsed_s']}s dims={entries[0]['api_dims']}"
                    + (f" QA-FAIL={bad}" if bad else ""))
                handle_ok(label)
            except Exception as exc:
                record(fail_entries(g, "2x2_tile", exc, meter["api_calls"] - before),
                       err=f"{label}: {exc}")
                handle_fail(label, exc)
        for shot in tile_fallback:
            before = meter["api_calls"]
            try:
                e, rec = gen_single(shot, batch_dir, meter, mode="single_fallback")
                record([e], rec)
                log(f"OK single_fallback {e['id']} {e['elapsed_s']}s dims={e['api_dims']}")
                handle_ok(e["id"])
            except Exception as exc:
                record(fail_entries([shot], "single_fallback", exc, meter["api_calls"] - before),
                       err=f"single_fallback:{shot['id']}: {exc}")
                handle_fail(f"single_fallback {shot['id']}", exc)

    try:
        run_jobs()
    finally:
        meter["wall_s"] = round(meter.get("wall_s", 0.0) + (time.time() - wall_start), 1)
        save_manifest(manifest)

    ok_n = sum(1 for it in manifest["items"] if it.get("status") == "ok")
    fail_n = sum(1 for it in manifest["items"] if it.get("status") == "failed")
    log(f"RUN DONE ok={ok_n} failed={fail_n} api_calls={meter['api_calls']} "
        f"api_s={round(meter['api_elapsed_s'], 1)} wall_s={meter['wall_s']}")
    _log_fh.close()
    write_report(manifest, plan)
    print("report written:", REPORT_PATH)
    return 0 if fail_n == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
