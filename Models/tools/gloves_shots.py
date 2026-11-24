# gloves_shots.py — кадры перчаток пилота в кабине (фоновый Blender):
#   bash tools/bg.sh "load('chaika_cockpit_final.blend'); run('gloves_shots.py', GL_BLEND='pilot_gloves_final.blend', LIVE_VIEWS=['eye_down'])"
# Перчатки подгружаются из src/<GL_BLEND> (коллекция pilot_gloves). GL_PREFIX — куда писать (по умолчанию shots/E_gloves_),
# GL_SIZE — размер кадра, LIVE_SAMPLES — число проходов.
import bpy, os, math, time
from mathutils import Vector

TOOLS = r'C:\UnrealScenes\Models\tools'
ROOT = os.path.dirname(TOOLS)
exec(open(os.path.join(TOOLS, 'shots_kit.py'), encoding='utf-8').read())
E = Vector((0.0, -5.20, 2.78))                        # eye_pilot
HR, HL = Vector((-0.490, -5.270, 2.445)), Vector((0.480, -5.200, 2.430))
sc = bpy.context.scene


def _dir(yaw, pitch):
    y, p = math.radians(yaw), math.radians(pitch)
    return Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p)))


#        вид: (камера, направление, поле зрения по горизонтали)
VIEWS = {
    'eye_down': (E, _dir(0, -62), 126),                                   # из глаз вперёд-вниз, обе кисти у краёв кадра
    'eye_right': (E, HR - E, 52), 'eye_left': (E, HL - E, 52),            # из глаз на правую и на левую кисть
    'stick_close': (Vector((-0.18, -5.60, 2.63)), HR + Vector((0, -0.02, 0.0)) - Vector((-0.18, -5.60, 2.63)), 44),
    'throttle_close': (Vector((0.17, -5.56, 2.66)), HL + Vector((0, -0.03, -0.01)) - Vector((0.17, -5.56, 2.66)), 44),
    'stick_back': (Vector((-0.78, -4.98, 2.66)), HR - Vector((-0.78, -4.98, 2.66)), 46),
    'throttle_under': (Vector((0.26, -5.50, 2.36)), HL + Vector((0, -0.03, -0.01)) - Vector((0.26, -5.50, 2.36)), 50),
}
if 'pilot_gloves' not in bpy.data.objects:
    with bpy.data.libraries.load(os.path.join(ROOT, 'src', globals().get('GL_BLEND', 'pilot_gloves_final.blend')), link=False) as (src, dst):
        dst.collections = [c for c in src.collections if c == 'pilot_gloves']
    for c in dst.collections:
        sc.collection.children.link(c)
if 'stage_water' not in bpy.data.objects:
    sky_world(1.0, horizon=(0.86, 0.84, 0.82), zenith=(0.34, 0.50, 0.74), ground=(0.40, 0.42, 0.44))
    sun(30, 30, 3.2, color=(1.0, 0.93, 0.84))
    plane('stage_ground', 0.0, 8000, simple_mat('stage_ground', (0.50, 0.47, 0.42), 0.85))
    plane('stage_water', 0.45, 8000, water_mat())
w, h = globals().get('GL_SIZE', (1920, 1080))
setup_cycles(w, h, samples=globals().get('LIVE_SAMPLES', 40), bounces=5)
sc.cycles.adaptive_threshold = 0.04
prefix = globals().get('GL_PREFIX', os.path.join(ROOT, 'shots', 'E_gloves_'))
for v in list(globals().get('LIVE_VIEWS') or VIEWS):
    pos, d, fov = VIEWS[v]
    old = bpy.data.objects.get('cam_gl')
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    sc.camera = camera('cam_gl', pos, d, fov=fov, clip=(0.02, 9000))
    sc.render.filepath = prefix + v + '.png'
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print('RENDERED %s %.0f s' % (v, time.time() - t0))
