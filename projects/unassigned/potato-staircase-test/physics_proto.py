import math
import pymunk

# debug simulation only
N = 6
W, H = 90.0, 100.0
SLOPE = math.radians(8)
DROP = W * math.tan(SLOPE)
X0, Y0 = 120.0, 420.0
RADII = [18.0 + i * 1.5 for i in range(N)]

space = pymunk.Space()
space.gravity = (0, 800)
space.damping = 0.999

def seg(a, b, friction=0.9, elasticity=0.05):
    s = pymunk.Segment(space.static_body, a, b, 3)
    s.friction = friction
    s.elasticity = elasticity
    space.add(s)
    return s

for i in range(N):
    x = X0 + i * W
    y = Y0 + i * H
    a = (x, y)
    b = (x + W, y + DROP)
    c = (x + W, y + H)
    seg(a, b)
    if i < N - 1:
        seg(b, c)
    # lip at right end
    seg((b[0], b[1]), (b[0], b[1] - 3), friction=0.9, elasticity=0.05)

bodies = []
shapes = []
for i in range(N):
    x = X0 + i * W
    y = Y0 + i * H
    r = RADII[i]
    cx = x + W - r - 4
    cy = y + (cx - x) * math.tan(SLOPE) - r
    if i == 0:
        cx = x + 22
        cy = y + (cx - x) * math.tan(SLOPE) - r
    mass = r * r * 0.0007
    body = pymunk.Body(mass, pymunk.moment_for_circle(mass, 0, r))
    body.position = (cx, cy)
    shape = pymunk.Circle(body, r)
    shape.friction = 0.9
    shape.elasticity = 0.1
    space.add(body, shape)
    bodies.append(body)
    shapes.append(shape)

# collision log
SIM_T = 0.0
HITS = []

def post_solve(arb, space, data):
    a, b = arb.shapes
    if isinstance(a, pymunk.Circle) and isinstance(b, pymunk.Circle):
        HITS.append((round(SIM_T, 3), round(arb.total_impulse.length, 1)))

space.on_collision(0, 0, post_solve=post_solve)

# initial push
bodies[0].velocity = (80, 0)

for step in range(int(15 * 240)):
    SIM_T = step / 240
    space.step(1 / 240)
    if step % 240 == 0:
        print("t=", step / 240, [(round(b.position.x), round(b.position.y), round(b.angle, 2)) for b in bodies])

print("hits", HITS)
print("final", [(round(b.position.x), round(b.position.y)) for b in bodies])
