# Wave shadow as a light function of the Sun (analytic, soft controllable edge; replaces cascaded shadows of a caster 12 km away).
# Data comes in MPC vector 'SunDir' = (crest x cm, crest height cm, penumbra half-width cm, 0)  -- see q_shots.apply()
import unreal, importlib, mu, s1u
importlib.reload(mu)
from mu import *
mpc = EAL.load_asset('/Game/Scene1/MPC_Otliv')
m = new_mat('M_LF_WaveShadow')
m.set_editor_property('material_domain', unreal.MaterialDomain.MD_LIGHT_FUNCTION)
g = G(m)
wp = g.wpos()
sv = g.mpc(mpc, 'SunDir')
LF = r'''
float cx = S.r; float ch = S.g; float w = max(S.b, 1.0);
float s = (ch - P.z) / 0.17633 - (cx - P.x);
float front = P.x < cx ? 1.0 : 0.0;
return 1.0 - front * smoothstep(-w, w, s);
'''
lf = g.custom(LF, [('P', wp), ('S', sv)], 'f1')
g.out(lf, MP.MP_EMISSIVE_COLOR)
g.done()
sun = s1u.find('Sun').light_component
sun.set_editor_property('light_function_material', m)
sun.set_editor_property('light_function_fade_distance', 1.0e9)
sun.set_editor_property('disabled_brightness', 1.0)
sun.set_editor_property('far_shadow_cascade_count', 0)
w = s1u.find('Wave').static_mesh_component
w.set_editor_property('cast_shadow', False)
s1u.save()
print('light function ok')
