# shots_kit.py — рендеры на приёмку: камеры, свет, Workbench (быстрая проверка) и Cycles (чистовые).
import bpy, math, os
from mathutils import Vector, Matrix, Euler


def look_rot(direction, up=(0, 0, 1)):
    """Поворот камеры, смотрящей вдоль direction (верх кадра — к up)."""
    d = Vector(direction).normalized()
    return d.to_track_quat('-Z', 'Y').to_euler()


def camera(name, loc, direction, fov=None, ortho=None, lens=None, clip=(0.05, 5000.0)):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = 'ORTHO'
        cd.ortho_scale = ortho
    elif fov:
        cd.sensor_fit = 'HORIZONTAL'
        cd.sensor_width = 36.0
        cd.lens = 18.0 / math.tan(math.radians(fov) / 2)
    elif lens:
        cd.lens = lens
    cd.clip_start, cd.clip_end = clip
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = look_rot(direction)
    return ob


def setup_workbench(w, h, cavity=True):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading
    sh.light = 'STUDIO'
    sh.color_type = 'MATERIAL'
    sh.show_cavity = cavity
    sh.cavity_type = 'BOTH'
    sh.show_shadows = False
    sh.show_object_outline = False
    sh.show_specular_highlight = True
    try:
        sc.display.render_aa = '8'
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = 'PNG'
    sc.view_settings.view_transform = 'Standard'
    if sc.world is None:
        sc.world = bpy.data.worlds.new('World')
    sc.world.use_nodes = False
    sc.world.color = (0.75, 0.77, 0.80)


def setup_cycles(w, h, samples=64, transparent=False, bounces=6):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    c = sc.cycles
    c.device = 'CPU'
    c.samples = samples
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.02
    c.use_denoising = True
    c.max_bounces = bounces
    c.diffuse_bounces = 3
    c.glossy_bounces = 3
    c.transmission_bounces = 4
    c.transparent_max_bounces = 12
    c.caustics_reflective = False
    c.caustics_refractive = False
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA' if transparent else 'RGB'
    sc.render.use_persistent_data = False
    try:
        sc.render.threads_mode = 'FIXED'
        sc.render.threads = 10
    except Exception:
        pass
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass


def sky_world(strength=1.0, horizon=(0.80, 0.84, 0.90), zenith=(0.30, 0.46, 0.72), ground=(0.42, 0.44, 0.47)):
    sc = bpy.context.scene
    w = bpy.data.worlds.new('sky')
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = -1.0
    mr.inputs['From Max'].default_value = 1.0
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
    nt.links.new(mr.outputs['Result'], ramp.inputs['Fac'])
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (*ground, 1)
    cr.elements[1].position = 1.0
    cr.elements[1].color = (*zenith, 1)
    e = cr.elements.new(0.495)
    e.color = (*ground, 1)
    e = cr.elements.new(0.505)
    e.color = (*horizon, 1)
    e = cr.elements.new(0.62)
    e.color = tuple((a + b) / 2 for a, b in zip(horizon, zenith)) + (1,)
    bg.inputs['Strength'].default_value = strength
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    nt.links.new(bg.outputs[0], out.inputs['Surface'])
    return w


def sun(az_deg, el_deg, strength=3.5, angle=1.5, color=(1.0, 0.96, 0.90)):
    """Солнце: азимут — куда светит источник ОТКУДА (0° = со стороны носа, −Y; 90° = с правого борта, +X)."""
    L = bpy.data.lights.new('sun', 'SUN')
    L.energy = strength
    L.angle = math.radians(angle)
    L.color = color
    ob = bpy.data.objects.new('sun', L)
    bpy.context.scene.collection.objects.link(ob)
    a, e = math.radians(az_deg), math.radians(el_deg)
    to_sun = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    ob.rotation_euler = (-to_sun).to_track_quat('-Z', 'Y').to_euler()
    return ob


def plane(name, z, size, material):
    me = bpy.data.meshes.new(name)
    s = size / 2
    me.from_pydata([(-s, -s, z), (s, -s, z), (s, s, z), (-s, s, z)], [], [(0, 1, 2, 3)])
    me.materials.append(material)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def simple_mat(name, color, rough=0.6, metallic=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = (*color[:3], alpha)
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = (*color[:3], 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metallic
    b.inputs['Alpha'].default_value = alpha
    return m


def water_mat(name='water_preview'):
    """Вода для приёмочных кадров: зеркальная плёнка, сквозь которую видно дно и опоры."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = (0.55, 0.65, 0.70, 0.35)
    nt = m.node_tree
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    tr.inputs['Color'].default_value = (0.80, 0.88, 0.90, 1)
    try:
        gl = nt.nodes.new('ShaderNodeBsdfGlossy')
    except Exception:
        gl = nt.nodes.new('ShaderNodeBsdfAnisotropic')
    gl.inputs['Roughness'].default_value = 0.04
    fr = nt.nodes.new('ShaderNodeFresnel')
    fr.inputs['IOR'].default_value = 1.33
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(fr.outputs[0], mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(gl.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs['Surface'])
    return m


def render(cam, path):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print('RENDERED', path)


def show_only(names):
    """Показать в рендере только коллекции из списка (верхнего уровня)."""
    for c in bpy.context.scene.collection.children:
        c.hide_render = c.name not in names
        lc = bpy.context.view_layer.layer_collection.children.get(c.name)
        if lc:
            lc.exclude = c.name not in names
