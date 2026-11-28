# S8: where the game gets heavy. In PIE the scene is paused at each given second and the frame time is averaged over
# a number of frames (the laptop is GPU-bound, so this is mostly the GPU cost of that moment). Optionally ProfileGPU at
# chosen seconds (the pass breakdown goes to Saved/Logs/Scenes.log).
#   import s8_perf as P; P.run([360, 400, 430, 440, 450, 458, 500, 505, 510]); ... P.st()
import unreal, time
import rt_check as C

_S = {}


def run(seconds, settle_s=6.0, n=12, profile=()):
    st = {'q': list(seconds), 'phase': 'jump', 't': 0.0, 's': None, 'dts': [], 'res': [], 'done': False}
    def tick(dt):
        try:
            now = time.time()
            if st['phase'] == 'jump':
                if not st['q']:
                    unreal.unregister_slate_post_tick_callback(st['h']); st['done'] = True; return
                st['s'] = st['q'].pop(0); p = C.player(); C.jump(int(st['s'] * 24)); p.pause()
                st['t'] = now; st['phase'] = 'settle'
            elif st['phase'] == 'settle' and now - st['t'] >= settle_s:
                st['dts'] = []; st['phase'] = 'measure'
                if st['s'] in profile:
                    unreal.SystemLibrary.execute_console_command(C.gw(), 'ProfileGPU')
            elif st['phase'] == 'measure':
                st['dts'].append(dt)
                if len(st['dts']) >= n:
                    d = sorted(st['dts'][2:]); st['res'].append((st['s'], round(1000 * sum(d) / len(d)), round(1000 * d[-1])))
                    st['phase'] = 'jump'
        except Exception:
            import traceback
            unreal.unregister_slate_post_tick_callback(st['h']); st['res'].append(traceback.format_exc()); st['done'] = True
    st['h'] = unreal.register_slate_post_tick_callback(tick); _S['run'] = st
    return 'started'


def shots(seconds, outdir, prefix, settle_s=10.0, after_s=4.0, w=960, h=540):
    """jump to each second, pause, let the picture settle, shoot <prefix><mm_ss>.png"""
    import os
    st = {'q': list(seconds), 'phase': 'jump', 't': 0.0, 's': None, 'res': [], 'done': False}
    def tick(dt):
        try:
            now = time.time()
            if st['phase'] == 'jump':
                if not st['q']:
                    unreal.unregister_slate_post_tick_callback(st['h']); st['done'] = True; return
                st['s'] = st['q'].pop(0); p = C.player(); C.jump(int(st['s'] * 24)); p.pause(); st['t'] = now; st['phase'] = 'settle'
            elif st['phase'] == 'settle' and now - st['t'] >= settle_s:
                s = st['s']; f = os.path.join(outdir, '%s%d_%02d.png' % (prefix, int(s) // 60, int(s) % 60))
                C.shot(f, w, h); st['res'].append(f); st['t'] = now; st['phase'] = 'after'
            elif st['phase'] == 'after' and now - st['t'] >= after_s:
                st['phase'] = 'jump'
        except Exception:
            import traceback
            unreal.unregister_slate_post_tick_callback(st['h']); st['res'].append(traceback.format_exc()); st['done'] = True
    st['h'] = unreal.register_slate_post_tick_callback(tick); _S['run'] = st
    return 'started'


def st():
    s = _S.get('run', {})
    return s.get('done'), s.get('res')
