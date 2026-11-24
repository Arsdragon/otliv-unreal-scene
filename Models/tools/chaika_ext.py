# chaika_ext.py — этап B: детальная внешняя модель «Чайки» с развёртками под два атласа текстур.
# Запуск: bash tools/bl.sh tools/chaika_ext.py  ->  src/chaika_ext.blend, export/chaika_ext/layout.json, faces_A/B.npz
# Дальше: python tools/chaika_tex.py (текстуры) -> bash tools/bl.sh src/chaika_ext.blend tools/chaika_final.py (материалы, экспорт)
import bpy, bmesh, math, os, sys, json
from mathutils import Vector, Matrix, Euler

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
for _f in ('kit.py', 'chaika_shape.py', 'uvkit.py'):
    exec(open(os.path.join(TOOLS, _f), encoding='utf-8').read())
EXP = os.path.join(ROOT, 'export', 'chaika_ext')
os.makedirs(EXP, exist_ok=True)
R = math.radians

# Материалы на этапе сборки = классы поверхности для художника текстур (имя -> номер класса, цвет для проверки).
CLS = {'tile_white': 1, 'tile_belly': 2, 'frame': 3, 'tunnel': 4, 'rcc': 5, 'tile_gray': 6, 'm_white': 10, 'm_dark': 11, 'm_alu': 12,
       'm_steel': 13, 'm_chrome': 14, 'm_rubber': 15, 'm_orange': 16, 'm_nozzle': 17, 'm_tread': 18,
       'glass': 30, 'emissive': 31}
_PV = {'tile_gray': (0.62, 0.62, 0.61), 'tile_white': (0.80, 0.80, 0.78), 'tile_belly': (0.06, 0.06, 0.065), 'frame': (0.16, 0.17, 0.18),
       'tunnel': (0.55, 0.57, 0.56), 'rcc': (0.17, 0.175, 0.18), 'm_white': (0.78, 0.78, 0.76), 'm_dark': (0.09, 0.095, 0.10),
       'm_alu': (0.70, 0.71, 0.72), 'm_steel': (0.30, 0.30, 0.31), 'm_chrome': (0.9, 0.9, 0.9), 'm_rubber': (0.03, 0.03, 0.03),
       'm_orange': (0.85, 0.33, 0.05), 'm_nozzle': (0.36, 0.32, 0.29), 'm_tread': (0.2, 0.2, 0.21)}
for _n, _c in _PV.items():
    defmat(_n, (*_c, 1), metallic=1.0 if _n in ('m_alu', 'm_steel', 'm_chrome', 'm_nozzle') else 0.0, rough=0.5)
defmat('glass', (0.55, 0.75, 0.85, 0.25), rough=0.03, kind='glass')
defmat('emissive', (1.0, 0.93, 0.75, 1), rough=0.3, emis=4.0)
use_coll('chaika_ext')


# ====================================================================== развёртка корпуса
_hc = {}


def _sect(y):
    yq = round(min(max(y, -6.95), TAIL_Y), 3)
    v = _hc.get(yq)
    if v is None:
        hp = _half(sec(yq))
        L = [0.0]
        for a, b in zip(hp[:-1], hp[1:]):
            L.append(L[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        v = _hc[yq] = (hp, L)
    return v


def hull_t(y, x, z):
    """Расстояние по обводу сечения от конька крыши до точки (x, z) на станции y."""
    hp, L = _sect(y)
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


SMAX = max(_sect(y)[1][-1] for y in frange(-6.95, TAIL_Y, 0.05)) + 0.03
HULL_W = TAIL_Y - NOSE_Y


def hull_uv(p, sgn):
    """Точка обшивки -> развёртка корпуса в метрах: u — от носа к хвосту, v — по обводу (конёк крыши посередине,
    правый борт ниже по карте, левый — выше)."""
    return (p[1] - NOSE_Y, SMAX + sgn * hull_t(p[1], p[0], p[2]))


def side_pt(y, z, sgn):
    return hull_uv((halfwidth(y, z), y, z), sgn)


def set_hull_uv(bm):
    L = uvl(bm)
    cache = {}
    for f in bm.faces:
        sgn = 1 if f.calc_center_median().x >= 0 else -1
        for lp in f.loops:
            k = (lp.vert.index, sgn)
            if k not in cache:
                cache[k] = hull_uv(lp.vert.co, sgn)
            lp[L].uv = cache[k]


def quad3(y0, y1, z0, z1, sgn):
    """Прямоугольник на борту (y0…y1, z0…z1) -> три точки развёртки: левый нижний угол, правый нижний, левый
    верхний — как это видит наблюдатель снаружи (на правом борту нос слева, на левом — справа)."""
    if sgn > 0:
        return [side_pt(y0, z0, 1), side_pt(y1, z0, 1), side_pt(y0, z1, 1)]
    return [side_pt(y1, z0, -1), side_pt(y0, z0, -1), side_pt(y1, z1, -1)]


def hull_decals():
    d = []
    for sgn in (1, -1):
        d.append(dict(type='text', text='ЧАЙКА', q=quad3(-2.55, -0.70, 2.52, 2.95, sgn), color='ink', align='l'))
        d.append(dict(type='text', text='ПОСАДОЧНЫЙ МОДУЛЬ ПМ-2', q=quad3(-2.55, -0.70, 2.37, 2.46, sgn), color='ink', align='l'))
        d.append(dict(type='text', text='07', q=quad3(0.75, 1.75, 2.15, 2.85, sgn), color='ink', align='c'))
        d.append(dict(type='text', text='07', q=quad3(4.75, 5.35, 3.27, 3.47, sgn), color='ink', align='c'))
        d.append(dict(type='text', text='АВАРИЙНОЕ ВСКРЫТИЕ', q=quad3(-4.40, -3.72, 2.06, 2.13, sgn), color='orange', align='c'))
        d.append(dict(type='panel', q=quad3(-4.42, -3.70, 2.03, 2.25, sgn), style='rescue'))
        for (ya, yb, za, zb, lab) in ((-3.62, -3.16, 1.86, 2.26, 'БОРТОВАЯ ЭЛЕКТРОНИКА'), (-1.95, -1.25, 1.88, 2.28, 'ЗАПРАВКА  ОКИСЛИТЕЛЬ'),
                                      (-0.95, -0.35, 1.84, 2.24, 'ГИДРОСИСТЕМА'), (1.15, 1.85, 2.95, 3.25, 'АЗОТ  ПРОДУВКА'),
                                      (-3.85, -3.35, 2.62, 2.97, 'ЛЮК ОБСЛУЖИВАНИЯ'), (2.55, 3.05, 2.75, 3.10, 'ЭЛЕКТРОПИТАНИЕ')):
            d.append(dict(type='panel', q=quad3(ya, yb, za, zb, sgn), style='hatch', label=lab))
        for (yc, zc, r) in ((-0.30, 2.72, 0.07), (0.30, 2.50, 0.05), (2.10, 2.62, 0.06), (0.25, 2.05, 0.045)):
            d.append(dict(type='port', q=quad3(yc - r, yc + r, zc - r, zc + r, sgn)))
        d.append(dict(type='text', text='НЕ ВСТАВАТЬ ПОД СОПЛО', q=quad3(2.2, 3.0, 2.50, 2.57, sgn), color='orange', align='c'))
    d.append(dict(type='band', u=[-4.30 - NOSE_Y, -4.12 - NOSE_Y], color='orange'))
    d.append(dict(type='band', u=[5.70 - NOSE_Y, 5.82 - NOSE_Y], color='orange'))
    return d


# ====================================================================== корпус и фонарь
def cut_tunnel(bm, part):
    def low(f):
        c = f.calc_center_median()
        return f.normal.z < -0.05 and HATCH_Y - 0.4 < c.y < TUN_Y1 + 0.4 and abs(c.x) < TUN_X + 0.4
    bm.normal_update()
    for sgn in (1, -1):
        cut(bm, (sgn * TUN_X, 0, 0), (1, 0, 0), low)
        bm.normal_update()
    for y in (HATCH_Y, TUN_Y1):
        cut(bm, (0, y, 0), (0, 1, 0), low)
        bm.normal_update()
    dele = [f for f in bm.faces if f.normal.z < -0.05 and HATCH_Y < f.calc_center_median().y < TUN_Y1
            and abs(f.calc_center_median().x) < TUN_X]
    bmesh.ops.delete(bm, geom=dele, context='FACES')
    ret = bmesh.ops.extrude_edge_only(bm, edges=[e for e in bm.edges if e.is_boundary])
    for g in ret['geom']:
        if isinstance(g, bmesh.types.BMVert):
            g.co.z = TUN_ZTOP
        elif isinstance(g, bmesh.types.BMFace):
            g[part] = 1
    r2 = bmesh.ops.edgeloop_fill(bm, edges=[g for g in ret['geom'] if isinstance(g, bmesh.types.BMEdge)])
    for f in r2['faces']:
        f[part] = 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])


def build_hull():
    bm = bmesh.new()
    part = bm.faces.layers.int.new('part')
    vr, _ = skin(bm, [ring(y) for y in hull_stations()], closed=True)
    tip = bm.verts.new((0, NOSE_Y, NOSE_Z))
    for i in range(NTH):
        bm.faces.new((tip, vr[0][(i + 1) % NTH], vr[0][i]))
    bm.faces.new(vr[-1])[part] = 2
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    cut_tunnel(bm, part)
    canopy_cuts(bm)
    panes = canopy_mark(bm)
    for f in bm.faces:
        f.smooth = True
    out = []
    bg = extract(bm, [f for f in bm.faces if f.material_index == GLASS])
    for f in bg.faces:
        f.material_index = 0
    out.append(bm_obj(bg, 'ext_canopy_glass', 'glass', 30))
    bf = extract(bm, [f for f in bm.faces if f.material_index == FRAME])
    for f in bf.faces:
        f.material_index = 0
    frame_solid(bf, proud=0.014, depth=0.05)
    bf.verts.index_update()
    set_hull_uv(bf)
    fr = bm_obj(bf, 'ext_canopy_frame', 'frame', 35)
    fr['chart_of'] = 'ext_hull'
    out.append(fr)
    bt = extract(bm, [f for f in bm.faces if f[part] == 1])
    out.append(bm_obj(bt, 'ext_tunnel', 'tunnel', 35))
    bb = extract(bm, [f for f in bm.faces if f[part] == 2])
    out.append(bm_obj(bb, 'ext_tail_base', 'm_dark', None))
    bm.normal_update()
    for f in bm.faces:
        c = f.calc_center_median()
        yy = min(max(c.y, -6.95), TAIL_Y)
        if c.y < Y_CAP - RIM:
            f.material_index = 2
        elif _sect(c.y)[1][-1] - hull_t(c.y, c.x, c.z) < _sect(c.y)[1][SEG_K + SEG_B + SEG_C // 2] - 1e-4:
            f.material_index = 1                      # днище — до середины скругления скулы (ровно по ряду сетки)
        else:
            f.material_index = 0
    bm.verts.index_update()
    set_hull_uv(bm)
    hull = bm_obj(bm, 'ext_hull', ['tile_white', 'tile_belly', 'rcc'], 30)
    zu = frange(0.05, HULL_W, 0.05)                    # линии плеча и скулы вдоль корпуса — для рядов плитки
    zs_ = [_sect(NOSE_Y + u)[1] for u in zu]
    zones = dict(u=[round(u, 3) for u in zu], tk=[round(L[-1], 4) for L in zs_],
                 tc=[round(L[-1] - L[SEG_K + SEG_B + SEG_C // 2], 4) for L in zs_],
                 ts=[round(L[-1] - L[SEG_K + SEG_B + SEG_C + SEG_S + SEG_SH // 2], 4) for L in zs_])
    set_chart(hull, 'hull', HULL_W, 2 * SMAX, 'A', tiles=True, smax=SMAX, zones=zones, decals=hull_decals())
    out.append(hull)
    smart_uv(out[2], 'C', dens=0.7)
    smart_uv(out[3], 'B', dens=0.6)
    return out


# ====================================================================== крыло, кили
def _foil(rings, n, name, mats, mat_fn, transpose=False):
    """Обшивка крыла/киля: развёртка с носком профиля посередине карты (верх — к началу v, низ — к концу)."""
    cents = [sum((Vector(p) for p in r), Vector()) / len(r) for r in rings]
    u = [0.0]
    for a, b in zip(cents[:-1], cents[1:]):
        u.append(u[-1] + (b - a).length)
    vv = []
    for r in rings:
        Lc = ring_len(r, True)
        vv.append([Lc[n] - l for l in Lc])
    HM = max(abs(v) for row in vv for v in row) + 0.03
    if transpose:
        uvr = [[(HM - v, u[i]) for v in vv[i]] for i in range(len(rings))]
    else:
        uvr = [[(u[i], HM - v) for v in vv[i]] for i in range(len(rings))]
    bm = bmesh.new()
    vr, _ = skin_uv(bm, rings, uvr, True, mat_fn)
    L = uvl(bm)
    f = bm.faces.new(vr[-1])                         # торец законцовки
    f.material_index = len(mats) - 1
    for lp in f.loops:
        lp[L].uv = uvr[-1][n]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = bm_obj(bm, name, mats, 30)
    return ob, (u[-1], 2 * HM), u


def _span_table():
    xs = frange(0.9, 4.1, 0.01)
    ss = [0.0]
    for a, b in zip(xs[:-1], xs[1:]):
        ss.append(ss[-1] + math.hypot(b - a, wing_z(b) - wing_z(a)))
    return xs, ss


_SX, _SS = _span_table()


def span_s(x):
    """Длина по размаху вдоль средней линии крыла (вид спереди, с изломом «чайки») от x = 0,9 м."""
    i = max(0, min(len(_SX) - 2, int((x - _SX[0]) / (_SX[1] - _SX[0]))))
    f = (x - _SX[i]) / (_SX[i + 1] - _SX[i])
    return _SS[i] + (_SS[i + 1] - _SS[i]) * f


def build_wing():
    """Крыло: развёртка в плане — u вдоль оси корабля (как у днища), v по размаху вдоль излома; верх и низ — два острова.
    Плитка ложится прямоугольной сеткой вдоль корпуса (у прежней развёртки по стреловидной кромке она шла ромбами)."""
    n = 18
    rings = [wing_root_ring(n)] + [wing_section(x, n) for x in WING_XS]
    mf = lambda i, j: 2 if n - 3 <= j < n + 3 else (0 if j < n else 1)
    ob, _, _ = _foil(rings, n, 'ext_wing_R', ['tile_white', 'tile_belly', 'rcc'], mf)   # низ — графитовая плитка, кромка тёмная
    me = ob.data
    ys = [v.co.y for v in me.vertices]
    Y0 = min(ys) - 0.03
    W = max(ys) - Y0 + 0.03
    S = span_s(WING_TIP_X + 0.02) + 0.03
    GAP = 0.12
    uvd = me.uv_layers.active.data
    for p in me.polygons:
        lower = (p.normal.z < 0) if p.material_index == 2 else (p.material_index == 1)
        off = S + GAP if lower else 0.0
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uvd[li].uv = (co.y - Y0, off + span_s(co.x))
    dec = []                                           # щели закрылков и элеронов — по 73 % хорды, сверху и снизу
    for off in (0.0, S + GAP):
        for x0, x1 in ((1.62, 2.22), (2.68, 3.86)):
            hp = [(_w_le(x) + 0.73 * (_w_te(x) - _w_le(x)) - Y0, off + span_s(x)) for x in (x0 + (x1 - x0) * k / 8 for k in range(9))]
            dec += [dict(type='line', q=[a, b], w=0.006, color='groove') for a, b in zip(hp[:-1], hp[1:])]
            for x, q in ((x0, hp[0]), (x1, hp[-1])):
                dec.append(dict(type='line', q=[q, (_w_te(x) - Y0 + 0.02, off + span_s(x))], w=0.006, color='groove'))
    set_chart(ob, 'skin', W, 2 * S + GAP, 'B', tiles=True, vbands=[[S - 0.45, S - 0.03, 'orange']], decals=dec)
    return ob


def build_fin():
    n = 12
    nx, nz = FIN_TIP['x'] - FIN_ROOT['x'], FIN_TIP['z'] - FIN_ROOT['z']
    Lf = math.hypot(nx, nz)
    px, pz = -nz / Lf, nx / Lf
    rings = []
    for t in (-0.30, 0.0, 0.25, 0.5, 0.75, 1.0):
        d = {k: FIN_ROOT[k] + (FIN_TIP[k] - FIN_ROOT[k]) * t for k in FIN_ROOT}
        rings.append([(d['x'] + px * tt * d['chord'], d['y_le'] + s * d['chord'], d['z'] + pz * tt * d['chord'])
                      for s, tt in airfoil(n, d['th'] / d['chord'], 0.0)])
    mf = lambda i, j: 1 if n - 2 <= j < n + 2 else 0
    ob, (w, h), u = _foil(rings, n, 'ext_fin_R', ['tile_white', 'rcc'], mf, transpose=True)
    set_chart(ob, 'skin', h, w, 'A', tiles=True, vbands=[[w - 0.30, w, 'orange']])
    return ob


# ====================================================================== мотогондола и кормовой двигатель
NAC_PROF = [(1e-4, -0.42), (0.285, -0.42), (0.295, -0.80), (0.32, -0.94), (0.342, -0.975), (0.365, -0.985), (0.39, -0.97),
            (0.41, -0.93), (0.43, -0.75), (0.44, -0.45), (0.44, 0.10), (0.425, 0.55), (0.39, 0.90), (0.345, 1.10),
            (0.315, 1.20), (1e-4, 1.20)]


def build_nacelle_shell():
    """Обечайка мотогондолы в полётном положении (ось вдоль Y, заборник к носу), опорная точка — ось поворота."""
    bm = bmesh.new()
    seg_cls = [4, 2, 2, 1, 1, 1, 1, 0, 0, 0, 0, 0, 3, 3, 2]
    revolve_uv(bm, NAC_PROF, 48, 0.44, 'Y', mat_fn=lambda i, j: seg_cls[i])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = bm_obj(bm, 'ext_nacelle_R', ['m_white', 'm_alu', 'm_dark', 'm_nozzle', 'm_steel'], 30)
    _, u = revolve_rings(NAC_PROF, 4)
    set_chart(ob, 'skin', u[-1], 2 * math.pi * 0.44, 'B', panels=[0.62, 0.69], u_soot=[u[12], u[-1]])
    return ob


def build_pod():
    ys = frange(1.30, 6.35, 0.2525)
    rings = []
    for y in ys:
        r, xc, zc = POD_R(y), POD_X(y), POD_Z(y)
        rings.append([(xc + r * math.cos(2 * math.pi * i / 32 + math.pi / 2), y, zc + r * math.sin(2 * math.pi * i / 32 + math.pi / 2))
                      for i in range(32)])
    rref = 0.46
    uvr = [[(y - ys[0], 2 * math.pi * rref * j / 32) for j in range(33)] for y in ys]
    nlast = len(ys) - 1
    # j = 0 — верх обтекателя; низ (j около 16) — графитовая плитка, корма — тёмный теплозащитный пояс
    mf = lambda i, j: 2 if i >= nlast - 1 else (1 if 11 <= j < 21 else 0)
    bm = bmesh.new()
    vr, _ = skin_uv(bm, rings, uvr, True, mf)
    L = uvl(bm)
    for ringv, uvrow in ((vr[0], uvr[0]), (vr[-1], uvr[-1])):
        f = bm.faces.new(ringv)
        f.material_index = 2
        for lp in f.loops:
            lp[L].uv = uvrow[0]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = bm_obj(bm, 'ext_pod_R', ['tile_white', 'tile_belly', 'rcc'], 30)
    set_chart(ob, 'skin', ys[-1] - ys[0], 2 * math.pi * rref, 'A', tiles=True)
    return ob


# ====================================================================== сборка
exec(open(os.path.join(TOOLS, 'chaika_ext_parts.py'), encoding='utf-8').read())


def twin(ob, name):
    """Зеркальная копия неподвижной части (та же развёртка, тот же участок атласа)."""
    m = mirror_x(ob, name)
    m['chart_of'] = ob.get('chart_of') or ob.name
    shade(m, 32)
    return m


def twin_local(ob, name, parent=None):
    """Зеркальная копия подвижной части: зеркалится сетка в осях объекта, опорная точка переносится на другой борт."""
    me = ob.data.copy()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.scale(bm, vec=Vector((-1, 1, 1)), verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    m = bpy.data.objects.new(name, me)
    link(m)
    m['chart_of'] = ob.get('chart_of') or ob.name
    bpy.context.view_layer.update()
    if parent is not None:
        m.parent = parent
        m.location, m.rotation_euler = (-ob.location.x, ob.location.y, ob.location.z), ob.rotation_euler
    else:
        m.location, m.rotation_euler = (-ob.location.x, ob.location.y, ob.location.z), ob.rotation_euler
    shade(m, 32)
    return m


def build_all():
    clear_scene()
    use_coll('chaika_ext')
    objs = build_hull()
    w = build_wing()
    objs += [w, twin(w, 'ext_wing_L')]
    f = build_fin()
    objs += [f, twin(f, 'ext_fin_L')]
    p = build_pod()
    objs += [p, twin(p, 'ext_pod_L')]
    objs += build_static_parts(twin)
    objs += build_moving_parts(twin_local)
    root = empty('chaika_ext', (0, 0, 0), size=0.5)
    marks = build_markers()
    bpy.context.view_layer.update()
    for o in list(bpy.data.collections['chaika_ext'].objects):
        if o is not root and o.parent is None:
            set_parent(o, root)
    return [o for o in bpy.data.collections['chaika_ext'].objects if o.type == 'MESH']


if __name__ == '__main__':
    objs = build_all()
    sA = (ATLAS - 2 * PAD) / HULL_W
    rA, cA = pack_atlas(objs, 'A', fixed=('ext_hull', sA))
    rB, cB = pack_atlas(objs, 'B')
    rC, cC = pack_atlas(objs, 'C')
    apply_atlas(objs, {**rA, **rB, **rC})
    layout = {'A': layout_of(rA, cA), 'B': layout_of(rB, cB), 'C': layout_of(rC, cC)}
    json.dump(layout, open(os.path.join(EXP, 'layout.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    nA = dump_faces(objs, 'A', CLS, os.path.join(EXP, 'faces_A.npz'), cA)
    nB = dump_faces(objs, 'B', CLS, os.path.join(EXP, 'faces_B.npz'), cB) + dump_faces(objs, 'C', CLS, os.path.join(EXP, 'faces_C.npz'), cC)
    tr = sum(tris(o) for o in objs)
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    print('ГАБАРИТЫ: длина %.2f, размах %.2f, высота %.2f, низ %.2f' % (hi[1] - lo[1], hi[0] - lo[0], hi[2], lo[2]))
    print('ТРЕУГОЛЬНИКОВ %d, объектов %d; атлас A: %.0f пикс/м (корпус), прочее %.0f; атлас B: %.0f, C: %.0f пикс/м; граней A %d, B+C %d'
          % (tr, len(objs), sA, min(r[2] for n, r in rA.items() if n != 'ext_hull'), min(r[2] for r in rB.values()),
             min(r[2] for r in rC.values()), nA, nB))
    json.dump(dict(tris=tr, objects=len(objs), lo=lo, hi=hi), open(os.path.join(EXP, 'build_stats.json'), 'w'))
    # Имена бортов: при носе по −Y ось +X — левый борт. Внутри сборки правая (по +X) половина называлась *_R;
    # здесь суффиксы меняются местами, чтобы в файле и в экспорте *_L было слева от пилота, *_R — справа.
    allo = list(bpy.data.collections['chaika_ext'].all_objects)
    new = {o.name: (o.name[:-2] + ('_L' if o.name.endswith('_R') else '_R')) for o in allo if o.name[-2:] in ('_R', '_L')}
    for o in allo:
        if o.get('chart_of') in new:
            o['chart_of'] = new[o['chart_of']]
    for o in allo:
        if o.name in new:
            o['_new'] = new[o.name]
            o.name = '__' + o.name
    for o in allo:
        if o.get('_new'):
            o.name = o['_new']
            del o['_new']
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'src', 'chaika_ext.blend'))
    print('SAVED chaika_ext.blend')
