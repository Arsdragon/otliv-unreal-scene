# MPC, seabed material, water material (Single Layer Water)
import unreal, importlib, mu
importlib.reload(mu)
from mu import *
NRM = '/Water/Textures/Normals/T_Water_TilingNormal_Waves_02'
CAU = '/Water/Textures/Caustics/Caustics_Tiling_01_HDR'

rings = [('Ring%d' % i, (0.0, 0.0, -100.0, 0.0)) for i in range(8)]
mpc = mpc_asset(scalars=[('SimTime', 0.0), ('WaveX', 3600000.0), ('FlowSpeed', 0.0), ('RippleAmp', 1.0)],
                vectors=rings + [('SunDir', (-0.985, 0.0, -0.174, 0.0))])

# ---------------- seabed: salt crust ----------------
m = new_mat('M_Seabed')
g = G(m)
wp = g.wpos()
tint = g.vec('SaltColor', (0.78, 0.75, 0.69))
cell = g.scalar('CellSize', 140.0)
cau = g.tex(CAU)
VOR = r'''
struct V {
 float2 h2(float2 p){ p=float2(dot(p,float2(127.1,311.7)),dot(p,float2(269.5,183.3))); return frac(sin(p)*43758.5453); }
 float h1(float2 p){ return frac(sin(dot(p,float2(12.9898,78.233)))*43758.5453); }
 float vn(float2 p){ float2 i=floor(p), f=frac(p); f=f*f*(3-2*f);
   return lerp(lerp(h1(i),h1(i+float2(1,0)),f.x),lerp(h1(i+float2(0,1)),h1(i+float2(1,1)),f.x),f.y); }
 float edge(float2 p){ float2 n=floor(p), f=frac(p); float d1=8, d2=8;
   for(int j=-1;j<=1;j++) for(int i=-1;i<=1;i++){ float2 g=float2(i,j); float2 o=h2(n+g);
     float d=length(g+o-f); if(d<d1){d2=d1;d1=d;} else if(d<d2){d2=d;} }
   return d2-d1; }
 float H(float2 p, float cs){ float e = edge(p/cs); float r = exp(-e*e*90.0);
   return r*1.6 + 0.35*vn(p/9.0) + 0.25*vn(p/31.0); }
};
V v;
float2 p = P.xy;
float h = v.H(p, CS);
float e = 2.0;
float hx = v.H(p+float2(e,0), CS), hy = v.H(p+float2(0,e), CS);
Nrm = normalize(float3(-(hx-h)/e*1.4, -(hy-h)/e*1.4, 1));
float macro = v.vn(p/2300.0)*0.6 + v.vn(p/9000.0)*0.4;
float ridge = saturate((h-0.35)/1.3);
return Tint * (0.86 + 0.12*macro) * (0.93 + 0.12*ridge);
'''
cs = g.custom(VOR, [('P', wp), ('CS', cell), ('Tint', tint)], 'f3', outs=[('Nrm', 'f3')])
m.set_editor_property('tangent_space_normal', False)
g.out(cs, MP.MP_BASE_COLOR)
g.out(cs, MP.MP_NORMAL, 'Nrm')
g.out(g.const(0.8), MP.MP_ROUGHNESS)
g.done()
print('seabed ok')

# ---------------- water: single layer water ----------------
w = new_mat('M_Water', shading=unreal.MaterialShadingModel.MSM_SINGLE_LAYER_WATER)
w.set_editor_property('tangent_space_normal', False)
g = G(w)
wp = g.wpos()
t = g.mpc(mpc, 'SimTime')
flow = g.mpc(mpc, 'FlowSpeed')
ramp = g.mpc(mpc, 'RippleAmp')
rn = [g.mpc(mpc, 'Ring%d' % i) for i in range(8)]
uv1 = g.custom('return P.xy/900.0 + float2(T*0.006 + T*F/900.0, T*0.004);', [('P', wp), ('T', t), ('F', flow)], 'f2')
uv2 = g.custom('return P.xy/370.0 + float2(-T*0.011 + T*F/370.0, T*0.007);', [('P', wp), ('T', t), ('F', flow)], 'f2')
n1 = g.tex(NRM, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, uv1)
n2 = g.tex(NRM, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, uv2)
strength = g.scalar('MicroNormal', 0.06)
RING = r'''
float4 R[8] = {R0,R1,R2,R3,R4,R5,R6,R7};
float2 grad = (N1.xy + N2.xy*0.7) * S * A;
for (int i=0;i<8;i++){
  float age = T - R[i].z;
  if (age > 0.0 && R[i].w > 0.0){
    float2 d = P.xy - R[i].xy; float r = length(d) + 0.01;
    float rad = 3.0 + 38.0*age;
    float sg = 2.5 + 7.0*age;
    float x = r - rad;
    float k = 6.2831/4.5;
    float env = R[i].w * exp(-x*x/(2.0*sg*sg)) * exp(-age*0.45) * rsqrt(1.0 + r/20.0);
    float dh = env * (k*cos(k*x) - x/(sg*sg)*sin(k*x));
    grad += 0.06 * dh * d / r;
  }
}
return normalize(float3(-grad, 1.0));
'''
nr = g.custom(RING, [('P', wp), ('T', t), ('S', strength), ('A', ramp), ('N1', n1), ('N2', n2)] +
              [('R%d' % i, rn[i]) for i in range(8)], 'f3')
g.out(nr, MP.MP_NORMAL)
g.out(g.scalar('Roughness', 0.025), MP.MP_ROUGHNESS)
g.out(g.scalar('Specular', 0.5), MP.MP_SPECULAR)
g.out(g.vec('BaseColor', (0.0, 0.0, 0.0)), MP.MP_BASE_COLOR)
slw = g.node(unreal.MaterialExpressionSingleLayerWaterMaterialOutput)
g.link(g.vec('Scattering', (0.010, 0.022, 0.020)), '', slw, 'ScatteringCoefficients')
g.link(g.vec('Absorption', (0.35, 0.065, 0.035)), '', slw, 'AbsorptionCoefficients')
g.link(g.const(0.2), '', slw, 'PhaseG')
g.done()
print('water ok')
