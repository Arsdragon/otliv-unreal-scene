# d_tex.py — художник текстур моделей этапа D (numpy + Pillow, Blender не нужен):
#   python tools/d_tex.py svetlyak        python tools/d_tex.py probe_wreck
# Читает export/<id>/layout.json, tris.npz (пишет сборочный скрипт) и _ao.png (запекание tools/d_bake.py, если есть).
# Каждый тексель знает своё 3D-положение (в осях детали и в мире), нормаль, класс поверхности и деталь, поэтому шум,
# износ, соль, «ватерлинии», швы и надписи рисуются в 3D — без разрывов на стыках островов развёртки.
# Выход: T_<Имя>_BaseColor.png (sRGB), _Normal.png (OpenGL, +Y), _ORM.png (R — затенение, G — шероховатость, B — металл).
import os, sys, json, math, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ID = sys.argv[1]
ATL = sys.argv[2] if len(sys.argv) > 2 else 'A'                      # атлас: A, M …
EXP = os.path.join(ROOT, 'export', ID)
LAY = json.load(open(os.path.join(EXP, 'layout.json'), encoding='utf-8'))
PREFIX = LAY.get('tex', {}).get(ATL)                                  # имя набора текстур атласа
N = LAY['atlas']
CLASSES = {int(k): v for k, v in LAY['classes'].items()}
FONT = next(p for p in (r'C:\Windows\Fonts\bahnschrift.ttf', r'C:\Windows\Fonts\arialbd.ttf') if os.path.exists(p))
T0 = time.time()


def log(*a):
    print('[%5.1f с]' % (time.time() - T0), *a, flush=True)


# ============================================================ геометрия текселей
def rasterize():
    tf = os.path.join(EXP, 'tris_%s.npz' % ATL)
    F = np.load(tf if os.path.exists(tf) else os.path.join(EXP, 'tris.npz'))
    UV, LP, WN, CL, OB = F['uv'], F['lp'], F['wn'], F['cls'], F['obj']
    MATS, NAMES = F['mats'], [str(s) for s in F['names']]
    im = Image.new('I', (N, N), 0)
    d = ImageDraw.Draw(im)
    for i in range(len(UV)):
        pts = [tuple(p) for p in UV[i]]
        d.polygon(pts, fill=i + 1, outline=i + 1)
    ids = np.asarray(im, dtype=np.int64) - 1
    cov = ids >= 0
    for _ in range(5):                                       # запас 5 пикселей вокруг островов
        hole = ids < 0
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            sh = np.roll(np.roll(ids, dy, 0), dx, 1)
            f = hole & (sh >= 0)
            ids[f] = sh[f]
            hole = ids < 0
    ys, xs = np.nonzero(ids >= 0)
    t = ids[ys, xs]
    P = np.stack([xs + 0.5, ys + 0.5], 1)
    A, B, C = UV[t, 0].astype(np.float64), UV[t, 1].astype(np.float64), UV[t, 2].astype(np.float64)
    v0, v1, v2 = B - A, C - A, P - A
    d00, d01, d11 = (v0 * v0).sum(1), (v0 * v1).sum(1), (v1 * v1).sum(1)
    d20, d21 = (v2 * v0).sum(1), (v2 * v1).sum(1)
    den = d00 * d11 - d01 * d01
    den = np.where(np.abs(den) < 1e-9, 1e-9, den)
    b1 = np.clip((d11 * d20 - d01 * d21) / den, 0, 1)
    b2 = np.clip((d00 * d21 - d01 * d20) / den, 0, 1)
    s = b1 + b2
    k = np.where(s > 1, 1 / np.maximum(s, 1e-9), 1.0)
    b1, b2 = b1 * k, b2 * k
    b0 = 1 - b1 - b2
    lp = (b0[:, None] * LP[t, 0] + b1[:, None] * LP[t, 1] + b2[:, None] * LP[t, 2]).astype(np.float32)
    wn = (b0[:, None] * WN[t, 0] + b1[:, None] * WN[t, 1] + b2[:, None] * WN[t, 2])
    wn = (wn / np.maximum(np.linalg.norm(wn, axis=1, keepdims=True), 1e-6)).astype(np.float32)
    ob = OB[t].astype(np.int32)
    M = MATS[ob]
    wp = (np.einsum('nij,nj->ni', M[:, :3, :3], lp) + M[:, :3, 3]).astype(np.float32)
    a3 = 0.5 * np.linalg.norm(np.cross(LP[:, 1] - LP[:, 0], LP[:, 2] - LP[:, 0]), axis=1)
    e1, e2 = UV[:, 1] - UV[:, 0], UV[:, 2] - UV[:, 0]
    a2 = 0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0])
    mpp_t = np.sqrt(a3 / np.maximum(a2, 1e-6))
    g = dict(ys=ys, xs=xs, cls=CL[t].astype(np.int32), obj=ob, lp=lp, wp=wp, wn=wn, mpp=mpp_t[t].astype(np.float32),
             cov=cov[ys, xs], names=NAMES, mats=MATS)
    log('растр: %d текселей, %d треугольников' % (len(ys), len(UV)))
    return g


def vnoise(p, freq, seed, octaves=3, stretch=(1, 1, 1)):
    """Плавный 3D-шум 0…1 по точкам p (M×3, метры); stretch — вытяжка по осям (потёки, струи)."""
    p = p.astype(np.float64) * np.array(stretch, np.float64)
    out = np.zeros(len(p), np.float64)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        q = p * (freq * 2 ** o) + (seed * 17.31 + o * 3.7)
        i = np.floor(q).astype(np.int64)
        f = q - i
        f = f * f * (3 - 2 * f)

        def h(dx, dy, dz):
            n = ((i[:, 0] + dx) * 73856093) ^ ((i[:, 1] + dy) * 19349663) ^ ((i[:, 2] + dz) * 83492791) ^ (seed * 2654435761 + o * 97)
            n = (n ^ (n >> 13)) * 1274126177
            return ((n >> 7) & 0xFFFF).astype(np.float64) / 65535.0
        x0 = h(0, 0, 0) * (1 - f[:, 0]) + h(1, 0, 0) * f[:, 0]
        x1 = h(0, 1, 0) * (1 - f[:, 0]) + h(1, 1, 0) * f[:, 0]
        x2 = h(0, 0, 1) * (1 - f[:, 0]) + h(1, 0, 1) * f[:, 0]
        x3 = h(0, 1, 1) * (1 - f[:, 0]) + h(1, 1, 1) * f[:, 0]
        y0 = x0 * (1 - f[:, 1]) + x1 * f[:, 1]
        y1 = x2 * (1 - f[:, 1]) + x3 * f[:, 1]
        out += amp * (y0 * (1 - f[:, 2]) + y1 * f[:, 2])
        tot += amp
        amp *= 0.5
    return (out / tot).astype(np.float32)


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ============================================================ разметка в осях детали
def obj_mask(g, name):
    return g['obj'] == g['names'].index(name) if name in g['names'] else np.zeros(len(g['obj']), bool)


def local_dir(g, name, d):
    """Направление d в осях детали -> в мире (для сравнения с нормалями мира)."""
    M = g['mats'][g['names'].index(name)]
    v = M[:3, :3] @ np.array(d, np.float32)
    return v / max(np.linalg.norm(v), 1e-9)


def rrect_sdf(a, b, w, h, r):
    qx, qy = np.abs(a) - (w / 2 - r), np.abs(b) - (h / 2 - r)
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r


def frame_coords(g, m, c, u, v):
    """Координаты в плоскости (u, v) с началом c — для текселей маски m (оси детали)."""
    rel = g['lp'][m] - np.array(c, np.float32)
    u, v = np.array(u, np.float32), np.array(v, np.float32)
    n = np.cross(u, v)
    return rel @ u, rel @ v, rel @ n


_font_cache = {}


def text_img(text, px=160):
    key = (text, px)
    if key not in _font_cache:
        f = ImageFont.truetype(FONT, px)
        x0, y0, x1, y1 = f.getbbox(text)
        im = Image.new('L', (x1 - x0 + 8, y1 - y0 + 8), 0)
        ImageDraw.Draw(im).text((4 - x0, 4 - y0), text, font=f, fill=255)
        _font_cache[key] = np.asarray(im, np.float32) / 255.0
    return _font_cache[key]


def decal_text(g, obj, text, c, u, v, h, depth=0.02, facing=0.3, w=None):
    """Надпись text высотой h (м) в плоскости (u — направление строки, v — вверх) с центром c, в осях детали obj.
    Возвращает (маска текселей, покрытие 0…1)."""
    m = obj_mask(g, obj)
    if not m.any():
        return m, np.zeros(0, np.float32)
    img = text_img(text)
    ih, iw = img.shape
    w = w or h * iw / ih
    a, b, dn = frame_coords(g, m, c, u, v)
    n_w = local_dir(g, obj, np.cross(u, v))
    ok = (np.abs(a) < w / 2) & (np.abs(b) < h / 2) & (np.abs(dn) < depth) & (g['wn'][m] @ n_w > facing)
    px = np.clip(((a / w + 0.5) * (iw - 1)).astype(np.int32), 0, iw - 1)
    py = np.clip(((0.5 - b / h) * (ih - 1)).astype(np.int32), 0, ih - 1)
    cv = np.where(ok, img[py, px], 0.0).astype(np.float32)
    return m, cv


# ============================================================ запись карт
def to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def write_maps(g, prefix, base, rough, metal, height, ao):
    """base — линейный цвет (M×3); height — метры; ao — 0…1. Нормали — из высоты с учётом размера текселя."""
    ys, xs = g['ys'], g['xs']
    H = np.zeros((N, N), np.float32)
    H[ys, xs] = height
    MPP = np.full((N, N), 1e-3, np.float32)
    MPP[ys, xs] = np.maximum(np.nan_to_num(g['mpp'], nan=1e-3), 2e-5)          # вырожденные треугольники — без деления на ноль
    H = np.nan_to_num(H)
    gx = (np.roll(H, -1, 1) - np.roll(H, 1, 1)) * 0.5 / MPP
    gy = (np.roll(H, -1, 0) - np.roll(H, 1, 0)) * 0.5 / MPP
    gx, gy = np.clip(np.nan_to_num(gx), -3, 3), np.clip(np.nan_to_num(gy), -3, 3)
    inv = 1.0 / np.sqrt(gx * gx + gy * gy + 1.0)
    nrm = np.stack(((-gx * inv) * 0.5 + 0.5, (gy * inv) * 0.5 + 0.5, inv * 0.5 + 0.5), -1)
    img = np.zeros((N, N, 3), np.float32)
    img[:] = (0.5, 0.5, 0.5)
    img[ys, xs] = to_srgb(base)
    p = os.path.join(EXP, prefix)
    Image.fromarray((img * 255 + 0.5).astype(np.uint8)).save(p + '_BaseColor.png')
    Image.fromarray((np.clip(nrm, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p + '_Normal.png')
    orm = np.zeros((N, N, 3), np.float32)
    orm[:] = (1.0, 0.6, 0.0)
    orm[ys, xs, 0] = np.clip(ao, 0, 1)
    orm[ys, xs, 1] = np.clip(rough, 0.04, 1)
    orm[ys, xs, 2] = np.clip(metal, 0, 1)
    Image.fromarray((orm * 255 + 0.5).astype(np.uint8)).save(p + '_ORM.png')
    Image.fromarray((img * 255 + 0.5).astype(np.uint8)).resize((1024, 1024), Image.LANCZOS).save(
        os.path.join(ROOT, 'shots', '_tmp', prefix + '_preview.png'))
    log('сохранено', prefix)


def load_ao(g):
    p = os.path.join(EXP, '_ao_%s.png' % ATL)
    p = p if os.path.exists(p) else os.path.join(EXP, '_ao.png')
    if not os.path.exists(p):
        log('нет _ao.png — затенение белое')
        return np.ones(len(g['ys']), np.float32)
    a = np.asarray(Image.open(p).convert('L').resize((N, N), Image.BILINEAR), np.float32) / 255.0
    return a[g['ys'], g['xs']]


def palette(g, pal):
    """Цвет, шероховатость, металл по классам: pal = {имя класса: (цвет, шерох., металл)}."""
    M = len(g['cls'])
    base, rough, metal = np.full((M, 3), 0.5, np.float32), np.full(M, 0.6, np.float32), np.zeros(M, np.float32)
    for cid, name in CLASSES.items():
        if name in pal:
            m = g['cls'] == cid
            c, r, mt = pal[name]
            base[m], rough[m], metal[m] = c, r, mt
    return base, rough, metal


def cls_mask(g, *names):
    ids = [cid for cid, nm in CLASSES.items() if nm in names]
    return np.isin(g['cls'], ids)


exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'd_tex_rules.py'), encoding='utf-8').read())

if __name__ == '__main__':
    g = rasterize()
    RULES[ID](g)
    log('готово')
