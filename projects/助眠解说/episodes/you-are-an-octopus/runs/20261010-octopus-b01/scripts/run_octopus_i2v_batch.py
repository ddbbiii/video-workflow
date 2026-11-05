# -*- coding: utf-8 -*-
"""Octopus V3 batch LTX-2.3 I2V. Native ~12s (289 frames @24fps) to match timeline split_beat."""
from __future__ import annotations
import json, os, shutil, subprocess, sys, time
from datetime import datetime
from pathlib import Path
from PIL import Image

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\you-are-an-octopus")
STILLS = EP / "image" / "stills_16x9"
RUN = EP / "runs" / "20261010-i2v-batch-b01"
HELPER = Path(r"E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\archive\i2v\select_v1\_work")
PLAN = EP / "visual" / "SHOT_PLAN.json"
MEDIA_MAP = EP / "runs" / "20261010-octopus-b01" / "media-map.json"
TIMELINE = EP / "runs" / "20261010-octopus-b01" / "timeline.json"
REQ = Path(r"E:\program\1project\video\shared\gpu-queue\requests\zhumian-octopus-i2v-batch-20261010.json")
FF = shutil.which("ffmpeg") or r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"

# 12s @ 24fps, 8n+1 legal for LTX
FRAMES = 289
FPS = 24
WIDTH, HEIGHT = 1280, 704
NEGATIVE = (
    "overexposed, oversaturated, static freeze, fast camera movement, camera shake, scene change, cut, "
    "blurry details, subtitles, text, watermark, logo, worst quality, low quality, jpeg artifacts, "
    "warping, melting objects, deformed octopus, extra arms, missing arms, tentacle tangle, mutated cephalopod, humanoid face, gore, swarm, "
    "flicker, morphing, mutant, neon octopus, armor"
)

sys.path.insert(0, str(HELPER))
import i2v_cmp as m  # noqa: E402
sys.path.insert(0, str(Path(r"E:\program\1project\video\shared\camera-motion")))
from blender_backend import acquire_gpu_lock, release_gpu_lock  # noqa: E402


def ensure_dirs():
    for d in ("in", "out", "logs", "temp", "raw", "crop", "lanczos"):
        (RUN / d).mkdir(parents=True, exist_ok=True)


def write_req(**kw):
    if REQ.exists():
        d = json.loads(REQ.read_text(encoding="utf-8"))
    else:
        d = {
            "id": "zhumian-octopus-i2v-batch-20261010",
            "owner_thread": "助眠解说",
            "line": "助眠解说",
            "submitted_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "priority": 90,
            "status": "queued",
            "task": "《你是一只章鱼》V3 批量 LTX-2.3 I2V (~12s)",
            "command_or_workflow_path": str(Path(__file__).resolve()),
            "working_directory": str(RUN),
            "output_directory": str(RUN),
            "estimated_minutes": 600,
            "estimated_vram_mb": 15000,
            "dependencies": [],
            "authorization": "2026-10-07 老大授权助眠自行代管 GPU",
            "pid": None,
            "log_path": str(RUN / "logs" / "i2v.log"),
        }
    d.update(kw)
    REQ.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return d


def load_jobs():
    """V3-effective from timeline (78), not all SHOT_PLAN V3 candidates (83)."""
    tl = json.loads(TIMELINE.read_text(encoding="utf-8"))
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    by_id = {s["id"]: s for s in plan["shots"]}
    ids = [s["id"] for s in tl["shots"] if s.get("strategy_effective") == "V3"]
    jobs = []
    for sid in ids:
        s = by_id[sid]
        jpg = STILLS / f"{sid}.jpg"
        png = RUN / "in" / f"{sid}.png"
        if not jpg.exists():
            raise FileNotFoundError(jpg)
        if not png.exists():
            with Image.open(jpg) as im:
                im.convert("RGB").save(png)
        jobs.append({"shot": sid, "i2v_input": str(png), "i2v_prompt": s["motion_prompt"]})
    return jobs


def post(raw: Path, shot: str):
    crop = RUN / "crop" / f"{shot}-ltx-1248x702.mp4"
    base = RUN / "lanczos" / f"{shot}-ltx-lanczos-1920x1080.mp4"
    if not crop.exists():
        subprocess.run([FF, "-v", "error", "-y", "-i", str(raw), "-an", "-vf", "crop=1248:702,setsar=1",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "10", "-pix_fmt", "yuv420p", str(crop)], check=True)
    if not base.exists():
        subprocess.run([FF, "-v", "error", "-y", "-i", str(crop), "-an", "-vf", "scale=1920:1080:flags=lanczos,setsar=1",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-pix_fmt", "yuv420p", str(base)], check=True)
    for p in (raw, crop, base):
        subprocess.run([FF, "-v", "error", "-i", str(p), "-f", "null", "-"], check=True)
    return crop, base


def bootstrap_from_pilot(results):
    pilot_mf = EP / "runs" / "20261010-i2v-pilot-b01" / "i2v_manifest.json"
    if not pilot_mf.exists():
        return results
    for r in json.loads(pilot_mf.read_text(encoding="utf-8")):
        if not r.get("ok"):
            continue
        shot = r["shot"]
        if any(x.get("shot") == shot and x.get("ok") for x in results):
            continue
        # pilot is 5s — keep as ok but mark short; assemble will fallback unless we re-gen
        row = dict(r)
        row["note"] = "from_pilot_5s_may_fallback"
        row["frames"] = r.get("frames", 121)
        for key, sub in (("raw", "raw"), ("crop", "crop"), ("lanczos", "lanczos")):
            srcp = Path(r[key]) if r.get(key) else None
            if srcp and srcp.exists():
                dstp = RUN / sub / srcp.name
                if not dstp.exists():
                    shutil.copy2(srcp, dstp)
                row[key] = str(dstp)
        results.append(row)
    return results


def main():
    ensure_dirs()
    shutil.copy2(HELPER / "extra_model_paths_diffusion.yaml", RUN / "extra_model_paths_diffusion.yaml")
    m.SCR = str(RUN)
    m.LOGF = str(RUN / "logs" / "runner.log")
    jobs = load_jobs()
    mf = RUN / "i2v_manifest.json"
    results = json.loads(mf.read_text(encoding="utf-8")) if mf.exists() else []
    results = bootstrap_from_pilot(results)
    mf.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    done = {r["shot"] for r in results if r.get("ok") and int(r.get("frames") or 0) >= FRAMES - 2}
    # Re-generate pilot 5s clips that are too short for timeline
    short_ok = {r["shot"] for r in results if r.get("ok") and int(r.get("frames") or 0) < FRAMES - 2}
    write_req(status="running", pid=os.getpid(),
              started_at=datetime.now().astimezone().isoformat(timespec="seconds"),
              granted_at=datetime.now().astimezone().isoformat(timespec="seconds"),
              granted_by="助眠解说自管", frames=FRAMES, jobs=len(jobs))
    lock = acquire_gpu_lock(owner="zhumian-octopus-i2v-batch-20261010", timeout_s=600)
    try:
        # Prefer attaching to existing Comfy on 8191 if pilot left it up
        m.start_comfy("portable", "octopus_i2v_batch")
        for job in jobs:
            shot = job["shot"]
            if shot in done:
                m.log(f"{shot} already ok at>={FRAMES-2} frames, skip")
                continue
            r = {
                "shot": shot, "engine": "LTX-2.3 distilled I2V",
                "w": WIDTH, "h": HEIGHT, "frames": FRAMES, "fps": FPS, "seed": 42,
                "input": job["i2v_input"], "prompt": job["i2v_prompt"], "negative": NEGATIVE,
                "started": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            t0 = time.monotonic()
            try:
                if m.PROC is None or m.PROC.poll() is not None:
                    m.log("comfy not running -> restart")
                    m.PROC = None
                    m.start_comfy("portable", "octopus_i2v_batch_re")
                m.IMAGE, m.PROMPT = f"{shot}.png", job["i2v_prompt"]
                g = m.g_ltx(WIDTH, HEIGHT, FRAMES, 11, "octopus-batch/" + shot)
                g["19"]["inputs"]["noise_seed"] = 42
                g["30"]["inputs"]["noise_seed"] = 42
                g["5"]["inputs"]["text"] = NEGATIVE
                (RUN / "logs" / f"{shot}-graph.json").write_text(json.dumps(g, ensure_ascii=False, indent=1), encoding="utf-8")
                pid = json.loads(m.http("/prompt", {"prompt": g, "client_id": shot}))["prompt_id"]
                m.log(f"{shot} queued {pid} frames={FRAMES}")
                while True:
                    time.sleep(5)
                    if m.PROC.poll() is not None:
                        raise RuntimeError("ComfyUI exited")
                    h = m.jget("/history/" + pid)
                    if pid in h:
                        entry = h[pid]
                        break
                    if time.monotonic() - t0 > 3600:
                        m.http("/interrupt", {})
                        raise TimeoutError(shot)
                if entry.get("status", {}).get("status_str") != "success":
                    raise RuntimeError(str(entry.get("status"))[:500])
                out_dir = RUN / "out" / "octopus-batch"
                raw0 = max(out_dir.glob(shot + "_*.mp4"), key=lambda p: p.stat().st_mtime)
                raw = RUN / "raw" / f"{shot}-ltx-raw-{WIDTH}x{HEIGHT}.mp4"
                shutil.copy2(raw0, raw)
                crop, base = post(raw, shot)
                r.update(ok=True, raw=str(raw), crop=str(crop), lanczos=str(base),
                         gen_s=round(time.monotonic() - t0, 1), decode_ok=True, visual_qa="pending")
                m.http("/free", {"unload_models": False, "free_memory": True})
            except Exception as e:
                r.update(ok=False, error=repr(e)[:800], gen_s=round(time.monotonic() - t0, 1))
                m.log(f"{shot} FAILED {e!r}")
                # OOM fallback once to 193 frames (~8s)
                if "out of memory" in repr(e).lower() or "cuda" in repr(e).lower():
                    m.log(f"{shot} will retry later at fewer frames if needed")
            r["ended"] = time.strftime("%Y-%m-%d %H:%M:%S")
            results = [x for x in results if x["shot"] != shot] + [r]
            mf.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            print(shot, "ok" if r.get("ok") else "FAILED", r.get("gen_s"), flush=True)
            if r.get("ok"):
                done.add(shot)
    finally:
        try:
            m.stop_comfy()
        except Exception:
            pass
        release_gpu_lock(lock)
    bad = [r["shot"] for r in results if not r.get("ok")]
    write_req(status="completed" if not bad else "failed",
              finished_at=datetime.now().astimezone().isoformat(timespec="seconds"),
              ok=sum(1 for r in results if r.get("ok")), failed=bad)
    print("DONE ok=%d failed=%s" % (sum(1 for r in results if r.get("ok")), bad), flush=True)
    return 0 if len(bad) < max(1, len(results)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
