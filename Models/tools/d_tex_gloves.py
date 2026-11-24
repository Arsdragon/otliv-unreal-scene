# d_tex_gloves.py — раскраска перчаток пилота (подключается из d_tex_rules.py, работает в его пространстве имён).
# Ткань тыла кисти и рукава (мелкое плетение, складки), прорезиненная ладонь и кончики пальцев (пупырчатая фактура),
# гофра на суставах пальцев (по списку суставов из layout.json), матовое кольцо разъёма, следы носки в складках.


def paint_gloves_impl(g):
    pal = {'g_fabric': ((0.78, 0.78, 0.76), 0.78, 0.0), 'g_palm': ((0.115, 0.12, 0.125), 0.62, 0.0), 'g_tip': ((0.085, 0.087, 0.09), 0.50, 0.0),
           'g_pad': ((0.19, 0.20, 0.21), 0.50, 0.0), 'g_ring': ((0.66, 0.68, 0.70), 0.34, 1.0), 'g_lock': ((0.30, 0.31, 0.33), 0.42, 1.0),
           'g_bellows': ((0.075, 0.077, 0.08), 0.58, 0.0), 'g_cuff': ((0.80, 0.79, 0.76), 0.82, 0.0), 'g_strap': ((0.20, 0.21, 0.23), 0.72, 0.0),
           'g_dark': ((0.02, 0.02, 0.02), 0.90, 0.0), 'g_orange': ((0.78, 0.33, 0.08), 0.62, 0.0)}
    base, rough, metal = palette(g, pal)
    H = np.zeros(len(base), np.float32)
    wp, lp = g['wp'], g['lp']
    ao = load_ao(g)
    nf, nm, nb = vnoise(wp, 2600, 11, 2), vnoise(wp, 160, 12, 3), vnoise(wp, 22, 13, 3)
    fab = cls_mask(g, 'g_fabric', 'g_cuff').astype(np.float32)
    web = cls_mask(g, 'g_strap', 'g_orange').astype(np.float32)
    grip = cls_mask(g, 'g_palm', 'g_tip').astype(np.float32)
    met = cls_mask(g, 'g_ring', 'g_lock').astype(np.float32)
    # ткань: зерно плетения, мягкие складки, лёгкая разнотонность; рукав — складки покрупнее
    H += fab * ((nf - 0.5) * 0.00010 + (nm - 0.5) * 0.00035)
    base *= (1 + fab * ((nb - 0.5) * 0.06 + (nf - 0.5) * 0.05))[:, None]
    H += cls_mask(g, 'g_cuff') * (vnoise(wp, 45, 14, 3) - 0.5) * 0.0016
    H += web * (nf - 0.5) * 0.00016
    # резина ладони и кончиков: пупырчатая фактура
    peb = sstep(0.52, 0.70, vnoise(wp, 900, 15, 1))
    H += grip * peb * 0.00022
    rough += grip * (peb * 0.08 - 0.03)
    base += (grip * (nm - 0.5) * 0.02)[:, None]
    # гофра на суставах пальцев (только по ткани тыльной стороны)
    for j in LAY.get('joints', []):
        idx = np.nonzero(obj_mask(g, j['obj']))[0]
        if not len(idx):
            continue
        d = lp[idx] - np.array(j['c'], np.float32)
        u = d @ np.array(j['t'], np.float32)
        near = (np.linalg.norm(d, axis=1) < j['r'] * 1.9) & (np.abs(u) < 0.0080)
        sel, uu = idx[near], u[near]
        rib = np.cos(uu / 0.0040 * 2 * np.pi) * (1 - (np.abs(uu) / 0.0080) ** 2) * fab[sel]
        H[sel] += rib * 0.00050
        base[sel] *= (1 - 0.14 * np.clip(-rib, 0, 1))[:, None]
    # металл кольца: матовая анодировка с разнотоном
    rough += met * (vnoise(wp, 700, 16, 2) - 0.5) * 0.12
    base *= (1 + met * (vnoise(wp, 300, 19, 2) - 0.5) * 0.08)[:, None]
    # носка: потемнение в складках и стыках, пятна на ткани, потёртости резины
    occ = np.clip((0.85 - ao) / 0.5, 0, 1)
    base += (np.array((0.42, 0.40, 0.37), np.float32) - base) * (0.35 * occ * fab)[:, None]
    smudge = fab * sstep(0.55, 0.80, vnoise(wp, 55, 17, 3)) * 0.10
    base += (np.array((0.50, 0.48, 0.45), np.float32) - base) * smudge[:, None]
    scuff = grip * sstep(0.62, 0.82, vnoise(wp, 240, 18, 2))
    base += (np.array((0.20, 0.20, 0.21), np.float32) - base) * (0.5 * scuff)[:, None]
    rough += 0.10 * scuff
    base *= (0.86 + 0.14 * ao)[:, None]
    write_maps(g, PREFIX or 'T_PilotGloves', base, np.clip(rough, 0.05, 1), np.clip(metal, 0, 1), H, ao)
