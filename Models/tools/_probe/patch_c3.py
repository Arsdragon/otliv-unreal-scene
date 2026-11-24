# Разовая правка: имена бортов. Нос по −Y, значит +X — ЛЕВЫЙ борт. Во внешней модели части на +X назывались *_R —
# в конце сборки суффиксы меняются местами, чтобы имена соответствовали настоящим бортам. Заодно — текст манифеста.
import os
T = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rd(n):
    return open(os.path.join(T, n), encoding='utf-8').read()


def wr(n, s):
    open(os.path.join(T, n), 'w', encoding='utf-8').write(s)


def rep(s, a, b):
    assert a in s, a[:70]
    return s.replace(a, b)


s = rd('chaika_ext.py')
s = rep(s, "    json.dump(dict(tris=tr, objects=len(objs), lo=lo, hi=hi), open(os.path.join(EXP, 'build_stats.json'), 'w'))\n",
        """    json.dump(dict(tris=tr, objects=len(objs), lo=lo, hi=hi), open(os.path.join(EXP, 'build_stats.json'), 'w'))
    # Имена бортов: при носе по −Y ось +X — левый борт. Внутри сборки правая (по +X) половина называлась *_R;
    # здесь суффиксы меняются местами, чтобы в файле и в экспорте *_L было слева от пилота, *_R — справа.
    allo = list(bpy.data.collections['chaika_ext'].all_objects)
    new = {o.name: (o.name[:-2] + ('_L' if o.name.endswith('_R') else '_R')) for o in allo if o.name[-2:] in ('_R', '_L')}
    for o in allo:
        if o.get('chart_of') in new:
            o['chart_of'] = new[o['chart_of']]
    for o in allo:
        if o.name in new:
            o['_new'] = new[o.name]
            o.name = '__' + o.name
    for o in allo:
        if o.get('_new'):
            o.name = o['_new']
            del o['_new']
""")
wr('chaika_ext.py', s)

s = rd('chaika_final.py')
s = rep(s, "axes='Z вверх, нос по −Y, правый борт +X (оси Blender); в glb оси пересчитаны экспортёром в Y вверх',",
        "axes='Z вверх, нос по −Y; ВНИМАНИЕ: +X — левый борт, −X — правый (оси Blender). Суффиксы _L / _R в именах — настоящие борта. '\n             'В glb оси пересчитаны экспортёром в Y вверх',")
s = rep(s, "note='люк шлюза: петли слева (если смотреть снаружи), открывается наружу в нишу; открывать при опущенном трапе'),",
        "note='люк шлюза: петли на правом борту (−X), открывается наружу в нишу трапа; открывать при опущенном трапе'),")
wr('chaika_final.py', s)

s = rd('chaika_cockpit_station.py')
s = rep(s, "_pp(a, PANEL_R + 0.155, PZ1 - 0.004), _pp(a, PANEL_R - 0.012, PZ1 + 0.002)] for a in PANEL_AZ],\n                      mat_name='c_bezel', smooth=None))",
        "_pp(a, PANEL_R + 0.155, PZ1 - 0.004), _pp(a, PANEL_R - 0.012, PZ1 + 0.002)] for a in PANEL_AZ],\n                      mat_name='m_rubber', smooth=None))      # козырёк — матовый чёрный, без бликов")
wr('chaika_cockpit_station.py', s)
print('patch_c3 ok')
