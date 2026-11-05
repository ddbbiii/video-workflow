# -*- coding: utf-8 -*-
"""分片并行渲染 motion_plan.json(纯 CPU,调用 shared/camera-motion affine 后端)。
把 134 镜按帧数均衡切成 N 片,各片独立 camera_motion 渲染(幂等可 --resume),
完成后把逐镜 mp4 汇总到 runs/20261103-gla-b01/media/affine/ 并校验帧数。
"""
from __future__ import annotations
import json, math, shutil, subprocess, sys, time
from pathlib import Path

EP = Path(__file__).resolve().parents[3]
RUN = EP / "runs" / "20261103-gla-b01"
CM = Path(r"E:\program\1project\video\shared\camera-motion\camera_motion.py")
PLAN = RUN / "motion_plan.json"
SHARD_ROOT = RUN / "media" / "affine_shards"
FINAL = RUN / "media" / "affine"
FPS = 30

def main():
    n_shards = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    shots = plan["shots"]
    # 帧数均衡分片(保持顺序)
    frames = [round(s["duration_s"] * FPS) for s in shots]
    total = sum(frames)
    per = math.ceil(total / n_shards)
    shards, cur, acc = [], [], 0
    for s, f in zip(shots, frames):
        cur.append(s); acc += f
        if acc >= per and len(shards) < n_shards:
            shards.append(cur); cur, acc = [], 0
    if cur:
        shards.append(cur)
    SHARD_ROOT.mkdir(parents=True, exist_ok=True)
    procs = []
    t0 = time.time()
    for k, sh in enumerate(shards):
        sp = SHARD_ROOT / f"shard{k}" / "plan.json"
        sp.parent.mkdir(parents=True, exist_ok=True)
        sub = dict(plan); sub["shots"] = sh
        sub["overview"] = f"{plan['overview']} [shard {k}/{len(shards)}]"
        sp.write_text(json.dumps(sub, ensure_ascii=False, indent=2), encoding="utf-8")
        log = open(sp.with_suffix(".log"), "w", encoding="utf-8")
        p = subprocess.Popen([sys.executable, str(CM), str(sp), "--out", str(sp.parent / "out"),
                              "--resume"], stdout=log, stderr=subprocess.STDOUT)
        procs.append((k, p, len(sh), sum(round(s["duration_s"] * FPS) for s in sh)))
        print(f"shard{k}: {len(sh)} shots {sum(round(s['duration_s']*FPS) for s in sh)} frames", flush=True)
    fail = []
    for k, p, n, f in procs:
        rc = p.wait()
        print(f"shard{k} done rc={rc} ({n} shots {f}f) elapsed {time.time()-t0:.0f}s", flush=True)
        if rc != 0:
            fail.append(k)
    if fail:
        raise SystemExit(f"shards failed: {fail}")
    # 汇总
    FINAL.mkdir(parents=True, exist_ok=True)
    copied = 0
    manifest_all = []
    for k in range(len(shards)):
        outd = SHARD_ROOT / f"shard{k}" / "out"
        m = json.loads((outd / "manifest.json").read_text(encoding="utf-8"))
        if m.get("status") != "complete":
            raise SystemExit(f"shard{k} manifest status={m.get('status')}")
        manifest_all.extend(m["shots"])
        for mp4 in outd.glob("*.mp4"):
            if mp4.name.endswith(".partial.mp4"):
                continue
            dst = FINAL / mp4.name
            if not dst.exists():
                shutil.copy2(mp4, dst); copied += 1
    # 帧数校验
    bad = []
    for s in shots:
        dst = FINAL / f"{s['id']}.mp4"
        if not dst.exists():
            bad.append((s["id"], "missing")); continue
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=nb_frames,width,height,avg_frame_rate",
                            "-of", "csv=p=0", str(dst)], capture_output=True, text=True)
        w, h, fr, nf = (r.stdout.strip().split(",") + [""] * 4)[:4]
        want = round(s["duration_s"] * FPS)
        if not nf.isdigit() or int(nf) != want or f"{w}x{h}" != "1920x1080" or fr != "30/1":
            bad.append((s["id"], f"nf={nf} want={want} {w}x{h}@{fr}"))
    print(f"copied {copied}, verified {len(shots)} shots, bad={bad}")
    if bad:
        raise SystemExit(f"frame-check failed: {bad[:10]}")
    print(f"ALL OK in {time.time()-t0:.0f}s -> {FINAL}")

if __name__ == "__main__":
    main()
