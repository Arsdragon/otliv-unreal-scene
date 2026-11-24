# svetlyak.py — этап D: дрон-разведчик «Светляк» (≈0,58 × 0,48 м): корпус-«галька» (белый верх, графитовое днище, шов
# по поясу), 4 импеллера в кольцах с бамперами и спрямляющими лопатками, сенсорная голова-шар с одним крупным
# объективом и излучателем сканера, тёплый жёлто-зелёный фонарь сзади, складной манипулятор (захват + резак) под днищем.
# Запуск в открытом Blender:  bash tools/live.sh svetlyak.py   ->  src/svetlyak.blend, export/svetlyak/{layout.json, tris.npz}
# Оси: метры, Z вверх, нос по −Y, +X — левый борт. Начало координат — центр корпуса в плоскости импеллеров.
import bpy, bmesh, math, os, sys, json
from mathutils import Vector, Matrix, Euler

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
for _f in ('kit.py', 'uvkit.py', 'partkit.py', 'dkit.py'):
    exec(open(os.path.join(TOOLS, _f), encoding='utf-8').read())
ID = 'svetlyak'
EXP = os.path.join(ROOT, 'export', ID)
os.makedirs(EXP, exist_ok=True)
R = math.radians

CLS = {'sv_shell': 1, 'sv_dark': 2, 'sv_orange': 3, 'sv_carbon': 4, 'm_alu': 5, 'm_steel': 6, 'm_rubber': 7,
       'sv_lensbody': 8, 'm_chrome': 9, 'sv_ceramic': 10, 'glass': 60, 'emissive': 61, 'scanner': 62}
_PV = {'sv_shell': (0.78, 0.77, 0.73), 'sv_dark': (0.06, 0.065, 0.07), 'sv_orange': (0.80, 0.30, 0.05), 'sv_carbon': (0.035, 0.037, 0.04),
       'm_alu': (0.74, 0.75, 0.76), 'm_steel': (0.33, 0.33, 0.34), 'm_rubber': (0.03, 0.03, 0.03), 'sv_lensbody': (0.025, 0.026, 0.03),
       'm_chrome': (0.9, 0.9, 0.9), 'sv_ceramic': (0.85, 0.83, 0.78)}
for _n, _c in _PV.items():
    defmat(_n, (*_c, 1), metallic=1.0 if _n in ('m_alu', 'm_steel', 'm_chrome') else 0.0, rough=0.45)
defmat('glass', (0.30, 0.34, 0.36, 0.3), rough=0.02, kind='glass')
defmat('emissive', (0.72, 1.0, 0.22, 1), rough=0.3, emis=6.0)
defmat('scanner', (0.10, 0.16, 0.20, 1), rough=0.1, emis=0.6)

# ---------------------------------------------------------------- корпус-«галька»
BODY = [  # y, полуширина W, высота верха над швом zt, глубина низа под швом zb
    (-0.200, 0.030, 0.016, 0.014), (-0.190, 0.058, 0.030, 0.021), (-0.170, 0.083, 0.042, 0.027), (-0.140, 0.102, 0.052, 0.031),
    (-0.100, 0.113, 0.060, 0.034), (-0.050, 0.118, 0.065, 0.043), (0.010, 0.118, 0.066, 0.046), (0.070, 0.113, 0.062, 0.045),
    (0.120, 0.100, 0.054, 0.040), (0.160, 0.080, 0.044, 0.032), (0.185, 0.064, 0.036, 0.026), (0.195, 0.058, 0.032, 0.023)]
_bf = [pchip([k[0] for k in BODY], [k[i] for k in BODY]) for i in (1, 2, 3)]
SEAM = -0.0047                       # нижняя кромка шва по поясу (верх корпуса — от 0, днище — от SEAM)
ET, EB, NU, NL = 2.3, 3.2, 28, 24


YT = -0.2046                         # кончик носа: перед первым сечением корпус сходится по дуге (без гранёной пирамидки)


def body_dims(y):
    if y < BODY[0][0]:
        f = math.sqrt(max(1e-4, (y - YT) / (BODY[0][0] - YT)))
        return [BODY[0][i] * f for i in (1, 2, 3)]
    return [f(y) for f in _bf]


def body_ring(y):
    """Сечение корпуса: верхняя дуга (белая), вырез шва слева, нижняя дуга (графит), вырез шва справа."""
    W, zt, zb = body_dims(y)
    up = []
    for i in range(NU + 1):
        t = math.pi * i / NU
        c, s = math.cos(t), math.sin(t)
        up.append((math.copysign(W * abs(c) ** (2 / ET), c), y, zt * abs(s) ** (2 / ET)))
    lo = []
    for i in range(NL + 1):
        t = math.pi + math.pi * i / NL
        c, s = math.cos(t), math.sin(t)
        lo.append((math.copysign(W * abs(c) ** (2 / EB), c), y, SEAM - zb * abs(s) ** (2 / EB)))
    wn = max(W - 0.0016, W * 0.6)
    nl = [(-wn, y, -0.0013), (-wn, y, -0.0034)]
    nr = [(wn, y, -0.0034), (wn, y, -0.0013)]
    return up + nl + lo + nr


def top_z(x, y):
    W, zt, zb = body_dims(y)
    u = min(0.999, abs(x) / W)
    return zt * (1 - u ** ET) ** (1 / ET)


def bot_z(x, y):
    W, zt, zb = body_dims(y)
    u = min(0.999, abs(x) / W)
    return SEAM - zb * (1 - u ** EB) ** (1 / EB)


def build_body_shell():
    ys = [YT + (BODY[0][0] - YT) * t * t for t in (0.16, 0.34, 0.52, 0.70, 0.86)]             # скруглённый кончик носа
    ys += [-0.200 + 0.195 * (1 - math.cos(math.pi * 0.5 * k / 10)) for k in range(11)]      # гуще у носа
    ys += frange(-0.004, 0.150, 0.022)[1:] + [0.165, 0.178, 0.188, 0.195]
    rings = [body_ring(y) for y in ys]
    n = len(rings[0])
    bm = bmesh.new()
    vr, _ = skin(bm, rings, closed=True)
    tip = bm.verts.new((0, YT - 0.0002, -0.0023))
    for i in range(n):
        bm.faces.new((tip, vr[0][(i + 1) % n], vr[0][i]))
    bm.faces.new(vr[-1])                                       # кормовой торец — под фонарь
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        f.material_index = 0 if f.calc_center_median().z > -0.0012 else 1
        f.smooth = True
    return bm_obj(bm, 'shell', ['sv_shell', 'sv_dark'], 34)


def strut(p0, p1, c0, c1, th, mat_name):
    """Обтекаемая стойка от p0 к p1: сечение — линза с хордой вдоль Y (c0 → c1) и толщиной th."""
    p0, p1 = Vector(p0), Vector(p1)
    rings = []
    for t in (0.0, 0.33, 0.66, 1.0):
        p = p0 + (p1 - p0) * t
        c = c0 + (c1 - c0) * t
        rings.append([(p.x, p.y + c * (s - 0.5), p.z + c * tt) for s, tt in airfoil(8, th / c, 0.0)])
    return loft('strut', rings, mat_name=mat_name, smooth=40)


# ---------------------------------------------------------------- импеллеры
DUCTS = {'FL': (0.215, -0.095), 'FR': (-0.215, -0.095), 'RL': (0.215, 0.115), 'RR': (-0.215, 0.115)}
RI, RO, ROTOR_Z = 0.060, 0.0735, 0.004


def duct_parts(cx, cy):
    c = (cx, cy, 0.0)
    body = [(RI, -0.024), (RO - 0.0015, -0.024), (RO, -0.017), (RO, 0.011), (RI, 0.011)]
    lip = [(RI - 0.001, 0.011), (RO, 0.011), (RO - 0.002, 0.018), (RO - 0.0075, 0.0228), (RI + 0.0012, 0.019)]
    p = [revolve('duct', body, 64, 'Z', c, 'sv_dark', closed=True, cap=False),
         revolve('lip', lip, 64, 'Z', c, 'sv_shell', closed=True, cap=False),
         torus('bump', (cx, cy, -0.003), RO + 0.0035, 0.0045, 'Z', 'm_rubber', 64, 8),
         revolve('motor', [(0.0, -0.025), (0.016, -0.025), (0.019, -0.021), (0.019, -0.006), (0.0, -0.006)], 24, 'Z', c, 'sv_dark'),
         revolve('mring', [(0.0192, -0.016), (0.0205, -0.0155), (0.0205, -0.0105), (0.0192, -0.010)], 24, 'Z', c, 'm_alu', closed=True, cap=False)]
    for k in range(4):                                         # спрямляющие лопатки под ротором
        a = math.pi / 4 + k * math.pi / 2
        e, t = Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0))
        M = frame_M(Vector(c) + e * ((0.019 + RI) / 2) + Vector((0, 0, -0.014)), e, Vector((0, 0, 1)))
        p += place([box('vane', (RI - 0.019 + 0.002, 0.0028, 0.011), (0, 0, 0), mat_name='sv_dark', rot=(0, 0, 0))], M)
    return p


def rotor(cx, cy, name):
    """Ротор: 5 лопастей с круткой (шаг 0,10 м), ступица с обтекателем. Опорная точка — центр ступицы, ось Z."""
    parts = [revolve('hub', [(0.0, -0.006), (0.0165, -0.006), (0.0165, 0.004), (0.012, 0.0085), (0.0, 0.0095)], 24, 'Z',
                     (cx, cy, ROTOR_Z), 'm_alu'),
             revolve('cap', [(0.0, 0.0094), (0.005, 0.0094), (0.005, 0.0101), (0.0, 0.0101)], 16, 'Z', (cx, cy, ROTOR_Z), 'sv_orange')]
    sec_ = [(s - 0.5, t) for s, t in airfoil(6, 0.10, 0.04)]
    for k in range(5):
        ph = 2 * math.pi * k / 5
        er, et = Vector((math.cos(ph), math.sin(ph), 0)), Vector((-math.sin(ph), math.cos(ph), 0))
        rings = []
        for r in (0.0155, 0.022, 0.030, 0.038, 0.046, 0.0525, 0.0572):
            ch = 0.020 - 0.11 * (r - 0.0155)
            b = math.atan(0.10 / (2 * math.pi * r))
            cb, sb = math.cos(b), math.sin(b)
            c0 = Vector((cx, cy, ROTOR_Z)) + er * r
            rings.append([c0 + et * (ch * (s * cb - t * sb)) + Vector((0, 0, ch * (s * sb + t * cb))) for s, t in sec_])
        parts.append(loft('blade', rings, mat_name='sv_carbon', smooth=40))
    ob = merge(parts, name, (cx, cy, ROTOR_Z))
    shade(ob, 40)
    smart_uv(ob, 'A', dens=0.8)
    return ob


# ---------------------------------------------------------------- голова с объективом
HC = Vector((0.0, -0.163, -0.050))
HR = 0.050


def build_head():
    prof = [(HR * math.sin(math.pi * k / 20), -HR * math.cos(math.pi * k / 20)) for k in range(21)]
    prof[0], prof[-1] = (0.0, -HR), (0.0, HR)
    p = [revolve('ball', prof, 48, 'Z', HC, 'sv_dark')]
    ax = Vector((0, -1, 0.0))
    c0 = HC + ax * (HR - 0.010)                                   # объектив: всё — трубки вдоль −Y, стекло спереди
    tube = lambda nm, r0, r1, h0, h1, m: revolve(nm, [(r0, -h0), (r1, -h0), (r1, -h1), (r0, -h1)], 40, 'Y', c0, m, closed=True, cap=False)
    p += [tube('barrel', 0.0268, 0.0310, 0.0, 0.026, 'sv_lensbody'),
          tube('ring', 0.0268, 0.0335, 0.024, 0.030, 'm_alu'),
          tube('hood', 0.0300, 0.0325, 0.028, 0.034, 'sv_lensbody'),
          revolve('inner', [(0.0, -0.0060), (0.0268, -0.0060), (0.0268, -0.0095), (0.0, -0.0095)], 40, 'Y', c0, 'sv_lensbody'),
          revolve('inner_glass', [(0.0, -0.0118), (0.012, -0.0112), (0.0215, -0.0100), (0.0215, -0.0096), (0.0, -0.0096)], 40, 'Y', c0, 'm_chrome')]
    for rr in (0.0232, 0.0175, 0.0115):
        p.append(torus('iris', c0 + ax * 0.0104, rr, 0.0010, 'Y', 'm_chrome', 40, 6))
    p.append(revolve('glass', [(0.0, 0.0), (0.016, 0.0012), (0.0265, 0.0045), (0.0265, 0.0062), (0.0, 0.0062)], 40, 'Y',
                     c0 + ax * 0.0318, 'glass'))                 # выпуклость вперёд: края стекла отстают к корме
    sc = HC + Vector((0, -(HR - 0.004), -0.026))                 # излучатель сканера под объективом
    p += [box('emit_pad', (0.046, 0.012, 0.016), sc, bevel=0.003, mat_name='sv_lensbody'),
          box('emit_win', (0.038, 0.002, 0.0075), sc + Vector((0, -0.0061, 0.0)), mat_name='scanner'),
          box('emit_rib', (0.040, 0.0016, 0.0011), sc + Vector((0, -0.0068, 0.0052)), mat_name='m_alu')]
    for sx in (-1, 1):
        p.append(hexbolt(HC + Vector((sx * 0.026, -0.040, -0.022)), Vector((sx * 0.5, -0.8, -0.4)).normalized(), 0.0045, 0.0015))
        p.append(cyl('trun', HC + Vector((sx * (HR - 0.006), 0, 0)), HC + Vector((sx * (HR + 0.004), 0, 0)), 0.012, 20, 'm_alu', bevel=0.0015))
    ob = merge(p, 'sv_head', tuple(HC))
    shade(ob, 36)
    smart_uv(ob, 'A', angle=40.0, dens=1.6)
    return ob, sc + Vector((0, -0.0075, 0)), c0 + ax * 0.034


# ---------------------------------------------------------------- манипулятор (сложен под днищем)
S_AX = Vector((0, -0.070, -0.068))       # плечо (ось X)
E_AX = Vector((0, 0.075, -0.078))        # локоть (ось X)
W_AX = Vector((0, -0.045, -0.088))       # кисть (ось X)


def seg_beam(y0, y1, z, w, h, mat_name):
    sec_ = rrect(w, h, min(w, h) * 0.35, 2)
    return loft('beam', [[(x, y, z + zz) for x, zz in sec_] for y in (y0, y1)], mat_name=mat_name, smooth=40)


def joint(c, r, wdt, caps=True):
    c = Vector(c)
    p = [cyl('jh', c - Vector((wdt / 2, 0, 0)), c + Vector((wdt / 2, 0, 0)), r, 24, 'm_alu', bevel=0.0015)]
    if caps:
        p += [cyl('jc', c + Vector((s * wdt / 2, 0, 0)), c + Vector((s * (wdt / 2 + 0.0025), 0, 0)), r * 0.82, 24, 'sv_orange') for s in (-1, 1)]
    return p


def build_arm():
    base = merge([cyl('disc', (0, -0.070, -0.0505), (0, -0.070, -0.0565), 0.019, 28, 'm_alu', bevel=0.0015),
                  box('cheekL', (0.004, 0.026, 0.018), (0.0165, -0.070, -0.064), bevel=0.0015, mat_name='sv_dark'),
                  box('cheekR', (0.004, 0.026, 0.018), (-0.0165, -0.070, -0.064), bevel=0.0015, mat_name='sv_dark')],
                 'sv_arm_base', (0, -0.070, -0.053))
    up = merge(joint(S_AX, 0.011, 0.028) + joint((0, 0.075, -0.068), 0.0095, 0.024, caps=False) +
               [seg_beam(-0.064, 0.072, -0.068, 0.020, 0.015, 'sv_dark'),
                pipe('cab', [(0.012, -0.060, -0.064), (0.0125, 0.0, -0.063), (0.012, 0.068, -0.064)], 0.0022, 'm_rubber', sides=6, res=3)],
               'sv_arm_upper', tuple(S_AX))
    fore = merge(joint(E_AX, 0.0105, 0.026) + [seg_beam(-0.040, 0.075, -0.088, 0.017, 0.013, 'sv_dark'),
                                                 pipe('cab', [(-0.011, 0.070, -0.085), (-0.0115, 0.010, -0.084), (-0.011, -0.040, -0.085)],
                                                      0.002, 'm_rubber', sides=6, res=3)],
                 'sv_arm_fore', tuple(E_AX))
    wr = merge(joint(W_AX, 0.0095, 0.022) +
               [box('palm', (0.026, 0.018, 0.017), (0, -0.0545, -0.088), bevel=0.003, mat_name='sv_dark'),
                cyl('cut_body', (0.0175, -0.046, -0.088), (0.0175, -0.088, -0.088), 0.0055, 16, 'm_steel', bevel=0.001),
                cyl('cut_collar', (0.0175, -0.080, -0.088), (0.0175, -0.086, -0.088), 0.0068, 16, 'sv_orange'),
                cyl('cut_tip', (0.0175, -0.088, -0.088), (0.0175, -0.100, -0.088), 0.0055, 16, 'sv_ceramic', r1=0.0018),
                pipe('cut_hose', [(0.0175, -0.047, -0.088), (0.019, -0.040, -0.090), (0.012, -0.030, -0.092)], 0.0025, 'm_rubber', sides=6, res=3)],
               'sv_arm_wrist', tuple(W_AX))
    fingers = []
    for sg, nm in ((1, 'L'), (-1, 'R')):
        pv = Vector((sg * 0.0075, -0.0625, -0.088))
        poly = [(sg * 0.0060, -0.0600), (sg * 0.0098, -0.0600), (sg * 0.0072, -0.0870), (sg * 0.0030, -0.0950),
                (sg * 0.0008, -0.0935), (sg * 0.0034, -0.0700)]
        f = merge([prism('fing', poly, -0.094, -0.082, 'Z', bevel=0.0008, mat_name='m_steel'),
                   box('pad', (0.0012, 0.020, 0.010), (sg * 0.0022, -0.083, -0.088), mat_name='m_rubber'),
                   cyl('fpin', pv + Vector((0, 0, -0.0075)), pv + Vector((0, 0, 0.0075)), 0.0022, 10, 'm_alu')],
                  'sv_finger_' + nm, tuple(pv))
        fingers.append(f)
    objs = [base, up, fore, wr] + fingers
    for o in objs:
        shade(o, 36)
        smart_uv(o, 'A', dens=1.5)
    set_parent(up, base)
    set_parent(fore, up)
    set_parent(wr, fore)
    for f in fingers:
        set_parent(f, wr)
    return objs


# ---------------------------------------------------------------- сборка
def build_all():
    clear_scene()
    use_coll(ID)
    p = [build_body_shell()]
    for k, (cx, cy) in DUCTS.items():
        p += duct_parts(cx, cy)
        sg = 1 if cx > 0 else -1
        W = body_dims(cy)[0]
        p.append(strut((sg * (W - 0.010), cy, 0.003), (sg * (abs(cx) - RO + 0.004), cy, 0.0), 0.044, 0.034, 0.013, 'sv_shell'))
    # фонарь в кормовом торце
    lc = Vector((0, 0.195, 0.004))
    ell = lambda a, b, n=40: [(a * math.cos(2 * math.pi * k / n), b * math.sin(2 * math.pi * k / n)) for k in range(n)]
    p.append(loft('lamp_bezel', [[(x, 0.194, lc.z + z) for x, z in ell(0.050, 0.019)], [(x, 0.201, lc.z + z) for x, z in ell(0.049, 0.018)],
                                 [(x, 0.201, lc.z + z) for x, z in ell(0.045, 0.0145)], [(x, 0.198, lc.z + z) for x, z in ell(0.045, 0.0145)]],
                  closed=True, cap0=True, cap1=True, mat_name='sv_lensbody', smooth=40))
    p.append(loft('lamp_lens', [[(x, 0.198, lc.z + z) for x, z in ell(0.0448, 0.0143)], [(x, 0.2025, lc.z + z) for x, z in ell(0.040, 0.0120)],
                                [(x, 0.2045, lc.z + z) for x, z in ell(0.026, 0.0078)]], closed=True, cap0=False, cap1=True,
                  mat_name='emissive', smooth=60))
    # крепление головы, антенна, купол навигации, светодиод состояния, крепёж люка
    zc = bot_z(0.0, HC.y) + 0.0015                             # кольцо крепления головы — по днищу
    p.append(torus('collar', (HC.x, HC.y, zc), math.sqrt(max(HR ** 2 - (zc - HC.z) ** 2, 0.0)) + 0.002, 0.0055, 'Z', 'sv_dark', 48, 8))
    zt = top_z(0.042, 0.118)
    p += [cyl('ant_base', (0.042, 0.118, zt - 0.002), (0.042, 0.118, zt + 0.006), 0.0055, 16, 'sv_dark', bevel=0.0012),
          cyl('ant_whip', (0.042, 0.118, zt + 0.005), (0.042, 0.130, zt + 0.078), 0.0011, 8, 'm_steel'),
          cyl('ant_tip', (0.042, 0.1302, zt + 0.0775), (0.042, 0.1307, zt + 0.081), 0.0024, 10, 'sv_orange'),
          revolve('gnss', [(0.0, 0.0), (0.020, 0.0), (0.019, 0.004), (0.012, 0.0085), (0.0, 0.0095)], 32, 'Z',
                  (0, -0.080, top_z(0, -0.080) - 0.0015), 'sv_shell'),
          cyl('led', (-0.032, 0.140, top_z(-0.032, 0.140) - 0.001), (-0.032, 0.140, top_z(-0.032, 0.140) + 0.0016), 0.0028, 12, 'emissive')]
    for x, y in ((0.062, -0.025), (-0.062, -0.025), (0.062, 0.065), (-0.062, 0.065)):
        p.append(hexbolt((x, y, top_z(x, y) - 0.0004), (x * 0.9, 0, 1.0), 0.0052, 0.0016))
    zb = bot_z(0, -0.070)
    p.append(box('arm_mount', (0.050, 0.080, 0.004), (0, -0.050, zb - 0.0015), bevel=0.0012, mat_name='sv_dark'))
    for x, y in ((0.020, -0.084), (-0.020, -0.084), (0.020, -0.016), (-0.020, -0.016)):
        p.append(hexbolt((x, y, zb - 0.0035), (0, 0, -1), 0.0045, 0.0014))
    body = merge(p, 'sv_body', (0, 0, 0))
    shade(body, 34)
    smart_uv(body, 'A', angle=32.0, dens=1.0)          # мелкие острова: без растяжения на гладкой «гальке»
    head, scan_pt, lens_pt = build_head()
    rotors = {k: rotor(cx, cy, 'sv_rotor_' + k) for k, (cx, cy) in DUCTS.items()}
    arm = build_arm()
    root = empty(ID, (0, 0, 0), size=0.1)
    marker('fx_scanner', scan_pt, (0, -1, -0.25), head)
    marker('cam_lens', lens_pt, (0, -1, 0.06), head)
    marker('light_tail', (0, 0.205, lc.z), (0, 1, 0))
    marker('fx_cutter', (0.0175, -0.101, -0.088), (0, -1, 0), bpy.data.objects['sv_arm_wrist'])
    marker('grip_point', (0, -0.086, -0.088), (0, -1, 0), bpy.data.objects['sv_arm_wrist'])
    for k, (cx, cy) in DUCTS.items():
        marker('fx_downwash_' + k, (cx, cy, -0.026), (0, 0, -1))
    bpy.context.view_layer.update()
    for o in list(bpy.data.collections[ID].objects):
        if o is not root and o.parent is None:
            set_parent(o, root)
    return [body, head] + list(rotors.values()) + arm


if __name__ == '__main__':
    objs = build_all()
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    print('ГАБАРИТЫ: %.3f × %.3f × %.3f м (x %.3f…%.3f, y %.3f…%.3f, z %.3f…%.3f)' %
          (hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
    finish_model(ID, EXP, objs, CLS, extra=dict(bbox=[lo, hi]))
