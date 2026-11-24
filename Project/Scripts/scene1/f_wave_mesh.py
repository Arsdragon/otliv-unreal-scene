# Generate the 2100 m wave as a static mesh (Geometry Script). Local origin = crest line at y=0; front faces -X.
import unreal, math
H = 2100.0
# profile control points (x, z) in metres, from the front foot over the crest to the back
CP = [(-1700, 0.0), (-1400, 2.0), (-1150, 14), (-950, 45), (-770, 115), (-610, 240), (-470, 420), (-350, 650),
      (-250, 900), (-172, 1170), (-112, 1450), (-74, 1710), (-58, 1880), (-60, 1985), (-46, 2060), (-18, 2094),
      (20, 2098), (90, 2075), (250, 2000), (550, 1840), (1050, 1580), (2000, 1160), (3500, 720), (6000, 340),
      (10000, 130), (18000, 45), (30000, 18), (45000, 10)]
SUN = math.radians(10.0)

def catmull(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return tuple(0.5 * ((2 * p1[i]) + (-p0[i] + p2[i]) * t + (2 * p0[i] - 5 * p1[i] + 4 * p2[i] - p3[i]) * t2 +
                        (-p0[i] + 3 * p1[i] - 3 * p2[i] + p3[i]) * t3) for i in range(2))

def profile():
    pts = []
    P = [CP[0]] + CP + [CP[-1]]
    for i in range(1, len(P) - 2):
        a, b = P[i], P[i + 1]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        hi = max(a[1], b[1])
        step = 25.0 if hi > 1500 else (45.0 if hi > 300 else 160.0)
        if a[0] > 3000: step = 1500.0
        n = max(1, int(L / step))
        for k in range(n):
            pts.append(catmull(P[i - 1], a, b, P[i + 2], k / n))
    pts.append(CP[-1])
    return pts

def htop_fn(pts):
    ic = max(range(len(pts)), key=lambda i: pts[i][1])
    back = pts[ic:]
    front = pts[:ic + 1]
    def h(x):
        if x >= back[0][0]:
            for j in range(len(back) - 1):
                if back[j][0] <= x <= back[j + 1][0]:
                    t = (x - back[j][0]) / max(1e-6, back[j + 1][0] - back[j][0])
                    return back[j][1] + t * (back[j + 1][1] - back[j][1])
            return 0.0
        best = 0.0
        for j in range(len(front) - 1):
            x0, x1 = sorted((front[j][0], front[j + 1][0]))
            if x0 <= x <= x1:
                t = 0.0 if x1 == x0 else (x - front[j][0]) / (front[j + 1][0] - front[j][0])
                best = max(best, front[j][1] + t * (front[j + 1][1] - front[j][1]))
        return best
    return h, ic

def thickness(p, h):
    # total water path along the ray toward the sun (re-entries included)
    dx, dz = math.cos(SUN), math.sin(SUN)
    x, z, d, acc = p[0] + dx * 0.5, p[1] + dz * 0.5, 0.0, 0.0
    step = 4.0
    while z < 2200.0 and d < 25000.0:
        if z < h(x): acc += step
        x += dx * step; z += dz * step; d += step
        step = 4.0 if d < 200 else 25.0
    return acc

def noise1(y, seed):
    # smooth 1D value noise
    i = math.floor(y); f = y - i
    def r(k): return (math.sin((k + seed * 17.13) * 127.1) * 43758.5453) % 1.0
    u = f * f * (3 - 2 * f)
    return (r(i) * (1 - u) + r(i + 1) * u) * 2 - 1

def ycols():
    ys = [0.0]
    y = 0.0
    while y < 90000:
        a = abs(y)
        y += 60.0 if a < 4000 else (150.0 if a < 16000 else 700.0)
        ys.append(y)
    return [-v for v in reversed(ys[1:])] + ys

def ridge(y, seed):
    return 1.0 - abs(noise1(y, seed))


def _raw_scale(y):
    # peaks and saddles: +-150..300 m with a 5..20 km step, plus small detail
    r = ridge(y / 4500.0, 5)
    return 1.0 + 0.10 * noise1(y / 8000.0, 1) + 0.16 * (r * r - 0.40) + 0.02 * noise1(y / 900.0, 2) + 0.006 * noise1(y / 210.0, 3)


_SC0 = None


def col_params(y):
    """per-column crest shape: (height scale, forward lean of the front, x offset of the arc)"""
    global _SC0
    if _SC0 is None:
        _SC0 = _raw_scale(0.0)
    # near the ship (y = 0) the crest is 2140 m, as the on-board voice reports
    sc = _raw_scale(y) - (_SC0 - 1.02) * math.exp(-(y / 6000.0) ** 2)
    sc = max(0.75, sc)
    end = min(1.0, max(0.0, (90000 - abs(y)) / 20000.0))
    sc *= (0.25 + 0.75 * end)
    lean = 1.0 + 0.25 * noise1(y / 1700.0, 4)
    xo = y * y / (2 * 200000.0)
    return sc, lean, xo


def build():
    pts = profile()
    h, ic = htop_fn(pts)
    s, acc = [], 0.0
    for i, p in enumerate(pts):
        if i: acc += math.hypot(p[0] - pts[i - 1][0], p[1] - pts[i - 1][1])
        s.append(acc)
    th = [thickness(p, h) if i <= ic + 2 else 3000.0 for i, p in enumerate(pts)]
    ys = ycols()
    R = 200000.0
    V, UV, C = [], [], []
    for y in ys:
        sc, lean, xo = col_params(y)
        for i, p in enumerate(pts):
            zf = p[1] / H
            x = p[0] * (lean if p[0] < 0 else 1.0)
            V.append(unreal.Vector((x + xo) * 100.0, y * 100.0, p[1] * sc * 100.0))
            UV.append(unreal.Vector2D(y / 100.0, s[i] / 100.0))
            C.append(unreal.LinearColor(min(1.0, th[i] * sc / 1500.0), zf, 1.0 if i <= ic else 0.0, 1.0))
    n = len(pts)
    T = []
    for j in range(len(ys) - 1):
        for i in range(n - 1):
            a, b = j * n + i, j * n + i + 1
            c, d = (j + 1) * n + i, (j + 1) * n + i + 1
            T.append(unreal.IntVector(a, c, b)); T.append(unreal.IntVector(b, c, d))
    return V, UV, C, T, len(pts), len(ys)

def make(asset='/Game/Scene1/Wave/SM_Wave', flip=False):
    V, UV, C, T, n, m = build()
    if flip:
        T = [unreal.IntVector(t.x, t.z, t.y) for t in T]
    buf = unreal.GeometryScriptSimpleMeshBuffers()
    buf.vertices = V; buf.uv0 = UV; buf.vertex_colors = C; buf.triangles = T
    mesh = unreal.DynamicMesh()
    unreal.GeometryScript_MeshEdits.append_buffers_to_mesh(mesh, buf, 0)
    unreal.GeometryScript_Normals.recompute_normals(mesh, unreal.GeometryScriptCalculateNormalsOptions())
    unreal.GeometryScript_Normals.compute_tangents(mesh, unreal.GeometryScriptTangentsOptions())
    if unreal.EditorAssetLibrary.does_asset_exist(asset):
        sm = unreal.EditorAssetLibrary.load_asset(asset)
        unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(mesh, sm, unreal.GeometryScriptCopyMeshToAssetOptions(), unreal.GeometryScriptMeshWriteLOD())
    else:
        o = unreal.GeometryScriptCreateNewStaticMeshAssetOptions()
        o.enable_collision = False
        o.enable_nanite = False
        sm, out = unreal.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(mesh, asset, o)
    unreal.EditorAssetLibrary.save_loaded_asset(sm)
    print('wave mesh', n, 'x', m, 'verts', len(V), 'tris', len(T))
    return sm
