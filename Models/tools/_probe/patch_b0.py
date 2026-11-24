# Разовая правка после приёмки этапа A (фонарь из 7 окон, пульт, панель, лыжи). Запуск: python tools/_probe/patch_b0.py
import os
T = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rd(n):
    return open(os.path.join(T, n), encoding='utf-8').read()


def wr(n, s):
    open(os.path.join(T, n), 'w', encoding='utf-8').write(s)


def rep(s, a, b):
    assert a in s, a[:60]
    return s.replace(a, b)


s = rd('chaika_shape.py')
a = s.index("# ---------------- фонарь кабины ----------------")
b = s.index("# ---------------- крыло «чайка» ----------------")
s = s[:a] + rd(os.path.join('_probe', 'canopy_new.txt')) + s[b:]
s = rep(s, "SKI_LEN, SKI_W = 2.10, 0.62", "SKI_LEN, SKI_W = 2.40, 0.96")
s = rep(s, "'front': dict(A=(1.50, -2.90, 1.72), P=(2.02, -2.90, 0.0)),", "'front': dict(A=(1.50, -2.90, 1.72), P=(2.10, -2.90, 0.0)),")
s = rep(s, "'rear': dict(A=(1.62, 2.30, 1.95), P=(2.22, 2.90, 0.0)),", "'rear': dict(A=(1.62, 2.30, 1.95), P=(2.30, 2.90, 0.0)),")
wr('chaika_shape.py', s)

s = rd('chaika_block.py')
s = rep(s, "    solidify(frame, WALL + 0.012, offset=-1 + 2 * 0.012 / (WALL + 0.012))\n", "")
s = rep(s, "    frame = bm_obj(bf, 'canopy_frame', 'clay_frame', 30)\n", "    frame_solid(bf)\n    frame = bm_obj(bf, 'canopy_frame', 'clay_frame', 30)\n")
a = s.index("    strut = prism('strut',")
tail = "    out.append(merge([panel, hood, strut], 'ck_panel', (0, 0, 0)))"
b = s.index(tail)
s = s[:a] + "    out.append(merge([panel, hood], 'ck_panel', (0, 0, 0)))" + s[b + len(tail):]
s = rep(s, "    y0, y1 = -5.52, -4.80\n", "    y0, y1 = -5.28, -4.62\n")
s = rep(s, "            yy = y0 + 0.10 + 0.24 * i", "            yy = y0 + 0.10 + 0.22 * i")
s = rep(s, "ovh = box('ck_overhead', (0.36, math.hypot(y1 - y0, z1 - z0), 0.07)", "ovh = box('ck_overhead', (0.30, math.hypot(y1 - y0, z1 - z0), 0.07)")
s = rep(s, "(-0.12 + 0.06 * j, yy, zz), mat_name='clay_frame'))", "(-0.10 + 0.05 * j, yy, zz), mat_name='clay_frame'))")
a = s.index("        prof = [(y0 + 0.95, 0.03), (y0 + 0.86, 0.0)")
b = s.index("        for sx in (-0.12, 0.12):")
s = s[:a] + '''        prof = [(y0 + 1.08, 0.05), (y0 + 0.96, 0.0), (y0 - 0.70, 0.0), (y0 - 1.02, 0.08), (y0 - 1.30, 0.30),
                (y0 - 1.30, 0.40), (y0 - 0.98, 0.22), (y0 - 0.70, 0.14), (y0 + 1.08, 0.14)]
        parts = [prism('ski', prof, P.x - SKI_W / 2, P.x + SKI_W / 2, 'X', bevel=0.03, mat_name='clay_mid')]
        for sx in (-SKI_W / 2 + 0.06, 0.0, SKI_W / 2 - 0.06):          # продольные рёбра жёсткости
            parts.append(box('rib', (0.07, 1.70, 0.07), (P.x + sx, y0 + 0.12, 0.17), bevel=0.02, mat_name='clay_frame'))
        for yy in (-0.45, 0.70):                                         # поперечные балки
            parts.append(box('beam', (SKI_W - 0.10, 0.10, 0.08), (P.x, y0 + yy, 0.175), bevel=0.02, mat_name='clay_frame'))
''' + s[b:]
s = rep(s, "prism('cheek', [(y0 - 0.20, 0.09), (y0 + 0.20, 0.09), (y0 + 0.09, 0.46), (y0 - 0.09, 0.46)],",
        "prism('cheek', [(y0 - 0.24, 0.13), (y0 + 0.24, 0.13), (y0 + 0.10, 0.48), (y0 - 0.10, 0.48)],")
s = rep(s, "        K = Vector((P.x, P.y, 0.36))\n", "        K = Vector((P.x, P.y, 0.40))\n")
s = rep(s, "defmat('screen', (0.10, 0.22, 0.30, 1), rough=0.3, emis=1.2)", "defmat('screen', (0.05, 0.13, 0.19, 1), rough=0.3, emis=0.7)")
wr('chaika_block.py', s)

s = rd('shots_a.py')
s = rep(s, "setup_cycles(1920, 1080, samples=40, bounces=4)", "setup_cycles(1920, 1080, samples=26, bounces=4)")
s = rep(s, "L.energy, L.size = 30.0, 0.7", "L.energy, L.size = 10.0, 0.7")
s = rep(s, "render(cam, os.path.join(OUT, 'A_%s.png' % v))", "render(cam, os.path.join(OUT, '%s_%s.png' % (os.environ.get('SHOTPREFIX', 'A'), v)))")
wr('shots_a.py', s)

s = rd('sheet_a.py')
s = rep(s, "TMP = os.path.join(ROOT, 'shots', '_tmp')", "TMP = os.path.join(ROOT, 'shots', '_tmp')\nPX = os.environ.get('SHOTPREFIX', 'A')")
for nm in ('A_rear.png', 'A_eye_fwd.png', 'A_eye_up.png', 'A_eye_down.png', 'A_pano.png', 'A_chaika_rear_ramp.png',
           'A_eye_forward.png', 'A_eye_up40.png', 'A_eye_down25.png', 'A_eye_visibility_map.png'):
    s = s.replace("'%s'" % nm, "PX + '%s'" % nm[1:])
wr('sheet_a.py', s)
print('patch_b0 ok')
