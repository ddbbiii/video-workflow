import math
import bisect

STEPS = 10
W, H = 110.0, 130.0
X0, Y0 = 100.0, 420.0
R = [22.0 + i * 4.5 for i in range(STEPS)]

# surface polyline (treads + risers), 2px spacing
pts = []
for i in range(STEPS):
    x = X0 + i * W
    y = Y0 + i * H
    for k in range(0, 111, 2):
        pts.append((x + W * k / 110.0, y))
    if i < STEPS - 1:
        for k in range(0, 131, 2):
            pts.append((x + W, y + H * k / 130.0))

# smooth interior
sm = [pts[0]]
for i in range(1, len(pts) - 1):
    a, b, c = pts[i - 1], pts[i], pts[i + 1]
    sm.append(((a[0] + 2 * b[0] + c[0]) / 4, (a[1] + 2 * b[1] + c[1]) / 4))
sm.append(pts[-1])
pts = sm
cum = [0.0]
for i in range(1, len(pts)):
    cum.append(cum[-1] + math.dist(pts[i - 1], pts[i]))
L = cum[-1]


def sample(s):
    s = max(0.0, min(L, s))
    i = min(bisect.bisect_right(cum, s) - 1, len(pts) - 2)
    t = (s - cum[i]) / max(1e-9, cum[i + 1] - cum[i])
    px = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t
    py = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t
    dx = pts[i + 1][0] - pts[i][0]
    dy = pts[i + 1][1] - pts[i][1]
    ln = math.hypot(dx, dy) or 1.0
    return (px, py), (dx / ln, dy / ln)


def s_at_x(x, y):
    best = 0.0
    bd = 1e9
    for i in range(len(pts)):
        d = (pts[i][0] - x) ** 2 + (pts[i][1] - y) ** 2
        if d < bd:
            bd = d
            best = cum[i]
    return best


S = []
for i in range(STEPS):
    x = X0 + i * W + W - R[i] - 3
    y = Y0 + i * H
    S.append(s_at_x(x, y))
S[0] = s_at_x(X0 + 22, Y0)
V = [0.0] * STEPS
M = [r * r for r in R]
HOLD = [0.0] * STEPS
PENDING = [0.0] * STEPS
COOLDOWN = [0.0] * STEPS
V[0] = 190.0
DWELL = 4.0
G = 900.0
DAMP = 0.8
E = 0.2

hits = []
t = 0.0
dt = 1 / 240
for step in range(int(80 / dt)):
    t = step * dt
    for i in range(STEPS):
        COOLDOWN[i] = max(0.0, COOLDOWN[i] - dt)
        if HOLD[i] > 0:
            HOLD[i] -= dt
            V[i] = 0.0
            if HOLD[i] <= 0:
                V[i] = max(PENDING[i], 170.0)
            continue
        p, tan = sample(S[i])
        V[i] += G * tan[1] * dt
        V[i] *= math.exp(-DAMP * dt)
        S[i] += V[i] * dt
    for i in range(STEPS - 1):
        if COOLDOWN[i] > 0:
            continue
        gap = R[i] + R[i + 1]
        if S[i + 1] - S[i] < gap:
            rel = V[i] - V[i + 1]
            if rel > 0:
                j = -(1 + E) * rel / (1 / M[i] + 1 / M[i + 1])
                V[i] += j / M[i]
                V[i + 1] -= j / M[i + 1]
                hits.append((round(t, 2), i, round(abs(j), 1)))
                COOLDOWN[i] = DWELL + 2.0
                if HOLD[i + 1] <= 0:
                    PENDING[i + 1] = max(0.0, V[i + 1])
                    HOLD[i + 1] = DWELL
                    V[i + 1] = 0.0
                    V[i] = 0.0
                    S[i] = S[i + 1] - gap - 1.0
            overlap = gap - (S[i + 1] - S[i])
            if overlap > 0:
                S[i] -= overlap * 0.5
                S[i + 1] += overlap * 0.5
    if step % (240*5) == 0:
        print(t, [round(x) for x in S], [round(x) for x in V])
print("hits", hits[:12], "count", len(hits))
print("L", L, "finalS", [round(x) for x in S])
