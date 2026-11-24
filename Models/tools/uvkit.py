# uvkit.py — развёртки и атласы текстур. Подключать после kit.py.
# Схема: у каждого объекта развёртка сначала в МЕТРАХ в своей «карте» (chart), затем карты раскладываются по
# атласам 4096 × 4096 (A — корпус, B — агрегаты), а для художника текстур (tools/chaika_tex.py) выгружаются
# layout.json (где какая карта лежит) и faces_<атлас>.npz (каждая грань: контур в атласе, класс материала, высота).
import json
import numpy as np

ATLAS = 4096
PAD = 8


def uvl(bm):
    return bm.loops.layers.uv.verify()


def skin_uv(bm, rings, uvr, closed=True, mat_fn=None):
    """Обшивка по сечениям с развёрткой. rings — списки точек; uvr — списки (u, v) в метрах той же длины
    (для замкнутых сечений на один элемент длиннее: последняя запись — шов). mat_fn(i, j) -> индекс материала."""
    L = uvl(bm)
    vr = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(vr[0])
    faces = []
    for i in range(len(vr) - 1):
        A, B = vr[i], vr[i + 1]
        for j in (range(n) if closed else range(n - 1)):
            k = (j + 1) % n
            try:
                f = bm.faces.new((A[j], A[k], B[k], B[j]))
            except ValueError:
                continue
            for lp, uv in zip(f.loops, (uvr[i][j], uvr[i][j + 1], uvr[i + 1][j + 1], uvr[i + 1][j])):
                lp[L].uv = uv
            if mat_fn:
                f.material_index = mat_fn(i, j)
            f.smooth = True
            faces.append(f)
    return vr, faces


def ring_len(ring, closed=True):
    """Накопленная длина вдоль сечения: n (+1 для замкнутого) значений."""
    out = [0.0]
    pts = list(ring) + ([ring[0]] if closed else [])
    for a, b in zip(pts[:-1], pts[1:]):
        out.append(out[-1] + (Vector(b) - Vector(a)).length)
    return out


def revolve_rings(profile, segs, axis='Y', center=(0, 0, 0)):
    """Кольца тела вращения по профилю (r, h) (ось — как в kit.revolve) и длина вдоль профиля."""
    rings, u = [], [0.0]
    for k, (r, h) in enumerate(profile):
        r = max(r, 1e-4)
        rings.append([_axpt(r * math.cos(2 * math.pi * i / segs), r * math.sin(2 * math.pi * i / segs), h, axis, center)
                      for i in range(segs)])
        if k:
            u.append(u[-1] + math.hypot(profile[k][0] - profile[k - 1][0], profile[k][1] - profile[k - 1][1]))
    return rings, u


def revolve_uv(bm, profile, segs, rref, axis='Y', center=(0, 0, 0), mat_fn=None, u0=0.0, v0=0.0):
    """Тело вращения с развёрткой: u — длина вдоль профиля, v — дуга на опорном радиусе rref."""
    rings, u = revolve_rings(profile, segs, axis, center)
    uvr = [[(u0 + u[i], v0 + 2 * math.pi * rref * j / segs) for j in range(segs + 1)] for i in range(len(rings))]
    return skin_uv(bm, rings, uvr, True, mat_fn)


def set_chart(ob, kind, w, h, atlas, **params):
    ob['chart'] = json.dumps(dict(kind=kind, w=w, h=h, atlas=atlas, **params))


def shift_uv(ob, du, dv):
    L = ob.data.uv_layers.active.data
    for d in L:
        d.uv = (d.uv[0] + du, d.uv[1] + dv)


def smart_uv(ob, atlas='B', angle=66.0, fill=0.62, dens=1.0, **params):
    """Автоматическая развёртка агрегата (островами по углу) и перевод её в метры."""
    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name='UVMap')
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=0.004, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    area = sum(p.area for p in me.polygons)
    L = math.sqrt(max(area, 1e-4) / fill) * dens
    for d in me.uv_layers.active.data:
        d.uv = (d.uv[0] * L, d.uv[1] * L)
    set_chart(ob, 'mech', L, L, atlas, **params)
    return L


def _shelf(items, W, H, s):
    """Раскладка прямоугольников полками. items = [(имя, w_м, h_м)], s — пикселей на метр. -> {имя: (x, y)} или None."""
    x = y = rowh = 0
    out = {}
    for nm, w, h in sorted(items, key=lambda t: -t[2]):
        pw, ph = int(math.ceil(w * s)) + PAD, int(math.ceil(h * s)) + PAD
        if pw > W:
            return None
        if x + pw > W:
            x, y, rowh = 0, y + rowh, 0
        if y + ph > H:
            return None
        out[nm] = (x, y)
        x += pw
        rowh = max(rowh, ph)
    return out


def pack_atlas(objs, atlas, fixed=None, smax=1e9):
    """Разложить карты объектов по атласу. fixed = (имя объекта, пикселей на метр): эта карта кладётся в левый
    верхний угол в заданном масштабе, остальные — в полосу под ней. Возвращает {имя: (x0, y0, масштаб)}."""
    charts = {}
    for o in objs:
        if o.get('chart'):
            c = json.loads(o['chart'])
            if c['atlas'] == atlas:
                charts[o.name] = c
    rect = {}
    y0 = 0
    if fixed:
        nm, s = fixed
        rect[nm] = (PAD // 2, PAD // 2, s)
        y0 = int(math.ceil(charts[nm]['h'] * charts[nm].get('dens', 1.0) * s)) + PAD
        s_hi = min(smax, s * 1.6)
    else:
        s_hi = smax
    items = [(nm, c['w'] * c.get('dens', 1.0), c['h'] * c.get('dens', 1.0)) for nm, c in charts.items() if nm not in rect]
    lo, hi = 1.0, min(s_hi, 3000.0)
    best = None
    for _ in range(40):
        mid = (lo + hi) / 2
        r = _shelf(items, ATLAS - PAD, ATLAS - y0 - PAD, mid)
        if r:
            best, lo = (r, mid), mid
        else:
            hi = mid
    r, s = best
    for nm, (x, y) in r.items():
        rect[nm] = (x + PAD // 2, y0 + y + PAD // 2, s)
    return rect, charts


def apply_atlas(objs, rects):
    """Перевести развёртки из метров в координаты атласа (начало — левый верхний угол картинки)."""
    for o in objs:
        src = o.get('chart_of') or o.name
        if src not in rects or o.type != 'MESH' or not o.data.uv_layers:
            continue
        x0, y0, s = rects[src]
        so = bpy.data.objects.get(src)
        s = s * (json.loads(so['chart']).get('dens', 1.0) if so and so.get('chart') else 1.0)
        o['rect'] = [x0, y0, s]
        for d in o.data.uv_layers.active.data:
            d.uv = ((x0 + d.uv[0] * s) / ATLAS, 1.0 - (y0 + d.uv[1] * s) / ATLAS)


def layout_of(rects, charts):
    """Записи для layout.json: прямоугольник карты в пикселях атласа, масштаб, параметры."""
    out = {}
    for nm, (x0, y0, s) in rects.items():
        c = charts[nm]
        k = s * c.get('dens', 1.0)
        out[nm] = dict(c, rect=[x0, y0, x0 + c['w'] * k, y0 + c['h'] * k], scale=s)
    return out


def dump_faces(objs, atlas, cls_of, path, charts):
    """Выгрузить грани атласа для художника текстур: контуры в пикселях, класс материала, высота и наклон."""
    off, uv, cls, zz, nz = [0], [], [], [], []
    bpy.context.view_layer.update()
    for o in objs:
        src = o.get('chart_of') or o.name
        if o.type != 'MESH' or src not in charts or not o.data.uv_layers:
            continue
        me = o.data
        L = me.uv_layers.active.data
        mw = o.matrix_world
        rot = mw.to_3x3()
        names = [m.name if m else '' for m in me.materials]
        for p in me.polygons:
            c = cls_of.get(names[p.material_index] if names else '', 0)
            if c >= 30:
                continue
            for li in p.loop_indices:
                u = L[li].uv
                uv.append((u[0] * ATLAS, (1.0 - u[1]) * ATLAS))
            off.append(len(uv))
            cls.append(c)
            zz.append((mw @ p.center).z)
            nz.append((rot @ p.normal).normalized().z)
    np.savez_compressed(path, off=np.array(off, np.int32), uv=np.array(uv, np.float32), cls=np.array(cls, np.uint8),
                        z=np.array(zz, np.float32), nz=np.array(nz, np.float32))
    return len(cls)
