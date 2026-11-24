# Разовая правка: плотная раскладка лицевых панелей (откладывается до finish), перенос задней части кабины
# в атлас B, плотнее обшивка кабины, крупнее подписи.
import os
T = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rd(n):
    return open(os.path.join(T, n), encoding='utf-8').read()


def wr(n, s):
    open(os.path.join(T, n), 'w', encoding='utf-8').write(s)


def rep(s, a, b):
    assert a in s, a[:70]
    return s.replace(a, b)


s = rd('partkit.py')
a = s.index("class Plates:")
b = s.index("# ---------------- органы управления")
s = s[:a] + '''class Plates:
    """Лицевые панели приборов: плоские прямоугольники с точной развёрткой в метрах (карта 'plate'), на которые
    художник текстур наносит надписи. Раскладка по карте делается в finish() — высокие панели в один ряд."""

    def __init__(self, cls='c_panel', row=1.75):
        self.cls, self.row = cls, row
        self.plates, self.items = [], []

    def add(self, M, w, h):
        pl = type('Plate', (), {})()
        pl.M, pl.w, pl.h, pl.u0, pl.v0 = M, w, h, 0.0, 0.0
        pl.tc = lambda x, y, pl=pl: (pl.u0 + x + pl.w / 2, pl.v0 + pl.h / 2 - y)
        self.plates.append(pl)
        return pl

    def label(self, pl, x, y, text, hh=0.0065, color='label', align='c', w=None):
        w = w or max(0.012, len(text) * hh * 0.66)
        self.items.append((pl, dict(type='text', text=text, color=color, align=align),
                           [(x - w / 2, y - hh / 2), (x + w / 2, y - hh / 2), (x - w / 2, y + hh / 2)]))

    def line(self, pl, x0, y0, x1, y1, w=0.0008, color='label'):
        self.items.append((pl, dict(type='line', w=w, color=color), [(x0, y0), (x1, y1)]))

    def box(self, pl, x0, y0, x1, y1, w=0.0008, color='label'):
        self.items.append((pl, dict(type='rect', w=w, color=color), [(x0, y0), (x1, y0), (x0, y1)]))

    def finish(self, name, atlas, dens):
        x = y = rowh = W = 0.0
        for pl in sorted(self.plates, key=lambda p: -p.h):
            if x + pl.w > self.row:
                x, y, rowh = 0.0, y + rowh + 0.012, 0.0
            pl.u0, pl.v0 = x, y
            x += pl.w + 0.012
            rowh, W = max(rowh, pl.h), max(W, x)
        bm = bmesh.new()
        L = uvl(bm)
        for pl in self.plates:
            w, h = pl.w, pl.h
            f = bm.faces.new([bm.verts.new(pl.M @ Vector(p)) for p in ((-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0))])
            for lp, uv in zip(f.loops, ((pl.u0, pl.v0 + h), (pl.u0 + w, pl.v0 + h), (pl.u0 + w, pl.v0), (pl.u0, pl.v0))):
                lp[L].uv = uv
        ob = bm_obj(bm, name, self.cls, None)
        decals = [dict(d, q=[pl.tc(*p) for p in pts]) for pl, d, pts in self.items]
        set_chart(ob, 'plate', W, y + rowh, atlas, dens=dens, decals=decals)
        return ob


''' + s[b:]
wr('partkit.py', s)

s = rd('chaika_cockpit_station.py')
s = s.replace("0.0058)", "0.0064)")
s = rep(s, "    objs.append(P.finish('ck_faceplates', 'A', 4.5))", "    objs.append(P.finish('ck_faceplates', 'A', 4.0))")
wr('chaika_cockpit_station.py', s)

s = rd('chaika_cockpit_rear.py')
s = rep(s, "    objs.append(mech(p, 'ck_rear_cockpit', atlas='A', dens=0.9))", "    objs.append(mech(p, 'ck_rear_cockpit', atlas='B', dens=0.9))")
s = rep(s, "    objs.append(mech([bulk, fr] + fb, 'ck_bulkhead', atlas='A', dens=0.8))", "    objs.append(mech([bulk, fr] + fb, 'ck_bulkhead', atlas='B', dens=0.8))")
s = rep(s, "origin=(0.405, BULKHEAD_Y, DOOR_ZC), atlas='A')", "origin=(0.405, BULKHEAD_Y, DOOR_ZC), atlas='B')")
s = rep(s, "    PB = Plates(row=0.8)", "    PB = Plates(row=0.8)                                                         # лицевая панель пульта")
wr('chaika_cockpit_rear.py', s)

s = rd('chaika_cockpit.py')
s = rep(s, "build_liner(Y_CAP, BULKHEAD_Y, 'ck_liner_cockpit', 'A', 0.5, front=True)", "build_liner(Y_CAP, BULKHEAD_Y, 'ck_liner_cockpit', 'A', 0.8, front=True)")
s = rep(s, "    objs.append(mech(parts, 'ck_structure_cockpit', atlas='A', dens=0.8))", "    objs.append(mech(parts, 'ck_structure_cockpit', atlas='A', dens=0.7))")
wr('chaika_cockpit.py', s)
print('patch_c2 ok')
