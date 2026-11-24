# d_tex_wreck.py — раскраска обломков зонда «НЕВОД-2» (подключается из d_tex_rules.py, работает в его пространстве имён).
# Порядок: краска и вариации -> солнечные элементы -> ЭВТИ -> надписи -> сколы, ржавчина, потёки -> выгорание на солнце ->
# соль: общий налёт ниже верхней «ватерлинии», плотные корки у каждой линии, подводный налёт -> затенение.


def paint_wreck_impl(g):
    pal = {'w_white': ((0.78, 0.77, 0.73), 0.55, 0.0), 'w_mli': ((0.66, 0.56, 0.36), 0.36, 0.65),
           'w_dark': ((0.075, 0.075, 0.08), 0.55, 0.0), 'w_alu': ((0.64, 0.65, 0.66), 0.42, 1.0),
           'w_steel': ((0.34, 0.33, 0.32), 0.50, 1.0), 'w_cell': ((0.022, 0.036, 0.080), 0.16, 0.0),
           'w_cellback': ((0.58, 0.58, 0.57), 0.55, 0.3), 'w_orange': ((0.76, 0.30, 0.07), 0.55, 0.0),
           'w_rubber': ((0.04, 0.04, 0.045), 0.80, 0.0), 'w_inner': ((0.34, 0.39, 0.34), 0.62, 0.0),
           'w_storage': ((0.12, 0.13, 0.15), 0.36, 0.7), 'w_dish': ((0.82, 0.81, 0.78), 0.70, 0.0),
           'w_gold': ((0.76, 0.58, 0.25), 0.35, 1.0)}
    base, rough, metal = palette(g, pal)
    Mn = len(base)
    H = np.zeros(Mn, np.float32)
    wp, lp, wn = g['wp'], g['lp'], g['wn']
    z = wp[:, 2]
    ao = load_ao(g)
    nf, nm, nb = vnoise(wp, 500, 11, 2), vnoise(wp, 40, 12, 3), vnoise(wp, 4, 13, 3)
    clean = obj_mask(g, 'wr_storage')
    # ниша была закрыта крышкой: всё, что глубже наружной панели грани P, — без соли, сколов и выгорания
    clean = clean | (obj_mask(g, 'wr_bus_front') & (lp @ np.array((0.70711, 0.70711, 0.0), np.float32) < 0.640))
    painted = cls_mask(g, 'w_white', 'w_dish', 'w_orange', 'w_dark', 'w_cellback')
    base *= (0.92 + 0.16 * nb)[:, None]
    rough += (nm - 0.5) * 0.12
    # ---- солнечные элементы: сетка 104 мм в осях крыла, межэлементные зазоры, шины, трещины
    for name, d in LAY.get('solar', {}).items():
        m = obj_mask(g, name) & cls_mask(g, 'w_cell')
        if not m.any():
            continue
        idx = np.nonzero(m)[0]
        p = lp[idx] + np.array(d['offset'], np.float32)
        x, y = p[:, 0], p[:, 1]
        inside = (x > d['x'][0]) & (x < d['x'][1]) & (y > d['y'][0]) & (y < d['y'][1])
        cx, cy = (x - d['x'][0]) / 0.104, (y - d['y'][0]) / 0.104
        fx, fy = cx - np.floor(cx), cy - np.floor(cy)
        gap = (np.minimum(np.minimum(fx, 1 - fx), np.minimum(fy, 1 - fy)) * 0.104 < 0.0016) | ~inside
        busb = (np.abs(fx - 0.33) * 0.104 < 0.0006) | (np.abs(fx - 0.67) * 0.104 < 0.0006)
        hsh = ((np.floor(cx).astype(np.int64) * 73856093) ^ (np.floor(cy).astype(np.int64) * 19349663) ^ hash(name) % 9973) & 0xFFFF
        rnd = hsh.astype(np.float32) / 65535.0
        b = base[idx]
        b *= (0.85 + 0.30 * rnd)[:, None]
        crack = (rnd > 0.78) & (np.abs(vnoise(p, 60, 77, 2) - 0.5) < 0.012)
        b[crack] = (0.42, 0.45, 0.50)
        b[busb & ~gap] = (0.30, 0.31, 0.33)
        b[gap] = (0.56, 0.57, 0.59)
        base[idx] = b
        metal[idx[gap]] = 0.8
        rough[idx[gap]] = 0.35
        rough[idx[crack]] = 0.6
        H[idx] += np.where(gap, -0.0003, 0) + np.where(crack, 0.0001, 0)
    # ---- ЭВТИ: мятая плёнка
    mli = cls_mask(g, 'w_mli')
    cr = vnoise(wp, 140, 21, 3)
    H += np.where(mli, (cr - 0.5) * 0.0022, 0)
    base[mli] *= (0.85 + 0.3 * cr[mli])[:, None]
    rough[mli] = 0.25 + 0.30 * np.abs(cr[mli] - 0.5) * 2
    # ---- надписи (до соли: корка ложится поверх)
    COL = {'ink': (0.07, 0.07, 0.08), 'orange': (0.70, 0.28, 0.07), 'label': (0.86, 0.86, 0.83)}
    for d in LAY.get('decals', []):
        if d['kind'] == 'rect':
            m = obj_mask(g, d['obj'])
            if not m.any():
                continue
            idx = np.nonzero(m)[0]
            a, b2, dn = frame_coords(g, m, d['c'], d['u'], d['v'])
            nw = local_dir(g, d['obj'], np.cross(d['u'], d['v']))
            sd = rrect_sdf(a, b2, d['w'], d['h'], 0.012)
            cv = ((np.abs(sd) < 0.004) & (np.abs(dn) < d['depth']) & (wn[idx] @ nw > 0.3)).astype(np.float32)
        else:
            m, cv = decal_text(g, d['obj'], d['text'], d['c'], d['u'], d['v'], d['h'], depth=d['depth'], facing=0.3)
            idx = np.nonzero(m)[0]
            if not len(idx):
                continue
        cv = cv * (1 - d.get('fade', 0) * (0.5 + 0.5 * nm[idx]))
        base[idx] += (np.array(COL[d['color']], np.float32) - base[idx]) * (0.95 * cv)[:, None]
    # ---- сколы краски, ржавчина, потёки
    chip = painted & ~clean & (nf > 0.74) & (nm > 0.52)
    base[chip] = base[chip] * 0.3 + np.array((0.50, 0.52, 0.50), np.float32) * 0.7
    metal[chip], rough[chip] = 0.6, 0.45
    H -= 0.00025 * chip
    steel = cls_mask(g, 'w_steel')
    rust = steel * sstep(0.35, 0.70, nm)
    base += (np.array((0.28, 0.13, 0.05), np.float32) - base) * (0.8 * rust)[:, None]
    rough += 0.3 * rust
    metal *= (1 - 0.7 * rust)
    streak = painted & ~clean & (z > 0.45)
    sv = vnoise(wp * np.array((1, 1, 0.07), np.float32), 26, 14, 2)
    run = streak * sstep(0.60, 0.78, sv) * (0.4 + 0.6 * nm)
    base += (np.array((0.42, 0.33, 0.24), np.float32) - base) * (0.35 * run)[:, None]
    # ---- выгорание на солнце (выше воды, сильнее на гранях, смотрящих вверх)
    expo = np.clip(0.35 + 0.65 * np.clip(wn[:, 2], 0, 1), 0, 1) * (z > WATER_) * ~clean
    lum = base.mean(1, keepdims=True)
    fadeable = painted | mli | cls_mask(g, 'w_rubber', 'w_gold')
    k = (0.55 * expo * fadeable)[:, None]
    base += (lum * 1.05 + 0.10 - base) * k
    # ---- соль: налёт ниже верхней линии; у каждой «ватерлинии» — тёмная минеральная полоса, под ней светлая корка
    # разной ширины, потёки вниз и местами друзы кристаллов. Пояса должны читаться с 10 м.
    wob = (vnoise(wp * np.array((1, 1, 0), np.float32), 3, 31, 2) - 0.5) * 0.03
    zz = z + wob
    top_line = max(WLINES)
    below = sstep(top_line + 0.04, top_line - 0.02, zz) * ~clean
    salt = np.array((0.88, 0.86, 0.80), np.float32)                       # соль — бежево-белая, матовая
    film = below * (0.35 + 0.65 * nm) * (1 - 0.7 * cls_mask(g, 'w_inner'))
    base += (np.array((0.64, 0.61, 0.54), np.float32) - base) * (0.50 * film)[:, None]   # ниже верхней линии — тусклее и грязнее
    rough += 0.25 * film
    metal *= (1 - 0.6 * film)
    flat = np.array((1, 1, 0), np.float32)
    nf2 = vnoise(wp, 260, 41, 2)
    nl = vnoise(wp * flat, 18, 43, 2)                                     # разрывы поясов вдоль линии
    nw = vnoise(wp * flat, 9, 44, 2)                                      # ширина корки гуляет
    drip = vnoise(wp * np.array((1, 1, 0.05), np.float32), 45, 45, 2)     # вертикальные потёки
    ncr = vnoise(wp, 60, 46, 2)                                           # где сидят друзы кристаллов
    grain = vnoise(wp, 1100, 47, 1)
    npat = vnoise(wp, 70, 48, 2)                                          # корка пятнами: местами видна краска
    lines = list(zip(sorted(WLINES, reverse=True), (0.055, 0.075, 0.090))) + [(WATER_ + 0.012, 0.035)]
    for zk, wd in lines:
        dz = zz - zk
        keep = (0.72 + 0.28 * sstep(0.28, 0.50, nl)) * ~clean
        wloc = wd * (0.65 + 0.70 * nw)
        stain = sstep(0.003, -0.002, dz) * sstep(-0.030, -0.018, dz) * keep
        crust = sstep(-0.014, -0.022, dz) * sstep(-wloc - 0.02, -wloc + 0.01, dz) * keep * (0.40 + 0.60 * sstep(0.36, 0.58, npat))
        runs = sstep(-wloc + 0.02, -wloc - 0.01, dz) * sstep(-wloc - 0.22, -wloc - 0.04, dz) * sstep(0.56, 0.72, drip) * keep * 0.55
        grime = sstep(0.0, -0.010, dz) * sstep(-wloc - 0.20, -wloc, dz) * keep * 0.8
        cryst = sstep(0.60, 0.70, ncr) * sstep(0.012, -0.004, dz) * sstep(-wloc - 0.05, -wloc + 0.02, dz) * ~clean
        base *= (1 - 0.18 * grime)[:, None]
        base += (np.array((0.50, 0.44, 0.36), np.float32) - base) * (0.12 * grime)[:, None]
        sa = np.clip(0.95 * crust + runs, 0, 1)
        base += (salt - base) * sa[:, None]
        base += (np.array((0.25, 0.22, 0.17), np.float32) - base) * (0.90 * stain)[:, None]
        base += (np.array((0.95, 0.94, 0.91), np.float32) - base) * (cryst * (0.55 + 0.45 * grain))[:, None]
        rough = np.maximum(rough, 0.90 * crust)
        rough = np.where(cryst > 0.5, 0.30 + 0.50 * grain, rough)
        metal *= (1 - sa) * (1 - stain) * (1 - cryst)
        H += 0.0011 * crust * nf2 - 0.0002 * stain + 0.0040 * cryst * (0.3 + 0.7 * grain) + 0.0005 * runs
    pud = np.clip(wn[:, 2], 0, 1) ** 2 * below * sstep(0.45, 0.70, nm)        # корка на горизонтальных местах
    base += (salt - base) * (0.6 * pud)[:, None]
    rough += 0.3 * pud
    H += 0.0012 * pud * nf2
    crev = (1 - ao) * below
    base += (salt - base) * (0.30 * crev)[:, None]
    under = (z < WATER_) & ~clean                                             # под водой: мокро, минеральный налёт
    base[under] = base[under] * 0.70 + np.array((0.42, 0.42, 0.38), np.float32) * 0.18
    rough[under] = np.minimum(rough[under], 0.38)
    base *= (0.70 + 0.30 * ao)[:, None]
    H += (nf - 0.5) * 0.00006
    write_maps(g, PREFIX or 'T_ProbeWreck', base, np.clip(rough, 0.05, 1), np.clip(metal, 0, 1), H, ao)


WATER_ = LAY.get('water', 0.45)
WLINES = LAY.get('waterlines', [0.62, 0.78, 1.02])
