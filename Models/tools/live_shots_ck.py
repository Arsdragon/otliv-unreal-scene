# live_shots_ck.py — приёмочные рендеры кабины в ОТКРЫТОМ окне Blender (очередь кадров, окно не блокируется):
#   python tools/bmcp.py @tools/live_shots_ck.py 300        (LIVE_VIEWS — список видов, по умолчанию все)
# В сцене должна быть коллекция chaika_cockpit с итоговыми материалами. Готовность: shots/_tmp/live_done.txt
import bpy, os, math, time
from mathutils import Vector

TOOLS = r'C:\UnrealScenes\Models\tools'
ROOT = os.path.dirname(TOOLS)
exec(open(os.path.join(TOOLS, 'shots_kit.py'), encoding='utf-8').read())
E = Vector((0.0, -5.20, 2.78))


def _dir(yaw, pitch):
    """yaw > 0 — влево от пилота (к +X), pitch > 0 — вверх."""
    y, p = math.radians(yaw), math.radians(pitch)
    return Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p)))


#          камера                 направление или цель                    угол обзора
VIEWS = {
    'eye_fwd': (E, _dir(0, 0), 90), 'eye_up40': (E, _dir(0, 40), 90), 'eye_down25': (E, _dir(0, -25), 90),
    'eye_left60': (E, _dir(60, -8), 90), 'eye_right60': (E, _dir(-60, -8), 90), 'eye_left100': (E, _dir(100, -8), 90),
    'back_airlock': (Vector((0.10, -4.55, 2.90)), Vector((0.0, 0.6, 2.50)) - Vector((0.10, -4.55, 2.90)), 80),
    'panel': (Vector((0.0, -5.36, 2.74)), Vector((0.0, -6.0, 2.43)) - Vector((0.0, -5.36, 2.74)), 66),
    'console_left': (Vector((0.60, -5.02, 3.22)), 'down', 64),      # строго сверху, верх кадра — к носу (как видит пилот)
    'console_right': (Vector((-0.60, -5.02, 3.22)), 'down', 64),
    'overhead': (Vector((0.0, -5.42, 2.74)), Vector((0.0, -4.98, 3.52)) - Vector((0.0, -5.42, 2.74)), 62),
    'airlock': (Vector((0.0, -1.95, 3.30)), Vector((0.0, 1.2, 2.55)) - Vector((0.0, -1.95, 3.30)), 86),
}
todo = list(globals().get('LIVE_VIEWS') or [v for v in VIEWS if v not in ('overhead', 'airlock')])
SAMPLES = globals().get('LIVE_SAMPLES', 40)
done_file = os.path.join(ROOT, 'shots', '_tmp', 'live_done.txt')
if os.path.exists(done_file):
    os.remove(done_file)
sc = bpy.context.scene
for im in bpy.data.images:
    if im.filepath and ('T_Cockpit' in im.filepath or 'T_Screen' in im.filepath):
        im.reload()
if 'stage_water' not in bpy.data.objects:
    sky_world(1.0, horizon=(0.86, 0.84, 0.82), zenith=(0.34, 0.50, 0.74), ground=(0.40, 0.42, 0.44))
    sun(30, 30, 3.2, color=(1.0, 0.93, 0.84))
    plane('stage_ground', 0.0, 8000, simple_mat('stage_ground', (0.50, 0.47, 0.42), 0.85))
    plane('stage_water', 0.45, 8000, water_mat())
setup_cycles(1920, 1080, samples=SAMPLES, bounces=5)
sc.cycles.adaptive_threshold = 0.04
cams = {}
for v in todo:
    pos, d, fov = VIEWS[v]
    old = bpy.data.objects.get('cam_' + v)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    cams[v] = camera('cam_' + v, pos, (0, 0, -1) if isinstance(d, str) else d, fov=fov, clip=(0.02, 9000))
    if isinstance(d, str):
        cams[v].rotation_euler = (0, 0, math.pi)
if 'overhead' in cams:                                    # как видит пилот, запрокинув голову: верх кадра — к хвосту
    from mathutils import Quaternion
    cams['overhead'].rotation_euler = (cams['overhead'].rotation_euler.to_quaternion() @ Quaternion((0, 0, 1), math.pi)).to_euler()
log = open(os.path.join(ROOT, 'shots', '_tmp', 'live_shots.log'), 'a', encoding='utf-8')
state = {'t0': 0.0, 'cur': None}
door = bpy.data.objects.get('ck_door')


def _tick():
    if bpy.app.is_job_running('RENDER'):
        return 3.0
    if state['cur']:
        log.write('RENDERED %s %.0f s\n' % (state['cur'], time.time() - state['t0']))
        log.flush()
        state['cur'] = None
    if not todo:
        if door:
            door.rotation_euler = (0, 0, 0)
        open(done_file, 'w').write('done')
        log.write('LIVE_DONE\n')
        log.flush()
        return None
    v = todo.pop(0)
    if door:                                                # дверь в шлюз открыта только для взгляда назад
        door.rotation_euler = (0, 0, math.radians(-100) if v == 'back_airlock' else 0)
    sc.camera = cams[v]
    sc.render.filepath = os.path.join(ROOT, 'shots', 'C_cockpit_%s.png' % v)
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
