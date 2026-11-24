# правка: соль на обломках — ниша под крышкой чистая, корка пятнами с просветами краски, фон между поясами темнее;
# кадр главного блока с 10 м
import os
T = r'C:\UnrealScenes\Models\tools'


def patch(name, pairs):
    p = os.path.join(T, name)
    s = open(p, encoding='utf-8').read()
    for a, b in pairs:
        assert a in s, (name, a[:70])
        s = s.replace(a, b)
    open(p, 'w', encoding='utf-8').write(s)
    print('ok', name)


patch('d_tex_wreck.py', [
    ("    clean = obj_mask(g, 'wr_storage')\n",
     "    clean = obj_mask(g, 'wr_storage')\n"
     "    # ниша была закрыта крышкой: всё, что глубже наружной панели грани P, — без соли, сколов и выгорания\n"
     "    clean = clean | (obj_mask(g, 'wr_bus_front') & (lp @ np.array((0.70711, 0.70711, 0.0), np.float32) < 0.640))\n"),
    ("    base += (np.array((0.76, 0.74, 0.68), np.float32) - base) * (0.40 * film)[:, None]   # ниже верхней линии — тусклее\n",
     "    base += (np.array((0.64, 0.61, 0.54), np.float32) - base) * (0.50 * film)[:, None]   # ниже верхней линии — тусклее и грязнее\n"),
    ("    grain = vnoise(wp, 1100, 47, 1)\n", "    grain = vnoise(wp, 1100, 47, 1)\n    npat = vnoise(wp, 70, 48, 2)                                          # корка пятнами: местами видна краска\n"),
    ("(0.070, 0.100, 0.125))) + [(WATER_ + 0.012, 0.035)]", "(0.055, 0.075, 0.090))) + [(WATER_ + 0.012, 0.035)]"),
    ("* keep * (0.62 + 0.38 * sstep(0.30, 0.60, nf2))\n", "* keep * (0.40 + 0.60 * sstep(0.36, 0.58, npat))\n"),
    ("        H += 0.0022 * crust * nf2 - 0.0002 * stain + 0.0045 * cryst * (0.3 + 0.7 * grain) + 0.0008 * runs\n",
     "        H += 0.0011 * crust * nf2 - 0.0002 * stain + 0.0040 * cryst * (0.3 + 0.7 * grain) + 0.0005 * runs\n"),
])
patch('live_shots_d.py', [
    ("#            вид: (камера, подготовка сцены, солнце",
     "def bus10():\n"
     "    \"\"\"Главный блок с 10 м, с высоты глаз, обычным объективом — читаются ли пояса соли.\"\"\"\n"
     "    n = ydir('panel_center')\n"
     "    n.z = 0\n"
     "    n.normalize()\n"
     "    d = (n * 0.82 + Vector((-n.y, n.x, 0)) * 0.57).normalized()\n"
     "    b = bpy.data.objects['wr_bus'].matrix_world.translation\n"
     "    tgt = Vector((b.x, b.y, 0.55))\n"
     "    return (tgt + d * 10.0 + Vector((0, 0, 1.15)), tgt, 36)\n\n\n"
     "#            вид: (камера, подготовка сцены, солнце"),
    ("    'main': (panel_view, None, (225, 32)),\n", "    'main': (panel_view, None, (225, 32)),\n    'salt10': (bus10, None, (225, 32)),\n"),
])
