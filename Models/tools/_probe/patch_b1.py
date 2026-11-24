# Разовая правка: плотность развёртки агрегатов, длина приёмников давления, цапфа мотогондолы.
import os
T = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rd(n):
    return open(os.path.join(T, n), encoding='utf-8').read()


def wr(n, s):
    open(os.path.join(T, n), 'w', encoding='utf-8').write(s)


def rep(s, a, b):
    assert a in s, a[:70]
    return s.replace(a, b)


s = rd('uvkit.py')
s = rep(s, "def smart_uv(ob, atlas='B', angle=66.0, fill=0.50, **params):", "def smart_uv(ob, atlas='B', angle=66.0, fill=0.62, dens=1.0, **params):")
s = rep(s, "    L = math.sqrt(max(area, 1e-4) / fill)\n", "    L = math.sqrt(max(area, 1e-4) / fill) * dens\n")
wr('uvkit.py', s)

s = rd('chaika_ext_parts.py')
s = rep(s, "def mech(parts, name, origin=(0, 0, 0), atlas='B'):", "def mech(parts, name, origin=(0, 0, 0), atlas='B', dens=1.0):")
s = rep(s, "    smart_uv(ob, atlas)\n    return ob", "    smart_uv(ob, atlas, dens=dens)\n    return ob")
s = rep(s, "    return mech(parts, 'ext_cockpit_proxy')", "    return mech(parts, 'ext_cockpit_proxy', dens=0.33)")
s = rep(s, "    return mech(parts, 'ext_tunnel_fit')", "    return mech(parts, 'ext_tunnel_fit', dens=0.8)")
s = rep(s, "q + n2 * 0.11 + Vector((0, -0.12, 0)), q + n2 * 0.11 + Vector((0, -0.30, 0))]", "q + n2 * 0.11 + Vector((0, -0.06, 0)), q + n2 * 0.11 + Vector((0, -0.13, 0))]")
s = rep(s, "parts.append(cyl('trunnion', (0.42, 0, 0), (0.505, 0, 0), 0.15, 24, 'm_steel', bevel=0.015))", "parts.append(cyl('trunnion', (0.42, 0, 0), (0.472, 0, 0), 0.15, 24, 'm_steel', bevel=0.012))")
s = rep(s, "parts += bolt_circle((0.505, 0, 0), (1, 0, 0), 0.11, 8, 0.026, 0.012)", "parts += bolt_circle((0.472, 0, 0), (1, 0, 0), 0.11, 8, 0.026, 0.010)")
wr('chaika_ext_parts.py', s)

s = rd('chaika_ext.py')
s = rep(s, "    for o in out[2:4]:\n        smart_uv(o, 'B')", "    for o in out[2:4]:\n        smart_uv(o, 'B', dens=0.6)")
wr('chaika_ext.py', s)
print('patch_b1 ok')
