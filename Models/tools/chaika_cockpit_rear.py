# chaika_cockpit_rear.py — задняя часть кабины (стойки оборудования, откидное кресло, переборка с дверью) и шлюз
# (скафандры, скамья, ложемент дрона, шкафы, пульт с экраном, задняя стенка с проёмом люка). Подключается из chaika_cockpit.py.
DOOR_ZC = FLOOR_Z + 0.93
HATCH_ZC = FLOOR_Z + 0.88


def avionics_box(xc, y0, y1, z0, h, sg, depth=0.36):
    """Блок в стойке у борта sg; лицевая панель смотрит к оси кабины."""
    xf = xc - sg * depth / 2
    ym = (y0 + y1) / 2
    p = [box('unit', (depth, y1 - y0 - 0.02, h - 0.02), (xc, ym, z0 + h / 2), bevel=0.006, mat_name='m_dark'),
         box('face', (0.006, y1 - y0 - 0.035, h - 0.035), (xf - sg * 0.003, ym, z0 + h / 2), bevel=0.002, segs=1, mat_name='c_plastic'),
         box('led', (0.004, 0.012, 0.006), (xf - sg * 0.007, y0 + 0.09, z0 + h - 0.035), mat_name='emissive'),
         box('plc', (0.003, 0.07, 0.018), (xf - sg * 0.007, y1 - 0.11, z0 + h - 0.04), mat_name='c_placard')]
    for yy in (y0 + 0.05, y1 - 0.05):
        p.append(pipe('h', [(xf, yy, z0 + 0.04), (xf - sg * 0.035, yy, z0 + 0.05), (xf - sg * 0.035, yy, z0 + h - 0.05), (xf, yy, z0 + h - 0.04)],
                      0.005, 'm_alu', sides=6, res=3))
    for dy in (-0.07, 0.03):
        p.append(cyl('conn', (xf, ym + dy, z0 + h * 0.4), (xf - sg * 0.022, ym + dy, z0 + h * 0.4), 0.013, 10, 'm_steel'))
    for sy in (y0 + 0.025, y1 - 0.025):
        for zz in (z0 + 0.025, z0 + h - 0.025):
            p.append(hexbolt((xf - sg * 0.006, sy, zz), (-sg, 0, 0), 0.009, 0.003))
    return p


def rack(sg, ya, yb):
    zt = 3.08
    xo = min(halfwidth(ya, zt, WALL), halfwidth(yb, zt, WALL)) - 0.03
    xc = sg * (xo - 0.19)
    p = []
    for dx in (-0.19, 0.19):
        for yy in (ya, yb):
            p.append(box('post', (0.03, 0.03, zt - FLOOR_Z), (xc + dx, yy, (zt + FLOOR_Z) / 2), bevel=0.004, mat_name='c_frame'))
    z = FLOOR_Z + 0.05
    for h in (0.22, 0.30, 0.18, 0.26, 0.20, 0.22):
        if z + h > zt:
            break
        p += avionics_box(xc, ya + 0.03, yb - 0.03, z, h, sg)
        z += h + 0.012
    ym = (ya + yb) / 2
    for dy in (-0.15, 0.2):
        xr = xc * 0.86
        p.append(pipe('loom', [(xc, ym + dy, zt - 0.03), (xc, ym + dy, zt + 0.10), (xr, ym + dy + 0.06, top_z(ym, xr, WALL) - 0.03)], 0.017,
                      'm_rubber', sides=8, res=4))
        p.append(cyl('lclamp', (xc, ym + dy, zt + 0.02), (xc, ym + dy, zt + 0.05), 0.022, 10, 'm_steel'))
    return p


def door_parts(y, zc, sgx):
    """Дверь в шлюз: петли на стороне sgx, открывается в шлюз."""
    p = [prism('door', [(x, zc + z) for x, z in rrect(0.82, 1.84, 0.10)], y - 0.02, y + 0.022, 'Y', bevel=0.008, mat_name='m_white'),
         prism('dpan', [(x, zc + z - 0.45) for x, z in rrect(0.62, 0.74, 0.06)], y - 0.028, y + 0.030, 'Y', bevel=0.004, mat_name='m_white'),
         revolve('port', [(0.13, -0.034), (0.17, -0.034), (0.17, 0.036), (0.13, 0.036)], 28, 'Y', (0, y, zc + 0.42), 'm_alu', closed=True, cap=False),
         cyl('pglass', (0, y - 0.006, zc + 0.42), (0, y + 0.006, zc + 0.42), 0.132, 28, 'glass')]
    p += bolt_circle((0, y - 0.034, zc + 0.42), (0, -1, 0), 0.15, 10, 0.012, 0.005)
    for sy in (-1, 1):                                                           # рукоятка с обеих сторон
        yy = y + sy * 0.03
        p += [cyl('hb', (-sgx * 0.30, yy, zc - 0.05), (-sgx * 0.30, yy + sy * 0.03, zc - 0.05), 0.022, 12, 'm_alu'),
              box('hl', (0.16, 0.016, 0.028), (-sgx * 0.24, yy + sy * 0.034, zc - 0.05), bevel=0.006, mat_name='m_orange')]
    for dz in (-0.6, 0.6):
        p.append(box('hinge', (0.07, 0.05, 0.14), (sgx * 0.405, y, zc + dz), bevel=0.01, mat_name='m_steel'))
    return p


def build_rear_cockpit():
    objs, p = [], []
    p += rack(1, -4.22, BULKHEAD_Y - 0.10) + rack(-1, -3.22, BULKHEAD_Y - 0.10)
    # откидное кресло на правом борту (сложено к стенке)
    xw = halfwidth(-3.78, 2.3, WALL)
    p += [box('jback', (0.05, 0.46, 0.62), (-(xw - 0.06), -3.78, 2.36), bevel=0.012, mat_name='c_plastic'),
          box('jpan', (0.07, 0.42, 0.40), (-(xw - 0.125), -3.78, 2.28), bevel=0.02, segs=3, mat_name='c_fabric'),
          cyl('jhinge', (-(xw - 0.10), -4.0, 2.06), (-(xw - 0.10), -3.56, 2.06), 0.014, 10, 'm_steel'),
          box('jstrap', (0.012, 0.04, 0.30), (-(xw - 0.165), -3.78, 2.30), mat_name='m_orange')]
    for zz in (2.50, 2.20):
        p.append(box('jbelt', (0.008, 0.38, 0.04), (-(xw - 0.165), -3.78, zz), mat_name='c_belt'))
    # огнетушитель и аптечка на переборке, поручни и светильники на потолке
    by = BULKHEAD_Y - 0.04
    p += [cyl('ext', (0.66, by - 0.07, 1.98), (0.66, by - 0.07, 2.30), 0.055, 16, 'm_orange', bevel=0.012),
          cyl('extn', (0.66, by - 0.07, 2.30), (0.66, by - 0.07, 2.36), 0.02, 10, 'm_steel'),
          box('extb', (0.14, 0.02, 0.05), (0.66, by - 0.012, 2.14), bevel=0.005, mat_name='m_steel'),
          box('med', (0.26, 0.09, 0.20), (-0.66, by - 0.05, 2.75), bevel=0.012, mat_name='m_white'),
          box('medc', (0.10, 0.004, 0.03), (-0.66, by - 0.097, 2.75), mat_name='m_orange'),
          box('medc2', (0.03, 0.004, 0.10), (-0.66, by - 0.097, 2.75), mat_name='m_orange')]
    for sg in (1, -1):
        zl = top_z(-3.4, 0.5, WALL)
        p += [box('lampb', (0.10, 1.50, 0.02), (sg * 0.5, -3.40, zl - 0.012), bevel=0.005, mat_name='m_dark'),
              box('lamp', (0.07, 1.42, 0.008), (sg * 0.5, -3.40, zl - 0.026), mat_name='emissive')]
        zg = top_z(-2.75, 0.22, WALL)
        p.append(pipe('grab', [(sg * 0.22, -2.95, zg - 0.005), (sg * 0.22, -2.92, zg - 0.07), (sg * 0.22, -2.58, zg - 0.07), (sg * 0.22, -2.55, zg - 0.005)],
                      0.013, 'm_orange', sides=8, res=4))
    objs.append(mech(p, 'ck_rear_cockpit', atlas='B', dens=0.9))
    # переборка, рама двери, дверь
    bulk = section_wall('bulk', BULKHEAD_Y, [(-0.42, 0.42, FLOOR_Z, FLOOR_Z + 1.86)], 0.07, 'c_frame')
    fr = frame_loop(rrect(1.00, 2.02, 0.16, 5), rrect(0.84, 1.86, 0.10, 5), BULKHEAD_Y - 0.045, BULKHEAD_Y + 0.045, DOOR_ZC)
    fb = [hexbolt((x, BULKHEAD_Y - 0.045, DOOR_ZC + z), (0, -1, 0), 0.016, 0.007) for x, z in rrect(0.92, 1.94, 0.13, 3)]
    objs.append(mech([bulk, fr] + fb, 'ck_bulkhead', atlas='B', dens=0.8))
    door = mech(door_parts(BULKHEAD_Y, DOOR_ZC, 1), 'ck_door', origin=(0.405, BULKHEAD_Y, DOOR_ZC), atlas='B')
    REFS['door'] = door
    objs.append(door)
    return objs


def suit(xc, yc, z0, sg):
    """Скафандр на стойке у борта sg, лицом к оси шлюза."""
    f = -sg
    p = [box('torso', (0.26, 0.48, 0.56), (xc, yc, z0 + 1.18), bevel=0.09, segs=3, mat_name='c_suit'),
         box('pack', (0.16, 0.40, 0.58), (xc + sg * 0.20, yc, z0 + 1.22), bevel=0.03, mat_name='m_white'),
         box('chest', (0.05, 0.22, 0.16), (xc + f * 0.145, yc, z0 + 1.22), bevel=0.012, mat_name='c_plastic'),
         torus('neck', (xc, yc, z0 + 1.49), 0.125, 0.016, 'Z', 'm_alu', 24),
         torus('waist', (xc, yc, z0 + 0.92), 0.20, 0.02, 'Z', 'm_alu', 24),
         revolve('helm', [(0.118, 0.0), (0.165, 0.06), (0.175, 0.15), (0.15, 0.25), (0.09, 0.31), (0.0, 0.33)], 24, 'Z',
                 (xc, yc, z0 + 1.50), 'c_suit'),
         revolve('visor', [(0.0, -0.115), (0.07, -0.095), (0.115, -0.04), (0.125, 0.02), (0.10, 0.08), (0.05, 0.115), (0.0, 0.125)], 20, 'Z',
                 (xc + f * 0.075, yc, z0 + 1.665), 'c_bezel'),
         box('plc', (0.004, 0.10, 0.03), (xc + f * 0.172, yc - 0.04, z0 + 1.27), mat_name='c_placard')]
    for k in range(3):
        p.append(cyl('cb', (xc + f * 0.17, yc - 0.06 + 0.06 * k, z0 + 1.19), (xc + f * 0.182, yc - 0.06 + 0.06 * k, z0 + 1.19), 0.012, 10,
                     'm_orange' if k == 1 else 'c_knob'))
    for sy in (-1, 1):
        sh, hd = Vector((xc, yc + sy * 0.30, z0 + 1.38)), Vector((xc + f * 0.05, yc + sy * 0.34, z0 + 0.84))
        p += [cyl('arm', sh, hd, 0.068, 16, 'c_suit', bevel=0.02),
              torus('elbow', (sh + hd) / 2, 0.072, 0.012, 'Z', 'm_alu', 18),
              box('glove', (0.10, 0.11, 0.17), hd + Vector((0, 0, -0.08)), bevel=0.035, mat_name='c_fabric'),
              cyl('leg', (xc, yc + sy * 0.12, z0 + 0.92), (xc, yc + sy * 0.13, z0 + 0.15), 0.088, 16, 'c_suit', bevel=0.02),
              torus('knee', (xc, yc + sy * 0.125, z0 + 0.52), 0.092, 0.012, 'Z', 'm_alu', 18),
              box('boot', (0.28, 0.14, 0.13), (xc + f * 0.04, yc + sy * 0.13, z0 + 0.075), bevel=0.035, mat_name='c_plastic')]
    p.append(torus('band', (xc, yc + 0.31, z0 + 1.20), 0.073, 0.011, 'Z', 'm_orange', 18))
    # стойка: две трубы, перекладина с крюком, подножка
    xb = xc + sg * 0.30
    for sy in (-0.30, 0.30):
        p.append(cyl('rpost', (xb, yc + sy, z0), (xb, yc + sy, z0 + 1.72), 0.016, 10, 'c_frame'))
    p += [cyl('rbar', (xb, yc - 0.30, z0 + 1.70), (xb, yc + 0.30, z0 + 1.70), 0.016, 10, 'c_frame'),
          box('rfoot', (0.36, 0.66, 0.02), (xc + sg * 0.12, yc, z0 + 0.012), bevel=0.004, mat_name='m_tread'),
          box('rhook', (0.14, 0.05, 0.04), (xc + sg * 0.24, yc, z0 + 1.52), bevel=0.01, mat_name='m_steel')]
    return p


def build_airlock():
    global SCR6
    objs, z0 = [], FLOOR_Z
    ya, yb = BULKHEAD_Y + 0.04, HATCH_Y - 0.06
    # ---- силовой набор, пол, задняя стенка с проёмом люка
    p = floor_plates(ya, yb) + [rib(y) for y in (-1.27, -0.30, 0.62, 1.52)]
    for sg in (1, -1):
        p.append(stringer(lambda y: sec(y)['zs'] - 0.30, ya, yb, sg))
    p.append(section_wall('aft', HATCH_Y - 0.03, [(-0.45, 0.45, z0 + 0.02, z0 + 1.74)], 0.05, 'c_frame'))
    p.append(frame_loop(rrect(1.12, 1.94, 0.22, 6), rrect(0.93, 1.75, 0.155, 6), HATCH_Y - 0.085, HATCH_Y - 0.02, HATCH_ZC))
    p += [hexbolt((x, HATCH_Y - 0.085, HATCH_ZC + z), (0, -1, 0), 0.02, 0.008) for x, z in rrect(1.025, 1.845, 0.19, 4)]
    for sx, sy in ((-0.5, -1.2), (0.5, -1.2), (-0.5, 0.9), (0.5, 0.9)):
        p.append(torus('tie', (sx, sy, z0 + 0.012), 0.035, 0.007, 'Z', 'm_steel', 16))
    objs.append(mech(p, 'ck_structure_airlock', atlas='B', dens=0.85))
    hp = mech([prism('hproxy', [(x, HATCH_ZC + z) for x, z in rrect(0.90, 1.72, 0.14)], HATCH_Y - 0.02, HATCH_Y - 0.005, 'Y', bevel=0.004,
                     mat_name='m_white')], 'ck_hatch_proxy', atlas='B', dens=0.6)
    objs.append(hp)
    # ---- скафандры (левый борт, +X)
    p = []
    for yc in (-1.72, -0.86):
        xw = halfwidth(yc, z0 + 1.65, WALL) - 0.05
        p += suit(xw - 0.42, yc, z0, 1)
    objs.append(mech(p, 'ck_suits', atlas='B'))
    # ---- оборудование шлюза
    p = []
    xw = halfwidth(0.8, z0 + 0.5, WALL) - 0.03                                  # скамья с рундуками (левый борт)
    p += [box('bench', (0.44, 1.30, 0.05), (xw - 0.22, 0.80, z0 + 0.445), bevel=0.012, mat_name='c_plastic'),
          box('cush', (0.40, 1.24, 0.05), (xw - 0.22, 0.80, z0 + 0.49), bevel=0.02, segs=3, mat_name='c_fabric')]
    for yy in (0.48, 1.12):
        p += [box('bin', (0.40, 0.60, 0.38), (xw - 0.22, yy, z0 + 0.21), bevel=0.012, mat_name='m_white'),
              box('binh', (0.02, 0.16, 0.025), (xw - 0.43, yy, z0 + 0.30), bevel=0.006, mat_name='m_alu')]
    yc = -1.45                                                                   # ложемент дрона (правый борт, −X)
    xw = halfwidth(yc, z0 + 1.35, WALL) - 0.04
    p += [box('cr_plate', (0.04, 0.74, 0.62), (-(xw - 0.02), yc, z0 + 1.02), bevel=0.01, mat_name='m_dark'),
          box('cr_conn', (0.06, 0.10, 0.08), (-(xw - 0.07), yc, z0 + 1.12), bevel=0.01, mat_name='m_alu'),
          box('cr_plc', (0.004, 0.20, 0.05), (-(xw - 0.042), yc, z0 + 1.27), mat_name='c_placard')]
    for sy in (-0.24, 0.24):
        p += [box('cr_arm', (0.36, 0.07, 0.05), (-(xw - 0.20), yc + sy, z0 + 0.93), bevel=0.012, mat_name='m_alu'),
              box('cr_pad', (0.30, 0.06, 0.015), (-(xw - 0.21), yc + sy, z0 + 0.962), bevel=0.005, mat_name='m_rubber'),
              pipe('cr_clamp', [(-(xw - 0.12), yc + sy, z0 + 0.96), (-(xw - 0.12), yc + sy, z0 + 1.10), (-(xw - 0.30), yc + sy, z0 + 1.10),
                                (-(xw - 0.30), yc + sy, z0 + 1.04)], 0.012, 'm_steel', sides=8, res=4),
              box('cr_latch', (0.03, 0.03, 0.10), (-(xw - 0.33), yc + sy, z0 + 1.0), bevel=0.008, mat_name='m_orange')]
    REFS['cradle'] = (-(xw - 0.22), yc, z0 + 1.045)
    xw = halfwidth(-0.1, z0 + 1.52, WALL) - 0.03                                 # шкафы (правый борт)
    p.append(box('lockers', (0.40, 1.35, 1.50), (-(xw - 0.20), -0.08, z0 + 0.75), bevel=0.012, mat_name='m_white'))
    for k in range(3):
        yy = -0.08 + (k - 1) * 0.445
        p += [box('ldoor', (0.012, 0.425, 1.42), (-(xw - 0.405), yy, z0 + 0.75), bevel=0.004, segs=1, mat_name='m_white'),
              box('lhandle', (0.02, 0.03, 0.14), (-(xw - 0.42), yy + 0.16, z0 + 0.85), bevel=0.006, mat_name='m_alu')]
        for j in range(4):
            p.append(box('lvent', (0.004, 0.22, 0.012), (-(xw - 0.412), yy, z0 + 1.28 + 0.03 * j), mat_name='c_bezel'))
    xw = halfwidth(1.3, z0 + 1.27, WALL) - 0.03                                  # пульт шлюза (правый борт, у люка)
    p.append(prism('pult', [(-xw, z0), (-(xw - 0.36), z0), (-(xw - 0.36), z0 + 0.95), (-(xw - 0.20), z0 + 1.25), (-xw, z0 + 1.25)],
                   0.95, 1.65, 'Y', bevel=0.012, mat_name='c_plastic'))
    PB = Plates(row=0.8)                                                         # лицевая панель пульта
    A_, B_ = Vector((-(xw - 0.36), 1.30, z0 + 0.95)), Vector((-(xw - 0.20), 1.30, z0 + 1.25))
    M = _lift(frame_M((A_ + B_) / 2, (0, 1, 0), B_ - A_))
    pl = PB.add(M, 0.66, 0.33)
    SCR6 = screen_unit(PB, pl, 6, 0.336, 0.21, 'ШЛЮЗ', p, keys=False, ox=-0.135)
    its = []
    for i, t in enumerate(('ТРАП', 'ЛЮК', 'НАДДУВ')):
        x = 0.12 + 0.075 * i
        its += toggle(x, 0.05, guard=(i < 2))
        PB.label(pl, x, 0.024, t, 0.007)
    for i, t in enumerate(('СВЕТ', 'СВЯЗЬ', 'ДРОН')):
        x = 0.12 + 0.075 * i
        its += button(x, -0.06, 0.03, 0.022, 'c_knob')
        PB.label(pl, x, -0.085, t, 0.007)
    PB.label(pl, 0.195, 0.115, 'УПРАВЛЕНИЕ ШЛЮЗОМ', 0.008)
    p += place(its, M)
    for sg in (1, -1):                                                           # светильники и потолочные поручни
        zl = top_z(-0.2, 0.45, WALL)
        p += [box('lampb', (0.11, 2.60, 0.02), (sg * 0.45, -0.20, zl - 0.012), bevel=0.005, mat_name='m_dark'),
              box('lamp', (0.075, 2.50, 0.008), (sg * 0.45, -0.20, zl - 0.026), mat_name='emissive')]
        zr = top_z(-0.2, 0.2, WALL) - 0.075
        p.append(cyl('hrail', (sg * 0.20, -1.95, zr), (sg * 0.20, 1.60, zr), 0.014, 10, 'm_orange'))
        for yy in (-1.95, -0.75, 0.45, 1.60):
            p.append(cyl('hstand', (sg * 0.20, yy, zr), (sg * 0.20, yy, zr + 0.075), 0.010, 8, 'm_steel'))
    # манометр и вентиль у люка
    p += [cyl('gauge', (0.72, HATCH_Y - 0.06, z0 + 1.45), (0.72, HATCH_Y - 0.10, z0 + 1.45), 0.06, 20, 'm_dark', bevel=0.006),
          cyl('gface', (0.72, HATCH_Y - 0.10, z0 + 1.45), (0.72, HATCH_Y - 0.103, z0 + 1.45), 0.05, 20, 'c_placard'),
          torus('valve', (0.72, HATCH_Y - 0.12, z0 + 1.22), 0.055, 0.009, 'Y', 'm_orange', 18),
          cyl('vstem', (0.72, HATCH_Y - 0.06, z0 + 1.22), (0.72, HATCH_Y - 0.12, z0 + 1.22), 0.012, 8, 'm_steel'),
          pipe('vpipe', [(0.72, HATCH_Y - 0.07, z0 + 1.22), (0.72, HATCH_Y - 0.07, z0 + 1.45)], 0.012, 'm_steel', sides=8, res=2, smooth=False)]
    objs.append(mech(p, 'ck_airlock_equip', atlas='B'))
    objs += [PB.finish('ck_faceplates_airlock', 'B', 3.0), SCR6]
    return objs


def build_markers():
    m = [empty('eye_pilot', EYE, size=0.1), empty('cam_airlock', (0, -0.3, FLOOR_Z + 1.68), size=0.15),
         empty('drone_cradle', REFS['cradle'], size=0.2), empty('door_center', (0, BULKHEAD_Y, DOOR_ZC), size=0.2),
         empty('hatch_center', (0, HATCH_Y, HATCH_ZC), size=0.2)]
    for nm, pos in (('light_cabin_L', (0.5, -3.4, 3.4)), ('light_cabin_R', (-0.5, -3.4, 3.4)),
                    ('light_airlock_L', (0.45, -0.2, 3.4)), ('light_airlock_R', (-0.45, -0.2, 3.4))):
        m.append(empty(nm, pos, size=0.1))
    return m
