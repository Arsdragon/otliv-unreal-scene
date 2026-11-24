# S3, animatic v2 (director's notes of 2026-11-22). Patches s3_timeline (T) in place:
#   import s3_v2 as V; V.install()      -> T.apply_time / T.render / s3_sequence.build() now use the v2 timeline
#   V.render_v2()                        -> re-renders only the changed intervals into animatic_v2 (the rest are v1 frames)
# What is new: events on the walk (look back at the ship and the giant, look down at the water, the drone circles us, a long look at
# the "mountains"), walk around the wreck, opening of the niche (sparks, the cover falls into the water, the storage with a green light,
# the drone carries it away), glances over the shoulder on the run, the giant on the way back and after surfacing, plasma as a sheath,
# clouds and spray at landing, water rising over the glass before the impact and a blackout.
import unreal, math, os, importlib
import s1u, l_keys, q_shots, s3_timeline as T
from s3_timeline import cr, ease, sstep, lerp, n1
ML = unreal.MathLibrary
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
OUT2 = r'C:\UnrealScenes\Renders\scene1\animatic_v2'
BUS = (128.6, 153.2)
BEACON = (128.01, 153.32, 1.0)
GIANT = (200.0, 27.0)                 # where to look to have the gas giant (azimuth 210, elevation 35) in the frame
HOVER2 = (128.02, 152.04, 0.95)       # the drone at the niche: 0.8 m from the cover, a little aside so that the niche stays visible
GRAB = (128.01, 152.50, 0.90)
INTERVALS = [(50.0, 70.0), (73.0, 82.5), (94.0, 106.5), (137.0, 398.0), (457.0, 462.5), (505.0, 520.0)]
SPRAY = [(96.0, 0.0), (99.6, 0.30), (100.4, 0.55), (100.9, 1.0), (102.5, 0.5), (105.5, 0.0)]
CIRC = [(165.0, 0.0, 5.0, 1.2), (168.0, -35.0, 2.3, 1.45), (172.0, -180.0, 1.9, 1.55), (176.0, -325.0, 2.1, 1.45), (179.5, -360.0, 5.5, 1.2)]
DR_Y2 = [(106, 0), (121, 0), (124, 60), (129, 15), (134, -30), (137, 215), (145.5, 215), (148, 51), (164, 51), (181, 51), (226, 51),
         (235, 71), (296, 71), (300, 230), (331, 230), (366, 230), (372, 200), (383, 200), (388, 0), (397, 0)]
DR_ARM2 = [(240, 0.0), (246, 1.0), (294, 1.0), (298, 0.35), (396, 0.35), (397, 0.0)]
_orig = {}
_S = {}
DR_A, DR_B = [], []


def wrap(a): return (a + 180.0) % 360.0 - 180.0
def on(s): return (T.A_[0] + T.D_[0] * s, T.A_[1] + T.D_[1] * s)
def ring(ang, r):
    a = math.radians(ang); return (BUS[0] + r * math.cos(a), BUS[1] + r * math.sin(a))


def cam_p2():
    k = [x for x in _orig['CAM_P'] if x[0] <= 137.5]
    k += [(145.5, 12.5, 9.4, 1.70), (148,) + on(4.0) + (1.70,), (155,) + on(21.0) + (1.70,), (162,) + on(38.0) + (1.70,),
          (168,) + on(52.5) + (1.70,), (176,) + on(62.0) + (1.70,), (180,) + on(71.5) + (1.70,), (190,) + on(81.5) + (1.70,),
          (193,) + on(87.0) + (1.70,), (226,) + on(173.0) + (1.70,), (228.5, 123.5, 147.0, 1.70), (229.5, 123.5, 147.0, 1.70),
          (233,) + ring(215, 5.0) + (1.70,), (238,) + ring(150, 5.0) + (1.70,), (243,) + ring(95, 5.2) + (1.70,),
          (245.5,) + ring(95, 5.2) + (1.70,), (250,) + ring(160, 4.6) + (1.70,), (255,) + ring(232, 3.3) + (1.50,),
          (298,) + ring(232, 3.3) + (1.50,), (300.5, 124.6, 148.4, 1.70)]
    k += [x for x in _orig['CAM_P'] if x[0] >= 331]
    return k


def cam_l2():
    k = [x for x in _orig['CAM_L'] if x[0] <= 137.5]
    k += [(139.5, 216, 10, 0, 14), (145.5, 216, 10, 0, 14), (148, 51, -2, 0, 24), (154, 51, -2, 0, 24), (156, 60, -58, 0, 20),
          (160.5, 58, -58, 0, 20), (163, 51, -2, 0, 24), (166, 51, -2, 0, 24), (178.5, 51, -2, 0, 24), (179.5, 51, -2, 0, 24),
          (181.5, 3, 2, 0, 32), (189.5, 1, 2.5, 0, 36), (192, 51, -2, 0, 24), (225, 51, -2, 0, 24), (228.5, 50, -6, 0, 24),
          (255, 51, -10, 0, 28), (298, 51, -12, 0, 30), (300, 80, -45, 0, 20), (304, 80, -45, 0, 20), (307, 200, -6, 0, 20),
          (310, 235, -4, 0, 20), (313, 362, 2, 0, 28), (316, 361, 2.5, 0, 50), (326, 361, 3.0, 0, 50), (330, 230, -2, 0, 24),
          (336.5, 230, -2, 0, 24), (338, 322, 2, 0, 26), (339.6, 322, 2.5, 0, 26), (341.2, 230, -2, 0, 24),
          (347.5, 230, -2, 0, 24), (349, 324, 3, 0, 30), (350.8, 324, 3.5, 0, 30), (352.4, 230, -2, 0, 24),
          (353.6, 230, -2, 0, 24), (355, 212, 24, 0, 20), (357, 212, 24, 0, 20), (358.5, 230, -2, 0, 24),
          (360, 230, -2, 0, 24), (361.5, 326, 4, 0, 34), (363.5, 326, 4.5, 0, 34), (365, 232, -2, 0, 24), (366, 232, -4, 0, 18)]
    k += [x for x in _orig['CAM_L'] if x[0] >= 370]
    return k


WRECK_T = [(229.5, BUS[0], BUS[1], 0.75), (242.0, BUS[0], BUS[1], 0.75), (243.5,) + BEACON, (246.0,) + BEACON, (248.0, BUS[0], BUS[1], 0.75),
           (253.0, BUS[0], BUS[1], 0.75), (256.0, T.PANEL[0], T.PANEL[1], 0.80), (297.5, T.PANEL[0], T.PANEL[1], 0.80)]


def _circ(t):
    px, py, _ = cr(T.CAM_P, t)
    hd = math.atan2(T.D_[1], T.D_[0])
    phi, r, z = ease(CIRC, t)
    a = hd + math.radians(phi)
    return (px + r * math.cos(a), py + r * math.sin(a), z)


def build_drone_keys():
    L = T._lead
    a = [(106, -7.8, 1.6, 1.5), (121, -7.8, 1.6, 1.5), (124, -5.5, 6.5, 1.3), (129, 4.0, 8.6, 1.2), (134, 10.5, 7.5, 1.05),
         (137, 10.87, 5.75, 0.97), (145.5, 10.87, 5.75, 0.97)]
    for tt in (149, 154, 160): a.append((tt,) + L(tt, 5.0, 1.2))
    a.append((165.0,) + _circ(165.0))
    b = [(179.5,) + _circ(179.5)]
    for tt in range(184, 226, 5): b.append((tt,) + L(tt, 5.0, 1.2))
    b += [(227,) + L(227, 3.5, 1.15), (235,) + HOVER2, (290,) + HOVER2, (294,) + GRAB, (296,) + GRAB, (300, 126.9, 151.0, 1.5), (331, 126.9, 151.0, 1.5)]
    for tt in range(336, 371, 4): b.append((tt,) + L(tt, 7.0, 1.6))
    b += [(376, -8.2, 2.6, 1.75), (383, -8.2, 2.6, 1.75), (388, -5.0, 0.4, 2.4), (391, -2.2, 0.0, 2.9), (394, 0.0, 0.8, 2.8), (397,) + T.CRADLE]
    return a, b


def drone_world2(t):
    if t < 106.0 or t >= 397.0: return None
    if t <= 165.0: return tuple(cr(DR_A, t))
    if t < 179.5: return _circ(t)
    return tuple(cr(DR_B, t))


LOOKAT = [(166.5, 177.5, lambda t: ('pt',) + tuple(drone_world2(t))),
          (229.5, 297.5, lambda t: ('pt',) + tuple(ease(WRECK_T, t))),
          (508.5, 516.0, lambda t: ('dir',) + GIANT)]


def cam_local2(t):
    x, y, z, yaw, pitch, roll, focal = _orig['cam_local'](t)
    for t0, t1, fn in LOOKAT:
        if t0 < t < t1:
            k = sstep((t - t0) / 1.3) * (1.0 - sstep((t - (t1 - 1.3)) / 1.3))
            tg = fn(t); sp = T.ship_pose(t)
            if tg[0] == 'pt':            # the ship rests during these shots: ship space = world
                dx, dy, dz = tg[1] - x, tg[2] - y, tg[3] - z
                ty = math.degrees(math.atan2(dy, dx)); tp = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
            else:
                ty, tp = tg[1] - sp[4], tg[2] - sp[3]
            yaw += k * wrap(ty - yaw); pitch += k * (tp - pitch)
    if 460.0 <= t < 462.0:               # the blow
        tau = t - 460.0; kk = math.exp(-tau * 3.5)
        pitch += -10.0 * kk * math.cos(tau * 17.0); roll += 7.0 * kk * math.sin(tau * 13.0); yaw += 4.0 * kk * math.sin(tau * 21.0)
        z += -0.05 * kk
    return (x, y, z, yaw, pitch, roll, focal)


def rings2(t):
    out = _orig['rings'](t)
    if 273.4 < t < 281.0:                # the cover of the niche falls into the water
        out = [((T.PANEL[0] + T.PN[0] * 0.45) * 100.0, (T.PANEL[1] + T.PN[1] * 0.45) * 100.0, 273.4, 2.2)] + out
    return out[:8]


def _to_world(p, t):
    sx, sy, sz, sp, syaw, sr = T.ship_pose(t)
    v = ML.greater_greater_vector_rotator(unreal.Vector(p[0] * 100.0, p[1] * 100.0, p[2] * 100.0), unreal.Rotator(pitch=sp, yaw=syaw, roll=sr))
    return unreal.Vector(v.x + sx * 100.0, v.y + sy * 100.0, v.z + sz * 100.0)


def _show(a, on_):
    a.set_actor_hidden_in_game(not on_); a.set_is_temporarily_hidden_in_editor(not on_)


def apply_time2(t):
    _orig['apply_time'](t)
    A = T.A; PN = T.PN; PANEL = T.PANEL
    # glow of the plasma on the panel and the gloves
    gi = round(1.5 * ease(T.PLASMA, t)[0] * (0.75 + 0.25 * n1(t * 11.0, 41)), 2)
    if _S.get('pg') != gi:
        _S['pg'] = gi; lc = A('PlasmaGlow').point_light_component; lc.set_intensity(gi); lc.set_visibility(gi > 0.0)
    if gi > 0.0: A('PlasmaGlow').set_actor_location(_to_world((5.9, 0.0, 3.25), t), False, False)
    # cloud layer and spray over the glass
    z = T.ship_pose(t)[2]
    cw = round(sstep((2400.0 - z) / 500.0) * sstep((z - 850.0) / 400.0), 3) if 70.0 < t < 86.0 else 0.0
    if _S.get('cw') != cw:
        _S['cw'] = cw; A('PPV_Cloud').set_editor_property('blend_weight', cw)
    sw = round(ease(SPRAY, t)[0], 3)
    if _S.get('sw') != sw:
        _S['sw'] = sw; A('PPV_Spray').set_editor_property('blend_weight', sw)
    # the drone turns its lens to us while it circles
    d = drone_world2(t)
    if d is not None and 165.5 < t < 179.0:
        px, py, _ = cr(T.CAM_P, t)
        base = ease(T.DR_Y, t)[0]
        k = sstep((t - 165.5) / 1.5) * (1.0 - sstep((t - 177.5) / 1.5))
        yw = base + k * wrap(math.degrees(math.atan2(py - d[1], px - d[0])) - base)
        A('Svetlyak').set_actor_rotation(unreal.Rotator(pitch=2.0 * math.sin(t * 1.1), yaw=yw - 90.0, roll=2.0 * math.sin(t * 0.8)), False)
    # the niche: cutting, the cover falls into the water
    if t >= 238.0:
        pan = A('wr_panel'); p0 = T._LAST['panel0']; r0 = _S['panrot0']
        k1 = sstep((t - 272.0) / 0.6); k2 = max(0.0, min(1.0, (t - 272.6) / 1.1)); fall = k2 * k2
        off = 12.0 * k1 + 45.0 * fall
        pan.set_actor_location(unreal.Vector(p0.x + PN[0] * off, p0.y + PN[1] * off, lerp(p0.z + PN[2] * 12.0 * k1, 12.0, fall)), False, False)
        pan.set_actor_rotation(unreal.Rotator(pitch=r0.pitch + 70.0 * fall, yaw=r0.yaw + 25.0 * fall, roll=r0.roll + 15.0 * fall), False)
        _show(pan, True)
    cutting = 250.0 < t < 272.0
    c0 = ((PANEL[0] + PN[0] * 0.05) * 100.0, (PANEL[1] + PN[1] * 0.05) * 100.0, (PANEL[2] + 0.03) * 100.0)
    if cutting or _S.get('cut') != cutting:
        cl = A('CutterLight')
        cl.set_actor_location(unreal.Vector(*c0), False, False)
        cl.point_light_component.set_intensity(1.1 * (0.3 + 0.7 * abs(n1(t * 23.0, 31))) if cutting else 0.0)
        for i in range(8):
            a = A('Spark%d' % i)
            if cutting:
                u = t * 2.6 + i * 0.861; ph = u % 1.0; sd = i * 3.1 + math.floor(u) * 1.7
                dx, dy, dz = PN[0] + 0.7 * n1(sd, 51), PN[1] + 0.7 * n1(sd, 52), 0.5 + 0.6 * n1(sd, 53)
                a.set_actor_location(unreal.Vector(c0[0] + dx * 55.0 * ph, c0[1] + dy * 55.0 * ph, c0[2] + dz * 40.0 * ph - 90.0 * ph * ph), False, False)
                sc = 0.03 * (1.0 - 0.7 * ph); a.set_actor_scale3d(unreal.Vector(sc, sc, sc))
            if _S.get('cut') != cutting: _show(a, cutting)
        _S['cut'] = cutting
    elif 236.0 < t <= 250.0:
        A('CutterLight').point_light_component.set_intensity(0.0)      # v1 lit the cutter earlier
    # the storage: slides out with a green light, then the drone carries it to the ship
    if t >= 238.0:
        st = A('wr_storage'); s0 = T._LAST['stor0']
        ks = sstep((t - 278.0) / 14.0)
        out = (s0.x + PN[0] * 42.0 * ks, s0.y + PN[1] * 42.0 * ks, s0.z + PN[2] * 42.0 * ks)
        loc = out
        if d is not None and t >= 294.0:
            kg = sstep((t - 294.0) / 2.0)
            loc = (lerp(out[0], d[0] * 100.0, kg), lerp(out[1], d[1] * 100.0, kg), lerp(out[2], d[2] * 100.0 - 17.0, kg))
        st.set_actor_location(unreal.Vector(*loc), False, False)
        _show(st, t < 397.0)
        ind = 273.0 <= t < 397.0
        il = A('IndicatorLight')
        if ind:
            kk = 0.0 if t >= 296.0 else 20.0
            il.set_actor_location(unreal.Vector(loc[0] + PN[0] * kk, loc[1] + PN[1] * kk, loc[2] + PN[2] * kk + 4.0), False, False)
        if _S.get('ind') != ind:
            _S['ind'] = ind; il.point_light_component.set_intensity(0.25 if ind else 0.0); il.point_light_component.set_visibility(ind)
    # the beacon of the probe still blinks
    bon = (t % 1.6) < 0.25
    if _S.get('bon') != bon and _S.get('beacon_mi') is not None:
        _S['bon'] = bon
        MEL.set_material_instance_scalar_parameter_value(_S['beacon_mi'], 'EmissiveStrength', 12.0 if bon else 0.4)
        MEL.update_material_instance(_S['beacon_mi'])
    # the impact: water rises over the glass, blackout, then the underwater light
    if 458.8 <= t < T.T_UP - 0.4:
        fr = sstep((t - 459.0) / 1.0)
        dk = 0.0
        if t >= 460.0: dk = 1.0 if t < 460.5 else 1.0 - sstep((t - 460.5) / 0.7)
        val = (round(fr, 3), round(dk, 3))
        if t >= 459.0: A('PPV_Underwater').set_editor_property('blend_weight', 1.0)
    else:
        val = (1.0, 0.0)
    if _S.get('fl') != val and _S.get('uw_mi') is not None:
        _S['fl'] = val
        MEL.set_material_instance_vector_parameter_value(_S['uw_mi'], 'Flood', unreal.LinearColor(val[0], val[1], 0.0, 0.0))
        MEL.update_material_instance(_S['uw_mi'])
    return t


def install():
    """reload the v1 timeline and put the v2 keys and behaviours over it"""
    global DR_A, DR_B
    importlib.reload(T)
    _orig.clear(); _S.clear()
    _orig.update(cam_local=T.cam_local, apply_time=T.apply_time, rings=T.rings, drone_world=T.drone_world, CAM_P=list(T.CAM_P), CAM_L=list(T.CAM_L))
    T.CAM_P = cam_p2(); T.CAM_L = cam_l2()
    T.drone_world = drone_world2
    DR_A, DR_B = build_drone_keys()
    T.DR_Y = DR_Y2; T.DR_ARM = DR_ARM2
    T.rings = rings2; T.cam_local = cam_local2; T.apply_time = apply_time2
    n = T.init()
    _S['panrot0'] = T.A('wr_panel').get_actor_rotation()
    for p in EAL.list_assets('/Game/Scene1/Props/ProbeWreck', recursive=True):
        if p.endswith('/emissive_beacon.emissive_beacon'): _S['beacon_mi'] = EAL.load_asset(p)
    _S['uw_mi'] = EAL.load_asset('/Game/Scene1/Materials/MI_PP_Underwater')
    return n


def frames_v2(lead=12):
    fr = []
    for a, b in INTERVALS:
        fr += list(range(int(a * 24) - lead, int(b * 24) + 1))
    return fr


def render_v2():
    return T.render(0, 0, outdir=OUT2, frames=frames_v2())
