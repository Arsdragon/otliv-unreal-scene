# Mood and weather (SCENE1.md, "Смена настроения"): elements that the curves in s3_mood.py drive.
#  - M_PP_Weather (+ MI_PP_Weather, PPV_Weather): rain streaks, wind-driven water dust, drops and rivulets on glass, rainbow, dull flashes;
#  - Overcast: a high flat sheet of cloud over the whole area (instance of M_Spray);
#  - WaveVeil: a thin veil running ahead of the wave; WaveRoll: the dark roll cloud growing over the crest (ribbons on the wave);
#  - lights: two landing lights of the ship, the lamp of the drone.
# One new material, the rest are instances of M_Spray.
import unreal, importlib, mu, s1u, i_tune, f_wave_mesh as fw, r_boil
importlib.reload(mu); importlib.reload(i_tune)
from mu import *
mpc = EAL.load_asset('/Game/Scene1/MPC_Otliv')
mpcfx = EAL.load_asset('/Game/Scene1/MPC_OtlivFX')          # animated parameters of the post-process materials (made once by s6_fx_collection.py)

# ---------- weather post-process ----------
m = new_mat('M_PP_Weather')
m.set_editor_property('material_domain', unreal.MaterialDomain.MD_POST_PROCESS)
g = G(m)


def st(i):
    n = g.node(unreal.MaterialExpressionSceneTexture); n.set_editor_property('scene_texture_id', i); return n


sc = st(unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0)
sd = st(unreal.SceneTextureId.PPI_SCENE_DEPTH)
cs = st(unreal.SceneTextureId.PPI_CUSTOM_STENCIL)
cam = g.node(unreal.MaterialExpressionCameraVectorWS)
scr = g.node(unreal.MaterialExpressionScreenPosition)
t = g.mpc(mpc, 'SimTime')
rain = g.mpc(mpcfx, 'Rain')            # amount, slant, speed
dust = g.mpc(mpcfx, 'Dust')            # horizontal water dust: amount, speed
glass = g.mpc(mpcfx, 'Glass')          # drops on the glass: amount, speed, direction of the flow (x, y)
bow = g.mpc(mpcfx, 'Rainbow')          # rainbow amount
flash = g.mpc(mpcfx, 'Flash')          # flash inside the wall: level, sideways, up
WX = r'''
struct U {
 float h1(float x){ return frac(sin(x*127.1)*43758.5453); }
 float h2(float2 p){ return frac(sin(dot(p,float2(12.9898,78.233)))*43758.5453); }
 float n1(float x){ float i=floor(x), f=frac(x); f=f*f*(3-2*f); return lerp(h1(i),h1(i+1),f); }
 float n2(float2 p){ float2 i=floor(p), f=frac(p); f=f*f*(3-2*f);
   return lerp(lerp(h2(i),h2(i+float2(1,0)),f.x),lerp(h2(i+float2(0,1)),h2(i+float2(1,1)),f.x),f.y); }
};
U u;
// The direction of the view for this pixel. NOT from the CameraVector node: for sky pixels the engine builds it from a point
// at the far "infinite" depth, and beyond 58 degrees off the axis (the corners of the 10.5 mm cockpit lens) the length
// overflows - the vector becomes NaN and anything that does not clamp it paints the corner black. From the screen
// position and the axes of the camera it is exact at any angle and does not depend on depth.
float2 spn = float2(UV.x*2.0 - 1.0, 1.0 - UV.y*2.0);
float3 dir = normalize(ResolvedView.ViewForward + ResolvedView.ViewRight*(spn.x*ResolvedView.ClipToView[0][0]) + ResolvedView.ViewUp*(spn.y*ResolvedView.ClipToView[1][1]));
float inside = CS.r > 0.5 ? 1.0 : 0.0;
float d = min(SD.r, 1.0e8) / 100.0;
float2 suv = UV * float2(1.78, 1.0);
float3 outc = SC.rgb;
float lum = dot(outc, float3(0.3, 0.59, 0.11));
// wind-driven water dust: soft horizontal streaks and a thin veil
float dn = u.n2(float2(suv.x*1.3 - T*Ds.g, suv.y*7.0 + T*0.3))*0.6 + u.n2(float2(suv.x*3.1 - T*Ds.g*1.7, suv.y*15.0))*0.4;
float dv = saturate((dn - 0.42)*2.2) * Ds.r * saturate(d/6.0);
outc = lerp(outc, float3(0.60, 0.64, 0.68)*(0.25 + 0.9*lum), dv*0.55);
// a flash inside the wall of water: the wall and the cloud glow from within; far things light up, near things do not
float3 fpos = normalize(float3(1.0, Fx.g, Fx.b));
float fa = saturate(dot(dir, fpos));
float fa2 = fa*fa; float fa5 = fa2*fa2*fa; float fa48 = fa5*fa5; fa48 = fa48*fa48; fa48 = fa48*fa48*fa5*fa2*fa;
float fglow = (0.22*smoothstep(-0.15, 0.5, dir.x) + 0.9*fa5 + 1.3*fa48) * (0.7 + 0.3*u.n2(dir.yz*7.0 + 3.0));
// the glow comes from behind the wall and the cloud: what is dark in front of it stays darker, so their shapes remain
float3 fcol = float3(0.60, 0.72, 0.98) * Fx.r * fglow * 0.85 * (0.45 + 2.2*saturate(lum*1.5));
outc += fcol * saturate((d - 150.0)/600.0);
// rain in gusts: sparse long streaks close to the camera, dense and more slanted curtains toward the wave
float gust = u.n2(float2(suv.x*1.1 - T*0.55, suv.y*0.7 + T*0.12));
float gust2 = u.n2(float2(suv.x*2.7 - T*0.9 + 5.0, T*0.2));
float gk = 0.12 + 1.75*gust*gust;
float towave = 0.55 + 0.65*smoothstep(-0.3, 0.6, dir.x);
float streak = 0.0;
for (int i=0;i<4;i++){
  float fi = i;
  float scl = 20.0 + 18.0*fi;
  float slant = Rn.g * (0.50 + 0.42*fi) * (0.6 + 0.9*gust2);
  float2 p = float2(suv.x + suv.y*slant, suv.y);
  float cx = p.x*scl; float col = floor(cx); float hr = u.h1(col + 31.0*fi);
  float len = 0.09 + 0.20*u.h1(col*1.7 + 9.0*fi);
  float y = p.y*scl*len - T*Rn.b*(6.0 + 3.5*fi)*(0.7 + 0.6*hr) + hr*40.0;
  float cell = floor(y); float f = frac(y);
  float dens = Rn.r * (0.16 + 0.26*fi) * gk * lerp(1.0, towave, saturate(fi*0.5));
  float on = u.h2(float2(col, cell)) > (1.0 - saturate(dens)) ? 1.0 : 0.0;
  float xin = abs(frac(cx) - 0.5);
  float gate = saturate((d - (0.8 + 6.0*fi*fi)) / (2.0 + 10.0*fi));
  streak += on * smoothstep(0.13 - 0.02*fi, 0.0, xin) * smoothstep(0.0, 0.5, f) * smoothstep(1.0, 0.9, f) * gate * (0.55 + 0.15*fi);
}
float curtain = saturate(d/900.0) * Rn.r * (0.25 + 0.75*gust) * smoothstep(-0.10, 0.10, dir.x);
outc = lerp(outc, float3(0.42, 0.46, 0.52)*(0.30 + 0.8*lum), curtain*0.35);
outc += float3(0.70, 0.76, 0.82) * streak * 0.20 * saturate(Rn.r*3.0) * (0.5 + 0.7*lum) * (1.0 + 7.0*Fx.r*(0.25 + fglow));        // the rain in front of the flash turns to silver
// rainbow in the water dust: 42 degrees around the point opposite to the sun; pale, only against the sky, fading upward
float3 A = float3(-0.9848, 0.0, -0.1736);
float ang = degrees(acos(clamp(dot(dir, A), -1.0, 1.0)));
float bw = (ang - 39.6) / 3.4;
float inb = smoothstep(0.0, 0.35, bw) * (1.0 - smoothstep(0.65, 1.0, bw));
float3 spec = saturate(float3(1.5 - abs(bw*4.0 - 3.2), 1.5 - abs(bw*4.0 - 2.0), 1.5 - abs(bw*4.0 - 0.8)));
float sg = dot(spec, float3(0.333, 0.333, 0.333));
spec = lerp(float3(sg, sg, sg), spec, 0.6);
float bfade = lerp(1.0, 0.30, smoothstep(0.08, 0.50, dir.z)) * smoothstep(-0.02, 0.05, dir.z);
outc += spec * inb * Rb.r * 0.14 * saturate((d - 20000.0)/20000.0) * bfade;
// drops on the glass (canopy or helmet): running drops that creep along the flow, hesitate, wobble and leave a wet streak
// behind; tiny standing drops of several sizes that live for a while - the streaks wipe them away. Each drop is a small lens.
// Gl: r amount, g speed of the running drops, ba direction of the flow on the screen (x right, y down)
float gl = Gl.r;
if (gl > 0.001){
  float2 fdir = normalize(Gl.ba + float2(0.0, 1.0e-4));
  float2 fperp = float2(-fdir.y, fdir.x);
  float2 gs = float2(dot(suv, fperp), dot(suv, fdir));
  float2 off = float2(0.0, 0.0); float wet = 0.0; float rim = 0.0; float glint = 0.0; float wipe = 0.0; float glow2 = 0.0;
  for (int j=0;j<3;j++){
    float fj = j; float cols = 7.0 + 5.0*fj;
    float gx = gs.x*cols + 17.3*fj; float ci = floor(gx); float hc = u.h1(ci + 3.0 + 40.0*fj);
    float onc = (hc < gl*0.9) ? 1.0 : 0.0;
    float spd = (0.07 + 0.16*u.h1(ci*1.7 + 11.0)) * Gl.g;
    float tt2 = T + 0.9*sin(T*0.7 + hc*30.0);
    float per = 0.75 + 0.5*u.h1(ci*2.3 + 5.0);
    float ph = gs.y/per - tt2*spd/per + hc*17.0;
    float a = frac(ph);
    float wob = 0.20*sin(gs.y*6.0 + hc*40.0) + 0.09*sin(gs.y*15.0 + hc*9.0);
    float cx = frac(gx) - 0.5 - wob;
    float ay = (a - 0.88)*per*cols;
    float rh = 0.17 + 0.10*u.h1(ci*3.1 + floor(ph)*7.0);
    float2 hv2 = float2(cx, ay*0.62);
    float mh = onc * smoothstep(rh, rh*0.55, length(hv2));
    float tf = (a < 0.88) ? saturate(a/0.88) : 0.0;
    tf = tf*tf;
    float tw = 0.035 + 0.075*tf;
    float beads = 0.45 + 0.55*smoothstep(0.35, 0.65, u.n1(gs.y*38.0 + hc*70.0));
    float mt = onc * smoothstep(tw, tw*0.45, abs(cx)) * tf * lerp(beads, 1.0, tf);
    float m = max(mh, mt);
    off -= (fperp*cx + fdir*(ay*0.62)*(mh > mt ? 1.0 : 0.0)) / cols * m * 1.5;
    wet = max(wet, m);
    rim += mh * smoothstep(rh*0.5, rh*0.95, length(hv2)) + 0.7 * mt * smoothstep(tw*0.45, tw*0.95, abs(cx));
    glint += mh * smoothstep(rh*0.30, 0.0, length(hv2 - float2(-0.3, -0.3)*rh));
    glow2 += mh * smoothstep(rh*0.45, 0.0, length(hv2 - float2(0.05, 0.45)*rh));
    wipe = max(wipe, onc * smoothstep(0.34, 0.14, abs(cx)) * tf);
  }
  for (int k=0;k<3;k++){
    float fk = k; float sc2 = 15.0 + 14.0*fk;
    float2 q = suv*sc2 + 31.0*fk; float2 c = floor(q); float2 f = frac(q) - 0.5;
    float r = u.h2(c + 5.0 + fk);
    float age = frac(r*13.0 + T*(0.04 + 0.07*u.h2(c + 2.0)));
    float alive = smoothstep(0.0, 0.10, age) * (1.0 - smoothstep(0.8, 1.0, age));
    float2 o = (float2(u.h2(c + 1.3), u.h2(c + 7.9)) - 0.5) * 0.7;
    float rad = max((0.09 + 0.24*r*r) * alive, 1.0e-3);
    float2 dv2 = (f - o)*float2(1.0, 0.85);
    float dd = length(dv2);
    float on2 = (u.h2(c + 9.0) < gl*(0.60 - 0.12*fk)) ? 1.0 : 0.0;
    float m = on2 * smoothstep(rad, rad*0.6, dd) * (1.0 - wipe) * (alive > 0.02 ? 1.0 : 0.0);
    off -= dv2 / sc2 * m * 1.6;
    wet = max(wet, m); rim += m * smoothstep(rad*0.5, rad*0.95, dd);
    glint += m * smoothstep(rad*0.30, 0.0, length(dv2 - float2(-0.30, -0.32)*rad));
    glow2 += m * smoothstep(rad*0.45, 0.0, length(dv2 - float2(0.05, 0.45)*rad));
  }
  float2 ruv = clamp(UV + off*float2(0.5625, 1.0), 0.002, 0.998);
  float3 refr = SceneTextureLookup(ViewportUVToSceneTextureUV(ruv, 14), 14, false).rgb;
  float3 wcol = refr*0.95 + float3(0.04, 0.045, 0.05)*(0.3 + lum);
  wcol += fcol * (0.6 + 0.8*saturate(dot(refr, float3(0.3, 0.59, 0.11))*1.5)) * saturate((d - 150.0)/600.0);     // the flash seen through the drop
  wcol *= 1.0 - 0.42*saturate(rim);
  wcol += float3(0.75, 0.80, 0.86) * saturate(glint) * (0.10 + 0.5*lum);
  wcol += float3(0.20, 0.27, 0.34) * saturate(glow2) * 0.16;                                    // light of the cabin (or of the helmet) in the lower edge
  outc = lerp(outc, wcol, saturate(wet)*0.93);
}
return lerp(outc, SC.rgb, inside);
'''
o = g.custom(WX, [('SC', sc), ('SD', sd), ('CS', cs), ('CV', cam), ('UV', scr, 'ViewportUV'), ('T', t), ('Rn', rain), ('Ds', dust),
                  ('Gl', glass), ('Rb', bow), ('Fx', flash)], 'f3')
g.out(o, MP.MP_EMISSIVE_COLOR)
g.done()
mi = i_tune.mi('MI_PP_Weather', '/Game/Scene1/Materials/M_PP_Weather')
ppv = s1u.spawn(unreal.PostProcessVolume, 'PPV_Weather', folder='Sky')
ppv.set_editor_property('unbound', True); ppv.set_editor_property('blend_weight', 0.0)
s = ppv.get_editor_property('settings')
wb = unreal.WeightedBlendable(); wb.set_editor_property('weight', 1.0); wb.set_editor_property('object', mi)
wbs = unreal.WeightedBlendables(); wbs.set_editor_property('array', [wb])
s.set_editor_property('weighted_blendables', wbs); ppv.set_editor_property('settings', s)

# ---------- overcast sheet ----------
ov = i_tune.mi('MI_Overcast', '/Game/Scene1/Materials/M_Spray')
i_tune.setp(ov, ScaleA=(55.0, 55.0, 0.02, 0.01), ScaleB=(170.0, 170.0, -0.03, 0.02), Offset=(0.0, 0.0, 0.0, 0.0), Color=(0.30, 0.32, 0.35),
            SunColor=(0.5, 0.48, 0.44), Profile=(0.0001, 0.0, 0.10, 6.0), Backlit=0.6, Density=0.0, Threshold=0.18, Contrast=2.2, Gain=1.0)
a = s1u.spawn(unreal.StaticMeshActor, 'Overcast', loc=(2000000.0, 0.0, 260000.0), folder='Sky')
c = a.static_mesh_component
c.set_static_mesh(EAL.load_asset('/Engine/BasicShapes/Plane')); c.set_material(0, ov)
c.set_mobility(unreal.ComponentMobility.MOVABLE); c.set_editor_property('cast_shadow', False)
c.set_editor_property('affect_distance_field_lighting', False)
a.set_actor_scale3d(unreal.Vector(300000.0, 300000.0, 1.0))          # 300 km
a.set_actor_rotation(unreal.Rotator(pitch=180.0, yaw=0.0, roll=0.0), False)   # face down (the material is two-sided anyway)


# ---------- roll cloud material: flat leaden base above the crest, lighter shoulders; no scene fog (its own haze) ----------
rm = new_mat('M_Roll', shading=unreal.MaterialShadingModel.MSM_UNLIT, blend=unreal.BlendMode.BLEND_TRANSLUCENT, two_sided=True)
rm.set_editor_property('use_translucency_vertex_fog', False)
g = G(rm)
r_uv = g.node(unreal.MaterialExpressionTextureCoordinate)
r_t = g.mpc(mpc, 'SimTime')
r_sa = g.vec('ScaleA', (0.10, 1.1, 0.002, -0.02)); r_sb = g.vec('ScaleB', (0.45, 2.8, -0.003, -0.04)); r_of = g.vec('Offset', (6.1, 0.5, 0.0, 0.0))
r_col = g.vec('Color', (0.07, 0.08, 0.095)); r_hz = g.vec('Haze', (0.36, 0.40, 0.46, 0.0))
r_pf = g.vec('Profile', (0.07, 0.8, 0.5, 0.0))          # base height (share of the ribbon), falloff power to the top, extra density at the base
r_de = g.scalar('Density', 0.0); r_th = g.scalar('Threshold', -0.2); r_cn = g.scalar('Contrast', 2.0); r_gn = g.scalar('Gain', 1.0)
r_fd = g.node(unreal.MaterialExpressionDepthFade); r_fd.set_editor_property('fade_distance_default', 6000.0)
RL = r"""
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
float base = Pf.r * (0.6 + 0.8*s.vn(float2(q.x*SA.x*0.7, 3.0)));
float bot = smoothstep(base*0.45, base, v);
float top = pow(saturate(1.0 - v), Pf.g);
float body = saturate((n - Th) * Cn + (1.0 - v)*Pf.b);
Op = saturate(bot * top * body * De) * FD;
float3 c = Co.rgb * lerp(0.55, 1.6, saturate(v*1.3)) * (0.75 + 0.5*n);
c = lerp(c, Hz.rgb, Hz.a);
return c * Gn;
"""
r_sp = g.custom(RL, [('UV', r_uv), ('T', r_t), ('SA', r_sa, 'RGBA'), ('SB', r_sb, 'RGBA'), ('Of', r_of, 'RGBA'), ('Co', r_col), ('Hz', r_hz, 'RGBA'),
                     ('Pf', r_pf, 'RGBA'), ('De', r_de), ('Th', r_th), ('Cn', r_cn), ('Gn', r_gn), ('FD', r_fd)], 'f3', outs=[('Op', 'f1')])
g.out(r_sp, MP.MP_EMISSIVE_COLOR); g.out(r_sp, MP.MP_OPACITY, 'Op'); g.done()


def roll_rows(y):
    """the roll hangs over the crest and leans ahead of it; its base follows the height of the crest"""
    sc, lean, xo = fw.col_params(y)
    hc = 2100.0 * sc
    k = 0.9 + 0.2 * (0.5 + 0.5 * fw.noise1(y / 9000.0, 12))
    return [(xo + dx, hc + dz * k) for dx, dz in [(-500, 90), (-1150, 280), (-1500, 620), (-1350, 980), (-700, 1300), (500, 1520)]]


# ---------- veil ahead of the wave, roll cloud over the crest ----------
def smooth_rows(x_from_crest, heights):
    """ribbon cross-section that changes only slowly along the crest (no jagged top edge)"""
    def rows(y):
        sc, lean, xo = fw.col_params(y)
        hv = 0.9 + 0.2 * (0.5 + 0.5 * fw.noise1(y / 9000.0, 12))
        return [(x_from_crest + xo + dx, dz * hv) for dx, dz in heights]
    return rows


wave = s1u.find('Wave')
ITEMS = [('WaveVeil', '/Game/Scene1/Wave/SM_WaveVeil', smooth_rows(-9000.0, [(0, 0), (-200, 600), (-500, 1500), (-900, 2600), (-1400, 3800)]),
          dict(ScaleA=(0.05, 0.3, 0.001, -0.01), ScaleB=(0.17, 0.7, -0.002, -0.02), Offset=(2.3, 0.2, 0.0, 0.0), Color=(0.42, 0.46, 0.52),
               SunColor=(0.8, 0.74, 0.64), Profile=(0.02, 2.0, 0.20, 5.0), Backlit=0.3, Density=0.0, Threshold=-0.15, Contrast=0.8, Gain=1.0)),
         ('WaveRoll', '/Game/Scene1/Wave/SM_WaveRoll', roll_rows,
          dict(ScaleA=(0.10, 1.1, 0.002, -0.02), ScaleB=(0.45, 2.8, -0.003, -0.04), Offset=(6.1, 0.5, 0.0, 0.0), Color=(0.07, 0.08, 0.095),
               Haze=(0.36, 0.40, 0.46, 0.0), Profile=(0.07, 0.8, 0.5, 0.0), Density=0.0, Threshold=-0.2, Contrast=2.0, Gain=1.0))]
for lb, asset, rows, params in ITEMS:
    sm = r_boil.ribbon(asset, rows)
    mi_r = i_tune.mi('MI_' + lb, '/Game/Scene1/Materials/M_Spray')
    if lb == 'WaveRoll':
        MEL.set_material_instance_parent(mi_r, rm)
    i_tune.setp(mi_r, **params)
    b = s1u.spawn(unreal.StaticMeshActor, lb, loc=(0, 0, 0), folder='Wave')
    c = b.static_mesh_component
    c.set_static_mesh(sm); c.set_material(0, mi_r)
    c.set_editor_property('translucency_sort_priority', 5 if lb == 'WaveRoll' else 0)   # the roll is drawn after the overcast sheet
    c.set_mobility(unreal.ComponentMobility.MOVABLE); c.set_editor_property('cast_shadow', False)
    c.set_editor_property('affect_distance_field_lighting', False)
    b.set_actor_location(wave.get_actor_location(), False, False)
    b.attach_to_actor(wave, '', unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)

# ---------- warm lights: landing lights of the ship, lamp of the drone ----------
for lb in ('ShipLight_L', 'ShipLight_R'):
    a = s1u.find(lb)
    if a is None:
        a = s1u.EAS.spawn_actor_from_class(unreal.SpotLight, unreal.Vector(0, 0, -1000), s1u.R())
        a.set_actor_label(lb); a.set_folder_path('Chaika')
    lc = a.get_component_by_class(unreal.SpotLightComponent)
    lc.set_mobility(unreal.ComponentMobility.MOVABLE)
    lc.set_editor_property('intensity_units', unreal.LightUnits.CANDELAS)
    lc.set_editor_property('attenuation_radius', 6000.0)
    lc.set_editor_property('outer_cone_angle', 24.0); lc.set_editor_property('inner_cone_angle', 12.0)
    lc.set_editor_property('cast_shadows', False)
    lc.set_light_color(unreal.LinearColor(1.0, 0.84, 0.62)); lc.set_intensity(0.0)
a = s1u.find('DroneLamp')
if a is None:
    a = s1u.EAS.spawn_actor_from_class(unreal.PointLight, unreal.Vector(0, 0, -1000), s1u.R())
    a.set_actor_label('DroneLamp'); a.set_folder_path('Props')
lc = a.point_light_component
lc.set_mobility(unreal.ComponentMobility.MOVABLE)
lc.set_editor_property('intensity_units', unreal.LightUnits.CANDELAS)
lc.set_editor_property('attenuation_radius', 500.0); lc.set_editor_property('cast_shadows', False)
lc.set_light_color(unreal.LinearColor(1.0, 0.86, 0.55)); lc.set_intensity(0.0)

# ---------- S5: the light of a flash; puffs of steam at the cutter ----------
fl_a = s1u.find('FlashLight')
if fl_a is None:
    fl_a = s1u.EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 50000), unreal.Rotator(pitch=-12.0, yaw=180.0, roll=0.0))
    fl_a.set_actor_label('FlashLight'); fl_a.set_folder_path('Sky')
flc = fl_a.get_component_by_class(unreal.DirectionalLightComponent)
flc.set_mobility(unreal.ComponentMobility.MOVABLE); flc.set_editor_property('cast_shadows', False)
flc.set_editor_property('atmosphere_sun_light', False)
flc.set_light_color(unreal.LinearColor(0.62, 0.74, 1.0)); flc.set_intensity(0.0)
pm = new_mat('M_Puff', shading=unreal.MaterialShadingModel.MSM_UNLIT, blend=unreal.BlendMode.BLEND_TRANSLUCENT, two_sided=True)
g = G(pm)
p_uv = g.node(unreal.MaterialExpressionTextureCoordinate); p_t = g.mpc(mpc, 'SimTime')
p_fd = g.scalar('Fade', 0.0); p_sd = g.scalar('Seed', 0.0); p_col = g.vec('Color', (0.80, 0.83, 0.86))
PF = r"""
struct S { float h2(float2 p){ return frac(sin(dot(p,float2(12.9898,78.233)))*43758.5453); }
 float vn(float2 p){ float2 i=floor(p), f=frac(p); f=f*f*(3-2*f);
   return lerp(lerp(h2(i),h2(i+float2(1,0)),f.x),lerp(h2(i+float2(0,1)),h2(i+float2(1,1)),f.x),f.y); } };
S s;
float2 c = UV - 0.5; float r = length(c)*2.0;
float n = 0.6*s.vn(c*4.0 + Sd*7.0 + float2(0.0, -T*0.4)) + 0.4*s.vn(c*9.0 + Sd*3.0 + float2(T*0.3, -T*0.7));
Op = saturate((1.0 - r*r) * (0.35 + 0.9*n) - 0.15) * Fd;
return Co.rgb;
"""
p_sp = g.custom(PF, [('UV', p_uv), ('T', p_t), ('Fd', p_fd), ('Sd', p_sd), ('Co', p_col)], 'f3', outs=[('Op', 'f1')])
g.out(p_sp, MP.MP_EMISSIVE_COLOR); g.out(p_sp, MP.MP_OPACITY, 'Op'); g.done()
for i in range(3):
    mi_p = i_tune.mi('MI_Puff%d' % i, '/Game/Scene1/Materials/M_Puff')
    i_tune.setp(mi_p, Fade=0.0, Seed=float(i) * 1.37)
    a = s1u.spawn(unreal.StaticMeshActor, 'Puff%d' % i, loc=(0, 0, -1000), folder='Props/Sparks')
    c = a.static_mesh_component
    c.set_static_mesh(EAL.load_asset('/Engine/BasicShapes/Plane')); c.set_material(0, mi_p)
    c.set_mobility(unreal.ComponentMobility.MOVABLE); c.set_editor_property('cast_shadow', False)
    c.set_editor_property('affect_distance_field_lighting', False)
    a.set_actor_hidden_in_game(True); a.set_is_temporarily_hidden_in_editor(True)
s1u.save()
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
print('mood build ok')
