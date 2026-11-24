# probe_wreck.py — этап D: обломки старой автоматической станции «НЕВОД-2» (≈3,5 м до гибели): восьмигранный приборный
# блок, 4 опоры, тарелка антенны, 2 солнечных крыла, решётчатая метеомачта с маяком. Разорвана на 12 кусков, каждый —
# отдельный объект; в главном куске под съёмной панелью (отдельный объект) — накопитель (отдельный объект).
# Запуск в открытом Blender:  bash tools/live.sh probe_wreck.py  ->  src/probe_wreck.blend, export/probe_wreck/{layout.json, tris.npz}
# Оси = оси сцены (Blender): Z вверх, волна приходит с +X, хвост обломков тянется к −X. Начало — главный кусок на грунте.
# Панель накопителя смотрит на корабль, если зонд стоит в точке (128,6; −153,2), а корабль — в начале координат сцены.
import bpy, bmesh, math, os, sys, json, random
from mathutils import Vector, Matrix, Euler, Quaternion

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
for _f in ('kit.py', 'uvkit.py', 'partkit.py', 'dkit.py'):
    exec(open(os.path.join(TOOLS, _f), encoding='utf-8').read())
ID = 'probe_wreck'
EXP = os.path.join(ROOT, 'export', ID)
os.makedirs(EXP, exist_ok=True)
R = math.radians
WATER, WATERLINES = 0.45, [0.62, 0.78, 1.02]

CLS = {'w_white': 1, 'w_mli': 2, 'w_dark': 3, 'w_alu': 4, 'w_steel': 5, 'w_cell': 6, 'w_cellback': 7, 'w_orange': 8,
       'w_rubber': 9, 'w_inner': 11, 'w_storage': 12, 'w_dish': 13, 'w_gold': 14,
       'glass': 60, 'emissive_beacon': 61, 'emissive_indicator': 62}
_PV = {'w_white': (0.80, 0.79, 0.75), 'w_mli': (0.70, 0.60, 0.38), 'w_dark': (0.08, 0.08, 0.085), 'w_alu': (0.70, 0.71, 0.72),
       'w_steel': (0.36, 0.35, 0.34), 'w_cell': (0.03, 0.05, 0.10), 'w_cellback': (0.55, 0.56, 0.57), 'w_orange': (0.80, 0.32, 0.07),
       'w_rubber': (0.04, 0.04, 0.045), 'w_inner': (0.36, 0.41, 0.36), 'w_storage': (0.13, 0.14, 0.16), 'w_dish': (0.82, 0.82, 0.80),
       'w_gold': (0.75, 0.56, 0.22)}
for _n, _c in _PV.items():
    defmat(_n, (*_c, 1), metallic=1.0 if _n in ('w_alu', 'w_steel', 'w_gold') else 0.0, rough=0.5)
defmat('glass', (0.6, 0.7, 0.75, 0.3), rough=0.05, kind='glass')
defmat('emissive_beacon', (1.0, 0.42, 0.10, 1), rough=0.3, emis=8.0)
defmat('emissive_indicator', (0.25, 1.0, 0.35, 1), rough=0.3, emis=4.0)

DECALS, SOLAR, OFFS = [], {}, {}
FRONT = []                                  # детали грани с нишей — им плотность текстуры выше
A8 = 0.65                                   # апофема восьмигранника (поперёк граней 1,30 м)
R8 = A8 / math.cos(math.pi / 8)
HB = 0.80                                   # высота блока
EDGE = 2 * A8 * math.tan(math.pi / 8)       # ширина грани 0,54 м
P_FACE = 1                                  # грань с панелью накопителя (нормаль 45° в осях блока)


# ============================================================ помощники
def fnorm(k):
    return Vector((math.cos(R(45 * k)), math.sin(R(45 * k)), 0))


def ftan(k):
    return Vector((-math.sin(R(45 * k)), math.cos(R(45 * k)), 0))


def vert(k, z, r=R8):
    a = R(45 * k + 22.5)
    return Vector((r * math.cos(a), r * math.sin(a), z))


def face_M(k, off=0.0):
    """Оси грани k: X — вдоль грани (против часовой), Y — вверх, Z — наружу; начало — на плоскости грани, z = 0."""
    return frame_M(fnorm(k) * (A8 + off), ftan(k), Vector((0, 0, 1)))


def beam(a, b, w, h, m, up=(0, 0, 1), bevel=0.003):
    a, b = Vector(a), Vector(b)
    d = b - a
    upv = Vector(up)
    if abs(d.normalized().dot(upv)) > 0.95:
        upv = Vector((1, 0, 0)) if abs(d.normalized().x) < 0.9 else Vector((0, 1, 0))
    return place([box('beam', (d.length, h, w), (0, 0, 0), bevel=bevel, mat_name=m)], frame_M((a + b) / 2, d, upv))[0]


def torn_tube(p0, p1, r, m, segs=12, wall=0.003, jag=0.035, seed=0, torn0=False, torn1=True, rings=4):
    """Труба со стенкой от p0 к p1; рваные концы — неровный край с изломами."""
    rng = random.Random(seed)
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length

    def ends(base, sgn, torn):
        if not torn:
            return [base] * segs
        return [base + sgn * jag * rng.random() * (0.35 + 0.65 * abs(math.sin(i * 1.7 + seed))) for i in range(segs)]
    z0s, z1s = ends(0.0, 1, torn0), ends(L, -1, torn1)
    bm = bmesh.new()

    def ring_(rr, zs):
        return [bm.verts.new((rr * math.cos(2 * math.pi * i / segs), rr * math.sin(2 * math.pi * i / segs), zs[i])) for i in range(segs)]
    zlist = [z0s] + [[L * k / rings] * segs for k in range(1, rings)] + [z1s]
    O = [ring_(r, zs) for zs in zlist]
    I = [ring_(r - wall, zs) for zs in zlist]
    for a, b in zip(range(len(O) - 1), range(1, len(O))):
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((O[a][i], O[a][j], O[b][j], O[b][i]))
            bm.faces.new((I[a][j], I[a][i], I[b][i], I[b][j]))
    for i in range(segs):
        j = (i + 1) % segs
        bm.faces.new((O[-1][i], O[-1][j], I[-1][j], I[-1][i]))
        bm.faces.new((O[0][j], O[0][i], I[0][i], I[0][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = bm_obj(bm, 'tube', m, 40)
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    ob.data.transform(Matrix.Translation(p0) @ q.to_matrix().to_4x4())
    return ob


def kink(objs, point, axis, angle, side, blend=0.06):
    """Изгиб: вершины по сторону side от плоскости через point поворачиваются вокруг оси axis (плавно на длине blend)."""
    point, axis, side = Vector(point), Vector(axis).normalized(), Vector(side).normalized()
    for ob in objs:
        for v in ob.data.vertices:
            s = (v.co - point).dot(side)
            if s > 0:
                v.co = point + Matrix.Rotation(angle * min(1.0, s / blend), 3, axis) @ (v.co - point)
        ob.data.update()
    return objs


def dent(objs, center, dirn, radius, depth):
    center, dirn = Vector(center), Vector(dirn).normalized()
    for ob in objs:
        for v in ob.data.vertices:
            dd = (v.co - center).length
            if dd < radius:
                v.co += dirn * depth * (1 - dd / radius) ** 2
        ob.data.update()
    return objs


def jag_line(p0, p1, n, amp, seed):
    rng = random.Random(seed)
    p0, p1 = Vector((*p0, 0)), Vector((*p1, 0))
    d = p1 - p0
    nrm = Vector((-d.y, d.x, 0)).normalized()
    out = []
    for i in range(n + 1):
        t = i / n
        o = 0.0 if i in (0, n) else (rng.random() - 0.5) * 2 * amp
        q = p0 + d * t + nrm * o
        out.append((q.x, q.y))
    return out


def set_mats(ob, names, fn):
    """Назначить материалы граням: fn(центр, нормаль) -> индекс в names."""
    me = ob.data
    me.materials.clear()
    for nm in names:
        me.materials.append(mat(nm))
    for p in me.polygons:
        p.material_index = fn(p.center, p.normal)
    me.update()
    return ob


def piece(parts, name, origin, dens=0.3, angle=55.0, atlas='A'):          # дальние куски — пожиже
    ob = merge(parts, name, origin)
    OFFS[name] = list(origin)
    shade(ob, 38)
    smart_uv(ob, atlas, angle=angle, dens=dens)
    return ob


def place_piece(ob, xy, rot, sink, yaw_first=False):
    """Поставить кусок: поворот rot (градусы, XYZ), затем сдвиг в точку xy так, чтобы низ ушёл в грунт на sink."""
    ob.rotation_euler = Euler([R(a) for a in rot], 'XYZ')
    ob.location = (xy[0], xy[1], 0.0)
    bpy.context.view_layer.update()
    mw = ob.matrix_world
    zmin = min((mw @ v.co).z for v in ob.data.vertices)
    ob.location.z -= zmin + sink
    bpy.context.view_layer.update()
    return ob


def decal(obj, text, c, u, v, h, color='ink', depth=0.03, kind='text', w=None, fade=0.0):
    DECALS.append(dict(obj=obj, kind=kind, text=text, c=[round(x, 5) for x in c], u=[round(x, 5) for x in u],
                       v=[round(x, 5) for x in v], h=h, w=w, color=color, depth=depth, fade=fade))


# ============================================================ главный кусок: приборный блок
def mli_panel(w, seed):
    """Одеяло ЭВТИ: «подушка» с мятой плёнкой, прижимные планки на болтах, подложка."""
    rng = random.Random(seed)
    h0, h1, nx, ny = 0.045, 0.755, 12, 16
    bm = bmesh.new()
    V = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            u, v = i / nx, j / ny
            x, y = -w / 2 + w * u, h0 + (h1 - h0) * v
            z = 0.006 + 0.013 * (math.sin(math.pi * u) * math.sin(math.pi * v)) ** 0.7
            if 0 < i < nx and 0 < j < ny:
                z += (rng.random() - 0.5) * 0.004
            row.append(bm.verts.new((x, y, z)))
        V.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((V[j][i], V[j][i + 1], V[j + 1][i + 1], V[j + 1][i]))
    p = [bm_obj(bm, 'mli', 'w_mli', 30), box('mback', (w, h1 - h0, 0.004), (0, (h0 + h1) / 2, 0.002), mat_name='w_dark')]
    for cx, cy, sx, sy in ((0, h0 + 0.010, w, 0.020), (0, h1 - 0.010, w, 0.020), (-w / 2 + 0.010, (h0 + h1) / 2, 0.020, h1 - h0),
                           (w / 2 - 0.010, (h0 + h1) / 2, 0.020, h1 - h0)):
        p.append(box('strip', (sx, sy, 0.005), (cx, cy, 0.0085), bevel=0.0015, segs=1, mat_name='w_white'))
    for x in frange(-w / 2 + 0.03, w / 2 - 0.03, 0.09):
        for y in (h0 + 0.010, h1 - 0.010):
            p.append(hexbolt((x, y, 0.011), (0, 0, 1), 0.010, 0.004, 'w_steel'))
    for y in frange(h0 + 0.10, h1 - 0.10, 0.12):
        for x in (-w / 2 + 0.010, w / 2 - 0.010):
            p.append(hexbolt((x, y, 0.011), (0, 0, 1), 0.010, 0.004, 'w_steel'))
    return p


def radiator_panel(w):
    p = [box('rad', (w, 0.71, 0.008), (0, 0.40, 0.004), bevel=0.002, segs=1, mat_name='w_white')]
    for x in frange(-w / 2 + 0.045, w / 2 - 0.045, (w - 0.09) / 8):
        p.append(box('fin', (0.004, 0.64, 0.012), (x, 0.40, 0.012), mat_name='w_white'))
    for y in (0.08, 0.72):
        p.append(cyl('hpipe', (-w / 2 + 0.03, y, 0.016), (w / 2 - 0.03, y, 0.016), 0.008, 10, 'w_alu'))
    p += [hexbolt((x, y, 0.008), (0, 0, 1), 0.012, 0.005, 'w_steel') for x in (-w / 2 + 0.02, w / 2 - 0.02) for y in (0.06, 0.40, 0.74)]
    return p


OP_Y, OP_W, OP_H = 0.60, 0.32, 0.26          # проём накопителя на грани P (в осях грани)


def p_panel(w):
    """Панель грани P с проёмом под съёмную крышку накопителя."""
    y0, y1 = OP_Y - OP_H / 2, OP_Y + OP_H / 2
    t = 0.010
    p = [box('pb', (w, y0 - 0.045, t), (0, (0.045 + y0) / 2, t / 2), mat_name='w_white'),
         box('pt', (w, 0.755 - y1, t), (0, (y1 + 0.755) / 2, t / 2), mat_name='w_white'),
         box('pl', (w / 2 - OP_W / 2, OP_H, t), (-(w / 2 + OP_W / 2) / 2, OP_Y, t / 2), mat_name='w_white'),
         box('pr', (w / 2 - OP_W / 2, OP_H, t), ((w / 2 + OP_W / 2) / 2, OP_Y, t / 2), mat_name='w_white')]
    p += [hexbolt((x, y, t), (0, 0, 1), 0.012, 0.005, 'w_steel') for x in (-w / 2 + 0.02, w / 2 - 0.02) for y in (0.07, 0.30, 0.74)]
    for x in (-0.17, 0.0, 0.17):                                          # гнёзда винтов крышки
        for y in (y0 - 0.012, y1 + 0.012):
            p.append(cyl('insert', (x, y, t - 0.001), (x, y, t + 0.002), 0.008, 10, 'w_alu'))
    return p


def bay_parts():
    """Ниша накопителя за проёмом (в осях грани P, внутрь — к −Z): стенки, ложемент, хомуты, разъём, жгут."""
    hw, y0, y1, d = OP_W / 2 - 0.002, OP_Y - OP_H / 2 + 0.002, OP_Y + OP_H / 2 - 0.002, 0.43
    bm = bmesh.new()
    c = [bm.verts.new(v) for v in ((-hw, y0, 0), (hw, y0, 0), (hw, y1, 0), (-hw, y1, 0),
                                    (-hw, y0, -d), (hw, y0, -d), (hw, y1, -d), (-hw, y1, -d))]
    for f in ((c[4], c[5], c[6], c[7]), (c[0], c[1], c[5], c[4]), (c[1], c[2], c[6], c[5]), (c[2], c[3], c[7], c[6]), (c[3], c[0], c[4], c[7])):
        bm.faces.new(f)
    bm.normal_update()
    cen = Vector((0, OP_Y, -d / 2))
    for f in bm.faces:
        if f.normal.dot(cen - f.calc_center_median()) < 0:
            f.normal_flip()
    walls = bm_obj(bm, 'bay', 'w_inner', 30)
    solidify(walls, 0.006, -1.0)                                # толщина — наружу от ниши
    p = [walls]
    cy = y0 + 0.004 + 0.062
    for z in (-0.11, -0.31):
        p += [box('saddle', (0.10, cy - 0.06 - y0, 0.04), (0, (y0 + cy - 0.06) / 2, z), bevel=0.004, mat_name='w_dark'),
              pipe('clamp', [(-0.064, cy - 0.02, z), (-0.066, cy + 0.03, z), (-0.03, cy + 0.066, z), (0.03, cy + 0.066, z),
                             (0.066, cy + 0.03, z), (0.064, cy - 0.02, z)], 0.005, 'w_steel', sides=8, res=3),
              box('latch', (0.02, 0.02, 0.03), (0.068, cy - 0.02, z), bevel=0.003, mat_name='w_steel')]
    p += [box('socket', (0.12, 0.12, 0.03), (0, cy, -d + 0.02), bevel=0.004, mat_name='w_dark'),
          pipe('harness', [(0.03, cy - 0.04, -d + 0.03), (0.10, cy - 0.06, -d + 0.04), (hw - 0.01, y0 + 0.04, -d + 0.06)], 0.012, 'w_rubber', sides=8, res=3)]
    return p, cy


def storage_parts(cy):
    """Накопитель: цилиндр Ø 0,12 × 0,35 вдоль оси ниши, ручка наружу, зелёный индикатор, рифлёные пояса."""
    z0, z1 = -0.395, -0.045
    p = [revolve('st', [(0.0, z0), (0.054, z0), (0.060, z0 + 0.006), (0.060, z1 - 0.006), (0.054, z1), (0.0, z1)], 40, 'Z',
                 (0, cy, 0), 'w_storage')]
    for z in (z0 + 0.03, z1 - 0.03):
        p.append(torus('knurl', (0, cy, z), 0.0605, 0.0035, 'Z', 'w_alu', 40, 6))
    p += [pipe('handle', [(-0.035, cy, z1), (-0.035, cy, z1 + 0.028), (0.035, cy, z1 + 0.028), (0.035, cy, z1)], 0.0065, 'w_dark', sides=10, res=4),
          cyl('grip', (-0.022, cy, z1 + 0.028), (0.022, cy, z1 + 0.028), 0.0085, 12, 'w_rubber'),
          cyl('ledbase', (0.0, cy + 0.035, z1 - 0.001), (0.0, cy + 0.035, z1 + 0.004), 0.009, 12, 'w_dark'),
          revolve('led', [(0.0, z1 + 0.004), (0.0065, z1 + 0.004), (0.005, z1 + 0.008), (0.0, z1 + 0.0095)], 16, 'Z', (0.0, cy + 0.035, 0),
                  'emissive_indicator')]
    for a in range(6):
        x, y = 0.038 * math.cos(R(60 * a + 30)), cy + 0.038 * math.sin(R(60 * a + 30))
        p.append(cyl('pin', (x, y, z0 - 0.006), (x, y, z0 + 0.001), 0.004, 8, 'w_gold'))
    return p


def access_cover():
    """Съёмная крышка накопителя (в осях грани P): пластина с рёбрами, 6 винтов, утопленная ручка."""
    t0 = 0.010
    w, h = OP_W + 0.024, OP_H + 0.024
    p = [box('cover', (w, h, 0.005), (0, OP_Y, t0 + 0.0025), bevel=0.0015, segs=1, mat_name='w_white'),
         loft('rim', [[(x, OP_Y + y, t0 + 0.005) for x, y in rrect(w - 0.010, h - 0.010, 0.012, 3)],
                      [(x, OP_Y + y, t0 + 0.009) for x, y in rrect(w - 0.014, h - 0.014, 0.010, 3)],
                      [(x, OP_Y + y, t0 + 0.009) for x, y in rrect(w - 0.040, h - 0.040, 0.010, 3)],
                      [(x, OP_Y + y, t0 + 0.005) for x, y in rrect(w - 0.044, h - 0.044, 0.010, 3)]],
              closed=True, cap0=False, cap1=False, mat_name='w_white', smooth=40),
         box('cup', (0.07, 0.03, 0.004), (0, OP_Y - 0.075, t0 + 0.0065), bevel=0.002, segs=1, mat_name='w_dark'),
         cyl('tbar', (-0.025, OP_Y - 0.075, t0 + 0.010), (0.025, OP_Y - 0.075, t0 + 0.010), 0.004, 8, 'w_alu')]
    for x in (-0.17, 0.0, 0.17):
        for y in (OP_Y - OP_H / 2 - 0.012, OP_Y + OP_H / 2 + 0.012):
            p.append(hexbolt((x, y, t0 + 0.005), (0, 0, 1), 0.012, 0.0045, 'w_steel'))
    return p


def build_bus():
    p = []
    for k in range(8):                                                   # каркас: стойки и пояса
        v = vert(k, 0, R8 * 0.985)
        p.append(box('post', (0.045, 0.045, HB), (v.x, v.y, HB / 2), bevel=0.004, mat_name='w_white', rot=(0, 0, 45 * k + 22.5)))
        for z in (0.022, HB - 0.022):
            p.append(beam(vert(k - 1, z, R8 * 0.985), vert(k, z, R8 * 0.985), 0.04, 0.044, 'w_white'))
    octa = [(v.x, v.y) for v in (vert(k, 0, R8 * 0.995) for k in range(8))]
    p += [prism('deck', octa, HB - 0.004, HB + 0.012, 'Z', bevel=0.004, mat_name='w_white'),
          prism('bottom', octa, -0.012, 0.004, 'Z', bevel=0.004, mat_name='w_dark'),
          prism('shelf', [(v.x, v.y) for v in (vert(k, 0, R8 * 0.90) for k in range(8))], 0.395, 0.405, 'Z', mat_name='w_inner')]
    w = EDGE - 0.055
    for k in range(8):
        M = face_M(k, -0.006)
        if k == P_FACE:
            fr = place(p_panel(w), M)
            bp, cy = bay_parts()
            fr += place(bp, M)
            FRONT.extend(fr)
            p += fr
        elif k in (0, 3, 6):
            p += place(mli_panel(w, k), M)
        elif k in (2, 4, 7):
            p += place(radiator_panel(w), M)
    # внутренности за сорванной панелью (грань 5): блоки, аккумулятор, жгуты свисают наружу
    M5 = face_M(5, 0.0)
    inner = [box('box1', (0.30, 0.16, 0.22), (-0.08, 0.52, -0.16), bevel=0.006, mat_name='w_dark'),
             box('box2', (0.20, 0.14, 0.18), (0.14, 0.50, -0.20), bevel=0.006, mat_name='w_inner'),
             box('batt', (0.36, 0.20, 0.24), (0.0, 0.17, -0.22), bevel=0.008, mat_name='w_dark'),
             box('battband', (0.362, 0.04, 0.242), (0.0, 0.22, -0.22), mat_name='w_orange'),
             box('rib', (EDGE, 0.03, 0.05), (0, 0.40, -0.03), mat_name='w_inner')]
    for i, (x0, y0, x1, y1) in enumerate(((-0.10, 0.44, -0.18, -0.30), (0.05, 0.43, 0.10, -0.40), (0.15, 0.40, 0.30, -0.35))):
        inner.append(pipe('hang', [(x0, y0, -0.10), (x0 + 0.02, y0 - 0.05, 0.05), (x1 * 0.6, 0.10, 0.25), (x1, y1, 0.40)],
                          0.010 + 0.003 * i, 'w_rubber' if i != 1 else 'w_orange', sides=8, res=5))
    p += place(inner, M5)
    # палуба: обломок подвеса антенны, пенёк мачты, приборный блок, датчик Солнца
    p += [torn_tube((0.22, -0.18, HB + 0.012), (0.22, -0.18, HB + 0.16), 0.085, 'w_alu', segs=20, wall=0.006, jag=0.05, seed=3),
          prism('gflange', [(0.22 + 0.13 * math.cos(R(a)), -0.18 + 0.13 * math.sin(R(a))) for a in range(0, 360, 30)], HB + 0.012,
                HB + 0.024, 'Z', bevel=0.003, mat_name='w_alu'),
          box('ibox', (0.18, 0.12, 0.08), (0.20, 0.30, HB + 0.052), bevel=0.006, mat_name='w_white'),
          revolve('sunsens', [(0.0, 0.0), (0.03, 0.0), (0.028, 0.012), (0.012, 0.022), (0.0, 0.024)], 16, 'Z', (-0.05, -0.38, HB + 0.012), 'w_dark')]
    for a in (90, 210, 330):                                             # пенёк мачты: три пояса фермы
        q = Vector((-0.30 + 0.092 * math.cos(R(a)), 0.18 + 0.092 * math.sin(R(a)), HB + 0.012))
        p.append(torn_tube(q, q + Vector((0, 0, 0.14 + 0.05 * math.sin(R(a)))), 0.0125, 'w_alu', segs=10, wall=0.0025, jag=0.03, seed=a))
    p.append(prism('mbase', [(-0.30 + 0.14 * math.cos(R(a)), 0.18 + 0.14 * math.sin(R(a))) for a in (90, 210, 330)], HB + 0.012, HB + 0.024,
                   'Z', bevel=0.004, mat_name='w_alu'))
    # узлы опор на углах 0, 2, 4, 6: опора A (угол 6) осталась, согнута; на углах 0 и 2 — обрывки; угол 4 — пустой узел
    for k in (0, 2, 4, 6):
        n = (vert(k, 0) - Vector((0, 0, 0))).normalized()
        for z in (0.06, 0.45):
            c = vert(k, z, R8 + 0.03)
            p.append(box('lugs', (0.06, 0.10, 0.10), c, bevel=0.006, mat_name='w_alu', rot=(0, 0, 45 * k + 22.5)))
        if k in (0, 2):
            c = vert(k, 0.45, R8 + 0.05)
            p.append(torn_tube(c, c + n * 0.16 + Vector((0, 0, -0.11)), 0.035, 'w_alu', segs=14, wall=0.004, jag=0.05, seed=k + 10))
    c = vert(6, 0.45, R8 + 0.05)
    n6 = vert(6, 0).normalized()
    legA = [torn_tube(c, c + n6 * 0.62 + Vector((0, 0, -0.50)), 0.035, 'w_alu', segs=14, wall=0.004, jag=0.06, seed=61, rings=8),
            cyl('shockA', c + n6 * 0.12 + Vector((0, 0, -0.10)), c + n6 * 0.32 + Vector((0, 0, -0.26)), 0.048, 16, 'w_white', bevel=0.006)]
    kink(legA, c + n6 * 0.36 + Vector((0, 0, -0.29)), Vector((-n6.y, n6.x, 0)), R(38), n6 + Vector((0, 0, -0.8)), blend=0.08)
    p += legA
    cl = vert(5, 0.06, R8 + 0.05)
    p.append(torn_tube(cl, cl + (n6 * 0.45 + (cl - c).normalized() * 0.1 + Vector((0, 0, -0.10))), 0.022, 'w_alu', segs=10, wall=0.003, seed=62))
    for k in range(0, 8, 2):                                             # рваные кронштейны двигательного отсека снизу
        q = vert(k, -0.012, R8 * 0.55)
        p.append(box('dbrk', (0.08, 0.05, 0.10), q + Vector((0, 0, -0.05)), bevel=0.004, mat_name='w_alu', rot=(0, 0, 45 * k + 22.5)))
    return p


# ============================================================ остальные куски (каждый — в своих осях)
def truss(z0, z1, side=0.16, rlong=0.0125, rbr=0.0065, step=0.25, jag0=False, jag1=False, seed=0):
    """Треугольная ферма вдоль +Z: три пояса-трубы, горизонтальные и диагональные раскосы."""
    rc = side / math.sqrt(3)
    corners = [Vector((rc * math.cos(R(90 + 120 * i)), rc * math.sin(R(90 + 120 * i)), 0)) for i in range(3)]
    p = []
    for i, c in enumerate(corners):
        p.append(torn_tube(c + Vector((0, 0, z0)), c + Vector((0, 0, z1 + (0.03 * math.sin(i * 2.1 + seed) if jag1 else 0))), rlong,
                           'w_alu', segs=10, wall=0.0025, jag=0.03, seed=seed + i, torn0=jag0, torn1=jag1, rings=2))
    zs = frange(z0 + 0.06, z1 - 0.06, step)
    for k, z in enumerate(zs):
        for i in range(3):
            a, b = corners[i] + Vector((0, 0, z)), corners[(i + 1) % 3] + Vector((0, 0, z))
            p.append(cyl('hbr', a, b, rbr, 6, 'w_alu'))
            if k + 1 < len(zs):
                p.append(cyl('dbr', a, corners[(i + 1) % 3] + Vector((0, 0, zs[k + 1])), rbr * 0.85, 6, 'w_alu'))
    return p, corners


def build_mast_top():
    p, cs = truss(0.0, 1.15, jag0=True, seed=21)
    p += [prism('mtop', [(c.x * 1.6, c.y * 1.6) for c in cs], 1.15, 1.165, 'Z', bevel=0.003, mat_name='w_alu'),
          cyl('bhouse', (0, 0, 1.165), (0, 0, 1.28), 0.058, 24, 'w_dark', bevel=0.006),
          cyl('bring', (0, 0, 1.275), (0, 0, 1.29), 0.064, 24, 'w_alu', bevel=0.002),
          revolve('blens', [(0.0, 1.29), (0.050, 1.29), (0.048, 1.32), (0.036, 1.345), (0.0, 1.355)], 24, 'Z', (0, 0, 0), 'emissive_beacon')]
    for a in range(0, 360, 90):                                          # защитная клетка маяка
        x, y = 0.066 * math.cos(R(a + 45)), 0.066 * math.sin(R(a + 45))
        p.append(cyl('cage', (x, y, 1.285), (x * 0.4, y * 0.4, 1.385), 0.0028, 6, 'w_steel'))
    p += [torus('cagering', (0, 0, 1.385), 0.028, 0.003, 'Z', 'w_steel', 16, 6),
          cyl('whip', (0.07, 0.0, 1.165), (0.09, 0.02, 1.70), 0.004, 8, 'w_steel'),
          cyl('arm1', (0.0, 0.0, 1.05), (0.24, 0.0, 1.05), 0.008, 8, 'w_alu'),
          cyl('ashaft', (0.24, 0.0, 1.05), (0.24, 0.0, 1.16), 0.006, 8, 'w_steel')]
    for a in range(0, 360, 120):                                         # анемометр
        e = Vector((math.cos(R(a)), math.sin(R(a)), 0))
        cpt = Vector((0.24, 0.0, 1.16)) + e * 0.075
        p += [cyl('aarm', Vector((0.24, 0.0, 1.16)), cpt, 0.0035, 6, 'w_steel'),
              revolve('cup', [(0.0, -0.022), (0.016, -0.018), (0.022, -0.006), (0.022, 0.0), (0.019, 0.0), (0.0, -0.019)], 12, 'X', (0, 0, 0), 'w_white')]
        p[-1].data.transform(Matrix.Translation(cpt) @ Matrix.Rotation(R(a + 90), 4, 'Z'))
    p += [cyl('arm2', (0.0, 0.0, 0.92), (-0.22, 0.0, 0.92), 0.008, 8, 'w_alu'),
          prism('vane', [(-0.22, 0.0), (-0.40, 0.03), (-0.40, -0.03)], 0.89, 0.95, 'Z', mat_name='w_white'),
          pipe('mcable', [(0.0, -0.09, 0.05), (0.0, -0.10, 0.6), (0.0, -0.09, 1.16)], 0.008, 'w_rubber', sides=8, res=3)]
    return p


def build_mast_low():
    p, cs = truss(0.0, 0.92, jag1=True, seed=31)
    p.append(prism('mflange', [(c.x * 1.9, c.y * 1.9) for c in cs], -0.012, 0.0, 'Z', bevel=0.003, mat_name='w_alu'))
    for c in cs:
        p.append(hexbolt(c * 1.55 + Vector((0, 0, -0.012)), (0, 0, -1), 0.016, 0.008, 'w_steel'))
    kink(p, (0, 0, 0.52), (1, 0, 0), R(24), (0, 0, 1), blend=0.10)
    return p


def build_leg(seed):
    """Опора в своих осях: тарелка у начала координат, основная стойка с амортизатором вверх-вбок, оборванный верх."""
    top = Vector((-0.95, 0.0, 1.30))
    foot = Vector((0.0, 0.0, 0.10))
    d = (top - foot).normalized()
    p = [revolve('pad', [(0.0, 0.0), (0.17, 0.0), (0.175, 0.012), (0.15, 0.05), (0.06, 0.08), (0.0, 0.085)], 28, 'Z', (0, 0, 0), 'w_alu'),
         revolve('ball', [(0.0, 0.07), (0.035, 0.08), (0.04, 0.10), (0.03, 0.12), (0.0, 0.13)], 14, 'Z', (0, 0, 0), 'w_steel'),
         torn_tube(foot, top, 0.035, 'w_alu', segs=14, wall=0.004, jag=0.07, seed=seed, rings=6),
         cyl('shock', foot + d * 0.10, foot + d * 0.55, 0.050, 16, 'w_white', bevel=0.006),
         cyl('collar', foot + d * 0.53, foot + d * 0.58, 0.056, 16, 'w_steel')]
    knee = foot + d * 0.95
    for s in (1, -1):
        p.append(torn_tube(knee, knee + Vector((-0.10, s * 0.38, 0.18)), 0.022, 'w_alu', segs=10, wall=0.003, jag=0.05, seed=seed + s))
    p.append(pipe('lcable', [foot + d * 0.12 + Vector((0, 0.05, 0)), foot + d * 0.6 + Vector((0, 0.06, 0)), foot + d * 1.1 + Vector((0, 0.05, 0))],
                  0.006, 'w_rubber', sides=6, res=3))
    return p


def build_propulsion():
    a, h = 0.50, 0.35
    r8 = a / math.cos(math.pi / 8)
    p = []
    for k in range(8):
        v = Vector((r8 * 0.98 * math.cos(R(45 * k + 22.5)), r8 * 0.98 * math.sin(R(45 * k + 22.5)), 0))
        p.append(box('ppost', (0.035, 0.035, h), (v.x, v.y, h / 2), bevel=0.003, mat_name='w_white', rot=(0, 0, 45 * k + 22.5)))
        vb = Vector((r8 * 0.98 * math.cos(R(45 * k - 22.5)), r8 * 0.98 * math.sin(R(45 * k - 22.5)), 0))
        p.append(beam(vb + Vector((0, 0, 0.02)), v + Vector((0, 0, 0.02)), 0.035, 0.035, 'w_white'))
        if k % 2 == 0:
            p.append(beam(vb + Vector((0, 0, h - 0.02)), v + Vector((0, 0, h - 0.02)), 0.035, 0.035, 'w_white'))
    octa = [(r8 * 0.99 * math.cos(R(45 * k + 22.5)), r8 * 0.99 * math.sin(R(45 * k + 22.5))) for k in range(8)]
    p.append(prism('pbot', octa, -0.010, 0.004, 'Z', bevel=0.003, mat_name='w_dark'))
    for sx in (-0.20, 0.20):                                             # баки
        p.append(revolve('tank', [(0.15 * math.sin(math.pi * k / 12), 0.17 - 0.15 * math.cos(math.pi * k / 12)) for k in range(13)], 28, 'Z',
                         (sx, 0.0, 0.0), 'w_alu'))
    for k in range(4):                                                   # сопла и трубопроводы
        c = Vector((0.27 * math.cos(R(90 * k + 45)), 0.27 * math.sin(R(90 * k + 45)), 0))
        p.append(revolve('bell', [(0.012, -0.01), (0.03, -0.04), (0.05, -0.10), (0.055, -0.12), (0.051, -0.12), (0.026, -0.04), (0.010, -0.01)], 20,
                         'Z', c, 'w_steel', closed=True, cap=False))
        p.append(pipe('feed', [c + Vector((0, 0, 0.0)), c * 0.7 + Vector((0, 0, 0.08)), Vector((0.20 if c.x > 0 else -0.20, 0, 0.17))],
                      0.007, 'w_steel', sides=8, res=3))
    for k in range(0, 8, 2):                                             # оборванные кронштейны крепления к блоку
        v = Vector((r8 * 0.55 * math.cos(R(45 * k + 22.5)), r8 * 0.55 * math.sin(R(45 * k + 22.5)), h))
        p.append(torn_tube(v, v + Vector((0, 0, 0.09)), 0.02, 'w_alu', segs=10, wall=0.003, seed=40 + k))
    return p


def build_dish():
    f, rmax = 0.42, 0.60
    zf = lambda r: r * r / (4 * f)
    front = [(0.0, 0.0)] + [(r, zf(r)) for r in frange(0.06, rmax, 0.03)]
    p = [revolve('dfront', front + [(rmax + 0.012, zf(rmax) + 0.004)], 64, 'Z', (0, 0, 0), 'w_dish', cap=False),
         revolve('dback', [(rmax + 0.012, zf(rmax) + 0.004)] + [(r, zf(r) - 0.018) for r in frange(rmax, 0.06, -0.03)] + [(0.0, -0.018)],
                 64, 'Z', (0, 0, 0), 'w_white', cap=False),
         torus('drim', (0, 0, zf(rmax) + 0.002), rmax + 0.008, 0.009, 'Z', 'w_white', 64, 8),
         cyl('dhub', (0, 0, -0.12), (0, 0, -0.01), 0.10, 24, 'w_dark', bevel=0.008),
         torn_tube((0, 0, -0.12), (0.0, 0.0, -0.26), 0.06, 'w_alu', segs=16, wall=0.005, jag=0.06, seed=51)]
    for k in range(8):                                                   # рёбра на тыльной стороне
        e = Vector((math.cos(R(45 * k)), math.sin(R(45 * k)), 0))
        rings = []
        for r in frange(0.10, rmax - 0.02, 0.05):
            c = e * r + Vector((0, 0, zf(r) - 0.018))
            nr = Vector((-r / (2 * f), 0, 1)).normalized()
            n3 = (e * nr.x + Vector((0, 0, nr.z))).normalized()
            t = Vector((-e.y, e.x, 0))
            rings.append([c + t * 0.008, c - t * 0.008, c - t * 0.008 - n3 * 0.035, c + t * 0.008 - n3 * 0.035])
        p.append(loft('drib', rings, mat_name='w_white', smooth=None))
    feed = Vector((0, 0, f))                                             # облучатель на треноге, одна стойка оборвана
    for k, a in enumerate((90, 210, 330)):
        rim = Vector((rmax * math.cos(R(a)), rmax * math.sin(R(a)), zf(rmax)))
        if k == 2:
            p.append(torn_tube(rim, rim + (feed - rim) * 0.45, 0.012, 'w_alu', segs=10, wall=0.0025, seed=52))
        else:
            p.append(cyl('fstrut', rim, feed + (rim - feed).normalized() * 0.04, 0.012, 10, 'w_alu'))
    p += [revolve('horn', [(0.0, f - 0.05), (0.045, f - 0.05), (0.045, f - 0.02), (0.07, f + 0.05), (0.066, f + 0.05), (0.040, f - 0.015),
                           (0.0, f - 0.015)], 24, 'Z', (0, 0, 0), 'w_gold'),
          box('fbox', (0.10, 0.10, 0.06), (0, 0, f - 0.08), bevel=0.006, mat_name='w_white')]
    dent(p, (rmax * math.cos(R(60)), rmax * math.sin(R(60)), zf(rmax)), (0.2, 0.3, -1), 0.30, 0.07)
    return p


def build_solar(x0, x1, jag0, jag1, seed, hinge=False):
    """Солнечное крыло (или его часть) в своих осях: X — вдоль крыла 1,40 м, Y — 0,70 м; элементы — на +Z."""
    SW, SH, ST = 1.40, 0.70, 0.030
    right = jag_line((x1, -SH / 2), (x1, SH / 2), 9, 0.045, seed) if jag1 else [(x1, -SH / 2), (x1, SH / 2)]
    left = jag_line((x0, SH / 2), (x0, -SH / 2), 9, 0.045, seed + 7) if jag0 else [(x0, SH / 2), (x0, -SH / 2)]
    poly = right + left
    ob = prism('sol', poly, 0.0, ST, 'Z', bevel=0.0 if (jag0 or jag1) else 0.003, mat_name='w_cellback')
    set_mats(ob, ['w_cellback', 'w_cell'], lambda c, n: 1 if n.z > 0.9 else 0)
    p = [ob]
    lo, hi = max(x0, -SW / 2 + 0.02) + (0.06 if jag0 else 0), min(x1, SW / 2 - 0.02) - (0.06 if jag1 else 0)
    for y in (-0.30, 0.0, 0.30):                                         # рёбра жёсткости сзади
        p.append(box('srib', (hi - lo, 0.020, 0.012), ((lo + hi) / 2, y, -0.006), mat_name='w_cellback'))
    for x in frange(lo, hi, max(0.2, (hi - lo) / 4)):
        p.append(box('srib', (0.020, SH - 0.06, 0.010), (x, 0.0, -0.005), mat_name='w_cellback'))
    if hinge:
        for y in (-0.22, 0.22):
            p += [box('hbr', (0.08, 0.05, 0.05), (-SW / 2 - 0.03, y, 0.012), bevel=0.004, mat_name='w_alu'),
                  torn_tube((-SW / 2 - 0.05, y - 0.03, 0.012), (-SW / 2 - 0.05, y + 0.06, 0.012), 0.012, 'w_steel', segs=10, wall=0.003, seed=y > 0)]
    return p


def build_frag1():
    poly = [(-0.42, -0.24), (0.42, -0.24)] + jag_line((0.42, -0.24), (0.36, 0.24), 6, 0.04, 81)[1:] + [(-0.42, 0.24)]
    pl = prism('rplate', poly, 0.0, 0.008, 'Z', mat_name='w_white')
    p = [pl] + [box('rfin', (0.004, 0.44, 0.012), (x, 0.0, 0.014), mat_name='w_white') for x in frange(-0.36, 0.24, 0.12)]
    p.append(cyl('rpipe', (-0.40, -0.20, 0.016), (0.30, -0.20, 0.016), 0.008, 10, 'w_alu'))
    kink(p, (0.05, 0, 0), (0, 1, 0), R(22), (1, 0, 0), blend=0.06)
    return p


def build_frag2():
    p = [box('tbox', (0.32, 0.24, 0.18), (0, 0, 0.09), bevel=0.008, mat_name='w_white'),
         box('tlid', (0.326, 0.246, 0.012), (0, 0, 0.176), bevel=0.003, mat_name='w_white'),
         box('tbrk', (0.36, 0.05, 0.012), (0, -0.13, 0.006), mat_name='w_alu')]
    for x in (-0.09, 0.0, 0.09):
        p += [cyl('conn', (x, 0.12, 0.09), (x, 0.145, 0.09), 0.016, 14, 'w_gold'),
              cyl('connr', (x, 0.118, 0.09), (x, 0.124, 0.09), 0.021, 14, 'w_dark')]
    for i, (dx, end) in enumerate(((-0.09, (-0.30, 0.95, 0.01)), (0.0, (0.25, 1.05, 0.0)), (0.09, (0.45, 0.70, 0.01)))):
        p.append(pipe('tcab', [(dx, 0.145, 0.09), (dx, 0.25, 0.06), (end[0] * 0.5, end[1] * 0.6, 0.02), end], 0.008,
                      'w_orange' if i == 1 else 'w_rubber', sides=8, res=4))
    p += [pipe('thandle', [(-0.10, -0.12, 0.12), (-0.10, -0.145, 0.13), (0.10, -0.145, 0.13), (0.10, -0.12, 0.12)], 0.006, 'w_steel', sides=8, res=3)]
    return p


# ============================================================ сборка и раскладка
def build_all():
    clear_scene()
    use_coll(ID)
    root = empty(ID, (0, 0, 0), size=0.5)
    bp_all = build_bus()
    hid = [o for o in bp_all if o.name.split('.')[0] in ('mback', 'bottom', 'shelf')]   # скрытое — в отдельный объект, пожиже
    front = [o for o in bp_all if o in FRONT and o not in hid]
    # грань с нишей, крышка и накопитель — в своём атласе M (второй набор 2048): камера работает в 1–2 м от ниши
    bus = piece([o for o in bp_all if o not in hid and o not in front], 'wr_bus', (0, 0, 0), dens=1.0, angle=50.0)
    busf = piece(front, 'wr_bus_front', (0, 0, 0), dens=1.0, angle=50.0, atlas='M')     # при экспорте вливается в wr_bus
    set_parent(busf, bus)
    inner = piece(hid, 'wr_bus_inner', (0, 0, 0), dens=0.25)
    set_parent(inner, bus)
    MP = face_M(P_FACE, -0.006)
    cov_c = MP @ Vector((0, OP_Y, 0.0))
    cover = piece(place(access_cover(), MP), 'wr_panel', tuple(cov_c), dens=1.15, atlas='M')
    cy = OP_Y - OP_H / 2 + 0.002 + 0.004 + 0.062                    # ось накопителя в нише (как в bay_parts)
    st_c = MP @ Vector((0, cy, -0.22))
    stor = piece(place(storage_parts(cy), MP), 'wr_storage', tuple(st_c), dens=1.15, atlas='M')
    set_parent(cover, bus)
    set_parent(stor, bus)
    # главный кусок: панель накопителя — к кораблю, сторона с панелью приподнята на 14°
    n_p = Vector((-0.643, 0.766, 0)).normalized()
    yaw = math.degrees(math.atan2(n_p.y, n_p.x)) - 45 * P_FACE
    t_ax = Vector((0, 0, 1)).cross(n_p).normalized()
    Rm = Matrix.Rotation(R(-14), 4, t_ax) @ Matrix.Rotation(R(yaw), 4, 'Z')
    bus.matrix_world = Rm
    bpy.context.view_layer.update()
    zmin = min((bus.matrix_world @ vert(k, -0.012)).z for k in range(8))     # посадка — по днищу (жгуты и опора уходят в грунт)
    bus.matrix_world = Matrix.Translation((0, 0, -zmin - 0.07)) @ Rm
    bpy.context.view_layer.update()
    # опорная точка верхушки мачты — на кромке палубы со стороны, повёрнутой на 45° от панели
    best = None
    for k in range(8):
        e = bus.matrix_world @ ((vert(k - 1, HB + 0.012) + vert(k, HB + 0.012)) / 2)
        dirn = Vector((e.x, e.y, 0)).normalized()
        sc = dirn.dot(Vector((math.cos(R(175)), math.sin(R(175)), 0)))
        if best is None or sc > best[0]:
            best = (sc, e)
    S = best[1] + Vector((0, 0, 0.03))
    A = S + Vector((S.x, S.y, 0)).normalized() * 1.0
    A.z = -0.02
    pieces = []
    mt = piece(build_mast_top(), 'wr_mast_top', (0, 0, 0))
    u = (S - A).normalized()
    mt.matrix_world = Matrix.Translation(A) @ Vector((0, 0, 1)).rotation_difference(u).to_matrix().to_4x4() @ Matrix.Rotation(R(30), 4, 'Z')
    pieces.append(mt)
    for nm, parts, org, xy, rot, sink in (
            ('wr_propulsion', build_propulsion(), (0, 0, 0.17), (-2.8, -1.25), (75, 0, 30), 0.05),
            ('wr_mast_low', build_mast_low(), (0, 0, 0.45), (-3.6, 3.1), (0, 88, 15), 0.02),
            ('wr_solar_A', build_solar(-0.70, 0.70, False, False, 61, hinge=True), (0, 0, 0.015), (-4.6, -3.1), (50, 0, -20), 0.04),
            ('wr_leg_B', build_leg(71), (-0.45, 0, 0.6), (-5.6, 1.9), (-84, 0, 120), 0.03),
            ('wr_frag_2', build_frag2(), (0, 0, 0.09), (-6.6, 4.6), (0, 0, 40), 0.02),
            ('wr_dish', build_dish(), (0, 0, 0.10), (-8.0, -0.9), (58, 0, 200), 0.05),
            ('wr_frag_1', build_frag1(), (0, 0, 0.0), (-9.6, -4.4), (18, 0, 70), 0.02),
            ('wr_solar_B1', build_solar(-0.70, 0.10, False, True, 62), (-0.30, 0, 0.015), (-11.6, 2.7), (72, 0, 10), 0.12),
            ('wr_solar_B2', build_solar(0.10, 0.70, True, False, 62), (0.40, 0, 0.015), (-14.1, -2.3), (3, 0, 65), 0.01),
            ('wr_leg_C', build_leg(72), (-0.45, 0, 0.6), (-17.0, 1.0), (0, 140, 30), 0.15)):
        ob = piece(parts, nm, org)
        place_piece(ob, xy, rot, sink)
        pieces.append(ob)
    for nm in ('wr_solar_A', 'wr_solar_B1', 'wr_solar_B2'):
        SOLAR[nm] = dict(offset=OFFS[nm], x=[-0.68, 0.68], y=[-0.33, 0.33], top=0.030)
    # метки
    marker('panel_center', cover.matrix_world.translation, bus.matrix_world.to_3x3() @ fnorm(P_FACE), cover, 0.1)
    marker('storage_handle', bus.matrix_world @ (MP @ Vector((0, cy, -0.045 + 0.028))), bus.matrix_world.to_3x3() @ fnorm(P_FACE), stor, 0.05)
    marker('light_indicator', bus.matrix_world @ (MP @ Vector((0, cy + 0.035, -0.045 + 0.009))), bus.matrix_world.to_3x3() @ fnorm(P_FACE), stor, 0.03)
    marker('light_beacon', mt.matrix_world @ Vector((0, 0, 1.33)), mt.matrix_world.to_3x3() @ Vector((0, 0, 1)), mt, 0.08)
    # надписи (для художника текстур): в осях детали; оси грани k у блока — u = касательная, v = вверх
    for k, txt in ((2, 'НЕВОД-2'), (4, 'НЕВОД-2')):
        c = fnorm(k) * (A8 + 0.008) + Vector((0, 0, 0.30))
        decal('wr_bus', txt, c, ftan(k), (0, 0, 1), 0.10, depth=0.04, fade=0.35)
        decal('wr_bus', 'АВТОМАТИЧЕСКАЯ СТАНЦИЯ', fnorm(k) * (A8 + 0.008) + Vector((0, 0, 0.19)), ftan(k), (0, 0, 1), 0.026, depth=0.04, fade=0.35)
    decal('wr_bus', 'ВЫСОКОЕ НАПРЯЖЕНИЕ', fnorm(7) * (A8 + 0.008) + Vector((0, 0, 0.66)), ftan(7), (0, 0, 1), 0.024, 'orange', 0.04, fade=0.5)
    cc = MP @ Vector((0, OP_Y, 0.0))
    for txt, dy, h in (('НАКОПИТЕЛЬ ДАННЫХ', 0.050, 0.024), ('СНЯТЬ КРЫШКУ — 6 ВИНТОВ', 0.012, 0.015)):
        decal('wr_panel', txt, (MP @ Vector((0, OP_Y + dy, 0.015))) - cc, ftan(P_FACE), (0, 0, 1), h, depth=0.02, fade=0.2)
    decal('wr_panel', '', (MP @ Vector((0, OP_Y, 0.015))) - cc, ftan(P_FACE), (0, 0, 1), OP_H + 0.004, 'orange', 0.02, kind='rect',
          w=OP_W + 0.004, fade=0.3)
    ax_out = fnorm(P_FACE)
    side = Vector((0, 0, 1))
    vlab = -ftan(P_FACE)                                                  # наклейка сверху цилиндра, строка — вдоль оси
    for txt, off in (('НАКОПИТЕЛЬ НД-4', 0.008), ('№ 0127', -0.012)):
        cpt = (MP @ Vector((0, cy + 0.0605, -0.21))) - st_c
        decal('wr_storage', txt, cpt + vlab * off, -ax_out, vlab, 0.016 if off > 0 else 0.012, 'label', 0.02)
    decal('wr_frag_2', 'БЛОК ТЕЛЕМЕТРИИ', Vector((0, -0.121, 0.10)) - Vector(OFFS['wr_frag_2']), (1, 0, 0), (0, 0, 1), 0.022, depth=0.02, fade=0.3)
    bpy.context.view_layer.update()
    for o in list(bpy.data.collections[ID].objects):
        if o is not root and o.parent is None:
            set_parent(o, root)
    return [bus, busf, inner, cover, stor] + pieces


if __name__ == '__main__':
    objs = build_all()
    pts = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    print('РАЗБРОС: x %.1f…%.1f, y %.1f…%.1f, z %.2f…%.2f' % (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
    for o in objs:
        print('  %-14s тр. %6d  центр (%.2f; %.2f; %.2f)' % (o.name, tris(o), *o.matrix_world.translation))
    finish_model(ID, EXP, objs, CLS, extra=dict(tex=dict(A='T_ProbeWreck', M='T_ProbeWreckMain'), bbox=[lo, hi], water=WATER, waterlines=WATERLINES, decals=DECALS, solar=SOLAR))
