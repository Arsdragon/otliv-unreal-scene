# live_shots.py — приёмочные рендеры этапа B в ОТКРЫТОМ окне Blender (очередь кадров, окно не блокируется):
#   python tools/bmcp.py @tools/live_shots.py
# Перед запуском в сцену должна быть загружена коллекция chaika_ext из src/chaika_ext_final.blend
# (tools/show_in_blender.py). Каждый кадр рендерится как обычный F12 — пользователь видит ход рендера.
# Готовность: появляется файл shots/_tmp/live_done.txt. Переменная LIVE_VIEWS — список видов (по умолчанию все).
import bpy, os, math, time
from mathutils import Vector

TOOLS = r'C:\UnrealScenes\Models\tools'
ROOT = os.path.dirname(TOOLS)
exec(open(os.path.join(TOOLS, 'shots_kit.py'), encoding='utf-8').read())
VIEWS = {
    'v15': ((-9.6, -11.5, 1.7), (0.2, 0.2, 2.35), 56, (-30, 26)),      # с высоты глаз, 15 м, спереди-слева
    'v60': ((-37.0, -47.0, 1.7), (0.0, 0.0, 2.6), 24, (-30, 26)),      # с 60 м
    'nose': ((-3.4, -9.0, 1.7), (-0.3, -5.5, 2.55), 52, (-45, 30)),    # нос и фонарь
    'gear': ((-5.0, -5.4, 1.25), (-2.0, -2.9, 0.95), 48, (-60, 32)),   # передняя опора с лыжей в воде
    'nacelle': ((-8.2, 2.4, 1.7), (-4.3, 0.1, 3.0), 46, (-75, 30)),    # мотогондола и законцовка крыла
    'side': ((-6.3, -2.6, 1.7), (-1.6, -2.6, 2.55), 50, (-70, 34)),    # борт с надписью
    'rear': ((5.6, 11.8, 1.7), (0.0, 2.6, 2.25), 56, (150, 30)),       # сзади, трап опущен
    'wingtop': ((-9.5, -5.5, 8.5), (-1.2, 0.2, 3.3), 50, (-50, 40)),   # крыло и крыша сверху
    'gear1m': ((-3.25, -4.05, 1.25), (-2.0, -2.9, 0.95), 60, (-60, 32)),  # опора с расстояния около 1,5 м
    'wingunder': ((7.6, -3.6, 1.7), (3.0, 0.3, 3.6), 50, (95, 14)),       # низ крыла с высоты глаз
}
todo = list(globals().get('LIVE_VIEWS') or [v for v in VIEWS if v not in ('wingtop', 'gear1m', 'wingunder')])
SAMPLES = globals().get('LIVE_SAMPLES', 36)
done_file = os.path.join(ROOT, 'shots', '_tmp', 'live_done.txt')
if os.path.exists(done_file):
    os.remove(done_file)
sc = bpy.context.scene
for im in bpy.data.images:                                  # перечитать текстуры с диска (могли перерисоваться)
    if im.filepath and 'T_Chaika' in im.filepath:
        im.reload()
if 'stage_water' not in bpy.data.objects:
    sky_world(1.0, horizon=(0.86, 0.84, 0.82), zenith=(0.34, 0.50, 0.74), ground=(0.40, 0.42, 0.44))
    sun(-30, 26, 3.4, color=(1.0, 0.93, 0.84))
    plane('stage_ground', 0.0, 8000, simple_mat('stage_ground', (0.50, 0.47, 0.42), 0.85))
    plane('stage_water', 0.45, 8000, water_mat())
the_sun = bpy.data.objects['sun']
setup_cycles(1920, 1080, samples=SAMPLES, bounces=5)
sc.cycles.adaptive_threshold = 0.035
try:
    sc.render.use_persistent_data = False
except Exception:
    pass
cams = {}
for v in todo:
    pos, tgt, fov, _ = VIEWS[v]
    old = bpy.data.objects.get('cam_' + v)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    cams[v] = camera('cam_' + v, Vector(pos), Vector(tgt) - Vector(pos), fov=fov, clip=(0.05, 9000))
log = open(os.path.join(ROOT, 'shots', '_tmp', 'live_shots.log'), 'a', encoding='utf-8')
state = {'t0': 0.0, 'cur': None}


def _tick():
    if bpy.app.is_job_running('RENDER'):
        return 3.0
    if state['cur']:
        log.write('RENDERED %s %.0f s\n' % (state['cur'], time.time() - state['t0']))
        log.flush()
        state['cur'] = None
    if not todo:
        open(done_file, 'w').write('done')
        log.write('LIVE_DONE\n')
        log.flush()
        return None
    v = todo.pop(0)
    az, el = VIEWS[v][3]
    a, e = math.radians(az), math.radians(el)
    to_sun = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    the_sun.rotation_euler = (-to_sun).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cams[v]
    sc.render.filepath = os.path.join(ROOT, 'shots', 'B_chaika_%s.png' % v)
    state['cur'], state['t0'] = v, time.time()
    w = bpy.context.window_manager.windows[0]
    try:
        with bpy.context.temp_override(window=w, screen=w.screen):
            bpy.ops.render.render('INVOKE_DEFAULT', write_still=True)
    except Exception as ex:
        log.write('ERROR %s %s\n' % (v, ex))
        log.flush()
    return 5.0


bpy.app.timers.register(_tick, first_interval=1.0)
print('очередь рендеров запущена:', todo)
