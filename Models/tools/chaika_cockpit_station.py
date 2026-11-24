# chaika_cockpit_station.py — место пилота: приборная панель с пятью экранами, боковые консоли (РУД слева,
# ручка справа), верхний пульт, кресло с ремнями, педали. Подключается из chaika_cockpit.py (exec).
# Лицевые панели — плоские пластины с точной развёрткой (partkit.Plates): на них художник текстур пишет подписи.
PANEL_R, PANEL_AZ, PZ0, PZ1 = 0.80, [-58, -35, -13, 13, 35, 58], 2.30, 2.54
SCREENS = []
REFS = {}


def _pp(a, r, z):
    return Vector((r * math.sin(R(a)), EY - r * math.cos(R(a)), z))


def _lift(M, d=0.0015):
    return Matrix.Translation(M.to_3x3() @ Vector((0, 0, d))) @ M


def screen_unit(P, pl, k, w, h, title, parts, keys=True, ox=0.0):
    """Экран: рамка, сам экран отдельным слотом screen_k (развёртка 0…1), кнопки по бокам, подпись сверху."""
    out_, inn = rrect(w + 0.018, h + 0.018, 0.010, 3), rrect(w, h, 0.004, 3)
    r0 = [(x + ox, y, 0.0) for x, y in out_]
    rings = [r0, [(x + ox, y, 0.007) for x, y in out_], [(x + ox, y, 0.007) for x, y in inn], [(x + ox, y, 0.002) for x, y in inn], r0]
    its = [loft('bez', rings, closed=True, cap0=False, cap1=False, mat_name='c_bezel', smooth=35)]
    if keys:
        for sx in (-1, 1):
            for j in range(5):
                its += button(ox + sx * (w / 2 + 0.021), -0.06 + 0.03 * j, 0.011, 0.011, 'c_knob')
    parts += place(its, pl.M)
    P.label(pl, ox, h / 2 + 0.021, title, 0.0065)
    me = bpy.data.meshes.new('ck_screen_%d' % k)
    me.from_pydata([pl.M @ Vector(p) for p in ((ox - w / 2, -h / 2, 0.0025), (ox + w / 2, -h / 2, 0.0025), (ox + w / 2, h / 2, 0.0025), (ox - w / 2, h / 2, 0.0025))],
                   [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name='UVMap')
    for i, t in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[i].uv = t
    me.materials.append(mat('screen_%d' % k))
    ob = bpy.data.objects.new('ck_screen_%d' % k, me)
    link(ob)
    SCREENS.append(dict(name=ob.name, slot='screen_%d' % k, width=w, height=h, aspect=round(w / h, 3), title=title))
    return ob


def toggle_row(P, pl, parts, y, labels, pitch=0.05, title=None, guard=False, hh=0.0064):
    n = len(labels)
    its = []
    for i, lab in enumerate(labels):
        x = (i - (n - 1) / 2) * pitch
        its += toggle(x, y, up=(i % 3 != 1), guard=guard)
        P.label(pl, x, y - (0.024 if guard else 0.019) - (hh - 0.0064) / 2, lab, hh)
    parts += place(its, pl.M)
    if title:
        w = (n - 1) * pitch / 2 + 0.03
        lift = 2.2 * (hh - 0.0064)                                        # крупные подписи — заголовок выше рычажков
        P.label(pl, 0, y + 0.034 + lift, title, max(0.0065, hh * 1.2))
        P.box(pl, -w, y - 0.034, w, y + 0.046 + lift)


def build_panel(P):
    parts, scr = [], []
    sec_ = lambda a: [_pp(a, PANEL_R - 0.03, PZ0), _pp(a, PANEL_R + 0.05, PZ1), _pp(a, PANEL_R + 0.14, PZ1 - 0.012),
                      _pp(a, PANEL_R + 0.07, PZ0 - 0.02)]
    parts.append(loft('body', [sec_(a) for a in PANEL_AZ], mat_name='c_plastic', smooth=None))
    parts.append(loft('hood', [[_pp(a, PANEL_R - 0.012, PZ1 + 0.014), _pp(a, PANEL_R + 0.155, PZ1 + 0.014),
                                _pp(a, PANEL_R + 0.155, PZ1 - 0.004), _pp(a, PANEL_R - 0.012, PZ1 + 0.002)] for a in PANEL_AZ],
                      mat_name='m_rubber', smooth=None))      # козырёк — матовый чёрный, без бликов
    titles = ['СВЯЗЬ', 'ДВИГАТЕЛИ', 'ПИЛОТАЖ', 'НАВИГАЦИЯ', 'СИСТЕМЫ']        # k = 0 — крайний правый для пилота
    for k in range(5):
        b0, b1 = _pp(PANEL_AZ[k], PANEL_R - 0.03, PZ0), _pp(PANEL_AZ[k + 1], PANEL_R - 0.03, PZ0)
        t0, t1 = _pp(PANEL_AZ[k], PANEL_R + 0.05, PZ1), _pp(PANEL_AZ[k + 1], PANEL_R + 0.05, PZ1)
        M = _lift(frame_M((b0 + b1 + t0 + t1) / 4, b0 - b1, (t0 + t1) / 2 - (b0 + b1) / 2))
        wf = (b1 - b0).length - 0.004
        pl = P.add(M, wf, 0.25)
        w, h = (0.30, 0.1875) if k == 2 else (0.248, 0.155)
        scr.append(screen_unit(P, pl, 5 - k, w, h, titles[k], parts))
        parts += place([hexbolt((sx * (wf / 2 - 0.008), sy * 0.117, 0), (0, 0, 1), 0.007, 0.002) for sx in (-1, 1) for sy in (-1, 1)], M)
    return parts, scr


def build_console(P, s):
    """Боковая консоль: s = +1 — слева от пилота (РУД), s = −1 — справа (ручка управления)."""
    parts, moving = [], []
    xi = 0.37
    rings = []
    for y in frange(Y_CHIN_AFT, -4.55, 0.1):
        xw = lambda z: max(1.0, halfwidth(y, z, WALL) + 0.02)
        rings.append([(s * xi, y, FLOOR_Z), (s * xi, y, 2.27), (s * (xi + 0.03), y, 2.30), (s * 0.74, y, 2.30), (s * 0.98, y, 2.42),
                      (s * xw(2.42), y, 2.42), (s * xw(2.0), y, 2.0), (s * max(xi + 0.05, halfwidth(y, FLOOR_Z, WALL)), y, FLOOR_Z)])
    parts.append(loft('con', rings, mat_name='c_plastic', smooth=30))
    parts.append(prism('horn', [(Y_CHIN_AFT + 0.02, 2.30), (Y_CHIN_AFT + 0.02, 2.08), (-5.60, 2.16), (-5.74, 2.24), (-5.74, 2.30)],
                       s * xi, s * 0.72, 'X', bevel=0.015, mat_name='c_plastic'))
    M = _lift(frame_M((s * 0.555, -5.00, 2.30), (-1, 0, 0), (0, -1, 0)))       # верх консоли: X — вправо для пилота, Y — вперёд
    pl = P.add(M, 0.36, 0.86)
    qx, qy = s * 0.075, 0.27                                                    # ближе к креслу
    if s > 0:
        parts += place([box('quad', (0.12, 0.24, 0.014), (qx, qy, 0.007), bevel=0.004, mat_name='m_alu'),
                        box('slot', (0.022, 0.19, 0.004), (qx, qy, 0.0145), mat_name='c_bezel')], M)
        for yy, t in ((0.19, 'МАЛЫЙ ГАЗ'), (0.27, 'НОМИНАЛ'), (0.35, 'ВЗЛЁТ')):
            P.label(pl, qx - 0.105, yy, t, 0.0064)
            P.line(pl, qx - 0.064, yy, qx - 0.052, yy)
        P.label(pl, qx, 0.405, 'РУД', 0.008)
        lev = place([cyl('sh', (qx, qy, -0.02), (qx, qy - 0.04, 0.105), 0.006, 10, 'm_steel'),
                     cyl('tb', (qx - 0.046, qy - 0.042, 0.112), (qx + 0.046, qy - 0.042, 0.112), 0.016, 16, 'c_knob', bevel=0.004),
                     cyl('btn', (qx + 0.046, qy - 0.042, 0.112), (qx + 0.052, qy - 0.042, 0.112), 0.007, 10, 'm_orange')], M)
        moving.append(mech(lev, 'ck_throttle', origin=M @ Vector((qx, qy, -0.02)), atlas='A'))
        toggle_row(P, pl, parts, 0.03, ['ПУСК Л', 'ПУСК П', 'КОРМ 1', 'КОРМ 2', 'ПРОДУВ', 'ЗАЖИГ'], title='ДВИГАТЕЛИ')
        kn = []
        for x, t in ((-0.07, 'ПОДСВЕТКА'), (0.07, 'КАБИНА')):
            kn += knob(x, -0.12)
            P.label(pl, x, -0.148, t, 0.0064)
        P.label(pl, 0, -0.085, 'ОСВЕЩЕНИЕ', 0.0065)
        for c in range(3):
            for r_ in range(4):
                kn += button(-0.02 + 0.02 * c, -0.345 + 0.02 * r_, 0.014, 0.014)
        P.label(pl, 0, -0.245, 'СВЯЗЬ', 0.0065)
        P.box(pl, -0.045, -0.365, 0.045, -0.262)
        parts += place(kn, M)
    else:
        parts += place([cyl('ring', (qx, qy, 0), (qx, qy, 0.012), 0.047, 20, 'm_alu', bevel=0.003),
                        revolve('boot', [(0.040, 0.0), (0.044, 0.006), (0.036, 0.012), (0.040, 0.018), (0.030, 0.024), (0.034, 0.030),
                                         (0.022, 0.038), (0.0, 0.038)], 20, 'Z', (qx, qy, 0.012), 'm_rubber'),
                        box('armbase', (0.14, 0.25, 0.012), (qx, 0.02, 0.006), bevel=0.004, mat_name='c_plastic'),
                        box('armpad', (0.13, 0.24, 0.03), (qx, 0.02, 0.026), bevel=0.012, segs=3, mat_name='c_fabric')], M)
        P.label(pl, qx, 0.405, 'УПРАВЛЕНИЕ', 0.008)
        grip = []
        for i, (z, a, b) in enumerate(((0.070, 0.019, 0.022), (0.100, 0.021, 0.025), (0.130, 0.022, 0.026), (0.160, 0.023, 0.027), (0.186, 0.019, 0.021))):
            grip.append([(qx + a * math.cos(2 * math.pi * j / 16), qy + 0.012 + 0.006 * i + b * math.sin(2 * math.pi * j / 16), z) for j in range(16)])
        st = place([cyl('sh', (qx, qy, 0.03), (qx, qy + 0.012, 0.078), 0.011, 12, 'm_steel'),
                    loft('grip', grip, mat_name='c_knob', smooth=40),
                    box('head', (0.048, 0.046, 0.03), (qx, qy + 0.04, 0.198), bevel=0.011, mat_name='c_knob'),
                    cyl('hat', (qx, qy + 0.04, 0.212), (qx, qy + 0.04, 0.224), 0.007, 10, 'c_plastic'),
                    cyl('rb', (qx - 0.016, qy + 0.05, 0.212), (qx - 0.016, qy + 0.05, 0.218), 0.005, 8, 'm_orange'),
                    box('trig', (0.008, 0.012, 0.03), (qx, qy + 0.062, 0.165), bevel=0.003, mat_name='c_plastic')], M)
        moving.append(mech(st, 'ck_stick', origin=M @ Vector((qx, qy, 0.03)), atlas='A'))
        toggle_row(P, pl, parts, -0.19, ['ШАССИ', 'ТРАП', 'ШЛЮЗ', 'ФАРЫ', 'АНО', 'ДРОН'], title='СИСТЕМЫ')
        toggle_row(P, pl, parts, -0.335, ['АВАР ПИТ', 'СБРОС', 'ПОЖАР'], pitch=0.08, guard=True)
    # наклонная панель автоматов защиты у борта
    M2 = _lift(frame_M((s * 0.86, -5.00, 2.36), (0, -s, 0), (s * 0.24, 0, 0.12)))
    p2 = P.add(M2, 0.84, 0.25)
    cb = []
    for r_, yy in enumerate((-0.075, -0.015, 0.045)):
        for i in range(13):
            cb += breaker(-0.36 + 0.06 * i, yy)
        P.label(p2, -0.398, yy, 'АБВ'[r_], 0.007)
    parts += place(cb, M2)
    P.label(p2, 0, 0.10, 'АВТОМАТЫ ЗАЩИТЫ — ' + ('ЛЕВЫЙ БОРТ' if s > 0 else 'ПРАВЫЙ БОРТ'), 0.0075)
    P.line(p2, -0.40, 0.083, 0.40, 0.083)
    for i in range(13):
        P.label(p2, -0.36 + 0.06 * i, -0.108, '%02d' % (i + 1), 0.0052)
    return parts, moving


def build_overhead(P):
    y0, y1 = -5.28, -4.62
    z0, z1 = top_z(y0, 0, WALL) - 0.075, top_z(y1, 0, WALL) - 0.075
    ang = math.atan2(z1 - z0, y1 - y0)
    Ln = math.hypot(y1 - y0, z1 - z0)
    c = Vector((0, (y0 + y1) / 2, (z0 + z1) / 2))
    Yv = Vector((0, math.cos(ang), math.sin(ang)))                              # вдоль пульта к хвосту
    M = frame_M(c, (-1, 0, 0), Yv)                                              # Z — вниз, к пилоту
    parts = place([box('ovh', (0.30, Ln, 0.06), (0, 0, 0.03 - 0.06), bevel=0.012, mat_name='c_frame')], M)   # корпус светлый
    Mp = _lift(M, 0.0015)
    pl = P.add(Mp, 0.28, Ln - 0.03)
    rows = (['АКК 1', 'АКК 2', 'ГЕН Л', 'ГЕН П', 'ШИНА А', 'ШИНА Б'], ['НАСОС 1', 'НАСОС 2', 'ГИДРО', 'ОБОГРЕВ', 'ВЕНТ', 'НАДДУВ'],
            ['САУ', 'НАВИГ', 'РАДИО', 'ОТВЕТЧ', 'ЗАПИСЬ', 'ТЕСТ'])
    for r_, labs in enumerate(rows):
        toggle_row(P, pl, parts, 0.17 - 0.115 * r_, labs, pitch=0.042, title=('ПИТАНИЕ', 'СИСТЕМЫ', 'АВИОНИКА')[r_], hh=0.0085)
    toggle_row(P, pl, parts, -0.215, ['ПОЖАР Л', 'ПОЖАР П'], pitch=0.09, guard=True, hh=0.0085)
    its = []
    for i in range(4):
        x = -0.075 + 0.05 * i
        its += [box('anf', (0.03, 0.016, 0.004), (x, 0.262, 0.002), mat_name='c_bezel'), box('an', (0.024, 0.011, 0.0025), (x, 0.262, 0.005), mat_name='emissive')]
    for sx in (-0.12, 0.12):
        its.append(pipe('hd', [(sx, -0.28, 0), (sx, -0.27, 0.03), (sx, -0.19, 0.03), (sx, -0.18, 0)], 0.005, 'm_alu', sides=6, res=3))
    parts += place(its, Mp)
    return parts


def build_seat():
    top = EZ - 0.79                                                              # верх подушки
    y = EY
    p = []
    for sx in (-0.17, 0.17):
        p.append(box('rail', (0.045, 0.95, 0.03), (sx, y + 0.15, FLOOR_Z + 0.015), bevel=0.004, mat_name='m_alu'))
        for sy in (-0.12, 0.30):
            p.append(cyl('leg', (sx, y + sy, FLOOR_Z + 0.07), (sx * 0.9, y + sy * 0.9 + 0.01, top - 0.11), 0.022, 12, 'm_steel'))
    p += [box('base', (0.40, 0.50, 0.05), (0, y + 0.10, FLOOR_Z + 0.055), bevel=0.01, mat_name='m_dark'),
          cyl('damp', (0, y + 0.32, FLOOR_Z + 0.08), (0, y + 0.20, top - 0.10), 0.03, 14, 'm_orange', bevel=0.006),
          box('pan_shell', (0.52, 0.52, 0.05), (0, y - 0.06, top - 0.105), bevel=0.02, mat_name='c_plastic'),
          box('pan', (0.48, 0.48, 0.085), (0, y - 0.07, top - 0.043), bevel=0.035, segs=3, mat_name='c_fabric'),
          box('back_shell', (0.52, 0.05, 0.88), (0, y + 0.325, top + 0.39), bevel=0.02, mat_name='c_plastic', rot=(-9, 0, 0)),
          box('back', (0.42, 0.08, 0.66), (0, y + 0.27, top + 0.36), bevel=0.03, segs=3, mat_name='c_fabric', rot=(-9, 0, 0)),
          box('head', (0.27, 0.10, 0.21), (0, y + 0.255, EZ + 0.03), bevel=0.04, segs=3, mat_name='c_fabric'),
          cyl('buckle', (0, y - 0.06, top + 0.004), (0, y - 0.06, top + 0.024), 0.036, 18, 'm_alu', bevel=0.004),
          cyl('bbtn', (0, y - 0.06, top + 0.024), (0, y - 0.06, top + 0.029), 0.018, 14, 'm_orange'),
          box('crotch', (0.045, 0.20, 0.007), (0, y - 0.18, top + 0.004), mat_name='c_belt'),
          box('lever', (0.02, 0.14, 0.02), (0.275, y - 0.12, top - 0.11), bevel=0.006, mat_name='m_orange')]
    for sx in (-1, 1):
        p += [box('bolster', (0.06, 0.42, 0.11), (sx * 0.245, y - 0.06, top - 0.02), bevel=0.028, mat_name='c_fabric'),
              box('bbol', (0.07, 0.11, 0.52), (sx * 0.235, y + 0.265, top + 0.33), bevel=0.03, mat_name='c_fabric', rot=(-9, 0, 0)),
              cyl('hpost', (sx * 0.07, y + 0.30, top + 0.76), (sx * 0.07, y + 0.275, EZ - 0.04), 0.008, 8, 'm_steel'),
              box('sbelt', (0.045, 0.007, 0.62), (sx * 0.105, y + 0.222, top + 0.40), mat_name='c_belt', rot=(-9, 0, 0)),
              box('lbelt', (0.20, 0.045, 0.007), (sx * 0.135, y - 0.045, top + 0.004), mat_name='c_belt', rot=(0, 0, -sx * 9)),
              box('reel', (0.07, 0.06, 0.05), (sx * 0.105, y + 0.345, top + 0.80), bevel=0.012, mat_name='m_dark')]
    return mech(p, 'ck_seat', atlas='A')


def build_pedals():
    kb = [(yy, bottom_z(yy, 0, WALL)) for yy in frange(-6.62, Y_CHIN_AFT, 0.13)]
    p = [prism('keel', [(yy, z - 0.03) for yy, z in kb] + [(yy, z + 0.06) for yy, z in reversed(kb)], -X_KEEL, X_KEEL, 'X', mat_name='c_frame')]
    zb = bottom_z(-6.10, 0, WALL) + 0.06
    zh = bottom_z(-5.85, 0, WALL) + 0.063
    for sx in (-0.12, 0.12):
        p += [box('pedal', (0.11, 0.022, 0.16), (sx, -6.13, zb + 0.17), bevel=0.006, mat_name='m_alu', rot=(28, 0, 0)),
              cyl('arm', (sx, -6.10, zb), (sx, -6.115, zb + 0.11), 0.014, 8, 'm_steel'),
              box('heel', (0.12, 0.26, 0.008), (sx, -5.85, zh), mat_name='m_tread', rot=(math.degrees(math.atan2(bottom_z(-5.72, 0, WALL) - bottom_z(-5.98, 0, WALL), 0.26)), 0, 0))]
        for dz in (-0.05, 0.0, 0.05):
            p.append(box('pgrip', (0.10, 0.006, 0.012), (sx, -6.13 - 0.012 + dz * 0.47, zb + 0.17 + dz * 0.88 + 0.006), mat_name='m_rubber', rot=(28, 0, 0)))
    return mech(p, 'ck_pedals', atlas='A')


def build_station():
    SCREENS.clear()
    P = Plates()
    objs = []
    parts, scr = build_panel(P)
    objs += scr + [mech(parts, 'ck_panel', atlas='A')]
    for s, nm in ((1, 'L'), (-1, 'R')):
        parts, mv = build_console(P, s)
        objs += [mech(parts, 'ck_console_' + nm, atlas='A')] + mv
    PO = Plates(cls='c_panel_lt', row=0.6, glow=True)                       # верхний пульт: светлая панель, подсветка надписей
    objs.append(mech(build_overhead(PO), 'ck_overhead', atlas='A'))
    objs.append(PO.finish('ck_faceplates_overhead', 'A', 6.0))
    objs.append(P.finish('ck_faceplates', 'A', 4.0))
    objs += [build_seat(), build_pedals()]
    return objs
