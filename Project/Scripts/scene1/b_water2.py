import unreal, importlib, mu
importlib.reload(mu)
from mu import *
NRM = "/Water/Textures/Normals/T_Water_TilingNormal_Waves_02"
mpc = unreal.EditorAssetLibrary.load_asset("/Game/Scene1/MPC_Otliv")
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
