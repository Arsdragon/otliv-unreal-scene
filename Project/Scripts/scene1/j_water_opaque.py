# Opaque mirror water (works with Planar Reflection + keeps distant haze in reflections).
# The salt bottom under the water is drawn inside this material (refraction parallax, absorption, caustics, Fresnel).
# Rings: MPC Ring0..7 = (x cm, y cm, start time s, amplitude). Ship skis under water: material params Leg0..3 = (x, y, half-length, half-width) cm.
import unreal, importlib, mu
importlib.reload(mu)
from mu import *
NRM = '/Water/Textures/Normals/T_Water_TilingNormal_Waves_02'
CAU = '/Water/Textures/Caustics/Caustics_Tiling_01_HDR'
mpc = unreal.EditorAssetLibrary.load_asset('/Game/Scene1/MPC_Otliv')
w = new_mat('M_WaterMirror')
w.set_editor_property('tangent_space_normal', False)
g = G(w)
wp = g.wpos()
cam = g.node(unreal.MaterialExpressionCameraVectorWS)
t = g.mpc(mpc, 'SimTime'); flow = g.mpc(mpc, 'FlowSpeed'); ramp = g.mpc(mpc, 'RippleAmp'); wx = g.mpc(mpc, 'WaveX')
rn = [g.mpc(mpc, 'Ring%d' % i) for i in range(8)]
uv1 = g.custom('return P.xy/900.0 + float2(T*0.006 + T*F/900.0, T*0.004);', [('P', wp), ('T', t), ('F', flow)], 'f2')
uv2 = g.custom('return P.xy/370.0 + float2(-T*0.011 + T*F/370.0, T*0.007);', [('P', wp), ('T', t), ('F', flow)], 'f2')
n1 = g.tex(NRM, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, uv1)
n2 = g.tex(NRM, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, uv2)
strength = g.scalar('MicroNormal', 0.025)
tint = g.vec('SaltColor', (0.78, 0.75, 0.69))
absb = g.vec('Absorption', (0.31, 0.088, 0.058))
cell = g.scalar('CellSize', 140.0)
glowc = g.vec('ShadowGlow', (0.02, 0.10, 0.16))
ck = g.scalar('Caustics', 0.05)
ringk = g.scalar('RingStrength', 1.0)
legs = [g.vec('Leg%d' % i, (0.0, 0.0, 0.0, 0.0)) for i in range(4)]
BOT = r'''
float3 V = normalize(CV);
float3 I = -V;
float3 tdir = refract(I, float3(0,0,1), 1.0/1.33);
float depth = max(P.z, 1.0);
float k = depth / max(0.05, -tdir.z);
return float3(P.xy + tdir.xy * k, k);
'''
bot = g.custom(BOT, [('P', wp), ('CV', cam)], 'f3')
cuv = g.custom('return B.xy/260.0 + float2(T*0.02, T*0.013);', [('B', bot), ('T', t)], 'f2')
cau = g.tex(CAU, None, cuv)
MAIN = r'''
struct V {
 float2 h2(float2 p){ p=float2(dot(p,float2(127.1,311.7)),dot(p,float2(269.5,183.3))); return frac(sin(p)*43758.5453); }
 float h1(float2 p){ return frac(sin(dot(p,float2(12.9898,78.233)))*43758.5453); }
 float vn(float2 p){ float2 i=floor(p), f=frac(p); f=f*f*(3-2*f);
   return lerp(lerp(h1(i),h1(i+float2(1,0)),f.x),lerp(h1(i+float2(0,1)),h1(i+float2(1,1)),f.x),f.y); }
 float edge(float2 p){ float2 n=floor(p), f=frac(p); float d1=8, d2=8;
   for(int j=-1;j<=1;j++) for(int i=-1;i<=1;i++){ float2 g=float2(i,j); float2 o=h2(n+g);
     float d=length(g+o-f); if(d<d1){d2=d1;d1=d;} else if(d<d2){d2=d;} }
   return d2-d1; }
};
V v;
// --- surface slope: micro ripples + expanding rings (steps, drone downwash) + wakes behind the ship legs ---
float4 R[8] = {R0,R1,R2,R3,R4,R5,R6,R7};
float4 LG[4] = {L0,L1,L2,L3};
float2 grad = (N1.xy + N2.xy*0.7) * S * A;
float dist = 0.0;
for (int i=0;i<8;i++){
  float age = T - R[i].z;
  if (age > 0.0 && R[i].w > 0.0){
    float2 d = P.xy - R[i].xy; float r = length(d) + 0.01;
    float rad = 6.0 + 30.0*age;          // ring radius, cm
    float wid = 6.0 + 9.0*age;           // packet half-width, cm
    float lam = 7.0 + 5.0*age;           // wavelength grows with age, cm
    float x = r - rad;
    float kk = 6.2831/lam;
    float env = R[i].w * exp(-x*x/(2.0*wid*wid)) * exp(-age*0.28) * rsqrt(1.0 + rad/25.0);
    float dh = env * (cos(kk*x)*6.2831 - x*lam/(wid*wid)*sin(kk*x));
    grad += 0.02 * RK * dh * d / r; dist += env;
  }
}
float fl = saturate(F/40.0);
for (int j=0;j<4;j++){
  if (LG[j].z > 0.0){
    float dx = P.x - LG[j].x; float dy = P.y - LG[j].y;
    float ww = 10.0 + 0.22*max(dx, 0.0);
    float wk = (dx > -15.0 ? 1.0 : 0.0) * exp(-dy*dy/(ww*ww)) * exp(-max(dx,0.0)/450.0) * fl;
    grad += N2.xy * wk * 0.35; dist += wk * 0.5;
  }
}
Nrm = normalize(float3(-grad, 1.0));
// --- bottom seen through the water ---
float2 bp = B.xy + grad * 6.0;
float e = v.edge(bp / CS);
float ridge = exp(-e*e*90.0);
float macro = v.vn(bp/2300.0)*0.6 + v.vn(bp/9000.0)*0.4;
float3 salt = Tint * (0.86 + 0.12*macro) * (0.93 + 0.12*ridge) * (0.97 + 0.06*v.vn(bp/11.0));
for (int q=0;q<4;q++){
  if (LG[q].z > 0.0){
    float2 dl = (bp - LG[q].xy) / LG[q].zw;
    float ee = dot(dl, dl);
    salt = lerp(salt, float3(0.07,0.075,0.08), (1.0 - smoothstep(0.55, 1.25, ee)) * 0.9);
    salt *= 1.0 - 0.35*(1.0 - smoothstep(1.0, 4.5, ee));       // soft contact shadow / silt around the ski
  }
}
float pathm = (B.z + max(P.z,1.0)*1.35) / 100.0;   // view path + refracted sun path, metres
float3 trans = exp(-Ab * pathm);
float caus = dot(CA.rgb, float3(0.33,0.33,0.34));
float ndv = saturate(dot(normalize(CV), Nrm));
float fres = 0.02 + 0.98*pow(1.0 - ndv, 5.0);
float3 col = salt * trans * (1.0 + CK*(caus - 0.5)) * (1.0 - fres);
// --- glow of disturbed water inside the wave shadow ---
float sx = WX - P.x;
float inshadow = (sx > 0.0 && sx < 1191000.0) ? 1.0 : 0.0;
Emis = GC * inshadow * (3.0*saturate(dist*2.0) + 1.5*saturate(length(grad)*10.0 - 0.15));
return col;
'''
mn = g.custom(MAIN, [('P', wp), ('B', bot), ('T', t), ('S', strength), ('A', ramp), ('F', flow), ('N1', n1), ('N2', n2), ('CA', cau),
                     ('Tint', tint), ('Ab', absb), ('CS', cell), ('WX', wx), ('GC', glowc), ('CK', ck), ('RK', ringk), ('CV', cam)]
             + [('R%d' % i, rn[i]) for i in range(8)] + [('L%d' % i, legs[i], 'RGBA') for i in range(4)],
             'f3', outs=[('Nrm', 'f3'), ('Emis', 'f3')])
g.out(mn, MP.MP_BASE_COLOR)
g.out(mn, MP.MP_NORMAL, 'Nrm')
g.out(mn, MP.MP_EMISSIVE_COLOR, 'Emis')
g.out(g.scalar('Roughness', 0.02), MP.MP_ROUGHNESS)
g.out(g.scalar('Specular', 0.25), MP.MP_SPECULAR)
g.done()
import i_tune
importlib.reload(i_tune)
mi = i_tune.mi('MI_WaterMirror', '/Game/Scene1/Materials/M_WaterMirror')
# skis of the landed ship (world cm): centres from manifest fx_splash_*, long axis along X
i_tune.setp(mi, Absorption=(0.31, 0.088, 0.058), Caustics=0.05,
            Leg0=(290.0, -210.0, 75.0, 24.0), Leg1=(290.0, 210.0, 75.0, 24.0),
            Leg2=(-290.0, -230.0, 75.0, 24.0), Leg3=(-290.0, 230.0, 75.0, 24.0))
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if a.get_actor_label().startswith('Water_'):
        a.static_mesh_component.set_material(0, mi)
print('water mirror ok')
