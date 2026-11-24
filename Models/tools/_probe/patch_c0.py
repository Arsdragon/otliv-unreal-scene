# Разовая правка по замечаниям к этапу B: низ крыла светлой плиткой, третий атлас (шасси, трап, люк, ниша),
# ряды плитки вдоль линий корпуса, плотность карт (dens) для структурных развёрток.
import os
T = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rd(n):
    return open(os.path.join(T, n), encoding='utf-8').read()


def wr(n, s):
    open(os.path.join(T, n), 'w', encoding='utf-8').write(s)


def rep(s, a, b):
    assert a in s, a[:70]
    return s.replace(a, b)


# ---------------- uvkit: плотность карты
s = rd('uvkit.py')
s = rep(s, "        y0 = int(math.ceil(charts[nm]['h'] * s)) + PAD\n", "        y0 = int(math.ceil(charts[nm]['h'] * charts[nm].get('dens', 1.0) * s)) + PAD\n")
s = rep(s, "    items = [(nm, c['w'], c['h']) for nm, c in charts.items() if nm not in rect]",
        "    items = [(nm, c['w'] * c.get('dens', 1.0), c['h'] * c.get('dens', 1.0)) for nm, c in charts.items() if nm not in rect]")
s = rep(s, """        x0, y0, s = rects[src]
        o['rect'] = [x0, y0, s]
        for d in o.data.uv_layers.active.data:
            d.uv = ((x0 + d.uv[0] * s) / ATLAS, 1.0 - (y0 + d.uv[1] * s) / ATLAS)
""", """        x0, y0, s = rects[src]
        so = bpy.data.objects.get(src)
        s = s * (json.loads(so['chart']).get('dens', 1.0) if so and so.get('chart') else 1.0)
        o['rect'] = [x0, y0, s]
        for d in o.data.uv_layers.active.data:
            d.uv = ((x0 + d.uv[0] * s) / ATLAS, 1.0 - (y0 + d.uv[1] * s) / ATLAS)


def layout_of(rects, charts):
    \"\"\"Записи для layout.json: прямоугольник карты в пикселях атласа, масштаб, параметры.\"\"\"
    out = {}
    for nm, (x0, y0, s) in rects.items():
        c = charts[nm]
        k = s * c.get('dens', 1.0)
        out[nm] = dict(c, rect=[x0, y0, x0 + c['w'] * k, y0 + c['h'] * k], scale=s)
    return out
""")
wr('uvkit.py', s)

# ---------------- chaika_ext
s = rd('chaika_ext.py')
s = rep(s, "CLS = {'tile_white': 1, 'tile_belly': 2, 'frame': 3, 'tunnel': 4, 'rcc': 5, 'm_white': 10,",
        "CLS = {'tile_white': 1, 'tile_belly': 2, 'frame': 3, 'tunnel': 4, 'rcc': 5, 'tile_gray': 6, 'm_white': 10,")
s = rep(s, "_PV = {'tile_white': (0.80, 0.80, 0.78),", "_PV = {'tile_gray': (0.62, 0.62, 0.61), 'tile_white': (0.80, 0.80, 0.78),")
s = rep(s, "    ob, (w, h), u = _foil(rings, n, 'ext_wing_R', ['tile_white', 'tile_belly', 'rcc'], mf)",
        "    ob, (w, h), u = _foil(rings, n, 'ext_wing_R', ['tile_white', 'tile_gray', 'rcc'], mf)   # низ — светло-серая плитка")
s = rep(s, "    set_chart(hull, 'hull', HULL_W, 2 * SMAX, 'A', tiles=True, smax=SMAX, decals=hull_decals())",
        """    zu = frange(0.05, HULL_W, 0.05)                    # линии плеча и скулы вдоль корпуса — для рядов плитки
    zs_ = [_sect(NOSE_Y + u)[1] for u in zu]
    zones = dict(u=[round(u, 3) for u in zu], tk=[round(L[-1], 4) for L in zs_],
                 tc=[round(L[-1] - L[SEG_K + SEG_B + SEG_C // 2], 4) for L in zs_],
                 ts=[round(L[-1] - L[SEG_K + SEG_B + SEG_C + SEG_S + SEG_SH // 2], 4) for L in zs_])
    set_chart(hull, 'hull', HULL_W, 2 * SMAX, 'A', tiles=True, smax=SMAX, zones=zones, decals=hull_decals())""")
s = rep(s, "    for o in out[2:4]:\n        smart_uv(o, 'B', dens=0.6)", "    smart_uv(out[2], 'C', dens=0.7)\n    smart_uv(out[3], 'B', dens=0.6)")
a = s.index("    rB, cB = pack_atlas(objs, 'B')")
b = s.index("    tr = sum(tris(o) for o in objs)")
s = s[:a] + """    rB, cB = pack_atlas(objs, 'B')
    rC, cC = pack_atlas(objs, 'C')
    apply_atlas(objs, {**rA, **rB, **rC})
    layout = {'A': layout_of(rA, cA), 'B': layout_of(rB, cB), 'C': layout_of(rC, cC)}
    json.dump(layout, open(os.path.join(EXP, 'layout.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    nA = dump_faces(objs, 'A', CLS, os.path.join(EXP, 'faces_A.npz'), cA)
    nB = dump_faces(objs, 'B', CLS, os.path.join(EXP, 'faces_B.npz'), cB) + dump_faces(objs, 'C', CLS, os.path.join(EXP, 'faces_C.npz'), cC)
""" + s[b:]
s = rep(s, "атлас B: %.0f пикс/м; граней A %d, B %d'\n          % (tr, len(objs), sA, min(r[2] for n, r in rA.items() if n != 'ext_hull'), min(r[2] for r in rB.values()), nA, nB))",
        "атлас B: %.0f, C: %.0f пикс/м; граней A %d, B+C %d'\n          % (tr, len(objs), sA, min(r[2] for n, r in rA.items() if n != 'ext_hull'), min(r[2] for r in rB.values()),\n             min(r[2] for r in rC.values()), nA, nB))")
wr('chaika_ext.py', s)

s = rd('chaika_ext_parts.py')
s = rep(s, "    return mech(parts, 'ext_gear_%s_R' % key)", "    return mech(parts, 'ext_gear_%s_R' % key, atlas='C')")
s = rep(s, "    ob = mech(parts, 'ext_ramp')", "    ob = mech(parts, 'ext_ramp', atlas='C')")
s = rep(s, "    return mech(parts, 'ext_hatch', origin=(-0.52, y + 0.085, zc))", "    return mech(parts, 'ext_hatch', origin=(-0.52, y + 0.085, zc), atlas='C')")
s = rep(s, "    return mech(parts, 'ext_tunnel_fit', dens=0.8)", "    return mech(parts, 'ext_tunnel_fit', atlas='C', dens=0.8)")
wr('chaika_ext_parts.py', s)

# ---------------- chaika_final: третий набор текстур
s = rd('chaika_final.py')
s = rep(s, "    mats = {'A': tex_mat('chaika_hull', 'T_ChaikaHull'), 'B': tex_mat('chaika_parts', 'T_ChaikaParts'),",
        "    mats = {'A': tex_mat('chaika_hull', 'T_ChaikaHull'), 'B': tex_mat('chaika_parts', 'T_ChaikaParts'),\n            'C': tex_mat('chaika_gear', 'T_ChaikaGear'),")
s = rep(s, "'T_ChaikaParts_BaseColor.png', 'T_ChaikaParts_Normal.png', 'T_ChaikaParts_ORM.png']),",
        "'T_ChaikaParts_BaseColor.png', 'T_ChaikaParts_Normal.png', 'T_ChaikaParts_ORM.png',\n                             'T_ChaikaGear_BaseColor.png', 'T_ChaikaGear_Normal.png', 'T_ChaikaGear_ORM.png']),")
s = rep(s, "dict(name='chaika_parts', textures='T_ChaikaParts_*', note='крыло, мотогондолы, опоры, трап, люк, детали'),",
        "dict(name='chaika_parts', textures='T_ChaikaParts_*', note='крыло, мотогондолы, мелкие детали корпуса'),\n                        dict(name='chaika_gear', textures='T_ChaikaGear_*', note='опоры с лыжами, трап, люк шлюза, ниша трапа (крупные планы у земли)'),")
wr('chaika_final.py', s)

s = rd('live_shots.py')
s = rep(s, "    'rear': ((5.6, 11.8, 1.7), (0.0, 2.6, 2.25), 56, (150, 30)),       # сзади, трап опущен\n",
        "    'rear': ((5.6, 11.8, 1.7), (0.0, 2.6, 2.25), 56, (150, 30)),       # сзади, трап опущен\n"
        "    'wingtop': ((-9.5, -5.5, 8.5), (-1.2, 0.2, 3.3), 50, (-50, 40)),   # крыло и крыша сверху\n"
        "    'gear1m': ((-3.25, -4.05, 1.25), (-2.0, -2.9, 0.95), 60, (-60, 32)),  # опора с расстояния около 1,5 м\n")
s = rep(s, "todo = list(globals().get('LIVE_VIEWS') or VIEWS)", "todo = list(globals().get('LIVE_VIEWS') or [v for v in VIEWS if v not in ('wingtop', 'gear1m')])")
wr('live_shots.py', s)

s = rd('stage_b.sh')
s = rep(s, "tex) python tools/chaika_tex.py A B |", "tex) python tools/chaika_tex.py chaika_ext |")
wr('stage_b.sh', s)
print('patch_c0 ok')
