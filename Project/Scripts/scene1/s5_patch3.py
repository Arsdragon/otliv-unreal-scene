# S5, second round after the first test stills. Run once outside Unreal:  python -I s5_patch3.py
import os
D = os.path.dirname(os.path.abspath(__file__))


def rep(s, old, new, count=1):
    assert old in s, old[:70]
    return s.replace(old, new, count)


p = os.path.join(D, 's3_mood_build.py'); s = open(p, encoding='utf-8').read()
# 1. black corners: with a 120-degree lens the corners look more than 90 degrees away from the flash, pow(0, n) gave NaN there
s = rep(s, "float fglow = (0.22*smoothstep(-0.15, 0.5, dir.x) + 0.9*pow(fa, 5.0) + 1.3*pow(fa, 48.0)) * (0.7 + 0.3*u.n2(dir.yz*7.0 + 3.0));\n"
           "outc += float3(0.60, 0.72, 0.98) * Fx.r * fglow * saturate((d - 150.0)/600.0);\n",
        "float fa2 = fa*fa; float fa5 = fa2*fa2*fa; float fa48 = fa5*fa5; fa48 = fa48*fa48; fa48 = fa48*fa48*fa5*fa2*fa;\n"
        "float fglow = (0.22*smoothstep(-0.15, 0.5, dir.x) + 0.9*fa5 + 1.3*fa48) * (0.7 + 0.3*u.n2(dir.yz*7.0 + 3.0));\n"
        "// the glow comes from behind the wall and the cloud: what is dark in front of it stays darker, so their shapes remain\n"
        "float3 fcol = float3(0.60, 0.72, 0.98) * Fx.r * fglow * 0.85 * (0.45 + 2.2*saturate(lum*1.5));\n"
        "outc += fcol * saturate((d - 150.0)/600.0);\n")
# 2. drops: what they refract is lit by the flash too; each catches a glint of the cabin light from below
s = rep(s, "    glint += mh * smoothstep(rh*0.30, 0.0, length(hv2 - float2(-0.3, -0.3)*rh));\n",
        "    glint += mh * smoothstep(rh*0.30, 0.0, length(hv2 - float2(-0.3, -0.3)*rh));\n"
        "    glow2 += mh * smoothstep(rh*0.45, 0.0, length(hv2 - float2(0.05, 0.45)*rh));\n")
s = rep(s, "    glint += m * smoothstep(rad*0.30, 0.0, length(dv2 - float2(-0.30, -0.32)*rad));\n  }\n  float2 ruv",
        "    glint += m * smoothstep(rad*0.30, 0.0, length(dv2 - float2(-0.30, -0.32)*rad));\n"
        "    glow2 += m * smoothstep(rad*0.45, 0.0, length(dv2 - float2(0.05, 0.45)*rad));\n  }\n  float2 ruv")
s = rep(s, "float2 off = float2(0.0, 0.0); float wet = 0.0; float rim = 0.0; float glint = 0.0; float wipe = 0.0;",
        "float2 off = float2(0.0, 0.0); float wet = 0.0; float rim = 0.0; float glint = 0.0; float wipe = 0.0; float glow2 = 0.0;")
s = rep(s, "  float3 wcol = refr*0.95 + float3(0.04, 0.045, 0.05)*(0.3 + lum);\n",
        "  float3 wcol = refr*0.95 + float3(0.04, 0.045, 0.05)*(0.3 + lum);\n"
        "  wcol += fcol * (0.6 + 0.8*saturate(dot(refr, float3(0.3, 0.59, 0.11))*1.5)) * saturate((d - 150.0)/600.0);     // the flash seen through the drop\n")
s = rep(s, "  wcol += float3(0.75, 0.80, 0.86) * saturate(glint) * (0.10 + 0.5*lum);\n",
        "  wcol += float3(0.75, 0.80, 0.86) * saturate(glint) * (0.10 + 0.5*lum);\n"
        "  wcol += float3(0.20, 0.27, 0.34) * saturate(glow2) * 0.16;                                    // light of the cabin (or of the helmet) in the lower edge\n")
open(p, 'w', encoding='utf-8').write(s)

p = os.path.join(D, 'n_underwater.py'); s = open(p, encoding='utf-8').read()
# 3. bubbles: no big blobs at the glass, smaller at the top of the range, longer smear, clearer streams
s = rep(s, "  float rad = 0.07 + 0.30*r*r*r;\n  float2 q = (f - o) * float2(1.0, 1.3);", "  float rad = 0.06 + 0.17*r*r*r;\n  float2 q = (f - o) * float2(1.0, 0.85);")
s = rep(s, "  float dens = (0.22 + 0.55*stream) * (1.0 - 0.08*fk);", "  float dens = (0.07 + 0.80*stream*stream) * (1.0 - 0.08*fk);")
s = rep(s, "amt = g.vec('Amounts', (0.10, 0.55, 0.10, 0.22))", "amt = g.vec('Amounts', (0.10, 0.55, 0.0, 0.22))")
open(p, 'w', encoding='utf-8').write(s)

p = os.path.join(D, 's3_mood.py'); s = open(p, encoding='utf-8').read()
s = rep(s, "_mi_vec(_S['mi_uw'], 'Amounts', (0.10, 0.55 * v, 0.10, 0.22))", "_mi_vec(_S['mi_uw'], 'Amounts', (0.10, 0.60 * v, 0.0, 0.22))")
# 4. the cutter: a dimmer, slightly warmer spot; longer sparks; denser steam
s = rep(s, "cl.point_light_component.set_intensity(0.30 * (0.35 + 0.65 * abs(T.n1(t * 23.0, 31))) if cutting else 0.0)",
        "cl.point_light_component.set_intensity(0.16 * (0.35 + 0.65 * abs(T.n1(t * 23.0, 31))) if cutting else 0.0)")
s = rep(s, "sa.set_actor_scale3d(unreal.Vector(0.085 * k, 0.011 * k, 0.011 * k))", "sa.set_actor_scale3d(unreal.Vector(0.13 * k, 0.014 * k, 0.014 * k))")
s = rep(s, "_mi_sc(_S['mi_puff'][i], 'Fade', round(0.55 * min(1.0, u / 0.15) * (1.0 - u) ** 1.5, 3))", "_mi_sc(_S['mi_puff'][i], 'Fade', round(0.85 * min(1.0, u / 0.15) * (1.0 - u) ** 1.5, 3))")
open(p, 'w', encoding='utf-8').write(s)
import ast
for f in ('s3_mood_build.py', 'n_underwater.py', 's3_mood.py'): ast.parse(open(os.path.join(D, f), encoding='utf-8').read())
print('patched')
