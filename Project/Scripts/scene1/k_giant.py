# Gas giant with rings, textures from Models\export\gas_giant (models chat).
# Unlit + additive: a pale daytime planet seen through the atmosphere, the night side dissolves in the sky.
# Sun lighting, ring shadow on the planet, planet shadow on the rings and mutual occlusion are analytic.
import unreal, math, importlib, mu, s1u
importlib.reload(mu)
from mu import *
GP = unreal.GeometryScript_Primitives
SRC = r'C:\UnrealScenes\Models\export\gas_giant'
TEXDIR = '/Game/Scene1/Sky/GasGiant'


def import_tex(name, clamp_x=False):
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', SRC + '\\' + name + '.png')
    task.set_editor_property('destination_path', TEXDIR)
    task.set_editor_property('automated', True)
    task.set_editor_property('replace_existing', True)
    task.set_editor_property('save', True)
    AT.import_asset_tasks([task])
    tx = EAL.load_asset(TEXDIR + '/' + name)
    if clamp_x:
        tx.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP)
        EAL.save_loaded_asset(tx)
    return tx


def unit_mesh(asset, fn):
    if EAL.does_asset_exist(asset):
        return EAL.load_asset(asset)
    mesh = unreal.DynamicMesh()
    fn(mesh)
    o = unreal.GeometryScriptCreateNewStaticMeshAssetOptions(); o.enable_collision = False; o.enable_nanite = False
    sm, _ = unreal.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(mesh, asset, o)
    EAL.save_loaded_asset(sm)
    return sm


for n, cl in [('T_GasGiant_BaseColor', False), ('T_GasGiant_Night', False), ('T_GasGiantRings_Lit', True), ('T_GasGiantRings_Backlit', True)]:
    import_tex(n, cl)
T_BASE, T_NIGHT = TEXDIR + '/T_GasGiant_BaseColor', TEXDIR + '/T_GasGiant_Night'
T_LIT, T_BACK = TEXDIR + '/T_GasGiantRings_Lit', TEXDIR + '/T_GasGiantRings_Backlit'

sph = unit_mesh('/Game/Scene1/Sky/SM_GiantSphere', lambda m: GP.append_sphere_lat_long(m, unreal.GeometryScriptPrimitiveOptions(), unreal.Transform(), 100.0, 96, 192))
rng = unit_mesh('/Game/Scene1/Sky/SM_GiantRings', lambda m: GP.append_disc(m, unreal.GeometryScriptPrimitiveOptions(), unreal.Transform(), 100.0, 384, 6, 0.0, 360.0, 54.0))

D = 1.0e8                     # 1000 km
az, el = math.radians(210.0), math.radians(35.0)
dirv = (math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el))
C = tuple(D * c for c in dirv)
R = D * math.tan(math.radians(11.0))      # angular diameter 22 deg
RING_OUT = 2.3
RN = (0.414, 0.628, 0.658)    # from the manifest: rings open 10 deg to us, lit side visible, sun 32 deg above the ring plane
pl = unreal.MaterialProperty
RU = 'float2((RR - 1.242) / 1.058, 0.5)'

# ---------- planet ----------
m = new_mat('M_Giant', shading=unreal.MaterialShadingModel.MSM_UNLIT, blend=unreal.BlendMode.BLEND_ADDITIVE)
try: m.set_editor_property('apply_cloud_fogging', True)
except Exception as e: print('no cloud fogging prop')
g = G(m)
uv = g.node(unreal.MaterialExpressionTextureCoordinate)
nrm = g.node(unreal.MaterialExpressionVertexNormalWS)
cam = g.node(unreal.MaterialExpressionCameraVectorWS)
cpos = g.node(unreal.MaterialExpressionCameraPositionWS)
cen = g.vec('Center', C + (0.0,))
rad = g.scalar('Radius', R)
rnor = g.vec('RingNormal', RN)
sunc = g.vec('SunColor', (1.0, 0.92, 0.82))
inten = g.scalar('Intensity', 0.6)
nightk = g.scalar('Night', 0.0)
contr = g.scalar('BandContrast', 1.3)
tb = g.tex(T_BASE, None, uv)
tn = g.tex(T_NIGHT, None, uv)
uvS = g.custom(r'''
float3 N = normalize(Nw); float3 L = float3(-0.9848, 0.0, 0.1736); float3 RN = normalize(Rn.xyz);
float dl = dot(L, RN);
float ts = -dot(N, RN) / (abs(dl) > 1e-4 ? dl : 1e-4);
float RR = ts > 0.0 ? length(N + L*ts) : 0.0;
return ''' + RU + ';', [('Nw', nrm), ('Rn', rnor)], 'f2')
uvO = g.custom(r'''
float3 N = normalize(Nw); float3 RN = normalize(Rn.xyz);
float3 c = (Cp - Ce.xyz) / Ra;
float den = dot(c - N, RN);
float s = dot(c, RN) / (abs(den) > 1e-5 ? den : 1e-5);
float RR = (s > 0.0 && s < 1.0) ? length(c + (N - c)*s) : 0.0;
return ''' + RU + ';', [('Nw', nrm), ('Rn', rnor), ('Cp', cpos), ('Ce', cen), ('Ra', rad)], 'f2')
aS = g.tex(T_LIT, None, uvS)
aO = g.tex(T_LIT, None, uvO)
PLAN = r'''
float3 N = normalize(Nw);
float3 L = float3(-0.9848, 0.0, 0.1736);
float ndl = dot(N, L);
float lam = saturate(ndl) * smoothstep(-0.02, 0.22, ndl);
float limb = pow(saturate(dot(N, normalize(Cv))), 0.45);
float3 col = Tb;
col = saturate(lerp(float3(0.45, 0.45, 0.45), col, Ct));      // contrast around mid grey so the bands read through the haze
float rs = 1.0 - 0.9*As;
float occ = 1.0 - 0.95*Ao;
float night = 1.0 - smoothstep(-0.12, 0.08, ndl);
return (col * Sc.rgb * (In * lam * limb * rs) + Tn * (Nk * night)) * occ;
'''
pn = g.custom(PLAN, [('Nw', nrm), ('Cv', cam), ('Tb', tb, 'RGB'), ('Tn', tn, 'RGB'), ('As', aS, 'A'), ('Ao', aO, 'A'),
                     ('Sc', sunc), ('In', inten), ('Nk', nightk), ('Ct', contr)], 'f3')
g.out(pn, pl.MP_EMISSIVE_COLOR)
g.done()

# ---------- rings ----------
r = new_mat('M_GiantRings', shading=unreal.MaterialShadingModel.MSM_UNLIT, blend=unreal.BlendMode.BLEND_ADDITIVE, two_sided=True)
try: r.set_editor_property('apply_cloud_fogging', True)
except Exception as e: print('no cloud fogging prop')
g = G(r)
wp = g.wpos()
cpos = g.node(unreal.MaterialExpressionCameraPositionWS)
cen = g.vec('Center', C + (0.0,))
rad = g.scalar('Radius', R)
rnor = g.vec('RingNormal', RN)
sunc = g.vec('SunColor', (1.0, 0.92, 0.82))
inten = g.scalar('Intensity', 0.6)
densx = g.scalar('Densify', 3.0)
uvR = g.custom('float RR = length((P - Ce.xyz) / Ra); return ' + RU + ';', [('P', wp), ('Ce', cen), ('Ra', rad)], 'f2')
tl = g.tex(T_LIT, None, uvR)
tk = g.tex(T_BACK, None, uvR)
RING = r'''
float3 v = (P - Ce.xyz) / Ra;
float3 L = float3(-0.9848, 0.0, 0.1736);
float3 RN = normalize(Rn.xyz);
float b = dot(v, L); float cc = dot(v, v) - 1.0;
float sh = (b < 0.0 && b*b - cc > 0.0) ? 0.0 : 1.0;
float3 c = (Cp - Ce.xyz) / Ra;
float3 w = normalize(c - v);
float bw = dot(v, w);
float hid = (bw < 0.0 && bw*bw - cc > 0.0) ? 0.0 : 1.0;
float same = dot(c, RN) * dot(L, RN) > 0.0 ? 1.0 : 0.0;
float3 col = lerp(Tk, Tl, same);
float a = 1.0 - pow(saturate(1.0 - Al), max(Dx, 1.0));        // rings seen at a shallow angle are denser
return col * Sc.rgb * (In * a * (0.45 + 0.55*abs(dot(L, RN))) * sh * hid);
'''
rn = g.custom(RING, [('P', wp), ('Cp', cpos), ('Ce', cen), ('Ra', rad), ('Rn', rnor), ('Tl', tl, 'RGB'), ('Tk', tk, 'RGB'), ('Al', tl, 'A'),
                     ('Sc', sunc), ('In', inten), ('Dx', densx)], 'f3')
g.out(rn, pl.MP_EMISSIVE_COLOR)
g.done()

import i_tune
importlib.reload(i_tune)
mi_p = i_tune.mi('MI_Giant', '/Game/Scene1/Materials/M_Giant')
mi_r = i_tune.mi('MI_GiantRings', '/Game/Scene1/Materials/M_GiantRings')
i_tune.setp(mi_p, Intensity=0.6, RingNormal=RN + (0.0,))
i_tune.setp(mi_r, Intensity=0.6, RingNormal=RN + (0.0,))

# ---------- actors: local Z of both = ring normal = rotation axis (texture north) ----------
F = 'Sky/Giant'
a = s1u.spawn(unreal.StaticMeshActor, 'GasGiant', loc=C, folder=F)
b = s1u.spawn(unreal.StaticMeshActor, 'GasGiantRings', loc=C, folder=F)
rnv = unreal.Vector(*RN); rnv.normalize()
rot = unreal.MathLibrary.make_rot_from_z(rnv)
for act, mesh, mat in [(a, sph, mi_p), (b, rng, mi_r)]:
    c = act.static_mesh_component
    c.set_static_mesh(mesh); c.set_material(0, mat)
    c.set_mobility(unreal.ComponentMobility.MOVABLE); c.set_editor_property('cast_shadow', False)
    c.set_editor_property('affect_distance_field_lighting', False); c.set_editor_property('affect_dynamic_indirect_lighting', False)
    act.set_actor_rotation(rot, False)
a.set_actor_scale3d(unreal.Vector(R / 100.0, R / 100.0, R / 100.0))
s = R * RING_OUT / 100.0
b.set_actor_scale3d(unreal.Vector(s, s, s))
s1u.save()
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
print('giant ok')
