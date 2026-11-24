# d_bake.py — запечь затенение (AO) атласов модели этапа D в открытом Blender; задания идут в фоне, окно не блокируется:
#   bash tools/live.sh @code "BAKE_ID='svetlyak'; BAKE_SEPARATE=['sv_head']; exec(open(r'C:\UnrealScenes\Models\tools\d_bake.py', encoding='utf-8').read())" 60
# По проходу на каждый атлас модели (атлас — из свойства chart объекта). BAKE_SEPARATE — детали, которые в первом проходе
# не затеняют остальные (подвижная голова и т. п.), а сами запекаются вторым проходом в тот же атлас.
# Результат — export/<id>/_ao_<атлас>.png (линейный, 2048); готовность — файл shots/_tmp/bake_done.txt.
import bpy, os, time, json

_EXP = os.path.join(r'C:\UnrealScenes\Models\export', BAKE_ID)
_done = r'C:\UnrealScenes\Models\shots\_tmp\bake_done.txt'
if os.path.exists(_done):
    os.remove(_done)
_sc = bpy.context.scene
_sc.render.engine = 'CYCLES'
_sc.cycles.device = 'CPU'
_sc.cycles.samples = globals().get('BAKE_SAMPLES', 32)
_sz = globals().get('BAKE_SIZE', 2048)
_objs = [o for o in bpy.data.collections[BAKE_ID].all_objects if o.type == 'MESH']
_sep = set(globals().get('BAKE_SEPARATE', []))
_by = {}
for _o in _objs:
    _by.setdefault(json.loads(_o['chart'])['atlas'] if _o.get('chart') else 'A', []).append(_o)
_imgs, _nodes, _jobs = {}, {}, []
for _at, _lst in sorted(_by.items()):
    _im = bpy.data.images.get('_ao_' + _at)
    if _im is None or tuple(_im.size) != (_sz, _sz):
        _im = bpy.data.images.new('_ao_' + _at, _sz, _sz, alpha=False)
    _im.colorspace_settings.name = 'Non-Color'
    _imgs[_at] = _im
    _first = [o for o in _lst if o.name not in _sep]
    _second = [o for o in _lst if o.name in _sep]
    if _first:
        _jobs.append(dict(at=_at, objs=_first, hide=[o for o in _objs if o.name in _sep], clear=True, margin=6))
    if _second:
        _jobs.append(dict(at=_at, objs=_second, hide=[], clear=not _first, margin=2))
for _m in {m for o in _objs for m in o.data.materials if m}:
    _m.use_nodes = True
    for _at, _im in _imgs.items():
        _n = _m.node_tree.nodes.new('ShaderNodeTexImage')
        _n.image = _im
        _nodes[(_m.name, _at)] = _n
_st = {'i': -1, 'baking': False, 't0': time.time()}


def _start(job):
    for o in _objs:
        o.hide_render = o in job['hide']
    for m in {m for o in job['objs'] for m in o.data.materials if m}:
        m.node_tree.nodes.active = _nodes[(m.name, job['at'])]
    bpy.ops.object.select_all(action='DESELECT')
    for o in job['objs']:
        o.select_set(True)
    bpy.context.view_layer.objects.active = job['objs'][0]
    if bpy.app.background:
        bpy.ops.object.bake(type='AO', use_clear=job['clear'], margin=job['margin'])
        return
    w = bpy.context.window_manager.windows[0]
    with bpy.context.temp_override(window=w, screen=w.screen, view_layer=bpy.context.view_layer,
                                   active_object=job['objs'][0], selected_objects=job['objs']):
        bpy.ops.object.bake('INVOKE_DEFAULT', type='AO', use_clear=job['clear'], margin=job['margin'])


def _bake_tick():
    if bpy.app.is_job_running('OBJECT_BAKE'):
        return 2.0
    _st['i'] += 1
    if _st['i'] < len(_jobs):
        _start(_jobs[_st['i']])
        return 2.0
    for at, im in _imgs.items():
        im.filepath_raw = os.path.join(_EXP, '_ao_%s.png' % at)
        im.file_format = 'PNG'
        im.save()
    for (mn, at), n in _nodes.items():
        m = bpy.data.materials.get(mn)
        if m:
            m.node_tree.nodes.remove(n)
    for o in _objs:
        o.hide_render = False
    open(_done, 'w', encoding='utf-8').write('done %.0f s, проходов %d' % (time.time() - _st['t0'], len(_jobs)))
    return None


if bpy.app.background:
    while _bake_tick() is not None:
        pass
else:
    bpy.app.timers.register(_bake_tick, first_interval=0.5)
print('запекание AO запущено: атласы', sorted(_imgs), 'проходов', len(_jobs))
