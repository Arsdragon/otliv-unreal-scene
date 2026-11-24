# shots_quick.py — быстрые проверочные снимки Workbench из сохранённого .blend:
#   blender -b src/<файл>.blend --python tools/shots_quick.py -- <префикс> [вид ...]
# виды: iso side front top rear eye_fwd eye_up eye_down plan section
import bpy, os, sys, math
from mathutils import Vector

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
exec(open(os.path.join(TOOLS, 'shots_kit.py'), encoding='utf-8').read())
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
prefix = args[0] if args else 'q'
views = args[1:] or ['iso', 'side', 'front', 'top', 'rear', 'eye_fwd', 'eye_up', 'eye_down', 'plan', 'section']
OUT = os.path.join(ROOT, 'shots', '_tmp')
os.makedirs(OUT, exist_ok=True)

g = bpy.data.materials.get('glass')
if g:
    g.diffuse_color = (0.55, 0.75, 0.85, 0.22)
eye = bpy.data.objects['eye_pilot'].location.copy()
C = Vector((0, 0, 2.2))


def pitch_dir(deg):
    return Vector((0, -math.cos(math.radians(deg)), math.sin(math.radians(deg))))


for v in views:
    setup_workbench(1400, 800)
    if v == 'iso':
        cam = camera(v, (-13, -17, 7.5), C - Vector((-13, -17, 7.5)), fov=38)
    elif v == 'rear':
        cam = camera(v, (9, 17, 4.0), Vector((0, 1.5, 1.8)) - Vector((9, 17, 4.0)), fov=38)
    elif v == 'side':
        cam = camera(v, (-40, 0, 2.3), (1, 0, 0), ortho=16.5)
    elif v == 'front':
        cam = camera(v, (0, -40, 2.3), (0, 1, 0), ortho=16.5)
    elif v == 'top':
        cam = camera(v, (0, 0, 40), (0, 0, -1), ortho=16.5)
        cam.rotation_euler = (0, 0, math.radians(90))
    elif v.startswith('eye'):
        setup_workbench(1920, 1080)
        d = {'eye_fwd': 0, 'eye_up': 40, 'eye_down': -25}[v]
        cam = camera(v, eye, pitch_dir(d), fov=90, clip=(0.02, 500))
    elif v == 'plan':
        cam = camera(v, (0, -2.3, 30), (0, 0, -1), ortho=10.5, clip=(30 - 3.05, 100))
        cam.rotation_euler = (0, 0, math.radians(90))
    elif v == 'section':
        cam = camera(v, (30, -2.3, 2.5), (-1, 0, 0), ortho=10.5, clip=(30 - 0.02, 100))
    render(cam, os.path.join(OUT, '%s_%s.png' % (prefix, v)))
