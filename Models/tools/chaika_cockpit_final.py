# chaika_cockpit_final.py — материалы на экспортных текстурах, экспорт glb / fbx и manifest.json для chaika_cockpit.
# В открытом Blender: python tools/bmcp.py "LIVE_SCRIPT='chaika_cockpit_final.py'; exec(open(r'C:\UnrealScenes\Models\tools\live_run.py', encoding='utf-8').read())" 900
import bpy, bmesh, math, os, sys, json
from mathutils import Vector, Matrix, Euler

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
_lib = {'__name__': 'chaika_final_lib', '__file__': os.path.join(TOOLS, 'chaika_final.py')}
exec(compile(open(_lib['__file__'], encoding='utf-8').read(), _lib['__file__'], 'exec'), _lib)
EXP = os.path.join(ROOT, 'export', 'chaika_cockpit')
_lib['EXP'] = EXP                                           # tex_mat берёт текстуры из папки кабины
R = math.radians
STATS = json.load(open(os.path.join(EXP, 'build_stats.json'), encoding='utf-8'))


def simple(name, base, rough=0.5, alpha=1.0, emis=None, emis_img=None, strength=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = (*base, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Alpha'].default_value = alpha
    if alpha < 1:
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:
            pass
    if emis_img:
        t = nt.nodes.new('ShaderNodeTexImage')
        t.image = bpy.data.images.load(emis_img, check_existing=True)
        nt.links.new(t.outputs['Color'], b.inputs['Emission Color'])
        b.inputs['Emission Strength'].default_value = strength
    elif emis:
        b.inputs['Emission Color'].default_value = (*emis, 1)
        b.inputs['Emission Strength'].default_value = strength
    return m


def make_materials():
    for m in list(bpy.data.materials):                       # следы прерванного прошлого запуска
        if m.users == 0:
            bpy.data.materials.remove(m)
    mats = {'A': _lib['tex_mat']('cockpit_front', 'T_CockpitFront'), 'B': _lib['tex_mat']('cockpit_rear', 'T_CockpitRear'),
            'glass': simple('glass_ck', (0.02, 0.03, 0.035), 0.02, alpha=0.14),
            'emissive': simple('emissive_ck', (0.9, 0.86, 0.74), 0.4, emis=(1.0, 0.92, 0.78), strength=14.0)}
    next(n for n in mats['glass'].node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['IOR'].default_value = 1.8
    for k in range(1, 7):
        mats['screen_%d' % k] = simple('screen_ck_%d' % k, (0.01, 0.012, 0.015), 0.18,
                                       emis_img=os.path.join(EXP, 'T_Screen_%d.png' % k), strength=1.3)
    return mats


def assign(objs, mats):
    for o in objs:
        src = bpy.data.objects.get(o.get('chart_of') or o.name)
        at = json.loads(src['chart'])['atlas'] if src and src.get('chart') else 'A'
        me = o.data
        target = [mats[nm if nm in mats else at] for nm in [m.name if m else '' for m in me.materials]]
        new = []
        for t in target:
            if t not in new:
                new.append(t)
        pm = [new.index(target[p.material_index]) for p in me.polygons]
        me.materials.clear()
        for t in new:
            me.materials.append(t)
        me.polygons.foreach_set('material_index', pm)
        me.update()


MOVING = {
    'ck_stick': dict(axis='X,Y', range_deg=[-18, 18], note='боковая ручка управления (правая консоль, −X): тангаж вокруг X, крен вокруг Y'),
    'ck_throttle': dict(axis='X', range_deg=[-35, 20], note='РУД (левая консоль, +X): поворот вокруг поперечной оси; 0° — малый газ, вперёд — увеличение'),
    'ck_door': dict(axis='Z', range_deg=[-100, 0], closed=0, open=-100, note='дверь кабина — шлюз: петли на левом борту (+X), открывается в шлюз'),
}
MARKS = {'eye_pilot': 'глаза пилота: точка камеры в кабине', 'cam_airlock': 'глаза стоящего в шлюзе человека',
         'drone_cradle': 'центр ложемента дрона «Светляк» (правый борт шлюза)', 'door_center': 'центр проёма двери в шлюз',
         'hatch_center': 'центр проёма наружного люка', 'light_': 'место светильника (в модели — светящаяся полоса слота emissive)'}


def export(objs, root):
    allo = list(bpy.data.collections['chaika_cockpit'].all_objects)
    bpy.ops.object.select_all(action='DESELECT')
    for o in allo:
        o.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(filepath=os.path.join(EXP, 'chaika_cockpit.glb'), export_format='GLB', use_selection=True,
                              export_yup=True, export_apply=False, export_texcoords=True, export_normals=True,
                              export_tangents=False, export_materials='EXPORT', export_image_format='AUTO',
                              export_cameras=False, export_lights=False, export_extras=False, export_animations=False)
    bpy.ops.export_scene.fbx(filepath=os.path.join(EXP, 'chaika_cockpit.fbx'), use_selection=True, object_types={'EMPTY', 'MESH'},
                             apply_scale_options='FBX_SCALE_ALL', mesh_smooth_type='FACE', use_tspace=False, bake_anim=False,
                             path_mode='AUTO', embed_textures=False, add_leaf_bones=False)
    parts, marks = [], []
    for o in allo:
        d = dict(name=o.name, parent=o.parent.name if o.parent else None, pivot=[round(v, 4) for v in o.matrix_world.translation])
        if o.type == 'MESH':
            d['triangles'] = sum(len(p.vertices) - 2 for p in o.data.polygons)
            d['materials'] = [m.name for m in o.data.materials]
            if o.name in MOVING:
                d['moving'] = MOVING[o.name]
            parts.append(d)
        elif o is not root:
            d['purpose'] = next((v for k, v in MARKS.items() if o.name.startswith(k)), '')
            marks.append(d)
    man = dict(
        id='chaika_cockpit', title='Кабина и шлюз «Чайки» изнутри', units='метры',
        axes='Z вверх, нос по −Y; ВНИМАНИЕ: +X — левый борт (слева от пилота), −X — правый. В glb оси пересчитаны экспортёром в Y вверх',
        origin='то же начало координат, что у chaika_ext: центр под опорами на уровне грунта (модели совмещаются без сдвига)',
        eye_pilot=[0.0, -5.20, 2.78], floor_z=1.66,
        triangles=sum(p['triangles'] for p in parts),
        files=dict(glb='chaika_cockpit.glb', fbx='chaika_cockpit.fbx',
                   textures=['T_CockpitFront_BaseColor.png', 'T_CockpitFront_Normal.png', 'T_CockpitFront_ORM.png',
                             'T_CockpitRear_BaseColor.png', 'T_CockpitRear_Normal.png', 'T_CockpitRear_ORM.png'],
                   screen_placeholders=['T_Screen_%d.png' % k for k in range(1, 7)],
                   emissive=[f for f in ('T_CockpitFront_Emissive.png',) if os.path.exists(os.path.join(EXP, f))]),
        texture_notes='4096×4096. BaseColor — sRGB. Normal — OpenGL (+Y): при ручном импорте PNG в Unreal включить Flip Green Channel. '
                      'ORM — линейная: R — затенение (белое, не запекалось), G — шероховатость, B — металл. '
                      'T_Screen_*.png — заглушки 1280×800 для экранов, в сцене заменяются живым интерфейсом. '
                      'T_CockpitFront_Emissive.png (sRGB) — тёплая неяркая подсветка надписей верхнего пульта: Emissive слота cockpit_front.',
        material_slots=[dict(name='cockpit_front', textures='T_CockpitFront_*', note='место пилота: панель, консоли, кресло, отделка фонаря, обшивка кабины'),
                        dict(name='cockpit_rear', textures='T_CockpitRear_*', note='задняя часть кабины, переборка с дверью, шлюз'),
                        dict(name='glass', textures=None, note='внутренние стёкла фонаря, иллюминатор двери'),
                        dict(name='emissive', textures=None, note='потолочные светильники, табло верхнего пульта, индикаторы блоков')] +
                       [dict(name=s['slot'], textures='T_Screen_%s.png (заглушка)' % s['slot'][-1], note='экран «%s», %d × %d мм, соотношение %.2f, развёртка 0…1'
                             % (s['title'], round(s['width'] * 1000), round(s['height'] * 1000), s['aspect'])) for s in sorted(STATS['screens'], key=lambda s: s['slot'])],
        screens=sorted(STATS['screens'], key=lambda s: s['slot']),
        notes=['Экраны 1…5 на приборной панели идут слева направо для пилота; экран 6 — пульт шлюза (правый борт, у люка).',
               'ck_glass — внутренние стёкла (на 2 см внутрь от наружных стёкол chaika_ext); при совместной загрузке одну из пар можно скрыть.',
               'ck_hatch_proxy — заглушка наружного люка изнутри; скрыть, когда загружена chaika_ext (там люк ext_hatch).',
               'Переплёты фонаря построены тем же кодом, что у chaika_ext (tools/chaika_shape.py), и лежат сразу за наружными.',
               'Ложемент дрона пуст: модель «Светляка» ставится в метку drone_cradle.',
               'ck_detail_L / ck_detail_R / ck_detail_roof — жгуты, поручни, сетки, короб маски, фонарь, воздуховод; ck_placards — таблички.'],
        parts=parts, markers=marks)
    json.dump(man, open(os.path.join(EXP, 'manifest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return man


if __name__ == '__main__':
    objs = [o for o in bpy.data.collections['chaika_cockpit'].all_objects if o.type == 'MESH']
    root = bpy.data.objects['chaika_cockpit']
    assign(objs, make_materials())
    for m in list(bpy.data.materials):
        if m.users == 0:
            bpy.data.materials.remove(m)
    for m in bpy.data.materials:
        for a, b in (('glass_ck', 'glass'), ('emissive_ck', 'emissive'), ('screen_ck_', 'screen_')):
            if m.name.startswith(a):
                m.name = m.name.replace(a, b)
    for lib in list(bpy.data.libraries):
        bpy.data.libraries.remove(lib)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'src', 'chaika_cockpit_final.blend'))
    print('SAVED chaika_cockpit_final.blend; материалы:', sorted({m.name for o in objs for m in o.data.materials}))
    man = export(objs, root)
    bpy.ops.wm.save_mainfile()
    for f in ('chaika_cockpit.glb', 'chaika_cockpit.fbx', 'manifest.json'):
        print('EXPORT %s %.1f МБ' % (f, os.path.getsize(os.path.join(EXP, f)) / 1e6))
    print('треугольников %d, частей %d, меток %d' % (man['triangles'], len(man['parts']), len(man['markers'])))
