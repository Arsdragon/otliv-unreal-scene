# Wave material v4.
# Reads as water: wide soft foam streams running down the face, dark troughs, sky glint, white crest, boiling foam at the foot.
# No glowing rim: turquoise appears only as a soft band where the water is thin AND the sun is right behind it.
# v4: texture layers are rotated and warped (no mirror symmetry, no "scales"), a third large normal octave,
#     streams are wider and softer, their density varies along the crest and they fade with distance (no scratches from afar).
# Vertex colour: R = water thickness toward the sun / 1500 m, G = height fraction, B = 1 on the front face.
# UV0 = (y along the crest, arc length up the profile) / 100 m. All scales are instance parameters.
import unreal, importlib, mu
importlib.reload(mu)
from mu import *
NRM = '/Water/Textures/Normals/T_Water_TilingNormal_Waves_02'
FOAM = '/Water/Textures/Foam/T_WaterFlow_01_Foam_Tiled'
mpc = unreal.EditorAssetLibrary.load_asset('/Game/Scene1/MPC_Otliv')
m = new_mat('M_Wave', two_sided=True)
g = G(m)
vc = g.node(unreal.MaterialExpressionVertexColor)
uv = g.node(unreal.MaterialExpressionTextureCoordinate)
t = g.mpc(mpc, 'SimTime')
cam = g.node(unreal.MaterialExpressionCameraVectorWS)
pdepth = g.node(unreal.MaterialExpressionPixelDepth)
# layer = scale xy + scroll zw ; rot = rotation deg, warp amount (uv units), warp frequency, unused
LAYERS = [('NrmScaleA', (0.11, 0.07, 0.0, -0.004), 'NrmRotA', (23.0, 0.6, 0.05, 0.0)),      # swell
          ('NrmScaleB', (0.9, 0.6, 0.002, -0.02), 'NrmRotB', (-41.0, 0.4, 0.21, 0.0)),      # chop
          ('NrmScaleC', (0.031, 0.023, 0.0, -0.001), 'NrmRotC', (67.0, 0.5, 0.02, 0.0)),    # very large undulation
          ('FoamScaleA', (0.9, 0.12, 0.0, -0.02), 'FoamRotA', (7.0, 0.5, 0.07, 0.0)),
          ('FoamScaleB', (3.1, 1.4, 0.003, -0.05), 'FoamRotB', (-19.0, 0.8, 0.33, 0.0))]
UVC = r'''
struct R2 {
 float h2(float2 p){ return frac(sin(dot(p,float2(12.9898,78.233)))*43758.5453); }
 float vn(float2 p){ float2 i=floor(p), f=frac(p); f=f*f*(3-2*f);
   return lerp(lerp(h2(i),h2(i+float2(1,0)),f.x),lerp(h2(i+float2(0,1)),h2(i+float2(1,1)),f.x),f.y); }
};
R2 r;
float a = radians(Rp.r); float ca = cos(a); float sa = sin(a);
float2 p = UV*S.xy;
p = float2(p.x*ca - p.y*sa, p.x*sa + p.y*ca);
float2 q = UV*Rp.b + 3.7;
float2 wv = float2(r.vn(q), r.vn(q + 17.3)) - 0.5;
return p + wv*Rp.g + S.zw*T;
'''
uvs = []
for sn_, sv_, rn_, rv_ in LAYERS:
    s_ = g.vec(sn_, sv_); r_ = g.vec(rn_, rv_)
    uvs.append(g.custom(UVC, [('UV', uv), ('T', t), ('S', s_, 'RGBA'), ('Rp', r_, 'RGBA')], 'f2'))
nA = g.tex(NRM, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, uvs[0])
nB = g.tex(NRM, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, uvs[1])
nC = g.tex(NRM, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, uvs[2])
fA = g.tex(FOAM, None, uvs[3])
fB = g.tex(FOAM, None, uvs[4])
deep = g.vec('DeepColor', (0.010, 0.050, 0.070))
turq = g.vec('Turquoise', (0.20, 0.72, 0.62))
sunc = g.vec('SunColor', (1.0, 0.86, 0.66))
foamc = g.vec('FoamColor', (0.80, 0.83, 0.84))
glow = g.scalar('GlowIntensity', 3.0)
lth = g.scalar('TransmitLength', 60.0)
phx = g.scalar('SunCone', 30.0)
foamA = g.scalar('FoamAmount', 1.0)
foamD = g.scalar('FoamDetail', 0.15)
nstr = g.vec('NrmStrength', (0.8, 0.12, 0.9, 0.0))          # strength of A, B, C
pstr = g.vec('StreakShape', (420.0, 2600.0, 900.0, 25.0))    # cell width m, cell length m, meander m, flow m/s
strk = g.vec('Streaks', (0.56, 0.34, 0.5, 0.80))             # threshold, softness, amount, height where curtains thicken
smod = g.vec('StreakMod', (0.22, 9.0, 22.0, 0.0))            # density variation along the crest, fade start km, fade range km
bands = g.vec('FoamBands', (0.90, 0.075, 0.0, 0.0))          # crest band start (height fraction), foot boil height
trg = g.vec('Troughs', (2500.0, 600.0, 0.6, 0.0))            # band cell along crest m, along slope m, depth
MAIN = r'''
struct W {
 float h2(float2 p){ return frac(sin(dot(p,float2(12.9898,78.233)))*43758.5453); }
 float vn(float2 p){ float2 i=floor(p), f=frac(p); f=f*f*(3-2*f);
   return lerp(lerp(h2(i),h2(i+float2(1,0)),f.x),lerp(h2(i+float2(0,1)),h2(i+float2(1,1)),f.x),f.y); }
 float fbm(float2 p){ return 0.5*vn(p) + 0.3*vn(p*2.13+7.1) + 0.2*vn(p*4.37+3.3); }
};
W w;
float thick = VC.r * 1500.0;
float zf = VC.g;
float front = VC.b;
float2 mm = UV * 100.0 + float2(3137.0, 0.0);
float warp = (w.vn(mm / float2(1300.0, 3100.0)) - 0.5) * Pw.b + (w.vn(mm / float2(290.0, 900.0) + 4.0) - 0.5) * Pw.b * 0.25;
float2 ps = float2((mm.x + warp) / max(Pw.r, 1.0), (mm.y - T*Pw.a) / max(Pw.g, 1.0));
float sn = w.fbm(ps);
float sn2 = w.vn(ps*float2(0.37, 0.8) + 11.0);                 // larger octave: wide streams
float streakN = sn*0.6 + sn2*0.4;
float hgt = smoothstep(St.a, 1.0, zf);
float dens = (w.vn(float2(mm.x/3800.0 + 9.0, mm.y/7000.0)) - 0.5) * Sm.r * 2.0;   // some stretches of the face are streakier
float th = St.r - 0.25*hgt - dens;
float dfade = saturate(1.0 - (PD/100000.0 - Sm.g) / max(Sm.b, 0.1));               // streams dissolve in the distance
float streak = smoothstep(th, th + St.g, streakN) * St.b * smoothstep(0.02, 0.25, zf) * dfade;
float det = lerp(1.0, 0.35 + 1.3*FB.r, Fd) * lerp(1.0, 0.4 + 1.2*FA_.r, Fd*0.6);
float fcrest = smoothstep(Bd.r, min(Bd.r + 0.06, 0.999), zf);
float boil = w.fbm(float2(mm.x/70.0, (mm.y - T*6.0)/45.0) + 2.0);
float ffoot = (1.0 - smoothstep(0.0, max(Bd.g, 0.001), zf)) * (0.25 + 1.5*boil);
float foam = saturate((fcrest*1.4 + ffoot + streak) * det * Fm) * front;
float band = w.fbm(float2(mm.x / max(Tr.r, 1.0), mm.y / max(Tr.g, 1.0)) + 5.0);
float trough = lerp(1.0 - Tr.b, 1.0 + Tr.b*0.6, band);
Nrm = normalize(float3((NA.xy*Ns.r + NB.xy*Ns.g + NC.xy*Ns.b) * (1.0 - foam*0.7), 1.0));
Rough = lerp(lerp(0.05, 0.16, band), 0.62, foam);
float3 L = float3(0.9848, 0.0, 0.1736);
float cosv = saturate(dot(-normalize(CV), L));
float xt = thick / max(LT, 1.0);
float body = xt * exp(1.0 - xt);
float ph = pow(cosv, max(Ph, 1.0));
Emis = Sc.rgb * Tq.rgb * (GI * body * ph * front * (1.0 - 0.6*foam));
return lerp(DC.rgb * trough, Fc.rgb, foam);
'''
mn = g.custom(MAIN, [('VC', vc), ('UV', uv), ('T', t), ('CV', cam), ('PD', pdepth), ('NA', nA), ('NB', nB), ('NC', nC), ('FA_', fA), ('FB', fB),
                     ('DC', deep), ('Tq', turq), ('Sc', sunc), ('Fc', foamc), ('GI', glow), ('LT', lth), ('Ph', phx),
                     ('Fm', foamA), ('Fd', foamD), ('Ns', nstr, 'RGBA'), ('Pw', pstr, 'RGBA'), ('St', strk, 'RGBA'), ('Sm', smod, 'RGBA'),
                     ('Bd', bands, 'RGBA'), ('Tr', trg, 'RGBA')],
             'f3', outs=[('Nrm', 'f3'), ('Rough', 'f1'), ('Emis', 'f3')])
g.out(mn, MP.MP_BASE_COLOR)
g.out(mn, MP.MP_NORMAL, 'Nrm')
g.out(mn, MP.MP_ROUGHNESS, 'Rough')
g.out(mn, MP.MP_EMISSIVE_COLOR, 'Emis')
g.done()
import i_tune
importlib.reload(i_tune)
mi = i_tune.mi('MI_Wave', '/Game/Scene1/Materials/M_Wave')
i_tune.setp(mi, GlowIntensity=3.0, Turquoise=(0.20, 0.72, 0.62), TransmitLength=60.0, DeepColor=(0.010, 0.050, 0.070),
            FoamDetail=0.15, NrmStrength=(0.8, 0.12, 0.9, 0.0), StreakShape=(420.0, 2600.0, 900.0, 25.0),
            Streaks=(0.56, 0.34, 0.5, 0.80), StreakMod=(0.22, 9.0, 22.0, 0.0), FoamBands=(0.90, 0.075, 0.0, 0.0),
            Troughs=(2500.0, 600.0, 0.6, 0.0))
print('wave mat ok')
