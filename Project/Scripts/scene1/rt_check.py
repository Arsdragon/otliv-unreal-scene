# Real-time version: does the baked sequence give the same scene as the Python timeline?
# Runs the level as a game inside the editor (PIE), jumps the sequence to a frame and compares what the GAME world holds
# with what the bake recorded from the timeline for that frame: transforms, visibility, lights, fog, post-process,
# both parameter collections, material parameters on meshes, pictures of the screens, the camera in use.
# Needs the bake of this editor session (rt_bake._J) and rt_bake.prepare_game(name, auto=False) before pie_start().
#   import rt_check as C; C.pie_start() ... C.jump(f) ... C.compare(f) ... C.shot(path) ... C.pie_stop()
import math, unreal
import s1u, rt_bake as B

UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
ML = unreal.MaterialLibrary
_G = {}


def gw(): return UES.get_game_world()


def pie_start():
    _G.clear(); s1u.LES.editor_request_begin_play()


def pie_stop():
    _G.clear(); s1u.LES.editor_request_end_play()


def actors():
    if 'by' not in _G:
        _G['by'] = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(gw(), unreal.Actor) if a.get_actor_label()}
    return _G['by']


def player():
    a = unreal.GameplayStatics.get_all_actors_of_class(gw(), unreal.LevelSequenceActor)
    return a[0].sequence_player if a else None


def jump(f):
    p = player()
    p.set_playback_position(unreal.MovieSceneSequencePlaybackParams(frame=unreal.FrameTime(unreal.FrameNumber(int(f))),
                                                                    position_type=unreal.MovieScenePositionType.FRAME, update_method=unreal.UpdatePositionMethod.JUMP))
    return p.get_current_time().time.frame_number.value


def shot(path, w=960, h=540):
    unreal.AutomationLibrary.take_high_res_screenshot(w, h, path)


def view():
    pc = unreal.GameplayStatics.get_player_controller(gw(), 0)
    vt = pc.get_view_target() if pc else None
    return vt.get_actor_label() if vt else None


def run(frames, outdir, settle_s=8.0, after_s=6.0, prefix='pie_'):
    """for every frame: jump, let the picture settle, compare with the recording, shoot; results in results()"""
    import time, os
    st = {'q': list(frames), 'phase': 'jump', 't': 0.0, 'f': None, 'res': [], 'done': False}
    def tick(dt):
        try:
            now = time.time()
            if st['phase'] == 'jump':
                if not st['q']:
                    unreal.unregister_slate_post_tick_callback(st['h']); st['done'] = True; return
                st['f'] = st['q'].pop(0); jump(st['f']); st['t'] = now; st['phase'] = 'settle'
            elif st['phase'] == 'settle' and now - st['t'] >= settle_s:
                r = compare(st['f']); r['view'] = view(); st['res'].append(r)
                shot(os.path.join(outdir, '%s%04d.png' % (prefix, int(round(st['f'] / 2.4))))); st['t'] = now; st['phase'] = 'after'
            elif st['phase'] == 'after' and now - st['t'] >= after_s:
                st['phase'] = 'jump'
        except Exception as e:
            import traceback
            unreal.unregister_slate_post_tick_callback(st['h']); st['res'].append({'error': traceback.format_exc()}); st['done'] = True
    st['h'] = unreal.register_slate_post_tick_callback(tick); _G['run'] = st
    return 'started'


def results():
    st = _G.get('run') or {}
    return {'done': st.get('done'), 'left': len(st.get('q', [])), 'res': st.get('res')}


def _near(a, b, tol):
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def compare(f, tol=2e-3):
    """mismatches between the game world (after jump(f)) and the recorded frame f; an empty list = the same"""
    j = B._J; d = j['data']; i = f - j['f0']; by = actors(); w = gw(); bad = []; n = 0
    for lb, a in j['tr']:
        g = by.get(lb)
        if g is None: bad.append(('no actor', lb)); continue
        got = B._rel(g); want = [c[i] for c in d['T|' + lb]]
        for k in range(9):
            n += 1
            if 3 <= k <= 5:
                if abs((got[k] - want[k] + 180.0) % 360.0 - 180.0) > 0.02: bad.append(('rot', lb, k, round(got[k], 3), round(want[k], 3)))
            elif not _near(got[k], want[k], tol): bad.append(('xform', lb, k, round(got[k], 3), round(want[k], 3)))
    for lb, a in j['vi']:
        g = by.get(lb); n += 1
        if g is None: bad.append(('no actor', lb)); continue
        if bool(g.get_editor_property('hidden')) != (d['V|' + lb][0][i] > 0.5): bad.append(('hidden', lb, bool(g.get_editor_property('hidden'))))
    ga = [by[a.get_actor_label()] for a in j['actors'] if a.get_actor_label() in by]
    for p in B._props(ga):
        cols = d.get('P|' + p[0])
        if cols is None: continue
        got = p[7](); want = [c[i] for c in cols]
        for k in range(len(want)):
            n += 1
            if not _near(got[k], want[k], tol): bad.append(('prop', p[0], k, round(got[k], 4), round(want[k], 4)))
    for m, pn in j['sc']:
        n += 1; got = ML.get_scalar_parameter_value(w, m, pn); want = d['S|%s|%s' % (m.get_name(), pn)][0][i]
        if not _near(got, want, tol): bad.append(('mpc', str(pn), round(got, 4), round(want, 4)))
    for m, pn in j['ve']:
        got = ML.get_vector_parameter_value(w, m, pn).to_tuple(); want = [c[i] for c in d['C|%s|%s' % (m.get_name(), pn)]]
        for k in range(4):
            n += 1
            if not _near(got[k], want[k], tol): bad.append(('mpc', str(pn), k, round(got[k], 4), round(want[k], 4)))
    for lb, a, c, slot, mi, sc, ve in j['mats']:
        g = by.get(lb)
        if g is None: bad.append(('no actor', lb)); continue
        mat = g.get_component_by_class(unreal.StaticMeshComponent).get_material(slot)
        if not isinstance(mat, unreal.MaterialInstanceDynamic): bad.append(('not a dynamic material', lb, mat.get_name() if mat else None)); continue
        for pn in sc:
            n += 1; got = mat.get_scalar_parameter_value(pn); want = d['M|%s|%s' % (lb, pn)][0][i]
            if not _near(got, want, tol): bad.append(('mat', lb, pn, round(got, 4), round(want, 4)))
        for pn in ve:
            got = mat.get_vector_parameter_value(pn).to_tuple(); want = [c2[i] for c2 in d['M|%s|%s' % (lb, pn)]]
            for k in range(4):
                n += 1
                if not _near(got[k], want[k], tol): bad.append(('mat', lb, pn, k, round(got[k], 4), round(want[k], 4)))
    # screens
    import s5_screens as S
    t = f / float(B.FPS); s = S.state_at(t); alt = s[4]
    for idx in range(1, 6):
        tex = s[3].get(idx)
        if alt and alt[0] == idx and S.burst(t): tex = alt[1]
        g = by.get('ck_screen_%d' % idx)
        if g is None or tex is None: continue
        n += 1; mat = g.get_component_by_class(unreal.StaticMeshComponent).get_material(0); want = 'MI_%d_%s' % (idx, tex.get_name()[2:])
        if mat is None or mat.get_name() != want: bad.append(('screen', idx, mat.get_name() if mat else None, want))
    # the camera in use: the film camera and its twin take turns at the cuts
    cuts = [c for c in j.get('cuts', []) if c <= f]; want = B.CAM if len(cuts) % 2 == 0 else B.CAM_B
    n += 1
    if view() != want: bad.append(('view target', view(), want))
    return {'frame': f, 'checked': n, 'bad': bad[:40], 'bad_total': len(bad)}
