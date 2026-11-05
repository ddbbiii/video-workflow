# -*- coding: utf-8 -*-
"""siffre 正文运镜与装配计划(2026-10-20 装配任务书口径)。

真源 = runs/20261018-sbt-b01/timeline.json 三级实测时间轴(不是 SHOT_PLAN est)。

窗口算法(画面与旁白逐段同步):
- 每镜在所属段落实测区间 [start_s,end_s] 内按 est 权重分摊自己的份额;
- 镜 i 的在屏窗口 = [前一镜窗口末尾, 下一镜所属段落实测 start_s](首镜从 0 起,
  末镜到 body_seconds);段间/章间留白与 102 个骑乘段旁白由前一镜顺势延长覆盖
  (REPORT_audio §1 口径:骑乘段声音落在相邻主段镜头画面上);
- 全部边界取整到 30fps 帧格,窗口帧数总和 = 正文总帧数(音视差 ≤1 帧)。

i2v 镜处置(硬规则,REPORT.md 剧本侧裁决 2026-10-20):
- c6-s07 按 V1 使用,不加尾帧推拉(其窗口 4.20s<12.04s,纯截取);
- 窗口 ≤12.0417s:i2v 原速截取直接使用;
- 需求>12.04s:优先自身尾帧停留(V3, tpad clone)补足;尾停 ≤13.0s
  (visual-motion.md: 尾帧不超过原生视频时长 12.0417s;≤13.0s 为裁决口径内的
  边际容差,逐镜记录偏差);c5-s03 允许一次 V5-C 循环(实际超出仅 0.66s,
  循环不经济,按 V3 尾停执行并记录);
- 尾停需求 >13.0s:材料不足,整镜退回 P 系(原图 affine 全窗单向运镜)+记录
  fallback,不动 SHOT_PLAN 语义(本 run v1: c1-s03/c8-s14/ep-s04);
- 【v2,第二轮裁决 2026-10-20】c8-s14/ep-s04 不再退 P 系,改 V5-C 单次首尾
  叠化循环:i2v 原速一遍(361f=12.033s)+ 拉伸循环遍补足全窗(叠化 0.4667s),
  二者为连续性环境运动,白名单允许循环;c1-s03(101.4s 长窗)维持 P 系慢推。
- 【v2,第二轮裁决 2026-10-20】c6-s07→c6-s08 切口(992.37s,亮阶跃 46→113)
  加 0.4667s 交叉叠化:c6-s08 运镜重渲为 83f(同起止 view 匀滑伸展),叠化后
  合成段 195f = 126+69,切口前后镜头窗口与全片时间轴不变(junctions 记录)。

P1/P2 幅度按 visual-motion 白名单:单向不往返,view 幅度取 SHOT_PLAN
reference_scale;P 系窗口>份额时运镜按全窗匀滑伸展(速度变缓,符合助眠低刺激),
不产生中途冻结。pan_down/pan_up 按垂直平移处理。

输出:
- runs/20261018-sbt-b01/motion_plan.json        -> shared/camera-motion 渲染(95 P + 3 fallback)
- runs/20261018-sbt-b01/manifests/assembly_manifest.json -> 135 镜逐镜装配真源(15 号脚本消费)
"""
from __future__ import annotations
import json
from pathlib import Path

EP = Path(__file__).resolve().parents[3]
RUN = EP / "runs" / "20261018-sbt-b01"
STILLS16 = EP / "image" / "stills_16x9"
PLAN_OUT = RUN / "motion_plan.json"
MANIFEST_OUT = RUN / "manifests" / "assembly_manifest.json"
TIMELINE = RUN / "timeline.json"
I2V_DIR = RUN / "i2v"
FPS = 30
OUT_W, OUT_H = 1920, 1080
I2V_NATIVE_S = 12.041667          # 289f @ 24fps
I2V_NATIVE_F30 = 361              # 289f@24fps 经 fps=30 换算的实测帧数(12.0333s)
HOLD_CAP_S = 13.0                 # >此值退回 P 系(白名单原生时长上限 12.0417 + 边际容差)
C6_S07 = "c6-s07"
C5_S03 = "c5-s03"
# v2(第二轮裁决 2026-10-20): V5-C 单次首尾叠化循环
V5C_SHOTS = {"c8-s14", "ep-s04"}  # 连续性环境运动,白名单允许循环;c1-s03 维持 P 系
XFADE_F = 14                      # 叠化 14 帧 = 0.4667s(~0.45s)
# v2(第二轮裁决 2026-10-20): c6-s07→c6-s08 亮切口柔化(992.37s, 46→113)
JUNCTION = {                      # 写入 manifest junctions 节,15 号脚本消费
    "between": ["c6-s07", "c6-s08"],
    "at_s": 992.3667,
    "mode": "xfade",
    "xfade_frames": XFADE_F,
    "second_ext_frames": 83,      # c6-s08 由 69f 重渲为 83f(同起止 view 全窗匀滑)
    "composite_frames": 126 + 83 - XFADE_F,  # 195 = 126+69,切口叠化不入账,时间轴不变
}

def view_from_scale(zoom):
    z = max(1.0, float(zoom))
    w = 1.0 / z
    x = (1.0 - w) / 2
    y = (1.0 - w) / 2
    return [round(x, 5), round(y, 5), round(w, 5), round(w, 5)]

def view_pan_h(direction, zoom, pan_frac=0.18):
    """水平平移:zoom 恒定,窗口中心横向移动。"""
    w = 1.0 / max(1.0, float(zoom))
    h = w
    shift = pan_frac * (1.0 - w)
    y = round((1 - h) / 2, 5)
    if direction == "pan_right":
        sv = [0.0, y, round(w, 5), round(h, 5)]
        ev = [round(min(1 - w, shift), 5), y, round(w, 5), round(h, 5)]
    else:  # pan_left
        sv = [round(min(1 - w, shift), 5), y, round(w, 5), round(h, 5)]
        ev = [0.0, y, round(w, 5), round(h, 5)]
    return sv, ev

def view_pan_v(direction, zoom, pan_frac=0.18):
    """垂直平移:zoom 恒定,窗口中心纵向移动。"""
    w = 1.0 / max(1.0, float(zoom))
    h = w
    shift = pan_frac * (1.0 - w)
    x = round((1 - w) / 2, 5)
    if direction == "pan_down":
        sv = [x, 0.0, round(w, 5), round(h, 5)]
        ev = [x, round(min(1 - h, shift), 5), round(w, 5), round(h, 5)]
    else:  # pan_up
        sv = [x, round(min(1 - h, shift), 5), round(w, 5), round(h, 5)]
        ev = [x, 0.0, round(w, 5), round(h, 5)]
    return sv, ev

def make_curve(dur):
    return {"type": "ramped_linear", "ramp_s": min(0.6, max(0.05, dur / 2 - 0.02))}

def views_for(shot, fallback=False, window_s=0.0):
    im = shot.get("image_motion") or {}
    direction = im.get("direction", "push_in")
    scale = im.get("reference_scale")
    if scale and len(scale) == 2:
        zs, ze = float(scale[0]), float(scale[1])
    elif fallback:
        # i2v 镜退 P 系:SHOT_PLAN 无 image_motion,按白名单幅度给缓和单向推近;
        # 超长窗(>60s)用本计划已用的最大幅度 1.18 保持缓慢可感。
        zs = 1.02
        ze = 1.18 if window_s > 60 else 1.14
    else:
        zs, ze = 1.02, 1.14
    if direction == "push_in":
        return view_from_scale(zs), view_from_scale(ze)
    if direction == "pull_out":
        return view_from_scale(ze), view_from_scale(zs)
    if direction in ("pan_left", "pan_right"):
        return view_pan_h(direction, zs)
    if direction in ("pan_down", "pan_up"):
        return view_pan_v(direction, zs)
    return view_from_scale(zs), view_from_scale(ze)

def main():
    plan_shots = json.loads((EP / "visual" / "SHOT_PLAN.json").read_text(encoding="utf-8"))
    tl = json.loads(TIMELINE.read_text(encoding="utf-8"))
    paras = tl["paragraphs"]
    body_s = tl["body_seconds"]
    total_frames = round(body_s * FPS)

    by_para: dict[str, list] = {}
    for s in plan_shots["shots"]:
        by_para.setdefault(s["paragraph_id"], []).append(s)

    # 1) 每镜段落内份额(实测区间按 est 权重分摊)
    shares = []
    for s in plan_shots["shots"]:
        pid = s["paragraph_id"]
        if not pid or pid not in paras:
            raise SystemExit(f"{s['id']}: paragraph_id 缺失或不在 timeline,先完成 01/02/04。")
        p = paras[pid]
        grp = by_para[pid]
        tot = sum(x.get("est_seconds", 1) for x in grp)
        c = p["start_s"]
        d = 0.0
        for x in grp:
            d = (p["end_s"] - p["start_s"]) * (x.get("est_seconds", 1) / max(tot, 1e-6))
            if x["id"] == s["id"]:
                break
            c += d
        shares.append((s, c, c + d))

    # 2) 在屏窗口(帧格取整):窗口末 = 下一镜头段落 start;首镜起点 0;末镜到正文末
    starts_f = [round(sh[1] * FPS) for sh in shares]     # 本镜理想起点(下一镜的硬边界)
    bounds_f = []
    prev = 0
    for i, (s, a, b) in enumerate(shares):
        nxt = starts_f[i + 1] if i + 1 < len(shares) else total_frames
        end = max(nxt, round(a * FPS), prev + 2)
        bounds_f.append((prev, end))
        prev = end
    assert prev == total_frames, f"窗口帧数总和 {prev} != 正文帧数 {total_frames}"

    # 3) 逐镜裁决 + 计划
    motion_shots, manifest_shots = [], []
    fallbacks, deviations = [], []
    for i, (s, a, b) in enumerate(shares):
        sid = s["id"]
        cls = s.get("shot_class")
        strategy = s.get("strategy")
        f0, f1 = bounds_f[i]
        frames = f1 - f0
        dur = frames / FPS
        entry = {
            "id": sid, "section": s["section"], "paragraph_id": s["paragraph_id"],
            "shot_class": cls, "strategy": strategy,
            "window_start_s": round(f0 / FPS, 4), "window_end_s": round(f1 / FPS, 4),
            "total_frames": frames, "total_seconds": round(dur, 4),
            "tail_extension_mode": "none", "tail_extension_seconds": 0.0,
            "motion_seconds": 0.0, "source": None, "notes": [],
        }
        if cls == "image_to_video":
            i2v_path = I2V_DIR / f"{sid}.mp4"
            if not i2v_path.exists():
                raise SystemExit(f"{sid}: i2v 缺失且不在本计划兜底范围,先排查 runs/.../i2v")
            need_hold = dur - I2V_NATIVE_S
            if sid == C6_S07:
                # 裁决:V1 使用,不加尾帧推拉;窗口 4.20s 纯截取
                entry.update(source=str(i2v_path), motion_seconds=round(min(dur, I2V_NATIVE_S), 4),
                             notes=["裁决2026-10-20: V1 原速截取,无尾帧推拉"])
                assert need_hold <= 0, "c6-s07 窗口超原生,违背 V1 裁决,需回裁决"
            elif need_hold <= 0.01:
                entry.update(source=str(i2v_path), motion_seconds=round(dur, 4))
            elif need_hold <= HOLD_CAP_S:
                hold = round(dur - I2V_NATIVE_S, 4)
                entry.update(source=str(i2v_path), tail_extension_mode="hold",
                             tail_extension_seconds=hold,
                             motion_seconds=round(I2V_NATIVE_S, 4))
                if sid == C5_S03:
                    entry["notes"].append(
                        f"裁决允许 V5-C 循环一次;实际超出仅 {hold:.2f}s,循环不经济,按 V3 尾停执行")
                if hold > I2V_NATIVE_S:
                    entry["notes"].append(
                        f"尾停 {hold:.2f}s 超原生时长 {I2V_NATIVE_S:.2f}s(边际容差内,已记录)")
                    deviations.append((sid, hold))
            elif sid in V5C_SHOTS:
                # v2 第二轮裁决: 不退 P 系,V5-C 单次首尾叠化循环补足全窗
                pass_b = frames - I2V_NATIVE_F30 + XFADE_F
                entry.update(
                    source=str(i2v_path), strategy="V5C",
                    tail_extension_mode="loop_xfade", tail_extension_seconds=0.0,
                    motion_seconds=round(dur, 4),
                    xfade_frames=XFADE_F,
                    v5c={"native_pass_frames": I2V_NATIVE_F30,
                         "native_pass_s": round(I2V_NATIVE_F30 / FPS, 4),
                         "loop_pass_frames": pass_b,
                         "loop_pass_s": round(pass_b / FPS, 4),
                         "loop_stretch": round(pass_b / I2V_NATIVE_F30, 4),
                         "tail_hold_s": 0.0},
                    notes=[f"v2 第二轮裁决 2026-10-20: 需尾停 {need_hold:.1f}s>{HOLD_CAP_S}s 上限,"
                           f"不退 P 系,改 V5-C 一次首尾叠化循环——原速 {I2V_NATIVE_F30/FPS:.2f}s"
                           f"({I2V_NATIVE_F30}f) + 拉伸循环遍 {pass_b/FPS:.2f}s({pass_b}f,"
                           f"×{pass_b/I2V_NATIVE_F30:.2f}) 补足 {dur:.1f}s 窗口,叠化 {XFADE_F/FPS:.4f}s,"
                           f"无需尾停;全窗均为 i2v 模型动态(原速+慢放),motion_seconds 记全窗"])
            else:
                # 材料不足:整镜退回 P 系(裁决口径:允许退回 P 系静帧+停留/运镜)
                src = STILLS16 / f"{sid}.jpg"
                if not src.exists():
                    raise SystemExit(f"{sid}: fallback 需要静帧 {src} 缺失")
                sv, ev = views_for(s, fallback=True, window_s=dur)
                motion_shots.append({
                    "id": sid, "source": str(src), "duration_s": dur,
                    "start_view": sv, "end_view": ev, "curve": make_curve(dur)})
                entry.update(source=str(src), delivery_class="image_camera_motion",
                             fallback_from="image_to_video", motion_seconds=round(dur, 4),
                             notes=[f"窗口 {dur:.1f}s 需尾停 {need_hold:.1f}s >{HOLD_CAP_S}s 上限,"
                                    f"整镜退回 P 系单向运镜;i2v 成片保留未用"])
                fallbacks.append((sid, round(dur, 1), round(need_hold, 1)))
        else:
            src = STILLS16 / f"{sid}.jpg"
            if not src.exists():
                raise SystemExit(f"{sid}: 静帧 {src} 缺失(11 未完成?)")
            sv, ev = views_for(s)
            motion_shots.append({
                "id": sid, "source": str(src), "duration_s": dur,
                "start_view": sv, "end_view": ev, "curve": make_curve(dur)})
            entry.update(source=str(src), motion_seconds=round(dur, 4),
                         tail_extension_mode=("span" if dur > (b - a) + 0.05 else "none"))
            if dur > (b - a) + 0.05:
                entry["notes"].append(
                    f"骑乘/留白延长:运镜按全窗 {dur:.1f}s 匀滑伸展(份额 {b-a:.1f}s),单向不往返")
            if sid == JUNCTION["between"][1]:
                entry["notes"].append(
                    f"v2 第二轮裁决: 与 {JUNCTION['between'][0]} 切口 @~{JUNCTION['at_s']}s 亮阶跃以 "
                    f"{XFADE_F/FPS:.2f}s 叠化柔化(见 manifest junctions);本镜重渲 "
                    f"{JUNCTION['second_ext_frames']}f(同起止 view 全窗匀滑伸展),窗口/时间轴不变")
        manifest_shots.append(entry)

    # 4) 写 motion_plan(仅 affine 镜:95 P + fallback)
    plan = {
        "schema_version": 1, "backend": "affine",
        "output": {"width": OUT_W, "height": OUT_H, "fps": FPS},
        "transition_s": 0,
        "overview": f"siffre-beyond-time P1/P2+fallback affine motion {len(motion_shots)} shots "
                    f"(timeline 20261018-sbt-b01 实测窗口)",
        "shots": motion_shots,
    }
    PLAN_OUT.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    # 5) 汇总统计
    n_i2v_direct = sum(1 for e in manifest_shots if e["shot_class"] == "image_to_video"
                       and not e.get("fallback_from"))
    i2v_motion = sum(e["motion_seconds"] for e in manifest_shots
                     if e["shot_class"] == "image_to_video" and not e.get("fallback_from"))
    p_total = sum(e["total_seconds"] for e in manifest_shots
                  if e["shot_class"] == "image_camera_motion")
    fb_total = sum(e["total_seconds"] for e in manifest_shots if e.get("fallback_from"))
    hold_total = sum(e["tail_extension_seconds"] for e in manifest_shots)
    summary = {
        "total_shots": len(manifest_shots), "total_frames": total_frames,
        "body_seconds_timeline": body_s, "body_seconds_frames": round(total_frames / FPS, 4),
        "i2v_shots_delivered_as_i2v": n_i2v_direct,
        "i2v_model_motion_seconds": round(i2v_motion, 1),
        "i2v_share_of_body": round(i2v_motion / (total_frames / FPS), 4),
        "affine_p_shots": sum(1 for e in manifest_shots if e["shot_class"] == "image_camera_motion"),
        "affine_p_seconds": round(p_total, 1),
        "fallback_shots": [f[0] for f in fallbacks],
        "fallback_seconds": round(fb_total, 1),
        "tail_hold_total_seconds": round(hold_total, 1),
        "fallbacks_detail": [{"id": x, "window_s": y, "hold_needed_s": z} for x, y, z in fallbacks],
        "tail_hold_deviations_over_native": [{"id": x, "hold_s": y} for x, y in deviations],
        "v5c_shots": [e["id"] for e in manifest_shots
                      if e.get("tail_extension_mode") == "loop_xfade"],
        "v5c_seconds": round(sum(e["total_seconds"] for e in manifest_shots
                                 if e.get("tail_extension_mode") == "loop_xfade"), 1),
        "junctions": [dict(JUNCTION, note="切口叠化合成段替代相邻两镜入 concat,总帧数不变")],
    }
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUT.write_text(json.dumps(
        {"schema": "siffre-body-assembly-v2", "fps": FPS, "width": OUT_W, "height": OUT_H,
         "i2v_native_s": I2V_NATIVE_S, "i2v_native_f30": I2V_NATIVE_F30, "hold_cap_s": HOLD_CAP_S,
         "source_of_truth": "runs/20261018-sbt-b01/timeline.json",
         "summary": summary, "shots": manifest_shots,
         "junctions": [dict(JUNCTION, note="切口叠化合成段替代相邻两镜入 concat,总帧数不变")]},
        ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"motion_plan: {len(motion_shots)} affine shots -> {PLAN_OUT.name}")
    print(f"manifest: {len(manifest_shots)} shots -> {MANIFEST_OUT}")
    print(f"body: {total_frames} frames = {total_frames/FPS:.3f}s (timeline {body_s}s)")
    print(f"i2v direct {n_i2v_direct} shots, model motion {i2v_motion:.1f}s "
          f"({i2v_motion/(total_frames/FPS)*100:.1f}% of body)")
    print(f"fallback to P: {fallbacks}")
    print(f"tail-hold deviations over native: {deviations}")
    print(f"tail hold total: {hold_total:.1f}s")

if __name__ == "__main__":
    main()
