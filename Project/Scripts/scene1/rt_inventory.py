# Real-time version, step 1: what exactly does the Python timeline change over time?
# Until now every frame of the scene was SET by Python in the editor (s3_timeline -> s3_v2 -> s3_mood). A game cannot do
# that: for the scene to play by itself, every changing value has to live in a Level Sequence (or in materials driven by it).
# This script walks the timeline in coarse steps and writes down everything that moves or changes:
#   transforms and visibility of actors, lights, fog, sky, post-process volumes, the material parameter collection,
#   the parameters of the material instances that were edited per frame.
# Run inside the editor after M.install():   import rt_inventory; rt_inventory.run()   -> Scripts\scene1\rt_inventory.json
import json, os, unreal
import s3_timeline as T, s3_mood as M, s1u

MEL = unreal.MaterialEditingLibrary; EAL = unreal.EditorAssetLibrary; ML = unreal.MaterialLibrary
HERE = os.path.dirname(os.path.abspath(__file__))
MIS = ['MI_PP_Weather', 'MI_PP_Underwater', 'MI_Overcast', 'MI_WaveVeil', 'MI_WaveRoll', 'MI_Spray', 'MI_Mist', 'MI_MistB', 'MI_MistC',
       'MI_WaveBoilA', 'MI_WaveBoilB', 'MI_Puff0', 'MI_Puff1', 'MI_Puff2', 'MI_PP_Cloud', 'MI_PP_Spray']


def r(v, n=3): return round(float(v), n)
def vec(v): return (r(v.x, 1), r(v.y, 1), r(v.z, 1))
def rot(v): return (r(v.pitch, 2), r(v.yaw, 2), r(v.roll, 2))
def col(c): return (r(c.r), r(c.g), r(c.b), r(c.a))


def snapshot(actors, mpc, mis):
    s = {}
    for a in actors:
        lb = a.get_actor_label()
        s[lb + '|loc'] = vec(a.get_actor_location()); s[lb + '|rot'] = rot(a.get_actor_rotation()); s[lb + '|scale'] = vec(a.get_actor_scale3d())
        s[lb + '|hidden'] = bool(a.is_hidden_ed()) or bool(a.get_editor_property('hidden'))
        for c in a.get_components_by_class(unreal.LightComponent):
            n = lb + '|' + c.get_class().get_name()
            s[n + '.intensity'] = r(c.intensity); s[n + '.color'] = col(c.get_light_color()); s[n + '.visible'] = bool(c.is_visible())
        for c in a.get_components_by_class(unreal.ExponentialHeightFogComponent):
            s[lb + '|fog.density'] = r(c.get_editor_property('fog_density'), 5); s[lb + '|fog.color'] = col(c.get_editor_property('fog_inscattering_luminance'))
            s[lb + '|fog.visible'] = bool(c.is_visible())
        for c in a.get_components_by_class(unreal.SkyAtmosphereComponent):
            s[lb + '|atm.luminance'] = col(c.get_editor_property('sky_and_aerial_perspective_luminance_factor'))
        for c in a.get_components_by_class(unreal.SkyLightComponent):
            s[lb + '|sky.capture'] = bool(c.get_editor_property('real_time_capture'))
        if isinstance(a, unreal.PostProcessVolume):
            st = a.get_editor_property('settings')
            s[lb + '|ppv.weight'] = r(a.get_editor_property('blend_weight'))
            s[lb + '|ppv.exposure'] = r(st.get_editor_property('auto_exposure_bias'))
            cs = st.get_editor_property('color_saturation'); cg = st.get_editor_property('color_gain')
            s[lb + '|ppv.saturation'] = (r(cs.x), r(cs.y), r(cs.z)); s[lb + '|ppv.gain'] = (r(cg.x), r(cg.y), r(cg.z))
        if isinstance(a, unreal.CineCameraActor):
            s[lb + '|focal'] = r(a.get_cine_camera_component().get_editor_property('current_focal_length'), 2)
    w = s1u.world()
    for p in mpc.get_editor_property('scalar_parameters'):
        pn = p.get_editor_property('parameter_name'); s['MPC|' + str(pn)] = r(ML.get_scalar_parameter_value(w, mpc, pn), 4)
    for p in mpc.get_editor_property('vector_parameters'):
        pn = p.get_editor_property('parameter_name'); s['MPC|' + str(pn)] = col(ML.get_vector_parameter_value(w, mpc, pn))
    for nm, mi in mis.items():
        for pn in MEL.get_scalar_parameter_names(mi): s['MI|%s.%s' % (nm, pn)] = r(MEL.get_material_instance_scalar_parameter_value(mi, pn), 4)
        for pn in MEL.get_vector_parameter_names(mi): s['MI|%s.%s' % (nm, pn)] = col(MEL.get_material_instance_vector_parameter_value(mi, pn))
    for i in range(1, 6):
        mi = EAL.load_asset('/Game/Scene1/Chaika/Cockpit/chaika_cockpit/Materials/screen_%d' % i)
        t = MEL.get_material_instance_texture_parameter_value(mi, 'EmissiveTexture')
        s['MI|screen_%d.EmissiveTexture' % i] = t.get_name() if t else None
    b = getattr(__import__('s3_v2'), '_S', {}).get('beacon_mi')
    if b: s['MI|beacon.EmissiveStrength'] = r(MEL.get_material_instance_scalar_parameter_value(b, 'EmissiveStrength'))
    return s


_ST = {'first': None, 'changed': {}, 'n': 0}


def reset():
    _ST['first'] = None; _ST['changed'] = {}; _ST['n'] = 0


def chunk(t0, t1, step=0.25):
    """one portion of the walk. Keep portions short (about 60 steps) and let the editor draw between them: a run of two
    thousand steps in one call killed the graphics driver (DXGI_ERROR_DEVICE_REMOVED) - every step updates material instances."""
    actors = [a for a in s1u.EAS.get_all_level_actors() if a.get_actor_label()]
    mpc = EAL.load_asset('/Game/Scene1/MPC_Otliv')
    mis = {n: EAL.load_asset('/Game/Scene1/Materials/' + n) for n in MIS}
    mis = {n: m for n, m in mis.items() if m is not None}
    t = t0
    while t < t1 - 1e-6:
        T.apply_time(t)
        s = snapshot(actors, mpc, mis); _ST['n'] += 1
        if _ST['first'] is None: _ST['first'] = s
        else:
            for key, v in s.items():
                if v != _ST['first'].get(key):
                    c = _ST['changed'].setdefault(key, {'first_change': t, 'values': set()})
                    if len(c['values']) < 40: c['values'].add(json.dumps(v))
        t += step
    return _ST['n'], len(_ST['changed'])


def finish():
    out = {k: {'first_change': v['first_change'], 'distinct': len(v['values'])} for k, v in _ST['changed'].items()}
    json.dump({'samples': _ST['n'], 'keys_total': len(_ST['first']), 'changing': out}, open(os.path.join(HERE, 'rt_inventory.json'), 'w', encoding='utf-8'), indent=0, sort_keys=True)
    return _ST['n'], len(_ST['first']), len(out)


def start(step=0.25, t0=0.0, t1=550.0, per_tick=2):
    """the whole walk, a couple of steps per editor tick, so that every step is drawn before the next ones come"""
    reset()
    st = {'t': t0, 'h': None, 'done': False}
    def tick(dt):
        if st['t'] >= t1 + 1e-6:
            unreal.unregister_slate_post_tick_callback(st['h']); st['done'] = True
            _ST['result'] = finish(); return
        a = st['t']; b = min(t1 + step, a + step * per_tick)
        chunk(a, b, step); st['t'] = b
    st['h'] = unreal.register_slate_post_tick_callback(tick)
    _ST['job'] = st
    return 'started'


def progress():
    j = _ST.get('job') or {}
    return {'t': j.get('t'), 'done': j.get('done'), 'samples': _ST['n'], 'changing': len(_ST['changed']), 'result': _ST.get('result')}
