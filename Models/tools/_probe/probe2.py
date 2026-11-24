import bpy, sys, time
sc = bpy.context.scene
for eng in ('CYCLES', 'BLENDER_WORKBENCH', 'BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
    try:
        sc.render.engine = eng; print("OK engine", eng)
    except Exception as e:
        print("NO engine", eng, str(e)[:80])
sc.render.engine = 'CYCLES'
print("denoiser", sc.cycles.denoiser, [e.identifier for e in type(sc.cycles).bl_rna.properties['denoiser'].enum_items])
print("cam types", [e.identifier for e in bpy.types.Camera.bl_rna.properties['type'].enum_items])
cam = bpy.data.cameras.new('c'); cam.type='PANO'
print("pano", [e.identifier for e in type(cam).bl_rna.properties['panorama_type'].enum_items] if hasattr(cam,'panorama_type') else dir(cam.cycles) if hasattr(cam,'cycles') else 'none')
print("vt", sc.view_settings.view_transform, sc.display_settings.display_device)
for vt in ('Standard','Filmic','AgX','Khronos PBR Neutral'):
    try:
        sc.view_settings.view_transform = vt; print("vt ok", vt)
    except Exception as e: print("vt no", vt)
bpy.ops.mesh.primitive_monkey_add()
sc.render.resolution_x, sc.render.resolution_y = 960, 540
sc.cycles.samples = 16
sc.cycles.use_denoising = True
co = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(co); co.location=(0,-5,0); co.rotation_euler=(1.5708,0,0); sc.camera=co
sc.render.filepath = r'C:\UnrealScenes\Models\tools\_probe\t.png'
t=time.time(); bpy.ops.render.render(write_still=True); print("cycles render s", time.time()-t)
