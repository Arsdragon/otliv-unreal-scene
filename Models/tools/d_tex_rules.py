# d_tex_rules.py — правила раскраски моделей этапа D (подключается из d_tex.py). Все размеры — метры.


def paint_svetlyak(g):
    pal = {'sv_shell': ((0.74, 0.73, 0.69), 0.36, 0.0), 'sv_dark': ((0.050, 0.053, 0.057), 0.46, 0.0),
           'sv_orange': ((0.76, 0.27, 0.045), 0.42, 0.0), 'sv_carbon': ((0.028, 0.030, 0.033), 0.30, 0.0),
           'm_alu': ((0.72, 0.73, 0.74), 0.30, 1.0), 'm_steel': ((0.36, 0.36, 0.37), 0.36, 1.0),
           'm_rubber': ((0.028, 0.028, 0.030), 0.82, 0.0), 'sv_lensbody': ((0.022, 0.023, 0.026), 0.32, 0.4),
           'm_chrome': ((0.92, 0.92, 0.92), 0.08, 1.0), 'sv_ceramic': ((0.82, 0.80, 0.75), 0.55, 0.0)}
    base, rough, metal = palette(g, pal)
    H = np.zeros(len(base), np.float32)
    wp, lp, wn = g['wp'], g['lp'], g['wn']
    ao = load_ao(g)
    nf, nm, nb = vnoise(wp, 300, 1, 2), vnoise(wp, 45, 2, 3), vnoise(wp, 8, 3, 3)
    shell, dark = cls_mask(g, 'sv_shell'), cls_mask(g, 'sv_dark')
    base *= (0.95 + 0.10 * nb)[:, None]
    rough += (nm - 0.5) * 0.10
    groove = np.zeros(len(base), np.float32)
    body = obj_mask(g, 'sv_body')
    x, y, z = wp[:, 0], wp[:, 1], wp[:, 2]
    top = body & shell & (wn[:, 2] > 0.55)
    sd = rrect_sdf(x, y - 0.020, 0.150, 0.100, 0.014)                       # люк обслуживания сверху
    groove = np.maximum(groove, np.where(top, sstep(0.0011, 0.0003, np.abs(sd)), 0))
    for y0 in (-0.118, 0.150):                                           # поперечные швы верхней оболочки
        groove = np.maximum(groove, np.where(body & shell & (z > 0.012), sstep(0.0010, 0.0003, np.abs(y - y0)), 0))
    vent = np.zeros(len(base), bool)                                     # жалюзи охлаждения у кормы
    for k in range(5):
        sdv = rrect_sdf(x - (-0.028 + 0.014 * k), y - 0.166, 0.0055, 0.020, 0.0025)
        vent |= top & (sdv < 0)
        groove = np.maximum(groove, np.where(top, sstep(0.0008, 0.0002, np.abs(sdv)), 0))
    for sg in (1, -1):                                                   # разъём зарядки на бортах
        m = body & (wn[:, 0] * sg > 0.6) & (np.abs(z - 0.010) < 0.02)
        sdp = rrect_sdf(y - 0.045, z - 0.010, 0.030, 0.014, 0.003)
        vent |= m & (sdp < 0)
        groove = np.maximum(groove, np.where(m, sstep(0.0008, 0.0002, np.abs(sdp)), 0))
        for dy in (-0.007, 0.007):
            pin = m & (np.hypot(y - 0.045 - dy, z - 0.010) < 0.0022)
            base[pin], metal[pin], rough[pin] = (0.80, 0.62, 0.30), 1.0, 0.25
    head = obj_mask(g, 'sv_head')
    groove = np.maximum(groove, np.where(head & dark, sstep(0.0009, 0.0003, np.abs(lp[:, 2])), 0))   # шов шара головы
    base[vent] = (0.018, 0.019, 0.02)
    H -= 0.0012 * vent
    H -= 0.0005 * groove
    base *= (1 - 0.55 * groove)[:, None]
    # надписи
    ink = np.array((0.10, 0.10, 0.11), np.float32)
    for obj, txt, c, u, v, h in (('sv_body', 'СВЕТЛЯК', (0.110, 0.000, 0.024), (0, 1, 0), (0, 0, 1), 0.017),
                                 ('sv_body', 'СВЕТЛЯК', (-0.110, 0.000, 0.024), (0, -1, 0), (0, 0, 1), 0.017),
                                 ('sv_body', 'СВ-2', (0.0, 0.103, 0.06), (-1, 0, 0), (0, -1, 0), 0.015),
                                 ('sv_body', 'ЗАРЯД', (0.110, 0.045, -0.002), (0, 1, 0), (0, 0, 1), 0.0045),
                                 ('sv_body', 'ЗАРЯД', (-0.110, 0.045, -0.002), (0, -1, 0), (0, 0, 1), 0.0045)):
        m, cv = decal_text(g, obj, txt, c, u, v, h, depth=0.03, facing=0.35)
        idx = np.nonzero(m)[0]
        base[idx] += (ink - base[idx]) * (0.92 * cv)[:, None]
        rough[idx] += 0.05 * cv
    # угольное волокно лопастей
    carb = cls_mask(g, 'sv_carbon')
    tw = (((g['xs'] // 3 + g['ys'] // 3) % 2) == 0).astype(np.float32)
    base[carb] *= (0.85 + 0.30 * tw[carb])[:, None]
    rough[carb] += (tw[carb] - 0.5) * 0.10
    H += np.where(carb, tw * 0.00005, 0)
    # ---- износ: кромки заборников и бамперы колец (не «из коробки»)
    optics = cls_mask(g, 'sv_lensbody', 'm_chrome', 'sv_ceramic', 'm_alu')
    rub = cls_mask(g, 'm_rubber')
    rr = np.full(len(base), 9.0, np.float32)
    for cx, cy in ((0.215, -0.095), (-0.215, -0.095), (0.215, 0.115), (-0.215, 0.115)):
        rr = np.minimum(rr, np.hypot(x - cx, y - cy))
    duct = body & (rr > 0.054) & (rr < 0.086)
    lip = duct & shell & (z > 0.012)
    scuff = sstep(0.60, 0.80, vnoise(wp, 160, 61, 2)) * lip
    base += (np.array((0.50, 0.50, 0.49), np.float32) - base) * (0.55 * scuff)[:, None]
    rough += 0.15 * scuff
    edge = lip & (z > 0.0195) & (nf > 0.70) & (nm > 0.40)                 # сколы до тёмного композита на самой кромке
    base[edge] = (0.16, 0.16, 0.17)
    H -= 0.00012 * edge
    throat = duct & shell & (rr < 0.0625) & (z > 0.010)
    base[throat] *= 0.82
    abr = sstep(0.55, 0.80, vnoise(wp * np.array((1, 1, 5), np.float32), 120, 62, 2)) * (rub & duct)
    base += (np.array((0.10, 0.10, 0.10), np.float32) - base) * (0.6 * abr)[:, None]
    rough -= 0.15 * abr
    # ---- соль: дымка и высохшие капли на днище (гуще к корме), подтёки на нижней части колец
    salt, salt_b = np.array((0.74, 0.73, 0.69), np.float32), np.array((0.86, 0.85, 0.81), np.float32)
    under = (wn[:, 2] < -0.25) & ~optics
    haze = under * (0.25 + 0.75 * sstep(-0.10, 0.20, y)) * (0.35 + 0.65 * nb)
    base += (salt - base) * (0.20 * haze)[:, None]
    rough += 0.15 * haze
    drops = sstep(0.79, 0.86, vnoise(wp, 700, 7, 2)) * under * (0.4 + 0.6 * sstep(0.35, 0.70, nb))
    base += (salt_b - base) * (0.55 * drops)[:, None]
    rough += 0.25 * drops
    H += 0.0001 * drops
    wall = duct & (z < 0.006) & (np.abs(wn[:, 2]) < 0.65) & ~rub
    st_ = sstep(0.60, 0.74, vnoise(wp * np.array((1, 1, 0.08), np.float32), 95, 63, 2)) * wall * sstep(0.006, -0.020, z)
    base += (salt - base) * (0.45 * st_)[:, None]
    rough += 0.2 * st_
    bot = duct & (wn[:, 2] < -0.5) & (nf > 0.55)                          # корка на нижних торцах колец
    base[bot] += (salt_b - base[bot]) * 0.35
    rsalt = rub & (z < -0.004) & (vnoise(wp, 500, 64, 1) > 0.70)          # соль в складке бампера снизу
    base[rsalt] += (salt_b - base[rsalt]) * 0.45
    dirt = np.clip((0.80 - ao) / 0.45, 0, 1) * (0.5 + 0.5 * nm)
    base += (np.array((0.26, 0.23, 0.19), np.float32) - base) * (0.15 * dirt)[:, None]
    chip = shell & (nf > 0.84) & (nm > 0.68)
    base[chip] = (0.30, 0.30, 0.31)
    H -= 0.00008 * chip
    tip = np.array((0.0175, -0.100, -0.088), np.float32)                 # копоть у сопла резака
    sc_ = sstep(0.030, 0.004, np.linalg.norm(wp - tip, axis=1)) * (0.6 + 0.4 * nm)
    base *= (1 - 0.75 * sc_)[:, None]
    rough += 0.3 * sc_
    metal *= (1 - 0.6 * sc_)
    base *= (0.88 + 0.12 * ao)[:, None]
    H += (nf - 0.5) * 0.00003
    write_maps(g, PREFIX or 'T_Svetlyak', base, rough, metal, H, ao * (1 - 0.4 * groove))


def paint_wreck(g):
    exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'd_tex_wreck.py'), encoding='utf-8').read(), globals())
    paint_wreck_impl(g)


def paint_gloves(g):
    exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'd_tex_gloves.py'), encoding='utf-8').read(), globals())
    paint_gloves_impl(g)


RULES = {'svetlyak': paint_svetlyak, 'probe_wreck': paint_wreck, 'pilot_gloves': paint_gloves}
