# -*- coding: utf-8 -*-
# cockpit_screens.py — наборы картинок для пяти экранов панели «Чайки» по состояниям сюжета сцены 1 «Отлив»
# (обычный Python + Pillow + numpy, Blender не нужен):
#   python tools/cockpit_screens.py  ->  export/cockpit_screens/<состояние>/T_Screen_1…5.png, manifest.json,
#                                        shots/F_screens_sheet.png (контрольный лист)
# Экраны: 1 СИСТЕМЫ, 2 НАВИГАЦИЯ, 3 ПИЛОТАЖ, 4 ДВИГАТЕЛИ, 5 СВЯЗЬ — 1280×800 (16:10), раскладка как у T_Screen_1…5
# кабины. Состояние landed — копия нынешних текстур кабины. Стиль: тёмно-синий фон, тонкие линии, светлый текст,
# янтарный — предупреждения, красный — только contact и failure, без свечения.
import os, math, json, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'export', 'chaika_cockpit')
OUT = os.path.join(ROOT, 'export', 'cockpit_screens')
W, H = 1280, 800
BG, GRID, FG, DIM, AMB, GRN = (9, 16, 24), (26, 44, 58), (188, 208, 214), (96, 124, 136), (222, 150, 54), (120, 190, 150)
RED, OFF, GROUND = (208, 72, 58), (44, 62, 74), (22, 36, 44)
COL = {'fg': FG, 'dim': DIM, 'ok': GRN, 'warn': AMB, 'bad': RED, 'off': OFF}
NAMES = {1: 'СИСТЕМЫ', 2: 'НАВИГАЦИЯ', 3: 'ПИЛОТАЖ', 4: 'ДВИГАТЕЛИ', 5: 'СВЯЗЬ'}
_fc = {}


def F(s):
    if s not in _fc:
        _fc[s] = ImageFont.truetype(r'C:\Windows\Fonts\bahnschrift.ttf', s)
    return _fc[s]


def tw(d, t, s):
    return d.textlength(t, font=F(s))


def fit(d, t, maxw, s, smin=24):
    while s > smin and tw(d, t, s) > maxw:
        s -= 2
    return s


def base(title, clock, tag=None):
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    for x in range(0, W, 80):
        d.line([(x, 70), (x, H - 40)], fill=GRID)
    for y in range(70, H - 40, 80):
        d.line([(0, y), (W, y)], fill=GRID)
    d.rectangle([0, 0, W, 56], fill=(14, 26, 36))
    d.text((24, 12), title, font=F(30), fill=FG)
    d.text((W - 250, 16), 'ЧАЙКА-07   ' + clock, font=F(22), fill=DIM)
    d.line([(0, 57), (W, 57)], fill=DIM, width=2)
    if tag:
        t, k = tag
        x0 = 24 + tw(d, title, 30) + 34
        x1 = x0 + tw(d, t, 26) + 28
        if k == 'bad':
            d.rectangle([x0, 8, x1, 48], fill=RED)
            d.text((x0 + 14, 13), t, font=F(26), fill=(240, 232, 226))
        else:
            d.rectangle([x0, 8, x1, 48], outline=COL[k], width=2)
            d.text((x0 + 14, 13), t, font=F(26), fill=COL[k])
    return im, d


def banner(d, box, text, k, size=40):
    """Плашка-сообщение: рамка цвета состояния и текст по центру (для красного — заливка)."""
    x0, y0, x1, y1 = box
    s = fit(d, text, x1 - x0 - 30, size, 26)
    if k == 'bad':
        d.rectangle(box, fill=RED)
        col = (240, 232, 226)
    else:
        d.rectangle(box, fill=BG, outline=COL[k], width=3)
        col = COL[k]
    d.text(((x0 + x1) / 2 - tw(d, text, s) / 2, (y0 + y1) / 2 - s * 0.58), text, font=F(s), fill=col)


def column(d, rows, x=880, y0=120, step=120, vs=44):
    for i, (a, b, k) in enumerate(rows):
        y = y0 + i * step
        if k == 'off':
            d.text((x, y), a, font=F(24), fill=OFF)
            d.text((x, y + 34), '— — —', font=F(vs), fill=OFF)
        else:
            d.text((x, y), a, font=F(24), fill=DIM)
            d.text((x, y + 34), b, font=F(fit(d, b, W - x - 16, vs, 30)), fill=COL[k])


# ------------------------------------------------------------------ 1. СИСТЕМЫ
def systems(rows, clock, tag=None):
    im, d = base(NAMES[1], clock, tag)
    for i, (a, b, c, k) in enumerate(rows):
        y = 96 + i * 92
        if k == 'off':
            d.rectangle([40, y, W - 40, y + 72], outline=OFF, width=2)
            d.text((64, y + 20), a, font=F(30), fill=OFF)
            d.text((560, y + 20), '— — —', font=F(30), fill=OFF)
            d.text((980, y + 20), 'НЕТ ДАННЫХ', font=F(30), fill=OFF)
            continue
        d.rectangle([40, y, W - 40, y + 72], outline=COL[k] if k in ('warn', 'bad') else DIM, width=3 if k in ('warn', 'bad') else 2)
        d.text((64, y + 20), a, font=F(fit(d, a, 470, 30)), fill=FG)
        d.text((560, y + 20), b, font=F(fit(d, b, 400, 30)), fill=COL[k] if k in ('warn', 'bad') else FG)
        d.text((980, y + 20), c, font=F(fit(d, c, 244, 30)), fill=COL[k])
    return im


# ------------------------------------------------------------------ 2. НАВИГАЦИЯ
def nav(kind, rows, clock, tag=None, beacon=None, front=None, scale=None, msg=None, dim=False):
    im, d = base(NAMES[2], clock, tag)
    low = msg is not None
    cx, cy = 470, (404 if low else 430)
    rr = (98, 196, 286) if low else (110, 220, 320)
    R = rr[2]
    ring = OFF if dim else DIM
    if kind == 'orbit':                                    # схема: планета, орбита, корабль и сигнал зонда на поверхности
        pr, orr = 190, 276
        d.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], outline=FG, width=3)
        for k in (0.35, 0.7):
            d.arc([cx - pr, cy - pr * k, cx + pr, cy + pr * k], 0, 180, fill=DIM, width=2)
            d.arc([cx - pr * k, cy - pr, cx + pr * k, cy + pr], 270, 90, fill=DIM, width=2)
        for a in range(0, 360, 8):
            d.arc([cx - orr, cy - orr, cx + orr, cy + orr], a, a + 4, fill=DIM, width=2)
        sa, ba = math.radians(-52), math.radians(18)
        sx, sy = cx + orr * math.cos(sa), cy + orr * math.sin(sa)
        bx, by = cx + pr * 0.86 * math.cos(ba), cy + pr * 0.86 * math.sin(ba)
        d.line([(sx, sy), (bx, by)], fill=AMB, width=3)
        d.polygon([(sx, sy - 22), (sx - 15, sy + 15), (sx + 15, sy + 15)], fill=BG, outline=FG, width=3)
        d.ellipse([bx - 11, by - 11, bx + 11, by + 11], outline=AMB, width=4)
        d.text((bx - 150, by + 20), 'СИГНАЛ ЗОНДА', font=F(24), fill=AMB)
        d.text((sx + 24, sy - 34), 'ЧАЙКА-07', font=F(24), fill=FG)
        d.text((cx - 60, cy + orr + 14), 'ВИТОК 3', font=F(24), fill=DIM)
    elif kind == 'profile':                                # профиль снижения: высота по дальности до точки посадки
        x0, y0, x1, y1 = 90, 130, 800, 690
        d.line([(x0, y0), (x0, y1), (x1, y1)], fill=DIM, width=2)
        d.text((x0 + 12, y0 - 6), 'ВЫСОТА, км', font=F(24), fill=DIM)
        d.text((x1 - 190, y1 + 12), 'ДАЛЬНОСТЬ, км', font=F(24), fill=DIM)
        for k, t in enumerate(('200', '150', '100', '50')):
            yy = y0 + 40 + k * 130
            d.line([(x0 - 8, yy), (x0, yy)], fill=DIM, width=2)
            d.text((x0 - 62, yy - 13), t, font=F(24), fill=DIM)
        pts = [(x0 + 30 + (x1 - x0 - 60) * t, y0 + 40 + (y1 - y0 - 44) * (1 - (1 - t) ** 2.2)) for t in (i / 60 for i in range(61))]
        k = 26
        d.line(pts[:k + 1], fill=FG, width=3)
        for i in range(k, 60, 2):
            d.line([pts[i], pts[i + 1]], fill=DIM, width=3)
        sx, sy = pts[k]
        d.polygon([(sx + 20, sy + 12), (sx - 16, sy - 14), (sx - 14, sy + 16)], fill=BG, outline=AMB, width=3)
        d.text((sx + 30, sy - 40), 'ЧАЙКА-07', font=F(24), fill=FG)
        ex, ey = pts[-1]
        d.ellipse([ex - 11, ey - 11, ex + 11, ey + 11], outline=AMB, width=4)
        d.text((ex - 150, ey - 50), 'СИГНАЛ ЗОНДА', font=F(24), fill=AMB)
    else:                                                  # круговой обзор, нос вверх
        for r in rr:
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ring, width=2)
        for a in range(0, 360, 30):
            x, y = math.sin(math.radians(a)), -math.cos(math.radians(a))
            d.line([(cx + x * (R - 20), cy + y * (R - 20)), (cx + x * R, cy + y * R)], fill=ring if dim else FG, width=3)
        if front:                                          # фронт волны идёт с носа: линия поперёк круга и штриховка за ней
            fr, k = front
            yf = cy - fr * R
            hw = math.sqrt(max(1.0, R * R - (fr * R) ** 2))
            for x in range(int(cx - hw) + 6, int(cx + hw) - 6, 22):
                top = cy - math.sqrt(max(0.0, R * R - (x - cx) ** 2))
                if yf - 4 > top:
                    d.line([(x, yf - 4), (x + 10, max(top, yf - 44))], fill=COL[k], width=2)
            d.line([(cx - hw, yf), (cx + hw, yf)], fill=COL[k], width=5)
            lab = 'ФРОНТ ВОЛНЫ'
            ly = yf + 12 if fr > 0.3 else yf + 40
            d.rectangle([cx + 40, ly - 2, cx + 46 + tw(d, lab, 24), ly + 30], fill=BG)
            d.text((cx + 44, ly), lab, font=F(24), fill=COL[k])
        d.polygon([(cx, cy - 26), (cx - 16, cy + 18), (cx + 16, cy + 18)], fill=BG, outline=OFF if dim else FG, width=3)
        if beacon:
            tx, ty = cx + beacon[0], cy + beacon[1]
            d.line([(cx, cy), (tx, ty)], fill=AMB, width=3)
            d.ellipse([tx - 12, ty - 12, tx + 12, ty + 12], outline=AMB, width=4)
            d.text((tx + 22 if beacon[0] < 200 else tx - 150, ty - 16 if beacon[0] < 200 else ty - 52), 'МАЯК ЗОНДА', font=F(24), fill=AMB)
        if scale:
            d.text((cx - R, cy + R - 26 if low else cy + R - 4), scale, font=F(24), fill=DIM)
    if msg:
        banner(d, [40, 708, 840, 772], msg[0], msg[1], 40)
    column(d, rows)
    return im


# ------------------------------------------------------------------ 3. ПИЛОТАЖ
def flight(pitch, roll, spd, alt, units, status, clock, tag=None, msg=None, big=None):
    im, d = base(NAMES[3], clock, tag)
    cx, cy = W // 2, 430
    box = [260, 120, W - 260, H - 70]
    if big:                                                # вместо авиагоризонта — крупный отсчёт
        cap, num, unit, k = big
        d.rectangle(box, fill=BG, outline=COL[k], width=5)
        d.text((cx - tw(d, cap, 64) / 2, 150), cap, font=F(64), fill=COL[k])
        wn = tw(d, num, 360)
        x0 = cx - (wn + 90) / 2
        d.text((x0, 240), num, font=F(360), fill=COL[k])
        d.text((x0 + wn + 22, 462), unit, font=F(120), fill=COL[k])
    else:
        att = im.copy()
        da = ImageDraw.Draw(att)
        r = math.radians(roll)
        ux, uy = math.cos(r), math.sin(r)                  # вдоль горизонта
        nx, ny = -uy, ux                                   # вниз от горизонта
        hx, hy = cx + nx * pitch * 9, cy + ny * pitch * 9
        da.polygon([(hx - ux * 2000, hy - uy * 2000), (hx + ux * 2000, hy + uy * 2000),
                    (hx + ux * 2000 + nx * 2000, hy + uy * 2000 + ny * 2000), (hx - ux * 2000 + nx * 2000, hy - uy * 2000 + ny * 2000)], fill=GROUND)
        da.line([(hx - ux * 2000, hy - uy * 2000), (hx + ux * 2000, hy + uy * 2000)], fill=FG, width=3)
        for k in (-20, -10, 10, 20):
            px, py = hx - nx * k * 9, hy - ny * k * 9
            da.line([(px - ux * 90, py - uy * 90), (px + ux * 90, py + uy * 90)], fill=DIM, width=2)
            if abs(roll) < 1:
                da.text((px + 100, py - 12), '%+d' % k, font=F(22), fill=DIM)
        m = Image.new('L', (W, H), 0)
        ImageDraw.Draw(m).rectangle([box[0] + 2, box[1] + 2, box[2] - 2, box[3] - 2], fill=255)
        im.paste(att, (0, 0), m)
        d.rectangle(box, outline=DIM, width=2)
        d.line([(cx - 150, cy), (cx - 50, cy)], fill=AMB, width=6)
        d.line([(cx + 50, cy), (cx + 150, cy)], fill=AMB, width=6)
        d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=AMB)
    for x, t, v, u in ((60, 'СКОРОСТЬ', spd, units[0]), (W - 230, 'ВЫСОТА', alt, units[1])):
        d.rectangle([x, 300, x + 170, 420], fill=BG, outline=FG, width=3)
        d.text((x + 8, 262), t, font=F(24), fill=DIM)
        s = fit(d, v, 150, 60, 36)
        d.text((x + 85 - tw(d, v, s) / 2, 360 - s * 0.6), v, font=F(s), fill=FG)
        d.text((x, 432), u, font=F(26), fill=DIM)
    if msg:
        banner(d, [260, 64, W - 260, 114], msg[0], msg[1], 34)
    s = fit(d, status[0], W - 80, 28, 24)
    d.text((cx - tw(d, status[0], s) / 2, H - 62), status[0], font=F(s), fill=COL[status[1]])
    return im


# ------------------------------------------------------------------ 4. ДВИГАТЕЛИ
def engines(bars, rows, clock, tag=None, msg=None):
    im, d = base(NAMES[4], clock, tag)
    hb = 380 if msg else 440
    for i, (lab, v, val, k) in enumerate(bars):
        x, y, w = 110 + i * 190, 150, 90
        c = COL[k]
        d.rectangle([x, y, x + w, y + hb], outline=OFF if k == 'off' else DIM, width=2)
        if v > 0:
            d.rectangle([x + 3, y + 3 + (hb - 6) * (1 - v), x + w - 3, y + hb - 3], fill=c)
        if k == 'bad':
            d.line([(x + 8, y + 8), (x + w - 8, y + hb - 8)], fill=RED, width=3)
            d.line([(x + w - 8, y + 8), (x + 8, y + hb - 8)], fill=RED, width=3)
        d.text((x - 4, y + hb + 8), lab, font=F(26), fill=OFF if k == 'off' else DIM)
        d.text((x - 4, y - 36), val, font=F(28), fill=c if k in ('warn', 'bad', 'off') else FG)
    if msg:
        banner(d, [60, 640, 840, 730], msg[0], msg[1], 46)
    column(d, rows, x=900, vs=40)
    return im


# ------------------------------------------------------------------ 5. СВЯЗЬ
def comms(ch1, ch2, clock, tag=None, foot=None):
    im, d = base(NAMES[5], clock, tag)
    rnd = np.random.default_rng(7)
    for (cap, text, k, wave), y0 in ((ch1, 110), (ch2, 420)):
        c = COL[k]
        d.text((60, y0), cap, font=F(26), fill=DIM)
        d.text((60, y0 + 50), text, font=F(fit(d, text, W - 120, 34, 26)), fill=c)
        ym = y0 + (190 if y0 < 300 else 180)
        if wave == 'sine':
            pts = [(60 + i * 14, ym + int(46 * math.sin(i * 0.31) * math.sin(i * 0.05))) for i in range(84)]
        elif wave == 'weak':
            pts = [(60 + i * 14, ym + int(10 * math.sin(i * 0.31) + rnd.normal(0, 9) * (1 if (i // 9) % 2 else 0.25))) for i in range(84)]
        elif wave == 'pulse':
            pts = [(60 + i * 14, ym + (-60 if i % 21 == 3 else 0)) for i in range(84)]
        else:
            pts = [(60 + i * 14, ym) for i in range(84)]
        d.line(pts, fill=OFF if wave == 'flat' else (GRN if k in ('fg', 'ok') else c), width=3)
    if foot:
        banner(d, [60, 690, W - 60, 760], foot[0], foot[1], 40)
    return im


def glitch(im, strength, seed, keep=()):
    """Помеха на экране: сдвинутые полосы строк, выпавшие строки, редкая «крупа». Без свечения — тона фона и линий."""
    a = np.asarray(im).astype(np.int16).copy()
    r = np.random.default_rng(seed)
    free = lambda y, h: all(y + h < a or y > b for a, b in keep)      # keep — полосы строк, которые помеха не трогает (текст)
    for _ in range(int(4 + 22 * strength)):
        y = int(r.integers(60, H - 20))
        h = int(r.integers(3, 10 + int(60 * strength)))
        if not free(y, h):
            continue
        a[y:y + h] = np.roll(a[y:y + h], int(r.integers(-30, 30) * (1 + 6 * strength)), axis=1)
    for _ in range(int(3 + 30 * strength)):
        y = int(r.integers(60, H - 4))
        if not free(y, 4):
            continue
        a[y:y + int(r.integers(1, 4))] = (a[y:y + 1] * 0.25 + np.array(GRID) * 0.75).astype(np.int16)
    if strength > 0.5:
        y0, y1 = int(r.integers(120, 300)), int(r.integers(420, 700))
        blk = a[y0:y1]
        blk[:] = (blk * 0.35 + np.array(BG) * 0.65).astype(np.int16)
        spk = r.random((y1 - y0, W)) > 0.93
        blk[spk] = np.array(DIM, np.int16) + r.integers(-20, 20, (int(spk.sum()), 3))
    n = r.random((H, W)) > (0.995 - 0.01 * strength)
    a[n] = np.array(DIM, np.int16)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


# ------------------------------------------------------------------ состояния
SYS_OK = [('ЭЛЕКТРОПИТАНИЕ', 'ШИНА А 28,1 В', 'НОРМА', 'ok'), ('ГИДРОСИСТЕМА', '20,6 МПа', 'НОРМА', 'ok'), ('НАДДУВ КАБИНЫ', '101 кПа', 'НОРМА', 'ok')]
LOCK = ('ШЛЮЗ', 'ЗАКРЫТ', 'ГЕРМЕТИЧЕН', 'ok')
DRONE = ('ДРОН «СВЕТЛЯК»', 'В ЛОЖЕМЕНТЕ', 'ЗАРЯД 100 %', 'ok')
BEACON = ('МАЯК ЗОНДА', 'ПЕРЕДАЁТ: «ВСЁ В ПОРЯДКЕ»', 'warn', 'pulse')
E0 = [('ЛЕВ', 0.0, '0 %', 'dim'), ('ПРАВ', 0.0, '0 %', 'dim'), ('КОРМ 1', 0.0, '0 %', 'dim'), ('КОРМ 2', 0.0, '0 %', 'dim')]


def orbit():
    c = '12:38:45'
    return [systems(SYS_OK + [('ТЕПЛОЗАЩИТА', 'ПЛИТКА 100 %', 'НОРМА', 'ok'), ('ШАССИ', 'УБРАНО', 'ЗАМКИ', 'ok'), LOCK, DRONE], c),
            nav('orbit', [('ВЫСОТА ОРБИТЫ', '212 км', 'fg'), ('СКОРОСТЬ', '7,31 км/с', 'fg'), ('ПЕЛЕНГ НА СИГНАЛ', '050°', 'fg'),
                          ('ДАЛЬНОСТЬ', '1 840 км', 'fg'), ('ДО СХОДА С ОРБИТЫ', '00:25', 'fg')], c),
            flight(0, 0, '7 310', '212', ('м/с', 'км'), ('ОРБИТА   КУРС 090°', 'ok'), c),
            engines(E0, [('РЕЖИМ', 'ОЖИДАНИЕ', 'fg'), ('ТОПЛИВО', '78 %', 'fg'), ('ОКИСЛИТЕЛЬ', '75 %', 'fg'), ('ЗАБОРНИКИ', 'ЗАКРЫТЫ', 'fg'),
                         ('ПОВОРОТ ГОНДОЛ', '0°', 'fg')], c),
            comms(('ОРБИТАЛЬНЫЙ БЛОК', 'КАНАЛ 2   УРОВЕНЬ –48 дБ', 'fg', 'sine'), ('МАЯК ЗОНДА', 'СИГНАЛ ЗОНДА: ВСЁ В ПОРЯДКЕ', 'warn', 'pulse'), c)]


def entry():
    c, tag = '12:39:25', ('ВХОД В АТМОСФЕРУ', 'warn')
    return [systems(SYS_OK + [('ТЕПЛОЗАЩИТА', 'ОБШИВКА 1 480 °C', 'НАГРЕВ', 'warn'), ('ПЕРЕГРУЗКА', '3,4 g', 'РАСТЁТ', 'warn'),
                              ('ШАССИ', 'УБРАНО', 'ЗАМКИ', 'ok'), LOCK], c, tag),
            nav('profile', [('ВЫСОТА', '64 км', 'warn'), ('СНИЖЕНИЕ', '–310 м/с', 'warn'), ('ДАЛЬНОСТЬ', '420 км', 'fg'),
                            ('ПЕЛЕНГ НА СИГНАЛ', '050°', 'fg'), ('ТЕМП. ОБШИВКИ', '1 480 °C', 'warn')], c, tag),
            flight(16, 0, '5 240', '64', ('м/с', 'км'), ('ВЫСОТА БЫСТРО ПАДАЕТ   –310 м/с', 'warn'), c, tag, msg=('ПЕРЕГРУЗКА 3,4 g', 'warn')),
            engines(E0, [('РЕЖИМ', 'ВЫКЛЮЧЕНЫ', 'fg'), ('ТОПЛИВО', '78 %', 'fg'), ('ОКИСЛИТЕЛЬ', '75 %', 'fg'), ('ЗАБОРНИКИ', 'ЗАКРЫТЫ', 'fg'),
                         ('ТЕМП. ГОНДОЛ', '920 °C', 'warn')], c, tag),
            comms(('ОРБИТАЛЬНЫЙ БЛОК', 'ПЛАЗМА: СВЯЗЬ ПРЕРЫВАЕТСЯ', 'warn', 'weak'), ('МАЯК ЗОНДА', 'СИГНАЛ ЗОНДА: ВСЁ В ПОРЯДКЕ', 'warn', 'pulse'), c, tag)]


def approach():
    c = '12:39:52'
    return [systems(SYS_OK + [('ТЕПЛОЗАЩИТА', 'ОБШИВКА 310 °C', 'ОСТЫВАЕТ', 'ok'), ('ШАССИ', 'ВЫПУЩЕНО', 'ЗАМКИ', 'ok'), LOCK, DRONE], c),
            nav('radar', [('ВЫСОТА', '38 м', 'fg'), ('ДАЛЬНОСТЬ', '0,35 км', 'fg'), ('ПЕЛЕНГ', '050°', 'fg'), ('ГЛУБИНА', '0,40 м', 'fg'),
                          ('СИЛА ТЯЖЕСТИ', '1,3 g', 'fg')], c, beacon=(236, -198), scale='КОЛЬЦО — 0,1 км'),
            flight(4, 0, '12', '38', ('м/с', 'м'), ('ЗАХОД   ШАССИ ВЫПУЩЕНО   ГЛУБИНА 0,40 м', 'ok'), c),
            engines([('ЛЕВ', 0.64, '64 %', 'ok'), ('ПРАВ', 0.64, '64 %', 'ok'), ('КОРМ 1', 0.22, '22 %', 'ok'), ('КОРМ 2', 0.22, '22 %', 'ok')],
                    [('РЕЖИМ', 'ПОСАДКА', 'fg'), ('ТОПЛИВО', '63 %', 'fg'), ('ОКИСЛИТЕЛЬ', '60 %', 'fg'), ('ЗАБОРНИКИ', 'ОТКРЫТЫ', 'fg'),
                     ('ПОВОРОТ ГОНДОЛ', '90°', 'fg')], c),
            comms(('ОРБИТАЛЬНЫЙ БЛОК', 'КАНАЛ 2   УРОВЕНЬ –66 дБ', 'fg', 'sine'), BEACON, c)]


def alert():
    c, tag = '12:45:15', ('ШТОРМОВОЕ ПРЕДУПРЕЖДЕНИЕ', 'warn')
    return [systems(SYS_OK + [('ВОЗДУХОЗАБОРНИКИ', 'ПРОДУВКА 40 с', 'ЖДИТЕ', 'warn'), ('ДВИГАТЕЛИ', 'ЗАПУСК', 'НЕ ГОТОВЫ', 'warn'),
                              ('ШАССИ', 'ВЫПУЩЕНО', 'ЗАМКИ', 'ok'), LOCK], c, tag),
            nav('radar', [('УРОВЕНЬ ВОДЫ', '0,05 м', 'warn'), ('ДО ФРОНТА', '6,0 км', 'warn'), ('СБЛИЖЕНИЕ', '150 м/с', 'warn'),
                          ('ВЫСОТА ВОЛНЫ', '2 100 м', 'warn'), ('ВЕТЕР', '31 м/с', 'fg')], c, tag, front=(0.60, 'warn'), scale='КОЛЬЦО — 3,3 км',
                msg=('УРОВЕНЬ ВОДЫ ПАДАЕТ', 'warn')),
            flight(0, 0, '0', '0', ('м/с', 'м'), ('НА ГРУНТЕ   ВЗЛЁТ НЕ ГОТОВ', 'warn'), c, tag, msg=('УРОВЕНЬ ВОДЫ ПАДАЕТ', 'warn')),
            engines([('ЛЕВ', 0.05, 'ЗАПУСК', 'warn'), ('ПРАВ', 0.05, 'ЗАПУСК', 'warn'), ('КОРМ 1', 0.0, '0 %', 'dim'), ('КОРМ 2', 0.0, '0 %', 'dim')],
                    [('РЕЖИМ', 'ЗАПУСК', 'warn'), ('ЗАБОРНИКИ', 'ПРОДУВКА', 'warn'), ('ДО КОНЦА ПРОДУВКИ', '40 с', 'warn'), ('ТОПЛИВО', '61 %', 'fg'),
                     ('ПОВОРОТ ГОНДОЛ', '90°', 'fg')], c, tag, msg=('ПРОДУВКА ВОЗДУХОЗАБОРНИКОВ 40 с', 'warn')),
            comms(('ОРБИТАЛЬНЫЙ БЛОК', 'ПРЕДУПРЕЖДЕНИЕ: ВОЛНА 2 100 м, 150 м/с', 'warn', 'sine'), BEACON, c, tag)]


def contact(n):
    c, tag = {25: '12:45:35', 15: '12:45:45', 5: '12:45:55'}[n], ('ТРЕВОГА', 'bad')
    dist = ('%.2f км' % (0.15 * n)).replace('.', ',')
    return [systems(SYS_OK + [('ВОЗДУХОЗАБОРНИКИ', 'ПРОДУВКА %d с' % n, 'ЖДИТЕ', 'warn'), ('ДВИГАТЕЛИ', 'ЗАПУСК', 'ТЯГИ НЕТ', 'bad'), LOCK,
                              ('ПРИВЯЗНЫЕ РЕМНИ', 'ЗАТЯНУТЬ', 'УДАР', 'bad')], c, tag),
            nav('radar', [('ДО ФРОНТА', dist, 'bad'), ('СБЛИЖЕНИЕ', '150 м/с', 'bad'), ('ВЫСОТА ВОЛНЫ', '2 100 м', 'bad'),
                          ('УРОВЕНЬ ВОДЫ', '0,00 м', 'warn'), ('ВЕТЕР', '46 м/с', 'warn')], c, tag, front=(0.15 * n / 5.0, 'bad'),
                scale='КОЛЬЦО — 1,7 км', msg=('ДО КОНТАКТА %d с' % n, 'bad')),
            flight(0, 0, '0', '0', ('м/с', 'м'), ('ПРИГОТОВИТЬСЯ К УДАРУ', 'bad'), c, tag, big=('ДО КОНТАКТА', '%d' % n, 'с', 'bad')),
            engines([('ЛЕВ', 0.08, 'ЗАПУСК', 'warn'), ('ПРАВ', 0.08, 'ЗАПУСК', 'warn'), ('КОРМ 1', 0.0, '0 %', 'dim'), ('КОРМ 2', 0.0, '0 %', 'dim')],
                    [('РЕЖИМ', 'ЗАПУСК', 'warn'), ('ДО КОНЦА ПРОДУВКИ', '%d с' % n, 'bad'), ('ТЯГА', 'НЕТ', 'bad'), ('ТОПЛИВО', '61 %', 'fg'),
                     ('ПОВОРОТ ГОНДОЛ', '90°', 'fg')], c, tag, msg=('ВЗЛЁТ НЕВОЗМОЖЕН', 'bad')),
            comms(('ОРБИТАЛЬНЫЙ БЛОК', 'ВОЛНА: ДО КОНТАКТА %d с' % n, 'bad', 'weak'), BEACON, c, tag)]


def failure():
    c, tag = '12:46:45', ('АВАРИЯ', 'bad')
    s5 = comms(('ОРБИТАЛЬНЫЙ БЛОК', 'НЕТ СВЯЗИ', 'warn', 'flat'), ('МАЯК ЗОНДА', 'НЕТ СИГНАЛА', 'dim', 'flat'), c, tag, foot=('КОРПУС ЦЕЛ   НА ПЛАВУ', 'ok'))
    return [systems([('ЭЛЕКТРОПИТАНИЕ', 'ШИНА Б 24,3 В', 'РЕЗЕРВ', 'warn'), ('ГИДРОСИСТЕМА', '', '', 'off'), ('НАДДУВ КАБИНЫ', '99 кПа', 'НОРМА', 'ok'),
                     ('КОРПУС', 'ЦЕЛ', 'ГЕРМЕТИЧЕН', 'ok'), ('ДВИГАТЕЛИ', 'ОТКАЗ', 'ЗАЛИТЫ', 'bad'), ('ШАССИ', '', '', 'off'),
                     ('ПОЛОЖЕНИЕ', 'НА ПЛАВУ', 'КРЕН 11°', 'ok')], c, tag),
            nav('radar', [('ПОЛОЖЕНИЕ', 'НА ПЛАВУ', 'ok'), ('ДРЕЙФ', '14 м/с', 'fg'), ('ГЛУБИНА', '', 'off'), ('МАЯК ЗОНДА', 'НЕТ СИГНАЛА', 'warn'),
                          ('ВЕТЕР', '', 'off')], c, tag, dim=True),
            flight(-3, 11, '14', '0', ('м/с', 'м'), ('НА ПЛАВУ   КОРПУС ЦЕЛ', 'ok'), c, tag),
            engines([('ЛЕВ', 0.0, 'ОТКАЗ', 'bad'), ('ПРАВ', 0.0, 'ОТКАЗ', 'bad'), ('КОРМ 1', 0.0, 'ОТКАЗ', 'bad'), ('КОРМ 2', 0.0, '— —', 'off')],
                    [('РЕЖИМ', 'ОТКАЗ', 'bad'), ('ЗАБОРНИКИ', 'ЗАЛИТЫ', 'bad'), ('ТОПЛИВО', '58 %', 'fg'), ('ОКИСЛИТЕЛЬ', '', 'off'),
                     ('ПОВОРОТ ГОНДОЛ', '', 'off')], c, tag, msg=('ДВИГАТЕЛИ — ОТКАЗ', 'bad')),
            glitch(s5, 0.12, 3, keep=((100, 205), (410, 515), (680, 770)))], glitch(s5, 1.0, 9)


STATES = [  # папка, состояние, с, по (секунды сцены), пояснение
    ('orbit', 'orbit', 0, 50, 'орбита: высота, скорость, пеленг на сигнал зонда'),
    ('entry', 'entry', 50, 85, 'вход в атмосферу: перегрузка, нагрев обшивки, высота быстро падает'),
    ('approach', 'approach', 85, 100, 'заход: высота в метрах, глубина 0,40 м, шасси выпущено'),
    ('landed', 'landed', 100, 400, 'на грунте: копия нынешних T_Screen_1…4 кабины; экран 5 пересобран с исправленным знаком «минус»'),
    ('alert', 'alert', 400, 435, 'шторм: уровень воды падает, фронт волны, продувка воздухозаборников 40 с'),
    ('contact_25', 'contact', 435, 445, 'до контакта 25 с'),
    ('contact_15', 'contact', 445, 455, 'до контакта 15 с'),
    ('contact_05', 'contact', 455, 460, 'до контакта 5 с'),
    ('failure', 'failure', 500, None, 'после волны: двигатели — отказ, корпус цел, на плаву; экран 5 мигает помехой'),
]


def mmss(s):
    return '%d:%02d' % (s // 60, s % 60)


if __name__ == '__main__':
    sets, extra = {}, None
    for folder, fn in (('orbit', orbit), ('entry', entry), ('approach', approach), ('alert', alert)):
        sets[folder] = fn()
    for n in (25, 15, 5):
        sets['contact_%02d' % n] = contact(n)
    sets['failure'], extra = failure()
    sets['landed'] = [Image.open(os.path.join(SRC, 'T_Screen_%d.png' % k)).convert('RGB') for k in range(1, 6)]
    # экран связи на грунте пересобран: в исходной текстуре кабины знак «минус» вышел пустым квадратом (нет в шрифте)
    sets['landed'][4] = comms(('ОРБИТАЛЬНЫЙ БЛОК', 'КАНАЛ 2   УРОВЕНЬ –71 дБ', 'fg', 'sine'), BEACON, '12:41:07')
    man_states = []
    for folder, state, t0, t1, note in STATES:
        d = os.path.join(OUT, folder)
        os.makedirs(d, exist_ok=True)
        for k, im in enumerate(sets[folder], 1):
            p = os.path.join(d, 'T_Screen_%d.png' % k)
            if folder == 'landed' and k != 5:
                shutil.copyfile(os.path.join(SRC, 'T_Screen_%d.png' % k), p)
            else:
                im.save(p)
        e = dict(folder=folder, state=state, time='%s–%s' % (mmss(t0), mmss(t1) if t1 else 'конец'), from_s=t0, to_s=t1, note=note,
                 files=['%s/T_Screen_%d.png' % (folder, k) for k in range(1, 6)])
        if folder == 'failure':
            extra.save(os.path.join(d, 'T_Screen_5_b.png'))
            e['flicker'] = dict(slot='screen_5', frames=['failure/T_Screen_5.png', 'failure/T_Screen_5_b.png'],
                                hint='основной кадр — T_Screen_5.png; T_Screen_5_b.png показывать короткими вспышками 0,08–0,2 с через неровные промежутки 0,5–3 с')
        man_states.append(e)
    json.dump(dict(
        id='cockpit_screens', title='Экраны панели «Чайки» по состояниям сюжета (сцена 1 «Отлив»)',
        size=[W, H], aspect='16:10', colorspace='sRGB, без альфы; в материале — эмиссия слота (как у нынешних экранов)',
        slots={'screen_%d' % k: 'T_Screen_%d.png — %s' % (k, NAMES[k]) for k in range(1, 6)},
        states=man_states,
        notes=['screen_6 (ШЛЮЗ) в наборы не входит — остаётся прежним',
               'интервал 7:40–8:20 (удар, под водой) в задании не описан: файлов для него нет',
               'contact: три набора подряд — 25, 15 и 5 секунд до удара в 7:40; числа на всех пяти экранах согласованы (дальность до фронта 3,75 / 2,25 / 0,75 км, продувка 25 / 15 / 5 с)',
               'часы в шапке экранов: 12:38:20 + время сцены; в каждом состоянии показано одно застывшее значение',
               'красный цвет есть только в contact и failure; янтарный — предупреждения и метка маяка зонда (как на нынешних экранах)']),
        open(os.path.join(OUT, 'manifest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # ---- контрольный лист
    tw_, th_, lab = 372, 232, 214
    rows = [f for f, *_ in STATES]
    S = Image.new('RGB', (lab + 6 * (tw_ + 8) + 8, 44 + len(rows) * (th_ + 10) + 8), (30, 32, 36))
    ds = ImageDraw.Draw(S)
    for k in range(1, 6):
        ds.text((lab + (k - 1) * (tw_ + 8) + 8, 10), 'screen_%d — %s' % (k, NAMES[k]), font=F(22), fill=(210, 210, 210))
    ds.text((lab + 5 * (tw_ + 8) + 8, 10), 'кадр мигания', font=F(22), fill=(210, 210, 210))
    for r, (folder, state, t0, t1, note) in enumerate(STATES):
        y = 44 + r * (th_ + 10)
        ds.text((10, y + 70), folder, font=F(26), fill=(230, 230, 230))
        ds.text((10, y + 106), '%s–%s' % (mmss(t0), mmss(t1) if t1 else 'конец'), font=F(22), fill=(160, 160, 160))
        for k, im in enumerate(sets[folder]):
            S.paste(im.resize((tw_, th_), Image.LANCZOS), (lab + k * (tw_ + 8), y))
        if folder == 'failure':
            S.paste(extra.resize((tw_, th_), Image.LANCZOS), (lab + 5 * (tw_ + 8), y))
    S.save(os.path.join(ROOT, 'shots', 'F_screens_sheet.png'))
    print('состояний %d, файлов %d; лист shots/F_screens_sheet.png %s' % (len(STATES), len(STATES) * 5 + 1, S.size))
