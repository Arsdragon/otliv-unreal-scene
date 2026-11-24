# S3 (animatic): draft elements that the key frames did not need.
#  - OrbitPlanet: ocean sphere under the level (same centre and radius as the Sky Atmosphere planet) with thin white arcs of waves;
#  - PPV_Plasma + M_PP_Plasma: glow and streaks on the canopy during atmospheric entry;
#  - Wave2: the next wave, 62 km behind the first one;
#  - CAM_Film: the first-person camera of the whole film;
#  - slow auto-exposure (the animatic is rendered several times slower than real time).
import unreal, importlib, mu, s1u
importlib.reload(mu)
from mu import *
mpc = EAL.load_asset('/Game/Scene1/MPC_Otliv')

# ---------- ocean seen from orbit ----------
m = new_mat('M_OrbitOcean')
g = G(m)
wp = g.wpos()
OC = r'''
struct O {
 float h2(float2 p){ return frac(sin(dot(p,float2(12.9898,78.233)))*43758.5453); }
 float vn(float2 p){ float2 i=floor(p), f=frac(p); f=f*f*(3-2*f);
   return lerp(lerp(h2(i),h2(i+float2(1,0)),f.x),lerp(h2(i+float2(0,1)),h2(i+float2(1,1)),f.x),f.y); }
};
O o;
float3 pk = P / 100000.0;                                   // km
float ph = (pk.x + 0.00035*pk.y*pk.y + 180.0*o.vn(pk.xy/900.0)) / 700.0;   // wave fronts: arcs every ~700 km
float fr = abs(frac(ph) - 0.5);
float arc = smoothstep(0.012, 0.0, fr) * smoothstep(0.25, 0.6, o.vn(pk.xy/1500.0 + 7.0) + 0.3);
Rough = lerp(0.14, 0.6, arc);
return lerp(float3(0.006, 0.020, 0.034) * (0.8 + 0.4*o.vn(pk.xy/300.0)), float3(0.78, 0.80, 0.80), arc);
'''
oc = g.custom(OC, [('P', wp)], 'f3', outs=[('Rough', 'f1')])
g.out(oc, MP.MP_BASE_COLOR)
g.out(oc, MP.MP_ROUGHNESS, 'Rough')
g.done()
RP = 6.36e8                         # cm: Sky Atmosphere ground radius
a = s1u.spawn(unreal.StaticMeshActor, 'OrbitPlanet', loc=(0, 0, -RP - 20000.0), folder='Sky')
c = a.static_mesh_component
c.set_static_mesh(EAL.load_asset('/Game/Scene1/Sky/SM_GiantSphere')); c.set_material(0, m)
c.set_mobility(unreal.ComponentMobility.MOVABLE); c.set_editor_property('cast_shadow', False)
c.set_editor_property('affect_distance_field_lighting', False); c.set_editor_property('affect_dynamic_indirect_lighting', False)
a.set_actor_scale3d(unreal.Vector(RP / 100.0, RP / 100.0, RP / 100.0))

# ---------- plasma on the canopy ----------
p = new_mat('M_PP_Plasma')
p.set_editor_property('material_domain', unreal.MaterialDomain.MD_POST_PROCESS)
g = G(p)


def st(i):
    n = g.node(unreal.MaterialExpressionSceneTexture)
    n.set_editor_property('scene_texture_id', i)
    return n


sc = st(unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0)
cs = st(unreal.SceneTextureId.PPI_CUSTOM_STENCIL)
scr = g.node(unreal.MaterialExpressionScreenPosition)
t = g.mpc(mpc, 'SimTime')
PL = r'''
struct U {
 float h2(float2 p){ return frac(sin(dot(p,float2(12.9898,78.233)))*43758.5453); }
 float n2(float2 p){ float2 i=floor(p), f=frac(p); f=f*f*(3-2*f);
   return lerp(lerp(h2(i),h2(i+float2(1,0)),f.x),lerp(h2(i+float2(0,1)),h2(i+float2(1,1)),f.x),f.y); }
};
U u;
float inside = CS.r > 0.5 ? 1.0 : 0.0;
float2 c = (UV - float2(0.5, 0.60)) * float2(1.78, 1.0);
float r = length(c); float a = atan2(c.y, c.x);
float sk = u.n2(float2(a*5.0, r*2.5 - T*4.0))*0.6 + u.n2(float2(a*15.0 + 3.0, r*6.0 - T*9.0))*0.4;
float gl = saturate(1.15 - r*0.85);
float3 col = lerp(float3(1.0, 0.33, 0.10), float3(1.0, 0.86, 0.70), saturate(sk*gl*1.5));
float k = saturate((0.40 + 0.85*sk) * (0.50 + 0.70*gl));
float3 outside = lerp(SC.rgb, col, k) + col * sk * 0.2;
return lerp(outside, SC.rgb, inside);
'''
pl = g.custom(PL, [('SC', sc), ('CS', cs), ('UV', scr, 'ViewportUV'), ('T', t)], 'f3')
g.out(pl, MP.MP_EMISSIVE_COLOR)
g.done()
ppv = s1u.spawn(unreal.PostProcessVolume, 'PPV_Plasma', folder='Sky')
ppv.set_editor_property('unbound', True)
ppv.set_editor_property('blend_weight', 0.0)
s = ppv.get_editor_property('settings')
wb = unreal.WeightedBlendable(); wb.set_editor_property('weight', 1.0); wb.set_editor_property('object', p)
wbs = unreal.WeightedBlendables(); wbs.set_editor_property('array', [wb])
s.set_editor_property('weighted_blendables', wbs)
ppv.set_editor_property('settings', s)

# ---------- the next wave ----------
w1 = s1u.find('Wave')
w2 = s1u.spawn(unreal.StaticMeshActor, 'Wave2', loc=(1.0e7, 0, 0), folder='Wave')
c = w2.static_mesh_component
c.set_static_mesh(EAL.load_asset('/Game/Scene1/Wave/SM_Wave')); c.set_material(0, EAL.load_asset('/Game/Scene1/Materials/MI_Wave'))
c.set_mobility(unreal.ComponentMobility.MOVABLE); c.set_editor_property('cast_shadow', False)
c.set_editor_property('affect_distance_field_lighting', False)
w2.set_actor_hidden_in_game(True); w2.set_is_temporarily_hidden_in_editor(True)

# ---------- film camera ----------
cam = s1u.spawn(unreal.CineCameraActor, 'CAM_Film', loc=(0, 0, 300), folder='Cameras')
cc = cam.get_cine_camera_component()
fb = cc.filmback; fb.sensor_width = 36.0; fb.sensor_height = 20.25; cc.set_editor_property('filmback', fb)
fs = cc.focus_settings; fs.focus_method = unreal.CameraFocusMethod.DISABLE; cc.set_editor_property('focus_settings', fs)
cc.set_editor_property('current_aperture', 16.0)

# ---------- cutter light at the wreck ----------
cl = s1u.find('CutterLight')
if cl is None:
    cl = s1u.EAS.spawn_actor_from_class(unreal.PointLight, unreal.Vector(0, 0, 0), s1u.R())
    cl.set_actor_label('CutterLight'); cl.set_folder_path('Props')
    lc = cl.point_light_component
    lc.set_mobility(unreal.ComponentMobility.MOVABLE)
    lc.set_editor_property('intensity_units', unreal.LightUnits.CANDELAS)
    lc.set_editor_property('attenuation_radius', 600.0)
    lc.set_editor_property('cast_shadows', False)
    lc.set_light_color(unreal.LinearColor(0.75, 0.9, 1.0))
    lc.set_intensity(0.0)

# ---------- slow exposure adaptation ----------
pg = s1u.find('PPV_Global'); sg_ = pg.get_editor_property('settings')
for k, v in [('override_auto_exposure_speed_up', True), ('auto_exposure_speed_up', 0.5), ('override_auto_exposure_speed_down', True), ('auto_exposure_speed_down', 0.25)]:
    sg_.set_editor_property(k, v)
pg.set_editor_property('settings', sg_)
s1u.save()
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
print('s3 build ok')
