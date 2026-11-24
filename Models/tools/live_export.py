# live_export.py — экспорт chaika_ext (glb, fbx, manifest.json) из ОТКРЫТОГО окна Blender:
#   python tools/bmcp.py @tools/live_export.py 900
# Берёт функции из tools/chaika_final.py; в сцене должна быть коллекция chaika_ext с итоговыми материалами.
import bpy, os
_p = r'C:\UnrealScenes\Models\tools\chaika_final.py'
_ns = {'__name__': 'chaika_final_lib', '__file__': _p}
exec(compile(open(_p, encoding='utf-8').read(), _p, 'exec'), _ns)
_objs = [o for o in bpy.data.collections['chaika_ext'].all_objects if o.type == 'MESH']
_man = _ns['export'](_objs, bpy.data.objects['chaika_ext'])
bpy.ops.wm.save_mainfile()
for _f in ('chaika_ext.glb', 'chaika_ext.fbx', 'manifest.json'):
    print('EXPORT %s %.1f МБ' % (_f, os.path.getsize(os.path.join(_ns['EXP'], _f)) / 1e6))
print('треугольников %d, частей %d, меток %d' % (_man['triangles'], len(_man['parts']), len(_man['markers'])))
