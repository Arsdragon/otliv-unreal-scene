# S5 (polish before the final render): one-off patch of the effect scripts. Run once outside Unreal:  python -I s5_patch.py
#  - weather material: new drops on the glass, a flash that lights the wall from within, no depth cut (the stencil is right);
#  - underwater material: small bubbles of many sizes in streams, smeared by motion.
import os, re
D = os.path.dirname(os.path.abspath(__file__))


def cut(s, a_mark, b_mark, new):
    a = s.index(a_mark); b = s.index(b_mark, a)
    return s[:a] + new + s[b:]


# ---------------------------------------------------------------- weather
p = os.path.join(D, 's3_mood_build.py'); s = open(p, encoding='utf-8').read()
s = re.sub(r'inside = max\(inside, d < Gl\.g \? 1\.0 : 0\.0\);[^\n]*\n', '', s)
FLASH = r'''// a flash inside the wall of water: the wall and the cloud glow from within; far things light up, near things do not
float3 fpos = normalize(float3(1.0, Fx.g, Fx.b));
float fa = saturate(dot(dir, fpos));
float fglow = (0.22*smoothstep(-0.15, 0.5, dir.x) + 0.9*pow(fa, 5.0) + 1.3*pow(fa, 48.0)) * (0.7 + 0.3*u.n2(dir.yz*7.0 + 3.0));
outc += float3(0.60, 0.72, 0.98) * Fx.r * fglow * saturate((d - 150.0)/600.0);
'''
if 'float3 fpos' not in s:
    s = s.replace('// rain in gusts', FLASH + '// rain in gusts', 1)
old = 'outc += float3(0.70, 0.76, 0.82) * streak * 0.20 * saturate(Rn.r*3.0) * (0.5 + 0.7*lum);'
if old in s:
    s = s.replace(old, old[:-1] + ' * (1.0 + 7.0*Fx.r*(0.25 + fglow));        // the rain in front of the flash turns to silver')
s = re.sub(r'// dull flash inside the cloud of water[^\n]*\noutc \+= [^\n]*\n', '', s)
GLASS = r'''// drops on the glass (canopy or helmet): running drops that creep along the flow, hesitate, wobble and leave a wet streak
// behind; tiny standing drops of several sizes that live for a while - the streaks wipe them away. Each drop is a small lens.
// Gl: r amount, g speed of the running drops, ba direction of the flow on the screen (x right, y down)
float gl = Gl.r;
if (gl > 0.001){
  float2 fdir = normalize(Gl.ba + float2(0.0, 1.0e-4));
  float2 fperp = float2(-fdir.y, fdir.x);
  float2 gs = float2(dot(suv, fperp), dot(suv, fdir));
  float2 off = float2(0.0, 0.0); float wet = 0.0; float rim = 0.0; float glint = 0.0; float wipe = 0.0;
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
  }
  float2 ruv = clamp(UV + off*float2(0.5625, 1.0), 0.002, 0.998);
  float3 refr = SceneTextureLookup(ViewportUVToSceneTextureUV(ruv, 14), 14, false).rgb;
  float3 wcol = refr*0.95 + float3(0.04, 0.045, 0.05)*(0.3 + lum);
  wcol *= 1.0 - 0.42*saturate(rim);
  wcol += float3(0.75, 0.80, 0.86) * saturate(glint) * (0.10 + 0.5*lum);
  outc = lerp(outc, wcol, saturate(wet)*0.93);
}
'''
s = cut(s, '// drops and rivulets on the glass', 'return lerp(outc, SC.rgb, inside);', GLASS)
# the light of the flash on the ship and the sea (no shadows: it lasts a few frames), puffs of steam at the cutter
EXTRA = r'''
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
'''
if 'FlashLight' not in s:
    s = s.replace("s1u.save()\nunreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)\nprint('mood build ok')", EXTRA + "s1u.save()\nunreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)\nprint('mood build ok')")
assert 'FlashLight' in s and 'float3 fpos' in s and 'Gl.g ?' not in s
open(p, 'w', encoding='utf-8').write(s)

# ---------------------------------------------------------------- underwater
p = os.path.join(D, 'n_underwater.py'); s = open(p, encoding='utf-8').read()
BUB = r'''// bubbles: many small ones of very different sizes, rising in wandering streams, smeared by their own motion
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
  float rad = 0.07 + 0.30*r*r*r;
  float2 q = (f - o) * float2(1.0, 1.3);
  float dd = length(q);
  float soft = smoothstep(rad, rad*0.25, dd);
  float ring = (r > 0.8 ? 1.0 : 0.0) * smoothstep(rad, rad*0.8, dd) * smoothstep(rad*0.3, rad*0.9, dd);
  float dens = (0.22 + 0.55*stream) * (1.0 - 0.08*fk);
  float onb = (u.h2(c + 57.0 + 3.0*fk) < dens) ? 1.0 : 0.0;
  bub += onb * (soft*0.65 + ring*0.6) / (1.0 + 0.45*fk);
}
'''
s = cut(s, '// bubbles in streams', '// a few big soft bubbles right at the glass', BUB)
s = s.replace("float nearb = (rn > 0.70 ? 1.0 : 0.0) * smoothstep(radn, radn*0.86, ddn) * (0.10 + 0.90*smoothstep(radn*0.55, radn*0.98, ddn));",
              "float nearb = (rn > 0.82 ? 1.0 : 0.0) * smoothstep(radn, radn*0.55, ddn) * (0.25 + 0.75*smoothstep(radn*0.35, radn*0.98, ddn));")
s = s.replace("amt = g.vec('Amounts', (0.10, 0.55, 0.30, 0.22))", "amt = g.vec('Amounts', (0.10, 0.55, 0.10, 0.22))")
assert 'pow(1.55, fk)' in s
open(p, 'w', encoding='utf-8').write(s)
print('patched')
