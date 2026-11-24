# Real-time version of scene 1: bakes the Python timeline into a Level Sequence that plays by itself in a game.
# Until now Python set every frame (s3_timeline -> s3_v2 -> s3_mood). Here Python is run once over the frames, everything
# it changes is read back from the level and written as keys:
#   - transforms of every actor whose own (relative) transform changes, visibility of the ones that are shown and hidden;
#   - lights (intensity, colour), sky light, fog, sky, post-process volumes (weight, exposure, grading), focal length;
#   - the material parameter collections MPC_Otliv (time of the scene, the wave, rings of the steps ...) and MPC_OtlivFX
#     (rain, drops on the glass, flash, the underwater picture);
#   - parameters of the material instances that Python edits on meshes (ribbons of mist, overcast, puffs, the beacon):
#     a game cannot edit an instance, so a "component material" track animates the mesh's own copy of the material;
#   - the pictures of the cockpit screens: one material per picture, a track switches the material of the screen;
#   - the soundtrack, the console variables of the "quality 3" mode, camera cuts (two twin cameras take turns, so that the
#     engine knows about every cut and does not smear the first frame after it), two seconds of black before the start.
# Keys are linear; frames that lie on a straight line between their neighbours are skipped.
# Inside the editor, after M.install():
#   import rt_bake; rt_bake.start(f0, f1, name='SEQ_Otliv_RT')      # a few frames per editor tick; rt_bake.progress()
#   rt_bake.prepare_game('SEQ_Otliv_RT')                            # the last thing before saving the level for a build
import os, math, time, pickle, unreal
from array import array
import s3_timeline as T, s1u

AT = unreal.AssetToolsHelpers.get_asset_tools(); EAL = unreal.EditorAssetLibrary; ML = unreal.MaterialLibrary; MEL = unreal.MaterialEditingLibrary
PATH = '/Game/Scene1/Seq'
FPS = 24
PREROLL = 48                    # frames of black before frame 0: the game loads textures and shaders of the first shot
LIN = unreal.MovieSceneKeyInterpolation.LINEAR; CONST = unreal.MovieSceneKeyInterpolation.CONSTANT
DR = unreal.MovieSceneTimeUnit.DISPLAY_RATE
CAM, CAM_B = 'CAM_Film', 'CAM_Film_B'
MI_DIR = '/Game/Scene1/Materials/'
# (actor, material slot, instance or None = take it from the mesh, scalar parameters, vector parameters)
MATS = [('Overcast', 0, 'MI_Overcast', ['Density'], ['Color']), ('WaveVeil', 0, 'MI_WaveVeil', ['Density', 'Gain'], []),
        ('WaveRoll', 0, 'MI_WaveRoll', ['Density', 'Gain'], ['Haze']), ('WaveSpray', 0, 'MI_Spray', ['Gain'], []),
        ('WaveMist', 0, 'MI_Mist', ['Gain'], []), ('WaveMistB', 0, 'MI_MistB', ['Gain'], []), ('WaveMistC', 0, 'MI_MistC', ['Gain'], []),
        ('WaveBoilA', 0, 'MI_WaveBoilA', ['Gain'], []), ('WaveBoilB', 0, 'MI_WaveBoilB', ['Gain'], []),
        ('Puff0', 0, 'MI_Puff0', ['Fade'], []), ('Puff1', 0, 'MI_Puff1', ['Fade'], []), ('Puff2', 0, 'MI_Puff2', ['Fade'], []),
        ('wr_mast_top', 1, None, ['EmissiveStrength'], [])]              # the beacon of the wreck
SOUND_FILE = r'C:\UnrealScenes\Audio\scene1\mix_v3.wav'
SOUND = '/Game/Scene1/Audio/mix_v3'
CVARS = 'r.SSR.Quality 0, r.LightFunctionAtlas 0, r.VSync 1'       # the first two: what q_shots.quality() sets by hand in the editor; no tearing
DATA = 'C:/UnrealScenes/Project/Saved/rt_bake_data.pkl'
_J = globals().get('_J') or {}         # survives importlib.reload: the recorded frames can be written again after a fix


def rewrite():
    """build the sequence again from the frames already recorded (after a change in the writing code)"""
    j = _J
    if not j.get('data') or (j.get('phase') not in ('done', 'failed')): return 'nothing recorded, or a bake is running'
    j['phase'] = 'write'; j['done'] = False; j['notes'] = []; j['msg'] = ''; j['t0'] = time.time(); j['gen'] = _write_gen(j)
    j['h'] = unreal.register_slate_post_tick_callback(_tick)
    return 'writing'


def _rel(a):
    c = a.root_component
    l = c.get_editor_property('relative_location'); r = c.get_editor_property('relative_rotation'); s = c.get_editor_property('relative_scale3d')
    return (l.x, l.y, l.z, r.roll, r.pitch, r.yaw, s.x, s.y, s.z)


def _hidden(a): return bool(a.get_editor_property('hidden')) or bool(a.is_hidden_ed())


def _props(actors):
    """animated properties besides transforms: (key, binding kind, actor, component, type, property name, path, reader)"""
    out = []
    for a in actors:
        lb = a.get_actor_label()
        for c in a.get_components_by_class(unreal.LightComponent):
            out.append((lb + '.Intensity', 'comp', a, c, 'float', 'Intensity', 'Intensity', lambda c=c: (float(c.intensity) if c.is_visible() else 0.0,)))
            out.append((lb + '.LightColor', 'comp', a, c, 'color', 'LightColor', 'LightColor', lambda c=c: tuple(c.get_light_color().to_tuple())))
        for c in a.get_components_by_class(unreal.SkyLightComponent):
            out.append((lb + '.SkyIntensity', 'comp', a, c, 'float', 'Intensity', 'Intensity', lambda c=c: (float(c.get_editor_property('intensity')) if c.is_visible() else 0.0,)))
            out.append((lb + '.SkyColor', 'comp', a, c, 'color', 'LightColor', 'LightColor', lambda c=c: tuple(c.get_light_color().to_tuple())))      # linear, as the track's setter wants it (the property itself is 8-bit sRGB, BGRA)
        for c in a.get_components_by_class(unreal.ExponentialHeightFogComponent):
            out.append((lb + '.FogDensity', 'comp', a, c, 'float', 'FogDensity', 'FogDensity', lambda c=c: (float(c.get_editor_property('fog_density')) if c.is_visible() else 0.0,)))
            out.append((lb + '.FogColor', 'comp', a, c, 'color', 'FogInscatteringLuminance', 'FogInscatteringLuminance', lambda c=c: tuple(c.get_editor_property('fog_inscattering_luminance').to_tuple())))
        for c in a.get_components_by_class(unreal.SkyAtmosphereComponent):
            out.append((lb + '.SkyLuminance', 'comp', a, c, 'color', 'SkyAndAerialPerspectiveLuminanceFactor', 'SkyAndAerialPerspectiveLuminanceFactor',
                        lambda c=c: tuple(c.get_editor_property('sky_and_aerial_perspective_luminance_factor').to_tuple())))
        if isinstance(a, unreal.PostProcessVolume):
            out.append((lb + '.BlendWeight', 'actor', a, None, 'float', 'BlendWeight', 'BlendWeight', lambda a=a: (float(a.get_editor_property('blend_weight')),)))
            # Sequencer switches the "override" checkbox ON for every post-process setting it animates. A volume that does not
            # override exposure or grading (rain, clouds, spray, plasma) must get no such tracks: otherwise in the game it
            # starts to override them with the unused defaults of its settings (the storm came out 1.5 stops too bright).
            st0 = a.get_editor_property('settings')
            def sat(a=a):
                v = a.get_editor_property('settings').get_editor_property('color_saturation'); return (v.x, v.y, v.z, v.w)
            def gain(a=a):
                v = a.get_editor_property('settings').get_editor_property('color_gain'); return (v.x, v.y, v.z, v.w)
            if st0.get_editor_property('override_auto_exposure_bias'):
                out.append((lb + '.Exposure', 'actor', a, None, 'float', 'AutoExposureBias', 'Settings.AutoExposureBias', lambda a=a: (float(a.get_editor_property('settings').get_editor_property('auto_exposure_bias')),)))
            if st0.get_editor_property('override_color_saturation'):
                out.append((lb + '.Saturation', 'actor', a, None, 'vec4', 'ColorSaturation', 'Settings.ColorSaturation', sat))
            if st0.get_editor_property('override_color_gain'):
                out.append((lb + '.Gain', 'actor', a, None, 'vec4', 'ColorGain', 'Settings.ColorGain', gain))
        if isinstance(a, unreal.CineCameraActor):
            c = a.get_cine_camera_component()
            out.append((lb + '.Focal', 'comp', a, c, 'float', 'CurrentFocalLength', 'CurrentFocalLength', lambda c=c: (float(c.get_editor_property('current_focal_length')),)))
    return out


def _mpc_params(mpc):
    sc = [p.get_editor_property('parameter_name') for p in mpc.get_editor_property('scalar_parameters')]
    ve = [p.get_editor_property('parameter_name') for p in mpc.get_editor_property('vector_parameters')]
    return sc, ve


def _put(d, key, vals):
    cols = d.get(key)
    if cols is None: cols = d[key] = [array('d') for _ in vals]
    for c, v in zip(cols, vals): c.append(v)


def _setup(f0, f1, name):
    """the level side of a bake: actors, properties, collections, materials on meshes"""
    actors = [a for a in s1u.EAS.get_all_level_actors() if a.get_actor_label() and a.root_component is not None and a.get_actor_label() != CAM_B]
    labels = [a.get_actor_label() for a in actors]
    mpcs = [m for m in (EAL.load_asset('/Game/Scene1/MPC_Otliv'), EAL.load_asset('/Game/Scene1/MPC_OtlivFX')) if m is not None]
    by = dict(zip(labels, actors)); mats = []
    for lb, slot, mi, sc, ve in MATS:
        a = by.get(lb)
        if a is None: continue
        c = a.get_component_by_class(unreal.StaticMeshComponent)
        m = EAL.load_asset(MI_DIR + mi) if mi else c.get_material(slot)
        if m is not None and isinstance(m, unreal.MaterialInstanceConstant): mats.append((lb, a, c, slot, m, sc, ve))
    j = {'f0': f0, 'f1': f1, 'name': name, 'actors': actors, 'labels': labels, 'mpcs': mpcs, 'props': _props(actors), 'mats': mats, 'phase': 'detect',
         'f': f0, 'done': False, 'rel0': None, 'hid0': None, 'dyn': set(), 'vis': set(), 'data': {},
         'h': None, 'msg': '', 'notes': [], 't0': time.time()}
    j['sc'] = [(m, n) for m in mpcs for n in _mpc_params(m)[0]]; j['ve'] = [(m, n) for m in mpcs for n in _mpc_params(m)[1]]
    return j


def start(f0=0, f1=13200, name='SEQ_Otliv_RT', per_tick=2, detect_step=6):
    """record frames f0..f1 (24 fps) and build the sequence /Game/Scene1/Seq/<name>"""
    if _J.get('h') is not None and not _J.get('done'): return 'a bake is running already'
    j = _setup(f0, f1, name); j['step'] = detect_step; j['per_tick'] = per_tick
    _J.clear(); _J.update(j)
    _J['h'] = unreal.register_slate_post_tick_callback(_tick)
    return 'started: %d actors, %d property channels, %d + %d parameters in %d collections, %d materials on meshes' % (
        len(j['actors']), len(j['props']), len(j['sc']), len(j['ve']), len(j['mpcs']), len(j['mats']))


def save_data(path=None):
    """the recorded frames on disk: a bake of the whole scene takes half an hour, an editor crash must not cost it"""
    j = _J; path = path or DATA
    with open(path, 'wb') as fh:
        pickle.dump({'f0': j['f0'], 'f1': j['f1'], 'name': j['name'], 'data': j['data'], 'tr': [lb for lb, a in j['tr']],
                     'vi': [lb for lb, a in j['vi']], 'cuts': j.get('cuts')}, fh, protocol=4)
    return os.path.getsize(path)


def load_data(path=None):
    """the recorded frames back in a fresh editor session: then rewrite() and rt_check.compare() work again"""
    with open(path or DATA, 'rb') as fh: s = pickle.load(fh)
    j = _setup(s['f0'], s['f1'], s['name']); by = dict(zip(j['labels'], j['actors']))
    j['tr'] = [(lb, by[lb]) for lb in s['tr'] if lb in by]; j['vi'] = [(lb, by[lb]) for lb in s['vi'] if lb in by]
    j['data'] = s['data']; j['cuts'] = s.get('cuts') or []; j['phase'] = 'done'; j['done'] = True; j['f'] = s['f1'] + 1
    _J.clear(); _J.update(j)
    return len(j['data']), len(j['tr']), len(j['vi'])


def _tick(dt):
    j = _J
    if j.get('busy'): return          # saving an asset shows a progress window, and that ticks the editor from inside this callback
    j['busy'] = True
    try:
        _tick2(j)
    finally:
        j['busy'] = False


def _tick2(j):
    try:
        if j['phase'] == 'detect':
            for _ in range(j['per_tick']):
                if j['f'] > j['f1']:
                    j['phase'] = 'record'; j['f'] = j['f0']
                    j['tr'] = [(lb, a) for lb, a in zip(j['labels'], j['actors']) if lb in j['dyn']]
                    j['vi'] = [(lb, a) for lb, a in zip(j['labels'], j['actors']) if lb in j['vis']]
                    return
                T.apply_time(j['f'] / float(FPS))
                rel = {lb: _rel(a) for lb, a in zip(j['labels'], j['actors'])}; hid = {lb: _hidden(a) for lb, a in zip(j['labels'], j['actors'])}
                if j['rel0'] is None: j['rel0'], j['hid0'] = rel, hid
                else:
                    for lb, v in rel.items():
                        if lb not in j['dyn'] and any(abs(x - y) > 1e-3 for x, y in zip(v, j['rel0'][lb])): j['dyn'].add(lb)
                    for lb, v in hid.items():
                        if v != j['hid0'][lb]: j['vis'].add(lb)
                j['f'] += j['step']
        elif j['phase'] == 'record':
            w = s1u.world(); d = j['data']
            for _ in range(j['per_tick']):
                if j['f'] > j['f1']:
                    j['phase'] = 'write'; j['gen'] = _write_gen(j); return
                T.apply_time(j['f'] / float(FPS))
                for lb, a in j['tr']: _put(d, 'T|' + lb, _rel(a))
                for lb, a in j['vi']: _put(d, 'V|' + lb, (1.0 if _hidden(a) else 0.0,))
                for p in j['props']: _put(d, 'P|' + p[0], p[7]())
                for lb, a, c, slot, mi, sc, ve in j['mats']:
                    for n in sc: _put(d, 'M|%s|%s' % (lb, n), (MEL.get_material_instance_scalar_parameter_value(mi, n),))
                    for n in ve: _put(d, 'M|%s|%s' % (lb, n), MEL.get_material_instance_vector_parameter_value(mi, n).to_tuple())
                for m, n in j['sc']: _put(d, 'S|%s|%s' % (m.get_name(), n), (ML.get_scalar_parameter_value(w, m, n),))
                for m, n in j['ve']: _put(d, 'C|%s|%s' % (m.get_name(), n), ML.get_vector_parameter_value(w, m, n).to_tuple())
                j['f'] += 1
        elif j['phase'] == 'write':
            t0 = time.time()
            try:
                while time.time() - t0 < 0.15: j['wstep'] = next(j['gen'])
            except StopIteration:
                unreal.unregister_slate_post_tick_callback(j['h']); j['phase'] = 'done'; j['done'] = True; j['took'] = round(time.time() - j['t0'])
    except Exception as e:
        import traceback
        unreal.unregister_slate_post_tick_callback(j['h'])
        j['msg'] = 'ERROR in phase %s at frame %s: %s\n%s' % (j['phase'], j['f'], e, traceback.format_exc()); j['phase'] = 'failed'; j['done'] = True


def _unwrap(vals):
    """Euler angles without jumps of 360 degrees between neighbouring frames"""
    out = [vals[0]]
    for v in vals[1:]:
        p = out[-1]; out.append(v + 360.0 * round((p - v) / 360.0))
    return out


def _pick(vals, eps, stops=(), win=24):
    """indices of the frames that need a key: all the other frames lie (within eps) on straight lines between the picked ones.
    stops: frames that always get a key (both sides of a cut)"""
    n = len(vals)
    if n <= 1 or max(vals) - min(vals) <= eps: return [0]
    keep = [0]; a = 0
    while a < n - 1:
        b = a + 1
        while b < n - 1 and b - a < win and b not in stops:
            nb = b + 1; va = vals[a]; st = (vals[nb] - va) / (nb - a); ok = True
            for k in range(a + 1, nb):
                if abs(vals[k] - (va + st * (k - a))) > eps: ok = False; break
            if not ok: break
            b = nb
        keep.append(b); a = b
    return keep


def _keys(ch, f0, vals, eps, cuts, stops):
    """writes one channel; the key before a cut holds its value (no sweep through the cut)"""
    idx = _pick(vals, eps, stops)
    for i in idx: ch.add_key(unreal.FrameNumber(f0 + i), float(vals[i]), 0.0, DR, CONST if (i + 1) in cuts else LIN)
    return len(idx)


def _jumps(cols, n, lim=150.0):
    """frames where an actor teleports: a big step that is not part of fast steady motion"""
    st = [0.0] + [math.dist((cols[0][i], cols[1][i], cols[2][i]), (cols[0][i - 1], cols[1][i - 1], cols[2][i - 1])) for i in range(1, n)]
    return set(i for i in range(1, n) if st[i] > lim and st[i] > 4.0 * max(st[i - 1], st[i + 1] if i < n - 1 else 0.0)), st


def _write_gen(j):
    f0, f1, name = j['f0'], j['f1'], j['name']; full = PATH + '/' + name; d = j['data']; n = f1 - f0 + 1; notes = j['notes']
    pre = PREROLL if f0 == 0 else 0; s0 = f0 - pre
    if EAL.does_asset_exist(full):
        # never delete: the player actor of the level refers to the sequence, and the editor then stops on a modal dialog
        # ("the asset is referenced") that nobody can answer from a script. Empty it in place instead.
        seq = EAL.load_asset(full)
        for b in list(seq.get_bindings()):
            for tr in list(b.get_tracks()): b.remove_track(tr)
            b.remove()
        for tr in list(seq.get_tracks()): seq.remove_track(tr)
    else:
        seq = AT.create_asset(name, PATH, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    seq.set_display_rate(unreal.FrameRate(FPS, 1)); seq.set_playback_start(s0); seq.set_playback_end(f1 + 1)
    try: unreal.MovieSceneSequenceExtensions.set_clock_source(seq, unreal.UpdateClockSource.PLATFORM)      # real time: the picture never falls behind the sound
    except Exception as e: notes.append('clock: %s' % e)
    tps = seq.get_tick_resolution(); tick = int(tps.numerator / tps.denominator / FPS)
    binds = {}; comp_b = {}; nk = 0; ntr = 0
    def bind(a):
        lb = a.get_actor_label()
        if lb not in binds: binds[lb] = seq.add_possessable(a)
        return binds[lb]
    def cbind(a, c):
        ck = (a.get_actor_label(), c.get_name())
        if ck not in comp_b:
            cb = seq.add_possessable(c); cb.set_parent(bind(a)); comp_b[ck] = cb
        return comp_b[ck]
    def ptime(i):
        return unreal.FrameNumber((f0 + i) * tick)
    yield 'start'
    # camera cuts: where the camera jumps, every key before the jump holds its value
    cuts = set(); cam = d.get('T|' + CAM)
    if cam:
        cuts, _st = _jumps(cam, n)
        rs = [0.0] + [max(abs((cam[k][i] - cam[k][i - 1] + 180.0) % 360.0 - 180.0) for k in (3, 4, 5)) for i in range(1, n)]
        cuts |= set(i for i in range(1, n) if rs[i] > 12.0 and rs[i] > 4.0 * max(rs[i - 1], rs[i + 1] if i < n - 1 else 0.0))
    stops = cuts | set(c - 1 for c in cuts)
    j['cuts'] = sorted(f0 + c for c in cuts)
    eps9 = (0.002, 0.002, 0.002, 2e-4, 2e-4, 2e-4, 1e-6, 1e-6, 1e-6)
    def xform(b, cols):
        tr = b.add_track(unreal.MovieScene3DTransformTrack); sec = tr.add_section(); sec.set_range(s0, f1 + 1); ch = sec.get_all_channels()
        cu = cuts | _jumps(cols, n)[0]; sp = cu | set(c - 1 for c in cu); k2 = 0
        for k in range(9):
            col = cols[k]
            if 3 <= k <= 5: col = _unwrap(col)
            k2 += _keys(ch[k], f0, col, eps9[k], cu, sp)
        return k2
    def ftrack(b, typ, pname, ppath, cols):
        cls = {'float': unreal.MovieSceneFloatTrack, 'color': unreal.MovieSceneColorTrack, 'vec4': unreal.MovieSceneDoubleVectorTrack}[typ]
        tr = b.add_track(cls); tr.set_property_name_and_path(pname, ppath)
        if typ == 'vec4': tr.set_num_channels_used(4)
        sec = tr.add_section(); sec.set_range(s0, f1 + 1); ch = sec.get_all_channels(); k2 = 0
        for k in range(min(len(cols), len(ch))):
            col = cols[k]; k2 += _keys(ch[k], f0, col, max(1e-9, 1e-6 * (max(col) - min(col))), cuts, stops)
        return k2
    for lb, a in j['tr']:
        nk += xform(bind(a), d['T|' + lb]); ntr += 1
        yield 'transform ' + lb
    for lb, a in j['vi']:
        col = d['V|' + lb][0]
        tr = bind(a).add_track(unreal.MovieSceneVisibilityTrack); tr.set_property_name_and_path('bHidden', 'bHidden')
        sec = tr.add_section(); sec.set_range(s0, f1 + 1); ch = sec.get_all_channels()[0]
        for i in range(n):
            if i == 0 or col[i] != col[i - 1]: ch.add_key(unreal.FrameNumber(f0 + i), col[i] < 0.5); nk += 1
    yield 'visibility'
    # a value that never changes still gets its one key: the level may have been saved with something else in it
    for key, kind, a, c, typ, pname, ppath, rd in j['props']:
        try:
            nk += ftrack(bind(a) if kind == 'actor' else cbind(a, c), typ, pname, ppath, d['P|' + key])
        except Exception as e:
            notes.append('%s: %s' % (key, e))
        yield 'property ' + key
    # the twin camera: the same motion and lens
    camA = s1u.find(CAM); camB = s1u.find(CAM_B)
    if camB is not None and cam:
        try:
            nk += xform(bind(camB), cam)
            nk += ftrack(cbind(camB, camB.get_cine_camera_component()), 'float', 'CurrentFocalLength', 'CurrentFocalLength', d['P|%s.Focal' % CAM])
        except Exception as e:
            notes.append('twin camera: %s' % e)
    yield 'twin camera'

    def interp(i): return CONST if (i + 1) in cuts else LIN
    def pkeys(sec, pname, cols, comp):
        """keys of one material parameter (scalar: one column, colour: four) in a parameter section"""
        k2 = 0
        if len(cols) == 1:
            col = cols[0]
            for i in _pick(col, max(1e-9, 1e-6 * (max(col) - min(col))), stops):
                if comp: sec.add_scalar_parameter_key(unreal.MaterialParameterInfo(name=pname), ptime(i), float(col[i]), '', '', interp(i))
                else: sec.add_scalar_parameter_key(pname, ptime(i), float(col[i]), interp(i))
                k2 += 1
        else:
            idx = set()
            for col in cols: idx |= set(_pick(col, max(1e-9, 1e-6 * (max(col) - min(col))), stops))
            for i in sorted(idx):
                v = unreal.LinearColor(cols[0][i], cols[1][i], cols[2][i], cols[3][i])
                if comp: sec.add_color_parameter_key(unreal.MaterialParameterInfo(name=pname), ptime(i), v, '', '', default_interpolation=interp(i))
                else: sec.add_color_parameter_key(pname, ptime(i), v, interp(i))
                k2 += 1
        return k2
    # the material parameter collections: one track each
    for m in j['mpcs']:
        try:
            tr = seq.add_track(unreal.MovieSceneMaterialParameterCollectionTrack); tr.set_editor_property('mpc', m)
            sec = tr.add_section(); sec.set_range(s0, f1 + 1)
            for mm, pn in j['sc'] + j['ve']:
                if mm != m: continue
                key = ('S|%s|%s' if (mm, pn) in j['sc'] else 'C|%s|%s') % (m.get_name(), pn)
                nk += pkeys(sec, pn, d[key], False)
                yield 'collection %s %s' % (m.get_name(), pn)
        except Exception as e:
            notes.append('collection track %s: %s' % (m.get_name(), e))
    # materials on meshes
    for lb, a, c, slot, mi, sc, ve in j['mats']:
        try:
            tr = cbind(a, c).add_track(unreal.MovieSceneComponentMaterialTrack)
            info = unreal.ComponentMaterialInfo(); info.set_editor_property('material_slot_index', slot)
            info.set_editor_property('material_type', unreal.ComponentMaterialType.INDEXED_MATERIAL)
            sn = c.get_material_slot_names()
            if slot < len(sn): info.set_editor_property('material_slot_name', sn[slot])
            tr.set_material_info(info)
            sec = tr.add_section(); sec.set_range(s0, f1 + 1)
            for pn in sc + ve: nk += pkeys(sec, pn, d['M|%s|%s' % (lb, pn)], True)
        except Exception as e:
            notes.append('material track %s: %s' % (lb, e))
        yield 'material ' + lb
    # the cockpit screens: one material per picture, the track switches the material of the screen
    try:
        import s5_screens as S
        if not S._S.get('states'): S.load()
        made = 0
        for idx in range(1, 6):
            a = s1u.find('ck_screen_%d' % idx)
            if a is None or not S._S.get('states'): continue
            c = a.get_component_by_class(unreal.StaticMeshComponent); prev = None; keys = []
            for i in range(n):
                t = (f0 + i) / float(FPS); s = S.state_at(t); alt = s[4]
                tex = s[3].get(idx)
                if alt and alt[0] == idx and S.burst(t): tex = alt[1]
                if tex is None or tex.get_name() == prev: continue
                prev = tex.get_name(); keys.append((i, tex))
            tr = cbind(a, c).add_track(unreal.MovieScenePrimitiveMaterialTrack)
            info = unreal.ComponentMaterialInfo(); info.set_editor_property('material_slot_index', 0)
            info.set_editor_property('material_type', unreal.ComponentMaterialType.INDEXED_MATERIAL)
            sn = c.get_material_slot_names()
            if sn: info.set_editor_property('material_slot_name', sn[0])
            tr.set_material_info(info)
            sec = tr.add_section(); sec.set_range(s0, f1 + 1); ch = sec.get_all_channels()[0]
            for i, tex in keys:
                p = '%s/MI/MI_%d_%s' % (S.DST, idx, tex.get_name()[2:])
                if EAL.does_asset_exist(p): m = EAL.load_asset(p)
                else:
                    m = EAL.duplicate_asset(S.MI % idx, p)
                    for prm in S._S['params']: MEL.set_material_instance_texture_parameter_value(m, prm, tex)
                    MEL.update_material_instance(m); EAL.save_loaded_asset(m); made += 1
                ch.add_key(unreal.FrameNumber(f0 + i), m); nk += 1
            yield 'screen %d' % idx
        notes.append('screen materials made: %d' % made)
    except Exception as e:
        import traceback
        notes.append('screens: %s %s' % (e, traceback.format_exc()[-300:]))
    # the soundtrack (from frame 0) and the console variables
    try:
        snd = EAL.load_asset(SOUND) if EAL.does_asset_exist(SOUND) else None
        if snd is not None:
            tr = seq.add_track(unreal.MovieSceneAudioTrack); sec = tr.add_section(); sec.set_sound(snd)
            sec.set_range(0, max(f1 + 1, 1))
        else: notes.append('no soundtrack asset ' + SOUND)
    except Exception as e:
        notes.append('audio track: %s' % e)
    try:
        tr = seq.add_track(unreal.MovieSceneCVarTrack); sec = tr.add_section(); sec.set_from_string(CVARS); sec.set_range(s0, f1 + 1)
        notes.append('cvars: ' + sec.get_string().replace('\r', '').replace('\n', '; '))
    except Exception as e:
        notes.append('cvar track: %s' % e)
    # black before the first frame, then a straight cut in
    if pre:
        try:
            tr = seq.add_track(unreal.MovieSceneFadeTrack); sec = tr.add_section(); sec.set_range(s0, f1 + 1); ch = sec.get_all_channels()[0]
            ch.add_key(unreal.FrameNumber(s0), 1.0, 0.0, DR, CONST); ch.add_key(unreal.FrameNumber(f0), 0.0, 0.0, DR, CONST)
        except Exception as e:
            notes.append('fade: %s' % e)
    # the view: the film camera and its twin take turns at every cut
    try:
        cut = seq.add_track(unreal.MovieSceneCameraCutTrack)
        bounds = [0] + (sorted(cuts) if camB is not None else []) + [n]
        for k in range(len(bounds) - 1):
            csec = cut.add_section(); csec.set_range((f0 + bounds[k]) if k else s0, f0 + bounds[k + 1])
            cid = unreal.MovieSceneObjectBindingID(); cid.set_editor_property('guid', bind(camA if k % 2 == 0 else camB).get_id()); csec.set_camera_binding_id(cid)
    except Exception as e:
        notes.append('camera cut: %s' % e)
    yield 'saving'
    EAL.save_loaded_asset(seq)
    j['seq'] = seq
    j['msg'] = 'sequence %s: frames %d-%d (playback from %d), %d transform tracks (%s), %d visibility tracks, %d keys, cuts at %s; notes: %s' % (
        full, f0, f1, s0, ntr, ', '.join(lb for lb, a in j['tr'])[:700], len(j['vi']), nk, j['cuts'], notes or 'none')


def progress():
    return {'phase': _J.get('phase'), 'frame': _J.get('f'), 'step': _J.get('wstep'), 'done': _J.get('done'), 'took_s': _J.get('took'), 'msg': _J.get('msg')}


# ---------------------------------------------------------------- one-off preparations of the level

def import_sound():
    """the final mix as a sound asset (plays from the sequence, not positioned in space)"""
    if EAL.does_asset_exist(SOUND): return EAL.load_asset(SOUND)
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', SOUND_FILE); task.set_editor_property('destination_path', SOUND.rsplit('/', 1)[0])
    task.set_editor_property('destination_name', SOUND.rsplit('/', 1)[1]); task.set_editor_property('automated', True)
    task.set_editor_property('replace_existing', True); task.set_editor_property('save', True)
    AT.import_asset_tasks([task])
    return EAL.load_asset(SOUND)


def second_camera():
    """the twin of the film camera (same lens, film back and settings); only the sequence moves it"""
    b = s1u.find(CAM_B)
    if b is None:
        b = s1u.EAS.duplicate_actor(s1u.find(CAM)); b.set_actor_label(CAM_B)
    return b


def player(seq_path, auto=True):
    """the actor that plays the sequence by itself when the level starts in a game"""
    seq = EAL.load_asset(seq_path)
    a = s1u.find('RT_Player')
    if a is None:
        a = s1u.EAS.spawn_actor_from_class(unreal.LevelSequenceActor, unreal.Vector(0, 0, 300), unreal.Rotator(0, 0, 0))
        a.set_actor_label('RT_Player'); a.set_folder_path('Cameras')
    a.set_sequence(seq)
    ps = a.get_editor_property('playback_settings')
    ps.set_editor_property('auto_play', auto); ps.set_editor_property('pause_at_end', True)
    lc = ps.get_editor_property('loop_count'); lc.set_editor_property('value', 0); ps.set_editor_property('loop_count', lc)
    for k in ('disable_movement_input', 'disable_look_at_input', 'hide_player', 'hide_hud'): ps.set_editor_property(k, True)
    a.set_editor_property('playback_settings', ps)
    return a


def prepare_game(name='SEQ_Otliv_RT', auto=True):
    """The last step before the level is saved for a game build. A game shows what is SAVED in the level, so:
      - the level is put into the state of the first frame (one frame may be drawn before the sequence takes over);
      - actors hidden only "in the editor" (the eye icon) get the real flag "hidden in game" - a game ignores the eye;
      - lights and fog that Python switched off through "visible" are made visible with zero strength: the sequence keys
        the strength, it cannot switch a component back on;
      - the player actor plays the sequence from the start of the level.
    After this the level is not in its working state: save, then restart the editor (or run M.install() again)."""
    T.apply_time(0.0)
    hid = []; lit = []
    for a in s1u.EAS.get_all_level_actors():
        lb = a.get_actor_label()
        if a.is_hidden_ed() and not a.get_editor_property('hidden'):
            a.set_actor_hidden_in_game(True); hid.append(lb)
        for c in list(a.get_components_by_class(unreal.LightComponent)) + list(a.get_components_by_class(unreal.SkyLightComponent)):
            if not c.is_visible():
                c.set_intensity(0.0); c.set_visibility(True); lit.append(lb)
        for c in a.get_components_by_class(unreal.ExponentialHeightFogComponent):
            if not c.is_visible():
                c.set_fog_density(0.0); c.set_visibility(True); lit.append(lb)
    player(PATH + '/' + name, auto)
    return {'hidden_in_game_now': hid, 'made_visible_with_zero': lit}
