# S3, animatic v2: new draft effects.
#  - M_PP_Plasma v2: a glowing sheath flowing over the canopy from the nose backward (no rays from one point);
#  - M_PP_Veil: soft streaming veil over the glass; instances for the cloud layer (PPV_Cloud) and for the spray at touchdown (PPV_Spray);
#  - sparks of the cutter (Spark0..7 + M_Spark), lights PlasmaGlow and IndicatorLight.
# The underwater material gets its "Flood" parameter in n_underwater.py.
import unreal, importlib, mu, s1u, i_tune
importlib.reload(mu); importlib.reload(i_tune)
from mu import *
mpc = EAL.load_asset('/Game/Scene1/MPC_Otliv')
NOISE = r'''
struct U {
 float h2(float2 p){ return frac(sin(dot(p,float2(12.9898,78.233)))*43758.5453); }
 float n2(float2 p){ float2 i=floor(p), f=frac(p); f=f*f*(3-2*f);
   return lerp(lerp(h2(i),h2(i+float2(1,0)),f.x),lerp(h2(i+float2(0,1)),h2(i+float2(1,1)),f.x),f.y); }
 float fbm(float2 p){ return 0.5*n2(p) + 0.3*n2(p*2.13+7.1) + 0.2*n2(p*4.37+3.3); }
};
U u;
float inside = CS.r > 0.5 ? 1.0 : 0.0;
'''


def pp(name):
    m = new_mat(name)
    m.set_editor_property('material_domain', unreal.MaterialDomain.MD_POST_PROCESS)
    g = G(m)
    def st(i):
        n = g.node(unreal.MaterialExpressionSceneTexture); n.set_editor_property('scene_texture_id', i); return n
    return m, g, st(unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0), st(unreal.SceneTextureId.PPI_CUSTOM_STENCIL), \
        g.node(unreal.MaterialExpressionScreenPosition), g.mpc(mpc, 'SimTime')


def ppv(label, obj):
    v = s1u.spawn(unreal.PostProcessVolume, label, folder='Sky')
    v.set_editor_property('unbound', True); v.set_editor_property('blend_weight', 0.0)
    s = v.get_editor_property('settings')
    wb = unreal.WeightedBlendable(); wb.set_editor_property('weight', 1.0); wb.set_editor_property('object', obj)
    wbs = unreal.WeightedBlendables(); wbs.set_editor_property('array', [wb])
    s.set_editor_property('weighted_blendables', wbs); v.set_editor_property('settings', s)
    return v


# ---------- plasma v2 ----------
p, g, sc, cs, scr, t = pp('M_PP_Plasma')
PL = NOISE + r'''
float2 c = (UV - float2(0.5, 0.74)) * float2(1.78, 1.0);        // stagnation point: the nose, low in the view
float r = length(c); float a = atan2(c.y, c.x);
float2 w = float2(u.n2(c*2.3 + T*0.7), u.n2(c*2.3 + 9.0 - T*0.6)) - 0.5;
float f1 = u.n2(float2(a*1.5 + w.x*2.2, r*2.1 - T*2.4 + w.y*1.4));
float f2 = u.n2(float2(a*2.9 - w.y*2.4 + 4.0, r*4.4 - T*4.0 + w.x*1.8));
float f3 = u.n2(c*9.0 + float2(w.x*3.0, -T*5.0));
float sheath = saturate(f1*0.60 + f2*0.38 + f3*0.12);
float core = exp(-r*r*8.0);
float edge = smoothstep(1.45, 0.20, r);
float k = saturate((0.16 + 0.80*sheath) * (0.30 + 0.80*edge) + core*0.55);
float3 hot = lerp(float3(1.0, 0.40, 0.13), float3(1.0, 0.92, 0.82), saturate(core*1.1 + sheath*sheath*0.30));
float3 outside = lerp(SC.rgb, hot, k) + hot * core * 0.12;
return lerp(outside, SC.rgb, inside);
'''
o = g.custom(PL, [('SC', sc), ('CS', cs), ('UV', scr, 'ViewportUV'), ('T', t)], 'f3')
g.out(o, MP.MP_EMISSIVE_COLOR); g.done()
ppv('PPV_Plasma', p)

# ---------- veil: clouds and spray ----------
v, g, sc, cs, scr, t = pp('M_PP_Veil')
col = g.vec('Color', (0.80, 0.82, 0.85))
sz = g.vec('Scale', (1.2, 0.9, 3.1, 2.4))           # two noise layers: xy and zw cells per screen height
fl = g.vec('Flow', (0.0, -3.0, 0.3, -5.0))          # their scroll speeds
mk = g.vec('Mask', (0.0, 0.2, 0.95, 0.0))           # r: 1 = only near the bottom of the view; g..b: fade range in screen y
th = g.vec('Shape', (0.25, 1.6, 0.55, 0.0))         # threshold, contrast, base amount
VE = NOISE + r'''
float2 p = UV * float2(1.78, 1.0);
float n = u.fbm(float2(p.x*Sz.r + Fl.r*T, p.y*Sz.g + Fl.g*T))*0.6 + u.fbm(float2(p.x*Sz.b + Fl.b*T + 5.0, p.y*Sz.a + Fl.a*T + 2.0))*0.4;
float mask = lerp(1.0, smoothstep(Mk.g, Mk.b, UV.y), Mk.r);
float veil = saturate((n - Th.r)*Th.g + Th.b) * mask;
float3 outside = lerp(SC.rgb, Co.rgb, veil);
return lerp(outside, SC.rgb, inside);
'''
o = g.custom(VE, [('SC', sc), ('CS', cs), ('UV', scr, 'ViewportUV'), ('T', t), ('Co', col), ('Sz', sz, 'RGBA'), ('Fl', fl, 'RGBA'),
                  ('Mk', mk, 'RGBA'), ('Th', th, 'RGBA')], 'f3')
g.out(o, MP.MP_EMISSIVE_COLOR); g.done()
mi_c = i_tune.mi('MI_PP_Cloud', '/Game/Scene1/Materials/M_PP_Veil')
i_tune.setp(mi_c, Color=(0.80, 0.82, 0.85), Scale=(1.2, 0.9, 3.1, 2.4), Flow=(0.15, -3.0, 0.3, -5.0), Mask=(0.0, 0.2, 0.95, 0.0), Shape=(0.25, 1.6, 0.55, 0.0))
mi_s = i_tune.mi('MI_PP_Spray', '/Game/Scene1/Materials/M_PP_Veil')
i_tune.setp(mi_s, Color=(0.86, 0.90, 0.92), Scale=(2.6, 1.4, 6.5, 3.0), Flow=(0.4, 2.2, -0.6, 3.6), Mask=(1.0, 0.02, 0.80, 0.0), Shape=(0.24, 2.4, 0.30, 0.0))
ppv('PPV_Cloud', mi_c)
ppv('PPV_Spray', mi_s)

# ---------- sparks ----------
sp = new_mat('M_Spark', shading=unreal.MaterialShadingModel.MSM_UNLIT)
g = G(sp)
sc_ = g.vec('Color', (1.0, 0.72, 0.38)); sk = g.scalar('Brightness', 40.0)
g.out(g.custom('return C.rgb * K;', [('C', sc_), ('K', sk)], 'f3'), MP.MP_EMISSIVE_COLOR)
g.done()
sphere = EAL.load_asset('/Engine/BasicShapes/Sphere')
for i in range(8):
    a = s1u.spawn(unreal.StaticMeshActor, 'Spark%d' % i, loc=(0, 0, -1000), folder='Props/Sparks')
    c = a.static_mesh_component
    c.set_static_mesh(sphere); c.set_material(0, sp); c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_editor_property('cast_shadow', False)
    a.set_actor_scale3d(unreal.Vector(0.03, 0.03, 0.03))
    a.set_actor_hidden_in_game(True); a.set_is_temporarily_hidden_in_editor(True)

# ---------- lights ----------
for lb, colr, rad in [('PlasmaGlow', (1.0, 0.52, 0.22), 500.0), ('IndicatorLight', (0.25, 1.0, 0.4), 70.0)]:
    a = s1u.find(lb)
    if a is None:
        a = s1u.EAS.spawn_actor_from_class(unreal.PointLight, unreal.Vector(0, 0, -1000), s1u.R())
        a.set_actor_label(lb); a.set_folder_path('Props')
    lc = a.point_light_component
    lc.set_mobility(unreal.ComponentMobility.MOVABLE)
    lc.set_editor_property('intensity_units', unreal.LightUnits.CANDELAS)
    lc.set_editor_property('attenuation_radius', rad)
    lc.set_editor_property('cast_shadows', lb == 'PlasmaGlow')
    lc.set_light_color(unreal.LinearColor(*colr)); lc.set_intensity(0.0)
s1u.save()
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
print('s3 build2 ok')
