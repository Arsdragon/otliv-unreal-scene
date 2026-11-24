# show_in_blender.py — показать собранную модель в открытом окне Blender пользователя (через tools/bmcp.py):
#   python tools/bmcp.py @tools/live_load.py      (или задать SHOW_PATH / SHOW_COLL / SHOW_TEX и выполнить этот файл)
# Добавляет коллекцию из файла (прежнюю такую же заменяет), прячет стандартный куб, включает показ текстур.
import bpy
PATH = globals().get('SHOW_PATH', r'C:\UnrealScenes\Models\src\chaika_ext.blend')
COLL = globals().get('SHOW_COLL', 'chaika_ext')
TEX = globals().get('SHOW_TEX', False)
old = bpy.data.collections.get(COLL)
if old:
    for o in list(old.all_objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(old)
for blk in (bpy.data.meshes, bpy.data.materials):          # убрать осиротевшие данные прежней версии
    for d in list(blk):
        if d.users == 0:
            blk.remove(d)
with bpy.data.libraries.load(PATH, link=False) as (src, dst):
    dst.collections = [c for c in src.collections if c == COLL]
for c in dst.collections:
    bpy.context.scene.collection.children.link(c)
for n in ('Cube', 'Light', 'Camera'):
    o = bpy.data.objects.get(n)
    if o:
        o.hide_viewport = True
        o.hide_render = True
for w in bpy.context.window_manager.windows:
    for a in w.screen.areas:
        if a.type == 'VIEW_3D':
            sp = a.spaces.active
            sp.shading.type = 'SOLID'
            sp.shading.color_type = 'TEXTURE' if TEX else 'MATERIAL'
            sp.shading.light = 'STUDIO'
            reg = next(r for r in a.regions if r.type == 'WINDOW')
            with bpy.context.temp_override(window=w, area=a, region=reg):
                bpy.ops.view3d.view_all()
print('показано объектов:', len(bpy.data.collections[COLL].all_objects),
      '| материалы:', sorted({m.name for o in bpy.data.collections[COLL].all_objects if o.type == 'MESH' for m in o.data.materials}))
