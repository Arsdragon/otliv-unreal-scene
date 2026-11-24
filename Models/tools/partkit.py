# partkit.py — общие заготовки агрегатов и приборов (подключать после kit.py, chaika_shape.py, uvkit.py).


def mech(parts, name, origin=(0, 0, 0), atlas='B', dens=1.0):
    """Слить детали в один объект с опорной точкой origin и автоматической развёрткой."""
    ob = merge(parts, name, origin)
    shade(ob, 35)
    smart_uv(ob, atlas, dens=dens)
    return ob


def place(objs, M):
    for o in objs:
        o.data.transform(M)
        o.data.update()
    return objs


def hexbolt(p, n, d=0.03, h=0.012, m='m_steel'):
    p, n = Vector(p), Vector(n).normalized()
    return cyl('bolt', p - n * 0.003, p + n * h, d / 2, 6, m)


def bolt_circle(c, axis, r, n, d=0.028, h=0.012, m='m_steel', phase=0.0):
    c, a = Vector(c), Vector(axis).normalized()
    e1 = a.cross(Vector((0, 0, 1)) if abs(a.z) < 0.9 else Vector((1, 0, 0))).normalized()
    e2 = a.cross(e1)
    return [hexbolt(c + (e1 * math.cos(t) + e2 * math.sin(t)) * r, a, d, h, m)
            for t in (phase + 2 * math.pi * k / n for k in range(n))]


def rrect(w, h, r, n=5):
    """Скруглённый прямоугольник w × h с центром в нуле: точки против часовой стрелки."""
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90.0 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def torus(name, c, R0, r, axis='Y', mat_name='m_steel', segs=28, n=8):
    prof = [(R0 + r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    return revolve(name, prof, segs, axis, c, mat_name, closed=True, cap=False)


def frame_M(p, x, y):
    """Матрица местных осей: начало p, ось X вдоль x, ось Y — ближайшая к y, Z = X × Y."""
    X = Vector(x).normalized()
    Z = X.cross(Vector(y)).normalized()
    Y = Z.cross(X)
    return Matrix.Translation(Vector(p)) @ Matrix((X, Y, Z)).transposed().to_4x4()


class Plates:
    """Лицевые панели приборов: плоские прямоугольники с точной развёрткой в метрах (карта 'plate'), на которые
    художник текстур наносит надписи. Раскладка по карте делается в finish() — высокие панели в один ряд."""

    def __init__(self, cls='c_panel', row=1.75, glow=False):
        self.cls, self.row, self.glow = cls, row, glow
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
        decals = [dict(d, q=[pl.tc(*p) for p in pts], glow=self.glow) for pl, d, pts in self.items]
        set_chart(ob, 'plate', W, y + rowh, atlas, dens=dens, decals=decals)
        return ob


# ---------------- органы управления (в местных осях панели: плоскость XY, +Z — от панели к пилоту) ----------------
def toggle(x, y, up=True, guard=False):
    s = 1 if up else -1
    o = [cyl('nut', (x, y, 0), (x, y, 0.0035), 0.0058, 6, 'm_steel'),
         cyl('lev', (x, y, 0.003), (x, y + s * 0.0065, 0.020), 0.0023, 8, 'm_alu', r1=0.0031)]
    if guard:
        for sx in (-0.0085, 0.0085):
            o.append(box('gd', (0.0016, 0.020, 0.018), (x + sx, y, 0.009), mat_name='m_orange'))
        o.append(box('gd', (0.0186, 0.0016, 0.018), (x, y + 0.0105, 0.009), mat_name='m_orange'))
    return o


def knob(x, y, r=0.011):
    return [revolve('kn', [(0.0, 0.0), (r * 1.3, 0.0), (r * 1.3, 0.004), (r, 0.006), (r * 0.94, 0.018), (r * 0.7, 0.020), (0.0, 0.020)],
                    14, 'Z', (x, y, 0), 'c_knob'),
            box('ptr', (0.0016, r * 0.9, 0.0012), (x, y + r * 0.5, 0.0204), mat_name='c_placard')]


def button(x, y, w=0.012, h=0.010, m='c_plastic'):
    return [box('bt', (w, h, 0.005), (x, y, 0.0025), bevel=0.0012, segs=1, mat_name=m)]


def breaker(x, y):
    return [cyl('cb', (x, y, 0), (x, y, 0.009), 0.0042, 8, 'c_knob'), cyl('cbr', (x, y, 0), (x, y, 0.002), 0.0062, 8, 'm_steel')]
