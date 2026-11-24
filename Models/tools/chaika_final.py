# chaika_final.py — материалы с экспортными текстурами, экспорт glb / fbx и manifest.json для chaika_ext.
#   bash tools/bl.sh src/chaika_ext.blend tools/chaika_final.py   ->  src/chaika_ext_final.blend, export/chaika_ext/*
import bpy, bmesh, math, os, sys, json
from mathutils import Vector, Matrix, Euler

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
for _f in ('kit.py', 'chaika_shape.py'):
    exec(open(os.path.join(TOOLS, _f), encoding='utf-8').read())
EXP = os.path.join(ROOT, 'export', 'chaika_ext')
R = math.radians
NO_EXPORT = '--noexport' in sys.argv


def tex_mat(name, prefix):
    """Материал PBR на трёх экспортных картах: BaseColor (sRGB), Normal (OpenGL, +Y), ORM (R — AO, G — шерох., B — металл)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')

    def img(suffix, cs):
        n = nt.nodes.new('ShaderNodeTexImage')
        n.image = bpy.data.images.load(os.path.join(EXP, prefix + suffix + '.png'), check_existing=True)
        n.image.colorspace_settings.name = cs
        return n
    bc, nm, orm = img('_BaseColor', 'sRGB'), img('_Normal', 'Non-Color'), img('_ORM', 'Non-Color')
    nt.links.new(bc.outputs['Color'], b.inputs['Base Color'])
    sep = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(orm.outputs['Color'], sep.inputs['Color'])
    nt.links.new(sep.outputs['Green'], b.inputs['Roughness'])
    nt.links.new(sep.outputs['Blue'], b.inputs['Metallic'])
    nmap = nt.nodes.new('ShaderNodeNormalMap')
    nt.links.new(nm.outputs['Color'], nmap.inputs['Color'])
    nt.links.new(nmap.outputs['Normal'], b.inputs['Normal'])
    g = bpy.data.node_groups.get('glTF Material Output')          # чтобы экспортёр glTF записал карту затенения
    if g is None:
        g = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
        g.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
    gn = nt.nodes.new('ShaderNodeGroup')
    gn.node_tree = g
    nt.links.new(sep.outputs['Red'], gn.inputs[0])
    if os.path.exists(os.path.join(EXP, prefix + '_Emissive.png')):     # подсветка надписей (есть только у кабины)
        em = img('_Emissive', 'sRGB')
        nt.links.new(em.outputs['Color'], b.inputs['Emission Color'])
        b.inputs['Emission Strength'].default_value = 1.0
    return m


def make_materials():
    mats = {'A': tex_mat('chaika_hull', 'T_ChaikaHull'), 'B': tex_mat('chaika_parts', 'T_ChaikaParts'),
            'C': tex_mat('chaika_gear', 'T_ChaikaGear'),
            'nozzle': tex_mat('nozzle', 'T_ChaikaParts')}
    g = bpy.data.materials.new('glass_ext')
    g.use_nodes = True
    b = next(n for n in g.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = (0.015, 0.022, 0.028, 1)
    b.inputs['Roughness'].default_value = 0.02
    b.inputs['IOR'].default_value = 1.9
    b.inputs['Alpha'].default_value = 0.34
    try:
        g.surface_render_method = 'BLENDED'
    except Exception:
        pass
    mats['glass'] = g
    e = bpy.data.materials.new('emissive_ext')
    e.use_nodes = True
    b = next(n for n in e.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = (0.9, 0.85, 0.7, 1)
    b.inputs['Emission Color'].default_value = (1.0, 0.90, 0.70, 1)
    b.inputs['Emission Strength'].default_value = 5.0
    mats['emissive'] = e
    return mats


def assign(objs, mats):
    for o in objs:
        src = bpy.data.objects.get(o.get('chart_of') or o.name)
        at = json.loads(src['chart'])['atlas'] if src and src.get('chart') else 'B'
        me = o.data
        old = [m.name if m else '' for m in me.materials]
        target = []
        for nm in old:
            key = 'glass' if nm == 'glass' else 'emissive' if nm == 'emissive' else 'nozzle' if nm == 'm_nozzle' else at
            target.append(mats[key])
        new = []
        for t in target:
            if t not in new:
                new.append(t)
        idx = [new.index(t) for t in target]
        pm = [idx[p.material_index] for p in me.polygons]
        me.materials.clear()
        for t in new:
            me.materials.append(t)
        me.polygons.foreach_set('material_index', pm)
        me.update()


MOVING = {
    'ext_nacelle_R': dict(axis='X', range_deg=[-95, 0], flight=0, landed=-90, note='мотогондола: 0° — полётное положение (сопло назад), −90° — посадочное (сопло вниз)'),
    'ext_nacelle_L': dict(axis='X', range_deg=[-95, 0], flight=0, landed=-90, note='как правая'),
    'ext_nacelle_nozzle_R': dict(axis='X,Z', range_deg=[-8, 8], note='сопло мотогондолы, качание в шарнире'),
    'ext_nacelle_nozzle_L': dict(axis='X,Z', range_deg=[-8, 8], note='как правое'),
    'ext_bell_R': dict(axis='X,Z', range_deg=[-6, 6], note='сопло кормового двигателя, качание вокруг опорной точки'),
    'ext_bell_L': dict(axis='X,Z', range_deg=[-6, 6], note='как правое'),
    'ext_ramp': dict(axis='X', range_deg=[round(RAMP_OPEN, 2), round(RAMP_CLOSED, 2)], closed=round(RAMP_CLOSED, 2),
                     open=round(RAMP_OPEN, 2), note='трап: петля у задней стенки шлюза; закрыт — прижат к днищу хвоста, открыт — конец на грунте'),
    'ext_hatch': dict(axis='Z', range_deg=[0, 100], closed=0, open=100,
                      note='люк шлюза: петли на правом борту (−X), открывается наружу в нишу трапа; открывать при опущенном трапе'),
}
MARKS = {'eye_pilot': 'глаза пилота (для сверки с кабиной)', 'fx_nozzle': 'срез сопла мотогондолы, струя вдоль +Y метки',
         'fx_intake': 'воздухозаборник мотогондолы', 'fx_bell': 'срез сопла кормового двигателя, струя вдоль +Y',
         'fx_splash': 'центр лыжи на грунте: брызги и круги на воде', 'light_landing': 'посадочная фара, луч вдоль +Y метки',
         'ramp_tip': 'конец трапа', 'hatch_center': 'центр проёма люка шлюза'}


def export(objs, root):
    refs = {n: bpy.data.objects[n] for n in MOVING}
    landed = {n: tuple(o.rotation_euler) for n, o in refs.items()}
    for n in ('ext_nacelle_R', 'ext_nacelle_L'):                    # поза экспорта: полёт, трап и люк закрыты
        refs[n].rotation_euler = (0, 0, 0)
    refs['ext_ramp'].rotation_euler = (R(RAMP_CLOSED), 0, 0)
    bpy.context.view_layer.update()
    allo = [o for o in bpy.data.collections['chaika_ext'].all_objects]
    bpy.ops.object.select_all(action='DESELECT')
    for o in allo:
        o.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(filepath=os.path.join(EXP, 'chaika_ext.glb'), export_format='GLB', use_selection=True,
                              export_yup=True, export_apply=False, export_texcoords=True, export_normals=True,
                              export_tangents=False, export_materials='EXPORT', export_image_format='AUTO',
                              export_cameras=False, export_lights=False, export_extras=False, export_animations=False)
    bpy.ops.export_scene.fbx(filepath=os.path.join(EXP, 'chaika_ext.fbx'), use_selection=True, object_types={'EMPTY', 'MESH'},
                             apply_scale_options='FBX_SCALE_ALL', mesh_smooth_type='FACE', use_tspace=False, bake_anim=False,
                             path_mode='AUTO', embed_textures=False, add_leaf_bones=False)
    parts, marks = [], []
    for o in allo:
        d = dict(name=o.name, parent=o.parent.name if o.parent else None,
                 pivot=[round(v, 4) for v in o.matrix_world.translation], local=[round(v, 4) for v in o.location])
        if o.type == 'MESH':
            d['triangles'] = sum(len(p.vertices) - 2 for p in o.data.polygons)
            d['materials'] = [m.name for m in o.data.materials]
            if o.name in MOVING:
                d['moving'] = MOVING[o.name]
            parts.append(d)
        elif o is not root:
            d['purpose'] = next((v for k, v in MARKS.items() if o.name.startswith(k)), '')
            marks.append(d)
    pts = [o.matrix_world @ Vector(c) for o in allo if o.type == 'MESH' for c in o.bound_box]
    lo = [round(min(p[i] for p in pts), 3) for i in range(3)]
    hi = [round(max(p[i] for p in pts), 3) for i in range(3)]
    man = dict(
        id='chaika_ext', title='Посадочный модуль «Чайка», снаружи', units='метры',
        axes='Z вверх, нос по −Y; ВНИМАНИЕ: +X — левый борт, −X — правый (оси Blender). Суффиксы _L / _R в именах — настоящие борта. '
             'В glb оси пересчитаны экспортёром в Y вверх',
        origin='центр под опорами на уровне грунта',
        export_pose='мотогондолы в полётном положении (0°), трап и люк закрыты; посадочные значения — в parts[].moving',
        bbox_export_pose=dict(min=lo, max=hi), size_landed=dict(length=14.0, span=10.0, height=4.5, belly_clearance=1.35, water=0.45),
        triangles=sum(p['triangles'] for p in parts),
        files=dict(glb='chaika_ext.glb', fbx='chaika_ext.fbx',
                   textures=['T_ChaikaHull_BaseColor.png', 'T_ChaikaHull_Normal.png', 'T_ChaikaHull_ORM.png',
                             'T_ChaikaParts_BaseColor.png', 'T_ChaikaParts_Normal.png', 'T_ChaikaParts_ORM.png',
                             'T_ChaikaGear_BaseColor.png', 'T_ChaikaGear_Normal.png', 'T_ChaikaGear_ORM.png']),
        texture_notes='4096×4096. BaseColor — sRGB. Normal — касательное пространство, соглашение OpenGL (+Y): при ручном импорте PNG '
                      'в Unreal включить Flip Green Channel. ORM — линейная: R — затенение (AO), G — шероховатость, B — металл.',
        material_slots=[dict(name='chaika_hull', textures='T_ChaikaHull_*', note='корпус, переплёты фонаря, кормовые обтекатели, кили'),
                        dict(name='chaika_parts', textures='T_ChaikaParts_*', note='крыло, мотогондолы, мелкие детали корпуса'),
                        dict(name='chaika_gear', textures='T_ChaikaGear_*', note='опоры с лыжами, трап, люк шлюза, ниша трапа (крупные планы у земли)'),
                        dict(name='nozzle', textures='T_ChaikaParts_*', note='сопла: отдельный слот под свечение и нагрев'),
                        dict(name='glass', textures=None, note='стёкла фонаря и иллюминатор люка'),
                        dict(name='emissive', textures=None, note='фары, маяки, светильники ниши трапа, бортовые огни')],
        notes=['Зеркальные части (L) делят участок атласа с правыми (R): развёртка отражена, касательные считать по MikkTSpace.',
               'ext_cockpit_proxy — тёмная заглушка кабины за стёклами; скрыть, когда загружена детальная кабина chaika_cockpit.',
               'Опоры неподвижны (посадочное положение). Вода в сцене — на высоте 0,45 м от начала координат.'],
        parts=parts, markers=marks)
    json.dump(man, open(os.path.join(EXP, 'manifest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for n, r in landed.items():
        refs[n].rotation_euler = r
    bpy.context.view_layer.update()
    return man


if __name__ == '__main__':
    objs = [o for o in bpy.data.collections['chaika_ext'].all_objects if o.type == 'MESH']
    root = bpy.data.objects['chaika_ext']
    assign(objs, make_materials())
    for m in list(bpy.data.materials):
        if m.users == 0:
            bpy.data.materials.remove(m)
    for m in bpy.data.materials:
        if m.name.startswith('glass_ext'):
            m.name = 'glass'
        if m.name.startswith('emissive_ext'):
            m.name = 'emissive'
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'src', 'chaika_ext_final.blend'))
    print('SAVED chaika_ext_final.blend; материалы:', sorted({m.name for o in objs for m in o.data.materials}))
    if not NO_EXPORT:
        man = export(objs, root)
        bpy.ops.wm.save_mainfile()
        for f in ('chaika_ext.glb', 'chaika_ext.fbx', 'manifest.json'):
            print('EXPORT %s %.1f МБ' % (f, os.path.getsize(os.path.join(EXP, f)) / 1e6))
        print('треугольников %d, частей %d, меток %d' % (man['triangles'], len(man['parts']), len(man['markers'])))
