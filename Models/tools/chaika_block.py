# chaika_block.py — этап A: серая блок-модель «Чайки» (снаружи + кабина и шлюз), без текстур.
# Запуск: blender -b --factory-startup --python tools/chaika_block.py   ->  src/chaika_blockA.blend
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix, Euler

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
for _f in ('kit.py', 'chaika_shape.py'):
    exec(open(os.path.join(TOOLS, _f), encoding='utf-8').read())

defmat('clay', (0.60, 0.60, 0.60, 1), rough=0.62)
defmat('clay_frame', (0.34, 0.35, 0.37, 1), rough=0.55)
defmat('clay_dark', (0.20, 0.205, 0.215, 1), rough=0.5)
defmat('clay_belly', (0.21, 0.215, 0.225, 1), rough=0.55)
defmat('clay_mid', (0.42, 0.43, 0.45, 1), rough=0.6)
defmat('clay_in', (0.50, 0.50, 0.49, 1), rough=0.7)
defmat('clay_seat', (0.36, 0.37, 0.40, 1), rough=0.8)
defmat('glass', (0.86, 0.93, 0.96, 1), rough=0.02, kind='glass')
defmat('screen', (0.05, 0.13, 0.19, 1), rough=0.3, emis=0.7)
defmat('emissive', (0.85, 0.95, 0.35, 1), rough=0.4, emis=2.0)

R = math.radians


# ====================================================================== СНАРУЖИ
def cut_tunnel(bm):
    """Ниша трапа под хвостом: прямоугольный вырез в днище + стенки вверх до потолка ниши."""
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
    dele = []
    for f in bm.faces:
        c = f.calc_center_median()
        if f.normal.z < -0.05 and HATCH_Y < c.y < TUN_Y1 and abs(c.x) < TUN_X:
            dele.append(f)
    bmesh.ops.delete(bm, geom=dele, context='FACES')
    edges = [e for e in bm.edges if e.is_boundary]
    ret = bmesh.ops.extrude_edge_only(bm, edges=edges)
    for g in ret['geom']:
        if isinstance(g, bmesh.types.BMVert):
            g.co.z = TUN_ZTOP
    top = [g for g in ret['geom'] if isinstance(g, bmesh.types.BMEdge)]
    bmesh.ops.edgeloop_fill(bm, edges=top)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])


def build_hull():
    bm = bmesh.new()
    ys = hull_stations()
    vr, _ = skin(bm, [ring(y, NTH) for y in ys], closed=True)
    tip = bm.verts.new((0, NOSE_Y, NOSE_Z))
    for i in range(NTH):
        bm.faces.new((tip, vr[0][(i + 1) % NTH], vr[0][i]))
    bm.faces.new(vr[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    cut_tunnel(bm)
    canopy_cuts(bm)
    panes = canopy_mark(bm)
    print('окна фонаря:', sorted(panes), '— всего', len(panes))
    for f in bm.faces:
        f.smooth = True
    use_coll('chaika_canopy')
    bg = extract(bm, [f for f in bm.faces if f.material_index == GLASS])
    for f in bg.faces:
        f.material_index = 0
    glass = bm_obj(bg, 'canopy_glass', 'glass', 30)
    bf = extract(bm, [f for f in bm.faces if f.material_index == FRAME])
    for f in bf.faces:
        f.material_index = 0
    frame_solid(bf)
    frame = bm_obj(bf, 'canopy_frame', 'clay_frame', 30)
    shade(frame, 30)
    use_coll('chaika_ext')
    bm.normal_update()
    for f in bm.faces:
        c = f.calc_center_median()
        yy = min(max(c.y, -6.95), TAIL_Y)
        belly = c.z < sec(yy)['zch'] - 0.02 and f.normal.z < -0.12 and not (abs(c.x) < TUN_X + 0.01 and HATCH_Y - 0.01 < c.y < TUN_Y1 + 0.01 and c.z > bottom_z(yy, c.x) + 0.05)
        f.material_index = 1 if belly else 0
    hull = bm_obj(bm, 'ext_hull', ['clay', 'clay_belly'], 30)
    return hull, glass, frame


def build_wings():
    out = []
    w = loft('ext_wing_R', [wing_root_ring()] + [wing_section(x) for x in WING_XS], mat_name='clay', smooth=30)
    hub = cyl('ext_wing_hub_R', (WING_TIP_X - 0.06, NAC_Y, NAC_Z), (NAC_X - NAC_R + 0.05, NAC_Y, NAC_Z), 0.20, 24,
              'clay_mid', bevel=0.02)
    for o in (w, hub):
        out += [o, mirror_x(o, o.name[:-1] + 'L')]
        shade(out[-1], 30)
    return out


def build_nacelle(side):
    """Поворотная мотогондола на законцовке. Строится в полётном положении (ось вдоль Y, заборник к носу),
    опорная точка — ось поворота; посадочное положение — поворот −90° вокруг X (сопло вниз)."""
    sg = 1 if side == 'R' else -1
    body = revolve('nac', [(0.0, -0.45), (0.29, -0.45), (0.30, -0.80), (0.325, -0.955), (0.36, -0.98), (0.40, -0.93),
                           (0.44, -0.42), (0.44, 0.15), (0.39, 0.80), (0.315, 1.20), (0.0, 1.20)], 40, 'Y', mat_name='clay')
    spike = revolve('spike', [(0.0, -0.92), (0.07, -0.75), (0.15, -0.44), (0.0, -0.44)], 24, 'Y', mat_name='clay_mid')
    band = revolve('band', [(0.445, -0.16), (0.455, -0.14), (0.455, 0.14), (0.445, 0.16)], 40, 'Y', mat_name='clay_mid',
                   cap=False)
    nac = merge([body, spike, band], 'ext_nacelle_' + side, (0, 0, 0))
    shade(nac, 30)
    noz = revolve('ext_nacelle_nozzle_' + side, [(0.0, 1.19), (0.305, 1.19), (0.275, 1.60), (0.245, 1.60), (0.22, 1.26),
                                                  (0.0, 1.26)], 32, 'Y', mat_name='clay_dark')
    set_origin(noz, (0, 1.2, 0))
    set_parent(noz, nac)
    nac.location = (sg * NAC_X, NAC_Y, NAC_Z)
    nac.rotation_euler = (R(-90), 0, 0)
    return nac, noz


def build_pods():
    out = []
    rings = []
    for y in frange(1.30, 6.35, 0.2525):
        r, xc, zc = POD_R(y), POD_X(y), POD_Z(y)
        rings.append([(xc + r * math.cos(2 * math.pi * i / 32), y, zc + r * math.sin(2 * math.pi * i / 32)) for i in range(32)])
    pod = loft('ext_pod_R', rings, mat_name='clay', smooth=30)
    bx, bz = POD_X(6.35), POD_Z(6.35)
    bell = revolve('ext_bell_R', [(0.0, 6.26), (0.14, 6.26), (0.20, 6.47), (0.285, 6.77), (BELL_R, BELL_Y1),
                                  (BELL_R - 0.022, BELL_Y1), (0.17, 6.45), (0.0, 6.41)], 32, 'Y', (bx, 0, bz),
                   mat_name='clay_dark')
    set_origin(bell, (bx, BELL_Y0, bz))
    nx, nz = FIN_TIP['x'] - FIN_ROOT['x'], FIN_TIP['z'] - FIN_ROOT['z']
    L = math.hypot(nx, nz)
    px, pz = -nz / L, nx / L                      # нормаль к плоскости киля
    rings = []
    for t in (-0.30, 0.0, 0.5, 1.0):
        d = {k: FIN_ROOT[k] + (FIN_TIP[k] - FIN_ROOT[k]) * t for k in FIN_ROOT}
        rings.append([(d['x'] + px * tt * d['chord'], d['y_le'] + s * d['chord'], d['z'] + pz * tt * d['chord'])
                      for s, tt in airfoil(12, d['th'] / d['chord'], 0.0)])
    fin = loft('ext_fin_R', rings, mat_name='clay', smooth=30)
    for o in (pod, bell, fin):
        m = mirror_x(o, o.name[:-1] + 'L')
        shade(m, 30)
        if o is bell:
            set_origin(m, (-bx, BELL_Y0, bz))
        out += [o, m]
    return out


def build_gear():
    """Опора: рычаг от скулы к оси лыжи, амортизатор к борту, подкос вдоль борта, широкая лыжа с загнутым носком."""
    out = []
    for key, g in GEAR.items():
        A, P = Vector(g['A']), Vector(g['P'])
        y0 = P.y
        K = Vector((P.x, P.y, 0.40))
        prof = [(y0 + 1.08, 0.05), (y0 + 0.96, 0.0), (y0 - 0.70, 0.0), (y0 - 1.02, 0.08), (y0 - 1.30, 0.30),
                (y0 - 1.30, 0.40), (y0 - 0.98, 0.22), (y0 - 0.70, 0.14), (y0 + 1.08, 0.14)]
        parts = [prism('ski', prof, P.x - SKI_W / 2, P.x + SKI_W / 2, 'X', bevel=0.03, mat_name='clay_mid')]
        for sx in (-SKI_W / 2 + 0.06, 0.0, SKI_W / 2 - 0.06):          # продольные рёбра жёсткости
            parts.append(box('rib', (0.07, 1.70, 0.07), (P.x + sx, y0 + 0.12, 0.17), bevel=0.02, mat_name='clay_frame'))
        for yy in (-0.45, 0.70):                                         # поперечные балки
            parts.append(box('beam', (SKI_W - 0.10, 0.10, 0.08), (P.x, y0 + yy, 0.175), bevel=0.02, mat_name='clay_frame'))
        for sx in (-0.12, 0.12):
            parts.append(prism('cheek', [(y0 - 0.24, 0.13), (y0 + 0.24, 0.13), (y0 + 0.10, 0.48), (y0 - 0.10, 0.48)],
                               P.x + sx - 0.02, P.x + sx + 0.02, 'X', bevel=0.008, mat_name='clay_frame'))
        parts.append(cyl('axle', (P.x - 0.17, y0, K.z), (P.x + 0.17, y0, K.z), 0.05, 16, 'clay_dark'))
        for dy in (-0.55, 0.55):                        # нижний треугольник: два рычага от скулы к оси лыжи
            za = sec(A.y + dy)['zch'] + 0.04
            Aa = Vector((halfwidth(A.y + dy, za) - 0.03, A.y + dy, za))
            d = (K - Aa).normalized()
            e1 = d.cross(Vector((0, 0, 1))).normalized()
            e2 = d.cross(e1).normalized()
            rings = []
            for t, a_, b_ in ((-0.10, 0.10, 0.075), (0.0, 0.10, 0.075), (1.0, 0.06, 0.05)):
                c = Aa + (K - Aa) * t
                rings.append([c + e1 * a_ + e2 * b_, c - e1 * a_ + e2 * b_, c - e1 * a_ - e2 * b_, c + e1 * a_ - e2 * b_])
            parts.append(loft('arm', rings, mat_name='clay_mid', smooth=None))
        zb = sec(A.y)['zch'] + 0.95
        B = Vector((halfwidth(A.y, zb) - 0.05, A.y, zb))                     # главная стойка-амортизатор от борта
        Kt = K + Vector((0, 0, 0.10))
        mid = B + (Kt - B) * 0.55
        parts.append(cyl('shock', B, mid, 0.095, 24, 'clay_mid', bevel=0.015))
        parts.append(cyl('collar', mid - (Kt - B).normalized() * 0.07, mid + (Kt - B).normalized() * 0.03, 0.112, 24,
                         'clay_frame', bevel=0.01))
        parts.append(cyl('rod', mid, Kt, 0.06, 18, 'clay'))
        parts.append(box('knuckle', (0.30, 0.22, 0.22), Kt + Vector((0, 0, -0.03)), bevel=0.03, mat_name='clay_frame'))
        leg = merge(parts, 'ext_gear_%s_R' % key, (0, 0, 0))
        shade(leg, 35)
        m = mirror_x(leg, 'ext_gear_%s_L' % key)
        shade(m, 35)
        out += [leg, m]
    return out


def build_ramp():
    hw = TUN_X - 0.02
    parts = [box('deck', (2 * hw, RAMP_LEN, RAMP_T), (0, RAMP_LEN / 2, -RAMP_T / 2), bevel=0.012, mat_name='clay_mid')]
    for sgn in (1, -1):
        parts.append(box('curb', (0.06, RAMP_LEN - 0.1, 0.07), (sgn * (hw - 0.03), RAMP_LEN / 2, 0.035), bevel=0.01,
                         mat_name='clay_frame'))
    n = 11
    for i in range(n):
        parts.append(box('tread', (2 * hw - 0.2, 0.05, 0.025), (0, 0.22 + (RAMP_LEN - 0.4) * i / (n - 1), 0.012),
                         mat_name='clay_frame'))
    ramp = merge(parts, 'ext_ramp', (0, 0, 0))
    shade(ramp, 35)
    ramp.location = (0, HATCH_Y, RAMP_HINGE_Z)
    ramp.rotation_euler = (R(RAMP_OPEN), 0, 0)
    # гидроцилиндры трапа (в блок-модели — неподвижные, в положении «трап опущен»)
    ca, sa = math.cos(R(RAMP_OPEN)), math.sin(R(RAMP_OPEN))
    struts = []
    for sgn in (1, -1):
        q = Vector((sgn * (hw - 0.03), HATCH_Y + 1.35 * ca, RAMP_HINGE_Z + 1.35 * sa + 0.07))
        top = Vector((sgn * (TUN_X - 0.04), HATCH_Y + 0.55, TUN_ZTOP - 0.25))
        mid = top + (q - top) * 0.5
        struts += [cyl('c', top, mid, 0.04, 12, 'clay_frame'), cyl('r', mid, q, 0.024, 10, 'clay')]
    st = merge(struts, 'ext_ramp_struts', (0, 0, 0))
    shade(st, 35)
    return [ramp, st]


def build_hatch():
    use_coll('chaika_canopy')                       # люк общий для внешней модели и шлюза
    fr = box('hatch_frame', (1.10, 0.05, 1.83), (0, HATCH_Y - 0.01, FLOOR_Z + 0.90), bevel=0.012, mat_name='clay_frame')
    door = box('hatch_outer', (0.90, 0.08, 1.72), (0, HATCH_Y, FLOOR_Z + 0.86 + 0.02), bevel=0.02, mat_name='clay_mid')
    wheel = cyl('hatch_wheel', (0, HATCH_Y + 0.04, FLOOR_Z + 1.0), (0, HATCH_Y + 0.075, FLOOR_Z + 1.0), 0.14, 20,
                'clay_frame')
    door = merge([door, wheel], 'hatch_outer', (0, 0, 0))
    set_origin(door, (-0.45, HATCH_Y, FLOOR_Z + 0.895))
    shade(door, 35)
    return [fr, door]


def build_exterior():
    use_coll('chaika_ext')
    hull, glass, frame = build_hull()
    use_coll('chaika_ext')
    objs = [hull] + build_wings()
    for s in 'RL':
        objs += build_nacelle(s)
    objs += build_pods() + build_gear() + build_ramp()
    hatch = build_hatch()
    return objs, [glass, frame] + hatch


# ====================================================================== КАБИНА И ШЛЮЗ
def face_in(bm):
    """Развернуть нормали оболочки внутрь (к оси корпуса)."""
    bm.normal_update()
    for f in bm.faces:
        c = f.calc_center_median()
        if f.normal.dot(Vector((c.x, 0, c.z - 2.55))) > 0:
            f.normal_flip()


def section_wall(name, y, holes, thick=0.06, mat_name='clay_in'):
    """Поперечная переборка по внутреннему сечению корпуса с прямоугольными проёмами holes = [(x0, x1, z0, z1)]."""
    bm = bmesh.new()
    bm.faces.new([bm.verts.new(p) for p in ring(y, NTH, WALL - 0.01)])
    for x0, x1, z0, z1 in holes:
        for x in (x0, x1):
            cut(bm, (x, 0, 0), (1, 0, 0))
        for z in (z0, z1):
            cut(bm, (0, 0, z), (0, 0, 1))
        dele = []
        for f in bm.faces:
            c = f.calc_center_median()
            if x0 < c.x < x1 and z0 < c.z < z1:
                dele.append(f)
        bmesh.ops.delete(bm, geom=dele, context='FACES')
    ob = bm_obj(bm, name, mat_name, None)
    solidify(ob, thick, 0.0)
    return ob


def build_shell():
    bm = bmesh.new()
    ys = hull_stations(Y_CAP, HATCH_Y - 0.03)
    skin(bm, [ring(y, NTH, WALL) for y in ys], closed=True)
    canopy_cuts(bm)
    canopy_mark(bm)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != HULL], context='FACES')
    face_in(bm)
    for f in bm.faces:
        f.smooth = True
        f.material_index = 0
    shell = bm_obj(bm, 'ck_shell', 'clay_in', 30)
    # пол
    bm = bmesh.new()
    fy = [y for y in hull_stations(Y_CHIN_AFT, HATCH_Y - 0.03)]
    rings = []
    for y in fy:
        hw = halfwidth(y, FLOOR_Z, WALL) + 0.02
        rings.append([(-hw, y, FLOOR_Z), (hw, y, FLOOR_Z)])
    skin(bm, rings, closed=False)
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    floor = bm_obj(bm, 'ck_floor', 'clay_mid', None)
    hw = halfwidth(Y_CHIN_AFT, FLOOR_Z, WALL)
    riser = box('ck_floor_riser', (2 * hw + 0.1, 0.04, 0.22), (0, Y_CHIN_AFT - 0.0, FLOOR_Z - 0.10), mat_name='clay_mid')
    nose = section_wall('ck_nose_wall', Y_CAP + 0.005, [], 0.02, 'clay_frame')
    bulk = section_wall('ck_bulkhead', BULKHEAD_Y, [(-0.42, 0.42, FLOOR_Z, FLOOR_Z + 1.85)], 0.07)
    aft = section_wall('ck_aft_wall', HATCH_Y - 0.03, [(-0.45, 0.45, FLOOR_Z + 0.02, FLOOR_Z + 1.74)], 0.05)
    door = box('ck_door_airlock', (0.84, 0.045, 1.85), (0, BULKHEAD_Y, FLOOR_Z + 0.925), bevel=0.012, mat_name='clay_mid')
    set_origin(door, (-0.42, BULKHEAD_Y, FLOOR_Z + 0.925))
    return [shell, floor, riser, nose, bulk, aft, door]


def build_seat():
    y = EYE[1]
    top = EYE[2] - 0.79                                   # верх подушки сиденья
    parts = [box('ped', (0.34, 0.44, top - 0.08 - FLOOR_Z), (0, y + 0.10, (top - 0.08 + FLOOR_Z) / 2), bevel=0.03,
                 mat_name='clay_dark'),
             box('pan', (0.50, 0.50, 0.10), (0, y - 0.07, top - 0.05), bevel=0.035, mat_name='clay_seat'),
             box('back', (0.48, 0.11, 0.80), (0, y + 0.275, top + 0.38), bevel=0.035, mat_name='clay_seat', rot=(-9, 0, 0)),
             box('head', (0.27, 0.10, 0.22), (0, y + 0.255, EYE[2] + 0.03), bevel=0.035, mat_name='clay_seat'),
             box('wingL', (0.05, 0.16, 0.50), (-0.25, y + 0.22, top + 0.40), bevel=0.02, mat_name='clay_dark', rot=(-9, 0, 0)),
             box('wingR', (0.05, 0.16, 0.50), (0.25, y + 0.22, top + 0.40), bevel=0.02, mat_name='clay_dark', rot=(-9, 0, 0))]
    for sgn in (1, -1):                                   # привязные ремни (плечевые)
        parts.append(box('belt', (0.045, 0.012, 0.62), (sgn * 0.11, y + 0.205, top + 0.42), mat_name='clay_dark',
                         rot=(-9, 0, 0)))
    seat = merge(parts, 'ck_seat_pilot', (0, 0, 0))
    shade(seat, 35)
    return seat


PANEL_R = 0.80
PANEL_AZ = [-58, -35, -13, 13, 35, 58]
PANEL_Z0, PANEL_Z1 = 2.30, 2.54


def _pp(az, r, z):
    return Vector((r * math.sin(R(az)), EYE[1] - r * math.cos(R(az)), z))


def build_panel():
    out = []
    rings = [[_pp(a, PANEL_R - 0.03, PANEL_Z0), _pp(a, PANEL_R + 0.05, PANEL_Z1), _pp(a, PANEL_R + 0.13, PANEL_Z1 - 0.01),
              _pp(a, PANEL_R + 0.05, PANEL_Z0 - 0.01)] for a in PANEL_AZ]
    panel = loft('panel', rings, mat_name='clay_dark', smooth=None)
    hood = loft('hood', [[_pp(a, PANEL_R + 0.00, PANEL_Z1 + 0.012), _pp(a, PANEL_R + 0.14, PANEL_Z1 + 0.012),
                          _pp(a, PANEL_R + 0.14, PANEL_Z1 - 0.008), _pp(a, PANEL_R + 0.00, PANEL_Z1 - 0.002)]
                         for a in PANEL_AZ], mat_name='clay_frame', smooth=None)
    out.append(merge([panel, hood], 'ck_panel', (0, 0, 0)))
    sizes = [(0.25, 0.185), (0.25, 0.185), (0.30, 0.185), (0.25, 0.185), (0.25, 0.185)]
    for k in range(5):
        a0, a1 = PANEL_AZ[k], PANEL_AZ[k + 1]
        b0, b1 = _pp(a0, PANEL_R - 0.03, PANEL_Z0), _pp(a1, PANEL_R - 0.03, PANEL_Z0)
        t0, t1 = _pp(a0, PANEL_R + 0.05, PANEL_Z1), _pp(a1, PANEL_R + 0.05, PANEL_Z1)
        c = (b0 + b1 + t0 + t1) / 4
        et = (b1 - b0).normalized()
        eu = ((t0 + t1) / 2 - (b0 + b1) / 2).normalized()
        n = et.cross(eu)
        if n.dot(Vector(EYE) - c) < 0:
            n = -n
        w, h = sizes[k]
        c = c + n * 0.004
        me = bpy.data.meshes.new('screen_%d' % (k + 1))
        me.from_pydata([c - et * w / 2 - eu * h / 2, c + et * w / 2 - eu * h / 2, c + et * w / 2 + eu * h / 2,
                        c - et * w / 2 + eu * h / 2], [], [(0, 1, 2, 3)])
        me.materials.append(mat('screen'))
        ob = bpy.data.objects.new('ck_screen_%d' % (k + 1), me)
        link(ob)
        if ob.data.polygons[0].normal.dot(n) < 0:
            ob.data.flip_normals()
        out.append(ob)
    return out


def build_consoles():
    out = []
    ys = frange(Y_CHIN_AFT, -4.55, 0.1)
    xi = 0.37
    for sgn, nm in ((1, 'R'), (-1, 'L')):
        rings = []
        for y in ys:
            xw = lambda z: max(xi + 0.35, halfwidth(y, z, WALL) + 0.02)
            rings.append([(sgn * xi, y, FLOOR_Z), (sgn * xi, y, 2.27), (sgn * (xi + 0.03), y, 2.30), (sgn * 0.74, y, 2.30),
                          (sgn * xw(2.42), y, 2.42), (sgn * xw(2.0), y, 2.0), (sgn * max(xi + 0.05, halfwidth(y, FLOOR_Z, WALL)), y, FLOOR_Z)])
        con = loft('con', rings, mat_name='clay_mid', smooth=30)
        horn = prism('horn', [(Y_CHIN_AFT + 0.02, 2.30), (Y_CHIN_AFT + 0.02, 2.08), (-5.60, 2.16), (-5.74, 2.24),
                              (-5.74, 2.30)], sgn * xi, sgn * 0.72, 'X', bevel=0.015, mat_name='clay_mid')
        out.append(merge([con, horn], 'ck_console_' + nm, (0, 0, 0)))
        shade(out[-1], 30)
    # боковая ручка (справа)
    p = Vector((0.53, -5.40, 2.30))
    stick = merge([cyl('b', p, p + Vector((0, 0, 0.035)), 0.05, 20, 'clay_dark'),
                   cyl('g', p + Vector((0, 0, 0.03)), p + Vector((0, -0.035, 0.17)), 0.021, 14, 'clay_dark', r1=0.026),
                   box('h', (0.05, 0.05, 0.035), p + Vector((0, -0.04, 0.185)), bevel=0.012, mat_name='clay_dark')],
                  'ck_stick', (0, 0, 0))
    set_origin(stick, p)
    # РУД (слева)
    q = Vector((-0.53, -5.40, 2.30))
    thr = merge([cyl('l', q + Vector((0, 0.02, -0.01)), q + Vector((0, -0.03, 0.12)), 0.012, 10, 'clay_dark'),
                 cyl('t', q + Vector((-0.045, -0.03, 0.125)), q + Vector((0.045, -0.03, 0.125)), 0.019, 12, 'clay_dark')],
                'ck_throttle', (0, 0, 0))
    set_origin(thr, q + Vector((0, 0.02, -0.01)))
    slot = box('ck_throttle_base', (0.11, 0.24, 0.02), q + Vector((0, 0, 0.008)), bevel=0.006, mat_name='clay_frame')
    for o in (stick, thr):
        shade(o, 35)
    return out + [stick, thr, slot]


def build_cockpit_rest():
    out = []
    # педали на килевой балке
    kb = [(y, bottom_z(y, 0, WALL)) for y in frange(-6.62, Y_CHIN_AFT, 0.13)]
    beam = prism('ck_keel_beam', [(y, z - 0.03) for y, z in kb] + [(y, z + 0.07) for y, z in reversed(kb)],
                 -X_KEEL, X_KEEL, 'X', bevel=0.0, mat_name='clay_mid')
    out.append(beam)
    for sgn, nm in ((1, 'R'), (-1, 'L')):
        zb = bottom_z(-6.10, 0, WALL) + 0.07
        out.append(merge([box('p', (0.11, 0.025, 0.15), (sgn * 0.12, -6.13, zb + 0.16), bevel=0.008, mat_name='clay_dark',
                              rot=(28, 0, 0)),
                          cyl('a', (sgn * 0.12, -6.10, zb), (sgn * 0.12, -6.11, zb + 0.10), 0.014, 8, 'clay_frame')],
                         'ck_pedal_' + nm, (0, 0, 0)))
    # верхняя панель с тумблерами под хребтовой балкой
    y0, y1 = -5.28, -4.62
    z0, z1 = top_z(y0, 0, WALL) - 0.075, top_z(y1, 0, WALL) - 0.075
    ang = math.degrees(math.atan2(z1 - z0, y1 - y0))
    ovh = box('ck_overhead', (0.30, math.hypot(y1 - y0, z1 - z0), 0.07), (0, (y0 + y1) / 2, (z0 + z1) / 2), bevel=0.015,
              mat_name='clay_dark', rot=(ang, 0, 0))
    out.append(ovh)
    for i in range(3):                                   # ряды тумблеров — намёк
        for j in range(5):
            yy = y0 + 0.10 + 0.22 * i
            zz = z0 + (z1 - z0) * (yy - y0) / (y1 - y0) - 0.04
            out.append(box('ck_ovh_sw', (0.018, 0.018, 0.03), (-0.10 + 0.05 * j, yy, zz), mat_name='clay_frame'))
    out = [o for o in out if not o.name.startswith('ck_ovh_sw')] + [merge([o for o in out if o.name.startswith('ck_ovh_sw')],
                                                                          'ck_overhead_switches', (0, 0, 0))]
    # стойки оборудования у переборки
    def rack(name, sgn, ya, yb, zt=3.12):
        xo = min(halfwidth(ya, zt, WALL), halfwidth(yb, zt, WALL)) - 0.03
        xi = xo - 0.42
        parts = [box('r', (0.42, yb - ya, zt - FLOOR_Z), (sgn * (xo + xi) / 2, (ya + yb) / 2, (zt + FLOOR_Z) / 2), bevel=0.012,
                     mat_name='clay_mid')]
        n = int((zt - FLOOR_Z - 0.1) / 0.24)
        for i in range(n):
            parts.append(box('u', (0.02, yb - ya - 0.08, 0.20), (sgn * (xi - 0.008), (ya + yb) / 2, FLOOR_Z + 0.18 + 0.24 * i),
                             bevel=0.006, mat_name='clay_dark'))
        return merge(parts, name, (0, 0, 0))
    out.append(rack('ck_rack_L', -1, -4.25, BULKHEAD_Y - 0.08))
    out.append(rack('ck_rack_R', 1, -3.25, BULKHEAD_Y - 0.08))
    # откидное кресло за пилотом (правый борт, лицом вперёд)
    jx, jy = 0.80, -3.75
    out.append(merge([box('p', (0.42, 0.40, 0.06), (jx, jy - 0.02, 2.03), bevel=0.02, mat_name='clay_seat'),
                      box('b', (0.42, 0.07, 0.62), (jx, jy + 0.21, 2.40), bevel=0.02, mat_name='clay_seat', rot=(-6, 0, 0)),
                      box('l', (0.04, 0.04, 0.42), (jx - 0.17, jy - 0.16, 1.81), mat_name='clay_dark'),
                      box('l', (0.04, 0.04, 0.42), (jx + 0.17, jy - 0.16, 1.81), mat_name='clay_dark')],
                     'ck_seat_jump', (0, 0, 0)))
    for o in out:
        shade(o, 35)
    return out


def build_airlock():
    out = []
    z0 = FLOOR_Z
    # стойки скафандров (левый борт)
    for k, yc in enumerate((-1.70, -0.85)):
        xw = halfwidth(yc, z0 + 1.82, WALL) - 0.04
        parts = [box('fr', (0.10, 0.70, 1.80), (-(xw - 0.05), yc, z0 + 0.90), bevel=0.01, mat_name='clay_mid'),
                 box('torso', (0.30, 0.50, 0.62), (-(xw - 0.27), yc, z0 + 1.18), bevel=0.08, mat_name='clay'),
                 box('pack', (0.16, 0.42, 0.56), (-(xw - 0.12), yc, z0 + 1.20), bevel=0.03, mat_name='clay_frame'),
                 box('legL', (0.19, 0.19, 0.82), (-(xw - 0.27), yc - 0.13, z0 + 0.45), bevel=0.06, mat_name='clay'),
                 box('legR', (0.19, 0.19, 0.82), (-(xw - 0.27), yc + 0.13, z0 + 0.45), bevel=0.06, mat_name='clay'),
                 box('armL', (0.15, 0.15, 0.62), (-(xw - 0.27), yc - 0.33, z0 + 1.15), bevel=0.05, mat_name='clay'),
                 box('armR', (0.15, 0.15, 0.62), (-(xw - 0.27), yc + 0.33, z0 + 1.15), bevel=0.05, mat_name='clay'),
                 revolve('helm', [(0.0, -0.17), (0.12, -0.12), (0.17, 0.0), (0.12, 0.12), (0.0, 0.17)], 20, 'Z',
                         (-(xw - 0.27), yc, z0 + 1.68), mat_name='clay')]
        out.append(merge(parts, 'ck_suit_rack_%d' % (k + 1), (0, 0, 0)))
    xw = halfwidth(0.4, z0 + 0.46, WALL) - 0.03
    out.append(box('ck_bench', (0.42, 1.30, 0.44), (-(xw - 0.21), 0.45, z0 + 0.22), bevel=0.02, mat_name='clay_mid'))
    # ложемент дрона (правый борт)
    yc = -1.45
    xw = halfwidth(yc, z0 + 1.32, WALL) - 0.04
    cr = [box('arm', (0.30, 0.08, 0.06), (xw - 0.15, yc - 0.22, z0 + 0.95), bevel=0.01, mat_name='clay_mid'),
          box('arm', (0.30, 0.08, 0.06), (xw - 0.15, yc + 0.22, z0 + 0.95), bevel=0.01, mat_name='clay_mid'),
          box('plate', (0.05, 0.70, 0.60), (xw - 0.025, yc, z0 + 1.0), bevel=0.01, mat_name='clay_mid'),
          box('tray', (0.46, 0.62, 0.04), (xw - 0.28, yc, z0 + 0.90), bevel=0.012, mat_name='clay_frame')]
    out.append(merge(cr, 'ck_drone_cradle', (0, 0, 0)))
    dr = [revolve('body', [(0.0, -0.075), (0.14, -0.06), (0.20, 0.0), (0.15, 0.06), (0.0, 0.085)], 24, 'Z',
                  (xw - 0.28, yc, z0 + 1.02), mat_name='clay')]
    dr[0].data.transform(Matrix.Translation((xw - 0.28, yc, 0)) @ Matrix.Diagonal((1.0, 1.35, 1.0, 1.0)) @
                         Matrix.Translation((-(xw - 0.28), -yc, 0)))
    for dx, dy in ((0.13, 0.17), (-0.13, 0.17), (0.13, -0.17), (-0.13, -0.17)):
        dr.append(revolve('ring', [(0.075, -0.02), (0.095, -0.02), (0.095, 0.02), (0.075, 0.02)], 16, 'Z',
                          (xw - 0.28 + dx, yc + dy, z0 + 1.03), mat_name='clay_frame', closed=True, cap=False))
    out.append(merge(dr, 'ck_drone_proxy', (0, 0, 0)))
    # шкафы и пульт шлюза (правый борт)
    xw = halfwidth(0.0, z0 + 1.47, WALL) - 0.03
    out.append(box('ck_lockers', (0.40, 1.50, 1.45), (xw - 0.20, -0.15, z0 + 0.725), bevel=0.015, mat_name='clay_mid'))
    xw = halfwidth(1.3, z0 + 1.27, WALL) - 0.03
    pult = prism('pult', [(xw, z0), (xw - 0.36, z0), (xw - 0.36, z0 + 0.95), (xw - 0.20, z0 + 1.25), (xw, z0 + 1.25)],
                 0.95, 1.65, 'Y', bevel=0.015, mat_name='clay_mid')
    out.append(pult)
    pult.name = 'ck_airlock_console'
    a, b = Vector((xw - 0.345, 1.02, z0 + 0.985)), Vector((xw - 0.215, 1.02, z0 + 1.225))
    n = Vector((-(b.z - a.z), 0, b.x - a.x)).normalized() * 0.004
    me = bpy.data.meshes.new('screen_6')
    me.from_pydata([a + n, a + n + Vector((0, 0.56, 0)), b + n + Vector((0, 0.56, 0)), b + n], [], [(0, 1, 2, 3)])
    me.materials.append(mat('screen'))
    sc6 = bpy.data.objects.new('ck_screen_6', me)
    link(sc6)
    if sc6.data.polygons[0].normal.x > 0:
        sc6.data.flip_normals()
    out.append(sc6)
    for o in out:
        if o.type == 'MESH' and len(o.data.polygons) > 1:
            shade(o, 35)
    return out


def build_cockpit():
    use_coll('chaika_cockpit')
    objs = build_shell() + [build_seat()] + build_panel() + build_consoles() + build_cockpit_rest() + build_airlock()
    return objs


# ====================================================================== СБОРКА
def build_all():
    clear_scene()
    ext, shared = build_exterior()
    ck = build_cockpit()
    use_coll('chaika_markers')
    empty('eye_pilot', EYE, size=0.1)
    bpy.context.view_layer.update()
    return ext, shared, ck


def bbox(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs if o.type == 'MESH' for c in o.bound_box]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


if __name__ == '__main__':
    ext, shared, ck = build_all()
    lo, hi = bbox(ext + shared)
    print('ГАБАРИТЫ снаружи: длина %.2f (y %.2f…%.2f), размах %.2f, высота %.2f, низ %.2f' %
          (hi[1] - lo[1], lo[1], hi[1], hi[0] - lo[0], hi[2], lo[2]))
    print('днище над грунтом: %.2f; треугольников: снаружи %d, кабина %d, фонарь+люк %d' %
          (bottom_z(0.0), sum(tris(o) for o in ext), sum(tris(o) for o in ck), sum(tris(o) for o in shared)))
    os.makedirs(os.path.join(ROOT, 'src'), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'src', 'chaika_blockA.blend'))
    print('SAVED chaika_blockA.blend')
