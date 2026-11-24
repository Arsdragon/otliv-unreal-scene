# chaika_cockpit_detail.py — доделки кабины после приёмки этапа C (замечание режиссёра 2026-11-20): то, что видно
# с места пилота на ±60–110° (стенки за боковыми окнами и под ними, борта консолей) и потолок над головой:
# жгуты кабелей на хомутах, поручни, сетки для вещей, короб кислородной маски, фонарь, воздуховод, светильники,
# трафаретные таблички. Подключается из chaika_cockpit.py (exec) после chaika_cockpit_station.py.
# Напоминание: +X — левый борт (слева от пилота), −X — правый.


def _prof(y):
    return _half(sec(min(max(y, -6.95), TAIL_Y)), WALL)


def snap(p, off=0.0):
    """Ближайшая к p точка внутренней обшивки в сечении y = p.y, сдвинутая внутрь на off, и внутренняя нормаль."""
    x, y, z = p
    sg = 1.0 if x >= 0 else -1.0
    best = None
    hp = _prof(y)
    for (ax, az), (bx, bz) in zip(hp[:-1], hp[1:]):
        dx, dz = bx - ax, bz - az
        d2 = dx * dx + dz * dz
        f = 0.0 if d2 < 1e-12 else max(0.0, min(1.0, ((abs(x) - ax) * dx + (z - az) * dz) / d2))
        cx, cz = ax + dx * f, az + dz * f
        e = (abs(x) - cx) ** 2 + (z - cz) ** 2
        if d2 > 1e-10 and (best is None or e < best[0]):
            best = (e, cx, cz, dx, dz)
    _, cx, cz, dx, dz = best
    L = math.hypot(dx, dz)
    nx, nz = -dz / L, dx / L
    if nx * (0.0 - cx) + nz * (2.6 - cz) < 0:
        nx, nz = -nx, -nz
    n = Vector((sg * nx, 0.0, nz))
    return Vector((sg * cx, y, cz)) + n * off, n


def wall_M(p, off=0.0, up_hint=None):
    """Местные оси на обшивке: Z — внутрь кабины, Y — вверх по стенке, X — вправо для смотрящего на стенку."""
    q, n = snap(p, off)
    if up_hint is None:
        up = Vector((n.z, 0.0, -n.x))
        if up.z < 0:
            up = -up
    else:
        up = Vector(up_hint) - n * Vector(up_hint).dot(n)
    up.normalize()
    return frame_M(q, up.cross(n), up), n


def y_edge(z):
    """Задняя граница остекления вместе с окантовкой на высоте z: дальше к хвосту — сплошная обшивка."""
    return Y_AFT + RIM - AFT_RAKE * (z - Z_SILL)


def polyline(pts, step):
    """Равномерная выборка по ломаной через точки pts с шагом около step."""
    pts = [Vector(p) for p in pts]
    out = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        k = max(1, int(round((b - a).length / step)))
        out += [a + (b - a) * (i / k) for i in range(1, k + 1)]
    return out


def loom(pts, off=0.05, n=4, r=0.0075, step=0.20, mats=('m_rubber', 'c_plastic', 'm_rubber', 'c_knob'), seed=0.0, tags=()):
    """Жгут кабелей у обшивки: ось — по точкам pts, прижатым к обшивке на off; n кабелей с лёгкой скруткой;
    хомуты с лапкой и винтом через каждые step метров; tags — доли длины, где надеты светлые бирки."""
    C = [snap(p, off) for p in polyline(pts, 0.10)]
    Q, NN = [c[0] for c in C], [c[1] for c in C]
    T = [(Q[min(i + 1, len(Q) - 1)] - Q[max(i - 1, 0)]).normalized() for i in range(len(Q))]
    rb = r * 1.7
    parts = []
    for k in range(n):
        cps = []
        for i in range(len(Q)):
            b = T[i].cross(NN[i]).normalized()
            a = 2 * math.pi * k / n + 0.45 * math.sin(i * 0.37 + k * 1.9 + seed)
            cps.append(Q[i] + NN[i] * (math.cos(a) * rb) + b * (math.sin(a) * rb))
        rk = r * (0.75 + 0.25 * ((k * 5 + int(abs(seed) * 3)) % 3))
        parts.append(pipe('cab', cps, rk, mats[k % len(mats)], sides=8, res=3))
    acc = [0.0]
    for a, b in zip(Q[:-1], Q[1:]):
        acc.append(acc[-1] + (b - a).length)
    nxt = step * 0.5
    for i in range(1, len(Q) - 1):
        if acc[i] + 1e-6 < nxt:
            continue
        nxt += step
        q, nn, t = Q[i], NN[i], T[i]
        parts.append(cyl('clamp', q - t * 0.007, q + t * 0.007, rb + r + 0.003, 12, 'm_steel'))
        parts += place([box('tab', (0.014, off - rb, 0.0025), (0, -(rb + (off - rb) / 2), 0), mat_name='m_steel')], frame_M(q, t, nn))
        parts.append(hexbolt(q - nn * off, nn, 0.009, 0.004))
    for f in tags:
        i = min(len(Q) - 1, max(0, int(f * (len(Q) - 1))))
        parts.append(cyl('tag', Q[i] - T[i] * 0.02, Q[i] + T[i] * 0.02, rb + r + 0.0015, 12, 'c_placard'))
    return parts


def grab_handle(sg, z0, z1, dy=0.04, off=0.062):
    """Поручень на задней стойке бокового окна: штанга с резиновой накладкой и две лапы на винтах."""
    yy = lambda z: y_edge(z) + dy
    zs = [z0 + 0.10, z0 + 0.25, (z0 + z1) / 2, z1 - 0.25, z1 - 0.10]
    f0, f1 = snap((sg * 1.3, yy(z0), z0), 0.006)[0], snap((sg * 1.3, yy(z1), z1), 0.006)[0]
    p = [pipe('hbar', [f0] + [snap((sg * 1.3, yy(z), z), off)[0] for z in zs] + [f1], 0.0125, 'm_alu', sides=10, res=4),
         pipe('hgrip', [snap((sg * 1.3, yy(z), z), off)[0] for z in frange(z0 + 0.14, z1 - 0.14, 0.04)], 0.016, 'm_rubber', sides=10, res=2)]
    for z in (z0, z1):
        M, _ = wall_M((sg * 1.3, yy(z), z), 0.0)
        p += place([box('hfoot', (0.04, 0.05, 0.016), (0, 0, 0.008), bevel=0.004, mat_name='m_steel')] +
                   [cyl('hs', (0, dz, 0.0155), (0, dz, 0.0185), 0.0045, 6, 'm_steel') for dz in (-0.017, 0.017)], M)
    return p


def net_pouch(w, h, bulge=0.04, items=True):
    """Карман с сеткой в местных осях (стенка — плоскость XY, Z — в кабину): подложка, окантовка, резинка сверху,
    сетка с ячейкой 24 мм и вещи внутри."""
    zf = lambda x, y: 0.007 + bulge * max(0.0, math.cos(math.pi * x / w)) ** 0.6 * max(0.0, y / h + 0.5) ** 0.8
    p = [box('back', (w, h, 0.004), (0, 0, 0.002), bevel=0.0015, segs=1, mat_name='c_fabric')]
    for cx, cy, sx, sy in ((0, -h / 2 + 0.008, w, 0.016), (-w / 2 + 0.008, 0, 0.016, h), (w / 2 - 0.008, 0, 0.016, h)):
        p.append(box('edge', (sx, sy, 0.010), (cx, cy, 0.006), bevel=0.003, segs=1, mat_name='c_fabric'))
    p.append(pipe('elastic', [(x, h / 2 - 0.006, zf(x, h / 2 - 0.006)) for x in frange(-w / 2 + 0.008, w / 2 - 0.008, 0.02)],
                  0.0055, 'c_belt', sides=8, res=2))
    nx, ny = max(3, int(w / 0.024)), max(3, int(h / 0.024))
    bm = bmesh.new()
    V = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            x, y = -w / 2 + 0.008 + (w - 0.016) * i / nx, -h / 2 + 0.008 + (h - 0.022) * j / ny
            row.append(bm.verts.new((x, y, zf(x, y))))
        V.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((V[j][i], V[j][i + 1], V[j + 1][i + 1], V[j + 1][i]))
    net = bm_obj(bm, 'net', 'm_rubber', None)
    md = net.modifiers.new('wf', 'WIREFRAME')
    md.thickness = 0.0024
    md.use_even_offset = True
    md.use_boundary = True
    apply_mod(net, md)
    p.append(net)
    if items:
        p += [box('item', (w * 0.62, h * 0.70, 0.016), (w * 0.08, -h * 0.08, 0.013), bevel=0.003, mat_name='c_plastic', rot=(0, 0, 4)),
              box('item2', (w * 0.45, h * 0.55, 0.007), (-w * 0.12, -h * 0.02, 0.0245), bevel=0.002, mat_name='m_white', rot=(0, 0, -6))]
    return p


def placard(PL, M, w, h, lines, border=None):
    """Табличка: пластина Plates с текстом lines = [(y, текст, высота букв, цвет)], border — цвет рамки."""
    pl = PL.add(M, w, h)
    for yy, t, hh, col in lines:
        PL.label(pl, 0, yy, t, hh, color=col, w=min(w - 0.008, len(t) * hh * 0.66))
    if border:
        PL.box(pl, -w / 2 + 0.003, -h / 2 + 0.003, w / 2 - 0.003, h / 2 - 0.003, w=0.0015, color=border)
    return pl


def o2_box(M, PL):
    """Короб аварийной кислородной маски с откидной крышкой и вытяжной петлёй."""
    p = [box('o2', (0.20, 0.15, 0.085), (0, 0, 0.0425), bevel=0.012, segs=2, mat_name='m_white'),
         box('o2seam', (0.203, 0.003, 0.088), (0, -0.040, 0.044), mat_name='c_bezel'),
         cyl('o2hinge', (-0.085, 0.074, 0.083), (0.085, 0.074, 0.083), 0.0055, 8, 'm_steel'),
         box('o2latch', (0.034, 0.010, 0.014), (0, -0.0755, 0.074), bevel=0.003, mat_name='m_steel'),
         pipe('o2pull', [(-0.035, -0.074, 0.050), (-0.035, -0.098, 0.062), (0.035, -0.098, 0.062), (0.035, -0.074, 0.050)], 0.0045,
              'm_orange', sides=6, res=3)]
    p += [hexbolt((sx, sy, 0.085), (0, 0, 1), 0.007, 0.0025) for sx in (-0.088, 0.088) for sy in (-0.062, 0.062)]
    place(p, M)
    placard(PL, M @ Matrix.Translation((0, 0.012, 0.0858)), 0.15, 0.075,
            [(0.018, 'АВАРИЙНЫЙ', 0.0125, 'ink'), (0.0, 'КИСЛОРОД', 0.0125, 'ink'), (-0.022, 'ПОТЯНУТЬ ВНИЗ', 0.009, 'orange')], border='orange')
    return p


def junction_box(M, PL, label):
    """Распределительная коробка у пола, в неё входит жгут."""
    p = [box('jb', (0.10, 0.14, 0.05), (0, 0, 0.025), bevel=0.006, mat_name='c_plastic'),
         box('jbl', (0.094, 0.132, 0.004), (0, 0, 0.051), bevel=0.002, segs=1, mat_name='c_plastic'),
         cyl('jbg', (0, 0.07, 0.025), (0, 0.088, 0.025), 0.019, 12, 'c_knob')]
    p += [hexbolt((sx, sy, 0.053), (0, 0, 1), 0.007, 0.0025) for sx in (-0.039, 0.039) for sy in (-0.058, 0.058)]
    place(p, M)
    placard(PL, M @ Matrix.Translation((0, -0.02, 0.0532)), 0.07, 0.026, [(0, label, 0.011, 'ink')])
    return p


def flashlight(c, ax, m):
    """Фонарь в двух зажимах: центр c, ось ax (к голове), m — направление к поверхности крепления."""
    c, ax, m = Vector(c), Vector(ax).normalized(), Vector(m).normalized()
    p = [cyl('fl_body', c - ax * 0.085, c + ax * 0.05, 0.0165, 14, 'c_knob'),
         cyl('fl_head', c + ax * 0.05, c + ax * 0.095, 0.0175, 14, 'c_knob', r1=0.024),
         cyl('fl_bezel', c + ax * 0.095, c + ax * 0.102, 0.0245, 14, 'm_alu'),
         cyl('fl_lens', c + ax * 0.1015, c + ax * 0.1035, 0.0205, 14, 'm_chrome'),
         cyl('fl_cap', c - ax * 0.096, c - ax * 0.085, 0.0172, 14, 'm_orange'),
         cyl('fl_btn', c - m * 0.0155, c - m * 0.021, 0.006, 8, 'm_rubber')]
    for t in (-0.045, 0.035):
        q = c + ax * t
        p += [cyl('fl_clip', q - ax * 0.006, q + ax * 0.006, 0.0195, 14, 'm_steel'),
              cyl('fl_stud', q + m * 0.017, q + m * 0.028, 0.007, 8, 'm_steel')]
    return p


def reading_lamp(base, n, tgt):
    """Светильник для чтения на шарнире, направлен на консоль (линза не светится — включает сцена)."""
    base, n = Vector(base), Vector(n)
    h = base + n * 0.045
    d = (Vector(tgt) - h).normalized()
    return [cyl('rl_base', base - n * 0.002, base + n * 0.012, 0.03, 16, 'c_frame', bevel=0.003),
            cyl('rl_stem', base + n * 0.01, h, 0.006, 8, 'm_steel'),
            cyl('rl_ball', h - d * 0.012, h + d * 0.012, 0.012, 10, 'm_steel'),
            cyl('rl_body', h - d * 0.03, h + d * 0.03, 0.019, 14, 'c_knob', r1=0.023),
            cyl('rl_lens', h + d * 0.029, h + d * 0.032, 0.0195, 14, 'm_chrome')]


def eyeball_vent(c, n):
    c, n = Vector(c), Vector(n)
    return [cyl('ev_ring', c - n * 0.002, c + n * 0.008, 0.032, 16, 'c_frame', bevel=0.003),
            cyl('ev_ball', c + n * 0.004, c + n * 0.022, 0.024, 14, 'c_knob', bevel=0.007),
            cyl('ev_noz', c + n * 0.018, c + n * 0.034, 0.011, 12, 'c_knob', r1=0.0085)]


def air_duct(y0, y1, w=0.16, h=0.066, off=0.05):
    """Воздуховод по оси потолка под шпангоутами: фланцы на болтах и подвесы-хомуты."""
    sec_ = rrect(w, h, 0.014, 3)
    zc = lambda y: top_z(y, 0, WALL) - off - h / 2
    p = [loft('duct', [[(x, y, zc(y) + z) for x, z in sec_] for y in frange(y0, y1, 0.08)], mat_name='c_frame', smooth=40)]
    fl = rrect(w + 0.016, h + 0.016, 0.02, 3)
    for y in frange(y0 + 0.30, y1 - 0.15, 0.56):
        z0 = zc(y)
        p.append(loft('flange', [[(x, y - 0.012, z0 + z) for x, z in fl], [(x, y + 0.012, z0 + z) for x, z in fl]], mat_name='c_frame', smooth=40))
        p += [hexbolt((sx * (w / 2 + 0.002), y - 0.012, z0 + sz * (h / 2 - 0.006)), (0, -1, 0), 0.007, 0.003) for sx in (-1, 1) for sz in (-1, 1)]
        zt = top_z(y + 0.03, 0, WALL)
        p.append(box('hstrap', (w + 0.04, 0.02, 0.003), (0, y + 0.03, z0 - h / 2 - 0.0015), mat_name='m_steel'))
        p += [box('hang', (0.003, 0.02, zt - (z0 - h / 2)), (sx * (w / 2 + 0.018), y + 0.03, (zt + z0 - h / 2) / 2), mat_name='m_steel')
              for sx in (-1, 1)]
    return p


def build_detail():
    PL = Plates(cls='c_placard', row=0.9)
    side = {1: [], -1: []}
    roof = []
    xo = min(halfwidth(-4.22, 3.08, WALL), halfwidth(BULKHEAD_Y - 0.10, 3.08, WALL)) - 0.03   # наружная стойка левого стеллажа
    for sg in (1, -1):
        o = side[sg]
        o += grab_handle(sg, 2.42, 3.02)
        yc = -4.435 if sg > 0 else -4.38                                 # сетка под окном, между консолью и стеллажом
        M, _ = wall_M((sg * 1.3, yc, 2.00), 0.003)
        o += place(net_pouch(0.21, 0.40), M)
        placard(PL, M @ Matrix.Translation((0, 0.235, 0.002)), 0.19, 0.03,
                [(0, 'ВЕЩИ — НЕ БОЛЕЕ 3 кг' if sg > 0 else 'КАРТЫ, ДОКУМЕНТЫ', 0.010, 'ink')])
        Mc = frame_M((sg * 0.369, -4.98, 1.97), Vector((0, 0, 1)).cross(Vector((-sg, 0, 0))), (0, 0, 1))
        o += place(net_pouch(0.40, 0.26, bulge=0.03), Mc)                # карман на борту консоли со стороны ног
        Mj, _ = wall_M((sg * 1.3, -4.27 if sg > 0 else -4.17, 1.88), 0.0)
        o += junction_box(Mj, PL, 'Ж-14' if sg > 0 else 'Ж-15')
        if sg > 0:
            pts = [(1.3, -4.27, 1.96), (1.3, -4.27, 2.24), (1.3, y_edge(2.55) + 0.10, 2.55), (1.3, y_edge(2.95) + 0.10, 2.95),
                   (1.25, y_edge(3.28) + 0.10, 3.28), (0.95, -4.60, 3.62), (0.60, -4.64, 3.70), (0.21, -4.64, 3.73)]
        else:
            pts = [(-1.3, -4.17, 1.96), (-1.3, -4.17, 2.30), (-1.3, -4.19, 2.80), (-1.3, -4.28, 3.15), (-1.25, y_edge(3.32) + 0.14, 3.32),
                   (-0.95, -4.58, 3.62), (-0.60, -4.64, 3.70), (-0.21, -4.64, 3.73)]
        o += loom(pts, off=0.045, n=4, r=0.0072, step=0.19, seed=1.3 * sg, tags=(0.22, 0.6))
        roof += loom([(sg * 0.18, -4.60, 3.72), (sg * 0.27, -4.46, 3.74), (sg * 0.30, -4.20, 3.75), (sg * 0.30, -3.30, 3.75),
                      (sg * 0.30, -2.40, 3.75)], off=0.056, n=3, r=0.0065, step=0.26, seed=2.1 * sg, tags=(0.35, 0.8))
        Mb, _ = wall_M((sg * 0.19, -4.61, 3.73), 0.0, up_hint=(0, 1, 0))       # ввод жгутов у кормового торца пульта
        roof += place([box('inlet', (0.07, 0.06, 0.045), (0, 0, 0.0225), bevel=0.006, mat_name='c_plastic')], Mb)
        base, nb = snap((sg * 0.30, -4.79, 3.74), 0.0)
        roof += reading_lamp(base, nb, (sg * 0.55, -5.00, 2.30))
    M, _ = wall_M((-1.3, -4.33, 2.62), 0.0)                              # кислородная маска — правый борт за окном
    side[-1] += o2_box(M, PL)
    side[1] += flashlight((xo - 0.38, -4.262, 2.62), (0, 0, -1), (0, 1, 0))   # фонарь — на передней стойке стеллажа слева
    roof += air_duct(-4.58, -2.34)
    for y in (-4.25, -3.30):
        roof += eyeball_vent((0, y, top_z(y, 0, WALL) - 0.05 - 0.066), (0, 0, -1))
    for sg in (1, -1):
        y = -3.85
        Md = frame_M((sg * 0.0805, y, top_z(y, 0, WALL) - 0.05 - 0.033), Vector((0, 0, 1)).cross(Vector((sg, 0, 0))), (0, 0, 1))
        placard(PL, Md, 0.24, 0.032, [(0, 'ВЕНТИЛЯЦИЯ КАБИНЫ', 0.012, 'ink')])
    return [mech(side[1], 'ck_detail_L', atlas='A'), mech(side[-1], 'ck_detail_R', atlas='A'),
            mech(roof, 'ck_detail_roof', atlas='A'), PL.finish('ck_placards', 'A', 5.0)]
