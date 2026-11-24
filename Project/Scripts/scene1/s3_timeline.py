# S3: the whole film as one timeline (0:00 - 9:10). Everything is a function of time t (seconds):
#   apply_time(t)  - puts the scene, the ship, the drone, the lights and the first-person camera CAM_Film into the state of time t
#   render(f0, f1) - renders frames f0..f1 (24 fps) to PNG, one per editor tick, in the background
#   strip(times)   - quick stills for checking
# The same functions are baked into the master sequence by s3_sequence.py.
import unreal, math, os, time, builtins, importlib
import s1u, l_keys, q_shots, f_wave_mesh as fw
from s1u import EAS, LES, UES, R, world
ML = unreal.MathLibrary
FPS = 24.0
T_END = 550.0
OUT = r'C:\UnrealScenes\Renders\scene1\animatic_v1'

# ---------------------------------------------------------------- small maths
def lerp(a, b, k): return a + (b - a) * k
def sstep(k):
    k = max(0.0, min(1.0, k)); return k * k * (3 - 2 * k)
def n1(x, seed=0.0):
    i = math.floor(x); f = x - i
    def r(k): return (math.sin((k + seed * 17.13) * 127.1) * 43758.5453) % 1.0
    u = f * f * (3 - 2 * f)
    return (r(i) * (1 - u) + r(i + 1) * u) * 2 - 1


def cr(keys, t):
    """smooth (C1) interpolation of [(t, v1, v2, ...)]; plateaus stay flat"""
    n = len(keys)
    if t <= keys[0][0]: return list(keys[0][1:])
    if t >= keys[-1][0]: return list(keys[-1][1:])
    i = 0
    for j in range(n - 1):
        if keys[j][0] <= t: i = j
        else: break
    t0, t1 = keys[i][0], keys[i + 1][0]
    h = t1 - t0; u = (t - t0) / h; u2 = u * u; u3 = u2 * u
    out = []
    for c in range(1, len(keys[i])):
        p0, p1 = keys[i][c], keys[i + 1][c]
        def tan(j):
            if j <= 0 or j >= n - 1: return 0.0
            a, b, d = keys[j - 1][c], keys[j][c], keys[j + 1][c]
            if a == b or b == d: return 0.0
            return (d - a) / (keys[j + 1][0] - keys[j - 1][0])
        m0, m1 = tan(i), tan(i + 1)
        out.append((2 * u3 - 3 * u2 + 1) * p0 + (u3 - 2 * u2 + u) * h * m0 + (-2 * u3 + 3 * u2) * p1 + (u3 - u2) * h * m1)
    return out


def ease(keys, t):
    """ease-in/ease-out interpolation between keys (head turns, values)"""
    if t <= keys[0][0]: return list(keys[0][1:])
    if t >= keys[-1][0]: return list(keys[-1][1:])
    for j in range(len(keys) - 1):
        if keys[j][0] <= t <= keys[j + 1][0]:
            k = sstep((t - keys[j][0]) / (keys[j + 1][0] - keys[j][0]))
            return [lerp(a, b, k) for a, b in zip(keys[j][1:], keys[j + 1][1:])]


# ---------------------------------------------------------------- the wave
_PTS = fw.profile()
_H, _IC = fw.htop_fn(_PTS)
SC0 = fw.col_params(0.0)[0]
def wave_x_m(t): return 150.0 * (460.0 - t)
def surf(xl): return _H(xl) * SC0                     # height of the wave surface, xl = metres from the crest (negative = in front)

# ---------------------------------------------------------------- the ship (x, z in metres; pitch, yaw in degrees)
# orbit: 320 km above the landing site (so that "down" is the world -Z), nose down, the giant 25 deg to the right of the nose
SHIP_A = [(0, -200e3, 320e3, -25.0, 185.0), (38, 104e3, 320e3, -25.0, 185.0), (50, 200e3, 312e3, 6.0, 360.0),
          (58, 264e3, 250e3, 18.0, 360.0), (62, 296e3, 215e3, 18.0, 360.0)]
SHIP_B = [(62, -52e3, 26e3, 8.0, 360.0), (66, -40e3, 18e3, 6.0, 360.0), (74, -17e3, 4e3, -8.0, 360.0), (78, -9.5e3, 1.5e3, -6.0, 360.0),
          (81, -6e3, 350.0, -3.0, 360.0), (88, -2.6e3, 60.0, 0.0, 360.0), (95, -300.0, 15.0, 4.0, 360.0), (99, -12.0, 2.0, 5.0, 360.0),
          (100.5, 0.0, 0.0, 0.0, 360.0)]
T_LAND, T_LIFT, T_HIT, T_UP = 100.5, 450.5, 460.0, 500.0


def _ride(t):
    k = t - T_LIFT
    xs = -6.6 * k * k
    xl = xs - wave_x_m(t)
    return xs, xl


def ship_pose(t):
    """-> (x, y, z, pitch, yaw, roll): ship frame = X nose, Y right, Z up"""
    if t < 62.0:
        x, z, p, y = cr(SHIP_A, t); r = 2.0 * n1(t * 0.11, 3)
    elif t < T_LAND:
        x, z, p, y = cr(SHIP_B, t); z = max(z, 0.0)
        r = 3.0 * n1(t * 0.35, 4) * sstep((95.0 - t) / 20.0)
    elif t < T_LIFT:
        return (0.0, 0.0, 0.0, 0.0, 360.0, 0.0)
    elif t < T_HIT:
        xs, xl = _ride(t)
        z = max(0.0, surf(xl) - 1.3)
        slope = math.degrees(math.atan((surf(xl + 6.0) - surf(xl - 6.0)) / 12.0))
        k = sstep((t - T_LIFT) / 2.0)
        return (xs, 0.0, z, slope * 0.9 * k + 1.5 * n1(t * 1.3, 5) * k, 360.0 + 2.0 * n1(t * 0.7, 6) * k, 4.0 * n1(t * 0.9, 7) * k)
    elif t < T_UP:
        xs0, xl0 = _ride(T_HIT)
        z0 = max(0.0, surf(xl0) - 1.3)
        x = xs0 - 30.0 * (t - T_HIT)
        xl_up = (xs0 - 30.0 * (T_UP - T_HIT)) - wave_x_m(T_UP)
        z = lerp(z0, surf(xl_up) - 0.9, sstep((t - 470.0) / 30.0))
        tau = t - T_HIT; damp = 1.0 - 0.6 * sstep(tau / 40.0)
        slope0 = math.degrees(math.atan((surf(xl0 + 6.0) - surf(xl0 - 6.0)) / 12.0)) * 0.9
        p = slope0 * (1.0 - sstep(tau / 3.0)) + 13.0 * math.sin(0.31 * tau + 1.0) * damp
        r = -12.0 * math.sin(0.23 * tau + 0.4) * damp
        y = 360.0 + 160.0 * sstep(tau / 40.0)
        return (x, 0.0, z, p, y, r)
    else:
        xs0, xl0 = _ride(T_HIT)
        x = xs0 - 30.0 * (T_UP - T_HIT)
        xl = x - wave_x_m(t)
        z = surf(xl) - 0.9 + 0.25 * math.sin(t * 0.9)
        y = 520.0 - 140.0 * sstep((t - 510.0) / 22.0)
        return (x, 0.0, z, 2.0 * math.sin(t * 0.7), y, 2.5 * math.sin(t * 0.55 + 1.0))
    return (x, 0.0, z, p, y, r)


# ---------------------------------------------------------------- the pilot's head, in ship space (= world while the ship rests)
A_, D_ = (12.5, 9.4), (0.6277, 0.7785)                 # start of the walk to the probe, its direction
W_ = (124.6, 148.4); C_ = (20.0, 22.0)                 # at the wreck; corner of the run back
def _on(a, d, s): return (a[0] + d[0] * s, a[1] + d[1] * s)
_d2 = ((C_[0] - W_[0]) / 164.07, (C_[1] - W_[1]) / 164.07)
CAM_P = [(0, 4.60, 0.0, 2.90), (104, 4.60, 0.0, 2.90), (106, 4.2, 0.0, 3.22), (108, 3.2, 0.0, 3.32), (110, 2.0, 0.0, 3.34),
         (112, 0.3, 0.0, 3.34), (114, -1.6, 0.0, 3.30), (116, -2.6, 0.0, 3.00), (119, -4.9, 0.0, 1.80), (121, -6.5, 0.6, 1.70),
         (125, -5.0, 4.5, 1.70), (130, 2.0, 6.8, 1.70), (135, 9.5, 8.6, 1.70), (137.5, 12.5, 9.4, 1.70), (143, 12.5, 9.4, 1.70),
         (145,) + _on(A_, D_, 3.0) + (1.70,), (180,) + _on(A_, D_, 80.0) + (1.70,), (186,) + _on(A_, D_, 87.0) + (1.70,),
         (220,) + _on(A_, D_, 173.0) + (1.70,), (223, 123.5, 147.0, 1.70), (258, 123.5, 147.0, 1.70),
         (262, 125.6, 149.6, 1.55), (296, 125.6, 149.6, 1.55), (300, 124.6, 148.4, 1.70), (331, 124.6, 148.4, 1.70),
         (334,) + _on(W_, _d2, 8.0) + (1.70,), (367.5, 20.0, 22.0, 1.70), (373.5, -6.0, 11.0, 1.70), (376, -14.0, 9.0, 1.70),
         (383, -14.0, 9.0, 1.70), (386, -7.0, 1.5, 1.70), (388, -4.9, 0.0, 1.80), (390.5, -2.6, 0.0, 3.00), (391.5, -1.6, 0.0, 3.30),
         (393.5, 0.3, 0.0, 3.34), (395.5, 2.0, 0.0, 3.34), (397.5, 3.3, 0.0, 3.30), (400, 4.2, 0.0, 3.15), (402, 4.60, 0.0, 2.90),
         (T_END, 4.60, 0.0, 2.90)]
# (t, yaw, pitch, roll, focal mm); yaw is continuous (not wrapped)
CAM_L = [(0, 8, 22, 0, 11), (14, 2, 14, 0, 11), (26, 12, 24, 0, 11), (38, 6, 18, 0, 11), (50, 0, 4, 0, 11), (60, 0, 2, 0, 11),
         (66, 0, -4, 0, 11), (78, 0, -6, 0, 11), (88, 0, -2, 0, 11), (99, 0, -4, 0, 11), (104, 0, -6, 0, 12),
         (106, 110, -5, 0, 14), (108, 180, -4, 0, 16), (114, 180, -8, 0, 18), (119, 180, -14, 0, 18), (121, 160, -8, 0, 18),
         (125, 70, -6, 0, 18), (130, 20, -4, 0, 18), (135, 14, -3, 0, 18), (137.5, 30, -2, 0, 18), (139.5, 216, 10, 0, 14),
         (142.5, 216, 10, 0, 14), (145, 51, -4, 0, 18), (179, 51, -5, 0, 18), (181, 4, 2, 0, 30), (185.5, 2, 2.5, 0, 34),
         (188, 51, -4, 0, 18), (219, 51, -5, 0, 18), (223, 50, -9, 0, 20), (232, 50, -8, 0, 24), (258, 52, -8, 0, 24),
         (262, 51, -14, 0, 24), (296, 51, -14, 0, 24), (300, 80, -45, 0, 20), (304, 80, -45, 0, 20), (307, 200, -6, 0, 18),
         (310, 235, -4, 0, 18), (313, 362, 2, 0, 28), (316, 361, 2.5, 0, 50), (326, 361, 3.0, 0, 50), (330, 230, -3, 0, 18),
         (346, 230, -4, 0, 18), (348.5, 325, 2, 0, 18), (350, 325, 3, 0, 18), (352.5, 230, -4, 0, 18), (366, 232, -4, 0, 18),
         (370, 205, -3, 0, 18), (374, 195, -2, 0, 18), (378, 347, 2.5, 0, 16), (382.5, 347, 3.5, 0, 16), (384.5, 313, -4, 0, 18),
         (387, 350, -6, 0, 18), (388, 360, 4, 0, 18), (392, 360, 0, 0, 18), (396, 360, -2, 0, 18), (399, 360, -6, 0, 16),
         (402, 360, -4, 0, 11), (408, 360, -12, 0, 11), (414, 360, 2, 0, 11), (430, 360, 3, 0, 10.5), (446, 360, 4, 0, 10.5),
         (452, 360, 8, 0, 10.5), (459, 360, 14, 0, 10.5), (461, 360, 2, 0, 10.5), (480, 366, 1, 0, 10.5), (500, 360, 0, 0, 10.5),
         (506, 360, -1, 0, 12), (T_END, 360, 0, 0, 12)]


def cam_local(t):
    """head position and look in ship space, with steps, breathing and shake"""
    x, y, z = cr(CAM_P, t)
    yaw, pitch, roll, focal = ease(CAM_L, t)
    x1, y1, z1 = cr(CAM_P, t - 0.1)
    v = math.hypot(x - x1, y - y1) / 0.1
    outside = 119.0 < t < 390.0
    if outside and v > 0.25:
        run = sstep((v - 2.6) / 1.2)
        f = lerp(1.75, 2.9, run) * 0.5 * (0.6 + 0.4 * min(v, 2.2) / 2.2)
        amp = lerp(0.018, 0.040, run) * sstep(v / 1.0)
        ph = t * f * 2 * math.pi
        z += amp * abs(math.sin(ph)) - amp * 0.5
        side = 0.012 * math.sin(ph) * sstep(v / 1.0)
        hd = math.atan2(y - y1, x - x1)
        x += -math.sin(hd) * side; y += math.cos(hd) * side
        pitch += 0.35 * math.sin(2 * ph) * sstep(v / 1.0); roll += 0.5 * math.sin(ph) * sstep(v / 1.0)
    z += 0.004 * math.sin(t * 1.57); pitch += 0.15 * math.sin(t * 1.57 + 0.6)          # breathing
    shake = 0.0
    if 52.0 < t < 80.0: shake = 0.55 * sstep((t - 52.0) / 5.0) * (1.0 - sstep((t - 68.0) / 12.0))
    if 99.5 < t < 103.0: shake = max(shake, 0.9 * (1.0 - sstep((t - 100.5) / 2.5)) * sstep((t - 99.5) / 1.0))
    if T_LIFT < t < T_HIT + 6.0: shake = max(shake, lerp(0.15, 1.1, sstep((t - T_LIFT) / 9.5)) * (1.0 - sstep((t - T_HIT - 1.0) / 5.0)))
    if shake > 0.0:
        pitch += shake * n1(t * 9.0, 11); yaw += shake * 0.7 * n1(t * 7.3, 12); roll += shake * 0.8 * n1(t * 8.1, 13)
        z += 0.012 * shake * n1(t * 10.0, 14)
    return (x, y, z, yaw, pitch, roll, focal)


# ---------------------------------------------------------------- the drone (world; inside the cradle it follows the ship)
CRADLE = (-1.45, 1.08, 2.705)
PANEL = (128.29, 152.83, 0.837); PN = (-0.624, -0.743, 0.242)
HOVER = (PANEL[0] + PN[0] * 0.55, PANEL[1] + PN[1] * 0.55, 0.97)
def _lead(t, ahead, zz):
    x, y, _ = cr(CAM_P, t); x1, y1, _ = cr(CAM_P, t - 0.5)
    d = math.hypot(x - x1, y - y1)
    dx, dy = ((x - x1) / d, (y - y1) / d) if d > 0.05 else (D_[0], D_[1])
    return (x + dx * ahead - dy * 0.7, y + dy * ahead + dx * 0.7, zz + 0.07 * math.sin(t * 0.9))
DR_P = [(106, -7.8, 1.6, 1.5), (121, -7.8, 1.6, 1.5), (124, -5.5, 6.5, 1.3), (129, 4.0, 8.6, 1.2), (134, 10.5, 7.5, 1.05),
        (137, 10.87, 5.75, 0.97), (143, 10.87, 5.75, 0.97), (147,) + _lead(147, 5.0, 1.2)]
for _t in range(152, 222, 5): DR_P.append((_t,) + _lead(_t, 5.0, 1.2))
DR_P += [(222,) + _lead(222, 3.0, 1.15), (230,) + HOVER, (296,) + HOVER, (300, 126.9, 151.0, 1.5), (331, 126.9, 151.0, 1.5)]
for _t in range(336, 371, 4): DR_P.append((_t,) + _lead(_t, 7.0, 1.6))
DR_P += [(376, -8.2, 2.6, 1.75), (383, -8.2, 2.6, 1.75), (388, -5.0, 0.4, 2.4), (391, -2.2, 0.0, 2.9), (394, 0.0, 0.8, 2.8), (397,) + CRADLE]
DR_Y = [(106, 0), (121, 0), (124, 60), (129, 15), (134, -30), (137, 215), (143, 215), (146, 51), (222, 51), (230, 50), (296, 50),
        (300, 230), (331, 230), (366, 230), (372, 200), (383, 200), (388, 0), (397, 0)]
DR_ARM = [(232, 0.0), (236, 1.0), (290, 1.0), (296, 0.0)]


# ---------------------------------------------------------------- values by time
EXPO = [(0, -1.2), (60, -1.2), (66, 0.0), (98, 0.0), (104, 0.4), (118, 1.0), (390, 1.0), (402, 0.0), (440, -1.0), (459, -1.0), (460.5, -1.5), (499, -1.5), (504, 0.5), (T_END, 0.5)]
PLASMA = [(52, 0.0), (58, 0.8), (63.5, 0.8), (68, 0.0)]
NACELLE = [(86, 0.0), (96, -90.0)]
RAMP = [(106, 32.98), (112, -24.78), (393, -24.78), (398, 32.98)]
HATCH = [(107, 0.0), (111, -100.0), (394, -100.0), (397, 0.0)]
DOOR = [(105, 0.0), (108, -100.0), (398, -100.0), (401, 0.0)]
RIPPLE = [(280, 1.0), (400, 4.0)]
LINES = [(20, 'Орбита стабильна. Сигнал зонда — прямо под нами. Он передаёт: «всё в порядке».'), (50, 'Вхожу в атмосферу.'),
         (85, 'Глубина — сорок сантиметров. Везде. До самого горизонта.'), (100, 'Касание. Двигатели — на холостой.'),
         (120, 'Гравитация — одна и три. Источник сигнала — двести метров. Светляк тебя проводит.'),
         (180, 'На горизонте горный хребет. Странно: на орбитальной съёмке суши нет.'), (230, 'Это он. Точнее, то, что от него осталось.'),
         (260, 'Светляк извлекает накопитель. Минута.'), (290, 'Уровень воды падает. Тридцать сантиметров. Двадцать.'),
         (315, 'Хребет сместился. Повторяю замер. Высота — две тысячи сто сорок. Дистанция — двадцать два километра. Сближение — сто пятьдесят метров в секунду.'),
         (330, 'Это не хребет. Это вода. Возвращайся.'), (410, 'Запускаю двигатели. Воздухозаборники залиты, продувка — сорок секунд.'),
         (435, 'Двадцать пять секунд до контакта.'), (455, 'Держись.'), (510, 'Корпус цел. Двигатели — отказ. Мы на плаву.'), (530, 'Фиксирую вторую.')]


def rings(t):
    """rings on the water: our steps (the last ones), the drone's downwash, the skis at touchdown"""
    out = []
    if 119.0 < t < 392.0:
        g = 0.31; j = int(t / g)
        while j * g > t - 5.0 and len(out) < 6:
            ts = j * g
            x, y, _ = cr(CAM_P, ts); x1, y1, _ = cr(CAM_P, ts - 0.1)
            v = math.hypot(x - x1, y - y1) / 0.1
            if (v > 3.0 or (j % 2 == 0 and v > 0.5)) and 119.0 < ts < 390.0:
                hd = math.atan2(y - y1, x - x1); lat = (0.17 if (j // (1 if v > 3.0 else 2)) % 2 == 0 else -0.17)
                rnd = 0.5 + 0.5 * n1(j * 0.731, 21)
                out.append(((x - math.sin(hd) * lat) * 100.0, (y + math.cos(hd) * lat) * 100.0, ts, 0.55 + 0.8 * rnd))
            j -= 1
    d = drone_world(t)
    if d is not None and d[2] < 1.5 and t > 106.0:
        out.append((d[0] * 100.0, d[1] * 100.0, t - (t % 1.3) - 0.2, 0.35))
    if T_LAND - 0.2 < t < T_LAND + 7.0:
        out = [(290.0, 210.0, T_LAND - 0.1, 3.0), (290.0, -210.0, T_LAND - 0.1, 3.0), (-290.0, 230.0, T_LAND + 0.05, 3.0), (-290.0, -230.0, T_LAND + 0.05, 3.0)]
    return out[:8]


def drone_world(t):
    if t < 106.0 or t >= 397.0: return None
    return tuple(cr(DR_P, t))


# ---------------------------------------------------------------- applying the state
_A = {}
_LAST = {}


def A(label):
    a = _A.get(label)
    if a is None:
        _A.clear()
        for x in EAS.get_all_level_actors(): _A[x.get_actor_label()] = x
        a = _A.get(label)
    return a


# base transforms of the niche cover and the storage: pivots from Models/export/probe_wreck/manifest.json (Blender x, y, z -> UE x, -y, z),
# the wreck root stands at (12860, 15320, 0) cm; both parts have no rotation of their own relative to wr_bus
WRECK_BASE = {'panel0': (12829.16, 15283.26, 83.69), 'stor0': (12841.92, 15298.46, 72.35)}


def _wreck_reset():
    """the cover and the storage are animated from their base transforms: never trust what the level happens to hold
    (a re-install in the middle of the timeline used to memorize the fallen cover as the base)"""
    bus = A('wr_bus'); pan = A('wr_panel'); st = A('wr_storage')
    pan.set_actor_location(unreal.Vector(*WRECK_BASE['panel0']), False, False); pan.set_actor_rotation(bus.get_actor_rotation(), False)
    st.set_actor_location(unreal.Vector(*WRECK_BASE['stor0']), False, False); st.set_actor_rotation(bus.get_actor_rotation(), False)


def init():
    """call once after the editor has started (and after s3_build): caches actors, speeds up helpers"""
    _A.clear(); _LAST.clear()
    A('Wave')
    for mod in (s1u, l_keys, q_shots):
        mod.find = A
    _wreck_reset()
    _LAST['panel0'] = A('wr_panel').get_actor_location()
    _LAST['stor0'] = A('wr_storage').get_actor_location()
    w = world()
    unreal.SystemLibrary.execute_console_command(w, 'r.HighResScreenshotDelay 1')
    q_shots.hide('ck_seat', True)
    for lb in ['ext_cockpit_proxy', 'ck_hatch_proxy']: q_shots.hide(lb, True)
    q_shots.flag_ship()
    return len(_A)


def _rot(p, y, r): return unreal.Rotator(pitch=p, yaw=y, roll=r)
def _set_rel(label, key, rot):
    if _LAST.get(key) != rot:
        _LAST[key] = rot
        A(label).root_component.set_relative_rotation(_rot(*rot), False, False)


def apply_time(t):
    sx, sy, sz, sp, syaw, sr = ship_pose(t)
    srot = _rot(sp, syaw, sr)
    spos = unreal.Vector(sx * 100.0, sy * 100.0, sz * 100.0)
    aroot = ML.compose_rotators(_rot(0.0, -90.0, 0.0), srot)
    for lb in ('Chaika', 'ChaikaCockpit', 'PilotGloves'):
        a = A(lb); a.set_actor_location(spos, False, False); a.set_actor_rotation(aroot, False)
    def to_world(p):
        v = ML.greater_greater_vector_rotator(unreal.Vector(p[0] * 100.0, p[1] * 100.0, p[2] * 100.0), srot)
        return unreal.Vector(v.x + spos.x, v.y + spos.y, v.z + spos.z)
    # camera
    cx, cy, cz, cyaw, cpitch, croll, focal = cam_local(t)
    cam = A('CAM_Film')
    cw = to_world((cx, cy, cz))
    cam.set_actor_location(cw, False, False)
    cam.set_actor_rotation(ML.compose_rotators(_rot(cpitch, cyaw, croll), srot), False)
    cc = cam.get_cine_camera_component()
    if _LAST.get('focal') != round(focal, 2):
        _LAST['focal'] = round(focal, 2); cc.set_editor_property('current_focal_length', focal)
    # wave, water, shadow, rings
    q_shots.apply(t, cw.y / 100.0, rings(t), penumbra_m=2.0)
    l_keys.set_mpc_defaults({'RippleAmp': ease(RIPPLE, t)[0]}, {})
    w2 = A('Wave2')
    show2 = t >= 470.0
    if _LAST.get('w2') != show2:
        _LAST['w2'] = show2; w2.set_actor_hidden_in_game(not show2); w2.set_is_temporarily_hidden_in_editor(not show2)
    if show2: w2.set_actor_location(unreal.Vector((wave_x_m(t) + 62000.0) * 100.0, 0.0, 0.0), False, False)
    # ship parts
    _set_rel('ext_nacelle_L', 'nl', (0.0, 0.0, round(ease(NACELLE, t)[0], 2)))
    _set_rel('ext_nacelle_R', 'nr', (0.0, 0.0, round(ease(NACELLE, t)[0], 2)))
    _set_rel('ext_ramp', 'ramp', (0.0, 0.0, round(ease(RAMP, t)[0], 2)))
    _set_rel('ext_hatch', 'hatch', (0.0, round(ease(HATCH, t)[0], 2), 0.0))
    _set_rel('ck_door', 'door', (0.0, round(ease(DOOR, t)[0], 2), 0.0))
    # drone
    dr = A('Svetlyak'); d = drone_world(t)
    if d is None:
        dr.set_actor_location(to_world(CRADLE), False, False); dr.set_actor_rotation(aroot, False)
    else:
        dr.set_actor_location(unreal.Vector(d[0] * 100.0, d[1] * 100.0, d[2] * 100.0), False, False)
        dr.set_actor_rotation(_rot(2.0 * math.sin(t * 1.1), ease(DR_Y, t)[0] - 90.0, 2.0 * math.sin(t * 0.8)), False)
    arm = ease(DR_ARM, t)[0]
    _set_rel('sv_arm_upper', 'au', (0.0, 0.0, round(-117.0 * arm, 1)))
    _set_rel('sv_arm_fore', 'af', (0.0, 0.0, round(134.5 * arm, 1)))
    _set_rel('sv_arm_wrist', 'aw', (0.0, 0.0, round(19.5 * arm, 1)))
    # wreck: the niche cover comes off, the storage slides out
    kp = sstep((t - 262.0) / 3.0); kd = sstep((t - 265.0) / 2.5)
    p0 = _LAST['panel0']
    pan = (round(kp, 3), round(kd, 3))
    if _LAST.get('pan') != pan:
        _LAST['pan'] = pan
        a = A('wr_panel')
        a.set_actor_location(unreal.Vector(p0.x + PN[0] * 25.0 * kp, p0.y + PN[1] * 25.0 * kp, p0.z + PN[2] * 25.0 * kp - 70.0 * kd), False, False)
        a.set_actor_hidden_in_game(t >= 268.0); a.set_is_temporarily_hidden_in_editor(t >= 268.0)
    ks = round(sstep((t - 275.0) / 14.0), 3); taken = t >= 296.0
    if _LAST.get('stor') != (ks, taken):
        _LAST['stor'] = (ks, taken)
        s0 = _LAST['stor0']; a = A('wr_storage')
        a.set_actor_location(unreal.Vector(s0.x + PN[0] * 42.0 * ks, s0.y + PN[1] * 42.0 * ks, s0.z + PN[2] * 42.0 * ks), False, False)
        a.set_actor_hidden_in_game(taken); a.set_is_temporarily_hidden_in_editor(taken)
    cut = A('CutterLight')
    ci = 5.0 * (0.4 + 0.6 * abs(n1(t * 23.0, 31))) if 236.0 < t < 262.0 else 0.0
    if _LAST.get('cut') != (ci > 0.0) or ci > 0.0:
        _LAST['cut'] = ci > 0.0
        cut.set_actor_location(unreal.Vector((PANEL[0] + PN[0] * 0.06) * 100.0, (PANEL[1] + PN[1] * 0.06) * 100.0, (PANEL[2] + 0.02) * 100.0), False, False)
        cut.point_light_component.set_intensity(ci)
    # light, exposure, post
    uw = T_HIT - 0.3 <= t < T_UP - 0.4
    if _LAST.get('uw') != uw:
        _LAST['uw'] = uw; q_shots.underwater(uw)
    wgt = sstep((t - (T_HIT - 0.4)) / 0.7) * (1.0 - sstep((t - (T_UP - 0.4)) / 0.8))
    if _LAST.get('uww') != round(wgt, 3):
        _LAST['uww'] = round(wgt, 3); A('PPV_Underwater').set_editor_property('blend_weight', wgt)
    pw = round(ease(PLASMA, t)[0], 3)
    if _LAST.get('pl') != pw:
        _LAST['pl'] = pw; A('PPV_Plasma').set_editor_property('blend_weight', pw)
    mode = 'emergency' if t >= T_HIT else ('cabin' if (t < 116.0 or t > 391.0) else 'off')
    if _LAST.get('cab') != mode:
        _LAST['cab'] = mode
        for lb in ('CabinEmergency_L', 'CabinEmergency_R'):
            c = A(lb).point_light_component
            c.set_light_color(unreal.LinearColor(1.0, 0.40, 0.16) if mode == 'emergency' else unreal.LinearColor(1.0, 0.86, 0.72))
            c.set_intensity({'emergency': 0.8, 'cabin': 0.22, 'off': 0.0}[mode]); c.set_visibility(mode != 'off')
        wf = A('WaterFill').point_light_component
    wfi = 40.0 if uw else 0.0
    if _LAST.get('wf') != wfi:
        _LAST['wf'] = wfi
        c = A('WaterFill').point_light_component; c.set_intensity(wfi); c.set_visibility(wfi > 0.0)
    for lb, off in (('CabinEmergency_L', (4.72, -0.36, 3.20)), ('CabinEmergency_R', (4.72, 0.36, 3.20)), ('WaterFill', (8.6, 0.6, 5.2))):
        A(lb).set_actor_location(to_world(off), False, False)
    fog_on = t >= 64.0            # from orbit the height fog would whiten the whole planet
    if _LAST.get('fog') != fog_on:
        _LAST['fog'] = fog_on
        A('HeightFog').get_component_by_class(unreal.ExponentialHeightFogComponent).set_visibility(fog_on)
    ex = round(ease(EXPO, t)[0], 2)
    if _LAST.get('ex') != ex:
        _LAST['ex'] = ex; q_shots.exposure(ex)
    return t


# ---------------------------------------------------------------- rendering
def _shoot(path, w, h, live=True):
    """live=True keeps the viewport redrawing every tick (stills); live=False draws only the captured frame (fast film render)"""
    unreal.AutomationLibrary.take_high_res_screenshot(w, h, path, camera=A('CAM_Film'))
    if live:
        LES.editor_set_viewport_realtime(True)
    LES.editor_invalidate_viewports()


_HWND = [None]


def _guard_window():
    """A minimised editor does not draw (e.g. after "show desktop"); after sleep Windows moves the window back on screen.
    Put it back beyond the right edge of the screen, without focus."""
    try:
        import ctypes
        from ctypes import wintypes
        u32 = ctypes.windll.user32
        u32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
        u32.SetWindowPos.restype = wintypes.BOOL
        u32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        u32.IsIconic.argtypes = [wintypes.HWND]; u32.ShowWindowAsync.argtypes = [wintypes.HWND, ctypes.c_int]
        if _HWND[0] is None:
            pid = os.getpid(); found = []
            proto = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            def cb(h, l):
                p_ = wintypes.DWORD(); u32.GetWindowThreadProcessId(h, ctypes.byref(p_))
                if p_.value == pid and u32.IsWindowVisible(h):
                    buf = ctypes.create_unicode_buffer(256); u32.GetWindowTextW(h, buf, 256)
                    if 'Unreal Editor' in buf.value: found.append(h)
                return True
            u32.EnumWindows(proto(cb), 0)
            if found: _HWND[0] = found[0]
        h = _HWND[0]
        if not h: return False
        r = wintypes.RECT(); u32.GetWindowRect(h, ctypes.byref(r))
        if u32.IsIconic(h) or r.left < 2400:
            if u32.IsIconic(h): u32.ShowWindowAsync(h, 4)
            u32.SetWindowPos(h, wintypes.HWND(1), 3000, 0, 1600, 1000, 0x0010)     # physical pixels (display scale 125 %)
            return True
    except Exception as e:
        pass
    return False


def _stop():
    h = getattr(builtins, '_s3_handle', None)
    if h is not None:
        unreal.unregister_slate_post_tick_callback(h); builtins._s3_handle = None


def render(f0, f1, outdir=OUT, w=960, h=540, times=None, prefix='f_', settle=0, frames=None):
    """frames f0..f1 (or explicit list of times) -> PNG. Runs in editor ticks; poll with status()."""
    _stop()
    os.makedirs(outdir, exist_ok=True)
    job = [(('%s%05d' % (prefix, f)), f / FPS) for f in (frames if frames is not None else range(f0, f1 + 1))] if times is None else [(('%s%04d' % (prefix, int(round(tt * 10)))), tt) for tt in times]
    st = dict(job=job, i=-1, dir=outdir, w=w, h=h, path=None, wait=0, t0=time.time(), done=False, err=None, settle=settle, hold=0, tick=0, retry=0, restored=0)
    builtins._s3 = st

    def tick(dt):
        s = builtins._s3
        if s['done']: return
        try:
            if s['hold'] > 0:                       # let the picture settle after a jump in time (stills only)
                s['hold'] -= 1; LES.editor_invalidate_viewports()
                if s['hold'] == 0: _shoot(s['path'], s['w'], s['h'])
                return
            s['tick'] += 1
            if s['tick'] % 50 == 0 and _guard_window():
                s['restored'] += 1
            if s['path'] and not os.path.exists(s['path']):
                s['wait'] += 1
                LES.editor_invalidate_viewports()      # the capture needs a redraw after the request is armed: redraw every tick
                if s['wait'] % 150 == 0:               # the frame got lost (window was minimised?): ask for the same frame again
                    s['retry'] += 1; _guard_window(); _shoot(s['path'], s['w'], s['h'], live=True)
                return
            s['i'] += 1; s['wait'] = 0
            if s['i'] >= len(s['job']):
                s['done'] = True; s['t1'] = time.time(); _stop(); return
            name, tt = s['job'][s['i']]
            apply_time(tt)
            s['path'] = os.path.join(s['dir'], name + '.png')
            if os.path.exists(s['path']): os.remove(s['path'])
            if s['settle'] > 0:
                s['hold'] = s['settle']; LES.editor_set_viewport_realtime(True); LES.editor_invalidate_viewports()
            else:
                _shoot(s['path'], s['w'], s['h'], live=True)
        except Exception as e:
            import traceback
            s['err'] = traceback.format_exc(); s['done'] = True; _stop()
    builtins._s3_handle = unreal.register_slate_post_tick_callback(tick)
    return len(job)


def status():
    s = getattr(builtins, '_s3', None)
    if s is None: return 'no job'
    el = (s.get('t1') or time.time()) - s['t0']
    n = max(s['i'], 0)
    return 'frame %d of %d, %.0f s, %.2f s/frame, done=%s%s' % (n, len(s['job']), el, el / max(n, 1), s['done'], ('\n' + s['err']) if s['err'] else '')
