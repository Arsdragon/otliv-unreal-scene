# giant_scene.py — газовый гигант с кольцами в открытом Blender: сфера и диск колец с развёрткой под текстуры
# export/gas_giant (их делает tools/giant_tex.py), экспорт .glb/.fbx/manifest.json и приёмочные кадры:
#   bash tools/live.sh @reset
#   bash tools/live.sh @code "LIVE_VIEWS=['view1','view2','view3']; exec(open(r'C:\UnrealScenes\Models\tools\giant_scene.py', encoding='utf-8').read())" 300
# Готовность кадров — shots/_tmp/live_done.txt. view3 пишется с прозрачным фоном в shots/_tmp/giant_v3_raw.png —
# на небо его накладывает tools/giant_comp.py.
import bpy, bmesh, os, math, json, time
from mathutils import Vector, Quaternion

TOOLS = r'C:\UnrealScenes\Models\tools'
ROOT = os.path.dirname(TOOLS)
EXP = os.path.join(ROOT, 'export', 'gas_giant')
exec(open(os.path.join(TOOLS, 'shots_kit.py'), encoding='utf-8').read())
PRM = json.load(open(os.path.join(EXP, '_params.json'), encoding='utf-8'))
R_IN, R_OUT = PRM['ring_in'], PRM['ring_out']
sc = bpy.context.scene
rad = math.radians


def img(name):
    im = bpy.data.images.load(os.path.join(EXP, name), check_existing=True)
    im.colorspace_settings.name = 'sRGB'
    return im


def node(m, kind):
    return next(n for n in m.node_tree.nodes if n.type == kind)


def tex(m, name, clamp=False):
    t = m.node_tree.nodes.new('ShaderNodeTexImage')
    t.image = img(name)
    t.extension = 'EXTEND' if clamp else 'REPEAT'
    return t


def build():
    col = bpy.data.collections.new('gas_giant')
    sc.collection.children.link(col)
    root = bpy.data.objects.new('gas_giant', None)
    col.objects.link(root)
    # ---- планета: сфера радиуса 1, ось вращения +Z, развёртка — широта/долгота
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    bmesh.ops.create_uvsphere(bm, u_segments=128, v_segments=64, radius=1.0, calc_uvs=True)
    north = [l[uvl].uv.y for f in bm.faces for l in f.loops if l.vert.co.z > 0.98]
    flip_v = sum(north) / len(north) < 0.5
    eq = sorted(((math.atan2(l.vert.co.y, l.vert.co.x), l[uvl].uv.x) for f in bm.faces for l in f.loops
                 if abs(l.vert.co.z) < 0.03 and 0.2 < math.atan2(l.vert.co.y, l.vert.co.x) < 1.2))
    flip_u = eq[-1][1] < eq[0][1]
    for f in bm.faces:
        f.smooth = True
        for l in f.loops:
            u, v = l[uvl].uv
            l[uvl].uv = ((1 - u) if flip_u else u, (1 - v) if flip_v else v)
    me = bpy.data.meshes.new('gg_planet')
    bm.to_mesh(me)
    bm.free()
    pl = bpy.data.objects.new('gg_planet', me)
    col.objects.link(pl)
    pl.parent = root
    # ---- кольца: плоский диск в плоскости экватора, U — по радиусу (0 — внутренний край), V — вдоль кольца
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    NS, NR = 256, 5
    vs = [[bm.verts.new(((R_IN + (R_OUT - R_IN) * j / (NR - 1)) * math.cos(2 * math.pi * i / NS),
                         (R_IN + (R_OUT - R_IN) * j / (NR - 1)) * math.sin(2 * math.pi * i / NS), 0.0)) for j in range(NR)] for i in range(NS)]
    for i in range(NS):
        for j in range(NR - 1):
            f = bm.faces.new((vs[i][j], vs[i][j + 1], vs[(i + 1) % NS][j + 1], vs[(i + 1) % NS][j]))
            uv = ((j / (NR - 1), i / NS), ((j + 1) / (NR - 1), i / NS), ((j + 1) / (NR - 1), (i + 1) / NS), (j / (NR - 1), (i + 1) / NS))
            for l, c in zip(f.loops, uv):
                l[uvl].uv = c
    me = bpy.data.meshes.new('gg_rings')
    bm.to_mesh(me)
    bm.free()
    rg = bpy.data.objects.new('gg_rings', me)
    col.objects.link(rg)
    rg.parent = root
    # ---- материалы: планета (цвет + слабое свечение ночной карты), кольца для экспорта и кольца для кадров
    m = bpy.data.materials.new('gas_giant')
    m.use_nodes = True
    b = node(m, 'BSDF_PRINCIPLED')
    m.node_tree.links.new(tex(m, 'T_GasGiant_BaseColor.png').outputs['Color'], b.inputs['Base Color'])
    m.node_tree.links.new(tex(m, 'T_GasGiant_Night.png').outputs['Color'], b.inputs['Emission Color'])
    b.inputs['Emission Strength'].default_value = 0.35
    b.inputs['Roughness'].default_value = 1.0
    b.inputs['Specular IOR Level'].default_value = 0.0
    pl.data.materials.append(m)
    m = bpy.data.materials.new('gas_giant_rings')
    m.use_nodes = True
    b = node(m, 'BSDF_PRINCIPLED')
    t = tex(m, 'T_GasGiantRings_Lit.png', True)
    m.node_tree.links.new(t.outputs['Color'], b.inputs['Base Color'])
    m.node_tree.links.new(t.outputs['Alpha'], b.inputs['Alpha'])
    b.inputs['Roughness'].default_value = 1.0
    b.inputs['Specular IOR Level'].default_value = 0.0
    m.use_backface_culling = False
    try:
        m.surface_render_method = 'BLENDED'
    except Exception:
        pass
    rg.data.materials.append(m)
    v = bpy.data.materials.new('gas_giant_rings_view')          # для кадров: отражение + просвет с обратной стороны
    v.use_nodes = True
    v.use_fake_user = True
    nt = v.node_tree
    nt.nodes.remove(node(v, 'BSDF_PRINCIPLED'))
    out = node(v, 'OUTPUT_MATERIAL')
    tl, tb = tex(v, 'T_GasGiantRings_Lit.png', True), tex(v, 'T_GasGiantRings_Backlit.png', True)
    dif, trl, add = nt.nodes.new('ShaderNodeBsdfDiffuse'), nt.nodes.new('ShaderNodeBsdfTranslucent'), nt.nodes.new('ShaderNodeAddShader')
    tra, mix = nt.nodes.new('ShaderNodeBsdfTransparent'), nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(tl.outputs['Color'], dif.inputs['Color'])
    nt.links.new(tb.outputs['Color'], trl.inputs['Color'])
    nt.links.new(dif.outputs[0], add.inputs[0])
    nt.links.new(trl.outputs[0], add.inputs[1])
    nt.links.new(tl.outputs['Alpha'], mix.inputs[0])
    nt.links.new(tra.outputs[0], mix.inputs[1])
    nt.links.new(add.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])
    return root, pl, rg, flip_u, flip_v


def tris(o):
    o.data.calc_loop_triangles()
    return len(o.data.loop_triangles)


def ue_normal(B, rho, az=210.0, el=35.0, sun_az=0.0, sun_el=10.0):
    """Нормаль колец в осях сцены Unreal для гиганта в направлении (азимут, высота): раскрытие B, крен rho; и высота Солнца над плоскостью колец."""
    d = Vector((math.cos(rad(az)) * math.cos(rad(el)), math.sin(rad(az)) * math.cos(rad(el)), math.sin(rad(el))))
    r = Vector((0, 0, 1)).cross(d).normalized()
    u = (Vector((0, 0, 1)) - d * d.z).normalized()
    n = (-d) * math.sin(rad(B)) + (r * math.sin(rad(rho)) + u * math.cos(rad(rho))) * math.cos(rad(B))
    s = Vector((math.cos(rad(sun_az)) * math.cos(rad(sun_el)), math.sin(rad(sun_az)) * math.cos(rad(sun_el)), math.sin(rad(sun_el))))
    return [round(c, 3) for c in n], round(math.degrees(math.asin(max(-1, min(1, n.dot(s))))), 1), (s.dot(r), s.dot(d), s.dot(u))


def export(root, pl, rg):
    bpy.ops.object.select_all(action='DESELECT')
    for o in (root, pl, rg):
        o.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(filepath=os.path.join(EXP, 'gas_giant.glb'), export_format='GLB', use_selection=True, export_yup=True,
                              export_materials='EXPORT', export_image_format='AUTO', export_cameras=False, export_lights=False)
    bpy.ops.export_scene.fbx(filepath=os.path.join(EXP, 'gas_giant.fbx'), use_selection=True, object_types={'EMPTY', 'MESH'},
                             apply_scale_options='FBX_SCALE_ALL', mesh_smooth_type='FACE', use_tspace=False, bake_anim=False,
                             path_mode='AUTO', embed_textures=False, add_leaf_bones=False)
    n10, sun10, _ = ue_normal(10.0, -20.0)
    man = dict(
        id='gas_giant', title='Газовый гигант с кольцами (небо сцены 1 «Отлив»)',
        textures={
            'T_GasGiant_BaseColor.png': '4096×2048, sRGB. Дневная сторона: цвет облаков (альбедо). Развёртка широта/долгота: U — долгота (шов U=0/1 бесшовный), верх картинки — северный полюс',
            'T_GasGiant_Night.png': '4096×2048, sRGB. Ночная сторона: свечение (полярные сияния, зарницы в поясах), остальное чёрное. Добавлять как эмиссию там, где нет дневного света; яркость — параметром (в кадрах 0,35)',
            'T_GasGiantRings_Lit.png': '4096×64, sRGB + альфа. Кольца с освещённой стороны: цвет + непрозрачность',
            'T_GasGiantRings_Backlit.png': '4096×64, sRGB + альфа. Кольца на просвет (наблюдатель и Солнце по разные стороны плоскости колец, ночная кромка): плотные кольца тёмные, разреженные светятся; альфа та же'},
        rings=dict(
            strip='радиальная полоса: U — радиус, V — вдоль кольца (все строки одинаковые)',
            inner_edge='U = 0 (левый край картинки) — ВНУТРЕННИЙ край, радиус %.3f R' % R_IN,
            outer_edge='U = 1 (правый край картинки) — внешний край, радиус %.3f R' % R_OUT,
            formula='U = (r/R − %.3f) / %.3f; края полосы прозрачные, адресация Clamp' % (R_IN, R_OUT - R_IN),
            layout_in_R={'внутреннее пылевое': [1.26, 1.36], 'главное плотное': [1.38, 1.81], 'широкая щель': [1.81, 1.88],
                         'внешнее': [1.88, 2.19], 'тонкое наружное колечко': [2.25, 2.26]},
            alpha='непрозрачность при взгляде перпендикулярно плоскости; при малом раскрытии B можно уплотнять: 1 − (1 − a)^(1/sin B), не обязательно',
            sides='цвет = lerp(Backlit, Lit, k), где k = 1, если Солнце и наблюдатель по одну сторону плоскости колец, иначе 0'),
        tilt=dict(
            recommended='раскрытие колец к наблюдателю 10° (диапазон 6–14°), крен большой оси в кадре около 20°: с поверхности кольца видны почти с ребра — тонкий эллипс поперёк диска и полоса тени на планете',
            ring_normal_for_scene=n10,
            ring_normal_note='нормаль колец в осях сцены для гиганта на азимуте 210°, высоте 35° и Солнца на азимуте 0°, высоте 10° (раскрытие 10°, крен −20°): видна освещённая сторона колец, Солнце на %.0f° выше их плоскости. Посчитано, в Unreal не проверено' % sun10,
            current_in_scene='сейчас в сцене нормаль (0.20, −0.35, 0.915) — раскрытие около 32°; тоже допустимо, если нужен более открытый вид',
            planet_axis='ось вращения планеты (север текстуры) совпадает с нормалью колец'),
        mesh=dict(note='необязательная сетка с готовой развёрткой: радиус планеты 1 м, ось +Z, кольца в плоскости XY; можно оставить сетки сцены и взять только текстуры',
                  files=['gas_giant.glb', 'gas_giant.fbx'],
                  parts=[dict(name='gg_planet', triangles=tris(pl), slot='gas_giant'), dict(name='gg_rings', triangles=tris(rg), slot='gas_giant_rings')]),
        material_slots=[dict(name='gas_giant', textures='T_GasGiant_BaseColor, T_GasGiant_Night (эмиссия)'),
                        dict(name='gas_giant_rings', textures='T_GasGiantRings_Lit (цвет + альфа), двусторонний, полупрозрачный')],
        notes=['без кислотных цветов: пастельная охра экваториальных поясов, голубовато-серые высокие широты',
               'большой светлый овал: широта %.1f°, долгота %.0f° (U = %.3f)' % (PRM['big_oval']['lat'], PRM['big_oval']['lon'], PRM['big_oval']['lon'] / 360),
               'тень планеты на кольцах и тень колец на планете — в материале или светом сцены; в текстурах их нет'])
    json.dump(man, open(os.path.join(EXP, 'manifest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('EXPORT gas_giant: планета %d тр., кольца %d тр.; нормаль колец для сцены %s, Солнце над плоскостью %.0f°' % (tris(pl), tris(rg), n10, sun10))


if 'gas_giant' not in bpy.data.objects:
    for _o in list(bpy.data.objects):
        bpy.data.objects.remove(_o, do_unlink=True)
    root, pl, rg, fu, fv = build()
    print('развёртка сферы: flip_u=%s flip_v=%s' % (fu, fv))
    export(root, pl, rg)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'src', 'gas_giant.blend'))
root, pl, rg = bpy.data.objects['gas_giant'], bpy.data.objects['gg_planet'], bpy.data.objects['gg_rings']
rg.data.materials[0] = bpy.data.materials['gas_giant_rings_view']

# ------------------------------------------------------------------ кадры
w = bpy.data.worlds.get('space') or bpy.data.worlds.new('space')
w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
bg.inputs[0].default_value = (0, 0, 0, 1)
bg.inputs[1].default_value = 0.0
sc.world = w
if 'gg_sun' not in bpy.data.objects:
    ld = bpy.data.lights.new('gg_sun', 'SUN')
    ld.energy, ld.angle = 3.4, rad(0.5)
    sc.collection.objects.link(bpy.data.objects.new('gg_sun', ld))
the_sun = bpy.data.objects['gg_sun']
uvl = pl.data.uv_layers.active.data
tu, tv = PRM['big_oval']['lon'] / 360.0, (PRM['big_oval']['lat'] + 90) / 180.0
best = min(pl.data.loops, key=lambda l: (uvl[l.index].uv.x - tu) ** 2 + (uvl[l.index].uv.y - tv) ** 2)
OVAL = pl.data.vertices[best.vertex_index].co.copy()            # где на сфере большой овал
_, _, S3 = ue_normal(10.0, -20.0)


def pose(B, rho, off):
    """Раскрытие колец к камере B, крен rho; овал повёрнут на off градусов от центра диска. Камера на −Y, смотрит по +Y."""
    a = Vector((math.cos(rad(B)) * math.sin(rad(rho)), -math.sin(rad(B)), math.cos(rad(B)) * math.cos(rad(rho))))
    q = Vector((0, 0, 1)).rotation_difference(a)
    cl = q.inverted() @ Vector((0, -1, 0))
    spin = math.atan2(cl.y, cl.x) + rad(off) - math.atan2(OVAL.y, OVAL.x)
    root.rotation_mode = 'QUATERNION'
    root.rotation_quaternion = q @ Quaternion((0, 0, 1), spin)


def sun_dir(phase, beta):
    return Vector((math.sin(rad(phase)) * math.cos(rad(beta)), -math.cos(rad(phase)), math.sin(rad(phase)) * math.sin(rad(beta))))


#        вид: (раскрытие, крен, поворот овала, направление на Солнце, расстояние, поле зрения, прозрачный фон, свечение ночи)
VIEWS = {
    'view1': (-20.0, 16.0, -24.0, sun_dir(38.0, 200.0), 12.0, 27.0, False, 0.35),      # вид с юга: большой овал в кадре
    'view2': (13.0, -14.0, 150.0, sun_dir(128.0, -12.0), 12.0, 27.0, False, 0.35),
    'view3': (10.0, -20.0, 22.0, Vector(S3).normalized(), 1.0 / math.sin(rad(11.0)), 62.0, True, 0.0),
}
todo = list(globals().get('LIVE_VIEWS') or [])
done_file = os.path.join(ROOT, 'shots', '_tmp', 'live_done.txt')
if os.path.exists(done_file):
    os.remove(done_file)
log = open(os.path.join(ROOT, 'shots', '_tmp', 'live_shots.log'), 'a', encoding='utf-8')
state = {'t0': 0.0, 'cur': None}


def _start(v):
    B, rho, off, s, D, fov, transp, night = VIEWS[v]
    pose(B, rho, off)
    setup_cycles(1920, 1080, samples=globals().get('LIVE_SAMPLES', 48), transparent=transp, bounces=4)
    sc.cycles.adaptive_threshold = 0.03
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    node(bpy.data.materials['gas_giant'], 'BSDF_PRINCIPLED').inputs['Emission Strength'].default_value = night
    the_sun.rotation_euler = (-s).to_track_quat('-Z', 'Y').to_euler()
    old = bpy.data.objects.get('cam_g')
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    sc.camera = camera('cam_g', Vector((0, -D, 0)), Vector((0, 1, 0)), fov=fov, clip=(0.1, 1000))
    sc.render.filepath = os.path.join(ROOT, 'shots', '_tmp', 'giant_v3_raw.png') if transp else os.path.join(ROOT, 'shots', 'E_giant_%s.png' % v)
    state['cur'], state['t0'] = v, time.time()
    if bpy.app.background:
        bpy.ops.render.render(write_still=True)
        return 0.1
    win = bpy.context.window_manager.windows[0]
    try:
        with bpy.context.temp_override(window=win, screen=win.screen):
            bpy.ops.render.render('INVOKE_DEFAULT', write_still=True)
    except Exception as ex:
        log.write('ERROR %s %s\n' % (v, ex))
        log.flush()
    return 5.0


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
    try:
        return _start(todo.pop(0))
    except Exception:
        import traceback
        log.write('ERROR ' + traceback.format_exc() + chr(10))
        log.flush()
        return 2.0


if todo and bpy.app.background:
    while todo:
        _v = todo.pop(0)
        _t = time.time()
        _start(_v)
        log.write('RENDERED %s %.0f s (фон)\n' % (_v, time.time() - _t))
        log.flush()
        print('RENDERED %s %.0f s' % (_v, time.time() - _t))
    open(done_file, 'w').write('done')
elif todo:
    bpy.app.timers.register(_tick, first_interval=1.0)
    print('очередь рендеров запущена:', todo)
