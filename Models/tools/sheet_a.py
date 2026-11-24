# sheet_a.py — сборка листов этапа A из кадров shots/_tmp/A_*.png (обычный Python + Pillow + numpy):
#   python tools/sheet_a.py
import os, json, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, 'shots', '_tmp')
PX = os.environ.get('SHOTPREFIX', 'A')
OUT = os.path.join(ROOT, 'shots')
F = lambda size, bold=False: ImageFont.truetype(r'C:\Windows\Fonts\%s' % ('segoeuib.ttf' if bold else 'segoeui.ttf'), size)
INK, DIM, WATER, PAPER = (40, 44, 50), (95, 100, 108), (60, 130, 170), (222, 225, 228)
meta = json.load(open(os.path.join(TMP, 'A_meta.json')))
TW, TH = meta['tile']
PPM = TW / meta['ortho_scale']


def paper(w, h):
    g = np.linspace(232, 212, h).reshape(h, 1, 1).repeat(w, 1).repeat(3, 2).astype(np.uint8)
    g[:, :, 2] += 3
    return Image.fromarray(g)


def load(name, over_paper=False):
    im = Image.open(os.path.join(TMP, name))
    if over_paper:
        bg = paper(*im.size)
        bg.paste(im.convert('RGBA'), (0, 0), im.convert('RGBA'))
        return bg
    return im.convert('RGB')


def label(d, xy, text, size=30, bold=True, fill=INK):
    d.text(xy, text, font=F(size, bold), fill=fill)


def dim_h(d, x0, x1, y, text, up=True):
    """Горизонтальная размерная линия."""
    d.line([(x0, y), (x1, y)], fill=DIM, width=2)
    for x in (x0, x1):
        d.line([(x, y - 12), (x, y + 12)], fill=DIM, width=2)
    f = F(26)
    w = d.textlength(text, font=f)
    d.text(((x0 + x1) / 2 - w / 2, y - 36 if up else y + 6), text, font=f, fill=DIM)


def dim_v(d, x, y0, y1, text, left=True):
    d.line([(x, y0), (x, y1)], fill=DIM, width=2)
    for y in (y0, y1):
        d.line([(x - 12, y), (x + 12, y)], fill=DIM, width=2)
    f = F(26)
    w = d.textlength(text, font=f)
    d.text((x - w - 12 if left else x + 12, (y0 + y1) / 2 - 16), text, font=f, fill=DIM)


def ext_sheet():
    per = load('A_persp.png')
    side = load('A_side.png', True)
    front = load('A_front.png', True)
    top = load('A_top.png', True)
    # --- вид сбоку: нос слева, X кадра = Y модели
    d = ImageDraw.Draw(side)
    sx = lambda y: TW / 2 + y * PPM
    sz = lambda z: TH / 2 - (z - meta['side_center'][1]) * PPM
    d.line([(60, sz(0)), (TW - 60, sz(0))], fill=INK, width=3)
    d.line([(60, sz(0.45)), (TW - 60, sz(0.45))], fill=WATER, width=2)
    d.text((70, sz(0.45) - 34), 'вода 0,45 м', font=F(24), fill=WATER)
    d.text((70, sz(0) + 6), 'грунт', font=F(24), fill=INK)
    dim_h(d, sx(-7.0), sx(7.0), sz(0) + 70, 'длина 14,0 м', up=False)
    dim_v(d, sx(7.0) + 70, sz(4.5), sz(0), '4,5 м', left=False)
    dim_v(d, sx(0.75), sz(1.35), sz(0), 'днище 1,35 м', left=False)
    label(d, (40, 30), 'Вид сбоку')
    # --- вид спереди
    d = ImageDraw.Draw(front)
    fx = lambda x: TW / 2 + x * PPM
    d.line([(200, sz(0)), (TW - 200, sz(0))], fill=INK, width=3)
    d.line([(200, sz(0.45)), (TW - 200, sz(0.45))], fill=WATER, width=2)
    dim_h(d, fx(-5.0), fx(5.0), sz(4.5) - 60, 'размах 10,0 м', up=True)
    dim_h(d, fx(-2.22), fx(2.22), sz(0) + 70, 'колея опор 4,4 м', up=False)
    label(d, (40, 30), 'Вид спереди')
    # --- вид сверху
    d = ImageDraw.Draw(top)
    label(d, (40, 30), 'Вид сверху')
    d.text((40, TH - 60), 'нос — влево; мотогондолы в посадочном положении (соплом вниз)', font=F(24), fill=DIM)
    d = ImageDraw.Draw(per)
    label(d, (40, 30), 'Общий вид (трап опущен, вода 0,45 м)', fill=(245, 245, 245))
    head = 110
    sheet = Image.new('RGB', (2 * TW, 2 * TH + head), PAPER)
    d = ImageDraw.Draw(sheet)
    d.text((40, 22), '«Чайка» — посадочный модуль. Этап A: серая блок-модель (концепт формы, без деталировки и текстур)',
           font=F(44, True), fill=INK)
    for k, im in enumerate((per, side, front, top)):
        sheet.paste(im, ((k % 2) * TW, head + (k // 2) * TH))
    d.line([(TW, head), (TW, head + 2 * TH)], fill=(170, 174, 180), width=2)
    d.line([(0, head + TH), (2 * TW, head + TH)], fill=(170, 174, 180), width=2)
    sheet.save(os.path.join(OUT, 'A_chaika_ext_views.png'))
    print('saved A_chaika_ext_views.png', sheet.size)


def single(src, dst, text, light=True):
    p = os.path.join(TMP, src)
    if not os.path.exists(p):
        print('нет', src)
        return
    im = Image.open(p).convert('RGB')
    d = ImageDraw.Draw(im)
    f = F(30, True)
    w = d.textlength(text, font=f)
    d.rectangle([(20, im.height - 66), (48 + w, im.height - 18)], fill=(20, 22, 26))
    d.text((34, im.height - 62), text, font=f, fill=(235, 236, 238))
    im.save(os.path.join(OUT, dst))
    print('saved', dst)


def pano():
    p = os.path.join(TMP, PX + '_pano.png')
    if not os.path.exists(p):
        print('нет A_pano.png')
        return
    a = np.asarray(Image.open(p).convert('L')).astype(np.float32) / 255.0
    H, W = a.shape
    vis = a > 0.5
    rgb = np.zeros((H, W, 3), np.uint8)
    rgb[vis] = (176, 208, 228)
    rgb[~vis] = (46, 49, 54)
    im = Image.fromarray(rgb)
    d = ImageDraw.Draw(im)
    X = lambda az: W / 2 + az / 360.0 * W
    Y = lambda el: H / 2 - el / 180.0 * H
    for az in range(-180, 181, 30):
        d.line([(X(az), 0), (X(az), H)], fill=(120, 124, 130), width=1)
        d.text((X(az) + 4, Y(0) + 4), '%d°' % az, font=F(18), fill=(250, 250, 250))
    for el in range(-75, 90, 15):
        d.line([(0, Y(el)), (W, Y(el))], fill=(120, 124, 130), width=1)
        d.text((6, Y(el) - 22), '%+d°' % el, font=F(18), fill=(250, 250, 250))
    d.line([(0, Y(0)), (W, Y(0))], fill=(235, 235, 235), width=2)
    box = [(X(-100), Y(50)), (X(100), Y(-35))]
    d.rectangle(box, outline=(240, 140, 40), width=4)
    d.text((X(-100) + 8, Y(50) + 6), 'требование ТЗ: ±100° по горизонту, +50° вверх, −35° вниз', font=F(22, True),
           fill=(240, 140, 40))
    # числа
    row0 = vis[int(Y(0))]
    def run(cond, c):
        lo = c
        while lo > 0 and cond[lo - 1]:
            lo -= 1
        hi = c
        while hi < len(cond) - 1 and cond[hi + 1]:
            hi += 1
        return lo, hi
    def az_limits(el):
        r = vis[int(Y(el))]
        idx = np.where(r)[0]
        return ((idx.min() - W / 2) / W * 360, (idx.max() - W / 2) / W * 360) if len(idx) else (0, 0)
    def el_limits(az):
        col = vis[:, int(min(W - 1, X(az)))]
        idx = np.where(col)[0]
        return (90 - idx.min() / H * 180, 90 - idx.max() / H * 180) if len(idx) else (0, 0)
    bx0, bx1, by0, by1 = int(X(-100)), int(X(100)), int(Y(50)), int(Y(-35))
    frac = vis[by0:by1, bx0:bx1].mean()
    lines = ['Карта обзора из eye_pilot (равнопромежуточная проекция): светлое — видно наружу, тёмное — закрыто',
             'по горизонту (0°): от %.0f° до %+.0f°;  прямо вперёд: вверх до %+.0f°, вниз до %.0f° (за панелью приборов)'
             % (*az_limits(0), *el_limits(0)),
             'на азимуте ±40°: вверх %+.0f°, вниз %.0f°;  на ±90°: вверх %+.0f°, вниз %.0f°;  в рамке ТЗ открыто %.0f %% площади'
             % (*el_limits(40), *el_limits(90), frac * 100)]
    head = 34 * len(lines) + 20
    out = Image.new('RGB', (W, H + head), (20, 22, 26))
    out.paste(im, (0, head))
    d = ImageDraw.Draw(out)
    for i, t in enumerate(lines):
        d.text((14, 10 + 34 * i), t, font=F(22, i == 0), fill=(235, 236, 238))
    out.save(os.path.join(OUT, PX + '_eye_visibility_map.png'))
    print('saved A_eye_visibility_map.png;', lines[1], '|', lines[2])


def layout():
    ims = []
    for nm, t in (('A_plan.png', 'План кабины и шлюза (срез на высоте 3,05 м, нос слева)'),
                  ('A_section.png', 'Продольный разрез по оси (вид на левый борт)')):
        p = os.path.join(TMP, nm)
        if not os.path.exists(p):
            print('нет', nm)
            return
        im = Image.open(p).convert('RGB')
        ImageDraw.Draw(im).text((30, 22), t, font=F(30, True), fill=INK)
        ims.append(im)
    w, h = ims[0].size
    out = Image.new('RGB', (w, 2 * h), PAPER)
    out.paste(ims[0], (0, 0))
    out.paste(ims[1], (0, h))
    out.save(os.path.join(OUT, 'A_cockpit_layout.png'))
    print('saved A_cockpit_layout.png')


if __name__ == '__main__':
    what = sys.argv[1:] or ['ext', 'singles', 'pano', 'layout']
    if 'ext' in what:
        ext_sheet()
    if 'singles' in what:
        single(PX + '_rear.png', PX + '_chaika_rear_ramp.png', 'Сзади с высоты глаз 1,7 м: трап опущен, люк шлюза, вода 0,45 м')
        single(PX + '_eye_fwd.png', PX + '_eye_forward.png', 'eye_pilot — прямо вперёд, угол обзора 90°')
        single(PX + '_eye_up.png', PX + '_eye_up40.png', 'eye_pilot — вверх на 40°, угол обзора 90°')
        single(PX + '_eye_down.png', PX + '_eye_down25.png', 'eye_pilot — вниз на 25°, угол обзора 90°')
    if 'pano' in what:
        pano()
    if 'layout' in what:
        layout()
