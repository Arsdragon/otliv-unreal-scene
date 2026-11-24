# d_final.py — материалы на экспортных текстурах, экспорт glb / fbx и manifest.json моделей этапа D.
# В открытом Blender (модель уже собрана в сцене):
#   bash tools/live.sh @code "import os; os.environ['D_ID']='svetlyak'; LIVE_SCRIPT='d_final.py'; exec(open(r'C:\UnrealScenes\Models\tools\live_run.py', encoding='utf-8').read())" 900
import bpy, math, os, json
from mathutils import Vector

ROOT = r'C:\UnrealScenes\Models'
ID = os.environ['D_ID']
EXP = os.path.join(ROOT, 'export', ID)
LAY = json.load(open(os.path.join(EXP, 'layout.json'), encoding='utf-8'))

CFG = {
    'svetlyak': dict(
        title='Дрон-разведчик «Светляк»', tex='T_Svetlyak', main='svetlyak',
        specials={'glass': dict(base=(0.035, 0.020, 0.060), alpha=0.32, rough=0.015),
                  'emissive': dict(base=(0.75, 0.95, 0.35), emis=(0.72, 1.0, 0.22), strength=6.0),
                  'scanner': dict(base=(0.03, 0.05, 0.06), emis=(0.55, 0.85, 1.0), strength=0.4, rough=0.08)},
        origin='центр корпуса в плоскости импеллеров; низ дрона — 0,10 м ниже начала координат',
        export_pose='манипулятор сложен под днищем, голова смотрит вперёд (−Y), роторы в нуле',
        moving={
            'sv_head': dict(axis='Z (поворот), X (наклон)', range_deg=dict(yaw=[-170, 170], pitch=[-60, 30]),
                            note='сенсорная голова: объектив смотрит вдоль −Y; излучатель сканера под объективом'),
            'sv_rotor_FL': dict(axis='Z', note='ротор, вращение непрерывное; FL и RR — против часовой (вид сверху), FR и RL — по часовой'),
            'sv_rotor_FR': dict(axis='Z', note='ротор, по часовой (вид сверху)'),
            'sv_rotor_RL': dict(axis='Z', note='ротор, по часовой (вид сверху)'),
            'sv_rotor_RR': dict(axis='Z', note='ротор, против часовой (вид сверху)'),
            'sv_arm_base': dict(axis='Z', range_deg=[-90, 90], note='поворот основания манипулятора'),
            'sv_arm_upper': dict(axis='X', range_deg=[-125, 0], work=-117, note='плечо: 0 — сложено вдоль днища к корме, −117 — вперёд-вниз'),
            'sv_arm_fore': dict(axis='X', range_deg=[0, 150], work=134.5, note='локоть: 0 — сложено, 134,5 — предплечье вперёд'),
            'sv_arm_wrist': dict(axis='X', range_deg=[-60, 60], work=19.5, note='кисть: захват и резак (резак слева от захвата)'),
            'sv_finger_L': dict(axis='Z', range_deg=[0, 25], note='палец захвата: 0 — сжат, + — раскрыт'),
            'sv_finger_R': dict(axis='Z', range_deg=[-25, 0], note='палец захвата: 0 — сжат, − — раскрыт')},
        notes=['Рабочая поза манипулятора (кадр B «с резаком»): плечо −117°, локоть +134,5°, кисть +19,5°, пальцы ±15°.',
               'Фонарь (слот emissive) — тёплый жёлто-зелёный; яркость и мигание задаёт сцена.',
               'Слот scanner — окно излучателя сканера; луч — эффект сцены из метки fx_scanner (ось +Y метки — направление луча).',
               'В ложементе кабины дрон ставится в метку drone_cradle модели chaika_cockpit.']),
    'probe_wreck': dict(
        title='Обломки автоматической станции «НЕВОД-2»', tex='T_ProbeWreck', main='probe_wreck',
        sets={'A': ('probe_wreck', 'T_ProbeWreck'), 'M': ('probe_wreck_main', 'T_ProbeWreckMain')},
        set_notes={'A': 'все куски и главный блок wr_bus, кроме грани с нишей',
                   'M': 'НОВЫЙ слот (второй набор 2048) для крупного плана: грань с нишей (часть wr_bus), крышка wr_panel, накопитель wr_storage'},
        join={'wr_bus': ['wr_bus_front']},
        specials={'glass': dict(base=(0.6, 0.7, 0.75), alpha=0.3, rough=0.05),
                  'emissive_beacon': dict(base=(0.9, 0.5, 0.2), emis=(1.0, 0.42, 0.10), strength=8.0),
                  'emissive_indicator': dict(base=(0.2, 0.8, 0.3), emis=(0.25, 1.0, 0.35), strength=4.0)},
        origin='главный кусок (приборный блок) на грунте; оси модели = оси сцены (Blender): волна приходит с +X, хвост обломков — к −X',
        export_pose='крышка ниши на месте, накопитель в нише',
        moving={'wr_panel': dict(axis='свободно', note='съёмная крышка ниши 0,34 × 0,28 м на 6 винтах; наружная нормаль — ось +Y метки panel_center. '
                                                       'Дрон срезает винты и снимает крышку'),
                'wr_storage': dict(axis='сдвиг вдоль +Y метки storage_handle', range_m=[0, 0.42],
                                   note='накопитель Ø 0,12 × 0,35 м с ручкой и зелёным индикатором (слот emissive_indicator); выдвигается за ручку')},
        notes=['Поставить в сцену без поворота в точку (128,6; −153,2; 0) — пеленг 50° вправо от +X, 200 м от корабля: '
               'тогда крышка накопителя смотрит на корабль, а хвост обломков тянется по ходу прошлых волн (к −X).',
               'Все куски лежат на грунте (z = 0) и чуть утоплены; вода в сцене — 0,45 м.',
               '«Ватерлинии» (солевые пояса) нарисованы на высотах 0,62 / 0,78 / 1,02 м и у нынешнего уровня 0,45 м; ниже воды — мокрый налёт.',
               'Маяк (слот emissive_beacon, янтарный) — метка light_beacon; мигание задаёт сцена.',
               'Куски: wr_bus (главный; wr_bus_inner — его скрытые днище, полка и подложки), wr_panel и wr_storage (дочерние к нему), wr_mast_top (с маяком, лежит на кромке палубы), '
               'wr_propulsion, wr_mast_low, wr_solar_A, wr_leg_B, wr_frag_2, wr_dish, wr_frag_1, wr_solar_B1, wr_solar_B2, wr_leg_C.']),
}


def tex_mat(name, prefix):
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
    g = bpy.data.node_groups.get('glTF Material Output')
    if g is None:
        g = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
        g.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
    gn = nt.nodes.new('ShaderNodeGroup')
    gn.node_tree = g
    nt.links.new(sep.outputs['Red'], gn.inputs[0])
    return m


def plain_mat(name, base=(0.5, 0.5, 0.5), alpha=1.0, rough=0.4, emis=None, strength=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = (*base, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Alpha'].default_value = alpha
    if alpha < 1:
        b.inputs['IOR'].default_value = 1.5
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:
            pass
    if emis:
        b.inputs['Emission Color'].default_value = (*emis, 1)
        b.inputs['Emission Strength'].default_value = strength
    return m


def tex_sets(cfg):
    """Наборы текстур по атласам: {атлас: (имя слота, префикс файлов)}."""
    return cfg['sets'] if 'sets' in cfg else {'A': (cfg['main'], cfg['tex'])}


def build_materials(cfg):
    for m in list(bpy.data.materials):
        if m.users == 0:
            bpy.data.materials.remove(m)
    mats = {'_main_' + at: tex_mat(nm + '_x', pre) for at, (nm, pre) in tex_sets(cfg).items()}
    for nm, d in cfg['specials'].items():
        mats[nm] = plain_mat(nm + '_x', **d)
    return mats


def assign(objs, mats):
    for o in objs:
        me = o.data
        at = json.loads(o['chart'])['atlas'] if o.get('chart') else 'A'
        target = [mats.get(m.name if m else '', mats.get('_main_' + at, mats['_main_A'])) for m in me.materials]
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


def export(cfg, root):
    allo = list(bpy.data.collections[ID].all_objects)
    bpy.ops.object.select_all(action='DESELECT')
    for o in allo:
        o.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(filepath=os.path.join(EXP, ID + '.glb'), export_format='GLB', use_selection=True, export_yup=True,
                              export_apply=False, export_texcoords=True, export_normals=True, export_tangents=False,
                              export_materials='EXPORT', export_image_format='AUTO', export_cameras=False, export_lights=False,
                              export_extras=False, export_animations=False)
    bpy.ops.export_scene.fbx(filepath=os.path.join(EXP, ID + '.fbx'), use_selection=True, object_types={'EMPTY', 'MESH'},
                             apply_scale_options='FBX_SCALE_ALL', mesh_smooth_type='FACE', use_tspace=False, bake_anim=False,
                             path_mode='AUTO', embed_textures=False, add_leaf_bones=False)
    parts, marks = [], []
    for o in allo:
        d = dict(name=o.name, parent=o.parent.name if o.parent else None, pivot=[round(v, 4) for v in o.matrix_world.translation])
        if o.type == 'MESH':
            d['triangles'] = sum(len(p.vertices) - 2 for p in o.data.polygons)
            d['materials'] = [m.name for m in o.data.materials]
            if o.name in cfg['moving']:
                d['moving'] = cfg['moving'][o.name]
            parts.append(d)
        elif o is not root:
            d['direction_+Y'] = [round(v, 3) for v in (o.matrix_world.to_3x3() @ Vector((0, 1, 0))).normalized()]
            marks.append(d)
    pts = [o.matrix_world @ Vector(c) for o in allo if o.type == 'MESH' for c in o.bound_box]
    lo = [round(min(p[i] for p in pts), 3) for i in range(3)]
    hi = [round(max(p[i] for p in pts), 3) for i in range(3)]
    texs = [pre + s + '.png' for at, (nm, pre) in sorted(tex_sets(cfg).items()) for s in ('_BaseColor', '_Normal', '_ORM')]
    man = dict(id=ID, title=cfg['title'], units='метры',
               axes='Z вверх, нос по −Y; +X — левый борт (оси Blender). В glb оси пересчитаны экспортёром в Y вверх',
               origin=cfg['origin'], export_pose=cfg['export_pose'], bbox=dict(min=lo, max=hi),
               triangles=sum(p['triangles'] for p in parts),
               files=dict(glb=ID + '.glb', fbx=ID + '.fbx', textures=texs),
               texture_notes='2048×2048. BaseColor — sRGB. Normal — OpenGL (+Y): при ручном импорте PNG в Unreal включить Flip Green '
                             'Channel. ORM — линейная: R — затенение (запечено), G — шероховатость, B — металл.',
               material_slots=[dict(name=nm, textures=pre + '_*', note=cfg.get('set_notes', {}).get(at, 'вся модель'))
                               for at, (nm, pre) in sorted(tex_sets(cfg).items())] +
                              [dict(name=k, textures=None, note=json.dumps(v, ensure_ascii=False)) for k, v in cfg['specials'].items()],
               notes=cfg['notes'], parts=parts, markers=marks)
    man.update(cfg.get('extra', {}))
    json.dump(man, open(os.path.join(EXP, 'manifest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return man


if __name__ == '__main__':
    cfg = CFG[ID] if ID in CFG else json.load(open(os.path.join(EXP, 'final_cfg.json'), encoding='utf-8'))
    objs = [o for o in bpy.data.collections[ID].all_objects if o.type == 'MESH']
    root = bpy.data.objects[ID]
    assign(objs, build_materials(cfg))
    for tgt, srcs in cfg.get('join', {}).items():                 # детали, разделённые только ради плотности текстуры
        t = bpy.data.objects[tgt]
        ss = [bpy.data.objects[n] for n in srcs if n in bpy.data.objects]
        if ss:
            with bpy.context.temp_override(active_object=t, object=t, selected_objects=[t] + ss, selected_editable_objects=[t] + ss):
                bpy.ops.object.join()
    objs = [o for o in bpy.data.collections[ID].all_objects if o.type == 'MESH']
    for m in list(bpy.data.materials):
        if m.users == 0:
            bpy.data.materials.remove(m)
    for m in bpy.data.materials:
        if m.name.endswith('_x'):
            m.name = m.name[:-2]
    for lib in list(bpy.data.libraries):
        bpy.data.libraries.remove(lib)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'src', ID + '_final.blend'))
    print('SAVED %s_final.blend; материалы:' % ID, sorted({m.name for o in objs for m in o.data.materials}))
    man = export(cfg, root)
    bpy.ops.wm.save_mainfile()
    for f in (ID + '.glb', ID + '.fbx', 'manifest.json'):
        print('EXPORT %s %.1f МБ' % (f, os.path.getsize(os.path.join(EXP, f)) / 1e6))
    print('треугольников %d, частей %d, меток %d' % (man['triangles'], len(man['parts']), len(man['markers'])))
