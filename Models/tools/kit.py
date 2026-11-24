# kit.py — общие помощники сборки моделей UnrealScenes (Blender 5.0, запуск без окна).
# Подключение: exec(open(os.path.join(TOOLS, 'kit.py'), encoding='utf-8').read())
# Оси: метры, Z вверх, нос по −Y. Геометрию строим bmesh'ем; матрицы объектов — только у подвижных частей.
import bpy, bmesh, math
import bisect as _bis
from mathutils import Vector, Matrix, Euler


# ============================== интерполяция ==============================
def pchip(xs, ys):
    """Монотонная кубическая интерполяция (без выбросов) по узлам xs (по возрастанию) -> функция f(x)."""
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = _bis.bisect_right(xs, x) - 1
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


def frange(a, b, step):
    n = max(1, int(round((b - a) / step)))
    return [a + (b - a) * i / n for i in range(n + 1)]


# ============================== материалы ==============================
_MATDEF = {}


def defmat(name, color, metallic=0.0, rough=0.55, emis=0.0, kind=''):
    _MATDEF[name] = (tuple(color), metallic, rough, emis, kind)


def mat(name):
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    col, met, rough, emis, kind = _MATDEF[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = col
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    b.inputs['Base Color'].default_value = col
    b.inputs['Metallic'].default_value = met
    b.inputs['Roughness'].default_value = rough
    if emis > 0:
        b.inputs['Emission Color'].default_value = col
        b.inputs['Emission Strength'].default_value = emis
    if kind == 'glass':                      # тонкое стекло без преломления: прозрачность + френелевский блик
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        tr.inputs['Color'].default_value = col
        try:
            gl = nt.nodes.new('ShaderNodeBsdfGlossy')
        except Exception:
            gl = nt.nodes.new('ShaderNodeBsdfAnisotropic')
        gl.inputs['Roughness'].default_value = 0.03
        lw = nt.nodes.new('ShaderNodeLayerWeight')          # блик растёт к скользящим углам, одинаково с обеих сторон
        lw.inputs['Blend'].default_value = 0.2
        pw = nt.nodes.new('ShaderNodeMath')
        pw.operation = 'POWER'
        pw.inputs[1].default_value = 3.0
        ml = nt.nodes.new('ShaderNodeMath')
        ml.operation = 'MULTIPLY_ADD'
        ml.inputs[1].default_value = 0.55
        ml.inputs[2].default_value = 0.035
        mx = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(lw.outputs['Facing'], pw.inputs[0])
        nt.links.new(pw.outputs[0], ml.inputs[0])
        nt.links.new(ml.outputs[0], mx.inputs[0])
        nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(gl.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs['Surface'])
    return m


# ============================== сцена и объекты ==============================
def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras, bpy.data.lights, bpy.data.materials,
                 bpy.data.images):
        for d in list(coll):
            if d.users == 0:
                coll.remove(d)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)


def coll(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


_CUR = [None]


def use_coll(name):
    """Все следующие объекты попадают в коллекцию name."""
    _CUR[0] = coll(name) if name else None


def link(ob):
    (_CUR[0] or bpy.context.scene.collection).objects.link(ob)
    return ob


def bm_obj(bm, name, mat_name='clay', smooth=35.0, recalc=False):
    """bmesh -> объект. smooth: угол (градусы) для жёстких рёбер, None — плоское затенение."""
    if recalc:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    names = mat_name if isinstance(mat_name, (list, tuple)) else [mat_name]
    for nm in names:
        me.materials.append(mat(nm))
    ob = bpy.data.objects.new(name, me)
    link(ob)
    if smooth is not None:
        shade(ob, smooth)
    return ob


def shade(ob, angle=35.0):
    me = ob.data
    for p in me.polygons:
        p.use_smooth = True
    try:
        me.set_sharp_from_angle(angle=math.radians(angle))
    except Exception:
        pass
    me.update()
    return ob


def apply_mod(ob, md):
    with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob], selected_editable_objects=[ob]):
        bpy.ops.object.modifier_apply(modifier=md.name)


def solidify(ob, thickness, offset=-1.0):
    md = ob.modifiers.new('solid', 'SOLIDIFY')
    md.thickness = thickness
    md.offset = offset
    md.use_even_offset = True
    md.use_rim = True
    apply_mod(ob, md)
    return ob


def set_origin(ob, p):
    """Перенести опорную точку объекта в точку мира p, не сдвигая геометрию (матрица объекта — только сдвиг)."""
    bpy.context.view_layer.update()
    p = Vector(p)
    ob.data.transform(Matrix.Translation(-p) @ ob.matrix_world)
    ob.matrix_world = Matrix.Translation(p)
    ob.data.update()
    return ob


def set_parent(child, parent):
    bpy.context.view_layer.update()
    mw = child.matrix_world.copy()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()
    child.matrix_world = mw


def empty(name, loc, rot=(0, 0, 0), size=0.2, parent=None, kind='PLAIN_AXES'):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = kind
    e.empty_display_size = size
    link(e)
    e.location = loc
    e.rotation_euler = rot
    if parent is not None:
        set_parent(e, parent)
    return e


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def merge(objs, name, origin=(0, 0, 0)):
    """Слить объекты в один меш (материалы — по именам), опорная точка — origin (мир)."""
    bpy.context.view_layer.update()
    bm = bmesh.new()
    mats = []
    for ob in objs:
        me = ob.data.copy()
        me.transform(ob.matrix_world)
        names = [m.name for m in ob.data.materials if m] or ['clay']
        start = len(bm.faces)
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        for f in bm.faces[start:]:
            nm = names[min(f.material_index, len(names) - 1)]
            if nm not in mats:
                mats.append(nm)
            f.material_index = mats.index(nm)
        bpy.data.meshes.remove(me)
    bmesh.ops.translate(bm, vec=-Vector(origin), verts=bm.verts)
    for ob in objs:
        me = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        if me.users == 0:
            bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for nm in mats:
        me.materials.append(mat(nm))
    ob = bpy.data.objects.new(name, me)
    ob.location = origin
    link(ob)
    return ob


def mirror_x(ob, name=None):
    """Зеркальная копия объекта относительно плоскости X = 0 (нормали остаются наружу)."""
    bpy.context.view_layer.update()
    me = ob.data.copy()
    me.transform(ob.matrix_world)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.scale(bm, vec=Vector((-1, 1, 1)), verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name or ob.name + '_m', me)
    link(o)
    return o


# ============================== геометрия ==============================
def skin(bm, rings, closed=True, cap0=False, cap1=False):
    """Обшивка по сечениям: rings — списки точек одинаковой длины. Возвращает (сетка вершин, грани)."""
    vr = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(vr[0])
    faces = []
    for A, B in zip(vr[:-1], vr[1:]):
        for i in (range(n) if closed else range(n - 1)):
            j = (i + 1) % n
            faces.append(bm.faces.new((A[i], A[j], B[j], B[i])))
    if cap0:
        faces.append(bm.faces.new(list(reversed(vr[0]))))
    if cap1:
        faces.append(bm.faces.new(vr[-1]))
    return vr, faces


def loft(name, rings, closed=True, cap0=True, cap1=True, mat_name='clay', smooth=35.0):
    bm = bmesh.new()
    skin(bm, rings, closed, cap0, cap1)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    return bm_obj(bm, name, mat_name, smooth, recalc=True)


def box(name, size, center, bevel=0.0, segs=2, mat_name='clay', rot=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=segs, profile=0.5, affect='EDGES',
                        clamp_overlap=True)
    if rot:
        bmesh.ops.rotate(bm, cent=(0, 0, 0), verts=bm.verts,
                         matrix=Euler(tuple(math.radians(a) for a in rot), 'XYZ').to_matrix())
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    return bm_obj(bm, name, mat_name, 35.0)


def prism(name, poly, a0, a1, axis='X', bevel=0.0, segs=2, mat_name='clay'):
    """Призма: многоугольник в плоскости, перпендикулярной оси, вытянут от a0 до a1.
    axis='X': точки (y, z); 'Y': точки (x, z); 'Z': точки (x, y)."""
    def P(u, v, a):
        return (a, u, v) if axis == 'X' else ((u, a, v) if axis == 'Y' else (u, v, a))
    bm = bmesh.new()
    A = [bm.verts.new(P(u, v, a0)) for u, v in poly]
    B = [bm.verts.new(P(u, v, a1)) for u, v in poly]
    bm.faces.new(A)
    bm.faces.new(list(reversed(B)))
    k = len(poly)
    for i in range(k):
        j = (i + 1) % k
        bm.faces.new((A[i], A[j], B[j], B[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=segs, profile=0.5, affect='EDGES',
                        clamp_overlap=True)
    return bm_obj(bm, name, mat_name, 35.0)


def _axpt(u, v, h, axis, c):
    if axis == 'Z':
        return Vector((c[0] + u, c[1] + v, c[2] + h))
    if axis == 'Y':
        return Vector((c[0] + v, c[1] + h, c[2] + u))
    return Vector((c[0] + h, c[1] + u, c[2] + v))


def revolve(name, profile, segs=32, axis='Z', center=(0, 0, 0), mat_name='clay', closed=False, cap=True, smooth=35.0):
    """Тело вращения: профиль (r, h), h — вдоль оси от center. Точки с r = 0 — вершины на оси."""
    bm = bmesh.new()
    rings = []
    for r, h in profile:
        if r < 1e-7:
            rings.append([bm.verts.new(_axpt(0, 0, h, axis, center))])
        else:
            rings.append([bm.verts.new(_axpt(r * math.cos(2 * math.pi * i / segs), r * math.sin(2 * math.pi * i / segs),
                                             h, axis, center)) for i in range(segs)])
    pairs = list(zip(rings[:-1], rings[1:]))
    if closed:
        pairs.append((rings[-1], rings[0]))
    for A, B in pairs:
        if len(A) == 1 and len(B) == 1:
            continue
        for i in range(segs):
            j = (i + 1) % segs
            if len(A) == 1:
                bm.faces.new((A[0], B[j], B[i]))
            elif len(B) == 1:
                bm.faces.new((A[i], A[j], B[0]))
            else:
                bm.faces.new((A[i], A[j], B[j], B[i]))
    if cap and not closed:
        if len(rings[0]) > 1:
            bm.faces.new(list(reversed(rings[0])))
        if len(rings[-1]) > 1:
            bm.faces.new(rings[-1])
    return bm_obj(bm, name, mat_name, smooth, recalc=True)


def cyl(name, p0, p1, r, segs=16, mat_name='clay', r1=None, bevel=0.0):
    """Цилиндр (или конус при r1) между двумя точками мира."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    r1 = r if r1 is None else r1
    if bevel > 0:
        prof = [(r - bevel, 0.0), (r, bevel), (r1, L - bevel), (r1 - bevel, L)]
    else:
        prof = [(r, 0.0), (r1, L)]
    ob = revolve(name, prof, segs=segs, axis='Z', mat_name=mat_name)
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    ob.data.transform(Matrix.Translation(p0) @ q.to_matrix().to_4x4())
    ob.data.update()
    return ob


def pipe(name, pts, r, mat_name='clay', sides=8, res=4, smooth=True):
    """Труба по точкам мира (плавные изгибы при smooth=True)."""
    cu = bpy.data.curves.new(name + '_cu', 'CURVE')
    cu.dimensions = '3D'
    cu.resolution_u = res
    cu.bevel_depth = r
    cu.bevel_resolution = max(0, (sides - 4) // 2)
    cu.use_fill_caps = True
    sp = cu.splines.new('BEZIER')
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = 'AUTO' if smooth else 'VECTOR'
    tmp = bpy.data.objects.new(name + '_cu', cu)
    bpy.context.scene.collection.objects.link(tmp)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp, do_unlink=True)
    bpy.data.curves.remove(cu)
    me.name = name
    me.materials.clear()
    me.materials.append(mat(mat_name))
    ob = bpy.data.objects.new(name, me)
    link(ob)
    shade(ob, 40)
    return ob


def airfoil(n=18, thick=0.12, camber=0.02):
    """Профиль крыла: список (s, t) при хорде 1 — от задней кромки по верху к носку и по низу обратно (2n точек)."""
    def yt(x):
        return 5 * thick * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x ** 2 + 0.2843 * x ** 3 - 0.1036 * x ** 4)
    xs = [0.5 * (1 - math.cos(math.pi * i / n)) for i in range(n + 1)]
    up = [(x, 4 * camber * x * (1 - x) + yt(x)) for x in reversed(xs)]          # TE -> LE
    lo = [(x, 4 * camber * x * (1 - x) - yt(x)) for x in xs[1:-1]]              # LE -> TE (без концов)
    return up + lo


def cut(bm, co, no, pred=None):
    """Разрезать грани плоскостью (ничего не удаляя). pred(грань) — какие грани резать."""
    faces = [f for f in bm.faces if pred is None or pred(f)]
    if not faces:
        return
    es = {e for f in faces for e in f.edges}
    vs = {v for f in faces for v in f.verts}
    bmesh.ops.bisect_plane(bm, geom=list(vs) + list(es) + faces, dist=1e-6, plane_co=Vector(co), plane_no=Vector(no),
                           clear_outer=False, clear_inner=False)


def extract(bm, faces):
    """Вынести грани в новый bmesh (из исходного удалить)."""
    bm2 = bmesh.new()
    vmap = {}
    for f in faces:
        vs = []
        for v in f.verts:
            if v not in vmap:
                vmap[v] = bm2.verts.new(v.co)
            vs.append(vmap[v])
        nf = bm2.faces.new(vs)
        nf.material_index = f.material_index
        nf.smooth = f.smooth
    bmesh.ops.delete(bm, geom=faces, context='FACES')
    return bm2
