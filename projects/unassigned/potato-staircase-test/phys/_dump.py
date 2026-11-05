import sys
from dataclasses import replace
sys.path.insert(0, 'E:/program/1project/video/projects/unassigned/potato-staircase-test')
from phys.scene import VARIANTS
from phys.sim import simulate

a = sys.argv
key = a[1] if len(a) > 1 else 'D'
push = float(a[2]) if len(a) > 2 else 100.0
tmax = float(a[3]) if len(a) > 3 else 6.0
step = int(a[4]) if len(a) > 4 else 6
frac = float(a[5]) if len(a) > 5 else None
sc = next(v for v in VARIANTS if v.key == key)
kw = {'push_v': push}
if frac is not None:
    kw['receiver_frac'] = frac
sc = replace(sc, **kw)
res = simulate(sc, t_max=tmax)
print('rest', [(round(p['pos'][0], 1), round(p['pos'][1], 1)) for p in res['rest']])
print('stair treads:', [(i, sc.x0 + i * sc.step_w, sc.x0 + (i + 1) * sc.step_w) for i in range(4)])
for k in range(0, len(res['trace']['t']), step):
    t = res['trace']['t'][k]
    cells = []
    for p, v, w in zip(res['trace']['pos'][k], res['trace']['vel'][k], res['trace']['angvel'][k]):
        cells.append("(%6.1f,%6.1f) v(%6.0f,%6.0f) w%7.1f" % (p[0], p[1], v[0], v[1], w))
    print("t=%5.2f  " % t + " | ".join(cells) + "  g=%s" % res['trace']['ground'][k])
print('impacts', [(e['t'], e['a'], e['b'], round(e['peak_impulse']), round(e['normal'][0], 2)) for e in res['impacts']])
print('landings', [(e['t'], e['a'], e['tread']) for e in res['landings']])
print('checks', [(c['name'], c['ok'], c['v']) for c in res['checks']])
