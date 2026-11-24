# Boiling foam and a low curtain of spray where the foot of the wave meets the flat water:
# two low ribbons attached to the wave, material instance of M_Spray (no shader compile).
import unreal, importlib, s1u, i_tune, f_wave_mesh as fw
importlib.reload(i_tune)
EAL = unreal.EditorAssetLibrary


def ribbon(asset, rows):
    ys = [y for y in fw.ycols() if abs(y) < 80000][::2]
    V, UV, T = [], [], []
    nr = None
    for y in ys:
        pts = rows(y)
        nr = len(pts)
        for k, (x, z) in enumerate(pts):
            V.append(unreal.Vector(x * 100.0, y * 100.0, z * 100.0))
            UV.append(unreal.Vector2D(y / 400.0, k / (nr - 1)))
    for j in range(len(ys) - 1):
        for i in range(nr - 1):
            a, b, c, d = j * nr + i, j * nr + i + 1, (j + 1) * nr + i, (j + 1) * nr + i + 1
            T.append(unreal.IntVector(a, c, b)); T.append(unreal.IntVector(b, c, d))
    buf = unreal.GeometryScriptSimpleMeshBuffers(); buf.vertices = V; buf.uv0 = UV; buf.triangles = T
    mesh = unreal.DynamicMesh()
    unreal.GeometryScript_MeshEdits.append_buffers_to_mesh(mesh, buf, 0)
    unreal.GeometryScript_Normals.recompute_normals(mesh, unreal.GeometryScriptCalculateNormalsOptions())
    if EAL.does_asset_exist(asset):
        sm = EAL.load_asset(asset)
        unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(mesh, sm, unreal.GeometryScriptCopyMeshToAssetOptions(), unreal.GeometryScriptMeshWriteLOD())
    else:
        o = unreal.GeometryScriptCreateNewStaticMeshAssetOptions(); o.enable_collision = False; o.enable_nanite = False
        sm, _ = unreal.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(mesh, asset, o)
    EAL.save_loaded_asset(sm)
    return sm


def rows_at(x_from_crest, heights):
    def rows(y):
        sc, lean, xo = fw.col_params(y)
        x0 = x_from_crest * lean + xo
        hv = 0.6 + 0.8 * (0.5 + 0.5 * fw.noise1(y / 420.0, 9))      # uneven height of the boil along the front
        return [(x0 + dx, dz * hv) for dx, dz in heights]
    return rows


ITEMS = [('WaveBoilA', '/Game/Scene1/Wave/SM_WaveBoilA', rows_at(-1400.0, [(-40, 0), (-22, 16), (0, 45), (25, 95), (60, 170)]), (0.0, 0.0), 1.5),
         ('WaveBoilB', '/Game/Scene1/Wave/SM_WaveBoilB', rows_at(-1170.0, [(-30, 0), (-15, 14), (0, 38), (20, 75), (45, 125)]), (5.1, 0.43), 1.2)]
wave = s1u.find('Wave')
for lb, asset, rows, offs, dens in ITEMS:
    sm = ribbon(asset, rows)
    mi = i_tune.mi('MI_' + lb, '/Game/Scene1/Materials/M_Spray')
    i_tune.setp(mi, ScaleA=(4.0, 1.1, 0.01, -0.22), ScaleB=(11.0, 2.4, -0.02, -0.4), Offset=(offs[0], offs[1], 0.0, 0.0),
                Color=(0.46, 0.52, 0.56), SunColor=(0.6, 0.56, 0.5), Profile=(0.02, 1.5, 0.22, 6.0), Backlit=0.25,
                Density=dens, Threshold=0.14, Contrast=2.0, Gain=1.0)
    a = s1u.spawn(unreal.StaticMeshActor, lb, loc=(0, 0, 0), folder='Wave')
    c = a.static_mesh_component
    c.set_static_mesh(sm); c.set_material(0, mi)
    c.set_mobility(unreal.ComponentMobility.MOVABLE); c.set_editor_property('cast_shadow', False)
    c.set_editor_property('affect_distance_field_lighting', False)
    a.set_actor_location(wave.get_actor_location(), False, False)
    a.attach_to_actor(wave, '', unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
s1u.save()
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
print('boil ok')
