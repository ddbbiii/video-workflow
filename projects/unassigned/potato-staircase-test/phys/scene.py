#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G1 物理场景：真实阶梯碰撞体 + 刚体土豆。

这里没有任何“轨道 / 按键释放 / 第 i 撞第 i+1”的特例：
阶梯是静态 Segment（踏面 + 竖板 + 前沿挡边），土豆是 Circle 刚体，
接力完全由 Pymunk 的通用冲量求解产生。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict, replace

import pymunk

CT_POTATO = 1
CT_STAIR = 2

W_CANVAS, H_CANVAS = 1080, 1920

# 土豆贴图是椭圆：宽 2r、高约 1.68r（1280x1051 内 bbox 1225x1023）
POTATO_ASPECT = 0.835


@dataclass
class Scene:
    key: str = "A"
    label: str = "水平踏面"
    note: str = ""

    n_potato: int = 3
    radii: tuple = (24.0, 31.0, 40.0)

    step_w: float = 88.0
    step_h: float = 125.0
    x0: float = 200.0
    y0: float = 560.0

    slope_deg: float = 0.0      # 踏面下坡角（右低）
    lip_h: float = 0.0          # 踏面前沿挡边高度；0 = 无挡边
    rail_x: float = 1000.0      # 末端挡墙

    receiver_frac: float = 0.55  # 仅无挡边时使用：接收者中心 = 踏面左端 + frac*step_w

    density: float = 0.012
    friction: float = 0.9
    elasticity: float = 0.55      # 两球相乘 ≈0.30 有效恢复系数：撞人者明显减速+回弹
    gravity: float = 1100.0
    roll_resist: float = 40.0    # 滚动阻力（px/s² 的等效减速度）：真实土豆会自己停住
    push_v: float = 200.0
    push_roll: bool = True       # 初速按纯滚动给（ω=v/r），避免滑动摩擦吃掉 1/3 动能
    iterations: int = 20

    def to_dict(self):
        return asdict(self)


class World:
    """建世界 + 记录几何，供渲染/QA 复用。"""

    def __init__(self, sc: Scene):
        self.sc = sc
        self.n_treads = sc.n_potato + 1
        self.space = pymunk.Space()
        self.space.gravity = (0.0, sc.gravity)
        self.space.iterations = sc.iterations
        self.space.collision_slop = 0.3
        self.space.damping = 0.9995

        self.stair_shapes: list = []
        self.stair_segs: list[tuple] = []   # (a, b, tread_index, kind)
        self.outline: list[tuple] = []      # 折线，用于调试视图描线
        self.potatoes: list[dict] = []

        self._build_stairs()
        self._build_potatoes()

    # ---------------------------------------------------------------- geometry
    def tread_x(self, i: int) -> tuple[float, float]:
        sc = self.sc
        xs = sc.x0 + i * sc.step_w
        if i == self.n_treads - 1:            # 最后一级是落地区，加宽
            xe = sc.rail_x
        else:
            xe = xs + sc.step_w
        return xs, xe

    def tread_base_y(self, i: int) -> float:
        return self.sc.y0 + i * self.sc.step_h

    def surface_y(self, i: int, x: float) -> float:
        xs, _ = self.tread_x(i)
        return self.tread_base_y(i) + (x - xs) * math.tan(math.radians(self.sc.slope_deg))

    def edge(self, i: int) -> tuple[float, float]:
        _, xe = self.tread_x(i)
        return xe, self.surface_y(i, xe)

    def tread_of(self, x: float) -> int:
        sc = self.sc
        i = int(math.floor((x - sc.x0) / sc.step_w))
        return max(0, min(self.n_treads - 1, i))

    def lip_arc(self, i: int) -> list[tuple[float, float]]:
        """前沿小圆弧挡边：半圆，apex 比踏面高 lip_h，两侧各 lip_h 收回。"""
        if self.sc.lip_h <= 0:
            return []
        xe, ye = self.edge(i)
        R = self.sc.lip_h
        cx = xe - R
        cy = self.surface_y(i, cx)
        pts = []
        n = 8
        for k in range(n + 1):
            a = math.pi + math.pi * k / n       # pi -> 2pi，y 向上隆起
            pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))
        return pts

    def _add_seg(self, a, b, tread=None, kind="tread", radius=1.5):
        sc = self.sc
        s = pymunk.Segment(self.space.static_body, a, b, radius)
        s.friction = sc.friction
        s.elasticity = sc.elasticity
        s.collision_type = CT_STAIR
        self.space.add(s)
        self.stair_shapes.append(s)
        self.stair_segs.append((a, b, tread, kind))
        return s

    def _build_stairs(self):
        sc = self.sc
        for i in range(self.n_treads):
            xs, xe = self.tread_x(i)
            ys, ye = self.surface_y(i, xs), self.surface_y(i, xe)
            arc = self.lip_arc(i)
            self._add_seg((xs, ys), (xe, ye), i, "tread")
            if arc:
                for a, b in zip(arc, arc[1:]):
                    self._add_seg(a, b, i, "lip")
            if i < self.n_treads - 1:
                ny = self.surface_y(i + 1, xs + sc.step_w)
                self._add_seg((xe, ye), (xs + sc.step_w, ny), i, "riser")
            # 描线（含挡边，和参考片一样是连续细线）
            if i == 0:
                self.outline.append((xs, ys))
            self._append_tread_outline(i, xs, ye, arc)

        xe, ye = self.edge(self.n_treads - 1)
        self.outline.append((xe, ye))
        # 末端挡墙：必须高出踏面，否则土豆会从右侧直接滚出世界（Pymunk 无 CCD）
        base_y = self.surface_y(self.n_treads - 1, sc.rail_x)
        self._add_seg((sc.rail_x, base_y - 420.0), (sc.rail_x, H_CANVAS),
                      self.n_treads - 1, "wall")
        self._add_seg((0, H_CANVAS - 4), (W_CANVAS, H_CANVAS - 4), None, "floor")

    def _append_tread_outline(self, i, xs, ye, arc):
        sc = self.sc
        if arc:
            self.outline.extend(arc)
            self.outline.append((self.edge(i)[0], ye))
        else:
            self.outline.append((self.edge(i)[0], ye))
        if i < self.n_treads - 1:
            self.outline.append((self.tread_x(i + 1)[0], self.surface_y(i + 1, self.tread_x(i + 1)[0])))

    # ---------------------------------------------------------------- potatoes
    def rest_guess(self, i: int) -> tuple[float, float]:
        """解析求静止位：椭圆土豆在踏面 + 圆弧挡边构成的楔形里的平衡点。

        球心离地 r、离挡边圆心 r+R ⇒ 水平间距 d = -sqrt(2rR+R²)。
        """
        sc = self.sc
        r = sc.radii[i]
        xs, xe = self.tread_x(i)
        if sc.lip_h > 0:
            R = sc.lip_h
            cx = xe - R
            d = -math.sqrt(2.0 * r * R + R * R)
            x = cx + d
        else:
            x = xs + max(sc.receiver_frac * sc.step_w, r + 10.0)
        return x, self.surface_y(i, x) - r

    def _build_potatoes(self):
        sc = self.sc
        for i in range(sc.n_potato):
            r = sc.radii[i]
            m = sc.density * r * r
            body = pymunk.Body(m, pymunk.moment_for_circle(m, 0.0, r))
            x, y = self.rest_guess(i)
            body.position = (x, y)
            shape = pymunk.Circle(body, r)
            shape.friction = sc.friction
            shape.elasticity = sc.elasticity
            shape.collision_type = CT_POTATO
            self.space.add(body, shape)
            self.potatoes.append({
                "idx": i, "r": r, "mass": m,
                "body": body, "shape": shape,
                "start_tread": i,
            })

    # ------------------------------------------------------------------ queries
    def potato_by_shape(self, sh):
        for p in self.potatoes:
            if p["shape"] is sh:
                return p["idx"]
        return -1

    def penetration(self) -> tuple[float, list]:
        """解析计算最大穿透（负数=穿进去）。返回 (最深穿透, 详情)。"""
        worst, detail = 0.0, []
        for p in self.potatoes:
            b, r = p["body"], p["r"]
            px, py = b.position
            for a, c, tread, kind in self.stair_segs:
                d = point_seg_dist(px, py, a, c) - 1.5 - r
                if d < worst:
                    worst, detail = d, [(p["idx"], kind, tread, round(d, 2))]
                elif d < -0.5:
                    detail.append((p["idx"], kind, tread, round(d, 2)))
        for i in range(len(self.potatoes)):
            for j in range(i + 1, len(self.potatoes)):
                bi = self.potatoes[i]["body"].position
                bj = self.potatoes[j]["body"].position
                d = dist(bi, bj) - self.potatoes[i]["r"] - self.potatoes[j]["r"]
                if d < worst:
                    worst, detail = d, [(i, j, "potato", round(d, 2))]
                elif d < -0.5:
                    detail.append((i, j, "potato", round(d, 2)))
        return worst, detail


def point_seg_dist(px, py, a, b) -> float:
    ax, ay = a
    bx, by = b
    vx, vy = bx - ax, by - ay
    L2 = vx * vx + vy * vy
    if L2 <= 1e-12:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * vx + (py - ay) * vy) / L2
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))


def dist(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


# --------------------------------------------------------------------------
# G1 变体
# --------------------------------------------------------------------------
VARIANTS = [
    Scene(key="A", label="参考比例 · 水平踏面",
          note="踏面 0°、无挡边；土豆静止不滚，全靠撞击驱动。",
          slope_deg=0.0, lip_h=0.0, receiver_frac=0.55),
    Scene(key="B", label="参考比例 · 3° 微坡 + 4px 挡边",
          note="踏面 3° 下坡，前沿 4px 圆弧挡边把土豆停在踏面前沿。",
          slope_deg=3.0, lip_h=4.0),
    Scene(key="C", label="参考比例 · 5° 微坡 + 4px 挡边",
          note="踏面 5°，挡边同 B；坡度更大，滚动更明显。",
          slope_deg=5.0, lip_h=4.0),
    Scene(key="D", label="加宽踏面 · 水平 · 前沿待位（G1 主方案）",
          note="W=200；土豆停在踏面前沿的临界点，小冲量即可把它推下去。",
          step_w=200.0, step_h=150.0, x0=90.0, y0=500.0, rail_x=1040.0,
          radii=(24.0, 30.0, 37.5), slope_deg=0.0, lip_h=0.0,
          receiver_frac=0.985, push_v=180.0, roll_resist=10.0),
    Scene(key="E", label="加宽踏面 · 5° + 4px 挡边",
          note="同 D 的尺度但 5° 微坡 + 挡边：挡边自动把接收者放在踏面前沿。",
          step_w=200.0, step_h=150.0, x0=90.0, y0=500.0, rail_x=1040.0,
          radii=(24.0, 30.0, 37.5), slope_deg=5.0, lip_h=4.0,
          push_v=240.0),
]

# 只做静止稳定性诊断，不出片
DIAGNOSTICS = [
    Scene(key="B0", label="3° 无挡边", slope_deg=3.0, lip_h=0.0),
    Scene(key="C0", label="5° 无挡边", slope_deg=5.0, lip_h=0.0),
]
