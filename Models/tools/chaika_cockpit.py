# chaika_cockpit.py — этап C: кабина и шлюз «Чайки» изнутри, с развёртками под два атласа текстур.
# Запуск в открытом Blender:  python tools/bmcp.py "LIVE_SCRIPT='chaika_cockpit.py'; exec(open(r'C:\UnrealScenes\Models\tools\live_run.py', encoding='utf-8').read())" 900
# (или без окна: bash tools/bl.sh tools/chaika_cockpit.py)  ->  src/chaika_cockpit.blend, export/chaika_cockpit/layout.json, faces_A/B.npz
# ВАЖНО про борта: нос по −Y, значит +X — ЛЕВЫЙ борт (слева от пилота), −X — правый. Ручка управления стоит на −X.
import bpy, bmesh, math, os, sys, json
from mathutils import Vector, Matrix, Euler

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
for _f in ('kit.py', 'chaika_shape.py', 'uvkit.py', 'partkit.py'):
    exec(open(os.path.join(TOOLS, _f), encoding='utf-8').read())
EXP = os.path.join(ROOT, 'export', 'chaika_cockpit')
os.makedirs(EXP, exist_ok=True)
R = math.radians
EY, EZ = EYE[1], EYE[2]

CLS = {'m_white': 10, 'm_dark': 11, 'm_alu': 12, 'm_steel': 13, 'm_chrome': 14, 'm_rubber': 15, 'm_orange': 16, 'm_tread': 18,
       'c_liner': 20, 'c_panel': 21, 'c_plastic': 22, 'c_fabric': 23, 'c_belt': 24, 'c_frame': 25, 'c_knob': 26, 'c_suit': 27,
       'c_bezel': 28, 'c_placard': 29, 'c_panel_lt': 19, 'glass': 60, 'emissive': 61}
_PV = {'m_white': (0.78, 0.78, 0.76), 'm_dark': (0.09, 0.095, 0.10), 'm_alu': (0.70, 0.71, 0.72), 'm_steel': (0.30, 0.30, 0.31),
       'm_chrome': (0.9, 0.9, 0.9), 'm_rubber': (0.03, 0.03, 0.03), 'm_orange': (0.85, 0.33, 0.05), 'm_tread': (0.2, 0.2, 0.21),
       'c_liner': (0.60, 0.59, 0.56), 'c_panel': (0.075, 0.078, 0.082), 'c_plastic': (0.30, 0.31, 0.32), 'c_fabric': (0.12, 0.14, 0.17),
       'c_belt': (0.40, 0.38, 0.34), 'c_frame': (0.50, 0.53, 0.51), 'c_knob': (0.04, 0.04, 0.045), 'c_suit': (0.80, 0.79, 0.75),
       'c_bezel': (0.05, 0.052, 0.055), 'c_placard': (0.78, 0.78, 0.74), 'c_panel_lt': (0.17, 0.18, 0.19)}
for _n, _c in _PV.items():
    defmat(_n, (*_c, 1), metallic=1.0 if _n in ('m_alu', 'm_steel', 'm_chrome') else 0.0, rough=0.5)
defmat('glass', (0.55, 0.75, 0.85, 0.25), rough=0.03, kind='glass')
defmat('emissive', (1.0, 0.93, 0.78, 1), rough=0.3, emis=3.0)
for _k in range(1, 7):
    defmat('screen_%d' % _k, (0.05, 0.12, 0.17, 1), rough=0.25, emis=0.8)
    CLS['screen_%d' % _k] = 40 + _k

# ---------------------------------------------------------------- развёртка внутренней обшивки
_sc = {}


def _sect_in(y):
    yq = round(y, 3)
    v = _sc.get(yq)
    if v is None:
        hp = _half(sec(yq), WALL)
        L = [0.0]
        for a, b in zip(hp[:-1], hp[1:]):
            L.append(L[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        v = _sc[yq] = (hp, L)
    return v


def liner_t(y, x, z):
    hp, L = _sect_in(y)
    x = abs(x)
    be, bs = 1e9, 0.0
    for k in range(len(hp) - 1):
        ax, az = hp[k]
        dx, dz = hp[k + 1][0] - ax, hp[k + 1][1] - az
        d2 = dx * dx + dz * dz
        f = 0.0 if d2 < 1e-12 else max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / d2))
        e = (x - ax - dx * f) ** 2 + (z - az - dz * f) ** 2
        if e < be:
            be, bs = e, L[k] + (L[k + 1] - L[k]) * f
    return L[-1] - bs


SM = max(_sect_in(y)[1][-1] for y in frange(Y_CAP, HATCH_Y - 0.03, 0.1)) + 0.03


def orient(bm, outward):
    bm.normal_update()
    for f in bm.faces:
        c = f.calc_center_median()
        if (f.normal.dot(Vector((c.x, 0, c.z - 2.55))) > 0) != outward:
            f.normal_flip()
    bm.normal_update()


def build_liner(y0, y1, name, atlas, dens, front=False):
    """Внутренняя обшивка отсека; для кабины заодно вырезаются стёкла и отделка переплётов (тем же кодом, что снаружи)."""
    bm = bmesh.new()
    skin(bm, [ring(y, NTH, WALL) for y in hull_stations(y0, y1)], closed=True)
    extra = []
    if front:
        canopy_cuts(bm)
        canopy_mark(bm)
        orient(bm, True)
        bg = extract(bm, [f for f in bm.faces if f.material_index == GLASS])
        for f in bg.faces:
            f.material_index = 0
            f.smooth = True
        for v in bg.verts:
            v.co += (Vector(EYE) - v.co).normalized() * -0.022          # внутреннее стекло — чуть наружу от обшивки
        gl = bm_obj(bg, 'ck_glass', 'glass', 30)
        bf = extract(bm, [f for f in bm.faces if f.material_index == FRAME])
        for f in bf.faces:
            f.material_index = 0
            f.smooth = True
        frame_solid(bf, proud=0.013, depth=0.014)
        extra = [gl, bm_obj(bf, 'trim', 'c_bezel', 35)]
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if max(v.co.z for v in f.verts) < FLOOR_Z - 0.012
                               and f.calc_center_median().y > Y_CHIN_AFT + RIM], context='FACES')
    orient(bm, False)
    L = uvl(bm)
    for f in bm.faces:
        sgn = 1 if f.calc_center_median().x >= 0 else -1
        f.material_index, f.smooth = 0, True
        for lp in f.loops:
            c = lp.vert.co
            lp[L].uv = (c.y - y0, SM + sgn * liner_t(c.y, c.x, c.z))
    ob = bm_obj(bm, name, 'c_liner', 30)
    set_chart(ob, 'skin', y1 - y0, 2 * SM, atlas, dens=dens, panels=[0.52, 0.44], panel_cls=20)
    return ob, extra


def trim_bolts():
    """Крепёж на отделке переплётов (ось болта — по линии взгляда пилота)."""
    E, out = Vector(EYE), []

    def put(p):
        p = Vector(p)
        d = (E - p).normalized()
        out.append(hexbolt(p + d * 0.014, d, 0.013, 0.006, 'm_steel'))
    tan = math.tan(R(AZ_POST))
    for sg in (1, -1):
        for z in frange(Z_SILL + 0.14, 3.50, 0.14):                  # стойки
            lo, hi = Y_CAP, EY
            for _ in range(30):
                mid = (lo + hi) / 2
                if halfwidth(mid, z, WALL) - (EY - mid) * tan > 0:
                    hi = mid
                else:
                    lo = mid
            a = (EY - hi) * tan
            if a > 0.25:
                put((sg * a, hi, z))
        for y in frange(-6.70, -4.56, 0.14):                          # подоконник
            put((sg * halfwidth(y, Z_SILL, WALL), y, Z_SILL))
        for y in frange(-5.20, -4.78, 0.14):                          # пояс над боковым окном
            a = halfwidth(y, Z_HEAD, WALL)
            if _post(a, y)[0] > FRAME_HW + 0.03:
                put((sg * a, y, Z_HEAD))
        for y in frange(Y_SPINE_FRONT + 0.07, -4.95, 0.13):           # хребтовая балка
            put((sg * 0.105, y, top_z(y, 0.105, WALL)))
    return out


def rib(y, w=0.05, h=0.04, mat_name='c_frame'):
    """Шпангоут: рама по внутреннему обводу от пола через потолок до пола."""
    pts = [Vector(p) for p in ring(y, NTH, WALL) if p[2] >= FLOOR_Z - 0.03]
    pts.sort(key=lambda p: math.atan2(p.x, p.z - 2.0))              # слева через верх направо
    rings = []
    for k, p in enumerate(pts):
        t = (pts[min(len(pts) - 1, k + 1)] - pts[max(0, k - 1)]).normalized()
        n = Vector((t.z, 0, -t.x))
        if n.dot(Vector((-p.x, 0, 2.6 - p.z))) < 0:
            n = -n
        a, b = Vector((0, -w / 2, 0)), Vector((0, w / 2, 0))
        rings.append([p + a - n * 0.004, p + b - n * 0.004, p + b + n * h, p + a + n * h])
    return loft('rib', rings, mat_name=mat_name, smooth=35)


def stringer(zf, y0, y1, sg, w=0.035, h=0.03):
    rings = []
    for y in frange(y0, y1, 0.15):
        p = Vector((sg * halfwidth(y, zf(y), WALL), y, zf(y)))
        n = Vector((-sg, 0, 0))
        rings.append([p + Vector((0, 0, -w / 2)) - n * 0.004, p + Vector((0, 0, w / 2)) - n * 0.004,
                      p + Vector((0, 0, w / 2)) + n * h, p + Vector((0, 0, -w / 2)) + n * h])
    return loft('stringer', rings, mat_name='c_frame', smooth=35)


def section_wall(name, y, holes, thick=0.06, mat_name='c_frame'):
    """Поперечная переборка по внутреннему сечению корпуса с прямоугольными проёмами holes = [(x0, x1, z0, z1)]."""
    bm = bmesh.new()
    bm.faces.new([bm.verts.new(p) for p in ring(y, NTH, WALL - 0.01)])
    for x0, x1, z0, z1 in holes:
        for x in (x0, x1):
            cut(bm, (x, 0, 0), (1, 0, 0))
        for z in (z0, z1):
            cut(bm, (0, 0, z), (0, 0, 1))
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if x0 < f.calc_center_median().x < x1 and z0 < f.calc_center_median().z < z1],
                         context='FACES')
    ob = bm_obj(bm, name, mat_name, None)
    solidify(ob, thick, 0.0)
    return ob


def floor_plates(y0, y1):
    out = []
    ys = frange(y0, y1, 0.62)
    for a, b in zip(ys[:-1], ys[1:]):
        hw = min(halfwidth(a, FLOOR_Z, WALL), halfwidth(b, FLOOR_Z, WALL)) + 0.02
        out.append(box('fp', (2 * hw, b - a - 0.006, 0.026), (0, (a + b) / 2, FLOOR_Z - 0.013), bevel=0.003, segs=1, mat_name='m_tread'))
        for sx in (-hw + 0.06, hw - 0.06):
            for yy in (a + 0.05, b - 0.05):
                out.append(hexbolt((sx, yy, FLOOR_Z), (0, 0, 1), 0.016, 0.003))
    return out


def frame_loop(outer, inner, y0, y1, zc, mat_name='m_dark'):
    """Рамка проёма в поперечной стенке: между скруглёнными контурами outer и inner, от y0 до y1."""
    r0 = [(x, y0, zc + z) for x, z in outer]
    rings = [r0, [(x, y1, zc + z) for x, z in outer], [(x, y1, zc + z) for x, z in inner], [(x, y0, zc + z) for x, z in inner], r0]
    return loft('frame', rings, closed=True, cap0=False, cap1=False, mat_name=mat_name, smooth=35)


for _f in ('chaika_cockpit_station.py', 'chaika_cockpit_rear.py', 'chaika_cockpit_detail.py'):
    exec(open(os.path.join(TOOLS, _f), encoding='utf-8').read())


def build_all():
    clear_scene()
    use_coll('chaika_cockpit')
    objs = []
    # ---- кабина: обшивка, стёкла, отделка переплётов
    lin, (gl, trim) = build_liner(Y_CAP, BULKHEAD_Y, 'ck_liner_cockpit', 'A', 0.8, front=True)
    objs += [lin, gl, mech([trim] + trim_bolts(), 'ck_canopy_trim', atlas='A')]
    parts = floor_plates(Y_CHIN_AFT, BULKHEAD_Y - 0.035)
    hw = halfwidth(Y_CHIN_AFT, FLOOR_Z, WALL)
    parts.append(box('riser', (2 * hw + 0.06, 0.03, 0.20), (0, Y_CHIN_AFT - 0.005, FLOOR_Z - 0.10), mat_name='c_frame'))
    parts += [rib(y) for y in (-4.15, -3.55, -2.95)]
    for sg in (1, -1):
        parts.append(stringer(lambda y: sec(y)['zs'] - 0.30, -4.40, BULKHEAD_Y - 0.04, sg))
    parts.append(section_wall('nose_wall', Y_CAP + 0.006, [], 0.02, 'c_bezel'))
    objs.append(mech(parts, 'ck_structure_cockpit', atlas='A', dens=0.7))
    objs += build_station()
    objs += build_detail()
    objs += build_rear_cockpit()
    # ---- шлюз
    lin2, _ = build_liner(BULKHEAD_Y, HATCH_Y - 0.03, 'ck_liner_airlock', 'B', 0.45)
    objs.append(lin2)
    objs += build_airlock()
    root = empty('chaika_cockpit', (0, 0, 0), size=0.5)
    build_markers()
    bpy.context.view_layer.update()
    for o in list(bpy.data.collections['chaika_cockpit'].objects):
        if o is not root and o.parent is None:
            set_parent(o, root)
    return [o for o in bpy.data.collections['chaika_cockpit'].objects if o.type == 'MESH']


if __name__ == '__main__':
    objs = build_all()
    rA, cA = pack_atlas(objs, 'A')
    rB, cB = pack_atlas(objs, 'B')
    apply_atlas(objs, {**rA, **rB})
    json.dump({'A': layout_of(rA, cA), 'B': layout_of(rB, cB)}, open(os.path.join(EXP, 'layout.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    nA = dump_faces(objs, 'A', CLS, os.path.join(EXP, 'faces_A.npz'), cA)
    nB = dump_faces(objs, 'B', CLS, os.path.join(EXP, 'faces_B.npz'), cB)
    tr = sum(tris(o) for o in objs)
    pl = json.loads(bpy.data.objects['ck_faceplates']['chart'])
    print('ТРЕУГОЛЬНИКОВ %d, объектов %d; атлас A: %.0f пикс/м (лицевые панели %.0f), атлас B: %.0f пикс/м; граней A %d, B %d'
          % (tr, len(objs), min(r[2] for r in rA.values()), rA['ck_faceplates'][2] * pl['dens'], min(r[2] for r in rB.values()), nA, nB))
    json.dump(dict(tris=tr, objects=len(objs), screens=SCREENS), open(os.path.join(EXP, 'build_stats.json'), 'w'), ensure_ascii=False)
    for lib in list(bpy.data.libraries):
        bpy.data.libraries.remove(lib)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'src', 'chaika_cockpit.blend'))
    print('SAVED chaika_cockpit.blend')
