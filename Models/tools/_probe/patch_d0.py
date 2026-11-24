# Разовая правка после приёмки этапа C: низ крыла — графитовая плитка с развёрткой в плане, верхний пульт со светлым
# корпусом и подсветкой надписей (эмиссионная карта), деталировка стенок и потолка кабины, контрольные виды.
import os
T = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rd(n):
    return open(os.path.join(T, n), encoding='utf-8').read()


def wr(n, s):
    open(os.path.join(T, n), 'w', encoding='utf-8').write(s)


def rep(s, a, b):
    assert a in s, a[:70]
    return s.replace(a, b)


WING = '''def _span_table():
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


'''

s = rd('chaika_ext.py')
a, b = s.index("def build_wing():"), s.index("def build_fin():")
s = s[:a] + WING + s[b:]
wr('chaika_ext.py', s)

s = rd('chaika_tex.py')
s = rep(s, "       29: ((0.78, 0.78, 0.74), 0.50, 0.0)}", "       29: ((0.78, 0.78, 0.74), 0.50, 0.0), 19: ((0.17, 0.18, 0.19), 0.62, 0.0)}")
s = rep(s, "        tint = 1.0 + (rnd - 0.5) * (0.06 if not dark else 0.07)", "        tint = 1.0 + (rnd - 0.5) * (0.06 if not dark else 0.12)")
s = rep(s, "    M = {k: Image.new('L', (N, N), 0) for k in ('ink', 'orange', 'label', 'groove', 'rivet', 'dark')}",
        "    M = {k: Image.new('L', (N, N), 0) for k in ('ink', 'orange', 'label', 'groove', 'rivet', 'dark', 'glow')}")
s = rep(s, """            a, b = px(d['q'][0]), px(d['q'][1])
            ImageDraw.Draw(M[d.get('color', 'label')]).line([tuple(a), tuple(b)], fill=255, width=max(1, int(round(d.get('w', 0.001) * s))))
            continue""", """            a, b = px(d['q'][0]), px(d['q'][1])
            for key in [d.get('color', 'label')] + (['glow'] if d.get('glow') else []):
                ImageDraw.Draw(M[key]).line([tuple(a), tuple(b)], fill=255, width=max(1, int(round(d.get('w', 0.001) * s))))
            continue""")
s = rep(s, """            stamp(M[d.get('color', 'ink')], tm, pu + e1 / W * off + e2 * (1 - k) / 2, e1 / W * tw * k, e2 * k)""",
        """            for key in [d.get('color', 'ink')] + (['glow'] if d.get('glow') else []):
                stamp(M[key], tm, pu + e1 / W * off + e2 * (1 - k) / 2, e1 / W * tw * k, e2 * k)""")
s = rep(s, """            cs = [tuple(pu), tuple(pu + e1), tuple(p0 + e1), tuple(p0)]
            ImageDraw.Draw(M[d.get('color', 'label')]).line(cs + [cs[0]], fill=255, width=max(1, int(round(d.get('w', 0.001) * s))))""",
        """            cs = [tuple(pu), tuple(pu + e1), tuple(p0 + e1), tuple(p0)]
            for key in [d.get('color', 'label')] + (['glow'] if d.get('glow') else []):
                ImageDraw.Draw(M[key]).line(cs + [cs[0]], fill=255, width=max(1, int(round(d.get('w', 0.001) * s))))""")
s = rep(s, "    del A, M\n", "    glow = A['glow']\n    del A, M\n")
s = rep(s, "    Image.fromarray((orm * 255 + 0.5).astype(np.uint8)).save(p + '_ORM.png')\n",
        """    Image.fromarray((orm * 255 + 0.5).astype(np.uint8)).save(p + '_ORM.png')
    if glow.max() > 0:                                       # подсветка надписей: тёплая и неяркая (линейные 0,50 / 0,33 / 0,17)
        em = np.clip(glow[:, :, None] * np.array((0.50, 0.33, 0.17), np.float32), 0, 1)
        em = np.where(em <= 0.0031308, em * 12.92, 1.055 * np.power(em, 1 / 2.4) - 0.055)
        Image.fromarray((np.clip(em, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p + '_Emissive.png')
        print('сохранено', CFG['names'][at] + '_Emissive')
    elif os.path.exists(p + '_Emissive.png'):
        os.remove(p + '_Emissive.png')
""")
wr('chaika_tex.py', s)

s = rd('partkit.py')
s = rep(s, "    def __init__(self, cls='c_panel', row=1.75):\n        self.cls, self.row = cls, row\n",
        "    def __init__(self, cls='c_panel', row=1.75, glow=False):\n        self.cls, self.row, self.glow = cls, row, glow\n")
s = rep(s, "        decals = [dict(d, q=[pl.tc(*p) for p in pts]) for pl, d, pts in self.items]",
        "        decals = [dict(d, q=[pl.tc(*p) for p in pts], glow=self.glow) for pl, d, pts in self.items]")
wr('partkit.py', s)

s = rd('chaika_cockpit_station.py')
s = rep(s, "def toggle_row(P, pl, parts, y, labels, pitch=0.05, title=None, guard=False):",
        "def toggle_row(P, pl, parts, y, labels, pitch=0.05, title=None, guard=False, hh=0.0064):")
s = rep(s, "        P.label(pl, x, y - (0.024 if guard else 0.019), lab, 0.0064)",
        "        P.label(pl, x, y - (0.024 if guard else 0.019) - (hh - 0.0064) / 2, lab, hh)")
s = rep(s, "        P.label(pl, 0, y + 0.034, title, 0.0065)", "        P.label(pl, 0, y + 0.034, title, max(0.0065, hh * 1.2))")
s = rep(s, "(0, 0, 0.03 - 0.06), bevel=0.012, mat_name='c_plastic')], M)", "(0, 0, 0.03 - 0.06), bevel=0.012, mat_name='c_frame')], M)   # корпус светлый")
s = rep(s, "labs, pitch=0.042, title=('ПИТАНИЕ', 'СИСТЕМЫ', 'АВИОНИКА')[r_])", "labs, pitch=0.042, title=('ПИТАНИЕ', 'СИСТЕМЫ', 'АВИОНИКА')[r_], hh=0.0085)")
s = rep(s, "['ПОЖАР Л', 'ПОЖАР П'], pitch=0.09, guard=True)", "['ПОЖАР Л', 'ПОЖАР П'], pitch=0.09, guard=True, hh=0.0085)")
s = rep(s, "    objs.append(mech(build_overhead(P), 'ck_overhead', atlas='A'))\n",
        "    PO = Plates(cls='c_panel_lt', row=0.6, glow=True)                       # верхний пульт: светлая панель, подсветка надписей\n"
        "    objs.append(mech(build_overhead(PO), 'ck_overhead', atlas='A'))\n"
        "    objs.append(PO.finish('ck_faceplates_overhead', 'A', 6.0))\n")
wr('chaika_cockpit_station.py', s)

s = rd('chaika_cockpit.py')
s = rep(s, "'c_bezel': 28, 'c_placard': 29, 'glass': 60, 'emissive': 61}", "'c_bezel': 28, 'c_placard': 29, 'c_panel_lt': 19, 'glass': 60, 'emissive': 61}")
s = rep(s, "'c_bezel': (0.05, 0.052, 0.055), 'c_placard': (0.78, 0.78, 0.74)}", "'c_bezel': (0.05, 0.052, 0.055), 'c_placard': (0.78, 0.78, 0.74), 'c_panel_lt': (0.17, 0.18, 0.19)}")
s = rep(s, "for _f in ('chaika_cockpit_station.py', 'chaika_cockpit_rear.py'):", "for _f in ('chaika_cockpit_station.py', 'chaika_cockpit_rear.py', 'chaika_cockpit_detail.py'):")
s = rep(s, "    objs += build_station()\n", "    objs += build_station()\n    objs += build_detail()\n")
wr('chaika_cockpit.py', s)

s = rd('chaika_final.py')
s = rep(s, "    nt.links.new(sep.outputs['Red'], gn.inputs[0])\n    return m\n",
        """    nt.links.new(sep.outputs['Red'], gn.inputs[0])
    if os.path.exists(os.path.join(EXP, prefix + '_Emissive.png')):     # подсветка надписей (есть только у кабины)
        em = img('_Emissive', 'sRGB')
        nt.links.new(em.outputs['Color'], b.inputs['Emission Color'])
        b.inputs['Emission Strength'].default_value = 1.0
    return m
""")
wr('chaika_final.py', s)

s = rd('chaika_cockpit_final.py')
s = rep(s, "                   screen_placeholders=['T_Screen_%d.png' % k for k in range(1, 7)]),",
        "                   screen_placeholders=['T_Screen_%d.png' % k for k in range(1, 7)],\n"
        "                   emissive=[f for f in ('T_CockpitFront_Emissive.png',) if os.path.exists(os.path.join(EXP, f))]),")
s = rep(s, "'T_Screen_*.png — заглушки 1280×800 для экранов, в сцене заменяются живым интерфейсом.',",
        "'T_Screen_*.png — заглушки 1280×800 для экранов, в сцене заменяются живым интерфейсом. '\n"
        "                      'T_CockpitFront_Emissive.png (sRGB) — тёплая неяркая подсветка надписей верхнего пульта: Emissive слота cockpit_front.',")
s = rep(s, "               'Ложемент дрона пуст: модель «Светляка» ставится в метку drone_cradle.'],",
        "               'Ложемент дрона пуст: модель «Светляка» ставится в метку drone_cradle.',\n"
        "               'ck_detail_L / ck_detail_R / ck_detail_roof — жгуты, поручни, сетки, короб маски, фонарь, воздуховод; ck_placards — таблички.'],")
wr('chaika_cockpit_final.py', s)

s = rd('live_shots.py')
s = rep(s, "    'gear1m': ((-3.25, -4.05, 1.25), (-2.0, -2.9, 0.95), 60, (-60, 32)),  # опора с расстояния около 1,5 м\n",
        "    'gear1m': ((-3.25, -4.05, 1.25), (-2.0, -2.9, 0.95), 60, (-60, 32)),  # опора с расстояния около 1,5 м\n"
        "    'wingunder': ((7.6, -3.6, 1.7), (3.0, 0.3, 3.6), 50, (95, 14)),       # низ крыла с высоты глаз\n")
s = rep(s, "[v for v in VIEWS if v not in ('wingtop', 'gear1m')]", "[v for v in VIEWS if v not in ('wingtop', 'gear1m', 'wingunder')]")
wr('live_shots.py', s)

s = rd('live_shots_ck.py')
s = rep(s, "    'eye_left60': (E, _dir(60, -8), 90), 'eye_right60': (E, _dir(-60, -8), 90),\n",
        "    'eye_left60': (E, _dir(60, -8), 90), 'eye_right60': (E, _dir(-60, -8), 90), 'eye_left100': (E, _dir(100, -8), 90),\n")
wr('live_shots_ck.py', s)
print('patch_d0 ok')
