import bpy, bmesh, sys
print("VER", bpy.app.version_string)
print("ENGINES", [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items])
import inspect
print("bisect" , bmesh.ops.bisect_plane.__doc__[:400])
sc = bpy.context.scene
print("cycles" , hasattr(sc, 'cycles'))
try:
    import cycles
    print("denoisers", [e.identifier for e in sc.cycles.bl_rna.properties['denoiser'].enum_items])
except Exception as e:
    print("cyc err", e)
print("view transforms", [e.identifier for e in sc.view_settings.bl_rna.properties['view_transform'].enum_items])
print("gltf", hasattr(bpy.ops.export_scene, 'gltf'), "fbx", hasattr(bpy.ops.export_scene, 'fbx'))
m = bpy.data.materials.new('x'); m.use_nodes = True
b = [n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'][0]
print("bsdf inputs", [i.name for i in b.inputs])
print("mesh attrs", [a for a in dir(bpy.types.Mesh) if 'sharp' in a or 'smooth' in a or 'normal' in a])
print("mods", [e.identifier for e in bpy.types.Modifier.bl_rna.properties['type'].enum_items][:80])
