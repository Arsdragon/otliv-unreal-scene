# live_shots_d.py — приёмочные кадры этапа D в открытом Blender (очередь F12, окно не блокируется):
#   bash tools/live.sh @code "D_ID='svetlyak'; LIVE_VIEWS=['around1']; LIVE_SAMPLES=24; exec(open(r'C:\UnrealScenes\Models\tools\live_shots_d.py', encoding='utf-8').read())" 120
# Готовность — shots/_tmp/live_done.txt; кадры — shots/D_<id>_<вид>.png. Сцена: грунт, вода 0,45 м, небо, солнце.
import bpy, os, math, time
from mathutils import Vector

TOOLS = r'C:\UnrealScenes\Models\tools'
ROOT = os.path.dirname(TOOLS)
exec(open(os.path.join(TOOLS, 'shots_kit.py'), encoding='utf-8').read())
SAMPLES = globals().get('LIVE_SAMPLES', 32)
done_file = os.path.join(ROOT, 'shots', '_tmp', 'live_done.txt')
if os.path.exists(done_file):
    os.remove(done_file)
sc = bpy.context.scene
root = bpy.data.objects[D_ID]
for im in bpy.data.images:
    if im.filepath and ('T_Svetlyak' in im.filepath or 'T_ProbeWreck' in im.filepath):
        im.reload()
if 'stage_water' not in bpy.data.objects:
    sky_world(1.0, horizon=(0.86, 0.84, 0.82), zenith=(0.34, 0.50, 0.74), ground=(0.40, 0.42, 0.44))
    sun(-30, 26, 3.4, color=(1.0, 0.93, 0.84))
    plane('stage_ground', 0.0, 8000, simple_mat('stage_ground', (0.50, 0.47, 0.42), 0.85))
    plane('stage_water', 0.45, 8000, water_mat())
the_sun = bpy.data.objects['sun']
HOVER = Vector((0, 0, 0.95))               # дрон висит: низ на 0,40 м над водой (вода 0,45 м)
WORK = {'sv_arm_upper': -117.0, 'sv_arm_fore': 134.5, 'sv_arm_wrist': 19.5, 'sv_finger_L': 15.0, 'sv_finger_R': -15.0}
AXIS = {'sv_arm_upper': 0, 'sv_arm_fore': 0, 'sv_arm_wrist': 0, 'sv_finger_L': 2, 'sv_finger_R': 2}
SAVED = {}


def reset():
    for nm in WORK:
        o = bpy.data.objects.get(nm)
        if o:
            o.rotation_euler = (0, 0, 0)
    for nm, mw in SAVED.items():
        bpy.data.objects[nm].matrix_world = mw
    SAVED.clear()
    pnl = bpy.data.objects.get('wr_panel')
    if pnl:
        pnl.hide_render = False
    bpy.context.view_layer.update()


def work_pose():
    for nm, a in WORK.items():
        o = bpy.data.objects.get(nm)
        if o:
            r = [0.0, 0.0, 0.0]
            r[AXIS[nm]] = math.radians(a)
            o.rotation_euler = r
    bpy.context.view_layer.update()


def open_bay():
    """Крышка снята, накопитель выдвинут на 0,14 м за ручку."""
    bpy.data.objects['wr_panel'].hide_render = True
    st = bpy.data.objects['wr_storage']
    ax = (bpy.data.objects['storage_handle'].matrix_world.to_3x3() @ Vector((0, 1, 0))).normalized()
    SAVED['wr_storage'] = st.matrix_world.copy()
    st.matrix_world = __import__('mathutils').Matrix.Translation(ax * 0.14) @ st.matrix_world
    bpy.context.view_layer.update()


def wp(name):
    return bpy.data.objects[name].matrix_world.translation.copy()


def ydir(name):
    return (bpy.data.objects[name].matrix_world.to_3x3() @ Vector((0, 1, 0))).normalized()


def around(az, el=18, dist=1.15, fov=40):
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    return (HOVER + d * dist, HOVER + Vector((0, 0, -0.01)), fov)


def face_view(k, dist=0.95, h=0.55, fov=48):
    bus = bpy.data.objects['wr_bus']
    n = (bus.matrix_world.to_3x3() @ Vector((math.cos(math.radians(45 * k)), math.sin(math.radians(45 * k)), 0))).normalized()
    c = bus.matrix_world @ (Vector((math.cos(math.radians(45 * k)), math.sin(math.radians(45 * k)), 0)) * 0.65 + Vector((0, 0, 0.42)))
    c.z = h
    n.z = 0
    n.normalize()
    return (c + n * dist + Vector((0, 0, 0.12)), c + Vector((0, 0, -0.04)), fov)


def panel_view():
    c, n = wp('panel_center'), ydir('panel_center')
    n.z = 0
    n.normalize()
    side = Vector((-n.y, n.x, 0))
    return (c + n * 1.75 + side * 0.45 + Vector((0, 0, 0.62)), c + Vector((0, 0, -0.18)), 46)


def bus10():
    """Главный блок с 10 м, с высоты глаз, обычным объективом — читаются ли пояса соли."""
    n = ydir('panel_center')
    n.z = 0
    n.normalize()
    d = (n * 0.82 + Vector((-n.y, n.x, 0)) * 0.57).normalized()
    b = bpy.data.objects['wr_bus'].matrix_world.translation
    tgt = Vector((b.x, b.y, 0.55))
    return (tgt + d * 10.0 + Vector((0, 0, 1.15)), tgt, 36)


#            вид: (камера, подготовка сцены, солнце (азимут: 0 — с −Y, 90 — с +X; высота))
VIEWS = {
    'around1': (lambda: around(35), None, (-40, 30)), 'around2': (lambda: around(125), None, (60, 30)),
    'around3': (lambda: around(215), None, (150, 30)), 'around4': (lambda: around(305), None, (-120, 30)),
    'lens': (lambda: (wp('cam_lens') + Vector((0.20, -0.44, 0.10)), wp('cam_lens'), 36), None, (-20, 28)),
    'impeller': (lambda: (HOVER + Vector((0.215, -0.095, 0.0)) + Vector((0.30, -0.30, 0.30)), HOVER + Vector((0.215, -0.095, -0.002)), 40),
                 None, (-50, 40)),
    'arm': (lambda: (wp('fx_cutter') + Vector((0.40, -0.36, 0.06)), wp('fx_cutter') + Vector((-0.03, 0.06, 0.05)), 44), work_pose, (-60, 30)),
    'hover': (lambda: (Vector((1.9, -2.3, 1.7)), HOVER + Vector((0, 0, -0.03)), 34), None, (-35, 18)),
    'below': (lambda: (HOVER + Vector((0.55, -0.62, -0.40)), HOVER + Vector((0.02, 0.0, -0.06)), 44), None, (-40, 35)),
    'wide10': (lambda: (Vector((-6.5, 10.5, 1.7)), Vector((-6.5, 0.0, 0.25)), 80), None, (100, 14)),
    'wide25': (lambda: (Vector((-6.5, 25.0, 1.7)), Vector((-6.5, 0.0, 0.25)), 48), None, (100, 14)),
    'main': (panel_view, None, (225, 32)),
    'salt10': (bus10, None, (225, 32)),
    'main_open': (panel_view, open_bay, (225, 32)),
    'crust': (lambda: face_view(7, dist=0.85, h=0.60, fov=46), None, (70, 22)),
}
todo = list(globals().get('LIVE_VIEWS') or VIEWS)
root.location = HOVER if D_ID == 'svetlyak' else Vector((0, 0, 0))
setup_cycles(1920, 1080, samples=SAMPLES, bounces=5)
sc.cycles.adaptive_threshold = 0.04
log = open(os.path.join(ROOT, 'shots', '_tmp', 'live_shots.log'), 'a', encoding='utf-8')
state = {'t0': 0.0, 'cur': None}


def _tick():
    if bpy.app.is_job_running('RENDER'):
        return 3.0
    if state['cur']:
        log.write('RENDERED %s %.0f s\n' % (state['cur'], time.time() - state['t0']))
        log.flush()
        state['cur'] = None
    reset()
    if not todo:
        open(done_file, 'w').write('done')
        log.write('LIVE_DONE\n')
        log.flush()
        return None
    v = todo.pop(0)
    fn, prep, (az, el) = VIEWS[v]
    if prep:
        prep()
    pos, tgt, fov = fn()
    old = bpy.data.objects.get('cam_d')
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    cam = camera('cam_d', pos, tgt - pos, fov=fov, clip=(0.01, 9000))
    a, e = math.radians(az), math.radians(el)
    to_sun = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    the_sun.rotation_euler = (-to_sun).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    sc.render.filepath = os.path.join(ROOT, 'shots', 'D_%s_%s.png' % (D_ID, v))
    state['cur'], state['t0'] = v, time.time()
    if bpy.app.background:
        bpy.ops.render.render(write_still=True)
        return 0.1
    w = bpy.context.window_manager.windows[0]
    try:
        with bpy.context.temp_override(window=w, screen=w.screen):
            bpy.ops.render.render('INVOKE_DEFAULT', write_still=True)
    except Exception as ex:
        log.write('ERROR %s %s\n' % (v, ex))
        log.flush()
    return 5.0


if bpy.app.background:
    while _tick() is not None:
        pass
else:
    bpy.app.timers.register(_tick, first_interval=1.0)
print('очередь рендеров запущена:', todo)
