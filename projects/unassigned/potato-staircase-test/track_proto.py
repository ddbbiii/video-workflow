import math

STEPS = 10
W, H = 140.0, 130.0
X0, Y0 = 120.0, 420.0
R = [24.0 + i * 4.0 for i in range(STEPS)]

# dense surface points along treads / risers
pts = []
for i in range(STEPS):
    x = X0 + i * W
    y = Y0 + i * H
    for k in range(0, 141, 2):
        pts.append((x + W * k / 140.0, y))
    if i < STEPS - 1:
        for k in range(0, 131, 2):
            pts.append((x + W, y + H * k / 130.0))

# smooth a bit (not endpoints)
sm = [pts[0]]
for i in range(1, len(pts) - 1):
    a, b, c = pts[i - 1], pts[i], pts[i + 1]
    sm.append(((a[0] + 2 * b[0] + c[0]) / 4, (a[1] + 2 * b[1] + c[1]) / 4))
sm.append(pts[-1])
pts = sm

# cumulative arc length
cum = [0.0]
for i in range(1, len(pts)):
    cum.append(cum[-1] + math.dist(pts[i - 1], pts[i]))
L = cum[-1]


def sample(s):
    s = max(0.0, min(L, s))
    import bisect
    i = bisect.bisect_right(cum, s) - 1
    i = min(i, len(pts) - 2)
    t = (s - cum[i]) / max(1e-9, cum[i + 1] - cum[i])
    p = (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t,
         pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t)
    dx = pts[i + 1][0] - pts[i][0]
    dy = pts[i + 1][1] - pts[i][1]
    ln = math.hypot(dx, dy) or 1
    return p, (dx / ln, dy / ln)


def s_at_x(x, y):
    best = None
    for i in range(len(pts)):
        if abs(pts[i][0] - x) < 1.5 and abs(pts[i][1] - y) < 2.0:
            best = cum[i]
    return best if best is not None else 0.0


# rest positions at right end of each tread
S = []
for i in range(STEPS):
    x = X0 + i * W + W - R[i] - 3
    y = Y0 + i * H
    S.append(s_at_x(x, y))
# top at left
S[0] = s_at_x(X0 + 22, Y0)

V = [0.0] * STEPS
M = [r * r for r in R]
V[0] = 360.0

G = 900.0
E = 0.25
DAMP = 0.8

hits = []
t = 0.0
dt = 1 / 240
for step in range(int(20 / dt)):
    t = step * dt
    # gravity + damping
    for i in range(STEPS):
        p, tan = sample(S[i])
        a = G * tan[1]
        V[i] += a * dt
        V[i] *= math.exp(-DAMP * dt)
        S[i] += V[i] * dt
    # adjacent collisions
    for i in range(STEPS - 1):
        if S[i + 1] - S[i] < R[i] + R[i + 1]:
            rel = V[i] - V[i + 1]
            if rel > 0:
                j = -(1 + E) * rel / (1 / M[i] + 1 / M[i + 1])
                V[i] += j / M[i]
                V[i + 1] -= j / M[i + 1]
                hits.append((round(t, 2), i, round(abs(j), 1)))
            overlap = R[i] + R[i + 1] - (S[i + 1] - S[i])
            if overlap > 0:
                S[i] -= overlap * 0.5
                S[i + 1] += overlap * 0.5
    if step % 240 == 0:
        print(t, [round(x, 1) for x in S], [round(x, 1) for x in V])
print("hits", hits[:20], "count", len(hits))
print("L", L)
