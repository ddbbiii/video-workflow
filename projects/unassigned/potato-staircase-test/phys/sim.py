#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G1 仿真驱动：固定 1/480 子步、接触/冲量事件、数值 QA。

流程：settle（让挡边凹处的静止位置由物理自己决定）→ idle（静止稳定性）
→ push（只给最上面土豆一次初速）→ run（记录轨迹与冲击事件）。
"""
from __future__ import annotations

import math
import pymunk

from .scene import (Scene, World, CT_POTATO, CT_STAIR, point_seg_dist,
                    W_CANVAS, H_CANVAS)

FPS = 60
SIM_HZ = 480
SUBSTEPS = SIM_HZ // FPS          # 8
DT = 1.0 / SIM_HZ

IMPULSE_EPS = 8.0                 # 低于这个冲量当作静止接触，不算“撞击”
STOP_V = 6.0
STOP_W = 0.25


def _v2(t) -> tuple[float, float]:
    return (float(t[0]), float(t[1]))


def _rel_speed(arb) -> float:
    """接触点处的相对速度大小（pymunk 7 的 Arbiter 没有 relative_velocity）。"""
    try:
        a, b = arb.bodies
    except Exception:
        return 0.0
    pts = arb.contact_point_set.points
    if not pts:
        return (a.velocity - b.velocity).length
    p = pts[0].point_a
    ra = (p[0] - a.position.x, p[1] - a.position.y)
    rb = (p[0] - b.position.x, p[1] - b.position.y)
    va = (a.velocity.x - a.angular_velocity * ra[1],
          a.velocity.y + a.angular_velocity * ra[0])
    vb = (b.velocity.x - b.angular_velocity * rb[1],
          b.velocity.y + b.angular_velocity * rb[0])
    return math.hypot(va[0] - vb[0], va[1] - vb[1])



def simulate(sc: Scene, *, settle: float = 1.0, idle: float = 1.2,
             t_max: float = 22.0, quiet_hold: float = 1.5,
             verbose: bool = False) -> dict:
    w = World(sc)
    space = w.space

    sim_t = 0.0
    raw: list[dict] = []
    pair_open: dict[tuple, float] = {}

    idx_of = {id(p["shape"]): p["idx"] for p in w.potatoes}

    def post_pp(arb, space_, data):
        a, b = arb.shapes
        ia = idx_of.get(id(a), -1)
        ib = idx_of.get(id(b), -1)
        mag = float(arb.total_impulse.length)
        if mag < IMPULSE_EPS:
            return
        pts = arb.contact_point_set.points
        cp = _v2(pts[0].point_a) if pts else (0.0, 0.0)
        raw.append({"t": sim_t, "kind": "potato-potato", "a": ia, "b": ib,
                    "impulse": mag, "normal": _v2(arb.normal), "point": cp,
                    "rel_v": _rel_speed(arb)})
        pair_open[(min(ia, ib), max(ia, ib))] = sim_t

    def post_ps(arb, space_, data):
        a, b = arb.shapes
        mag = float(arb.total_impulse.length)
        # 静止接触每个子步都有恒定冲量，靠法向相对速度区分“落地”
        if mag < IMPULSE_EPS or _rel_speed(arb) < 80.0:
            return
        pa = idx_of.get(id(a))
        if pa is None:
            pa = idx_of.get(id(b))
        pts = arb.contact_point_set.points
        cp = _v2(pts[0].point_a) if pts else (0.0, 0.0)
        raw.append({"t": sim_t, "kind": "potato-stair", "a": pa, "b": -1,
                    "impulse": mag, "normal": _v2(arb.normal), "point": cp,
                    "rel_v": _rel_speed(arb)})

    space.on_collision(CT_POTATO, CT_POTATO, post_solve=post_pp)
    space.on_collision(CT_POTATO, CT_STAIR, post_solve=post_ps)

    def step():
        nonlocal sim_t
        sim_t += DT
        space.step(DT)
        if sc.roll_resist > 0:
            _roll_resist(w, sc.roll_resist, DT)

    # ---------------------------------------------------------------- settle
    n = int(round(settle * SIM_HZ))
    for _ in range(n):
        step()
    rest = [{"pos": _v2(p["body"].position), "angle": float(p["body"].angle)}
            for p in w.potatoes]
    for p in w.potatoes:
        p["body"].velocity = (0, 0)
        p["body"].angular_velocity = 0

    # ------------------------------------------------------------------ idle
    n = int(round(idle * SIM_HZ))
    for _ in range(n):
        step()
    idle_drift = []
    for i, p in enumerate(w.potatoes):
        b = p["body"]
        d = math.dist(_v2(b.position), rest[i]["pos"])
        idle_drift.append({"idx": i, "drift": d,
                           "dangle": float(b.angle) - rest[i]["angle"]})
        b.velocity = (0, 0)
        b.angular_velocity = 0
        b.position = rest[i]["pos"]
        b.angle = rest[i]["angle"]

    # ------------------------------------------------------------------ push
    raw.clear()
    pair_open.clear()
    sim_t = 0.0
    t0_note = "push"
    w.potatoes[0]["body"].velocity = (sc.push_v, 0.0)
    if sc.push_roll:
        w.potatoes[0]["body"].angular_velocity = sc.push_v / sc.radii[0]

    trace = {"t": [], "pos": [], "vel": [], "angle": [], "angvel": [],
             "ground": [], "pen": []}
    quiet = 0.0
    frames = int(round(t_max * FPS))
    for f in range(frames):
        for _ in range(SUBSTEPS):
            step()
        poses, vels, angs, angv, ground = [], [], [], [], []
        for p in w.potatoes:
            b = p["body"]
            poses.append(_v2(b.position))
            vels.append(_v2(b.velocity))
            angs.append(float(b.angle))
            angv.append(float(b.angular_velocity))
            px, py = b.position
            md = min(point_seg_dist(px, py, a, c) - 1.5 - p["r"]
                     for a, c, _, _ in w.stair_segs)
            ground.append(1 if md < 0.6 else 0)
        pen, _ = w.penetration()
        trace["t"].append(sim_t)
        trace["pos"].append(poses)
        trace["vel"].append(vels)
        trace["angle"].append(angs)
        trace["angvel"].append(angv)
        trace["ground"].append(ground)
        trace["pen"].append(pen)

        moving = any(math.hypot(*v) > STOP_V or abs(av) > STOP_W
                     for v, av in zip(vels, angv))
        quiet = 0.0 if moving else quiet + 1.0 / FPS
        if quiet > quiet_hold:
            break

    # --------------------------------------------------------------- events
    events = _group_events(raw)
    impacts = [e for e in events if e["kind"] == "potato-potato"]
    landings = [e for e in events if e["kind"] == "potato-stair"]

    # 每次撞击的接收者：分离时间、撞前速度、撞后速度
    for e in impacts:
        ta, tb = e["a"], e["b"]
        f = min(range(len(trace["t"])), key=lambda k: abs(trace["t"][k] - e["t"]))
        e["i_a"], e["i_b"] = ta, tb
        e["pre"] = [round(_spd(trace["vel"][max(0, f - 2)][ta]), 1),
                    round(_spd(trace["vel"][max(0, f - 2)][tb]), 1)]
        # 撞后冲量效果：取 0.15s 窗口内的峰值（接触可能持续几十毫秒）
        w1 = min(f + int(0.15 * FPS), len(trace["t"]) - 1)
        e["post"] = [round(max(_spd(trace["vel"][k][ta]) for k in range(f, w1 + 1)), 1),
                     round(max(_spd(trace["vel"][k][tb]) for k in range(f, w1 + 1)), 1)]
        # 撞后 0.2s 内是否分离
        ra, rb = w.potatoes[ta]["r"], w.potatoes[tb]["r"]
        sep_dt = None
        for k in range(f, min(f + int(0.5 * FPS), len(trace["t"]))):
            d = math.dist(trace["pos"][k][ta], trace["pos"][k][tb])
            if d > ra + rb + 0.8:
                sep_dt = round(trace["t"][k] - e["t"], 3)
                break
        e["sep_dt"] = sep_dt
        e["max_pen"] = round(min(trace["pen"][max(0, f - 2):f + 3]), 2)

    for e in landings:
        p = e["point"]
        e["tread"] = w.tread_of(p[0])

    # ------------------------------------------------------------- QA metrics
    max_pen = min(trace["pen"]) if trace["pen"] else 0.0
    worst_frame = trace["t"][trace["pen"].index(max_pen)] if trace["pen"] else 0.0

    # 滚动/打滑：着地且速度足够的帧，slip = v_x - w*r
    slip_n, slip_sum, slip_max = 0, 0.0, 0.0
    for k, t in enumerate(trace["t"]):
        for i, p in enumerate(w.potatoes):
            if not trace["ground"][k][i]:
                continue
            vx, vy = trace["vel"][k][i]
            sp = math.hypot(vx, vy)
            if sp < 20:
                continue
            s = vx - trace["angvel"][k][i] * p["r"]
            slip_n += 1
            slip_sum += abs(s) / sp
            slip_max = max(slip_max, abs(s) / sp)

    # 顺序 / 自启动 / 跨台阶
    order_ok = True
    self_start = []
    for i in range(1, sc.n_potato):
        hit = next((e for e in impacts if i in (e["a"], e["b"])), None)
        if hit is None:
            order_ok = False
            self_start.append({"idx": i, "issue": "no impact"})
            continue
        pre = hit["pre"][0] if hit["a"] == i else hit["pre"][1]
        if pre > 8.0:
            order_ok = False
            self_start.append({"idx": i, "issue": "self-start", "pre_speed": pre})

    # 每个土豆落地过的台阶序列
    land_seq = {i: [] for i in range(sc.n_potato)}
    for e in landings:
        land_seq[e["a"]].append(e["tread"])
    skip = []
    for i, seq in land_seq.items():
        sq = sorted(set(seq))
        jumps = [b - a for a, b in zip(sq, sq[1:])]
        if any(j > 1 for j in jumps):
            skip.append({"idx": i, "seq": seq, "jumps": jumps})

    max_drift = max(d["drift"] for d in idle_drift)
    sep_all = [e["sep_dt"] for e in impacts]
    relay_pairs = [{"pair": (i - 1, i),
                    "hit": any({e["a"], e["b"]} == {i - 1, i} for e in impacts)}
                   for i in range(1, sc.n_potato)]
    last = sc.n_potato - 1
    last_moved = any(
        math.dist(trace["pos"][k][last], rest[last]["pos"]) > 10
        for k in range(len(trace["t"])))
    chain_ok = all(r["hit"] for r in relay_pairs) and order_ok and last_moved
    slip_mean = round(slip_sum / slip_n, 3) if slip_n else None

    checks = [
        {"name": "静止稳定 1.2s 漂移<1px", "ok": max_drift < 1.0,
         "v": round(max_drift, 2)},
        {"name": "最大穿透 > -2px", "ok": max_pen > -2.0, "v": round(max_pen, 2)},
        {"name": "逐对撞击齐全", "ok": all(r["hit"] for r in relay_pairs),
         "v": [r["hit"] for r in relay_pairs]},
        {"name": "无自启动", "ok": order_ok and not self_start,
         "v": self_start or "ok"},
        {"name": "撞击后分离", "ok": bool(impacts) and all(s is not None for s in sep_all),
         "v": sep_all},
        {"name": "滚动指数<0.35", "ok": slip_mean is not None and slip_mean < 0.35,
         "v": slip_mean},
        {"name": "不跨台阶", "ok": not skip, "v": skip or "ok"},
    ]

    return {
        "scene": sc.to_dict(),
        "rest": rest,
        "idle_drift": idle_drift,
        "trace": trace,
        "impacts": impacts,
        "landings": landings,
        "max_penetration": round(max_pen, 2),
        "max_penetration_at": round(worst_frame, 2),
        "slip_mean": round(slip_sum / slip_n, 3) if slip_n else None,
        "slip_max": round(slip_max, 3) if slip_n else None,
        "slip_samples": slip_n,
        "order_ok": order_ok,
        "relay_pairs": relay_pairs,
        "self_start": self_start,
        "land_seq": land_seq,
        "cross_step": skip,
        "chain_ok": chain_ok,
        "checks": checks,
        "pass": all(c["ok"] for c in checks),
        "n_impacts": len(impacts),
        "duration": round(trace["t"][-1], 2) if trace["t"] else 0.0,
    }


def _spd(v) -> float:
    return math.hypot(v[0], v[1])


def _roll_resist(w: World, decel: float, dt: float) -> None:
    """滚动阻力：只在贴地时作用，线速度与角速度同比例衰减（不引入打滑）。"""
    for p in w.potatoes:
        b = p["body"]
        px, py = b.position
        md = min(point_seg_dist(px, py, a, c) - 1.5 - p["r"]
                 for a, c, _, _ in w.stair_segs)
        if md > 1.5:
            continue
        vx, vy = b.velocity
        sp = math.hypot(vx, vy)
        if sp <= 1e-9:
            continue
        k = max(0.0, 1.0 - decel * dt / sp)
        b.velocity = (vx * k, vy * k)
        b.angular_velocity *= k


def _group_events(raw: list[dict], gap: float = 0.06) -> list[dict]:
    """把逐子步的冲量按 (pair,kind) 合并成一次撞击。"""
    out: list[dict] = []
    open_ev: dict[tuple, dict] = {}
    for r in raw:
        key = (r["kind"], min(r["a"], r["b"]), max(r["a"], r["b"]))
        ev = open_ev.get(key)
        if ev is None or r["t"] - ev["_last"] > gap:
            ev = {"kind": r["kind"], "a": r["a"], "b": r["b"], "t": r["t"],
                  "impulse": r["impulse"], "normal": r["normal"],
                  "point": r["point"], "rel_v": r["rel_v"],
                  "_last": r["t"], "_n": 1, "_imp": r["impulse"], "_imp_sum": r["impulse"]}
            open_ev[key] = ev
            out.append(ev)
        else:
            ev["_last"] = r["t"]
            ev["_n"] += 1
            ev["_imp_sum"] += r["impulse"]
            if r["impulse"] > ev["impulse"]:
                ev["impulse"] = r["impulse"]
                ev["point"] = r["point"]
                ev["normal"] = r["normal"]
                ev["rel_v"] = r["rel_v"]
    for ev in out:
        ev["peak_impulse"] = round(ev["impulse"], 1)
        ev["n_steps"] = ev["_n"]
        ev["t"] = round(ev["t"], 3)
        for k in ("_last", "_n", "_imp", "_imp_sum"):
            ev.pop(k, None)
    return out
