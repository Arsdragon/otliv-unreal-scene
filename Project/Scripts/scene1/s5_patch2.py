# S5: one-off patch of the mood layer (s3_mood.py). Run once outside Unreal:  python -I s5_patch2.py
#  - drops on the glass get a state by phase of the story (amount, speed, direction of the flow); the depth cut is gone;
#  - a flash is 2-3 bright frames and half a second of dying away, with a place on the wall and a light on the scene;
#  - bubbles burst out after the blow and thin out; the cutter is a small hot spot with streaks of sparks and puffs of steam.
import os
D = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(D, 's3_mood.py'); s = open(p, encoding='utf-8').read()

a = s.index('def nearcut(t):'); b = s.index('def _set(key, val, fn):')
s = s[:a] + r'''WET = [(500.3, 0.8), (504.0, 0.5), (515.0, 0.3), (548.0, 0.2)]      # the canopy after surfacing: rare drops running down
BUBBLES = [(460.0, 1.8), (464.0, 1.2), (472.0, 0.8), (498.0, 0.6)]   # a burst after the blow, then fewer
FLASH_POS = {411.0: (-0.25, 0.12), 433.5: (0.30, 0.20), 449.0: (0.05, 0.32)}   # where on the wall: sideways, up


def glass_state(t, rain, uw):
    """-> (amount, speed, flow x, flow y) of the drops on the glass in front of the camera (screen: x right, y down)"""
    if uw: return (0.0, 0.0, 0.0, 1.0)
    if t >= 500.0: return (max(rain * 0.6, ease(WET, t)[0]), 0.45, 0.03, 1.0)                  # afloat: rare, straight down
    if t >= 398.0: return (rain, 1.0, 0.22, -1.0)                                               # the storm drives them up the canopy
    if t >= 389.6: return (0.45 * rain * max(0.0, 1.0 - (t - 389.6) / 1.5), 0.6, 0.10, 1.0)     # inside the ship the visor dries
    if t >= 104.0: return (0.45 * rain, 0.6, 0.10, 1.0)                                         # the helmet: down the visor
    return (rain, 1.0, 0.0, -1.0)


def flash(t):
    """-> (level, sideways, up): three frames at full, then about half a second of dying away with one flutter"""
    for tf in FLASH_T:
        u = t - tf
        if -0.001 <= u < 0.125: return (1.0,) + FLASH_POS[tf]
        if 0.125 <= u < 0.85:
            return (math.exp(-(u - 0.125) / 0.15) * (1.0 + 0.6 * math.exp(-((u - 0.33) / 0.035) ** 2)),) + FLASH_POS[tf]
    return (0.0, 0.0, 0.2)


''' + s[b:]

old = "    fl = flash(t) if not uw else 0.0\n"
assert old in s
s = s.replace(old, "    fl, fy, fz = flash(t) if not uw else (0.0, 0.0, 0.2)\n")

a = s.index("    cockpit = t < 104.0 or t > 398.0\n"); b = s.index("    _set('wxw',")
s = s[:a] + r'''    gs = glass_state(t, rain, uw)
    bow = ease(BOW, t)[0]
    wind = ease(WIND, t)[0]
    w = _r3(rain, 0.20 + 0.05 * wind, dust, gs[0], bow, fl, gs[1], gs[2], gs[3], fy, fz)
    if _S.get('wx') != w:
        _S['wx'] = w; mi = _S['mi_wx']
        MEL.set_material_instance_vector_parameter_value(mi, 'Rain', unreal.LinearColor(w[0], w[1], 1.0, 0.0))
        MEL.set_material_instance_vector_parameter_value(mi, 'Dust', unreal.LinearColor(w[2], 2.2, 0.0, 0.0))
        MEL.set_material_instance_vector_parameter_value(mi, 'Glass', unreal.LinearColor(w[3], w[6], w[7], w[8]))
        MEL.set_material_instance_vector_parameter_value(mi, 'Rainbow', unreal.LinearColor(w[4], 0.0, 0.0, 0.0))
        MEL.set_material_instance_vector_parameter_value(mi, 'Flash', unreal.LinearColor(w[5], w[9], w[10], 0.0))
        MEL.update_material_instance(mi)
    flc = A('FlashLight').get_component_by_class(unreal.DirectionalLightComponent)
    _set('flash_l', round(6.0 * fl, 2), lambda v: (flc.set_intensity(v), flc.set_visibility(v > 0.0)))
    if uw: _set('bub', round(ease(BUBBLES, t)[0], 2), lambda v: _mi_vec(_S['mi_uw'], 'Amounts', (0.10, 0.55 * v, 0.10, 0.22)))
    # the cutter: a small hot spot instead of a floodlight, sparks as streaks along their flight, puffs of steam
    cutting = 250.0 < t < 272.0; steaming = 250.3 < t < 273.6
    if cutting or steaming or _S.get('cut3'):
        PN = T.PN; PANEL = T.PANEL
        c0 = ((PANEL[0] + PN[0] * 0.05) * 100.0, (PANEL[1] + PN[1] * 0.05) * 100.0, (PANEL[2] + 0.03) * 100.0)
        cl = A('CutterLight')
        cl.set_actor_location(unreal.Vector(c0[0] + PN[0] * 7.0, c0[1] + PN[1] * 7.0, c0[2] + PN[2] * 7.0), False, False)
        cl.point_light_component.set_intensity(0.30 * (0.35 + 0.65 * abs(T.n1(t * 23.0, 31))) if cutting else 0.0)
        for i in range(8):
            if not cutting: break
            u = t * 2.6 + i * 0.861; ph = u % 1.0; sd = i * 3.1 + math.floor(u) * 1.7
            dx, dy, dz = PN[0] + 0.7 * T.n1(sd, 51), PN[1] + 0.7 * T.n1(sd, 52), 0.5 + 0.6 * T.n1(sd, 53)
            vx, vy, vz = dx * 55.0, dy * 55.0, dz * 40.0 - 180.0 * ph
            sa = A('Spark%d' % i); k = 1.0 - 0.6 * ph
            sa.set_actor_rotation(unreal.Rotator(pitch=math.degrees(math.atan2(vz, math.hypot(vx, vy))), yaw=math.degrees(math.atan2(vy, vx)), roll=0.0), False)
            sa.set_actor_scale3d(unreal.Vector(0.085 * k, 0.011 * k, 0.011 * k))
        cam = A('CAM_Film').get_actor_location()
        for i in range(3):
            pa = A('Puff%d' % i); u = (t * 0.55 + i / 3.0) % 1.0
            born = t - u / 0.55                                              # when this puff left the cut
            on = steaming and 250.3 < born < 272.0
            if on:
                loc = unreal.Vector(c0[0] + PN[0] * (8.0 + 22.0 * u) + 6.0 * math.sin(i * 2.1 + u * 3.0), c0[1] + PN[1] * (8.0 + 22.0 * u) + 6.0 * math.cos(i * 1.7 + u * 2.0),
                                    c0[2] + 6.0 + 40.0 * u)
                pa.set_actor_location(loc, False, False)
                pa.set_actor_rotation(ML.compose_rotators(unreal.Rotator(pitch=-90.0, yaw=0.0, roll=0.0), ML.find_look_at_rotation(loc, cam)), False)
                sc = 0.10 + 0.34 * u; pa.set_actor_scale3d(unreal.Vector(sc, sc, sc))
                _mi_sc(_S['mi_puff'][i], 'Fade', round(0.55 * min(1.0, u / 0.15) * (1.0 - u) ** 1.5, 3))
            if _S.get('puff%d' % i) != on:
                _S['puff%d' % i] = on; V._show(pa, on)
        _S['cut3'] = cutting or steaming
''' + s[b:]

old = "    _S['mi_veil'] = EAL.load_asset(M + 'MI_WaveVeil'); _S['mi_roll'] = EAL.load_asset(M + 'MI_WaveRoll')\n"
assert old in s
s = s.replace(old, old + "    _S['mi_uw'] = EAL.load_asset(M + 'MI_PP_Underwater'); _S['mi_puff'] = [EAL.load_asset(M + 'MI_Puff%d' % i) for i in range(3)]\n")
assert 'nearcut' not in s
open(p, 'w', encoding='utf-8').write(s)
import ast; ast.parse(s)
print('patched')
