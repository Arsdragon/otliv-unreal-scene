# shots_a.py — чистовые рендеры этапа A (серая блок-модель «Чайки») в Cycles:
#   blender -b src/chaika_blockA.blend --python tools/shots_a.py -- [persp side front top rear eye_fwd eye_up eye_down pano]
# Кадры кладутся в shots/_tmp/A_*.png, листы клеит tools/sheet_a.py (обычный Python + Pillow).
import bpy, os, sys, math, json, time
from mathutils import Vector

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
exec(open(os.path.join(TOOLS, 'shots_kit.py'), encoding='utf-8').read())
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
views = args or ['persp', 'side', 'front', 'top', 'rear', 'eye_fwd', 'eye_up', 'eye_down', 'pano']
OUT = os.path.join(ROOT, 'shots', '_tmp')
os.makedirs(OUT, exist_ok=True)

eye = bpy.data.objects['eye_pilot'].location.copy()
ORTHO = 17.0                  # метров по ширине кадра в ортовидах
TW, TH = 1600, 1000
meta = {'ortho_scale': ORTHO, 'tile': [TW, TH], 'side_center': [0.0, 2.6], 'front_center': [0.0, 2.6],
        'top_center': [0.0, 0.0]}
json.dump(meta, open(os.path.join(OUT, 'A_meta.json'), 'w'))

sky_world(0.9)
sun_ext = sun(-38, 40, 3.0)
ground = plane('stage_ground', 0.0, 6000, simple_mat('stage_ground', (0.46, 0.45, 0.43), 0.8))
water = plane('stage_water', 0.45, 6000, water_mat())


def pitch_dir(deg):
    return Vector((0, -math.cos(math.radians(deg)), math.sin(math.radians(deg))))


def aim_sun(az, el):
    """Солнце светит со стороны азимута az (0° — со стороны носа, 90° — с правого борта) с высоты el."""
    a, e = math.radians(az), math.radians(el)
    to_sun = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    sun_ext.rotation_euler = (-to_sun).to_track_quat('-Z', 'Y').to_euler()


def stage(on):
    ground.hide_render = not on
    water.hide_render = not on


for v in views:
    t0 = time.time()
    if v in ('side', 'front', 'top'):
        setup_cycles(TW, TH, samples=40, transparent=True)
        stage(False)
        aim_sun(-38, 40)
        if v == 'side':
            cam = camera(v, (40, 0, 2.6), (-1, 0, 0), ortho=ORTHO)
        elif v == 'front':
            cam = camera(v, (0, -40, 2.6), (0, 1, 0), ortho=ORTHO)
        else:
            cam = camera(v, (0, 0, 40), (0, 0, -1), ortho=ORTHO)
            cam.rotation_euler = (0, 0, math.radians(90))
    elif v == 'persp':
        setup_cycles(TW, TH, samples=56)
        stage(True)
        aim_sun(-38, 40)
        p = Vector((-16.0, -15.0, 3.6))
        cam = camera(v, p, Vector((0.2, 0.3, 2.2)) - p, fov=46)
    elif v == 'rear':
        setup_cycles(TW, TH, samples=56)
        stage(True)
        aim_sun(150, 34)
        p = Vector((7.5, 16.0, 1.7))
        cam = camera(v, p, Vector((0.0, 1.5, 2.3)) - p, fov=52)
    elif v.startswith('eye'):
        setup_cycles(1920, 1080, samples=26, bounces=4)
        stage(True)
        if 'cabin_fill' not in bpy.data.objects:
            L = bpy.data.lights.new('cabin_fill', 'AREA')
            L.energy, L.size = 10.0, 0.7
            lo = bpy.data.objects.new('cabin_fill', L)
            bpy.context.scene.collection.objects.link(lo)
            lo.location = (0, -4.35, 3.30)
            lo.rotation_euler = look_rot((0, -0.75, -0.66))
        aim_sun(32, 30)
        d = {'eye_fwd': 0, 'eye_up': 40, 'eye_down': -25}[v]
        cam = camera(v, eye, pitch_dir(d), fov=90, clip=(0.02, 8000))
    elif v == 'pano':
        # карта обзора: всё непрозрачное — чёрное, стёкла — прозрачные, снаружи — белое
        setup_cycles(2048, 1024, samples=8)
        bpy.context.scene.cycles.use_denoising = False
        bpy.context.scene.view_settings.view_transform = 'Standard'
        stage(False)
        sun_ext.hide_render = True
        w = bpy.data.worlds.new('white')
        w.use_nodes = True
        w.node_tree.nodes.clear()
        wb = w.node_tree.nodes.new('ShaderNodeBackground')
        wo = w.node_tree.nodes.new('ShaderNodeOutputWorld')
        wb.inputs['Color'].default_value = (1, 1, 1, 1)
        wb.inputs['Strength'].default_value = 1.0
        w.node_tree.links.new(wb.outputs[0], wo.inputs['Surface'])
        for o in bpy.data.objects:
            if o.type == 'LIGHT':
                o.hide_render = True
        bpy.context.scene.world = w
        for m in bpy.data.materials:
            if not m.use_nodes:
                continue
            nt = m.node_tree
            out = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'), None)
            if out is None:
                continue
            if m.name == 'glass':
                sh = nt.nodes.new('ShaderNodeBsdfTransparent')
                sh.inputs['Color'].default_value = (1, 1, 1, 1)
            else:
                sh = nt.nodes.new('ShaderNodeEmission')
                sh.inputs['Color'].default_value = (0, 0, 0, 1)
            nt.links.new(sh.outputs[0], out.inputs['Surface'])
        cam = camera(v, eye, (0, -1, 0), clip=(0.02, 8000))
        cam.data.type = 'PANO'
        cam.data.panorama_type = 'EQUIRECTANGULAR'
    else:
        continue
    render(cam, os.path.join(OUT, '%s_%s.png' % (os.environ.get('SHOTPREFIX', 'A'), v)))
    print('TIME %s %.0f s' % (v, time.time() - t0))
