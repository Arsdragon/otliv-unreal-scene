# live_load.py — загрузить текстурированную chaika_ext в открытое окно Blender и сохранить сцену:
#   python tools/bmcp.py @tools/live_load.py 300
SHOW_PATH = r'C:\UnrealScenes\Models\src\chaika_ext_final.blend'
SHOW_COLL = 'chaika_ext'
SHOW_TEX = True
exec(open(r'C:\UnrealScenes\Models\tools\show_in_blender.py', encoding='utf-8').read())
bpy.ops.wm.save_as_mainfile(filepath=r'C:\UnrealScenes\Models\src\chaika_ext_live.blend')
print('сохранено: src/chaika_ext_live.blend')
