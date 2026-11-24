# chaika_tex.py — художник текстур (обычный Python: numpy + Pillow, Blender не нужен).
#   python tools/chaika_tex.py chaika_ext [A B C]        python tools/chaika_tex.py chaika_cockpit [A B]
# Читает export/<модель>/layout.json и faces_<атлас>.npz (их пишут сборочные скрипты), рисует в развёртке
# плитку, швы, крепёж, надписи, маркировку, нагар и потёки и сохраняет <имя>_{BaseColor|Normal|ORM}.png
# (ORM: R — затенение, G — шероховатость, B — металл).
import os, sys, json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = {'chaika_ext': dict(names={'A': 'T_ChaikaHull', 'B': 'T_ChaikaParts', 'C': 'T_ChaikaGear'}, interior=False),
          'chaika_cockpit': dict(names={'A': 'T_CockpitFront', 'B': 'T_CockpitRear'}, interior=True)}
MODEL = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in MODELS else 'chaika_ext'
CFG = MODELS[MODEL]
EXP = os.path.join(ROOT, 'export', MODEL)
N = 4096
layout = json.load(open(os.path.join(EXP, 'layout.json'), encoding='utf-8'))
FONT = next(p for p in (r'C:\Windows\Fonts\bahnschrift.ttf', r'C:\Windows\Fonts\arialbd.ttf') if os.path.exists(p))
COL = {'ink': np.array((0.075, 0.08, 0.085), np.float32), 'orange': np.array((0.83, 0.31, 0.05), np.float32),
       'label': np.array((0.80, 0.80, 0.76), np.float32)}
ORANGE = COL['orange']

# класс -> (цвет, шероховатость, металл)
MAT = {0: ((0.45, 0.45, 0.45), 0.6, 0.0), 1: ((0.84, 0.84, 0.82), 0.52, 0.0), 2: ((0.050, 0.052, 0.056), 0.62, 0.0),
       3: ((0.15, 0.16, 0.17), 0.42, 0.0), 4: ((0.60, 0.63, 0.61), 0.55, 0.0), 5: ((0.15, 0.155, 0.16), 0.50, 0.0),
       6: ((0.66, 0.66, 0.65), 0.56, 0.0),
       10: ((0.82, 0.82, 0.80), 0.42, 0.0), 11: ((0.085, 0.09, 0.095), 0.50, 0.0), 12: ((0.74, 0.75, 0.76), 0.34, 1.0),
       13: ((0.33, 0.33, 0.34), 0.42, 1.0), 14: ((0.92, 0.92, 0.92), 0.10, 1.0), 15: ((0.028, 0.028, 0.03), 0.85, 0.0),
       16: ((0.83, 0.31, 0.05), 0.46, 0.0), 17: ((0.40, 0.35, 0.31), 0.38, 1.0), 18: ((0.19, 0.19, 0.20), 0.72, 0.0),
       20: ((0.66, 0.65, 0.62), 0.86, 0.0), 21: ((0.075, 0.078, 0.082), 0.62, 0.0), 22: ((0.40, 0.41, 0.42), 0.58, 0.0),
       23: ((0.12, 0.14, 0.17), 0.92, 0.0), 24: ((0.40, 0.38, 0.34), 0.80, 0.0), 25: ((0.50, 0.53, 0.51), 0.50, 0.0),
       26: ((0.04, 0.04, 0.045), 0.35, 0.0), 27: ((0.80, 0.79, 0.75), 0.80, 0.0), 28: ((0.05, 0.052, 0.055), 0.40, 0.0),
       29: ((0.78, 0.78, 0.74), 0.50, 0.0), 19: ((0.25, 0.26, 0.27), 0.60, 0.0)}
PAINTED = (4, 10, 11, 16, 22, 25)
TILE = {1: 0.25, 2: 0.15, 6: 0.25}


def noise(h, w, cell, seed, octaves=3, sx=1.0, sy=1.0):
    """Плавный шум 0…1: случайные сетки, растянутые бикубически; sx, sy — вытяжка по осям."""
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        gh = max(2, int(h / (cell * sy) * 2 ** o) + 2)
        gw = max(2, int(w / (cell * sx) * 2 ** o) + 2)
        g = (rng.random((gh, gw)) * 255).astype(np.uint8)
        out += amp * np.asarray(Image.fromarray(g).resize((w, h), Image.BICUBIC), np.float32) / 255.0
        tot += amp
        amp *= 0.5
    return out / tot


def raster(at):
    F = np.load(os.path.join(EXP, 'faces_%s.npz' % at))
    off, uv, cls, z, nz = F['off'], F['uv'], F['cls'], F['z'], F['nz']
    ic, iz, inz = Image.new('L', (N, N), 0), Image.new('L', (N, N), 0), Image.new('L', (N, N), 127)
    dc, dz, dn = ImageDraw.Draw(ic), ImageDraw.Draw(iz), ImageDraw.Draw(inz)
    zq = np.clip(z * 50.0, 0, 255).astype(np.uint8)
    nq = np.clip((nz + 1) * 127.5, 0, 255).astype(np.uint8)
    for i in range(len(cls)):
        pts = uv[off[i]:off[i + 1]].ravel().tolist()
        c = int(cls[i])
        dc.polygon(pts, fill=c, outline=c)
        dz.polygon(pts, fill=int(zq[i]), outline=int(zq[i]))
        dn.polygon(pts, fill=int(nq[i]), outline=int(nq[i]))
    cov = np.asarray(ic) > 0
    for _ in range(5):                                   # запас по краям островов развёртки
        hole = np.asarray(ic) == 0
        ic = Image.fromarray(np.where(hole, np.asarray(ic.filter(ImageFilter.MaxFilter(3))), np.asarray(ic)))
        iz = Image.fromarray(np.where(hole, np.asarray(iz.filter(ImageFilter.MaxFilter(3))), np.asarray(iz)))
        inz = Image.fromarray(np.where(hole, np.asarray(inz.filter(ImageFilter.MaxFilter(3))), np.asarray(inz)))
    return np.asarray(ic).copy(), cov, np.asarray(iz, np.float32) / 50.0, np.asarray(inz, np.float32) / 127.5 - 1.0


def text_mask(text, hpx):
    f = ImageFont.truetype(FONT, int(hpx * 1.25) + 4)
    x0, y0, x1, y1 = f.getbbox(text)
    im = Image.new('L', (x1 - x0 + 4, y1 - y0 + 4), 0)
    ImageDraw.Draw(im).text((2 - x0, 2 - y0), text, font=f, fill=255)
    return im


def stamp(dst, src, p_tl, e1, e2):
    """Вклеить картинку src в маску dst: левый верхний угол p_tl, вектор вдоль строки e1 и вниз e2 (пиксели атласа)."""
    w, h = src.size
    cs = [p_tl, p_tl + e1, p_tl + e2, p_tl + e1 + e2]
    bx0, by0 = int(min(c[0] for c in cs)) - 1, int(min(c[1] for c in cs)) - 1
    bx1, by1 = int(max(c[0] for c in cs)) + 2, int(max(c[1] for c in cs)) + 2
    Mi = np.linalg.inv(np.array([[e1[0] / w, e2[0] / h], [e1[1] / w, e2[1] / h]]))
    o = Mi @ (np.array([bx0, by0], float) - p_tl)
    t = src.transform((bx1 - bx0, by1 - by0), Image.AFFINE, (Mi[0, 0], Mi[0, 1], o[0], Mi[1, 0], Mi[1, 1], o[1]), Image.BICUBIC)
    box = dst.crop((bx0, by0, bx1, by1))
    dst.paste(Image.fromarray(np.maximum(np.asarray(box), np.asarray(t))), (bx0, by0))


def decals(c, s, M):
    """Надписи, контуры люков, порты, линии. M — маски: ink, orange, label, groove, rivet, dark."""
    x0, y0 = c['rect'][0], c['rect'][1]
    px = lambda p: np.array((x0 + p[0] * s, y0 + p[1] * s), float)
    d_gr, d_rv, d_or, d_dk = (ImageDraw.Draw(M[k]) for k in ('groove', 'rivet', 'orange', 'dark'))
    for d in c.get('decals', []):
        if d['type'] == 'band':
            continue
        if d['type'] == 'line':
            a, b = px(d['q'][0]), px(d['q'][1])
            for key in [d.get('color', 'label')] + (['glow'] if d.get('glow') else []):
                ImageDraw.Draw(M[key]).line([tuple(a), tuple(b)], fill=255, width=max(1, int(round(d.get('w', 0.001) * s))))
            continue
        p0, p1, pu = (px(p) for p in d['q'])
        e1, e2 = p1 - p0, p0 - pu                           # вдоль строки и вниз
        W, H = np.linalg.norm(e1), np.linalg.norm(e2)
        if d['type'] == 'text':
            tm = text_mask(d['text'], max(7, H))
            tw = tm.size[0] * H / tm.size[1]
            k = min(1.0, W / tw)
            off = 0.0 if d.get('align') == 'l' else (W - tw * k) / 2
            for key in [d.get('color', 'ink')] + (['glow'] if d.get('glow') else []):
                stamp(M[key], tm, pu + e1 / W * off + e2 * (1 - k) / 2, e1 / W * tw * k, e2 * k)
        elif d['type'] == 'rect':
            cs = [tuple(pu), tuple(pu + e1), tuple(p0 + e1), tuple(p0)]
            for key in [d.get('color', 'label')] + (['glow'] if d.get('glow') else []):
                ImageDraw.Draw(M[key]).line(cs + [cs[0]], fill=255, width=max(1, int(round(d.get('w', 0.001) * s))))
        elif d['type'] == 'panel':
            cs = [tuple(pu), tuple(pu + e1), tuple(p0 + e1), tuple(p0)]
            if d['style'] == 'rescue':
                d_or.line(cs + [cs[0]], fill=255, width=max(3, int(0.012 * s)))
            else:
                d_gr.line(cs + [cs[0]], fill=255, width=2)
                step = 0.075 * s
                cen = (np.array(cs[0]) + np.array(cs[2])) / 2
                for a, b in zip(cs, cs[1:] + [cs[0]]):
                    a, b = np.array(a), np.array(b)
                    L = np.linalg.norm(b - a)
                    nrm = np.array((-(b - a)[1], (b - a)[0])) / L
                    if np.dot(nrm, cen - a) < 0:
                        nrm = -nrm
                    for i in range(int(L / step) + 1):
                        q = a + (b - a) * (i * step / L) + nrm * 0.028 * s
                        d_rv.ellipse([q[0] - 1.9, q[1] - 1.9, q[0] + 1.9, q[1] + 1.9], fill=255)
                if d.get('label'):
                    hh = 0.042 * s
                    tm = text_mask(d['label'], hh)
                    tw = tm.size[0] * hh / tm.size[1]
                    stamp(M['ink'], tm, pu + e1 / W * 0.06 * s + e2 / H * 0.055 * s, e1 / W * tw, e2 / H * hh)
        elif d['type'] == 'port':
            cen, r = (p1 + pu) / 2, W / 2
            d_gr.ellipse([cen[0] - r, cen[1] - r, cen[0] + r, cen[1] + r], outline=255, width=2)
            d_dk.ellipse([cen[0] - r * 0.6, cen[1] - r * 0.6, cen[0] + r * 0.6, cen[1] + r * 0.6], fill=255)
            for k in range(6):
                q = cen + np.array((math.cos(math.pi * k / 3), math.sin(math.pi * k / 3))) * r * 0.82
                d_rv.ellipse([q[0] - 1.6, q[1] - 1.6, q[0] + 1.6, q[1] + 1.6], fill=255)


def tiles(base, rough, height, cls, um, rows, s, seed):
    """Плитка теплозащиты. rows — координата ряда в метрах (2D или столбец): ряды идут вдоль линий корпуса."""
    for cid, size in TILE.items():
        m = cls == cid
        if not m.any():
            continue
        row = np.floor(rows / size).astype(np.int64)
        xs = um[None, :] + (row % 2) * (size * 0.5)
        col = np.floor(xs / size).astype(np.int64)
        fx = xs / size - col
        fy = rows / size - row
        edge = np.minimum(np.minimum(fx, 1 - fx), np.minimum(fy, 1 - fy)) * size * s       # до края плитки, пикс
        hsh = ((row * 73856093) ^ (col * 19349663) ^ (seed + cid * 977)) & 0xFFFF
        rnd = hsh.astype(np.float32) / 65535.0
        r2 = (((hsh * 2654435761) >> 7) & 0xFFFF).astype(np.float32) / 65535.0
        dark = cid == 2
        tint = 1.0 + (rnd - 0.5) * (0.06 if not dark else 0.12)
        tint = np.where(r2 > 0.975, tint + (0.06 if not dark else 0.10), tint)               # заменённые плитки
        tint = np.where(r2 < 0.030, tint - (0.07 if not dark else 0.05), tint)
        gap = np.clip(edge / 1.5, 0, 1)
        g0 = 0.35 if dark else 0.58
        k = (tint * (g0 + (1 - g0) * gap)).astype(np.float32)
        base[m] *= k[m][:, None]
        height[m] = (np.clip(edge / 3.5, 0, 1) * (0.9 + 0.2 * rnd))[m]
        rough[m] += ((rnd - 0.5) * 0.08 + (1 - gap) * 0.2)[m]


def panel_grid(base, height, cls, cid, um, vm, s, du, dv, dots=True):
    """Швы панелей (капоты мотогондол, обивка кабины) и крепёж вдоль них."""
    m = cls == cid
    fu, fv = np.abs((um / du + 0.5) % 1.0 - 0.5) * du * s, np.abs((vm / dv + 0.5) % 1.0 - 0.5) * dv * s
    line = (np.minimum(fu[None, :], fv[:, None]) < 1.1) & m
    base[line] *= 0.40
    height[line] -= 0.8
    if dots:
        pitch = 0.06 * s
        ru = (np.abs(fu[None, :] - 0.022 * s) < 1.7) & (np.abs((np.arange(len(vm)) % pitch) - pitch / 2)[:, None] < 1.7)
        rv = (np.abs(fv[:, None] - 0.022 * s) < 1.7) & (np.abs((np.arange(len(um)) % pitch) - pitch / 2)[None, :] < 1.7)
        riv = (ru | rv) & m
    else:                                                   # кнопки по углам панелей обивки
        riv = (np.abs(fu[None, :] - 0.03 * s) < 2.2) & (np.abs(fv[:, None] - 0.03 * s) < 2.2) & m
    base[riv] *= 0.78
    height[riv] += 0.7


def paint(at):
    print('атлас', at, '— растеризация граней…')
    inter = CFG['interior']
    cls, cov, zmap, nzmap = raster(at)
    lut_c, lut_r, lut_m = np.zeros((64, 3), np.float32), np.zeros(64, np.float32), np.zeros(64, np.float32)
    for k, (c, r, mt) in MAT.items():
        lut_c[k], lut_r[k], lut_m[k] = c, r, mt
    base, rough, metal = lut_c[cls], lut_r[cls], lut_m[cls]
    height = np.zeros((N, N), np.float32)
    seed = {'A': 11, 'B': 23, 'C': 37}[at] + (100 if inter else 0)
    n_fine, n_mid, n_big = noise(N, N, 3, seed, 2), noise(N, N, 70, seed + 1, 3), noise(N, N, 520, seed + 2, 3)
    M = {k: Image.new('L', (N, N), 0) for k in ('ink', 'orange', 'label', 'groove', 'rivet', 'dark', 'glow')}
    tiled = np.zeros((N, N), bool)
    soot = np.zeros((N, N), np.float32)
    drip = np.zeros((N, N), np.float32)
    for nm, c in layout[at].items():
        if c['kind'] == 'mech':
            continue
        x0, y0, x1, y1 = (int(round(v)) for v in c['rect'])
        x0, y0, x1, y1 = max(0, x0 - 4), max(0, y0 - 4), min(N, x1 + 4), min(N, y1 + 4)
        s = c['scale'] * c.get('dens', 1.0)
        sl = np.s_[y0:y1, x0:x1]
        um, vm = (np.arange(x0, x1) - c['rect'][0]) / s, (np.arange(y0, y1) - c['rect'][1]) / s
        sc = cls[sl]
        bands = [(d['u'][0], d['u'][1], 'u') for d in c.get('decals', []) if d['type'] == 'band']
        bands += [(a, b, 'u') for a, b, _ in c.get('bands', [])] + [(a, b, 'v') for a, b, _ in c.get('vbands', [])]
        for a, b, ax in bands:                               # оранжевые пояса — только по белой обшивке
            mm = ((um >= a) & (um <= b))[None, :] if ax == 'u' else ((vm >= a) & (vm <= b))[:, None]
            base[sl][mm & (sc == 1)] = ORANGE
        rows = vm[:, None]
        if c.get('zones'):                                   # корпус: ряды плитки вдоль конька, плеча и киля
            z = c['zones']
            T = np.abs(vm - c['smax'])[:, None]
            ts, tc, tk = (np.interp(um, z['u'], z[k]).astype(np.float32)[None, :] for k in ('ts', 'tc', 'tk'))
            rows = np.where(T < ts, T, np.where(T < tc, T - ts, tk - T)).astype(np.float32)
            side = (T > ts) & (T < tc) & (sc == 1)
            d_ch = tc - T                                     # расстояние вверх от скулы
            soot[sl] = np.where(side, np.clip(1 - d_ch / 0.28, 0, 1) ** 1.6 * 0.42, 0) + \
                np.clip(1.0 - um / 2.4, 0, 1)[None, :] * 0.30 * (sc == 1)
            dn = noise(y1 - y0, x1 - x0, 2.6, seed + 9, 2, sy=70)          # тонкие вертикальные потёки по бортам
            dn2 = noise(y1 - y0, x1 - x0, 40, seed + 10, 2, sy=3)
            drip[sl] = np.clip((dn - 0.66) * 6.0, 0, 1) * np.clip((dn2 - 0.35) * 3, 0, 1) * side
            del dn, dn2, T, d_ch, side
        if c.get('tiles'):
            tiles(base[sl], rough[sl], height[sl], sc, um, rows, s, seed)
            tiled[sl] |= np.isin(sc, list(TILE))
        if c.get('panels'):
            pc = c.get('panel_cls', 10)
            panel_grid(base[sl], height[sl], sc, pc, um, vm, s, c['panels'][0], c['panels'][1], dots=pc == 10)
        for a, b, v in c.get('lines', []):                   # щели рулевых поверхностей
            ImageDraw.Draw(M['groove']).line([(c['rect'][0] + a * s, c['rect'][1] + v * s), (c['rect'][0] + b * s, c['rect'][1] + v * s)],
                                             fill=255, width=3)
        if c.get('u_soot'):                                  # побежалость у сопла мотогондолы
            f = np.clip((um - (c['u_soot'][0] - 0.9)) / 0.9, 0, 1)[None, :] * (sc == 10)
            base[sl] *= (1 - 0.5 * f * (0.6 + 0.4 * n_big[sl]))[:, :, None]
            rough[sl] += 0.2 * f
        decals(c, s, M)
    A = {k: np.asarray(v, np.float32) / 255 for k, v in M.items()}
    base *= (1 - 0.6 * A['groove'] - 0.25 * A['rivet'] - 0.7 * A['dark'])[:, :, None]
    height += -0.9 * A['groove'] + 0.8 * A['rivet'] - 0.5 * A['dark']
    for k in ('ink', 'orange', 'label'):
        base += (COL[k] - base) * (0.94 * A[k])[:, :, None]
    glow = A['glow']
    del A, M
    base *= (1 - 0.70 * soot)[:, :, None]                    # нагар: мягкий градиент над скулой и на носу
    rough += 0.2 * soot
    base *= (1 - 0.24 * drip)[:, :, None]
    base[..., 2] -= 0.015 * drip
    del soot, drip
    belly = cls == 2
    base[belly] *= (0.86 + 0.5 * n_big[belly])[:, None]
    base[belly] += np.array((0.016, 0.011, 0.006), np.float32) * n_big[belly][:, None]
    rcc = cls == 5
    base[rcc] *= (0.85 + 0.35 * n_mid[rcc])[:, None]
    noz = cls == 17                                          # спокойная побежалость металла сопел
    if noz.any():
        t = n_big[noz][:, None]
        base[noz] = (np.array((0.235, 0.215, 0.20), np.float32) + np.array((0.10, 0.065, 0.02), np.float32) * np.clip(1.4 - 2.4 * t, 0, 1)
                     + np.array((0.0, 0.015, 0.07), np.float32) * np.clip(2.4 * t - 1.1, 0, 1)) * (0.9 + 0.2 * n_mid[noz][:, None])
    tread = cls == 18
    height[tread] += (n_fine[tread] - 0.5) * 1.2
    fab = np.isin(cls, (20, 23, 24, 27))                     # ткань: мелкая фактура
    height[fab] += (n_fine[fab] - 0.5) * 0.10
    mech = ~tiled & cov
    # потёртые кромки агрегатов: редкие мелкие сколы краски вдоль краёв островов развёртки, без рельефа
    er = np.asarray(Image.fromarray((cov * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(5))) > 0
    chip = cov & ~er & np.isin(cls, PAINTED) & mech & (n_fine > (0.66 if inter else 0.60))
    base[chip] = base[chip] * 0.5 + np.array((0.60, 0.61, 0.62), np.float32) * 0.5
    metal[chip], rough[chip] = 0.7, 0.40
    if not inter:
        low = np.clip((0.9 - zmap) / 0.9, 0, 1) * mech * (0.5 + 0.5 * n_big)   # грязь и соль у воды — плавно
        base += (np.array((0.30, 0.27, 0.23), np.float32) - base) * (0.30 * low)[:, :, None]
        rough += 0.15 * low
        metal *= (1 - 0.4 * low)
        under = np.clip(-nzmap - 0.3, 0, 1) * mech * (cls == 10)             # копоть на нижних поверхностях
        base *= (1 - 0.22 * under * n_big)[:, :, None]
    base *= (0.94 + 0.12 * n_big)[:, :, None]
    rough += (n_mid - 0.5) * 0.08
    ao = np.ones((N, N), np.float32)
    # ---- нормали из высоты
    k = 1.6
    gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5 * k
    gy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5 * k
    inv = 1.0 / np.sqrt(gx * gx + gy * gy + 1.0)
    nrm = np.stack(((-gx * inv) * 0.5 + 0.5, (gy * inv) * 0.5 + 0.5, inv * 0.5 + 0.5), -1)
    del gx, gy, inv, height
    p = os.path.join(EXP, CFG['names'][at])
    Image.fromarray((np.clip(base, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p + '_BaseColor.png')
    Image.fromarray((np.clip(nrm, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p + '_Normal.png')
    orm = np.stack((ao, np.clip(rough, 0.05, 1), np.clip(metal, 0, 1)), -1)
    Image.fromarray((orm * 255 + 0.5).astype(np.uint8)).save(p + '_ORM.png')
    if glow.max() > 0:                                       # подсветка надписей: тёплая и неяркая (линейные 0,50 / 0,33 / 0,17)
        em = np.clip(glow[:, :, None] * np.array((0.50, 0.33, 0.17), np.float32), 0, 1)
        em = np.where(em <= 0.0031308, em * 12.92, 1.055 * np.power(em, 1 / 2.4) - 0.055)
        Image.fromarray((np.clip(em, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p + '_Emissive.png')
        print('сохранено', CFG['names'][at] + '_Emissive')
    elif os.path.exists(p + '_Emissive.png'):
        os.remove(p + '_Emissive.png')
    print('сохранено', CFG['names'][at], '— покрытие развёртки %.0f %%' % (cov.mean() * 100))


if __name__ == '__main__':
    ats = [a for a in sys.argv[1:] if a in CFG['names']] or list(CFG['names'])
    for at in ats:
        paint(at)
