# Underwater post-process (KF5), v3. It must read as water, not as space:
#  - a bright patch of the surface above with rays of light spreading from it;
#  - the water body darkens to almost black downwards; murk is large, soft, without bright spots;
#  - bubbles of different sizes in streams, smeared along their motion, a few big ones right at the glass;
#  - rivulets and tiny bubbles crawling over the glass.
# The ship interior is excluded by custom stencil 1 (set on all Chaika components).
import unreal, importlib, mu, s1u
importlib.reload(mu)
from mu import *
mpc = EAL.load_asset('/Game/Scene1/MPC_Otliv')
m = new_mat('M_PP_Underwater')
m.set_editor_property('material_domain', unreal.MaterialDomain.MD_POST_PROCESS)
g = G(m)


def st(i):
    n = g.node(unreal.MaterialExpressionSceneTexture)
    n.set_editor_property('scene_texture_id', i)
    return n


sc = st(unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0)
sd = st(unreal.SceneTextureId.PPI_SCENE_DEPTH)
cs = st(unreal.SceneTextureId.PPI_CUSTOM_STENCIL)
cam = g.node(unreal.MaterialExpressionCameraVectorWS)
scr = g.node(unreal.MaterialExpressionScreenPosition)
t = g.mpc(mpc, 'SimTime')
deep = g.vec('Deep', (0.0008, 0.005, 0.009))
shal = g.vec('Shallow', (0.035, 0.20, 0.23))
lcol = g.vec('LightColor', (0.50, 0.86, 0.82))
sdir = g.vec('SurfaceDir', (0.694, -0.324, 0.643))          # where the bright patch of the surface is (world direction)
lgt = g.vec('Light', (0.55, 0.75, 0.0, 0.0))                # surface glow, rays
bmo = g.vec('BubbleMotion', (0.22, -1.0, 0.0, 0.0))         # screen direction of the bubble streams (x right, y down)
mpcfx = EAL.load_asset('/Game/Scene1/MPC_OtlivFX')
amt = g.mpc(mpcfx, 'Amounts')          # particles, bubbles, big bubbles at the glass, rivulets
vis = g.scalar('Visibility', 7.0)
flood = g.mpc(mpcfx, 'Flood')           # r: how high the water has risen over the glass (1 = fully under water), g: blackout
UW = r'''
struct U {
 float h1(float x){ return frac(sin(x*127.1)*43758.5453); }
 float h2(float2 p){ return frac(sin(dot(p,float2(12.9898,78.233)))*43758.5453); }
 float h3(float3 p){ return frac(sin(dot(p, float3(127.1,311.7,74.7)))*43758.5453); }
 float n1(float x){ float i=floor(x), f=frac(x); f=f*f*(3-2*f); return lerp(h1(i),h1(i+1),f); }
 float n2(float2 p){ float2 i=floor(p), f=frac(p); f=f*f*(3-2*f);
   return lerp(lerp(h2(i),h2(i+float2(1,0)),f.x),lerp(h2(i+float2(0,1)),h2(i+float2(1,1)),f.x),f.y); }
 float n3(float3 p){ float3 i=floor(p), f=frac(p); f=f*f*(3-2*f);
   return lerp(lerp(lerp(h3(i),h3(i+float3(1,0,0)),f.x), lerp(h3(i+float3(0,1,0)),h3(i+float3(1,1,0)),f.x), f.y),
               lerp(lerp(h3(i+float3(0,0,1)),h3(i+float3(1,0,1)),f.x), lerp(h3(i+float3(0,1,1)),h3(i+float3(1,1,1)),f.x), f.y), f.z); }
};
U u;
// the direction of the view from the screen position and the axes of the camera (the CameraVector node turns into NaN for sky
// pixels in the corners of the wide cockpit lens - see s3_mood_build.py)
float2 spn = float2(UV.x*2.0 - 1.0, 1.0 - UV.y*2.0);
float3 dir = normalize(ResolvedView.ViewForward + ResolvedView.ViewRight*(spn.x*ResolvedView.ClipToView[0][0]) + ResolvedView.ViewUp*(spn.y*ResolvedView.ClipToView[1][1]));
float inside = CS.r > 0.5 ? 1.0 : 0.0;
float d = min(SD.r, 1.0e7) / 100.0;
float2 suv = UV*float2(1.78, 1.0);
// water body: darker downwards, large soft murk
float upk = saturate(dir.z*0.9 + 0.30);
float3 fogc = lerp(Dp.rgb, Sh.rgb, upk*upk);
float turb = 0.6*u.n3(dir*1.3 + float3(T*0.03, T*0.015, -T*0.05)) + 0.4*u.n3(dir*2.7 + float3(-T*0.02, 4.0, T*0.04));
fogc *= 0.82 + 0.32*turb;
// bright patch of the surface and rays spreading from it
float3 Ls = normalize(Sv.xyz);
float3 a1 = normalize(cross(Ls, float3(0,1,0))); float3 a2 = cross(Ls, a1);
float ca = dot(dir, Ls);
float rr = acos(clamp(ca, -1.0, 1.0));
float ang = atan2(dot(dir,a2), dot(dir,a1));
float glow = exp(-rr*rr*6.0);
float rays = pow(saturate(u.n1(ang*7.0 + T*0.04)*0.6 + u.n1(ang*19.0 - T*0.07 + 5.0)*0.4), 2.2) * exp(-rr*1.5) * smoothstep(0.03, 0.22, rr);
fogc += Lc.rgb * (glow*Lg.r + rays*Lg.g);
// motion frame of the streams
float2 mdir = normalize(Bm.xy);
float2 perp = float2(-mdir.y, mdir.x);
float2 sm = float2(dot(suv, perp), dot(suv, mdir));
// suspended particles: soft, smeared, sparse
float spk = 0.0;
for (int i=0;i<2;i++){
  float ps = 26.0 + 19.0*i;
  float2 q = sm*ps + float2(11.0*i, -T*(2.0 + 1.0*i));
  float2 c = floor(q); float2 f = frac(q) - 0.5;
  float r = u.h2(c + 5.0*i);
  float2 o = (float2(u.h2(c+3.1), u.h2(c+7.7)) - 0.5) * 0.6;
  float rad = 0.05 + 0.10*r;
  spk += (r > 0.72 ? 1.0 : 0.0) * smoothstep(rad, 0.0, length((f - o)*float2(1.0, 0.35))) * (0.4 + 0.6*r);
}
// bubbles: many small ones of very different sizes, rising in wandering streams, smeared by their own motion
float stream = smoothstep(0.38, 0.72, u.n2(float2(sm.x*3.1 + 3.0, sm.y*0.30 - T*0.10))) * (0.6 + 0.4*u.n2(float2(sm.x*9.0, sm.y*0.8 - T*0.3)));
float bub = 0.0;
for (int k=0;k<5;k++){
  float fk = k;
  float bs = 13.0 * pow(1.55, fk);
  float spdk = (1.5 + 0.9*u.h1(fk*3.7 + 1.0)) * (1.0 - 0.10*fk);
  float2 p = float2(sm.x*bs + 7.0*fk, sm.y*bs*0.42 - T*spdk*bs*0.16);
  float2 c = floor(p); float2 f = frac(p) - 0.5;
  float r = u.h2(c + 31.0*fk);
  float2 o = float2((u.h2(c + 1.7) - 0.5)*0.6 + 0.10*sin(T*(3.0 + 4.0*r) + r*40.0), (u.h2(c + 9.2) - 0.5)*0.5);
  float rad = 0.06 + 0.17*r*r*r;
  float2 q = (f - o) * float2(1.0, 0.85);
  float dd = length(q);
  float soft = smoothstep(rad, rad*0.25, dd);
  float ring = (r > 0.8 ? 1.0 : 0.0) * smoothstep(rad, rad*0.8, dd) * smoothstep(rad*0.3, rad*0.9, dd);
  float dens = (0.07 + 0.80*stream*stream) * (1.0 - 0.08*fk);
  float onb = (u.h2(c + 57.0 + 3.0*fk) < dens) ? 1.0 : 0.0;
  bub += onb * (soft*0.65 + ring*0.6) / (1.0 + 0.45*fk);
}
// a few big soft bubbles right at the glass
float2 pn = sm*2.6 + float2(0.2*sin(T*0.7), -T*0.55);
float2 cn = floor(pn); float2 fn = frac(pn) - 0.5;
float rn = u.h2(cn + 77.0);
float2 on = (float2(u.h2(cn+2.9), u.h2(cn+5.3)) - 0.5) * 0.4;
float radn = 0.16 + 0.16*rn;
float ddn = length((fn - on)*float2(1.0, 0.7));
float nearb = (rn > 0.82 ? 1.0 : 0.0) * smoothstep(radn, radn*0.55, ddn) * (0.25 + 0.75*smoothstep(radn*0.35, radn*0.98, ddn));
// rivulets and tiny bubbles crawling over the glass
float nx = sm.x*11.0; float ci = floor(nx); float hr = u.h1(ci + 3.0);
float wob = 0.28*sin(sm.y*5.0 + hr*40.0 + T*0.3) + 0.12*sin(sm.y*13.0 + hr*17.0);
float dx = abs(frac(nx) - 0.5 - wob);
float seg = smoothstep(0.35, 0.65, u.n1(sm.y*3.0 + T*(0.25 + 0.3*hr) + hr*50.0));
float on_ = hr > 0.45 ? 1.0 : 0.0;
float riv = on_ * smoothstep(0.045, 0.0, dx) * seg;
float by = frac(sm.y*6.0 + T*(0.15 + 0.2*hr) + hr*9.0) - 0.5;
riv += on_ * smoothstep(0.10, 0.03, length(float2(dx*3.0, by))) * 0.9;
// compose
float f0 = 1.0 - exp(-d / max(Vi, 0.1));
float3 ab = exp(-float3(0.42, 0.07, 0.05) * d);
float3 outside = lerp(SC.rgb * ab, fogc, f0);
float lum = 0.30 + 0.70*upk;
outside += Lc.rgb * lum * (spk*Am.r + bub*Am.g + nearb*Am.b + riv*Am.a);
// water rising over the glass from the bottom (the second before the impact), then a blackout
float wl = 1.0 - Fd.r;
float wlw = 0.020*sin(UV.x*23.0 + T*9.0) + 0.012*sin(UV.x*57.0 - T*13.0);
float under = Fd.r >= 0.999 ? 1.0 : smoothstep(wl + wlw - 0.012, wl + wlw + 0.012, UV.y);
float foamL = (Fd.r > 0.001 && Fd.r < 0.999) ? smoothstep(0.04, 0.0, abs(UV.y - (wl + wlw))) : 0.0;
outside = lerp(SC.rgb, outside, under) + foamL*0.55;
return lerp(outside, SC.rgb, inside) * (1.0 - Fd.g);
'''
u = g.custom(UW, [('SC', sc), ('SD', sd), ('CS', cs), ('CV', cam), ('UV', scr, 'ViewportUV'), ('T', t), ('Dp', deep), ('Sh', shal), ('Lc', lcol),
                  ('Sv', sdir), ('Lg', lgt, 'RGBA'), ('Bm', bmo, 'RGBA'), ('Am', amt), ('Vi', vis), ('Fd', flood)], 'f3')
g.out(u, MP.MP_EMISSIVE_COLOR)
g.done()

ppv = s1u.spawn(unreal.PostProcessVolume, 'PPV_Underwater', folder='Sky')
ppv.set_editor_property('unbound', True)
ppv.set_editor_property('blend_weight', 0.0)
s = ppv.get_editor_property('settings')
wb = unreal.WeightedBlendable()
wb.set_editor_property('weight', 1.0)
import i_tune
mi_uw = i_tune.mi('MI_PP_Underwater', '/Game/Scene1/Materials/M_PP_Underwater')     # instance: parameters are tuned and animated without recompiling
wb.set_editor_property('object', mi_uw)
wbs = unreal.WeightedBlendables()
wbs.set_editor_property('array', [wb])
s.set_editor_property('weighted_blendables', wbs)
s.set_editor_property('override_auto_exposure_bias', True)
s.set_editor_property('auto_exposure_bias', -1.5)
ppv.set_editor_property('settings', s)
s1u.save()
print('underwater ok')
