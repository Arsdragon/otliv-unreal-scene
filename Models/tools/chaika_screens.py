# chaika_screens.py — заглушки изображений для экранов кабины (обычный Python + Pillow):
#   python tools/chaika_screens.py   ->  export/chaika_cockpit/T_Screen_1…6.png (1280 × 800, 16:10)
# Спокойный интерфейс без неона: тёмно-синий фон, тонкие светлые линии, янтарные акценты. В Unreal экраны —
# отдельные слоты материалов screen_1…screen_6, эти картинки нужны только для приёмочных рендеров и как образец.
import os, math
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXP = os.path.join(ROOT, 'export', 'chaika_cockpit')
os.makedirs(EXP, exist_ok=True)
W, H = 1280, 800
BG, GRID, FG, DIM, AMB, GRN = (9, 16, 24), (26, 44, 58), (188, 208, 214), (96, 124, 136), (222, 150, 54), (120, 190, 150)
F = lambda s, b=False: ImageFont.truetype(r'C:\Windows\Fonts\%s' % ('bahnschrift.ttf'), s)


def base(title):
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    for x in range(0, W, 80):
        d.line([(x, 70), (x, H - 40)], fill=GRID)
    for y in range(70, H - 40, 80):
        d.line([(0, y), (W, y)], fill=GRID)
    d.rectangle([0, 0, W, 56], fill=(14, 26, 36))
    d.text((24, 12), title, font=F(30), fill=FG)
    d.text((W - 250, 16), 'ЧАЙКА-07   12:41:07', font=F(22), fill=DIM)
    d.line([(0, 57), (W, 57)], fill=DIM, width=2)
    return im, d


def bar(d, x, y, w, h, v, label, val, col=FG):
    d.rectangle([x, y, x + w, y + h], outline=DIM, width=2)
    d.rectangle([x + 3, y + 3 + (h - 6) * (1 - v), x + w - 3, y + h - 3], fill=col)
    d.text((x - 4, y + h + 8), label, font=F(20), fill=DIM)
    d.text((x - 4, y - 30), val, font=F(22), fill=FG)


def systems():
    im, d = base('СИСТЕМЫ')
    rows = [('ЭЛЕКТРОПИТАНИЕ', 'ШИНА А 28,1 В', 'НОРМА'), ('ГИДРОСИСТЕМА', '20,6 МПа', 'НОРМА'), ('НАДДУВ КАБИНЫ', '101 кПа', 'НОРМА'),
            ('ТЕПЛОЗАЩИТА', 'ПЛИТКА 100 %', 'НОРМА'), ('ШАССИ', 'ВЫПУЩЕНО', 'ЗАМКИ'), ('ШЛЮЗ', 'ЗАКРЫТ', 'ГЕРМЕТИЧЕН'), ('ДРОН «СВЕТЛЯК»', 'В ЛОЖЕМЕНТЕ', 'ЗАРЯД 98 %')]
    for i, (a, b, c) in enumerate(rows):
        y = 96 + i * 92
        d.rectangle([40, y, W - 40, y + 72], outline=DIM, width=2)
        d.text((64, y + 20), a, font=F(30), fill=FG)
        d.text((560, y + 20), b, font=F(30), fill=FG)
        d.text((980, y + 20), c, font=F(30), fill=GRN)
    return im


def nav():
    im, d = base('НАВИГАЦИЯ')
    cx, cy = 470, 430
    for r in (110, 220, 320):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=DIM, width=2)
    for a in range(0, 360, 30):
        x, y = math.sin(math.radians(a)), -math.cos(math.radians(a))
        d.line([(cx + x * 300, cy + y * 300), (cx + x * 320, cy + y * 320)], fill=FG, width=3)
    d.polygon([(cx, cy - 26), (cx - 16, cy + 18), (cx + 16, cy + 18)], outline=FG, width=3)
    tx, ty = cx + 150, cy - 180
    d.line([(cx, cy), (tx, ty)], fill=AMB, width=3)
    d.ellipse([tx - 12, ty - 12, tx + 12, ty + 12], outline=AMB, width=4)
    d.text((tx + 22, ty - 16), 'МАЯК ЗОНДА', font=F(24), fill=AMB)
    for i, (a, b) in enumerate((('ДАЛЬНОСТЬ', '0,20 км'), ('ПЕЛЕНГ', '050°'), ('ГЛУБИНА', '0,45 м'), ('СИЛА ТЯЖЕСТИ', '1,3 g'), ('ВЕТЕР', '2 м/с'))):
        y = 120 + i * 120
        d.text((880, y), a, font=F(24), fill=DIM)
        d.text((880, y + 34), b, font=F(44), fill=FG)
    return im


def flight():
    im, d = base('ПИЛОТАЖ')
    cx, cy = W // 2, 430
    d.rectangle([260, 120, W - 260, H - 70], outline=DIM, width=2)
    d.rectangle([262, cy, W - 262, H - 72], fill=(22, 36, 44))
    d.line([(262, cy), (W - 262, cy)], fill=FG, width=3)
    for k in (-20, -10, 10, 20):
        y = cy - k * 9
        d.line([(cx - 90, y), (cx + 90, y)], fill=DIM, width=2)
        d.text((cx + 100, y - 12), '%+d' % k, font=F(22), fill=DIM)
    d.line([(cx - 150, cy), (cx - 50, cy)], fill=AMB, width=6)
    d.line([(cx + 50, cy), (cx + 150, cy)], fill=AMB, width=6)
    d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=AMB)
    for x, t, v in ((60, 'СКОРОСТЬ', '0'), (W - 230, 'ВЫСОТА', '0')):
        d.rectangle([x, 300, x + 170, 420], outline=FG, width=3)
        d.text((x + 8, 262), t, font=F(24), fill=DIM)
        d.text((x + 20, 326), v, font=F(60), fill=FG)
    d.text((60, 460), 'м/с', font=F(24), fill=DIM)
    d.text((W - 230, 460), 'м', font=F(24), fill=DIM)
    d.text((cx - 150, H - 62), 'НА ГРУНТЕ   КУРС 090°', font=F(28), fill=GRN)
    return im


def engines():
    im, d = base('ДВИГАТЕЛИ')
    for i, (lab, v, val) in enumerate((('ЛЕВ', 0.12, '12 %'), ('ПРАВ', 0.12, '12 %'), ('КОРМ 1', 0.0, '0 %'), ('КОРМ 2', 0.0, '0 %'))):
        bar(d, 110 + i * 190, 150, 90, 440, v, lab, val, GRN if v else DIM)
    for i, (a, b) in enumerate((('РЕЖИМ', 'МАЛЫЙ ГАЗ'), ('ТОПЛИВО', '61 %'), ('ОКИСЛИТЕЛЬ', '58 %'), ('ЗАБОРНИКИ', 'ОТКРЫТЫ'), ('ПОВОРОТ ГОНДОЛ', '90°'))):
        y = 120 + i * 120
        d.text((900, y), a, font=F(24), fill=DIM)
        d.text((900, y + 34), b, font=F(40), fill=FG)
    return im


def comms():
    im, d = base('СВЯЗЬ')
    d.text((60, 110), 'ОРБИТАЛЬНЫЙ БЛОК', font=F(26), fill=DIM)
    pts = [(60 + i * 14, 300 + int(46 * math.sin(i * 0.31) * math.sin(i * 0.05))) for i in range(84)]
    d.line(pts, fill=GRN, width=3)
    d.text((60, 160), 'КАНАЛ 2   УРОВЕНЬ −71 дБ', font=F(34), fill=FG)
    d.text((60, 420), 'МАЯК ЗОНДА', font=F(26), fill=DIM)
    pts = [(60 + i * 14, 600 + (-60 if i % 21 == 3 else 0)) for i in range(84)]
    d.line(pts, fill=AMB, width=3)
    d.text((60, 470), 'ПЕРЕДАЁТ: «ВСЁ В ПОРЯДКЕ»', font=F(34), fill=AMB)
    return im


def airlock():
    im, d = base('ШЛЮЗ')
    for i, (a, b, c) in enumerate((('ДАВЛЕНИЕ В ШЛЮЗЕ', '101 кПа', FG), ('ДАВЛЕНИЕ СНАРУЖИ', '94 кПа', FG), ('ЛЮК', 'ЗАКРЫТ', GRN), ('ТРАП', 'УБРАН', GRN),
                                   ('СОСТАВ ВОЗДУХА', 'НЕПРИГОДЕН', AMB))):
        y = 100 + i * 130
        d.rectangle([40, y, W - 40, y + 104], outline=DIM, width=2)
        d.text((70, y + 30), a, font=F(38), fill=DIM)
        d.text((760, y + 26), b, font=F(46), fill=c)
    return im


for k, fn in enumerate((systems, nav, flight, engines, comms, airlock), 1):
    fn().save(os.path.join(EXP, 'T_Screen_%d.png' % k))
print('экраны сохранены: T_Screen_1…6.png')
