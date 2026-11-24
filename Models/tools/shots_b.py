# shots_b.py — приёмочные рендеры этапа B (chaika_ext с экспортными текстурами), Cycles:
#   bash tools/bl.sh src/chaika_ext_final.blend tools/shots_b.py -- [quick] [v15 v60 nose gear nacelle side rear top]
# quick — быстрая проверка в Workbench (цвет из текстур, без освещения сцены) в shots/_tmp.
import bpy, os, sys, math, time
from mathutils import Vector

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
exec(open(os.path.join(TOOLS, 'shots_kit.py'), encoding='utf-8').read())
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
QUICK = 'quick' in args
views = [a for a in args if a != 'quick'] or ['v15', 'v60', 'nose', 'gear', 'nacelle', 'side', 'rear']
OUT = os.path.join(ROOT, 'shots', '_tmp' if QUICK else '')
os.makedirs(OUT, exist_ok=True)

#        камера (x, y, z)          цель               угол   солнце (азимут, высота)
VIEWS = {
    'v15': ((-9.6, -11.5, 1.7), (0.2, 0.2, 2.35), 56, (-30, 26)),      # с высоты глаз, 15 м, спереди-слева
    'v60': ((-37.0, -47.0, 1.7), (0.0, 0.0, 2.6), 24, (-30, 26)),      # с 60 м
    'nose': ((-3.4, -9.0, 1.7), (-0.3, -5.5, 2.55), 52, (-45, 30)),    # нос и фонарь
    'gear': ((-5.0, -5.4, 1.25), (-2.0, -2.9, 0.95), 48, (-60, 32)),   # передняя опора с лыжей в воде
    'nacelle': ((-8.2, 2.4, 1.7), (-4.3, 0.1, 3.0), 46, (-75, 30)),    # мотогондола и законцовка крыла
    'side': ((-6.3, -2.6, 1.7), (-1.6, -2.6, 2.55), 50, (-70, 34)),    # борт с надписью
    'rear': ((5.6, 11.8, 1.7), (0.0, 2.6, 2.25), 56, (150, 30)),       # сзади, трап опущен
    'top': ((-7.0, 6.0, 9.5), (0.0, 0.3, 3.0), 50, (-40, 45)),
}

if QUICK:
    sc = bpy.context.scene
    setup_workbench(1600, 900)
    sc.display.shading.color_type = 'TEXTURE'
    sc.display.shading.light = 'FLAT'
    sc.display.shading.show_cavity = False
else:
    sky_world(1.0, horizon=(0.86, 0.84, 0.82), zenith=(0.34, 0.50, 0.74), ground=(0.40, 0.42, 0.44))
    the_sun = sun(-30, 26, 3.4, color=(1.0, 0.93, 0.84))
    plane('stage_ground', 0.0, 8000, simple_mat('stage_ground', (0.50, 0.47, 0.42), 0.85))
    plane('stage_water', 0.45, 8000, water_mat())

for v in views:
    pos, tgt, fov, (az, el) = VIEWS[v]
    p = Vector(pos)
    cam = camera(v, p, Vector(tgt) - p, fov=fov, clip=(0.05, 9000))
    t0 = time.time()
    if QUICK:
        render(cam, os.path.join(OUT, 'bq_%s.png' % v))
        continue
    setup_cycles(1920, 1080, samples=72, bounces=6)
    a, e = math.radians(az), math.radians(el)
    to_sun = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    the_sun.rotation_euler = (-to_sun).to_track_quat('-Z', 'Y').to_euler()
    render(cam, os.path.join(OUT, 'B_chaika_%s.png' % v))
    print('TIME %s %.0f s' % (v, time.time() - t0))
