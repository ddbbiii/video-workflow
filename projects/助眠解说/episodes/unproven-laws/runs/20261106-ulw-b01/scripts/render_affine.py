# -*- coding: utf-8 -*-
"""Render motion_plan.json with the shared subpixel affine backend in N shards."""
import json, math, shutil, subprocess, sys, time
from pathlib import Path

RUN = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws\runs\20261106-ulw-b01")
CM = Path(r"E:\program\1project\video\shared\camera-motion\camera_motion.py")
PLAN = RUN / "motion_plan.json"
SHARD_ROOT = RUN / "affine_shards"
FINAL = RUN / "clips_affine"
FPS = 30


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    shots = plan["shots"]
    frames = [round(s["duration_s"] * FPS) for s in shots]
    per = math.ceil(sum(frames) / n)
    shards, cur, acc = [], [], 0
    for s, f in zip(shots, frames):
        cur.append(s); acc += f
        if acc >= per and len(shards) < n - 1:
            shards.append(cur); cur, acc = [], 0
    if cur:
        shards.append(cur)
    SHARD_ROOT.mkdir(exist_ok=True)
    procs = []
    t0 = time.time()
    for k, sh in enumerate(shards):
        d = SHARD_ROOT / ("s%d" % k)
        d.mkdir(parents=True, exist_ok=True)
        sp = d / "plan.json"
        sub = dict(plan); sub["shots"] = sh
        sub["overview"] = "unproven-laws affine shard %d" % k
        sp.write_text(json.dumps(sub, ensure_ascii=False, indent=1), encoding="utf-8")
        log = open(d / "run.log", "w", encoding="utf-8")
        p = subprocess.Popen([sys.executable, str(CM), str(sp), "--out", str(d / "out"), "--resume"],
                             stdout=log, stderr=subprocess.STDOUT)
        procs.append((k, p, len(sh), sum(round(s["duration_s"] * FPS) for s in sh)))
        print("shard", k, len(sh), "shots", procs[-1][3], "frames", flush=True)
    bad = []
    for k, p, nsh, nf in procs:
        rc = p.wait()
        print("shard", k, "rc", rc, "elapsed", round(time.time() - t0), flush=True)
        if rc != 0:
            bad.append(k)
    if bad:
        raise SystemExit("shards failed: %s" % bad)
    FINAL.mkdir(exist_ok=True)
    total = 0
    for k in range(len(shards)):
        out = SHARD_ROOT / ("s%d" % k) / "out"
        for mp4 in out.glob("*.mp4"):
            if mp4.name == "overview.mp4":
                continue
            shutil.copy2(mp4, FINAL / mp4.name)
            total += 1
    print("copied", total, "to", FINAL)


if __name__ == "__main__":
    main()
