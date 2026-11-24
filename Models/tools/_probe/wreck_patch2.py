# правка: обломки — главный блок в отдельный атлас M (второй набор 2048), заметные пояса соли с кристаллами
import os
T = r'C:\UnrealScenes\Models\tools'


def patch(name, pairs):
    p = os.path.join(T, name)
    s = open(p, encoding='utf-8').read()
    for a, b in pairs:
        assert a in s, (name, a[:70])
        s = s.replace(a, b)
    open(p, 'w', encoding='utf-8').write(s)
    print('ok', name)


patch('probe_wreck.py', [
    ("DECALS, SOLAR, OFFS = [], {}, {}\n", "DECALS, SOLAR, OFFS = [], {}, {}\nFRONT = []                                  # детали грани с нишей — им плотность текстуры выше\n"),
    ("def piece(parts, name, origin, dens=0.3, angle=55.0):", "def piece(parts, name, origin, dens=0.3, angle=55.0, atlas='A'):"),
    ("    smart_uv(ob, 'A', angle=angle, dens=dens)\n", "    smart_uv(ob, atlas, angle=angle, dens=dens)\n"),
    ("            p += place(p_panel(w), M)\n            bp, cy = bay_parts()\n            p += place(bp, M)\n",
     "            fr = place(p_panel(w), M)\n            bp, cy = bay_parts()\n            fr += place(bp, M)\n            FRONT.extend(fr)\n            p += fr\n"),
    ("    bus = piece([o for o in bp_all if o not in hid], 'wr_bus', (0, 0, 0), dens=1.0, angle=50.0)\n",
     "    front = [o for o in bp_all if o in FRONT and o not in hid]\n"
     "    # главный блок — в своём атласе M (второй набор 2048): камера работает в 1–2 м от ниши\n"
     "    bus = piece([o for o in bp_all if o not in hid and o not in front], 'wr_bus', (0, 0, 0), dens=1.0, angle=50.0, atlas='M')\n"
     "    busf = piece(front, 'wr_bus_front', (0, 0, 0), dens=2.2, angle=50.0, atlas='M')     # при экспорте вливается в wr_bus\n"
     "    set_parent(busf, bus)\n"),
    ("    cover = piece(place(access_cover(), MP), 'wr_panel', tuple(cov_c), dens=3.5)\n",
     "    cover = piece(place(access_cover(), MP), 'wr_panel', tuple(cov_c), dens=2.2, atlas='M')\n"),
    ("    stor = piece(place(storage_parts(cy), MP), 'wr_storage', tuple(st_c), dens=3.5)\n",
     "    stor = piece(place(storage_parts(cy), MP), 'wr_storage', tuple(st_c), dens=2.2, atlas='M')\n"),
    ("    return [bus, inner, cover, stor] + pieces\n", "    return [bus, busf, inner, cover, stor] + pieces\n"),
    ("extra=dict(bbox=[lo, hi], water=WATER,", "extra=dict(tex=dict(A='T_ProbeWreck', M='T_ProbeWreckMain'), bbox=[lo, hi], water=WATER,"),
])

p = os.path.join(T, 'd_tex_wreck.py')
s = open(p, encoding='utf-8').read()
a = s.index("    # ---- соль\n")
b = s.index("    pud = np.clip(wn[:, 2], 0, 1) ** 2 * below")
s = s[:a] + """    # ---- соль: налёт ниже верхней линии; у каждой «ватерлинии» — тёмная минеральная полоса, под ней светлая корка
    # разной ширины, потёки вниз и местами друзы кристаллов. Пояса должны читаться с 10 м.
    wob = (vnoise(wp * np.array((1, 1, 0), np.float32), 3, 31, 2) - 0.5) * 0.03
    zz = z + wob
    top_line = max(WLINES)
    below = sstep(top_line + 0.04, top_line - 0.02, zz) * ~clean
    salt = np.array((0.88, 0.86, 0.80), np.float32)                       # соль — бежево-белая, матовая
    film = below * (0.35 + 0.65 * nm) * (1 - 0.7 * cls_mask(g, 'w_inner'))
    base += (np.array((0.76, 0.74, 0.68), np.float32) - base) * (0.40 * film)[:, None]   # ниже верхней линии — тусклее
    rough += 0.25 * film
    metal *= (1 - 0.6 * film)
    flat = np.array((1, 1, 0), np.float32)
    nf2 = vnoise(wp, 260, 41, 2)
    nl = vnoise(wp * flat, 18, 43, 2)                                     # разрывы поясов вдоль линии
    nw = vnoise(wp * flat, 9, 44, 2)                                      # ширина корки гуляет
    drip = vnoise(wp * np.array((1, 1, 0.05), np.float32), 45, 45, 2)     # вертикальные потёки
    ncr = vnoise(wp, 60, 46, 2)                                           # где сидят друзы кристаллов
    grain = vnoise(wp, 1100, 47, 1)
    lines = list(zip(sorted(WLINES, reverse=True), (0.070, 0.100, 0.125))) + [(WATER_ + 0.012, 0.035)]
    for zk, wd in lines:
        dz = zz - zk
        keep = (0.72 + 0.28 * sstep(0.28, 0.50, nl)) * ~clean
        wloc = wd * (0.65 + 0.70 * nw)
        stain = sstep(0.003, -0.002, dz) * sstep(-0.030, -0.018, dz) * keep
        crust = sstep(-0.014, -0.022, dz) * sstep(-wloc - 0.02, -wloc + 0.01, dz) * keep * (0.62 + 0.38 * sstep(0.30, 0.60, nf2))
        runs = sstep(-wloc + 0.02, -wloc - 0.01, dz) * sstep(-wloc - 0.22, -wloc - 0.04, dz) * sstep(0.56, 0.72, drip) * keep * 0.55
        grime = sstep(0.0, -0.010, dz) * sstep(-wloc - 0.20, -wloc, dz) * keep * 0.8
        cryst = sstep(0.60, 0.70, ncr) * sstep(0.012, -0.004, dz) * sstep(-wloc - 0.05, -wloc + 0.02, dz) * ~clean
        base *= (1 - 0.18 * grime)[:, None]
        base += (np.array((0.50, 0.44, 0.36), np.float32) - base) * (0.12 * grime)[:, None]
        sa = np.clip(0.95 * crust + runs, 0, 1)
        base += (salt - base) * sa[:, None]
        base += (np.array((0.25, 0.22, 0.17), np.float32) - base) * (0.90 * stain)[:, None]
        base += (np.array((0.95, 0.94, 0.91), np.float32) - base) * (cryst * (0.55 + 0.45 * grain))[:, None]
        rough = np.maximum(rough, 0.90 * crust)
        rough = np.where(cryst > 0.5, 0.30 + 0.50 * grain, rough)
        metal *= (1 - sa) * (1 - stain) * (1 - cryst)
        H += 0.0022 * crust * nf2 - 0.0002 * stain + 0.0045 * cryst * (0.3 + 0.7 * grain) + 0.0008 * runs
""" + s[b:]
open(p, 'w', encoding='utf-8').write(s)
print('ok d_tex_wreck.py')

patch('d_final.py', [
    ("        set_notes={'A': 'главный блок (кроме грани с нишей) и все остальные куски',\n"
     "                   'M': 'крупный план: грань с нишей (wr_bus_front), крышка wr_panel, накопитель wr_storage'},",
     "        set_notes={'A': 'все куски, кроме главного блока (и скрытые детали wr_bus_inner)',\n"
     "                   'M': 'НОВЫЙ слот (второй набор 2048): главный блок wr_bus, крышка wr_panel, накопитель wr_storage; грань с нишей, крышка и накопитель — около 1000 пикс/м'},\n"
     "        join={'wr_bus': ['wr_bus_front']},"),
    ("    for m in list(bpy.data.materials):\n        if m.users == 0:\n            bpy.data.materials.remove(m)\n    for m in bpy.data.materials:\n        if m.name.endswith('_x'):",
     "    for tgt, srcs in cfg.get('join', {}).items():                 # детали, разделённые только ради плотности текстуры\n"
     "        t = bpy.data.objects[tgt]\n"
     "        ss = [bpy.data.objects[n] for n in srcs if n in bpy.data.objects]\n"
     "        if ss:\n"
     "            with bpy.context.temp_override(active_object=t, object=t, selected_objects=[t] + ss, selected_editable_objects=[t] + ss):\n"
     "                bpy.ops.object.join()\n"
     "    objs = [o for o in bpy.data.collections[ID].all_objects if o.type == 'MESH']\n"
     "    for m in list(bpy.data.materials):\n        if m.users == 0:\n            bpy.data.materials.remove(m)\n    for m in bpy.data.materials:\n        if m.name.endswith('_x'):"),
])
