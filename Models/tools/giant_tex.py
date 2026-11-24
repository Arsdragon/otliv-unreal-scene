# -*- coding: utf-8 -*-
# giant_tex.py — текстуры газового гиганта и колец для сцены 1 «Отлив» (numpy + scipy, без Blender):
#   python tools/giant_tex.py            — чистовые 4096×2048 в export/gas_giant/ + манифест + лист-развёртка в shots/
#   python tools/giant_tex.py 1024       — быстрая проба (то же, мельче; пишет только shots/_tmp/giant_prev.png)
# Гигант: полосы — функция исходной широты; узор получается переносом «краски» течением (струи вдоль широт, вихри,
# волны на границах полос, три фазы турбулентности) — трассировка назад по полю скоростей. Всё считается на сфере,
# поэтому шва по долготе и стягивания у полюсов нет. Кольца: радиальный профиль оптической толщины -> альфа и два
# цвета (освещённая сторона / на просвет).
import numpy as np, os, sys, json, time
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import map_coordinates

ROOT = r'C:\UnrealScenes\Models'
OUT = os.path.join(ROOT, 'export', 'gas_giant')
TMP = os.path.join(ROOT, 'shots', '_tmp')
os.makedirs(OUT, exist_ok=True)
W = int(sys.argv[1]) if len(sys.argv) > 1 else 4096
H = W // 2
FW = min(W, 2048)
FH = FW // 2
FINAL = W >= 4096
T0 = time.time()
rng = np.random.default_rng(11)
RING_IN, RING_OUT = 1.242, 2.300          # радиусы краёв колец в радиусах планеты (как у заглушки в сцене)


def log(s):
    print('[%.0f с] %s' % (time.time() - T0, s), flush=True)


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def sphere(lam, th):
    s = np.sin(th)
    return np.stack([s * np.cos(lam), s * np.sin(lam), np.cos(th)], -1).astype(np.float32)


def vnoise3(P, freq, seed=0, octaves=1, gain=0.5, lac=2.0):
    """Шум значений на решётке, P (N,3) -> [0,1]; считается кусками по миллиону точек."""
    N = P.shape[0]
    out = np.empty(N, np.float32)
    for a in range(0, N, 1 << 20):
        p = P[a:a + (1 << 20)]
        acc = np.zeros(len(p), np.float32)
        amp, tot = 1.0, 0.0
        for o in range(octaves):
            q = p * np.float32(freq * lac ** o) + np.float32(17.3 * o + 3.1)
            i = np.floor(q)
            f = q - i
            i = (i.astype(np.int64) & 0xFFFFFFFF).astype(np.uint32)
            f = f * f * (3 - 2 * f)
            kx, ky, kz = np.uint32(73856093), np.uint32(19349663), np.uint32(83492791)
            ix, iy, iz = i[:, 0] * kx, i[:, 1] * ky, i[:, 2] * kz
            sd = np.uint32(((seed * 1013 + o * 7919 + 1) * 2654435761) & 0xFFFFFFFF)

            def h(dx, dy, dz):
                n = (ix + kx * np.uint32(dx)) ^ (iy + ky * np.uint32(dy)) ^ (iz + kz * np.uint32(dz)) ^ sd
                n = (n ^ (n >> np.uint32(15))) * np.uint32(2246822519)
                n = (n ^ (n >> np.uint32(13))) * np.uint32(3266489917)
                n = n ^ (n >> np.uint32(16))
                return (n >> np.uint32(8)).astype(np.float32) * np.float32(1 / 16777215)

            fx, fy, fz = f[:, 0], f[:, 1], f[:, 2]
            a00 = h(0, 0, 0)
            a00 += (h(1, 0, 0) - a00) * fx
            a10 = h(0, 1, 0)
            a10 += (h(1, 1, 0) - a10) * fx
            a01 = h(0, 0, 1)
            a01 += (h(1, 0, 1) - a01) * fx
            a11 = h(0, 1, 1)
            a11 += (h(1, 1, 1) - a11) * fx
            a00 += (a10 - a00) * fy
            a01 += (a11 - a01) * fy
            acc += amp * (a00 + (a01 - a00) * fz)
            tot += amp
            amp *= gain
        out[a:a + (1 << 20)] = acc / tot
    return out


def noise1d(x, freq, seed):
    q = np.asarray(x, np.float64) * freq + 1000.0
    i = np.floor(q).astype(np.int64)
    f = q - i
    f = f * f * (3 - 2 * f)
    r = np.random.default_rng(seed).random(8192)
    return (r[i % 8192] * (1 - f) + r[(i + 1) % 8192] * f).astype(np.float32)


# ------------------------------------------------------------------ полосы (с юга на север), цвета — sRGB
EDGES = [-72, -60, -50, -40, -30, -21, -9, 8, 19, 28, 35, 45, 56, 68]
BANDS = [('cap', (0.47, 0.55, 0.62)), ('zone', (0.70, 0.75, 0.78)), ('belt', (0.58, 0.64, 0.68)),
         ('zone', (0.80, 0.81, 0.78)), ('belt', (0.74, 0.65, 0.53)), ('zone', (0.89, 0.85, 0.75)),
         ('belt', (0.75, 0.65, 0.52)), ('zone', (0.91, 0.87, 0.78)), ('belt', (0.72, 0.61, 0.49)),
         ('zone', (0.89, 0.85, 0.76)), ('belt', (0.77, 0.68, 0.55)), ('zone', (0.82, 0.84, 0.83)),
         ('belt', (0.61, 0.67, 0.71)), ('zone', (0.72, 0.77, 0.80)), ('cap', (0.52, 0.59, 0.66))]
AMP = {'belt': 1.0, 'zone': 0.32, 'cap': 0.50}                                   # сила турбулентности по типу полосы
JETS = [(8, 1), (19, -1), (28, 1), (35, -1), (45, 1), (56, -1), (68, 1),
        (-9, 1), (-21, -1), (-30, 1), (-40, -1), (-50, 1), (-60, -1), (-72, 1)]
NL = 8192
LAT = np.linspace(-90, 90, NL)


def make_lut():
    col = np.tile(np.array(BANDS[0][1], np.float64), (NL, 1))
    amp = np.full(NL, AMP[BANDS[0][0]])
    for e, (kind, c) in zip(EDGES, BANDS[1:]):
        t = 0.5 * (1 + np.tanh((LAT - e) / 0.55))
        col += (np.array(c) - col) * t[:, None]
        amp += (AMP[kind] - amp) * t
    lum = 1 + 0.060 * (noise1d(LAT, 0.55, 1) - 0.5) * 2 + 0.042 * (noise1d(LAT, 1.7, 2) - 0.5) * 2 \
        + 0.024 * (noise1d(LAT, 4.5, 3) - 0.5) * 2
    col *= lum[:, None]
    col += ((noise1d(LAT, 0.35, 5) - 0.5) * 2)[:, None] * np.array((0.040, 0.008, -0.034))
    eq = np.exp(-((LAT - 0.6) / 1.1) ** 2)                                        # тонкая сероватая полоса у экватора
    col += (np.array((0.74, 0.73, 0.70)) - col) * (0.45 * eq)[:, None]
    return col.astype(np.float32), amp.astype(np.float32)


LUT, AMPL = make_lut()


def u_zonal(lat):
    """Скорость на восток, рад/ед. времени."""
    u = 0.75 * np.exp(-(lat / 7.5) ** 2)
    for e, s in JETS:
        u = u + s * 0.62 * np.exp(-((lat - e) / 2.6) ** 2)
    return u * np.cos(np.radians(lat)) ** 1.5


# ------------------------------------------------------------------ вихри и «краска»
BIG = dict(lat=-25.6, lon=200.0, sl=6.6, sp=3.5, turns=2.2)
VORT = [BIG]
DYES = [(BIG['lat'], BIG['lon'], BIG['sl'] * 1.45, BIG['sp'] * 1.45, (0.62, 0.53, 0.42), 0.38),
        (BIG['lat'], BIG['lon'], BIG['sl'] * 0.85, BIG['sp'] * 0.85, (0.86, 0.87, 0.85), 0.80),
        (BIG['lat'], BIG['lon'], BIG['sl'] * 0.40, BIG['sp'] * 0.40, (0.70, 0.77, 0.82), 0.55)]
lon = 20.0
for k in range(9):                                                                # цепочка белых овалов на юге
    lon += rng.uniform(22, 40)
    s = rng.uniform(1.0, 1.5)
    VORT.append(dict(lat=-44.6 + rng.uniform(-0.6, 0.6), lon=lon, sl=s * 1.15, sp=s, turns=1.6))
    DYES.append((VORT[-1]['lat'], lon, s * 1.0, s * 0.9, (0.94, 0.93, 0.89), 0.85))
for lo in (38.0, 131.0, 262.0, 318.0):                                            # тёмные вытянутые «баржи» в северном поясе
    VORT.append(dict(lat=13.8 + rng.uniform(-0.8, 0.8), lon=lo + rng.uniform(-8, 8), sl=2.7, sp=0.95, turns=1.2))
    DYES.append((VORT[-1]['lat'], VORT[-1]['lon'], 2.5, 0.85, (0.47, 0.37, 0.29), 0.75))
for lo, la, s in ((96.0, 31.3, 2.1), (305.0, -36.0, 1.7), (164.0, 23.5, 1.5)):   # одиночные светлые овалы
    VORT.append(dict(lat=la, lon=lo, sl=s * 1.25, sp=s, turns=1.8))
    DYES.append((la, lo, s * 1.1, s * 0.9, (0.93, 0.91, 0.85), 0.8))
for sgn in (1, -1):                                                               # мелкие вихри у полюсов
    for k in range(14):
        la = sgn * (rng.uniform(0, 1) ** 0.7 * 24 + 58)
        s = rng.uniform(0.8, 1.5)
        VORT.append(dict(lat=la, lon=rng.uniform(0, 360), sl=s, sp=s, turns=rng.uniform(0.6, 1.2)))
        c = (0.74, 0.81, 0.86) if rng.random() < 0.55 else (0.40, 0.48, 0.56)
        DYES.append((la, VORT[-1]['lon'], s, s, c, rng.uniform(0.2, 0.4)))
lon = 0.0
while lon < 350:                                                                  # затравки фестонов у края экваториальной зоны
    DYES.append((6.3 + rng.uniform(-0.5, 0.5), lon, 2.2, 1.0, (0.56, 0.63, 0.69), 0.62))
    lon += rng.uniform(20, 38)
lon = 12.0
while lon < 350:
    DYES.append((-7.6 + rng.uniform(-0.5, 0.5), lon, 2.0, 0.9, (0.62, 0.64, 0.66), 0.42))
    lon += rng.uniform(30, 55)


def add_blob(C, A, lat, lon, sl, sp, color, k):
    DH, DW = A.shape
    lon = lon % 360
    cy, cx = (90 - lat) / 180 * DH, lon / 360 * DW
    ry = int(3.5 * sp / 180 * DH) + 2
    rx = int(3.5 * sl / max(np.cos(np.radians(lat)), 0.15) / 360 * DW) + 2
    ys = np.arange(max(0, int(cy) - ry), min(DH, int(cy) + ry + 1))
    xs = np.arange(int(cx) - rx, int(cx) + rx + 1)
    la, lo = 90 - (ys + 0.5) / DH * 180, (xs + 0.5) / DW * 360
    g = np.exp(-0.5 * ((la - lat) / sp) ** 2)[:, None] * np.exp(-0.5 * ((lo - lon) * np.cos(np.radians(lat)) / sl) ** 2)[None, :]
    a = (k * g).astype(np.float32)
    sub = np.ix_(ys, xs % DW)
    C[sub] = C[sub] * (1 - a[..., None]) + np.array(color, np.float32) * a[..., None]
    A[sub] = A[sub] + a * (1 - A[sub])


def padw(a):
    return np.concatenate([a[:, -1:], a, a[:, :1]], 1)


def samp(A, Y, X, w):
    return map_coordinates(A, [Y, np.mod(X, w) + 1.0], order=1, mode='nearest', output=np.float32)


# ------------------------------------------------------------------ течение и трассировка назад
def backtrace():
    lam1 = (np.arange(FW) + 0.5) / FW * 2 * np.pi
    th1 = (np.arange(FH) + 0.5) / FH * np.pi
    lat1 = 90 - np.degrees(th1)
    LAM, TH = np.meshgrid(lam1.astype(np.float32), th1.astype(np.float32))
    Pa = sphere(LAM, TH).reshape(-1, 3) * np.array((1, 1, 2.0), np.float32)
    amp_row = np.interp(lat1, LAT, AMPL)
    fade = sstep(87, 80, np.abs(lat1))
    uz = u_zonal(lat1)
    duz = np.gradient(uz)
    psi0 = np.zeros((FH, FW), np.float32)
    for e in EDGES:
        for k in range(2):
            m = int(rng.integers(8, 30))
            a = rng.uniform(0.0015, 0.0035) / (1 + k)
            a *= 0.45 if abs(e) > 50 else 1.0
            env = 0.30 + 0.70 * np.cos(int(rng.integers(1, 4)) * lam1 * 0.5 + rng.uniform(0, 6.28)) ** 2      # волны идут пачками
            psi0 += ((a * np.exp(-((lat1 - e) / 2.2) ** 2))[:, None] * (env * np.cos(m * lam1 + rng.uniform(0, 6.28)))[None, :]).astype(np.float32)
    for v in VORT:
        j = int(np.clip((90 - v['lat']) / 180 * FH, 0, FH - 1))
        s = (1.0 if duz[j] < 0 else -1.0) * v['turns'] * 2 * np.pi * np.radians(v['sl']) * np.radians(v['sp'])
        dl = np.angle(np.exp(1j * (lam1 - np.radians(v['lon']))))
        gl = np.exp(-0.5 * (dl * np.cos(np.radians(v['lat'])) / np.radians(v['sl'])) ** 2)
        gp = np.exp(-0.5 * ((lat1 - v['lat']) / v['sp']) ** 2)
        psi0 += (s * gp[:, None] * gl[None, :]).astype(np.float32)

    def turb(seed):
        t = 0.0065 * (vnoise3(Pa, 13, seed, 2) - 0.5) * 2 + 0.0020 * (vnoise3(Pa, 36, seed + 5, 1) - 0.5) * 2
        return t.reshape(FH, FW) * amp_row[:, None].astype(np.float32)

    common = turb(100) * 0.6
    K = FW / (2 * np.pi)
    sinc = np.maximum(np.sin(th1), 0.12)[:, None]
    fields = []
    for ph in range(3):
        psi = (psi0 + common + turb(200 + ph) * 0.7) * fade[:, None]
        gy = np.gradient(psi, axis=0)
        gx = (np.roll(psi, -1, 1) - np.roll(psi, 1, 1)) * 0.5
        fields.append((padw((K * (uz[:, None] + gy * K) / sinc).astype(np.float32)), padw((-K * gx * K / sinc).astype(np.float32))))
    log('поле течения готово')
    X0, Y0 = np.meshgrid(np.arange(FW, dtype=np.float32), np.arange(FH, dtype=np.float32))
    X, Y = X0.copy(), Y0.copy()
    NS = 22
    dt = np.float32(1.0 / (3 * NS))
    for Vx, Vy in reversed(fields):
        for k in range(NS):
            vx, vy = samp(Vx, Y, X, FW), samp(Vy, Y, X, FW)
            Xm, Ym = X - 0.5 * dt * vx, np.clip(Y - 0.5 * dt * vy, 0, FH - 1)
            vx, vy = samp(Vx, Ym, Xm, FW), samp(Vy, Ym, Xm, FW)
            X -= dt * vx
            Y = np.clip(Y - dt * vy, 0, FH - 1)
    log('трассировка назад готова')
    return X - X0, Y - Y0


# ------------------------------------------------------------------ цвет гиганта
def paint_giant():
    Dx, Dy = backtrace()
    DW = min(W, 2048)
    DH = DW // 2
    C, A = np.zeros((DH, DW, 3), np.float32), np.zeros((DH, DW), np.float32)
    for d in DYES:
        add_blob(C, A, *d)
    Cp, Ap = [padw(C[..., k]) for k in range(3)], padw(A)
    Dxp, Dyp = padw(Dx), padw(Dy)
    img = np.empty((H, W, 3), np.float32)
    xs = np.arange(W, dtype=np.float32)
    RB = max(1, (1 << 20) // W)
    for r0 in range(0, H, RB):
        ys = np.arange(r0, min(H, r0 + RB), dtype=np.float32)
        Xg, Yg = np.meshgrid(xs, ys)
        fx, fy = (Xg + 0.5) * FW / W - 0.5, (Yg + 0.5) * FH / H - 0.5
        fyc = np.clip(fy, 0, FH - 1)
        x0 = Xg + samp(Dxp, fyc, fx, FW) * (W / FW)
        y0 = Yg + samp(Dyp, fyc, fx, FW) * (H / FH)
        lam0 = ((x0 + 0.5) / W * 2 * np.pi).ravel()
        th0 = np.clip((y0 + 0.5) / H * np.pi, 0, np.pi).ravel()
        lat0 = 90 - np.degrees(th0)
        P0 = sphere(lam0, th0)
        amp = np.interp(lat0, LAT, AMPL).astype(np.float32)
        wv = (vnoise3(P0 * np.array((1, 1, 4), np.float32), 22, 31, 2) - 0.5) * 2
        latp = lat0 + amp * wv * 0.5 + (vnoise3(P0, 110, 37, 1) - 0.5) * 0.2
        col = np.stack([np.interp(latp, LAT, LUT[:, k]) for k in range(3)], -1).astype(np.float32)
        n1 = vnoise3(P0 * np.array((1, 1, 3), np.float32), 7, 41, 3)
        n2 = vnoise3(P0 * np.array((1, 1, 2), np.float32), 48, 43, 2)
        n3 = vnoise3(P0, 4.5, 47, 2)
        n4 = vnoise3(P0 * np.array((0.35, 0.35, 6), np.float32), 30, 49, 1)       # тонкие длинные полоски
        col *= (1 + (0.04 + 0.07 * amp) * (n1 - 0.5) * 2)[:, None]
        col *= (1 + 0.04 * (n2 - 0.5) * 2 + 0.05 * (n4 - 0.5) * 2)[:, None]
        col += ((n3 - 0.5) * 2 * 0.035)[:, None] * np.array((1.0, 0.1, -1.0), np.float32)
        dx, dy = (x0.ravel() + 0.5) * DW / W - 0.5, np.clip((y0.ravel() + 0.5) * DH / H - 0.5, 0, DH - 1)
        a = samp(Ap, dy, dx, DW)
        col *= (1 - a)[:, None]
        for k in range(3):
            col[:, k] += samp(Cp[k], dy, dx, DW)
        img[r0:r0 + len(ys)] = col.reshape(len(ys), W, 3)
    log('цвет гиганта готов')
    return np.clip(img, 0.02, 0.97)


def to8(img):
    d = (np.random.default_rng(5).random(img.shape, dtype=np.float32) - 0.5) / 255.0       # размытие ступенек 8 бит
    return (np.clip(img + d, 0, 1) * 255 + 0.5).astype(np.uint8)


# ------------------------------------------------------------------ ночная сторона: сияния и зарницы (эмиссия)
def paint_night():
    img = np.zeros((H, W, 3), np.float32)
    xs = np.arange(W, dtype=np.float32)
    RB = max(1, (1 << 20) // W)
    poles = []
    for sgn, lo in ((1, 40.0), (-1, 250.0)):
        t, l = np.radians(5.0), np.radians(lo)
        poles.append(np.array((np.sin(t) * np.cos(l), np.sin(t) * np.sin(l), sgn * np.cos(t)), np.float32))
    for r0 in range(0, H, RB):
        ys = np.arange(r0, min(H, r0 + RB), dtype=np.float32)
        Xg, Yg = np.meshgrid(xs, ys)
        P = sphere(((Xg + 0.5) / W * 2 * np.pi).ravel(), ((Yg + 0.5) / H * np.pi).ravel())
        I = np.zeros(len(P), np.float32)
        for k, m in enumerate(poles):
            g = np.degrees(np.arccos(np.clip(P @ m, -1, 1)))
            near = g < 30
            if not near.any():
                continue
            Pn = P[near]
            g0 = 14.0 + 2.6 * (vnoise3(Pn, 3.0, 61 + k, 2) - 0.5) * 2
            arc = 0.20 + 0.80 * sstep(0.38, 0.72, vnoise3(Pn, 8.0, 63 + k, 3))
            ray = 0.65 + 0.35 * vnoise3(Pn, 70.0, 65 + k, 2)
            d = g[near] - g0
            I[near] += np.exp(-(d / 1.3) ** 2) * arc * ray * 0.60 + 0.10 * np.exp(-((d + 3.0) / 3.5) ** 2) * arc
        img[r0:r0 + len(ys)] = (I[:, None] * np.array((0.34, 0.56, 0.80), np.float32)).reshape(len(ys), W, 3)
    L, LA = np.zeros((H, W, 3), np.float32), np.zeros((H, W), np.float32)
    r = np.random.default_rng(23)
    belts = [(-15, 5), (13.5, 4.5), (-35, 4), (31.5, 3), (50, 4.5), (-55, 4)]
    for c in range(26):
        la0, sp = belts[int(r.integers(0, len(belts)))]
        la0, lo0 = la0 + r.uniform(-sp, sp) * 0.7, r.uniform(0, 360)
        add_blob(L, LA, la0, lo0, 2.6, 1.0, (0.030, 0.036, 0.050), 1.0)             # слабо подсвеченные изнутри облака
        for k in range(int(r.integers(5, 22))):
            s = r.uniform(0.07, 0.24)
            add_blob(L, LA, la0 + r.normal(0, 0.8), lo0 + r.normal(0, 2.6), s, s, (0.80, 0.86, 1.0), r.uniform(0.25, 0.9))
    log('ночная карта готова')
    return np.clip(img + L, 0, 1)


# ------------------------------------------------------------------ кольца
def paint_rings(n=4096, hh=64):
    u = (np.arange(n) + 0.5) / n

    def band(a, b, s):
        return sstep(a - s, a + s, u) * (1 - sstep(b - s, b + s, u))

    dusty, main, div = band(0.018, 0.115, 0.008), band(0.130, 0.540, 0.0025), band(0.540, 0.605, 0.002)
    outer, thin = band(0.605, 0.895, 0.003), band(0.950, 0.963, 0.0015)
    tau = 0.10 * dusty * (0.35 + 0.65 * u / 0.115) + main * (0.80 + 1.7 * sstep(0.13, 0.42, u)) + 0.035 * div \
        + outer * (0.66 - 0.28 * sstep(0.62, 0.895, u)) + 0.17 * thin
    fine = 0.28 * (noise1d(u, 34, 1) - 0.5) + 0.24 * (noise1d(u, 95, 2) - 0.5) + 0.18 * (noise1d(u, 280, 3) - 0.5) \
        + 0.12 * (noise1d(u, 820, 4) - 0.5)
    tau = tau * np.clip(1 + 2.0 * fine * (0.35 + 0.65 * main + 0.25 * outer), 0.12, 2.2)
    for g, w in ((0.238, 0.0016), (0.336, 0.0040), (0.452, 0.0020), (0.566, 0.0030), (0.792, 0.0050), (0.846, 0.0020)):
        tau = tau * (1 - 0.97 * np.exp(-((u - g) / w) ** 4))
        tau = tau * (1 + 0.45 * np.exp(-((u - g - 2.2 * w) / (1.2 * w)) ** 2) * np.cos((u - g) / w * 5.0) ** 2)   # волны плотности у щели
    alpha = 1 - np.exp(-tau)
    c_d, c_mi, c_mo = np.array((0.56, 0.50, 0.44)), np.array((0.76, 0.67, 0.55)), np.array((0.88, 0.82, 0.70))
    c_v, c_o, c_t = np.array((0.62, 0.59, 0.55)), np.array((0.83, 0.81, 0.77)), np.array((0.76, 0.77, 0.79))
    col = np.tile(c_d, (n, 1))
    col += (c_mi + (c_mo - c_mi) * sstep(0.13, 0.40, u)[:, None] - col) * sstep(0.118, 0.132, u)[:, None]
    col += (c_v - col) * sstep(0.536, 0.544, u)[:, None]
    col += (c_o - col) * sstep(0.600, 0.610, u)[:, None]
    col += (c_t - col) * sstep(0.90, 0.94, u)[:, None]
    lit = col * (0.80 + 0.20 * np.clip(0.5 + 2.2 * fine, 0, 1))[:, None]
    tr = tau * np.exp(-1.6 * tau)
    back = np.array((0.82, 0.73, 0.62)) * (tr / tr.max())[:, None]
    out = []
    for rgb in (lit, back):
        a = np.concatenate([rgb, alpha[:, None]], 1).astype(np.float32)
        out.append(to8(np.tile(a[None], (hh, 1, 1))))
    log('кольца готовы')
    return out[0], out[1], tau


def font(sz):
    try:
        return ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', sz)
    except Exception:
        return ImageFont.load_default()


def sheet(base8, lit8, back8, path):
    """Лист на приёмку: развёртка гиганта и обе полосы колец на шахматке."""
    S = Image.new('RGB', (1920, 1080), (24, 25, 28))
    S.paste(Image.fromarray(base8).resize((1920, 960), Image.LANCZOS), (0, 0))
    d = ImageDraw.Draw(S)
    yy, xx = np.mgrid[0:38, 0:1500]
    chk = np.where(((xx // 19) + (yy // 19)) % 2 == 0, 52, 30).astype(np.float32)[..., None]
    for k, (im, name) in enumerate(((lit8, 'кольца: освещённая сторона'), (back8, 'кольца: на просвет (неосвещённая сторона)'))):
        st = np.asarray(Image.fromarray(im).resize((1500, 38), Image.LANCZOS)).astype(np.float32)
        a = st[..., 3:4] / 255
        S.paste(Image.fromarray((st[..., :3] * a + chk * (1 - a)).astype(np.uint8)), (400, 968 + k * 56))
        d.text((12, 978 + k * 56), name, font=font(17), fill=(205, 205, 205))
        d.text((400, 1008 + k * 56), '← внутренний край (U = 0, %.3f R)' % RING_IN, font=font(13), fill=(150, 150, 150))
        d.text((1700, 1008 + k * 56), 'внешний край (U = 1, %.2f R) →' % RING_OUT, font=font(13), fill=(150, 150, 150))
    S.save(path)


if __name__ == '__main__':
    log('гигант %d×%d, течение %d×%d' % (W, H, FW, FH))
    base = paint_giant()
    base8 = to8(base)
    if not FINAL:
        Image.fromarray(base8).resize((1600, 800), Image.LANCZOS).save(os.path.join(TMP, 'giant_prev.png'))
        log('проба: shots/_tmp/giant_prev.png')
        sys.exit(0)
    Image.fromarray(base8).save(os.path.join(OUT, 'T_GasGiant_BaseColor.png'))
    night8 = to8(paint_night())
    Image.fromarray(night8).save(os.path.join(OUT, 'T_GasGiant_Night.png'))
    lit8, back8, tau = paint_rings()
    Image.fromarray(lit8).save(os.path.join(OUT, 'T_GasGiantRings_Lit.png'))
    Image.fromarray(back8).save(os.path.join(OUT, 'T_GasGiantRings_Backlit.png'))
    sheet(base8, lit8, back8, os.path.join(ROOT, 'shots', 'E_giant_unwrap.png'))
    bx, by = int(BIG['lon'] / 360 * W), int((90 - BIG['lat']) / 180 * H)
    Image.fromarray(base8[by - 350:by + 350, bx - 640:bx + 640]).save(os.path.join(TMP, 'giant_crop.png'))
    Image.fromarray(np.clip(night8.astype(np.float32) * 3, 0, 255).astype(np.uint8)).resize((1600, 800), Image.LANCZOS).save(os.path.join(TMP, 'giant_night_prev.png'))
    json.dump(dict(big_oval=dict(lat=BIG['lat'], lon=BIG['lon']), ring_in=RING_IN, ring_out=RING_OUT),
              open(os.path.join(OUT, '_params.json'), 'w', encoding='utf-8'))
    log('готово: export/gas_giant, shots/E_giant_unwrap.png')
