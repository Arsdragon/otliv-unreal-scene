# Water dust torn off the crest (trails behind it, backlit by the sun) and the soft mist bank at the foot of the wave.
# Ribbon meshes attached to the wave + one unlit translucent material with procedural soft noise (no textures, no speckle).
import unreal, math, importlib, mu, s1u, f_wave_mesh as fw
importlib.reload(mu); importlib.reload(fw)
from mu import *
REBUILD_MESH = True


def ribbon(asset, rows):
    """rows(y) -> list of (x_m, z_m) from bottom to top for a column at y"""
    if EAL.does_asset_exist(asset) and not REBUILD_MESH:
        return EAL.load_asset(asset)
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


def spray_rows(y):
    # plume starts at the lip and trails back and up (the wave runs into still air at 150 m/s); its size varies along the crest
    sc, lean, xo = fw.col_params(y)
    zc = 2085.0 * sc
    hf = 0.45 + 0.9 * (0.5 + 0.5 * fw.noise1(y / 1100.0, 7))
    lf = 0.6 + 0.8 * (0.5 + 0.5 * fw.noise1(y / 2300.0, 8))
    base = [(-30, -60), (0, 20), (60, 90), (170, 170), (330, 240), (560, 300)]
    return [(-45 * lean + xo + dx * (lf if dx > 0 else 1.0), zc + dz * (hf if dz > 0 else 1.0)) for dx, dz in base]


def mist_rows_at(shift):
    def rows(y):
        sc, lean, xo = fw.col_params(y)
        x0 = -1250.0 * lean + xo + shift
        return [(x0 + dx, dz) for dx, dz in [(-90, 0), (-50, 70), (0, 190), (60, 360), (140, 560)]]
    return rows


sm_spray = ribbon('/Game/Scene1/Wave/SM_WaveSpray', spray_rows)
sm_mist = [ribbon('/Game/Scene1/Wave/SM_WaveMist', mist_rows_at(0.0)),
           ribbon('/Game/Scene1/Wave/SM_WaveMistB', mist_rows_at(-260.0)),
           ribbon('/Game/Scene1/Wave/SM_WaveMistC', mist_rows_at(230.0))]

m = new_mat('M_Spray', shading=unreal.MaterialShadingModel.MSM_UNLIT, blend=unreal.BlendMode.BLEND_TRANSLUCENT, two_sided=True)
g = G(m)
uv = g.node(unreal.MaterialExpressionTextureCoordinate)
mpc = EAL.load_asset('/Game/Scene1/MPC_Otliv')
t = g.mpc(mpc, 'SimTime')
cam = g.node(unreal.MaterialExpressionCameraVectorWS)
sa = g.vec('ScaleA', (0.35, 1.2, 0.002, -0.03))        # noise cells per uv unit (u = 400 m, v = ribbon height), scroll zw
sb = g.vec('ScaleB', (1.1, 2.6, -0.004, -0.06))
of = g.vec('Offset', (0.0, 0.0, 0.0, 0.0))
col = g.vec('Color', (0.62, 0.70, 0.74))
sunc = g.vec('SunColor', (1.0, 0.86, 0.66))
pf = g.vec('Profile', (0.14, 1.5, 0.25, 10.0))          # fade-in at the bottom, falloff power to the top, base light, sun cone exponent
back = g.scalar('Backlit', 3.0)
dens = g.scalar('Density', 0.7)
thr = g.scalar('Threshold', 0.25)
con = g.scalar('Contrast', 2.0)
gain = g.scalar('Gain', 1.0)
fade = g.node(unreal.MaterialExpressionDepthFade)
fade.set_editor_property('fade_distance_default', 6000.0)
SP = r'''
struct S {
 float h2(float2 p){ return frac(sin(dot(p,float2(12.9898,78.233)))*43758.5453); }
 float vn(float2 p){ float2 i=floor(p), f=frac(p); f=f*f*(3-2*f);
   return lerp(lerp(h2(i),h2(i+float2(1,0)),f.x),lerp(h2(i+float2(0,1)),h2(i+float2(1,1)),f.x),f.y); }
 float fbm(float2 p){ return 0.5*vn(p) + 0.3*vn(p*2.13+7.1) + 0.2*vn(p*4.37+3.3); }
};
S s;
float2 q = UV + Of.xy;
float n = s.fbm(q*SA.xy + SA.zw*T)*0.65 + s.fbm(q*SB.xy + SB.zw*T + 17.0)*0.35;
float v = UV.y;
float prof = smoothstep(0.0, max(Pf.r, 0.001), v) * pow(saturate(1.0 - v), Pf.g);
float d = saturate((n - Th) * Cn) * prof * De;
float3 L = float3(0.9848, 0.0, 0.1736);
float cosv = saturate(dot(-normalize(CV), L));
float ph = Pf.b + Bk * pow(cosv, max(Pf.a, 1.0));
Op = saturate(d) * FD;
return (Co.rgb * (0.8 + 0.2*n) + Sc.rgb * ph * (0.4 + 0.6*n)) * Gn;
'''
sp = g.custom(SP, [('UV', uv), ('T', t), ('CV', cam), ('SA', sa, 'RGBA'), ('SB', sb, 'RGBA'), ('Of', of, 'RGBA'), ('Co', col), ('Sc', sunc),
                   ('Pf', pf, 'RGBA'), ('Bk', back), ('De', dens), ('Th', thr), ('Cn', con), ('Gn', gain), ('FD', fade)],
              'f3', outs=[('Op', 'f1')])
g.out(sp, MP.MP_EMISSIVE_COLOR)
g.out(sp, MP.MP_OPACITY, 'Op')
g.done()

import i_tune
importlib.reload(i_tune)
mi_s = i_tune.mi('MI_Spray', '/Game/Scene1/Materials/M_Spray')
i_tune.setp(mi_s, ScaleA=(3.0, 1.3, 0.004, -0.05), ScaleB=(9.0, 2.9, -0.006, -0.09), Color=(0.55, 0.60, 0.62),
            Profile=(0.10, 1.2, 0.35, 8.0), Backlit=2.5, Density=1.6, Threshold=0.22, Contrast=2.2, Gain=1.0)
mist_mis = []
for i, offs in enumerate([(0.0, 0.0), (3.7, 0.31), (8.3, 0.67)]):
    mi_m = i_tune.mi('MI_Mist' if i == 0 else 'MI_Mist%s' % 'BC'[i - 1], '/Game/Scene1/Materials/M_Spray')
    i_tune.setp(mi_m, ScaleA=(0.35, 1.2, 0.002, -0.03), ScaleB=(1.1, 2.6, -0.004, -0.06), Offset=(offs[0], offs[1], 0.0, 0.0),
                Color=(0.22, 0.27, 0.31), SunColor=(0.5, 0.46, 0.40), Profile=(0.16, 1.4, 0.10, 6.0), Backlit=0.10,
                Density=0.55, Threshold=0.18, Contrast=1.6, Gain=1.0)
    mist_mis.append(mi_m)
wave = s1u.find('Wave')
items = [('WaveSpray', sm_spray, mi_s), ('WaveMist', sm_mist[0], mist_mis[0]), ('WaveMistB', sm_mist[1], mist_mis[1]), ('WaveMistC', sm_mist[2], mist_mis[2])]
for lb, sm, mat in items:
    a = s1u.spawn(unreal.StaticMeshActor, lb, loc=(0, 0, 0), folder='Wave')
    c = a.static_mesh_component
    c.set_static_mesh(sm); c.set_material(0, mat)
    c.set_mobility(unreal.ComponentMobility.MOVABLE); c.set_editor_property('cast_shadow', False)
    c.set_editor_property('affect_distance_field_lighting', False)
    a.set_actor_location(wave.get_actor_location(), False, False)
    a.attach_to_actor(wave, '', unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
s1u.save()
print('spray ok')
