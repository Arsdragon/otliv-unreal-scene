# pilot_gloves.py — этап E2: перчатки пилота в статичных позах, в системе координат chaika_cockpit:
#   glove_R — правая, держит ручку управления (ck_stick): указательный на гашетке, большой лежит на головке у «шляпки»;
#   glove_L — левая, лежит сверху на РУДе (ck_throttle): пальцы обхватывают перекладину, большой — на кнопке в торце.
# У каждой — манжета: раструб перчатки, металлическое кольцо разъёма, гофра и рукав скафандра до локтя (обрезан).
# Кисть строится в осях хвата G (ось Z — вдоль рукояти, ладонь со стороны −X, пальцы уходят через −Y к +X, запястье
# к +Y) как ПРАВАЯ; левая получается зеркальной матрицей. Опорные точки перчаток совпадают с осями качания ручки и РУДа.
# Запуск: bash tools/bg.sh "fresh(); run('pilot_gloves.py')"  ->  src/pilot_gloves.blend, export/pilot_gloves/{layout.json, tris_A.npz}
import bpy, bmesh, math, os, sys, json
from mathutils import Vector, Matrix

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
for _f in ('kit.py', 'uvkit.py', 'partkit.py', 'dkit.py'):
    exec(open(os.path.join(TOOLS, _f), encoding='utf-8').read())
ID = 'pilot_gloves'
EXP = os.path.join(ROOT, 'export', ID)
os.makedirs(EXP, exist_ok=True)
R = math.radians

CLS = {'g_fabric': 1, 'g_palm': 2, 'g_tip': 3, 'g_pad': 4, 'g_ring': 5, 'g_lock': 6, 'g_bellows': 7, 'g_cuff': 8, 'g_strap': 9,
       'g_dark': 10, 'g_orange': 11}
_PV = {'g_fabric': (0.78, 0.78, 0.76), 'g_palm': (0.115, 0.12, 0.125), 'g_tip': (0.085, 0.087, 0.09), 'g_pad': (0.19, 0.20, 0.21),
       'g_ring': (0.66, 0.68, 0.70), 'g_lock': (0.30, 0.31, 0.33), 'g_bellows': (0.075, 0.077, 0.08), 'g_cuff': (0.80, 0.79, 0.76),
       'g_strap': (0.20, 0.21, 0.23), 'g_dark': (0.02, 0.02, 0.02), 'g_orange': (0.78, 0.33, 0.08)}
for _n, _c in _PV.items():
    defmat(_n, (*_c, 1), metallic=1.0 if _n in ('g_ring', 'g_lock') else 0.0, rough=0.6)
GAP = 0.001                                   # зазор между перчаткой и рукоятью
FMAT = ['g_fabric', 'g_palm', 'g_tip']
JOINTS = []                                   # суставы пальцев (для гофры в текстуре): деталь, центр, ось пальца, радиус


def sstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def sweep(name, P, sec, mats, matfn=None, n=14, expo=2.0, inw=None, caps=(True, True), smooth=50.0):
    """Труба вдоль точек P. sec[i] = (полутолщина к рукояти, полуширина). inw[i] — направление «к рукояти» (по умолчанию —
    к оси Z хвата). matfn(i, psi) -> номер материала грани; psi в градусах: 0 — наружу (тыл кисти), 180 — к рукояти."""
    P = [Vector(p) for p in P]
    m = len(P)
    bm = bmesh.new()
    rings, last = [], Vector((1, 0, 0))
    for i in range(m):
        t = (P[min(i + 1, m - 1)] - P[max(i - 1, 0)]).normalized()
        v = Vector(inw[i]) if inw is not None else Vector((-P[i].x, -P[i].y, 0))
        v = v - t * v.dot(t)
        v = v.normalized() if v.length > 1e-6 else last
        last = v
        bn = t.cross(v).normalized()
        th, wd = sec[i]
        ring = []
        for k in range(n):
            c, s = math.cos(2 * math.pi * k / n), math.sin(2 * math.pi * k / n)
            ex, ey = math.copysign(abs(c) ** (2 / expo), c), math.copysign(abs(s) ** (2 / expo), s)
            ring.append(bm.verts.new(P[i] - v * (th * ex) + bn * (wd * ey)))
        rings.append(ring)
    for i in range(m - 1):
        for k in range(n):
            f = bm.faces.new((rings[i][k], rings[i][(k + 1) % n], rings[i + 1][(k + 1) % n], rings[i + 1][k]))
            f.material_index = matfn(i, (k + 0.5) / n * 360.0) if matfn else 0
            f.smooth = True
    if caps[0]:
        bm.faces.new(rings[0][::-1]).material_index = matfn(0, 0.0) if matfn else 0
    if caps[1]:
        bm.faces.new(rings[-1]).material_index = matfn(m - 2, 0.0) if matfn else 0
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    return bm_obj(bm, name, mats, smooth, recalc=True)


def round_tip(P, sec, r, steps=4):
    """Скруглить конец трубы: ещё несколько сужающихся сечений вдоль последней касательной."""
    t = (Vector(P[-1]) - Vector(P[-2])).normalized()
    p0, (th, wd) = Vector(P[-1]), sec[-1]
    for j in range(1, steps + 1):
        a = R(86.0 * j / steps)
        P.append(p0 + t * (r * math.sin(a)))
        sec.append((th * math.cos(a), wd * math.cos(a)))


def finger(tag, a, b, phi_k, z, L, r0, r1, bump=None):
    """Палец: дуга вокруг рукояти (полуоси a, b) от пястного сустава на угле phi_k. L = (L1, L2, L3) — фаланги."""
    Lt = sum(L)
    rad = lambda s: (r0 + (r1 - r0) * min(1.0, max(0.0, s / Lt))) * (1 + 0.08 * math.exp(-(s / 0.006) ** 2)
                                                                    + 0.07 * math.exp(-((s - L[0]) / 0.005) ** 2)
                                                                    + 0.05 * math.exp(-((s - L[0] - L[1]) / 0.0045) ** 2))
    phi, s = R(phi_k - 11.0), None
    P, sec, ss, ph = [], [], [], []
    pt = lambda f, sv: Vector(((a + rad(sv) + GAP + (bump(math.degrees(f)) if bump else 0)) * math.cos(f),
                               (b + rad(sv) + GAP + (bump(math.degrees(f)) if bump else 0)) * math.sin(f), z))
    s = -(R(11.0) * (max(a, b) + r0))
    p = pt(phi, s)
    while True:
        P.append(p)
        sec.append((rad(s), rad(s) * 1.03))
        ss.append(s)
        ph.append(phi)
        if s >= Lt - r1 * 0.9:
            break
        phi += 0.0035 / math.hypot((a + r0) * math.sin(phi), (b + r0) * math.cos(phi))
        q = pt(phi, s)
        s += (q - p).length
        p = q
    nb = len(P)
    round_tip(P, sec, r1 * 0.95)
    ss += [Lt] * (len(P) - nb)

    def mf(i, psi):
        if ss[i] > Lt - 0.015:
            return 2
        if abs(psi - 180.0) < 78.0:
            return 2 if ss[i] > L[0] + L[1] + 0.003 else 1
        return 0

    for sj in (L[0], L[0] + L[1]):
        k = min(range(nb), key=lambda i: abs(ss[i] - sj))
        JOINTS.append(dict(c=list(P[k]), t=list((P[k + 1] - P[k - 1]).normalized()), r=rad(sj)))
    return sweep('fin_' + tag, P, sec, FMAT, mf, n=14)


def bezier(p0, p1, p2, p3, n):
    out = []
    for i in range(n + 1):
        t = i / n
        out.append(Vector(p0) * (1 - t) ** 3 + Vector(p1) * 3 * t * (1 - t) ** 2 + Vector(p2) * 3 * t * t * (1 - t) + Vector(p3) * t ** 3)
    return out


def thumb(ctrl, end_in=(0, 0, -1), r0=0.0138, r1=0.0116):
    P = bezier(*ctrl, 18)
    n0 = len(P)
    sec, inw = [], []
    for i, p in enumerate(P):
        u = i / (n0 - 1)
        r = (r0 + (r1 - r0) * u) * (1 + 0.05 * math.exp(-((u - 0.52) / 0.07) ** 2))
        sec.append((r, r * 1.06))
        w = sstep(0.50, 0.92, u)
        v = Vector((-p.x, -p.y, 0))
        v = v.normalized() if v.length > 1e-6 else Vector((1, 0, 0))
        inw.append((v * (1 - w) + Vector(end_in).normalized() * w).normalized())
    round_tip(P, sec, r1 * 0.95)
    inw += [inw[-1]] * (len(P) - n0)
    us = [min(1.0, i / (n0 - 1)) for i in range(len(P))]

    def mf(i, psi):
        if us[i] > 0.86:
            return 2
        if abs(psi - 180.0) < 78.0:
            return 2 if us[i] > 0.60 else 1
        return 0

    k = int(0.52 * (n0 - 1))
    JOINTS.append(dict(c=list(P[k]), t=list((P[k + 1] - P[k - 1]).normalized()), r=sec[k][0]))
    return sweep('thumb', P, sec, FMAT, mf, n=14, inw=inw)


def blob(name, c, rad, mats=('g_fabric', 'g_palm')):
    """Возвышение у основания большого пальца: сплюснутый шар; сторона, обращённая к рукояти, — резина ладони."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=18, v_segments=12, radius=1.0)
    c = Vector(c)
    ax = Vector((-c.x, -c.y, 0)).normalized()
    for v in bm.verts:
        v.co = Vector((v.co.x * rad[0], v.co.y * rad[1], v.co.z * rad[2])) + c
    for f in bm.faces:
        f.smooth = True
        f.material_index = 1 if (f.calc_center_median() - c).normalized().dot(ax) > 0.15 else 0
    return bm_obj(bm, name, list(mats), 50.0, recalc=True)


def hand(cfg, F):
    """Кисть и манжета в осях хвата G. F — направление от запястья к локтю (в осях G)."""
    a, b, zs = cfg['a'], cfg['b'], cfg['zs']
    parts = []
    dims = (((0.047, 0.027, 0.024), 0.0122, 0.0105), ((0.051, 0.031, 0.025), 0.0125, 0.0108),
            ((0.047, 0.029, 0.024), 0.0118, 0.0102), ((0.037, 0.021, 0.022), 0.0108, 0.0095))
    for i, (tag, (L, r0, r1)) in enumerate(zip(('index', 'middle', 'ring', 'pinky'), dims)):
        parts.append(finger(tag, a, b, cfg['phi_k'], zs[i], L, r0, r1, cfg.get('bump') if i == 0 else None))
    # ---- ладонь: от костяшек вокруг рукояти до касания на 180°, дальше прямо к запястью, раструб перчатки по оси рукава
    zc, wk = (zs[0] + zs[3]) / 2, (zs[0] - zs[3]) / 2 + 0.0125
    P, sec, inw = [], [], []
    for ph, th, kw in ((cfg['phi_k'] + 9, 0.0085, 0.96), (cfg['phi_k'], 0.0145, 1.0), ((cfg['phi_k'] + 180) / 2 + 4, 0.0160, 1.0), (180.0, 0.0172, 0.98)):
        P.append(Vector(((a + th + GAP) * math.cos(R(ph)), (b + th + GAP) * math.sin(R(ph)), zc)))
        sec.append((th, wk * kw))
        inw.append((-math.cos(R(ph)), -math.sin(R(ph)), 0))
    x0 = -(a + 0.0172 + GAP)
    for y, th, wd, dz in ((0.024, 0.0185, wk * 0.95, 0.001), (0.048, 0.0200, wk * 0.86, 0.002), (0.070, 0.0215, wk * 0.74, 0.004)):
        P.append(Vector((x0 - 0.0006 * y / 0.07, y, zc + dz)))
        sec.append((th, wd))
        inw.append((1, 0, 0))
    F = Vector(F).normalized()
    w0 = P[-1]
    w1 = w0 + (Vector((0, 1, 0)) + F).normalized() * 0.020
    w2 = w1 + F * 0.022
    P += [w1, w2]
    sec += [(0.0300, 0.0345), (0.0395, 0.0405)]
    inw += [(1, 0, 0), (1, 0, 0)]
    parts.append(sweep('palm', P, sec, ['g_fabric', 'g_palm'], lambda i, psi: 1 if (abs(psi - 180.0) < 82.0 and i < 6) else 0,
                       n=28, expo=3.0, inw=inw))
    parts.append(blob('thenar', cfg['thenar'], cfg['thenar_r']))
    parts.append(thumb(cfg['thumb'], cfg.get('thumb_in', (0, 0, -1))))
    # ---- ремешок-стяжка на тыле кисти
    sx = x0 - 0.0198 - 0.0004
    parts.append(box('strap', (0.0032, 0.019, 2 * wk * 0.80), (sx, 0.040, zc + 0.002), bevel=0.0012, mat_name='g_strap'))
    parts.append(box('buckle', (0.0040, 0.015, 0.011), (sx - 0.0010, 0.040, zc + 0.012), bevel=0.0012, mat_name='g_lock'))
    # ---- манжета: кольцо разъёма, гофра, рукав. Оси A: Z — вдоль рукава от запястья, X — к ладонной стороне
    XA = (Vector((1, 0, 0)) - F * F.x).normalized()
    A = Matrix((XA, F.cross(XA), F)).transposed().to_4x4()
    A.translation = w2
    arm = [revolve('ring', [(0.0400, 0.000), (0.0462, 0.000), (0.0478, 0.0025), (0.0478, 0.0175), (0.0462, 0.020), (0.0400, 0.020)],
                   40, 'Z', (0, 0, 0), 'g_ring', closed=True, cap=False),
           revolve('ringline', [(0.0478, 0.0085), (0.0484, 0.0090), (0.0484, 0.0110), (0.0478, 0.0115)], 40, 'Z', (0, 0, 0), 'g_lock', closed=True, cap=False),
           box('latch', (0.012, 0.024, 0.015), (-0.0500, 0.0, 0.010), bevel=0.003, mat_name='g_lock'),
           box('mark', (0.003, 0.009, 0.0204), (0.0, 0.0473, 0.010), bevel=0.0008, mat_name='g_orange'),
           revolve('bellows', [(0.0405, 0.019), (0.0455, 0.0240), (0.0412, 0.0290), (0.0462, 0.0340), (0.0418, 0.0390), (0.0468, 0.0440),
                               (0.0440, 0.0490), (0.0400, 0.0490)], 40, 'Z', (0, 0, 0), 'g_bellows', closed=True, cap=False)]
    LS = cfg.get('sleeve', 0.235)
    rs = lambda h: 0.0445 + 0.0085 * sstep(0.049, 0.16, h)
    rings = []
    for k in range(18):
        h = 0.0470 + (LS - 0.0470) * k / 17
        wv = sstep(0.055, 0.10, h)
        rings.append([((rs(h) + wv * (0.0020 * math.sin(3 * t + 46 * h) + 0.0012 * math.sin(5 * t - 81 * h + 1.3))) * math.cos(t),
                       (rs(h) + wv * (0.0020 * math.sin(3 * t + 46 * h) + 0.0012 * math.sin(5 * t - 81 * h + 1.3))) * math.sin(t), h)
                      for t in (2 * math.pi * j / 36 for j in range(36))])
    arm.append(loft('sleeve', rings, closed=True, cap0=False, cap1=False, mat_name='g_cuff', smooth=50))
    arm.append(revolve('cuffband', [(rs(0.058) + 0.0008, 0.0560), (rs(0.058) + 0.0030, 0.0572), (rs(0.070) + 0.0030, 0.0708), (rs(0.070) + 0.0008, 0.0720)],
                       40, 'Z', (0, 0, 0), 'g_strap', closed=True, cap=False))
    arm.append(revolve('cuffmark', [(rs(0.080) + 0.0006, 0.0790), (rs(0.080) + 0.0022, 0.0796), (rs(0.085) + 0.0022, 0.0850), (rs(0.085) + 0.0006, 0.0856)],
                       40, 'Z', (0, 0, 0), 'g_orange', closed=True, cap=False))
    arm.append(revolve('inside', [(0.0, LS - 0.014), (rs(LS) - 0.003, LS - 0.014), (rs(LS) - 0.001, LS)], 36, 'Z', (0, 0, 0), 'g_dark', cap=False))
    parts += place(arm, A)
    return parts


def build_glove(name, MG, origin, cfg, F_world):
    j0 = len(JOINTS)
    M3 = MG.to_3x3()
    parts = hand(cfg, M3.transposed() @ Vector(F_world).normalized())
    for o in parts:
        o.data.transform(MG)
        if M3.determinant() < 0:
            o.data.flip_normals()
        o.data.update()
    ob = merge(parts, name, origin)
    shade(ob, 50)
    smart_uv(ob, 'A', angle=58.0, dens=1.0)
    for j in JOINTS[j0:]:
        j['obj'] = name
        j['c'] = list((MG @ Vector(j['c'])) - Vector(origin))
        j['t'] = list((M3 @ Vector(j['t'])).normalized())
    return ob


# ------------------------------------------------------------------ привязка к кабине (оси chaika_cockpit)
# ручка: верх правой консоли — начало (−0,555; −5,00; 2,3015), местные X — к −X мира, Y — к носу; ось рукояти наклонена вперёд
GR = Matrix(((1, 0, 0), (0, 0.9806, 0.1961), (0, -0.1961, 0.9806))).transposed().to_4x4()
GR.translation = Vector((-0.480, -5.2937, 2.4300))
STICK_PIVOT = (-0.480, -5.270, 2.3315)
CFG_R = dict(a=0.0225, b=0.0265, phi_k=222.0, zs=(0.0370, 0.0135, -0.0095, -0.0310),
             bump=lambda f: 0.0090 * math.exp(-((f - 270.0) / 24.0) ** 2),                    # указательный лежит на гашетке
             thenar=(-0.0240, 0.0360, 0.0200), thenar_r=(0.0160, 0.0260, 0.0210),
             thumb=((-0.0240, 0.0385, 0.0180), (-0.0180, 0.0480, 0.0500), (-0.0040, 0.0460, 0.0980), (0.0060, 0.0130, 0.0995)))
#            большой палец поднимается вдоль задней грани головки и ложится подушечкой на её верх у «шляпки»
FR_WORLD = (0.070, 0.965, -0.250)
# РУД: перекладина вдоль X мира, центр (0,480; −5,228; 2,4135), радиус 16 мм; зеркальные оси (левая рука):
# X хвата — вниз, Y — к корме, Z — к правому борту пилота (к кнопке в торце)
GL = Matrix(((0, 0, -1), (0, 1, 0), (-1, 0, 0))).transposed().to_4x4()
GL.translation = Vector((0.480, -5.2280, 2.4135))
THROTTLE_PIVOT = (0.480, -5.270, 2.2815)
CFG_L = dict(a=0.0160, b=0.0160, phi_k=225.0, zs=(0.0400, 0.0175, -0.0175, -0.0385),
             thenar=(-0.0140, 0.0300, 0.0240), thenar_r=(0.0150, 0.0240, 0.0200),
             thumb=((-0.0160, 0.0320, 0.0260), (-0.0060, 0.0420, 0.0500), (0.0050, 0.0320, 0.0680), (0.0030, 0.0050, 0.0640)))
FL_WORLD = (0.060, 0.975, -0.210)


def build_all():
    clear_scene()
    use_coll(ID)
    root = empty(ID, (0, 0, 0), size=0.1)
    gr = build_glove('glove_R', GR, STICK_PIVOT, CFG_R, FR_WORLD)
    gl = build_glove('glove_L', GL, THROTTLE_PIVOT, CFG_L, FL_WORLD)
    for o in (gr, gl):
        set_parent(o, root)
    return [gr, gl]


if __name__ == '__main__':
    objs = build_all()
    for o in objs:
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        print('  %-8s тр. %5d  x %.3f…%.3f  y %.3f…%.3f  z %.3f…%.3f' % (o.name, tris(o), min(p.x for p in pts), max(p.x for p in pts),
              min(p.y for p in pts), max(p.y for p in pts), min(p.z for p in pts), max(p.z for p in pts)))
    json.dump(dict(
        title='Перчатки пилота на ручке управления и РУДе (статичные позы, оси кабины)', tex='T_PilotGloves', main='pilot_gloves',
        specials={}, moving={},
        origin='оси и начало координат — как у chaika_cockpit (нос по −Y, +X — левый борт); опорная точка glove_R — ось качания ck_stick, glove_L — ось качания ck_throttle',
        export_pose='позы статичные: правая держит ручку в нейтрали, левая лежит на РУДе в положении, в котором он экспортирован в кабине',
        notes=['glove_R — правая рука на ручке (правая консоль, x = −0,48): указательный палец на гашетке, большой — на головке рядом со «шляпкой»',
               'glove_L — левая рука на РУДе (левая консоль, x = +0,48): пальцы обхватывают перекладину, рычаг проходит между средним и безымянным, большой палец на кнопке в торце',
               'у каждой перчатки — раструб, кольцо разъёма, гофра и рукав скафандра длиной около 24 см от запястья к локтю; дальше рукав обрезан (тела пилота нет)',
               'если ручка или РУД двигаются, перчатку вращать вместе с ними вокруг её опорной точки — она совпадает с осью детали',
               'один набор текстур 2048 (T_PilotGloves_*), слот pilot_gloves']),
        open(os.path.join(EXP, 'final_cfg.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    finish_model(ID, EXP, objs, CLS, extra=dict(tex=dict(A='T_PilotGloves'), joints=JOINTS))
