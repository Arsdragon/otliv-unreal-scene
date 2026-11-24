# Pulls exact timing out of the scene-1 timeline scripts WITHOUT Unreal (a stub replaces the `unreal` module):
# footsteps, the drone's track relative to the listener, camera heading, the voice-line markers.
# Result: timeline.json next to this file.   python -I extract_timeline.py
import sys, types, json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = r'C:\UnrealScenes\Project\Scripts\scene1'


class _Stub:
    def __init__(self, *a, **k): pass
    def __getattr__(self, n): return _Stub()
    def __call__(self, *a, **k): return _Stub()
    def __iter__(self): return iter(())
    def __getitem__(self, k): return _Stub()
    def __mul__(self, o): return _Stub()
    __rmul__ = __add__ = __radd__ = __sub__ = __rsub__ = __truediv__ = __neg__ = __mul__
    def __bool__(self): return False
    def __float__(self): return 0.0
    def __int__(self): return 0


u = types.ModuleType('unreal')
u.__getattr__ = lambda name: _Stub()
sys.modules['unreal'] = u
sys.path.insert(0, SCRIPTS)
import s3_timeline as T
import s3_v2 as V

# the same patching as V.install(), minus everything that needs the editor
V._orig.update(cam_local=T.cam_local, apply_time=T.apply_time, rings=T.rings, drone_world=T.drone_world, CAM_P=list(T.CAM_P), CAM_L=list(T.CAM_L))
T.CAM_P = V.cam_p2(); T.CAM_L = V.cam_l2()
T.drone_world = V.drone_world2
V.DR_A, V.DR_B = V.build_drone_keys()
T.DR_Y = V.DR_Y2; T.DR_ARM = V.DR_ARM2
T.rings = V.rings2; T.cam_local = V.cam_local2

cr = T.cr
out = {'T_LAND': T.T_LAND, 'T_LIFT': T.T_LIFT, 'T_HIT': T.T_HIT, 'T_UP': T.T_UP, 'T_END': T.T_END,
       'lines': [[t, s] for t, s in T.LINES]}

# footsteps: the same rule as rings(): a grid of 0.31 s, every cell when running, every second cell when walking
steps = []
g = 0.31
for j in range(int(119.0 / g), int(390.0 / g) + 1):
    ts = j * g
    if not (119.0 < ts < 390.0): continue
    x, y, _ = cr(T.CAM_P, ts); x1, y1, _ = cr(T.CAM_P, ts - 0.1)
    v = math.hypot(x - x1, y - y1) / 0.1
    if v > 3.0 or (j % 2 == 0 and v > 0.5):
        side = 1 if (j // (1 if v > 3.0 else 2)) % 2 == 0 else -1
        steps.append([round(ts, 3), round(v, 2), side, round(0.5 + 0.5 * T.n1(j * 0.731, 21), 3)])
out['steps'] = steps

# listener (camera) and the drone, 20 Hz: distance, bearing relative to the view direction (deg, + = right), height
tr = []
t = 100.0
while t <= 400.0:
    d = T.drone_world(t)
    cx, cy, cz, yaw, pitch, roll, focal = T.cam_local(t)
    px, py, pz = cr(T.CAM_P, t)
    row = [round(t, 2), round(px, 2), round(py, 2), round(yaw, 1)]
    if d is not None:
        dx, dy, dz = d[0] - px, d[1] - py, d[2] - pz
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        # UE: X forward, Y right, yaw turns from +X toward +Y -> a positive bearing difference is to the right
        brg = (math.degrees(math.atan2(dy, dx)) - yaw + 180.0) % 360.0 - 180.0
        row += [round(dist, 2), round(brg, 1), round(d[2], 2)]
    tr.append(row)
    t += 0.05
out['track'] = tr
# distance from the listener to the wreck's beacon
out['beacon'] = [[round(tt, 1), round(math.hypot(cr(T.CAM_P, tt)[0] - V.BEACON[0], cr(T.CAM_P, tt)[1] - V.BEACON[1]), 1)] for tt in [x * 0.5 for x in range(2 * 150, 2 * 392)]]
json.dump(out, open(os.path.join(HERE, 'timeline.json'), 'w', encoding='utf-8'), ensure_ascii=False)
run = [s for s in steps if s[1] > 3.0]
print('steps', len(steps), 'running', len(run), 'first', steps[0][0], 'last', steps[-1][0])
print('run from', run[0][0] if run else None, 'to', run[-1][0] if run else None)
dd = [r for r in tr if len(r) > 4]
print('drone samples', len(dd), 'min dist', min(r[4] for r in dd), 'max', max(r[4] for r in dd))
for tt in (107, 125, 140, 170, 200, 235, 270, 300, 331, 360, 380, 396):
    r = min(dd, key=lambda r: abs(r[0] - tt)); print(tt, 'dist', r[4], 'bearing', r[5])
