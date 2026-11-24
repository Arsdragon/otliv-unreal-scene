# Разовая правка кабины перед первой сборкой: смещение экрана, посадка скафандров, знак наклона подпятника.
import os
T = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rd(n):
    return open(os.path.join(T, n), encoding='utf-8').read()


def wr(n, s):
    open(os.path.join(T, n), 'w', encoding='utf-8').write(s)


def rep(s, a, b):
    assert a in s, a[:70]
    return s.replace(a, b)


s = rd('chaika_cockpit_station.py')
s = rep(s, "def screen_unit(P, pl, k, w, h, title, parts, keys=True):", "def screen_unit(P, pl, k, w, h, title, parts, keys=True, ox=0.0):")
s = rep(s, "    r0 = [(x, y, 0.0) for x, y in out_]\n    rings = [r0, [(x, y, 0.007) for x, y in out_], [(x, y, 0.007) for x, y in inn], [(x, y, 0.002) for x, y in inn], r0]",
        "    r0 = [(x + ox, y, 0.0) for x, y in out_]\n    rings = [r0, [(x + ox, y, 0.007) for x, y in out_], [(x + ox, y, 0.007) for x, y in inn], [(x + ox, y, 0.002) for x, y in inn], r0]")
s = rep(s, "its += button(sx * (w / 2 + 0.021), -0.06 + 0.03 * j, 0.011, 0.011, 'c_knob')", "its += button(ox + sx * (w / 2 + 0.021), -0.06 + 0.03 * j, 0.011, 0.011, 'c_knob')")
s = rep(s, "    P.label(pl, 0, h / 2 + 0.021, title, 0.0065)\n    me = bpy.data.meshes.new('ck_screen_%d' % k)",
        "    P.label(pl, ox, h / 2 + 0.021, title, 0.0065)\n    me = bpy.data.meshes.new('ck_screen_%d' % k)")
s = rep(s, "for p in ((-w / 2, -h / 2, 0.0025), (w / 2, -h / 2, 0.0025), (w / 2, h / 2, 0.0025), (-w / 2, h / 2, 0.0025))],",
        "for p in ((ox - w / 2, -h / 2, 0.0025), (ox + w / 2, -h / 2, 0.0025), (ox + w / 2, h / 2, 0.0025), (ox - w / 2, h / 2, 0.0025))],")
s = rep(s, "rot=(-math.degrees(math.atan2(bottom_z(-5.72, 0, WALL) - bottom_z(-5.98, 0, WALL), 0.26)), 0, 0))]",
        "rot=(math.degrees(math.atan2(bottom_z(-5.72, 0, WALL) - bottom_z(-5.98, 0, WALL), 0.26)), 0, 0))]")
wr('chaika_cockpit_station.py', s)

s = rd('chaika_cockpit_rear.py')
s = rep(s, "    SCR6 = screen_unit(PB, pl, 6, 0.336, 0.21, 'ШЛЮЗ', p, keys=False)\n    SCR6.data.transform(Matrix.Translation(M.to_3x3() @ Vector((-0.135, 0, 0))))\n",
        "    SCR6 = screen_unit(PB, pl, 6, 0.336, 0.21, 'ШЛЮЗ', p, keys=False, ox=-0.135)\n")
s = rep(s, "        xw = halfwidth(yc, z0 + 1.95, WALL) - 0.05\n        p += suit(xw - 0.34, yc, z0, 1)",
        "        xw = halfwidth(yc, z0 + 1.65, WALL) - 0.05\n        p += suit(xw - 0.42, yc, z0, 1)")
s = rep(s, "p.append(cyl('rpost', (xb, yc + sy, z0), (xb, yc + sy, z0 + 1.95), 0.016, 10, 'c_frame'))",
        "p.append(cyl('rpost', (xb, yc + sy, z0), (xb, yc + sy, z0 + 1.72), 0.016, 10, 'c_frame'))")
s = rep(s, "cyl('rbar', (xb, yc - 0.30, z0 + 1.93), (xb, yc + 0.30, z0 + 1.93), 0.016, 10, 'c_frame'),",
        "cyl('rbar', (xb, yc - 0.30, z0 + 1.70), (xb, yc + 0.30, z0 + 1.70), 0.016, 10, 'c_frame'),")
for a in ("(0.62, HATCH_Y - 0.06, z0 + 1.45), (0.62, HATCH_Y - 0.10, z0 + 1.45)", "(0.62, HATCH_Y - 0.10, z0 + 1.45), (0.62, HATCH_Y - 0.103, z0 + 1.45)",
          "(0.62, HATCH_Y - 0.12, z0 + 1.22)", "(0.62, HATCH_Y - 0.06, z0 + 1.22), (0.62, HATCH_Y - 0.12, z0 + 1.22)",
          "[(0.62, HATCH_Y - 0.07, z0 + 1.22), (0.62, HATCH_Y - 0.07, z0 + 1.45)]"):
    s = rep(s, a, a.replace('0.62', '0.72'))
wr('chaika_cockpit_rear.py', s)
print('patch_c1 ok')
