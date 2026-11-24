# Разовая правка: граница днища по ряду сетки, место надписей, спокойные сопла и плитка днища.
import os
T = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rd(n):
    return open(os.path.join(T, n), encoding='utf-8').read()


def wr(n, s):
    open(os.path.join(T, n), 'w', encoding='utf-8').write(s)


def rep(s, a, b):
    assert a in s, a[:70]
    return s.replace(a, b)


s = rd('chaika_ext.py')
s = rep(s, """        elif c.z < sec(yy)['zch'] - 0.02 and f.normal.z < -0.12:
            f.material_index = 1
""", """        elif _sect(c.y)[1][-1] - hull_t(c.y, c.x, c.z) < _sect(c.y)[1][SEG_K + SEG_B + SEG_C // 2] - 1e-4:
            f.material_index = 1                      # днище — до середины скругления скулы (ровно по ряду сетки)
""")
a = s.index("def hull_decals():")
b = s.index("# ====================================================================== корпус и фонарь")
s = s[:a] + '''def hull_decals():
    d = []
    for sgn in (1, -1):
        d.append(dict(type='text', text='ЧАЙКА', q=quad3(-2.55, -0.70, 2.52, 2.95, sgn), color='ink', align='l'))
        d.append(dict(type='text', text='ПОСАДОЧНЫЙ МОДУЛЬ ПМ-2', q=quad3(-2.55, -0.70, 2.37, 2.46, sgn), color='ink', align='l'))
        d.append(dict(type='text', text='07', q=quad3(0.75, 1.75, 2.15, 2.85, sgn), color='ink', align='c'))
        d.append(dict(type='text', text='07', q=quad3(4.75, 5.35, 3.27, 3.47, sgn), color='ink', align='c'))
        d.append(dict(type='text', text='АВАРИЙНОЕ ВСКРЫТИЕ', q=quad3(-4.40, -3.72, 2.06, 2.13, sgn), color='orange', align='c'))
        d.append(dict(type='panel', q=quad3(-4.42, -3.70, 2.03, 2.25, sgn), style='rescue'))
        for (ya, yb, za, zb, lab) in ((-3.62, -3.16, 1.86, 2.26, 'БОРТОВАЯ ЭЛЕКТРОНИКА'), (-1.95, -1.25, 1.88, 2.28, 'ЗАПРАВКА  ОКИСЛИТЕЛЬ'),
                                      (-0.95, -0.35, 1.84, 2.24, 'ГИДРОСИСТЕМА'), (1.15, 1.85, 2.95, 3.25, 'АЗОТ  ПРОДУВКА'),
                                      (-3.85, -3.35, 2.62, 2.97, 'ЛЮК ОБСЛУЖИВАНИЯ'), (2.55, 3.05, 2.75, 3.10, 'ЭЛЕКТРОПИТАНИЕ')):
            d.append(dict(type='panel', q=quad3(ya, yb, za, zb, sgn), style='hatch', label=lab))
        for (yc, zc, r) in ((-0.30, 2.72, 0.07), (0.30, 2.50, 0.05), (2.10, 2.62, 0.06), (0.25, 2.05, 0.045)):
            d.append(dict(type='port', q=quad3(yc - r, yc + r, zc - r, zc + r, sgn)))
        d.append(dict(type='text', text='НЕ ВСТАВАТЬ ПОД СОПЛО', q=quad3(2.2, 3.0, 2.50, 2.57, sgn), color='orange', align='c'))
    d.append(dict(type='band', u=[-4.30 - NOSE_Y, -4.12 - NOSE_Y], color='orange'))
    d.append(dict(type='band', u=[5.70 - NOSE_Y, 5.82 - NOSE_Y], color='orange'))
    return d


''' + s[b:]
wr('chaika_ext.py', s)

s = rd('chaika_tex.py')
s = rep(s, "tint = 1.0 + (rnd - 0.5) * (0.07 if cid == 1 else 0.30)", "tint = 1.0 + (rnd - 0.5) * (0.07 if cid == 1 else 0.16)")
s = rep(s, "tint = np.where(r2 > 0.972, tint + (0.07 if cid == 1 else 0.9), tint)", "tint = np.where(r2 > 0.972, tint + (0.07 if cid == 1 else 0.40), tint)")
s = rep(s, "tint = np.where(r2 < 0.035, tint - (0.10 if cid == 1 else 0.25), tint)", "tint = np.where(r2 < 0.035, tint - (0.10 if cid == 1 else 0.12), tint)")
a = s.index("        t = n_mid[noz][:, None]")
b = s.index("        rough[noz] += (n_mid[noz] - 0.5) * 0.25")
s = s[:a] + '''        t = n_big[noz][:, None]
        heat = np.array((0.235, 0.215, 0.20), np.float32) + np.array((0.10, 0.065, 0.02), np.float32) * np.clip(1.4 - 2.4 * t, 0, 1) + \\
            np.array((0.0, 0.015, 0.07), np.float32) * np.clip(2.4 * t - 1.1, 0, 1)
        base[noz] = heat * (0.85 + 0.3 * n_fine[noz][:, None]) * (0.8 + 0.4 * st_u[noz][:, None])
''' + s[b:]
wr('chaika_tex.py', s)
print('patch_b2 ok')
