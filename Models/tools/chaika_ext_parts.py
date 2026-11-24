# chaika_ext_parts.py — агрегаты внешней модели «Чайки»: опоры, трап, люк, ниша трапа, мелкие детали корпуса,
# начинка мотогондол и кормовых двигателей, заглушка кабины, метки. Подключается из chaika_ext.py (exec).


def mech(parts, name, origin=(0, 0, 0), atlas='B', dens=1.0):
    """Слить детали агрегата в один объект с опорной точкой origin и автоматической развёрткой."""
    ob = merge(parts, name, origin)
    shade(ob, 35)
    smart_uv(ob, atlas, dens=dens)
    return ob


def place(objs, M):
    for o in objs:
        o.data.transform(M)
        o.data.update()
    return objs


def hexbolt(p, n, d=0.03, h=0.012, m='m_steel'):
    p, n = Vector(p), Vector(n).normalized()
    return cyl('bolt', p - n * 0.003, p + n * h, d / 2, 6, m)


def bolt_circle(c, axis, r, n, d=0.028, h=0.012, m='m_steel', phase=0.0):
    c, a = Vector(c), Vector(axis).normalized()
    e1 = a.cross(Vector((0, 0, 1)) if abs(a.z) < 0.9 else Vector((1, 0, 0))).normalized()
    e2 = a.cross(e1)
    return [hexbolt(c + (e1 * math.cos(t) + e2 * math.sin(t)) * r, a, d, h, m)
            for t in (phase + 2 * math.pi * k / n for k in range(n))]


def rrect(w, h, r, n=5):
    """Скруглённый прямоугольник w × h с центром в нуле: точки против часовой стрелки."""
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90.0 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def torus(name, c, R0, r, axis='Y', mat_name='m_steel', segs=28, n=8):
    prof = [(R0 + r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    return revolve(name, prof, segs, axis, c, mat_name, closed=True, cap=False)


def side_frame(y, z, sgn):
    """Точка на борту и местные оси: X — вдоль борта (на правом борту к хвосту), Y — вверх по обводу, Z — наружу."""
    x = halfwidth(y, z)
    up = Vector((sgn * (halfwidth(y, z + 0.03) - x), 0, 0.03)).normalized()
    ty = Vector((sgn * (halfwidth(y + 0.03, z) - x), 0.03, 0)).normalized()
    X = ty * sgn
    Z = X.cross(up).normalized()
    Y = Z.cross(X).normalized()
    p = Vector((sgn * x, y, z))
    return p, Matrix.Translation(p) @ Matrix((X, Y, Z)).transposed().to_4x4(), Z


# ---------------------------------------------------------------------- опора с лыжей
def gear_leg(key):
    g = GEAR[key]
    A, P = Vector(g['A']), Vector(g['P'])
    y0, hw = P.y, SKI_W / 2
    K = Vector((P.x, P.y, 0.46))
    prof = [(y0 + 1.10, 0.06), (y0 + 0.98, 0.0), (y0 - 0.72, 0.0), (y0 - 1.04, 0.08), (y0 - 1.30, 0.30),
            (y0 - 1.30, 0.42), (y0 - 1.00, 0.24), (y0 - 0.72, 0.15), (y0 + 1.10, 0.15)]
    parts = [prism('ski', prof, P.x - hw, P.x + hw, 'X', bevel=0.03, mat_name='m_white')]
    for sx in (-hw + 0.035, hw - 0.035):                      # отбортовка
        parts.append(box('rail', (0.05, 1.82, 0.07), (P.x + sx, y0 + 0.19, 0.18), bevel=0.014, mat_name='m_white'))
    for sx in (-0.27, 0.0, 0.27):                             # продольные рёбра
        parts.append(box('rib', (0.06, 1.70, 0.07), (P.x + sx, y0 + 0.13, 0.182), bevel=0.016, mat_name='m_dark'))
    for yy in (-0.52, 0.74):                                  # поперечные балки
        parts.append(box('beam', (SKI_W - 0.16, 0.09, 0.085), (P.x, y0 + yy, 0.19), bevel=0.016, mat_name='m_dark'))
    parts.append(box('bumper', (SKI_W - 0.10, 0.08, 0.11), (P.x, y0 - 1.315, 0.36), bevel=0.03, mat_name='m_rubber'))
    parts.append(box('base', (0.46, 0.62, 0.035), (P.x, y0, 0.165), bevel=0.01, mat_name='m_alu'))
    for sx in (-0.19, 0.19):
        for yy in (-0.26, 0.26):
            parts.append(hexbolt((P.x + sx, y0 + yy, 0.182), (0, 0, 1), 0.034, 0.016))
    for sx in (-0.15, 0.15):                                  # щёки шарнира лыжи
        parts.append(prism('cheek', [(y0 - 0.27, 0.17), (y0 + 0.27, 0.17), (y0 + 0.11, 0.55), (y0 - 0.11, 0.55)],
                           P.x + sx - 0.022, P.x + sx + 0.022, 'X', bevel=0.008, mat_name='m_alu'))
    parts.append(cyl('axle', (P.x - 0.21, y0, K.z), (P.x + 0.21, y0, K.z), 0.045, 20, 'm_steel'))
    for sx in (-0.215, 0.185):
        parts.append(cyl('nut', (P.x + sx, y0, K.z), (P.x + sx + 0.03, y0, K.z), 0.062, 6, 'm_steel'))
    for dy in (-0.55, 0.55):                                  # нижний треугольник: два рычага от скулы
        za = sec(A.y + dy)['zch'] + 0.04
        Aa = Vector((halfwidth(A.y + dy, za) - 0.03, A.y + dy, za))
        d = (K - Aa).normalized()
        e1 = d.cross(Vector((0, 0, 1))).normalized()
        e2 = d.cross(e1).normalized()
        rings = []
        for t, a_, b_ in ((0.02, 0.105, 0.075), (0.5, 0.085, 0.062), (0.97, 0.062, 0.05)):
            c = Aa + (K - Aa) * t
            rings.append([c + e1 * a_ + e2 * b_, c - e1 * a_ + e2 * b_, c - e1 * a_ - e2 * b_, c + e1 * a_ - e2 * b_])
        arm = loft('arm', rings, mat_name='m_white', smooth=None)
        bm = bmesh.new()
        bm.from_mesh(arm.data)
        bmesh.ops.bevel(bm, geom=[e for e in bm.edges], offset=0.012, segments=2, profile=0.5, affect='EDGES', clamp_overlap=True)
        bm.to_mesh(arm.data)
        bm.free()
        parts.append(arm)
        parts.append(box('fit', (0.20, 0.26, 0.20), Aa + Vector((0.01, 0, 0.0)), bevel=0.03, mat_name='m_alu'))
        parts.append(cyl('pin', Aa + Vector((0.03, -0.15, 0)), Aa + Vector((0.03, 0.15, 0)), 0.03, 12, 'm_steel'))
        for zz in (-0.06, 0.06):
            parts.append(hexbolt(Aa + Vector((0.11, 0.08, zz)), (1, 0, 0.2), 0.03, 0.014))
            parts.append(hexbolt(Aa + Vector((0.11, -0.08, zz)), (1, 0, 0.2), 0.03, 0.014))
        parts.append(box('lug', (0.10, 0.16, 0.12), Aa + (K - Aa) * 0.985, bevel=0.02, mat_name='m_alu'))
    zb = sec(A.y)['zch'] + 0.95                                 # главная стойка-амортизатор от борта
    B = Vector((halfwidth(A.y, zb) - 0.05, A.y, zb))
    Kt = K + Vector((0, 0, 0.11))
    ax = (Kt - B).normalized()
    Ls = (Kt - B).length
    mid = B + ax * Ls * 0.56
    parts.append(cyl('shock', B, mid, 0.095, 28, 'm_white', bevel=0.015))
    for f in (0.12, 0.47):
        parts.append(cyl('clamp', B + ax * Ls * f, B + ax * Ls * (f + 0.025), 0.106, 28, 'm_steel', bevel=0.006))
    parts.append(cyl('gland', mid - ax * 0.02, mid + ax * 0.055, 0.088, 6, 'm_steel'))
    parts.append(cyl('rod', mid, Kt, 0.052, 20, 'm_chrome'))
    parts.append(box('knuckle', (0.30, 0.22, 0.20), Kt + Vector((0, 0, -0.02)), bevel=0.04, mat_name='m_alu'))
    parts.append(box('mount', (0.12, 0.30, 0.30), B + Vector((0.0, 0, 0)), bevel=0.03, mat_name='m_alu'))
    for yy in (-0.11, 0.11):
        for zz in (-0.11, 0.11):
            parts.append(hexbolt(B + Vector((0.06, yy, zz)), (1, 0, 0.15), 0.032, 0.014))
    off = Vector((0.03, 0.19, 0))                               # баллон азота и хомуты
    parts.append(cyl('bottle', B + ax * 0.18 + off, B + ax * Ls * 0.50 + off, 0.052, 18, 'm_orange', bevel=0.02))
    for f in (0.2, 0.42):
        parts.append(cyl('strap', B + ax * Ls * f + off, B + ax * (Ls * f + 0.03) + off, 0.058, 18, 'm_steel'))
    parts.append(pipe('bpipe', [B + ax * 0.16 + off, B + ax * 0.08 + off * 0.5, B + ax * 0.10], 0.010, 'm_steel', sides=6))
    fo = Vector((0, -0.14, 0))                                  # шлиц-шарнир («ножницы»)
    E = (mid + Kt) / 2 + Vector((0, -0.36, 0))
    for a_, b_ in ((mid - ax * 0.05 + fo * 0.6, E), (E, Kt + fo * 0.6)):
        parts.append(cyl('link', a_, b_, 0.024, 10, 'm_alu'))
    parts.append(cyl('epin', E - Vector((0.06, 0, 0)), E + Vector((0.06, 0, 0)), 0.03, 10, 'm_steel'))
    h0 = B + ax * 0.10 + Vector((0.02, -0.12, 0))               # гидрошланг
    hp = [h0, B + ax * Ls * 0.30 + Vector((0.03, -0.125, 0)), B + ax * Ls * 0.52 + Vector((0.03, -0.12, 0)),
          B + ax * Ls * 0.78 + Vector((0.10, -0.13, 0)), Kt + Vector((0.05, -0.12, 0.06))]
    parts.append(pipe('hose', hp, 0.014, 'm_rubber', sides=6, res=5))
    for q in hp[1:3]:
        parts.append(cyl('hclamp', q - ax * 0.015, q + ax * 0.015, 0.021, 8, 'm_steel'))
    return mech(parts, 'ext_gear_%s_R' % key, atlas='C')


# ---------------------------------------------------------------------- трап и люк шлюза
def build_ramp():
    L, hw = RAMP_LEN, TUN_X - 0.02
    parts = [box('deck', (2 * hw, L, 0.03), (0, L / 2, -0.015), bevel=0.006, mat_name='m_tread'),
             box('skin', (2 * hw, L, 0.014), (0, L / 2, -RAMP_T + 0.007), mat_name='m_dark')]
    for sgn in (1, -1):
        parts.append(box('beam', (0.07, L, RAMP_T - 0.03), (sgn * (hw - 0.035), L / 2, -RAMP_T / 2 - 0.008), bevel=0.01,
                         mat_name='m_white'))
        parts.append(box('curb', (0.05, L - 0.16, 0.075), (sgn * (hw - 0.025), L / 2, 0.037), bevel=0.014, mat_name='m_orange'))
    for i in range(6):
        parts.append(box('rib', (2 * hw - 0.14, 0.05, RAMP_T - 0.046), (0, 0.25 + (L - 0.5) * i / 5, -RAMP_T / 2 - 0.008),
                         mat_name='m_white'))
    n = 13
    for i in range(n):
        parts.append(box('tread', (2 * hw - 0.22, 0.045, 0.016), (0, 0.20 + (L - 0.38) * i / (n - 1), 0.008), bevel=0.004,
                         mat_name='m_alu'))
    for x in (-0.5, 0.0, 0.5):
        parts.append(cyl('barrel', (x - 0.14, 0, -0.05), (x + 0.14, 0, -0.05), 0.045, 18, 'm_steel', bevel=0.008))
    parts.append(box('toe', (2 * hw, 0.07, 0.06), (0, L - 0.035, -0.03), bevel=0.02, mat_name='m_rubber'))
    ob = mech(parts, 'ext_ramp', atlas='C')
    ob.location = (0, HATCH_Y, RAMP_HINGE_Z)
    ob.rotation_euler = (R(RAMP_OPEN), 0, 0)
    return ob


HATCH_ZC = FLOOR_Z + 0.02 + 0.86


def build_hatch():
    y, zc = HATCH_Y, HATCH_ZC
    parts = [prism('door', [(x, zc + z) for x, z in rrect(0.90, 1.72, 0.14)], y - 0.01, y + 0.06, 'Y', bevel=0.012,
                   mat_name='m_white'),
             prism('pan', [(x, zc + z) for x, z in rrect(0.70, 1.50, 0.10)], y + 0.055, y + 0.075, 'Y', bevel=0.006,
                   mat_name='m_white'),
             revolve('port', [(0.10, 0.0), (0.14, 0.0), (0.14, 0.03), (0.10, 0.03)], 28, 'Y', (0, y + 0.07, zc + 0.44), 'm_alu',
                     closed=True, cap=False),
             cyl('pglass', (0, y + 0.078, zc + 0.44), (0, y + 0.088, zc + 0.44), 0.102, 28, 'glass'),
             torus('wheel', (0, y + 0.15, zc - 0.10), 0.135, 0.015, 'Y', 'm_orange'),
             cyl('hub', (0, y + 0.07, zc - 0.10), (0, y + 0.165, zc - 0.10), 0.032, 14, 'm_steel'),
             box('placard', (0.24, 0.006, 0.10), (0.18, y + 0.078, zc + 0.16), mat_name='m_alu')]
    parts += bolt_circle((0, y + 0.10, zc + 0.44), (0, 1, 0), 0.12, 10, 0.016, 0.008)
    for k in range(3):
        a = math.radians(90 + 120 * k)
        parts.append(cyl('spoke', (0, y + 0.15, zc - 0.10), (0.135 * math.cos(a), y + 0.15, zc - 0.10 + 0.135 * math.sin(a)),
                         0.010, 8, 'm_orange'))
    for (dx, dz) in ((0.44, 0.5), (0.44, -0.5), (-0.44, 0.0), (0.0, 0.85), (0.0, -0.85), (0.44, 0.0)):
        parts.append(box('dog', (0.08 if dx else 0.04, 0.03, 0.04 if dx else 0.08), (dx * 0.98, y + 0.075, zc + dz * 0.985),
                         bevel=0.008, mat_name='m_steel'))
    for dz in (-0.55, 0.55):
        parts.append(box('hinge', (0.12, 0.05, 0.15), (-0.47, y + 0.07, zc + dz), bevel=0.012, mat_name='m_steel'))
        parts.append(cyl('hpin', (-0.52, y + 0.085, zc + dz - 0.09), (-0.52, y + 0.085, zc + dz + 0.09), 0.016, 10, 'm_steel'))
    return mech(parts, 'ext_hatch', origin=(-0.52, y + 0.085, zc), atlas='C')


def build_tunnel_fit():
    y, zc = HATCH_Y, HATCH_ZC
    out_, inn = rrect(1.12, 1.94, 0.22, 6), rrect(0.93, 1.75, 0.155, 6)
    r0 = [(x, y - 0.005, zc + z) for x, z in out_]
    rings = [r0, [(x, y + 0.035, zc + z) for x, z in out_], [(x, y + 0.035, zc + z) for x, z in inn],
             [(x, y - 0.005, zc + z) for x, z in inn], r0]
    parts = [loft('hframe', rings, closed=True, cap0=False, cap1=False, mat_name='m_dark', smooth=35)]
    mid = rrect(1.025, 1.845, 0.19, 5)
    for k in range(0, len(mid), 1):
        x, z = mid[k]
        parts.append(hexbolt((x, y + 0.035, zc + z), (0, 1, 0), 0.026, 0.012))
    for yy in (2.60, 3.30, 4.00):
        zt = TUN_ZTOP
        for sgn in (1, -1):
            z0 = bottom_z(yy, TUN_X) + 0.01
            parts.append(box('rib', (0.045, 0.07, zt - z0), (sgn * (TUN_X - 0.022), yy, (zt + z0) / 2), bevel=0.008, mat_name='tunnel'))
        parts.append(box('cbeam', (2 * TUN_X, 0.07, 0.05), (0, yy, zt - 0.025), bevel=0.008, mat_name='tunnel'))
    for sgn in (1, -1):
        parts.append(box('lamp_body', (0.11, 0.95, 0.03), (sgn * 0.45, 2.95, TUN_ZTOP - 0.015), bevel=0.006, mat_name='m_dark'))
        parts.append(box('lamp', (0.07, 0.88, 0.012), (sgn * 0.45, 2.95, TUN_ZTOP - 0.034), mat_name='emissive'))
        xs = sgn * 0.68                                           # поручень у люка
        parts.append(pipe('grab', [(xs, y + 0.02, zc - 0.25), (xs, y + 0.10, zc - 0.20), (xs, y + 0.10, zc + 0.30),
                                   (xs, y + 0.02, zc + 0.35)], 0.016, 'm_orange', sides=8, res=4))
    parts.append(box('sill', (0.96, 0.05, 0.035), (0, y + 0.02, FLOOR_Z + 0.0), bevel=0.008, mat_name='m_tread'))
    return mech(parts, 'ext_tunnel_fit', atlas='C', dens=0.8)


# ---------------------------------------------------------------------- мелкие детали корпуса
def build_hull_details():
    parts = []
    lights = []
    for sgn in (1, -1):
        # брызгоотбойные рейки вдоль скулы
        rings = []
        for yy in frange(-5.25, 2.15, 0.3):
            zc = sec(yy)['zch']
            x = halfwidth(yy, zc)
            k = min(1.0, (yy + 5.25) / 0.6, (2.15 - yy) / 0.6)
            rings.append([(sgn * (x - 0.012), yy, zc + 0.04), (sgn * (x + 0.06 * k), yy, zc - 0.004), (sgn * (x - 0.012), yy, zc - 0.05)])
        parts.append(loft('spray', rings, mat_name='m_dark', smooth=40))
        # двигатели ориентации на борту за кабиной
        p, M, n = side_frame(-4.02, 2.98, sgn)
        blk = [box('rcs', (0.46, 0.26, 0.04), (0, 0, 0.012), bevel=0.012, mat_name='rcc')]
        for xx in (-0.14, 0.0, 0.14):
            blk.append(revolve('rn', [(0.022, 0.0), (0.05, 0.055), (0.043, 0.055), (0.016, 0.008)], 14, 'Z', (xx, 0, 0.03), 'm_nozzle',
                               closed=True, cap=False))
        blk += [hexbolt((sx * 0.20, sy * 0.10, 0.03), (0, 0, 1), 0.02, 0.008) for sx in (-1, 1) for sy in (-1, 1)]
        parts += place(blk, M)
        # поручень над боковым окном
        pts, feet = [], []
        for yy in (-4.20, -3.85, -3.50, -3.15):
            q, M2, n2 = side_frame(yy, sec(yy)['zs'] - 0.24, sgn)
            pts.append(q + n2 * 0.075)
            feet.append((q, q + n2 * 0.075))
        parts.append(pipe('rail', pts, 0.016, 'm_alu', sides=8, res=3))
        for a_, b_ in (feet[0], feet[-1], feet[1]):
            parts.append(cyl('foot', a_ - (b_ - a_).normalized() * 0.01, b_, 0.012, 8, 'm_alu'))
        # приёмники воздушного давления на носовом обтекателе
        q, M2, n2 = side_frame(-6.86, 2.16, sgn)
        parts.append(pipe('pitot', [q - n2 * 0.01, q + n2 * 0.10, q + n2 * 0.11 + Vector((0, -0.06, 0)), q + n2 * 0.11 + Vector((0, -0.13, 0))],
                          0.011, 'm_alu', sides=8, res=4))
        # посадочные фары под носом
        xl, yl = sgn * 0.62, -4.95
        zl = bottom_z(yl, xl)
        a_, b_ = Vector((xl, yl, zl + 0.03)), Vector((xl, yl - 0.11, zl - 0.085))
        parts.append(cyl('lamp_body', a_, b_, 0.085, 20, 'm_dark', bevel=0.012))
        dd = (b_ - a_).normalized()
        parts.append(cyl('lamp_lens', b_ - dd * 0.004, b_ + dd * 0.006, 0.068, 20, 'emissive'))
        lights.append((sgn, b_, dd))
    # обтекатель спутниковой антенны, ножевые антенны, маяки
    zt = top_z(-3.30)
    parts.append(revolve('dome', [(0.0, -0.03), (0.30, -0.03), (0.30, 0.025), (0.26, 0.085), (0.16, 0.135), (0.0, 0.15)], 32, 'Z',
                         (0, -3.30, zt), 'm_white'))
    for yy in (-2.25, 3.30):
        zt = top_z(yy) - 0.02
        parts.append(prism('blade', [(yy, zt), (yy + 0.30, zt), (yy + 0.35, zt + 0.23), (yy + 0.21, zt + 0.25)], -0.011, 0.011, 'X',
                           bevel=0.004, mat_name='m_white'))
    for yy in (-1.30, 0.80):
        zb_ = bottom_z(yy) + 0.02
        parts.append(prism('bladeb', [(yy, zb_), (yy + 0.26, zb_), (yy + 0.30, zb_ - 0.17), (yy + 0.18, zb_ - 0.19)], -0.010, 0.010, 'X',
                           bevel=0.004, mat_name='m_dark'))
    for yy, zz, dn in ((4.05, top_z(4.05), 1), (1.55, bottom_z(1.55), -1)):
        parts.append(cyl('beacon_base', (0, yy, zz - 0.01 * dn), (0, yy, zz + 0.03 * dn), 0.05, 16, 'm_dark'))
        parts.append(revolve('beacon', [(0.042, 0.0), (0.042, 0.03 * dn), (0.03, 0.055 * dn), (0.0, 0.066 * dn)], 16, 'Z',
                             (0, yy, zz + 0.03 * dn), 'emissive'))
    return mech(parts, 'ext_details'), lights


def build_wing_parts():
    parts = [cyl('hub', (WING_TIP_X - 0.07, NAC_Y, NAC_Z), (NAC_X - 0.47, NAC_Y, NAC_Z), 0.20, 28, 'm_dark', bevel=0.02),
             cyl('flange', (WING_TIP_X - 0.02, NAC_Y, NAC_Z), (WING_TIP_X + 0.02, NAC_Y, NAC_Z), 0.245, 28, 'm_alu', bevel=0.008)]
    parts += bolt_circle((WING_TIP_X + 0.02, NAC_Y, NAC_Z), (1, 0, 0), 0.222, 14, 0.024, 0.012)
    zt = wing_z(3.45) - 0.11
    parts.append(cyl('act', (3.45, 0.42, zt), (3.82, 0.30, NAC_Z - 0.13), 0.036, 12, 'm_steel'))
    parts.append(cyl('actrod', (3.82, 0.30, NAC_Z - 0.13), (4.04, 0.22, NAC_Z - 0.16), 0.020, 10, 'm_chrome'))
    for x in (1.95, 3.05):                                       # обтекатели приводов закрылков
        ch = _w_te(x) - _w_le(x)
        zc = wing_z(x) - _w_th(x) * 0.36
        y0 = _w_le(x) + ch * 0.55
        parts.append(revolve('canoe', [(0.0, -0.36), (0.045, -0.24), (0.07, 0.0), (0.06, 0.34), (0.03, 0.58), (0.0, 0.70)], 14, 'Y',
                             (x, y0, zc), 'm_dark'))
    for x in (2.9, 3.3, 3.7):                                    # разрядники статического электричества
        te = _w_te(x)
        parts.append(cyl('wick', (x, te - 0.02, wing_z(x)), (x, te + 0.17, wing_z(x) - 0.012), 0.004, 5, 'm_dark'))
    xl = WING_TIP_X - 0.03
    parts.append(box('nav', (0.04, 0.12, 0.035), (xl, _w_le(xl) + 0.07, wing_z(xl)), bevel=0.012, mat_name='emissive'))
    return mech(parts, 'ext_wing_parts_R')


def build_pod_parts():
    bx, bz = POD_X(6.35), POD_Z(6.35)
    parts = [cyl('base', (bx, 6.33, bz), (bx, 6.375, bz), 0.40, 32, 'm_dark', bevel=0.008),
             revolve('gimbal', [(0.19, 6.36), (0.27, 6.36), (0.27, 6.43), (0.19, 6.43)], 28, 'Y', (bx, 0, bz), 'm_steel',
                     closed=True, cap=False)]
    parts += bolt_circle((bx, 6.375, bz), (0, 1, 0), 0.34, 12, 0.026, 0.012)
    yy = 5.35
    xo = POD_X(yy) + POD_R(yy) - 0.012
    parts.append(box('rcs', (0.05, 0.40, 0.26), (xo, yy, POD_Z(yy)), bevel=0.012, mat_name='rcc'))
    for dy in (-0.12, 0.0, 0.12):
        parts.append(revolve('rn', [(0.022, 0.0), (0.05, 0.055), (0.043, 0.055), (0.016, 0.008)], 14, 'X', (xo + 0.02, yy + dy, POD_Z(yy)),
                             'm_nozzle', closed=True, cap=False))
    return mech(parts, 'ext_pod_parts_R')


def build_bell():
    bx, bz = POD_X(6.35), POD_Z(6.35)
    prof = [(1e-4, 6.27), (0.13, 6.27), (0.16, 6.33), (0.20, 6.45), (0.212, 6.455), (0.212, 6.475), (0.205, 6.48), (0.26, 6.63),
            (0.272, 6.635), (0.272, 6.655), (0.265, 6.66), (0.31, 6.82), (0.322, 6.825), (0.322, 6.845), (0.315, 6.85),
            (BELL_R, BELL_Y1), (BELL_R - 0.02, BELL_Y1), (0.19, 6.46), (0.11, 6.36), (1e-4, 6.35)]
    bell = revolve('bell', prof, 40, 'Y', (bx, 0, bz), 'm_nozzle')
    return mech([bell], 'ext_bell_R', origin=(bx, BELL_Y0, bz))


def build_nacelle_parts():
    parts = [revolve('spike', [(0.0, -0.90), (0.05, -0.80), (0.11, -0.60), (0.15, -0.42), (0.0, -0.42)], 24, 'Y', mat_name='m_alu')]
    for k in range(14):
        v = box('vane', (0.17, 0.10, 0.008), (0.21, -0.50, 0), mat_name='m_steel', rot=(0, 0, 0))
        v.data.transform(Matrix.Rotation(2 * math.pi * k / 14, 4, 'Y') @ Matrix.Translation((0.21, -0.50, 0)) @
                         Matrix.Rotation(R(18), 4, 'X') @ Matrix.Translation((-0.21, 0.50, 0)))
        parts.append(v)
    parts.append(revolve('collar', [(0.441, -0.20), (0.462, -0.18), (0.462, 0.18), (0.441, 0.20)], 48, 'Y', mat_name='m_alu', cap=False))
    for hh in (-0.14, 0.14):
        for k in range(20):
            a = 2 * math.pi * (k + 0.5) / 20
            parts.append(hexbolt((0.462 * math.cos(a), hh, 0.462 * math.sin(a)), (math.cos(a), 0, math.sin(a)), 0.022, 0.010))
    for hh, rr in ((-0.72, 0.431), (0.72, 0.409)):
        parts.append(revolve('ringf', [(rr, hh - 0.02), (rr + 0.008, hh - 0.014), (rr + 0.008, hh + 0.014), (rr, hh + 0.02)], 48, 'Y',
                             mat_name='m_dark', cap=False))
    parts.append(cyl('trunnion', (0.42, 0, 0), (0.472, 0, 0), 0.15, 24, 'm_steel', bevel=0.012))
    parts += bolt_circle((0.472, 0, 0), (1, 0, 0), 0.11, 8, 0.026, 0.010)
    parts.append(cyl('socket', (-0.475, 0, 0), (-0.42, 0, 0), 0.225, 28, 'm_alu', bevel=0.008))
    return mech(parts, 'ext_nacelle_parts_R')


def build_nacelle_nozzle():
    noz = revolve('noz', [(1e-4, 1.19), (0.31, 1.19), (0.275, 1.60), (0.25, 1.60), (0.22, 1.26), (1e-4, 1.26)], 40, 'Y',
                  mat_name='m_nozzle')
    parts = [noz]
    for hh, rr in ((1.27, 0.305), (1.42, 0.292), (1.56, 0.280)):
        parts.append(revolve('nr', [(rr, hh - 0.012), (rr + 0.008, hh - 0.008), (rr + 0.008, hh + 0.008), (rr, hh + 0.012)], 40, 'Y',
                             mat_name='m_steel', cap=False))
    return mech(parts, 'ext_nacelle_nozzle_R', origin=(0, 1.20, 0))


def build_cockpit_proxy():
    """Тёмная заглушка кабины, чтобы снаружи сквозь стёкла был виден интерьер-силуэт (в сцене с детальной кабиной
    этот объект можно скрыть)."""
    bm = bmesh.new()
    ys = hull_stations(Y_CAP, -4.05)
    vr, _ = skin(bm, [ring(yy, NTH, 0.07) for yy in ys], closed=True)
    bm.faces.new(vr[-1])
    canopy_cuts(bm)
    canopy_mark(bm)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != HULL], context='FACES')
    bm.normal_update()
    for f in bm.faces:
        c = f.calc_center_median()
        if f.normal.dot(Vector((c.x, -0.3 if c.y > -4.1 else 0, c.z - 2.55))) > 0:
            f.normal_flip()
        f.material_index = 0
    shell = bm_obj(bm, 'liner', 'm_dark', 30)
    ey, top = EYE[1], EYE[2] - 0.79
    parts = [shell,
             box('floor', (2.3, 1.45, 0.04), (0, -4.75, FLOOR_Z - 0.02), mat_name='m_dark'),
             box('ped', (0.34, 0.44, top - 0.08 - FLOOR_Z), (0, ey + 0.10, (top - 0.08 + FLOOR_Z) / 2), bevel=0.03, mat_name='m_dark'),
             box('pan', (0.50, 0.50, 0.10), (0, ey - 0.07, top - 0.05), bevel=0.035, mat_name='m_rubber'),
             box('back', (0.48, 0.11, 0.80), (0, ey + 0.275, top + 0.38), bevel=0.035, mat_name='m_rubber', rot=(-9, 0, 0)),
             box('head', (0.27, 0.10, 0.22), (0, ey + 0.255, EYE[2] + 0.03), bevel=0.035, mat_name='m_rubber')]
    az = [-58, -35, -13, 13, 35, 58]
    pp = lambda a, r, z: Vector((r * math.sin(R(a)), ey - r * math.cos(R(a)), z))
    parts.append(loft('panel', [[pp(a, 0.77, 2.30), pp(a, 0.85, 2.54), pp(a, 0.94, 2.55), pp(a, 0.85, 2.29)] for a in az],
                      mat_name='m_dark', smooth=None))
    for sgn in (1, -1):
        parts.append(box('con', (0.50, 0.95, 0.66), (sgn * 0.66, -4.98, FLOOR_Z + 0.33), bevel=0.03, mat_name='m_dark'))
    return mech(parts, 'ext_cockpit_proxy', dens=0.33)


# ---------------------------------------------------------------------- сборка частей
def build_static_parts(twin):
    out = []
    for key in GEAR:
        g = gear_leg(key)
        out += [g, twin(g, 'ext_gear_%s_L' % key)]
    det, lights = build_hull_details()
    build_static_parts.lights = lights
    out += [det, build_tunnel_fit(), build_cockpit_proxy()]
    for b in (build_wing_parts(), build_pod_parts()):
        out += [b, twin(b, b.name[:-1] + 'L')]
    return out


def build_moving_parts(twin_local):
    out = []
    sh = build_nacelle_shell()
    pr = build_nacelle_parts()
    nz = build_nacelle_nozzle()
    set_parent(pr, sh)
    set_parent(nz, sh)
    sh.location = (NAC_X, NAC_Y, NAC_Z)
    sh.rotation_euler = (R(-90), 0, 0)                           # в сцене — посадочное положение (сопло вниз)
    bpy.context.view_layer.update()
    shL = twin_local(sh, 'ext_nacelle_L')
    prL = twin_local(pr, 'ext_nacelle_parts_L', parent=shL)
    nzL = twin_local(nz, 'ext_nacelle_nozzle_L', parent=shL)
    bell = build_bell()
    bellL = twin_local(bell, 'ext_bell_L')
    out += [sh, pr, nz, shL, prL, nzL, bell, bellL, build_ramp(), build_hatch()]
    build_moving_parts.refs = dict(nac_R=sh, nac_L=shL, noz_R=nz, noz_L=nzL, bell_R=bell, bell_L=bellL, ramp=out[-2], hatch=out[-1])
    return out


def build_markers():
    r = build_moving_parts.refs
    m = [empty('eye_pilot', EYE, size=0.1)]
    for s, sg in (('R', 1), ('L', -1)):
        m.append(empty('fx_nozzle_' + s, (0, 0.42, 0), size=0.2, parent=None))
        m[-1].parent = r['noz_' + s]
        m.append(empty('fx_intake_' + s, (0, -1.0, 0), size=0.2))
        m[-1].parent = r['nac_' + s]
        m.append(empty('fx_bell_' + s, (0, BELL_Y1 - BELL_Y0, 0), size=0.2))
        m[-1].parent = r['bell_' + s]
        for key, g in GEAR.items():
            m.append(empty('fx_splash_%s_%s' % (key, s), (sg * g['P'][0], g['P'][1], 0.0), size=0.3))
    for sgn, p, d in build_static_parts.lights:
        e = empty('light_landing_' + ('R' if sgn > 0 else 'L'), p, size=0.15)
        e.rotation_euler = d.to_track_quat('Y', 'Z').to_euler()      # ось +Y метки — направление луча
        m.append(e)
    m.append(empty('ramp_tip', (0, RAMP_LEN, 0), size=0.2))
    m[-1].parent = r['ramp']
    m.append(empty('hatch_center', (0, HATCH_Y, HATCH_ZC), size=0.2))
    return m
