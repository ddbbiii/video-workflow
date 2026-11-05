# -*- coding: utf-8 -*-
"""为 P1/P2 运镜镜构建 camera_motion 计划 JSON。
时长取自 timeline.json 段落实测；多镜段落按 est 比例分摊。
intro 段落用 est_seconds（片头阶段回填）。
start/end view 由 direction + reference_scale 推导（中心对称，保持16:9）。
输出 runs/.../motion_plan.json，供 shared/camera-motion/camera_motion.py 渲染。"""
from __future__ import annotations
import json, math
from pathlib import Path
EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\newton-to-chaos")
RUN = EP / "runs" / "20261014-ntc-b01"
STILLS16 = EP / "image" / "stills_16x9"
PLAN_OUT = RUN / "motion_plan.json"
TIMELINE = RUN / "timeline.json"
FPS = 30
OUT_W, OUT_H = 1920, 1080

def view_from_scale(zoom):
    # view = crop fraction; zoom 1.0 = full 16:9 region (view w=1,h matches)
    # for a 16:9 source matching 16:9 output, view w=h=1/zoom centered at 0.5
    z = max(1.0, float(zoom))
    w = 1.0 / z
    # since source is 16:9 == output, view h == w * (out_h/out_w) * (src_w/src_h)? source 16:9, output 16:9 => view h = w
    h = w
    x = (1.0 - w) / 2
    y = (1.0 - h) / 2
    return [round(x,5), round(y,5), round(w,5), round(h,5)]

def view_pan(direction, zoom_start, zoom_end, pan_frac=0.18):
    """pan: keep zoom, shift center horizontally. start one side -> end other."""
    z = max(1.0, float(zoom_start))
    w = 1.0/z; h=w
    shift = pan_frac * (1.0 - w)
    if direction == "pan_right":
        sx = max(0, 0.0); ex = min(1-w, shift)
    else:  # pan_left
        sx = min(1-w, shift); ex = 0.0
    return [round(sx,5), round((1-h)/2,5), round(w,5), round(h,5)], \
           [round(ex,5), round((1-h)/2,5), round(w,5), round(h,5)]

def make_curve(dur):
    return {"type": "ramped_linear", "ramp_s": min(0.6, max(0.05, dur/2 - 0.02))}

def main():
    plan_shots = json.loads((EP/"visual"/"SHOT_PLAN.json").read_text(encoding="utf-8"))
    tl = json.loads(TIMELINE.read_text(encoding="utf-8"))
    para_dur = {pid: round(t["end_s"]-t["start_s"],3) for pid,t in tl["paragraphs"].items()}
    # group shots by paragraph for duration split
    by_para = {}
    for s in plan_shots["shots"]:
        by_para.setdefault(s["paragraph_id"], []).append(s)
    motion_shots = []
    for s in plan_shots["shots"]:
        if s.get("shot_class") not in ("image_camera_motion","image_to_video"):
            continue
        pid = s["paragraph_id"]
        src = STILLS16 / f"{s['id']}.jpg"
        if not src.exists():
            continue
        # duration
        if pid in para_dur:
            shots_in_p = by_para[pid]
            total_est = sum(x.get("est_seconds",1) for x in shots_in_p)
            my_est = s.get("est_seconds",1)
            dur = para_dur[pid] * (my_est/max(total_est,1e-6))
        else:
            dur = s.get("est_seconds", 14)
        dur = max(2.0, round(dur,3))
        # snap to frame boundary (FPS) so duration*fps is integral
        dur = round(dur * FPS) / FPS
        if dur < 2/FPS:
            dur = 2/FPS
        # views
        im = s.get("image_motion") or {}
        direction = im.get("direction","push_in")
        scale = im.get("reference_scale")
        if scale and len(scale)==2:
            zs, ze = scale
        else:
            zs, ze = 1.02, 1.14
        if direction == "push_in":
            sv = view_from_scale(zs); ev = view_from_scale(ze)
        elif direction == "pull_out":
            sv = view_from_scale(ze); ev = view_from_scale(zs)
        elif direction in ("pan_left","pan_right"):
            sv, ev = view_pan(direction, zs, ze)
        else:
            sv = view_from_scale(zs); ev = view_from_scale(ze)
        motion_shots.append({
            "id": s["id"], "source": str(src), "duration_s": dur,
            "start_view": sv, "end_view": ev, "curve": make_curve(dur)
        })
    plan = {
        "schema_version": 1, "backend": "affine",
        "output": {"width": OUT_W, "height": OUT_H, "fps": FPS},
        "transition_s": 0,
        "overview": f"newton-to-chaos P1/P2 affine motion {len(motion_shots)} shots",
        "shots": motion_shots
    }
    PLAN_OUT.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"plan written: {len(motion_shots)} shots -> {PLAN_OUT.name}")
    print("total motion seconds:", round(sum(s['duration_s'] for s in motion_shots),1))

if __name__=="__main__":
    main()
