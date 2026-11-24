# live_quick.py — быстрые проверочные виды (Workbench) коллекции в открытом Blender:
#   bash tools/live.sh @code "Q_COLL='svetlyak'; Q_VIEWS=['iso','rear','side','bottom']; exec(open(r'C:\UnrealScenes\Models\tools\live_quick.py', encoding='utf-8').read())"
# Кадры: shots/_tmp/q_<коллекция>_<вид>.png и лист shots/_tmp/q_<коллекция>.png (2 × 2).
import bpy, math, os
from mathutils import Vector

exec(open(r'C:\UnrealScenes\Models\tools\shots_kit.py', encoding='utf-8').read())
OUT = r'C:\UnrealScenes\Models\shots\_tmp'
coll = bpy.data.collections[Q_COLL]
views = globals().get('Q_VIEWS') or ['iso', 'rear', 'side', 'bottom']
size = globals().get('Q_SIZE', 900)
DIRS = {'iso': (-0.62, -0.62, 0.48), 'rear': (0.55, 0.70, 0.45), 'side': (-1, 0, 0.05), 'front': (0, -1, 0.08),
        'top': (0.001, 0.001, 1), 'bottom': (-0.35, -0.45, -0.82), 'low': (-0.7, -0.6, 0.12)}
objs = [o for o in coll.all_objects if o.type == 'MESH']
pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
lo = Vector([min(p[i] for p in pts) for i in range(3)])
hi = Vector([max(p[i] for p in pts) for i in range(3)])
c = (lo + hi) / 2
rad = (hi - lo).length / 2
setup_workbench(size, size)
sc = bpy.context.scene
sc.display.shading.color_type = globals().get('Q_COLOR', 'MATERIAL')
files = []
for v in views:
    d = Vector(DIRS[v]).normalized()
    cam = camera('q_' + v, c + d * rad * 3.2, -d, fov=38, clip=(rad * 0.05, rad * 20))
    p = os.path.join(OUT, 'q_%s_%s.png' % (Q_COLL, v))
    sc.camera = cam
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    files.append(p)
    bpy.data.objects.remove(cam, do_unlink=True)
print('quick:', files)
