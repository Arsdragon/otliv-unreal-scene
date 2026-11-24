# chaika_shape.py — общая форма посадочного модуля «Чайка»: корпус по сечениям и фонарь кабины.
# Один и тот же код режет остекление и для chaika_ext, и для chaika_cockpit — переплёты совпадают по построению.
# Подключать после kit.py. Оси: метры, Z вверх, нос по −Y, начало координат — центр под опорами на грунте.
import math

# ---------------- главные размеры ----------------
EYE = (0.0, -5.20, 2.78)        # глаза пилота (метка eye_pilot)
FLOOR_Z = 1.66                  # пол кабины и шлюза
WALL = 0.065                    # толщина стенки корпуса (до внутренней обшивки)
NOSE_Y, NOSE_Z, TAIL_Y = -7.00, 2.05, 6.40    # носок и срез хвоста корпуса (сопла кормовых двигателей — до +7.00)
BULKHEAD_Y = -2.30              # переборка кабина / шлюз
HATCH_Y = 2.00                  # задняя стенка шлюза с люком (она же передняя стенка ниши трапа)
TUN_X, TUN_Y1, TUN_ZTOP = 0.80, 4.62, 3.50   # ниша трапа: полуширина, задний край, потолок
RAMP_HINGE_Z = 1.40
RAMP_LEN = math.hypot(TUN_Y1 - HATCH_Y, 3.10 - RAMP_HINGE_Z)
RAMP_CLOSED = math.degrees(math.atan2(3.10 - RAMP_HINGE_Z, TUN_Y1 - HATCH_Y))   # углы — вокруг +X от горизонтали
RAMP_T = 0.10                   # толщина трапа


def _ramp_open():
    a = 0.3
    for _ in range(30):         # низ конца трапа касается грунта: L sin a + T cos a = высота петли
        a = math.asin(max(-1, min(1, (RAMP_HINGE_Z - RAMP_T * math.cos(a)) / RAMP_LEN)))
    return -math.degrees(a)


RAMP_OPEN = _ramp_open()

# ---------------- сечения корпуса ----------------
# Сечение — скруглённый шестиугольник: киль K(0, zk) — скула C(W, zch) — плечо S(Ws, zs) — конёк T(0, zt).
# Днище килеватое («лодка»: корабль держится на плаву), борта завалены внутрь, крыша с лёгким скатом.
# rc, rs, rk, rt — радиусы скругления скулы, плеча, киля и конька (9 = «сколько влезет», нос круглый).
KEYS = [
    #  y      zk     W     zch   Ws    zs     zt     rc    rs    rk   rt
    (-7.00, 2.050, 0.00, 2.05, 0.00, 2.05, 2.050, 9, 9, 9, 9),
    (-6.95, 1.980, 0.17, 2.07, 0.15, 2.14, 2.200, 9, 9, 9, 9),
    (-6.80, 1.850, 0.40, 2.06, 0.36, 2.30, 2.440, 9, 9, 9, 9),
    (-6.50, 1.690, 0.69, 2.03, 0.62, 2.55, 2.800, 9, 9, 9, 9),
    (-6.00, 1.520, 0.99, 1.97, 0.88, 2.86, 3.220, 9, 9, 9, 9),
    (-5.50, 1.410, 1.18, 1.90, 1.03, 3.08, 3.520, 9, 9, 9, 9),
    (-5.00, 1.360, 1.31, 1.84, 1.12, 3.23, 3.710, 0.60, 0.60, 9, 9),
    (-4.40, 1.350, 1.41, 1.78, 1.18, 3.33, 3.800, 0.40, 0.48, 9, 9),
    (-3.00, 1.350, 1.62, 1.69, 1.26, 3.42, 3.800, 0.18, 0.34, 0.6, 2.2),
    (-1.50, 1.350, 1.75, 1.66, 1.30, 3.45, 3.800, 0.13, 0.28, 0.4, 2.2),
    (0.00, 1.350, 1.75, 1.66, 1.30, 3.45, 3.800, 0.13, 0.28, 0.4, 2.2),
    (2.00, 1.350, 1.75, 1.66, 1.30, 3.45, 3.800, 0.13, 0.28, 0.4, 2.2),
    (3.20, 2.135, 1.62, 2.42, 1.24, 3.47, 3.800, 0.13, 0.26, 0.3, 2.0),
    (4.62, 3.060, 1.40, 3.20, 1.12, 3.52, 3.800, 0.10, 0.18, 0.3, 1.8),
    (5.60, 3.100, 1.28, 3.22, 1.05, 3.52, 3.770, 0.09, 0.15, 0.3, 1.6),
    (6.40, 3.140, 1.18, 3.24, 0.98, 3.50, 3.720, 0.08, 0.13, 0.3, 1.4),
]
_kn = ('zk', 'W', 'zch', 'Ws', 'zs', 'zt', 'rc', 'rs', 'rk', 'rt')
_ky = [k[0] for k in KEYS]
_kf = {nm: pchip(_ky, [k[i + 1] for k in KEYS]) for i, nm in enumerate(_kn)}
SEG_K, SEG_B, SEG_C, SEG_S, SEG_SH, SEG_R, SEG_T = 3, 7, 8, 8, 8, 6, 8     # сегментов на половину сечения: 48
NTH = 2 * (SEG_K + SEG_B + SEG_C + SEG_S + SEG_SH + SEG_R + SEG_T)


def sec(y):
    return {nm: f(y) for nm, f in _kf.items()}


def _fil(A, B, C, r):
    """Скругление угла B между BA и BC: точки касания, центр, радиус (центр None — прямой участок)."""
    ax, az, cx, cz = A[0] - B[0], A[1] - B[1], C[0] - B[0], C[1] - B[1]
    la, lc = math.hypot(ax, az), math.hypot(cx, cz)
    if la < 1e-9 or lc < 1e-9:
        return B, B, None, 0.0
    ux, uz, vx, vz = ax / la, az / la, cx / lc, cz / lc
    phi = math.acos(max(-1.0, min(1.0, ux * vx + uz * vz)))
    tmax = 0.48 * min(la, lc)
    if phi > math.pi - 0.02 or r < 1e-4:
        t = min(0.012, tmax)
        return (B[0] + ux * t, B[1] + uz * t), (B[0] + vx * t, B[1] + vz * t), None, 0.0
    t = r / math.tan(phi / 2)
    if t > tmax:
        t = tmax
        r = t * math.tan(phi / 2)
    bx, bz = ux + vx, uz + vz
    bl = math.hypot(bx, bz)
    d = r / math.sin(phi / 2)
    return ((B[0] + ux * t, B[1] + uz * t), (B[0] + vx * t, B[1] + vz * t), (B[0] + bx / bl * d, B[1] + bz / bl * d), r)


def _arcpts(P1, P2, c, r, n):
    if c is None:
        return [(P1[0] + (P2[0] - P1[0]) * k / n, P1[1] + (P2[1] - P1[1]) * k / n) for k in range(n + 1)]
    a1 = math.atan2(P1[1] - c[1], P1[0] - c[0])
    da = math.atan2(P2[1] - c[1], P2[0] - c[0]) - a1
    while da > math.pi:
        da -= 2 * math.pi
    while da < -math.pi:
        da += 2 * math.pi
    return [(c[0] + r * math.cos(a1 + da * k / n), c[1] + r * math.sin(a1 + da * k / n)) for k in range(n + 1)]


def _offset_poly(K, C, S, T, d):
    def off(P, Q):
        dx, dz = Q[0] - P[0], Q[1] - P[1]
        L = math.hypot(dx, dz)
        return (P[0] - dz / L * d, P[1] + dx / L * d), (dx, dz)

    def isect(p, a, q, b):
        den = a[0] * b[1] - a[1] * b[0]
        t = ((q[0] - p[0]) * b[1] - (q[1] - p[1]) * b[0]) / den
        return (p[0] + a[0] * t, p[1] + a[1] * t)

    def at_x0(p, a):
        return (0.0, p[1] - p[0] / a[0] * a[1])
    (b0, bd), (s0, sd), (r0, rd) = off(K, C), off(C, S), off(S, T)
    return at_x0(b0, bd), isect(b0, bd, s0, sd), isect(s0, sd, r0, rd), at_x0(r0, rd)


def _half(s, inset=0.0):
    """Правая половина сечения (x >= 0) от киля до конька: 49 точек (x, z), постоянное число точек на каждом
    участке — линии скулы и плеча идут вдоль корпуса ровными рядами сетки."""
    K, C, S, T = (0.0, s['zk']), (s['W'], s['zch']), (s['Ws'], s['zs']), (0.0, s['zt'])
    rk, rc, rs, rt = s['rk'], s['rc'], s['rs'], s['rt']
    if inset > 0:
        K, C, S, T = _offset_poly(K, C, S, T, inset)
        rk, rc, rs, rt = (max(0.02, r - inset) for r in (rk, rc, rs, rt))
    Cm, Sm = (-C[0], C[1]), (-S[0], S[1])
    k1, k2, kc, kr = _fil(Cm, K, C, rk)
    c1, c2, cc, cr = _fil(K, C, S, rc)
    s1, s2, sc, sr = _fil(C, S, T, rs)
    t1, t2, tc, tr = _fil(S, T, Sm, rt)
    pts = _arcpts(k1, k2, kc, kr, 2 * SEG_K)[SEG_K:]
    pts += _arcpts(k2, c1, None, 0, SEG_B)[1:]
    pts += _arcpts(c1, c2, cc, cr, SEG_C)[1:]
    pts += _arcpts(c2, s1, None, 0, SEG_S)[1:]
    pts += _arcpts(s1, s2, sc, sr, SEG_SH)[1:]
    pts += _arcpts(s2, t1, None, 0, SEG_R)[1:]
    pts += _arcpts(t1, t2, tc, tr, 2 * SEG_T)[1:SEG_T + 1]
    pts[0] = (0.0, pts[0][1])
    pts[-1] = (0.0, pts[-1][1])
    return pts


def ring(y, n=NTH, inset=0.0):
    """Сечение корпуса на станции y: точки (x, y, z) от киля по правому борту через конёк и по левому борту.
    Точка i и точка n−i зеркальны."""
    half = _half(sec(y), inset)
    return [(x, y, z) for x, z in half] + [(-x, y, z) for x, z in reversed(half[1:-1])]


def halfwidth(y, z, inset=0.0):
    """Полуширина корпуса на станции y на высоте z (0, если выше или ниже корпуса)."""
    hp = _half(sec(y), inset)
    best = 0.0
    for a, b in zip(hp[:-1], hp[1:]):
        if (a[1] - z) * (b[1] - z) <= 0 and a[1] != b[1]:
            best = max(best, a[0] + (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1]))
    return best


def _zs_at(y, x, inset):
    hp = _half(sec(y), inset)
    x = abs(x)
    out = []
    for a, b in zip(hp[:-1], hp[1:]):
        if (a[0] - x) * (b[0] - x) <= 0 and a[0] != b[0]:
            out.append(a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]))
    return out or [hp[0][1], hp[-1][1]]


def top_z(y, x=0.0, inset=0.0):
    """Высота верхней поверхности корпуса на станции y при боковом смещении x."""
    return max(_zs_at(y, x, inset))


def bottom_z(y, x=0.0, inset=0.0):
    return min(_zs_at(y, x, inset))


def hull_stations(y0=-6.95, y1=TAIL_Y):
    """Станции обшивки: в носу (остекление) — часто, дальше реже."""
    ys = [y for y in frange(-6.95, -4.30, 0.05) if y0 - 1e-6 <= y <= y1 + 1e-6]
    ys += [y for y in frange(-4.20, 6.40, 0.10) if y0 - 1e-6 <= y <= y1 + 1e-6]
    if abs(ys[0] - y0) > 1e-6:
        ys.insert(0, y0)
    if abs(ys[-1] - y1) > 1e-6:
        ys.append(y1)
    return ys


# ---------------- фонарь кабины ----------------
# Семь крупных окон. Главное — центральное панорамное стекло wind_C: ±52° по азимуту от глаз пилота и от
# подоконника до хребтовой балки над головой, без единого переплёта («главный экран фильма»).
# Две стойки — вертикальные плоскости через вертикаль глаз пилота (он видит их «с торца»), все переплёты
# вытянуты внутрь по линии взгляда, поэтому изнутри видна только их лицевая ширина (36 мм, меньше 2°).
Y_CAP = -6.80          # впереди — глухой носовой обтекатель
Y_AFT = -4.48          # задний шпангоут остекления (на высоте подоконника), наклонён вперёд
AFT_RAKE = 0.30        # наклон заднего шпангоута: на каждый метр высоты — 0,3 м вперёд
Y_CHIN_AFT = -5.45     # задний край подбородочных окон (дальше пол кабины)
Z_SILL = 2.31          # подоконный пояс: ниже — подбородочные окна
Z_HEAD = 3.16          # пояс над боковыми окнами (только по бортам, за стойками): выше — надбровные окна
AZ_POST = 52.0         # азимут двух стоек от направления «вперёд», градусы
AZ_POSTS = (AZ_POST,)
X_KEEL = 0.20          # полуширина килевой балки между подбородочными окнами
X_SPINE = 0.17         # полуширина хребтовой балки крыши (под ней верхний пульт)
Y_SPINE_FRONT = EYE[1] - X_SPINE / math.tan(math.radians(AZ_POST))   # где стойки сходятся в хребет
FRAME_HW = 0.018       # полуширина переплёта
RIM = 0.04             # окантовка остекления
FRAME_DEPTH = 0.075    # глубина переплёта внутрь (по линии взгляда)

HULL, FRAME, GLASS = 0, 1, 2


def _post(a, y, az=AZ_POST):
    """Расстояние до плоскости стойки и координата вдоль неё (вперёд от глаз), a = |x|."""
    c, s = math.cos(math.radians(az)), math.sin(math.radians(az))
    return a * c + (y - EYE[1]) * s, a * s - (y - EYE[1]) * c


def canopy_class(p):
    """Класс точки обшивки: (HULL | FRAME | GLASS, имя окна или None)."""
    x, y, z = p
    a = abs(x)
    side = 'R' if x > 0 else 'L'
    if y < Y_CAP - RIM:
        return HULL, None
    if z < Z_SILL - FRAME_HW:                      # ниже подоконника: подбородочные окна
        if y < Y_CAP:
            return FRAME, None
        if y > Y_CHIN_AFT + RIM:
            return HULL, None
        if y > Y_CHIN_AFT:
            return FRAME, None
        if a < X_KEEL:
            return HULL, None
        if a < X_KEEL + 0.03:
            return FRAME, None
        return GLASS, 'chin_' + side
    A = y + AFT_RAKE * (z - Z_SILL)
    if A > Y_AFT + RIM:
        return HULL, None
    if A > Y_AFT or y < Y_CAP or z < Z_SILL + FRAME_HW:
        return FRAME, None
    d, fwd = _post(a, y)
    if abs(d) < FRAME_HW and fwd > 0:
        return FRAME, None
    if a < X_SPINE and y > Y_SPINE_FRONT:
        return FRAME, None
    if d < 0:                                      # между стойками — центральное стекло
        return GLASS, 'wind_C'
    if abs(z - Z_HEAD) < FRAME_HW:
        return FRAME, None
    return GLASS, ('brow_' if z > Z_HEAD else 'side_') + side


def canopy_cuts(bm):
    """Разрезать обшивку носа по всем границам остекления (ничего не удаляя)."""
    cen = lambda f: f.calc_center_median()
    nose = lambda f: cen(f).y < Y_AFT + 0.25
    for z in (Z_SILL - FRAME_HW, Z_SILL + FRAME_HW):
        cut(bm, (0, 0, z), (0, 0, 1), nose)
    for y in (Y_CAP - RIM, Y_CAP):
        cut(bm, (0, y, 0), (0, 1, 0), nose)
    upper = lambda f: nose(f) and cen(f).z > Z_SILL - FRAME_HW and cen(f).y > Y_CAP - RIM
    chin = lambda f: nose(f) and cen(f).z < Z_SILL - FRAME_HW and cen(f).y > Y_CAP - RIM
    for y in (Y_AFT, Y_AFT + RIM):
        cut(bm, (0, y, Z_SILL), (0, 1, AFT_RAKE), upper)
    for y in (Y_CHIN_AFT, Y_CHIN_AFT + RIM):
        cut(bm, (0, y, 0), (0, 1, 0), chin)
    for x in (X_KEEL, X_KEEL + 0.03):
        for sgn in (1, -1):
            cut(bm, (sgn * x, 0, 0), (1, 0, 0), chin)
    c, s = math.cos(math.radians(AZ_POST)), math.sin(math.radians(AZ_POST))
    for sgn in (1, -1):
        n = (sgn * c, s, 0)
        for off in (-FRAME_HW, FRAME_HW):
            cut(bm, (n[0] * off, EYE[1] + n[1] * off, 0), n,
                lambda f, sgn=sgn: upper(f) and cen(f).x * sgn > -0.02 and _post(abs(cen(f).x), cen(f).y)[1] > -0.08)
    outer = lambda f: upper(f) and _post(abs(cen(f).x), cen(f).y)[0] > 0      # за стойками (борта и крыша)
    for sgn in (1, -1):
        cut(bm, (sgn * X_SPINE, 0, 0), (1, 0, 0), lambda f: upper(f) and cen(f).y > Y_SPINE_FRONT - 0.1)
    cut(bm, (0, Y_SPINE_FRONT, 0), (0, 1, 0), lambda f: upper(f) and abs(cen(f).x) < X_SPINE)
    for z in (Z_HEAD - FRAME_HW, Z_HEAD + FRAME_HW):
        cut(bm, (0, 0, z), (0, 0, 1), outer)


def canopy_mark(bm):
    """Проставить классы граням: material_index = HULL / FRAME / GLASS. Возвращает {имя окна: [грани]}."""
    panes = {}
    for f in bm.faces:
        cls, pane = canopy_class(f.calc_center_median())
        f.material_index = cls
        if pane:
            panes.setdefault(pane, []).append(f)
    return panes


def frame_solid(bm, proud=0.012, depth=FRAME_DEPTH):
    """Превратить полосы переплётов в тела: наружу — по нормали на proud, внутрь — по линии взгляда пилота
    на depth (боковые стенки переплётов идут вдоль луча из глаз, изнутри их не видно)."""
    bm.normal_update()
    E = Vector(EYE)
    inner = {}
    for v in list(bm.verts):
        n = v.normal.copy()
        inner[v] = bm.verts.new(v.co + (E - v.co).normalized() * depth)
        v.co = v.co + n * proud
    for f in list(bm.faces):
        bm.faces.new([inner[v] for v in reversed(f.verts)])
    for e in [e for e in bm.edges if e.is_boundary and e.verts[0] in inner and e.verts[1] in inner]:
        a, b = e.verts
        bm.faces.new((a, b, inner[b], inner[a]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])


# ---------------- крыло «чайка» ----------------
WING_IN_X, WING_KINK_X, WING_TIP_X = 1.30, 2.45, 4.00       # корень (у плеча корпуса), излом, законцовка
WING_IN_Z, WING_KINK_Z, WING_TIP_Z = 3.40, 4.08, 3.52
_w_le = pchip([0.6, 1.3, 2.45, 4.0], [-2.75, -2.00, -1.40, -0.78])
_w_te = pchip([0.6, 1.3, 2.45, 4.0], [2.00, 1.62, 1.30, 0.92])
_w_th = pchip([0.6, 1.3, 2.45, 4.0], [0.74, 0.50, 0.32, 0.21])
NAC_X, NAC_Y, NAC_Z = 4.56, 0.0, 3.52       # ось поворота мотогондолы на законцовке
NAC_FWD, NAC_AFT, NAC_R = 0.98, 1.60, 0.44   # от оси вперёд (воздухозаборник), назад (сопло), наибольший радиус
WING_XS = [1.45, 1.70, 2.00, 2.20, 2.33, 2.45, 2.57, 2.70, 2.90, 3.25, 3.65, 4.00]


def wing_z(x, blend=0.30):
    """Средняя линия крыла в виде спереди: подъём до излома и спуск к законцовке, излом скруглён."""
    k1 = (WING_KINK_Z - WING_IN_Z) / (WING_KINK_X - WING_IN_X)
    k2 = (WING_TIP_Z - WING_KINK_Z) / (WING_TIP_X - WING_KINK_X)
    if x <= WING_KINK_X - blend:
        return WING_KINK_Z + k1 * (x - WING_KINK_X)
    if x >= WING_KINK_X + blend:
        return WING_KINK_Z + k2 * (x - WING_KINK_X)
    t = (x - (WING_KINK_X - blend)) / (2 * blend)
    return (1 - t) ** 2 * (WING_KINK_Z - k1 * blend) + 2 * t * (1 - t) * WING_KINK_Z + t * t * (WING_KINK_Z + k2 * blend)


def wing_section(x, n=18):
    """Сечение правого крыла плоскостью x = const: точки (x, y, z)."""
    le, te, th = _w_le(x), _w_te(x), _w_th(x)
    ch = te - le
    zc = wing_z(x)
    return [(x, le + s * ch, zc + t * ch) for s, t in airfoil(n, th / ch, 0.018)]


def wing_root_ring(n=18, inset=0.045):
    """Корневое сечение крыла, уложенное по обшивке корпуса (на inset внутрь): крыло не входит в объём кабины."""
    le, te, th = _w_le(WING_IN_X), _w_te(WING_IN_X), _w_th(WING_IN_X)
    ch = te - le
    zc = wing_z(WING_IN_X)
    out = []
    for s, t in airfoil(n, th / ch, 0.018):
        y, z = le + s * ch, zc + t * ch
        out.append((max(0.3, halfwidth(y, z) - inset), y, z))
    return out


# ---------------- кормовые двигатели, кили, опоры ----------------
_p_y = [1.30, 2.20, 3.20, 4.40, 5.60, 6.35]
POD_R = pchip(_p_y, [0.03, 0.22, 0.38, 0.46, 0.46, 0.42])      # радиус обтекателя кормового двигателя
POD_X = pchip(_p_y, [1.22, 1.24, 1.27, 1.30, 1.27, 1.24])
POD_Z = pchip(_p_y, [3.40, 3.44, 3.50, 3.54, 3.54, 3.52])
BELL_Y0, BELL_Y1, BELL_R = 6.30, 7.00, 0.34
FIN_ROOT = dict(x=1.42, z=3.92, y_le=4.25, chord=1.95, th=0.14)
FIN_TIP = dict(x=2.22, z=4.50, y_le=5.72, chord=0.86, th=0.07)
GEAR = {                                     # A — узел на скуле корпуса, P — центр лыжи на грунте (правый борт)
    'front': dict(A=(1.50, -2.90, 1.72), P=(2.10, -2.90, 0.0)),
    'rear': dict(A=(1.62, 2.30, 1.95), P=(2.30, 2.90, 0.0)),
}
SKI_LEN, SKI_W = 2.40, 0.96
