# -*- coding: utf-8 -*-
"""牛顿到混沌 受控模拟渲染器（34 镜，9 类物理系统）。
输出 16:9 mp4，深色调，遵循 sleep-aid-visual-style。
2026-10-17 修复：fig.patch 未设深底 + ax.axis("off") 隐藏 ax 底色 → 34 镜全部输出纯白；
同时线宽/点径整体加粗约 1.7x（深底上细线不可见）。
物理：velocity-Verlet (引力)、RK4 (双摆/洛伦兹)；数值预计算后逐帧渲染。
可断点续跑（已有 mp4 跳过）。"""
from __future__ import annotations
import json, os, subprocess, sys, math
from pathlib import Path
import numpy as np

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\newton-to-chaos")
RUN = EP / "runs" / "20261014-ntc-b01"
SIMS_OUT = EP / "image" / "sims"
LOG = RUN / "logs" / "sims_render.log"
FFMPEG = r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"
W, H, FPS = 1280, 720, 24
BG = (8/255, 18/255, 28/255)
TEAL = (95/255, 212/255, 200/255)
AMBER = (232/255, 168/255, 87/255)
DIM_TEAL = (40/255, 110/255, 104/255)
WHITE = (220/255, 235/255, 240/255)
G = 1.0
SOFT = 0.02

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter
from matplotlib.collections import LineCollection
plt.rcParams.update({"font.family": "DejaVu Sans"})

SIMS_OUT.mkdir(parents=True, exist_ok=True)
LOG.parent.mkdir(parents=True, exist_ok=True)

def log(m):
    line = f"{m}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

# ---------- physics ----------
def accel(pos, mass):
    n = len(mass)
    a = np.zeros_like(pos)
    for i in range(n):
        r = pos - pos[i]
        d2 = (r*r).sum(1) + SOFT**2
        inv3 = mass / (d2 * np.sqrt(d2))
        a[i] = (G * r * inv3[:, None]).sum(0)
    return a

def integrate_nbody(pos, vel, mass, dt, steps):
    P = np.zeros((steps, *pos.shape))
    P[0] = pos
    a = accel(pos, mass)
    for k in range(1, steps):
        vel = vel + 0.5*a*dt
        pos = pos + vel*dt
        a = accel(pos, mass)
        vel = vel + 0.5*a*dt
        P[k] = pos
    return P

def figure8_ic():
    # Chenciner-Montgomery equal-mass figure-8, G=1, m=1 each
    p1 = np.array([0.97000436, -0.24308753])
    p3 = -p1
    p2 = np.array([0.0, 0.0])
    v2 = np.array([0.4662036850, 0.4323657300])
    v1 = -v2/2
    v3 = v1
    pos = np.array([p1, p2, p3], float)
    vel = np.array([v1, v2, v3], float)
    mass = np.array([1,1,1], float)
    return pos, vel, mass

def two_body_ic(masses, e=0.2, a=1.0):
    m1, m2 = masses
    M = m1 + m2
    # place on apocenter line, reduce to relative
    r_apo = a*(1+e)
    v_apo = math.sqrt(G*M*(1-e)/(a*(1+e)))
    # m1 at -m2/M * r, m2 at m1/M * r; 远日点速度必须垂直于连线(y 方向),
    # 原版误设为 x 分量 → 轨道退化为直线对撞,轨迹呈一条水平线
    pos = np.array([[-m2/M*r_apo, 0.0],[m1/M*r_apo, 0.0]])
    vel = np.array([[0.0, -m2/M*v_apo],[0.0, m1/M*v_apo]])
    return pos, vel, np.array(masses)

def three_body_ic(masses, variant="drift"):
    m = masses
    if variant == "drift":
        pos = np.array([[1.0, 0.0],[-0.5, 0.6],[-0.5, -0.6]])*0.9
        vel = np.array([[0.0, -0.15],[0.10, 0.10],[-0.10, 0.05]])
    elif variant == "perturb":
        pos = np.array([[1.0, 0.0],[0.0, 0.0],[-0.8, 0.2]])
        vel = np.array([[0.0, -0.20],[0.0, 0.0],[0.18, -0.05]])
    elif variant == "scatter_far":
        # tight binary + distant 3rd approaching slowly
        pos = np.array([[0.6, 0.0],[-0.6, 0.0],[4.0, 1.2]])
        vel = np.array([[0.0, 0.30],[0.0, -0.30],[-0.18, -0.02]])
    elif variant == "scatter_close":
        pos = np.array([[0.5, 0.0],[-0.5, 0.0],[2.6, 0.8]])
        vel = np.array([[0.0, 0.34],[0.0, -0.34],[-0.22, -0.03]])
    elif variant == "scatter_after":
        pos = np.array([[0.35, 0.0],[-0.35, 0.0],[3.5, -0.4]])
        vel = np.array([[0.0, 0.40],[0.0, -0.40],[-0.30, 0.10]])
    elif variant == "perturb2":
        pos = np.array([[1.0, 0.0],[0.0, 0.0],[-0.9, 0.15]])
        vel = np.array([[0.0, -0.18],[0.0, 0.0],[0.16, 0.02]])
    else:
        pos = np.array([[1.0, 0.0],[-0.5, 0.6],[-0.5, -0.6]])
        vel = np.array([[0.0, -0.15],[0.10, 0.10],[-0.10, 0.05]])
    return pos, vel, np.array(m)

def double_pendulum_ic(dual=False, low_energy=False, diff=0.001):
    # state = [theta1, theta2, omega1, omega2]
    if low_energy:
        s0 = np.array([0.6, 0.1, 0.0, 0.0])
    else:
        s0 = np.array([math.pi*0.8, math.pi*0.7, 0.0, 0.0])
    return s0, s0 + np.array([diff, 0, 0, 0]) if dual else None

def dp_deriv(s, L=1.0, L2=1.0, m=1.0, m2=1.0, g=1.0):
    t1,t2,w1,w2 = s
    a = 2*m+m2; b=m2; c=m2*L2/L
    d = w1*w1*L*math.cos(t1-t2)+w2*w2*L2
    num1 = -g*(a)*math.sin(t1) - b*g*math.sin(t1-2*t2)+2*math.sin(t1-t2)*b*(w2*w2*L2 + w1*w1*L*math.cos(t1-t2))
    den1 = L*(a - b*math.cos(2*t1-2*t2)) + 1e-9
    num2 = 2*math.sin(t1-t2)*(w1*w1*L*(a) + g*(a)*math.cos(t1) + w2*w2*L2*b*math.cos(t1-t2))
    den2 = L2*(a - b*math.cos(2*t1-2*t2)) + 1e-9
    return np.array([w1, w2, num1/den1, num2/den2])

def integrate_dp(s0, dt, steps, s0b=None):
    out = np.zeros((steps, 4)); out[0]=s0
    outb = np.zeros((steps,4)) if s0b is not None else None
    if s0b is not None: outb[0]=s0b
    s=s0.copy(); sb=s0b.copy() if s0b is not None else None
    for k in range(1,steps):
        # RK4
        k1=dp_deriv(s); k2=dp_deriv(s+0.5*dt*k1); k3=dp_deriv(s+0.5*dt*k2); k4=dp_deriv(s+dt*k3)
        s = s + dt/6*(k1+2*k2+2*k3+k4); out[k]=s
        if sb is not None:
            k1b=dp_deriv(sb); k2b=dp_deriv(sb+0.5*dt*k1b); k3b=dp_deriv(sb+0.5*dt*k2b); k4b=dp_deriv(sb+dt*k3b)
            sb = sb + dt/6*(k1b+2*k2b+2*k3b+k4b); outb[k]=sb
    return out, outb

def dp_pos(s, L=1.0, L2=1.0, origin=(0,0)):
    x1 = origin[0] + L*math.sin(s[0]); y1 = origin[1] - L*math.cos(s[0])
    x2 = x1 + L2*math.sin(s[1]); y2 = y1 - L2*math.cos(s[1])
    return (x1,y1),(x2,y2)

def lorenz_ic(dual=True, diff=1e-8):
    s0 = np.array([1.0, 1.0, 1.0])
    return s0, s0 + np.array([diff,0,0]) if dual else None

def lorenz_deriv(s, sigma=10, rho=28, beta=8/3):
    return np.array([sigma*(s[1]-s[0]), s[0]*(rho-s[2])-s[1], s[0]*s[1]-beta*s[2]])

def integrate_lorenz(s0, dt, steps, s0b=None):
    out=np.zeros((steps,3)); out[0]=s0
    outb=np.zeros((steps,3)) if s0b is not None else None
    if s0b is not None: outb[0]=s0b
    s=s0.copy(); sb=s0b.copy() if s0b is not None else None
    for k in range(1,steps):
        k1=lorenz_deriv(s); k2=lorenz_deriv(s+0.5*dt*k1); k3=lorenz_deriv(s+0.5*dt*k2); k4=lorenz_deriv(s+dt*k3)
        s=s+dt/6*(k1+2*k2+2*k3+k4); out[k]=s
        if sb is not None:
            k1b=lorenz_deriv(sb); k2b=lorenz_deriv(sb+0.5*dt*k1b); k3b=lorenz_deriv(sb+0.5*dt*k2b); k4b=lorenz_deriv(sb+dt*k3b)
            sb=sb+dt/6*(k1b+2*k2b+2*k3b+k4b); outb[k]=sb
    return out,outb

# ---------- rendering helpers ----------
def make_fig():
    fig = plt.figure(figsize=(W/100, H/100), dpi=100)
    # 画布底色必须设在 fig.patch：ax.axis("off") 会隐藏 ax 自己的底色
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0,0,1,1]); ax.set_facecolor(BG)
    ax.set_xticks([]); ax.set_yticks([]); ax.axis("off")
    return fig, ax

_STARFIELD = None
def _make_starfield(w=W, h=H, n=140, seed=20261017):
    """静态微星光层:深底上的低亮度冷白星点,填充空旷感(不闪烁)。"""
    import random
    from PIL import Image as _Img, ImageDraw as _Dr
    rnd = random.Random(seed)
    img = _Img.new("L", (w, h), 0)
    d = _Dr.Draw(img)
    for _ in range(n):
        x = rnd.uniform(0, w); y = rnd.uniform(0, h)
        r = rnd.choice([0.6, 0.8, 0.9, 1.0, 1.1, 1.4, 1.8])
        a = rnd.uniform(35, 105)
        d.ellipse([x - r, y - r, x + r, y + r], fill=int(a))
    return np.asarray(img).astype(np.float32) / 255.0

def save_frame(fig):
    fig.canvas.draw()
    buf = np.asarray(fig.canvas.buffer_rgba())
    rgb = buf[..., :3].astype(np.float32)  # drop alpha -> HxWx3
    global _STARFIELD
    if _STARFIELD is None:
        _STARFIELD = _make_starfield()
    star = np.array([200, 216, 236], dtype=np.float32)
    rgb = rgb + _STARFIELD[..., None] * star[None, None, :]
    return np.clip(rgb, 0, 255).astype(np.uint8)

def write_mp4(frames, path, fps=FPS):
    # save RGB frames as PNG sequence then encode via ffmpeg
    import tempfile, shutil
    tmp = Path(tempfile.mkdtemp(prefix="sim_"))
    try:
        from PIL import Image
        for i, f in enumerate(frames):
            Image.fromarray(f).save(str(tmp/f"f{i:05d}.png"))
        cmd=[FFMPEG,"-y","-framerate",str(fps),"-i",str(tmp/"f%05d.png"),
             "-c:v","libx264","-pix_fmt","yuv420p","-crf","20",
             "-vf",f"scale={W}:{H}",str(path)]
        r=subprocess.run(cmd,capture_output=True,text=True)
        if r.returncode!=0:
            raise RuntimeError("ffmpeg: "+(r.stderr or "")[-500:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def render_trails(ax, pos_hist, color, trail_len=120, lw=3.0, alpha_max=0.9):
    # accepts (M,2) single body or (M,B,2) multi-body
    arr = np.asarray(pos_hist)
    if arr.ndim == 3:
        for b in range(arr.shape[1]):
            _render_one_trail(ax, arr[:, b], color, trail_len, lw, alpha_max)
        return
    _render_one_trail(ax, arr, color, trail_len, lw, alpha_max)

def _render_one_trail(ax, seg, color, trail_len, lw, alpha_max):
    n = len(seg); start = max(0, n-trail_len); seg = seg[start:]
    if len(seg) < 2: return
    pts = np.stack([seg[:-1], seg[1:]], axis=1)  # (M,2,2)
    alphas = alpha_max * (np.arange(len(pts))+1)/len(pts)
    rgba = np.zeros((len(pts),4)); rgba[:,:3] = color; rgba[:,3] = alphas
    lc = LineCollection(pts, colors=rgba, linewidths=lw, capstyle="round")
    ax.add_collection(lc)

def plot_body(ax, p, color, size=22, halo=True):
    if halo:
        for s, a in [(size*3.2, 0.10),(size*2.2,0.20)]:
            ax.scatter([p[0]],[p[1]], s=s, c=[color], alpha=a, edgecolors="none", zorder=3)
    ax.scatter([p[0]],[p[1]], s=size, c=[color], edgecolors="none", zorder=4)

# ---------- per-system renderers ----------
def sim_two_body(spec, key):
    e = 0.2
    if "eccentric" in key: e = 0.6
    if "wide" in key: e = 0.25
    if "barycenter" in key:
        masses=[1.0,0.12]
    elif "eccentric" in key:
        masses=[1.0,0.6]
    else:
        masses=spec["masses"]
    a = 1.6 if "wide" in key else 1.2
    pos, vel, mass = two_body_ic(masses, e=e, a=a)
    dur = spec["duration_s"]; steps = dur*FPS; dt = 1/30
    nint = int(steps*(1/30)/dt) + 1
    P = integrate_nbody(pos, vel, mass, dt, nint)
    # scale to view
    lim = 2.2 if "wide" in key else 1.8
    fig, ax = make_fig(); ax.set_xlim(-lim,lim); ax.set_ylim(-lim*0.5625, lim*0.5625); ax.set_aspect("equal")
    frames=[]; trail_len = 300
    for f in range(steps):
        ax.clear(); ax.set_xlim(-lim,lim); ax.set_ylim(-lim*0.5625,lim*0.5625); ax.set_aspect("equal")
        ax.set_facecolor(BG); ax.set_xticks([]); ax.set_yticks([]); ax.axis("off")
        k = int(f * nint / steps)
        render_trails(ax, P[:k+1], TEAL if "barycenter" not in key else TEAL, trail_len=trail_len)
        for i in range(2):
            plot_body(ax, P[k,i], AMBER if i==0 else TEAL, size=30 if mass[i]>0.5 else 20)
        if "barycenter" in key:
            ax.scatter([0],[0], marker="+", s=90, c=[WHITE], alpha=0.5, zorder=2)
        frames.append(save_frame(fig))
    return frames

def sim_three_body(spec, key):
    variant = "drift"
    if "perturb" in key and "scatter" not in key: variant="perturb"
    if "figure8" in key:
        pos, vel, mass = figure8_ic(); variant="fig8"
    elif "slow_drift" in key: variant="drift"
    elif "perturb" in key: variant="perturb"
    elif "numeric" in key: variant="drift"
    elif "scattering_far" in key: variant="scatter_far"
    elif "scattering_close" in key: variant="scatter_close"
    elif "scattering_after" in key: variant="scatter_after"
    elif "divergence" in key: variant="perturb2"
    elif "encounter_variants" in key: variant="perturb2"
    else: variant="drift"
    if "figure8" not in key:
        pos, vel, mass = three_body_ic(spec.get("masses",[1,0.8,0.6]), variant)
    dur=spec["duration_s"]; steps=int(dur*FPS); dt=1/40
    nint=int(dur/dt)+1
    dual = spec.get("dual_variant") or "divergence" in key or "encounter_variants" in key
    P = integrate_nbody(pos, vel, mass, dt, nint)
    Pb = None
    if dual:
        # tiny perturbation
        vel2 = vel + np.array([[0.002,0.0],[0.0,0.0],[0.0,0.0]])
        Pb = integrate_nbody(pos.copy(), vel2, mass, dt, nint)
    lim = 2.6
    if "closeup" in key: lim=1.4
    if "scattering_after" in key: lim=3.2
    fig, ax = make_fig(); ax.set_xlim(-lim,lim); ax.set_ylim(-lim*0.5625,lim*0.5625); ax.set_aspect("equal")
    frames=[]; trail_len = 300 if "numeric" not in key else 240
    step_vis = spec.get("step_visual")
    for f in range(steps):
        ax.clear(); ax.set_xlim(-lim,lim); ax.set_ylim(-lim*0.5625,lim*0.5625); ax.set_aspect("equal")
        ax.set_facecolor(BG); ax.set_xticks([]); ax.set_yticks([]); ax.axis("off")
        k = int(f*nint/steps)
        if step_vis:
            # light up segments in chunks
            chunk = max(1, k//8)
            kk = (k//chunk)*chunk
            render_trails(ax, P[:kk+1], TEAL, trail_len=trail_len)
        else:
            render_trails(ax, P[:k+1], TEAL, trail_len=trail_len)
        if Pb is not None:
            render_trails(ax, Pb[:k+1], AMBER, trail_len=trail_len)
        cols=[AMBER,TEAL,WHITE]
        for i in range(3):
            plot_body(ax, P[k,i], cols[i], size=26)
        if Pb is not None:
            for i in range(3):
                plot_body(ax, Pb[k,i], AMBER, size=16, halo=False)
        frames.append(save_frame(fig))
    return frames

def sim_ensemble(spec, key):
    n = spec.get("n", 18)
    masses = spec.get("masses",[1,0.8,0.5])
    dur=spec["duration_s"]; steps=int(dur*FPS); dt=1/40; nint=int(dur/dt)+1
    base_pos, base_vel, _ = three_body_ic(masses, "drift")
    Ps=[]
    rng=np.random.default_rng(7)
    for i in range(n):
        p = base_pos + rng.normal(0, 0.04, base_pos.shape)
        v = base_vel + rng.normal(0, 0.02, base_vel.shape)
        Ps.append(integrate_nbody(p, v, np.array(masses), dt, nint))
    lim=3.0
    fig,ax=make_fig()
    frames=[]; trail_len=280
    for f in range(steps):
        ax.clear(); ax.set_xlim(-lim,lim); ax.set_ylim(-lim*0.5625,lim*0.5625); ax.set_aspect("equal")
        ax.set_facecolor(BG); ax.set_xticks([]); ax.set_yticks([]); ax.axis("off")
        k=int(f*nint/steps)
        for i,P in enumerate(Ps):
            col = TEAL if i%2==0 else AMBER
            render_trails(ax, P[:k+1,0], col, trail_len=trail_len, lw=2.2, alpha_max=0.6)
            plot_body(ax, P[k,0], col, size=12, halo=False)
        frames.append(save_frame(fig))
    return frames

def sim_double_pendulum(spec, key):
    dual=spec.get("dual", False); low=spec.get("low_energy", False); bounded=spec.get("bounded_region", False)
    s0,s0b = double_pendulum_ic(dual=dual, low_energy=low)
    dur=spec["duration_s"]; steps=int(dur*FPS); dt=1/200; nint=int(dur/dt)+1
    out,outb = integrate_dp(s0, dt, nint, s0b)
    lim=2.6
    fig,ax=make_fig(); ax.set_xlim(-lim,lim); ax.set_ylim(-lim*0.5625-0.3,lim*0.5625+0.3); ax.set_aspect("equal")
    origin=(0,0)
    trail_a=[]; trail_b=[]
    frames=[]
    for f in range(steps):
        ax.clear(); ax.set_xlim(-lim,lim); ax.set_ylim(-lim*0.5625-0.3,lim*0.5625+0.3); ax.set_aspect("equal")
        ax.set_facecolor(BG); ax.set_xticks([]); ax.set_yticks([]); ax.axis("off")
        if bounded:
            th=np.linspace(0,2*math.pi,80)
            ax.plot(2.0*np.cos(th),2.0*np.sin(th), c=DIM_TEAL, lw=1, alpha=0.4)
        k=int(f*nint/steps)
        (x1,y1),(x2,y2)=dp_pos(out[k]); trail_a.append((x2,y2))
        ta=np.array(trail_a[-100:]) if len(trail_a)>1 else None
        if ta is not None and len(ta)>1:
            pts=np.stack([ta[:-1],ta[1:]],axis=1); al=0.8*(np.arange(len(pts))+1)/len(pts)
            rgba=np.zeros((len(pts),4)); rgba[:,:3]=TEAL; rgba[:,3]=al
            ax.add_collection(LineCollection(pts,colors=rgba,linewidths=1.4,capstyle="round"))
        ax.plot([0,x1],[0,y1],c=WHITE,lw=1.2,alpha=0.5); ax.plot([x1,x2],[y1,y2],c=WHITE,lw=1.2,alpha=0.5)
        ax.scatter([0],[0],s=70,c=[WHITE],zorder=5); ax.scatter([x1],[y1],s=50,c=[TEAL],zorder=5); ax.scatter([x2],[y2],s=36,c=[TEAL],zorder=6)
        if outb is not None:
            (b1x,b1y),(b2x,b2y)=dp_pos(outb[k]); trail_b.append((b2x,b2y))
            tb=np.array(trail_b[-100:]) if len(trail_b)>1 else None
            if tb is not None and len(tb)>1:
                pts=np.stack([tb[:-1],tb[1:]],axis=1); al=0.8*(np.arange(len(pts))+1)/len(pts)
                rgba=np.zeros((len(pts),4)); rgba[:,:3]=AMBER; rgba[:,3]=al
                ax.add_collection(LineCollection(pts,colors=rgba,linewidths=1.4,capstyle="round"))
            ax.plot([0,b1x],[0,b1y],c=WHITE,lw=1.0,alpha=0.35); ax.plot([b1x,b2x],[b1y,b2y],c=WHITE,lw=1.0,alpha=0.35)
            ax.scatter([b2x],[b2y],s=26,c=[AMBER],zorder=6)
        frames.append(save_frame(fig))
    return frames

def sim_lorenz(spec, key):
    s0,s0b=lorenz_ic(dual=True)
    dur=spec["duration_s"]; steps=int(dur*FPS); dt=0.01; nint=int(dur/dt)+1
    out,outb=integrate_lorenz(s0,dt,nint,s0b)
    # project x-z
    lim_x=26; lim_z=28
    fig,ax=make_fig(); ax.set_xlim(-lim_x,lim_x); ax.set_ylim(0,lim_z); ax.set_aspect("equal")
    frames=[]; trail_len=400
    for f in range(steps):
        ax.clear(); ax.set_xlim(-lim_x,lim_x); ax.set_ylim(0,lim_z); ax.set_aspect("equal")
        ax.set_facecolor(BG); ax.set_xticks([]); ax.set_yticks([]); ax.axis("off")
        k=int(f*nint/steps)
        seg=out[:k+1]; seg2=outb[:k+1] if outb is not None else None
        if len(seg)>2:
            pts=np.stack([seg[:-1,0],seg[:-1,2],seg[1:,0],seg[1:,2]],axis=1).reshape(-1,2,2)
            al=0.6*(np.arange(len(pts))+1)/len(pts); rgba=np.zeros((len(pts),4)); rgba[:,:3]=TEAL; rgba[:,3]=al
            ax.add_collection(LineCollection(pts,colors=rgba,linewidths=1.0))
        if seg2 is not None and len(seg2)>2:
            pts=np.stack([seg2[:-1,0],seg2[:-1,2],seg2[1:,0],seg2[1:,2]],axis=1).reshape(-1,2,2)
            al=0.6*(np.arange(len(pts))+1)/len(pts); rgba=np.zeros((len(pts),4)); rgba[:,:3]=AMBER; rgba[:,3]=al
            ax.add_collection(LineCollection(pts,colors=rgba,linewidths=1.0))
        plot_body(ax,(out[k,0],out[k,2]),TEAL,size=10)
        if outb is not None: plot_body(ax,(outb[k,0],outb[k,2]),AMBER,size=10)
        frames.append(save_frame(fig))
    return frames

def sim_scatterfit(spec, key):
    mode=spec.get("mode","scatter")
    rng=np.random.default_rng(11)
    n=14
    x=np.linspace(-2,2,n); trend=0.3*x**2-0.4
    y=trend+rng.normal(0,0.35,n)
    dur=spec["duration_s"]; steps=int(dur*FPS)
    lim=2.6
    fig,ax=make_fig(); ax.set_xlim(-lim,lim); ax.set_ylim(-lim*0.5625,lim*0.5625); ax.set_aspect("equal")
    frames=[]
    fit_t=np.linspace(-2,2,200)
    if mode=="underfit":
        fit_y=0.0*fit_t + 0.0*fit_t  # straight flat-ish line through mean
    elif mode=="good":
        fit_y=0.3*fit_t**2-0.4
    elif mode in ("overfit","overfit_newpoint"):
        # high-degree wiggle passing near points
        coef=np.polyfit(x,y,12)
        fit_y=np.polyval(coef,fit_t)
    else:
        fit_y=None
    if mode=="overfit_newpoint":
        x2=np.append(x,1.8); y2=np.append(y, trend[-1]+1.2 + rng.normal(0,0.1,1)); 
        coef=np.polyfit(x2[:-1],y2[:-1],12); fit_y=np.polyval(coef,fit_t)
    for f in range(steps):
        ax.clear(); ax.set_xlim(-lim,lim); ax.set_ylim(-lim*0.5625,lim*0.5625); ax.set_aspect("equal")
        ax.set_facecolor(BG); ax.set_xticks([]); ax.set_yticks([]); ax.axis("off")
        prog=(f+1)/steps
        nshow=int(n*prog)
        for i in range(nshow):
            plot_body(ax,(x[i],y[i]),AMBER if i%2==0 else TEAL, size=70, halo=True)
        if fit_y is not None and mode!="scatter":
            k=int(prog*len(fit_t)); k=max(2,k)
            ax.plot(fit_t[:k], fit_y[:k], c=TEAL, lw=1.6, alpha=0.85)
        if mode=="overfit_newpoint" and prog>0.8:
            plot_body(ax,(1.8, y2[-1]), WHITE, size=90, halo=True)
        frames.append(save_frame(fig))
    return frames

def sim_composite(spec, key):
    # left: overfit, right: divergence
    dur=spec["duration_s"]; steps=int(dur*FPS)
    rng=np.random.default_rng(3)
    n=12; x=np.linspace(-1.5,1.5,n); trend=0.4*x**2
    y=trend+rng.normal(0,0.25,n); coef=np.polyfit(x,y,11); fit_t=np.linspace(-1.5,1.5,150); fit_y=np.polyval(coef,fit_t)
    masses=[1,0.8,0.5]; pos,vel,_=three_body_ic(masses,"perturb2")
    vel2=vel+np.array([[0.003,0],[0,0],[0,0]]); dt=1/40; nint=int(dur/dt)+1
    P=integrate_nbody(pos,vel,np.array(masses),dt,nint); Pb=integrate_nbody(pos.copy(),vel2,np.array(masses),dt,nint)
    lim=3.2
    fig,ax=make_fig(); ax.set_xlim(-lim,lim); ax.set_ylim(-lim*0.5625,lim*0.5625); ax.set_aspect("equal")
    frames=[]
    for f in range(steps):
        ax.clear(); ax.set_xlim(-lim,lim); ax.set_ylim(-lim*0.5625,lim*0.5625); ax.set_aspect("equal")
        ax.set_facecolor(BG); ax.set_xticks([]); ax.set_yticks([]); ax.axis("off")
        # left half overfit (x in [-2.8,-0.4])
        off_l=(-1.6,0)
        prog=(f+1)/steps; k=int(prog*len(fit_t)); k=max(2,k)
        ax.plot(fit_t[:k]-1.6, fit_y[:k], c=TEAL, lw=1.4, alpha=0.8)
        for i in range(min(n,int(n*prog))):
            ax.scatter([x[i]-1.6],[y[i]], s=80, c=[AMBER], edgecolors="none", zorder=4)
        # right divergence (x in [0.4, 2.8])
        off_r=(1.4,0)
        ki=int(f*nint/steps)
        render_trails_offset(ax, P[:ki+1], TEAL, trail_len=300, offset=off_r)
        render_trails_offset(ax, Pb[:ki+1], AMBER, trail_len=300, offset=off_r)
        for i in range(3):
            ax.scatter([P[ki,i,0]+off_r[0]],[P[ki,i,1]+off_r[1]], s=70, c=[AMBER if i==0 else (TEAL if i==1 else WHITE)], edgecolors="none", zorder=5)
        frames.append(save_frame(fig))
    return frames

def render_trails_offset(ax, pos_hist, color, trail_len, offset, lw=3.0, alpha_max=0.9):
    n=len(pos_hist); start=max(0,n-trail_len); seg=pos_hist[start:]
    if len(seg)<2: return
    for i in range(len(seg)-1):
        a=alpha_max*(i+1)/len(seg)
        ax.plot([seg[i,0]+offset[0],seg[i+1,0]+offset[0]],[seg[i,1]+offset[1],seg[i+1,1]+offset[1]],color=color,lw=lw,alpha=a)

def sim_iterated(spec, key):
    # real trajectory (teal) + autoregressive model prediction (amber) drifting
    dur=spec["duration_s"]; steps=int(dur*FPS); dt=1/40; nint=int(dur/dt)+1
    masses=[1,0.8,0.5]; pos,vel,_=three_body_ic(masses,"perturb2")
    P=integrate_nbody(pos,vel,np.array(masses),dt,nint)
    # model: predicts step k from its own past with small systematic drift
    Mp=np.zeros_like(P); Mp[0]=P[0]
    drift=np.array([0.0008,-0.0004])
    for k in range(1,nint):
        # model one step: use true physics but accumulate drift each step
        Mp[k]=Mp[k-1] + (P[k]-P[k-1]) + drift
    lim=2.8
    fig,ax=make_fig(); ax.set_xlim(-lim,lim); ax.set_ylim(-lim*0.5625,lim*0.5625); ax.set_aspect("equal")
    frames=[]
    for f in range(steps):
        ax.clear(); ax.set_xlim(-lim,lim); ax.set_ylim(-lim*0.5625,lim*0.5625); ax.set_aspect("equal")
        ax.set_facecolor(BG); ax.set_xticks([]); ax.set_yticks([]); ax.axis("off")
        k=int(f*nint/steps)
        render_trails(ax, P[:k+1], TEAL, trail_len=400, lw=3.0, alpha_max=0.7)
        render_trails(ax, Mp[:k+1], AMBER, trail_len=400, lw=2.6, alpha_max=0.7)
        plot_body(ax, P[k,0], TEAL, size=24)
        plot_body(ax, Mp[k,0], AMBER, size=18, halo=False)
        frames.append(save_frame(fig))
    return frames

def sim_particle_weather(spec, key):
    n=spec.get("n_members",9); dur=spec["duration_s"]; steps=int(dur*FPS)
    rng=np.random.default_rng(5)
    # "rain band": region where dark amber particles cluster; each member slightly different center
    band_center=np.array([0.0,0.0]); band_dir=np.array([1.0,0.1])
    members=[]
    for i in range(n):
        c=band_center + rng.normal(0,0.15,2)
        members.append(c)
    lim=3.0
    fig,ax=make_fig(); ax.set_xlim(-lim,lim); ax.set_ylim(-lim*0.5625,lim*0.5625); ax.set_aspect("equal")
    frames=[]
    for f in range(steps):
        ax.clear(); ax.set_xlim(-lim,lim); ax.set_ylim(-lim*0.5625,lim*0.5625); ax.set_aspect("equal")
        ax.set_facecolor(BG); ax.set_xticks([]); ax.set_yticks([]); ax.axis("off")
        prog=(f+1)/steps
        for i,c in enumerate(members):
            # spawn particles along band for this member
            for p in range(40):
                t=rng.random()*2-1
                pt=c + band_dir*t*1.5 + np.array([rng.normal(0,0.15), rng.normal(0,0.3)])
                ax.scatter([pt[0]],[pt[1]], s=14, c=[AMBER if i%2==0 else TEAL], alpha=0.35, edgecolors="none")
            ax.scatter([c[0]],[c[1]], s=34, c=[WHITE], alpha=0.4, edgecolors="none", zorder=4)
        frames.append(save_frame(fig))
    return frames

DISPATCH = {
 "gravity2": sim_two_body,
 "gravity3": sim_three_body,
 "gravity3_ensemble": sim_ensemble,
 "double_pendulum": sim_double_pendulum,
 "lorenz": sim_lorenz,
 "scatterfit": sim_scatterfit,
 "composite": sim_composite,
 "iterated_prediction": sim_iterated,
 "particle_weather": sim_particle_weather,
}

def check_sim_output(path):
    """渲染后自检(2026-10-17 新增,防止白屏再次入库):中段抽帧,
    深底占比≥85% 且 白色占比<1% 且 有发光内容。返回 None 或 原因。"""
    import tempfile
    from PIL import Image
    d = 0.0
    r = subprocess.run([FFPROBE,"-v","error","-show_entries","format=duration",
                        "-of","csv=p=0",str(path)], capture_output=True, text=True)
    d = float(r.stdout.strip() or 0)
    mid = d/2 if d>0 else 0
    tmp = Path(tempfile.mkstemp(suffix=".jpg")[1])
    try:
        r = subprocess.run([FFMPEG,"-y","-ss",str(mid),"-i",str(path),
                            "-frames:v","1","-q:v","3",str(tmp)],
                           capture_output=True, text=True)
        if r.returncode!=0 or not tmp.exists():
            return "frame extract failed"
        im = Image.open(str(tmp)).convert("RGB")
        px = list(im.getdata()); n=len(px)
        dark = sum(1 for cr,cg,cb in px if cr<60 and cg<60 and cb<60)/n
        white = sum(1 for cr,cg,cb in px if cr>220 and cg>220 and cb>220)/n
        lit = sum(1 for cr,cg,cb in px if cr+cg+cb>300)/n
        if dark < 0.85: return f"dark bg only {dark*100:.0f}%"
        if white > 0.01: return f"white {white*100:.1f}%"
        if lit < 0.0005: return "no visible content"
        return None
    finally:
        tmp.unlink(missing_ok=True)

FFPROBE = FFMPEG.replace("ffmpeg.exe","ffprobe.exe")

def main():
    only = sys.argv[1] if len(sys.argv)>1 else None
    plan = json.loads((EP/"visual"/"SHOT_PLAN.json").read_text(encoding="utf-8"))
    sys.path.insert(0, str(RUN/"scripts"))
    from importlib import import_module
    SIMS = import_module("03_sim_specs").SIMS
    sim_shots = [s for s in plan["shots"] if s.get("shot_class")=="controlled_simulation" and s.get("sim_key")]
    log(f"sim shots: {len(sim_shots)}")
    done=0; fail=0
    for s in sim_shots:
        key=s["sim_key"]; outp = SIMS_OUT/f"{s['id']}.mp4"
        if only and only != s["id"]: continue
        if outp.exists() and outp.stat().st_size>10000:
            log(f"skip {s['id']} (exists)"); done+=1; continue
        spec=SIMS.get(key)
        if not spec: log(f"NO SPEC {key}"); fail+=1; continue
        sys_=spec["system"]; fn=DISPATCH.get(sys_)
        if not fn: log(f"NO RENDERER {sys_} for {s['id']}"); fail+=1; continue
        log(f"render {s['id']} [{sys_}/{key}] dur={spec['duration_s']}s")
        try:
            frames=fn(spec, key)
            write_mp4(frames, str(outp))
            bad = check_sim_output(outp)
            if bad:
                outp.unlink(missing_ok=True)
                log(f"  QA FAIL {s['id']}: {bad} (file removed)")
                fail+=1; continue
            log(f"  OK {s['id']} frames={len(frames)} -> {outp.name}")
            done+=1
        except Exception as e:
            import traceback; log(f"  FAIL {s['id']}: {e}"); log(traceback.format_exc()[:400])
            fail+=1
    log(f"SIMS DONE done={done} fail={fail}")
    return 0 if not fail else 1

if __name__=="__main__":
    raise SystemExit(main())
