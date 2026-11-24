# dkit.py — общее для моделей этапа D (дрон «Светляк», обломки зонда): атлас 2048, выгрузка треугольников для
# художника текстур (tools/d_tex.py рисует износ, соль, «ватерлинии» и надписи по 3D-координатам — без швов на стыках
# развёртки), раскладка и сохранение. Подключать после kit.py, uvkit.py, partkit.py.
import numpy as np

ATLAS = 2048
PAD = 6


def dump_tris(objs, cls_of, path):
    """Треугольники объектов: uv (пиксели атласа), вершины в осях объекта, нормали мира (с учётом острых рёбер),
    класс поверхности, номер объекта; матрицы объектов в мире и их имена. Стекло и свечение (класс ≥ 60) — без текстуры."""
    bpy.context.view_layer.update()
    uv, lp, wn, cl, oi, names, mats = [], [], [], [], [], [], []
    for k, o in enumerate(objs):
        me = o.data
        me.calc_loop_triangles()
        L = me.uv_layers.active.data
        cn = me.corner_normals
        mw = o.matrix_world
        nm = mw.to_3x3().inverted().transposed()
        names.append(o.name)
        mats.append([list(r) for r in mw])
        mnames = [m.name if m else '' for m in me.materials]
        for t in me.loop_triangles:
            c = cls_of.get(mnames[t.material_index] if mnames else '', 0)
            if c >= 60:
                continue
            for li in t.loops:
                u = L[li].uv
                uv.append((u[0] * ATLAS, (1.0 - u[1]) * ATLAS))
                lp.append(tuple(me.vertices[me.loops[li].vertex_index].co))
                wn.append(tuple((nm @ cn[li].vector).normalized()))
            cl.append(c)
            oi.append(k)
    np.savez_compressed(path, uv=np.array(uv, np.float32).reshape(-1, 3, 2), lp=np.array(lp, np.float32).reshape(-1, 3, 3),
                        wn=np.array(wn, np.float32).reshape(-1, 3, 3), cls=np.array(cl, np.uint8), obj=np.array(oi, np.uint16),
                        mats=np.array(mats, np.float32), names=np.array(names))
    return len(cl)


def finish_model(ID, EXP, objs, CLS, extra=None):
    """Раскладка карт по атласам 2048 (атлас — из chart объекта: 'A', 'M' …), выгрузка треугольников каждого атласа
    в tris_<атлас>.npz и layout.json, сохранение src/<ID>.blend."""
    ats = sorted({json.loads(o['chart'])['atlas'] for o in objs if o.get('chart')})
    rects, lays, cnt = {}, {}, 0
    for at in ats:
        r, c = pack_atlas(objs, at)
        rects.update(r)
        lays[at] = layout_of(r, c)
    apply_atlas(objs, rects)
    for at in ats:
        sel = [o for o in objs if (o.get('chart_of') or o.name) in lays[at]]
        cnt += dump_tris(sel, CLS, os.path.join(EXP, 'tris_%s.npz' % at))
    old = os.path.join(EXP, 'tris.npz')
    if os.path.exists(old):
        os.remove(old)
    lay = dict(atlas=ATLAS, classes={str(v): k for k, v in CLS.items()}, charts=lays.get('A', {}), atlases=lays,
               objects=[o.name for o in objs], **(extra or {}))
    json.dump(lay, open(os.path.join(EXP, 'layout.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    tr = sum(tris(o) for o in objs)
    for at in ats:
        sc = sorted(c['scale'] * c.get('dens', 1.0) for c in lays[at].values())
        print('атлас %s: %d карт, плотность %.0f…%.0f пикс/м' % (at, len(lays[at]), sc[0], sc[-1]))
    print('ТРЕУГОЛЬНИКОВ %d, объектов %d; треугольников в атласах %d' % (tr, len(objs), cnt))
    for lib in list(bpy.data.libraries):
        bpy.data.libraries.remove(lib)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(EXP).replace('export', 'src'), ID + '.blend'))
    print('SAVED %s.blend' % ID)
    return tr


def marker(name, loc, d=None, parent=None, size=0.03):
    """Метка-пустышка: ось +Y метки смотрит вдоль d (направление луча, струи, взгляда)."""
    e = empty(name, loc, size=size)
    if d is not None:
        e.rotation_euler = Vector(d).normalized().to_track_quat('Y', 'Z').to_euler()
    if parent is not None:
        set_parent(e, parent)
    return e
