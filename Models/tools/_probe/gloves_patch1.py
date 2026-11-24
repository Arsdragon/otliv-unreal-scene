# правка перчаток: накладка на костяшки сидит на кисти, пряжка меньше, большой палец правой — на кромке головки ручки;
# художник текстур знает про перчатки
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


patch('pilot_gloves.py', [
    ("def thumb(ctrl, r0=0.0138, r1=0.0116):", "def thumb(ctrl, end_in=(0, 0, -1), r0=0.0138, r1=0.0116):"),
    ("        inw.append((v * (1 - w) + Vector((0, 0, -1)) * w).normalized())", "        inw.append((v * (1 - w) + Vector(end_in).normalized() * w).normalized())"),
    ("    parts.append(thumb(cfg['thumb']))", "    parts.append(thumb(cfg['thumb'], cfg.get('thumb_in', (0, 0, -1))))"),
    ("    pk = cfg['phi_k'] + 4\n    rk = 2 * 0.0145 + GAP + 0.0030\n", "    pk = cfg['phi_k'] - 3\n    rk = 2 * 0.0145 + GAP - 0.0008\n"),
    ("[(0.0042 * (0.55 + 0.45 * math.sin(math.pi * i / 10)), 0.0105) for i in range(11)]", "[(0.0050 * (0.60 + 0.40 * math.sin(math.pi * i / 10)), 0.0085) for i in range(11)]"),
    ("    sx = x0 - 0.0200 - 0.0016\n", "    sx = x0 - 0.0198 - 0.0004\n"),
    ("    parts.append(box('buckle', (0.0050, 0.023, 0.016), (sx - 0.0015, 0.040, zc + 0.012), bevel=0.0015, mat_name='g_lock'))",
     "    parts.append(box('buckle', (0.0040, 0.015, 0.011), (sx - 0.0010, 0.040, zc + 0.012), bevel=0.0012, mat_name='g_lock'))"),
    ("             thumb=((-0.0240, 0.0385, 0.0180), (-0.0120, 0.0445, 0.0460), (0.0020, 0.0420, 0.0900), (0.0140, 0.0160, 0.0985)))",
     "             thumb=((-0.0240, 0.0385, 0.0180), (-0.0160, 0.0460, 0.0420), (-0.0040, 0.0400, 0.0700), (0.0060, 0.0310, 0.0890)),\n"
     "             thumb_in=(0, -0.75, -0.66))                                                      # подушечка — к задней кромке головки"),
    ("(1 + 0.06 * math.exp(-(s / 0.006) ** 2)", "(1 + 0.08 * math.exp(-(s / 0.006) ** 2)"),
    ("+ 0.05 * math.exp(-((s - L[0]) / 0.005) ** 2)", "+ 0.07 * math.exp(-((s - L[0]) / 0.005) ** 2)"),
    ("+ 0.04 * math.exp(-((s - L[0] - L[1]) / 0.0045) ** 2))", "+ 0.05 * math.exp(-((s - L[0] - L[1]) / 0.0045) ** 2))"),
])
patch('d_tex_rules.py', [
    ("RULES = {'svetlyak': paint_svetlyak, 'probe_wreck': paint_wreck}",
     "def paint_gloves(g):\n"
     "    exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'd_tex_gloves.py'), encoding='utf-8').read(), globals())\n"
     "    paint_gloves_impl(g)\n\n\n"
     "RULES = {'svetlyak': paint_svetlyak, 'probe_wreck': paint_wreck, 'pilot_gloves': paint_gloves}"),
])
