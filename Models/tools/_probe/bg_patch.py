# правка: giant_scene.py, d_bake.py, live_shots_d.py умеют работать в фоновом Blender (без окна и таймеров)
import os
T = r'C:\UnrealScenes\Models\tools'


def patch(name, pairs):
    p = os.path.join(T, name)
    s = open(p, encoding='utf-8').read()
    for a, b in pairs:
        assert a in s, (name, a[:60])
        s = s.replace(a, b)
    open(p, 'w', encoding='utf-8').write(s)
    print('ok', name)


patch('giant_scene.py', [
    ("    win = bpy.context.window_manager.windows[0]\n    try:\n        with bpy.context.temp_override(window=win, screen=win.screen):\n            bpy.ops.render.render('INVOKE_DEFAULT', write_still=True)\n",
     "    if bpy.app.background:\n        bpy.ops.render.render(write_still=True)\n        return 0.1\n    win = bpy.context.window_manager.windows[0]\n    try:\n        with bpy.context.temp_override(window=win, screen=win.screen):\n            bpy.ops.render.render('INVOKE_DEFAULT', write_still=True)\n"),
    ("if todo:\n    bpy.app.timers.register(_tick, first_interval=1.0)\n",
     "if todo and bpy.app.background:\n    while todo:\n        _v = todo.pop(0)\n        _t = time.time()\n        _start(_v)\n        log.write('RENDERED %s %.0f s (фон)\\n' % (_v, time.time() - _t))\n        log.flush()\n        print('RENDERED %s %.0f s' % (_v, time.time() - _t))\n    open(done_file, 'w').write('done')\nelif todo:\n    bpy.app.timers.register(_tick, first_interval=1.0)\n"),
    ("if 'gas_giant' not in bpy.data.objects:\n", "if 'gas_giant' not in bpy.data.objects:\n    for _o in list(bpy.data.objects):\n        bpy.data.objects.remove(_o, do_unlink=True)\n"),
])
patch('d_bake.py', [
    ("    w = bpy.context.window_manager.windows[0]\n    with bpy.context.temp_override(window=w,",
     "    if bpy.app.background:\n        bpy.ops.object.bake(type='AO', use_clear=job['clear'], margin=job['margin'])\n        return\n    w = bpy.context.window_manager.windows[0]\n    with bpy.context.temp_override(window=w,"),
    ("bpy.app.timers.register(_bake_tick, first_interval=0.5)\n",
     "if bpy.app.background:\n    while _bake_tick() is not None:\n        pass\nelse:\n    bpy.app.timers.register(_bake_tick, first_interval=0.5)\n"),
])
patch('live_shots_d.py', [
    ("    w = bpy.context.window_manager.windows[0]\n    try:\n        with bpy.context.temp_override(window=w, screen=w.screen):\n            bpy.ops.render.render('INVOKE_DEFAULT', write_still=True)\n",
     "    if bpy.app.background:\n        bpy.ops.render.render(write_still=True)\n        return 0.1\n    w = bpy.context.window_manager.windows[0]\n    try:\n        with bpy.context.temp_override(window=w, screen=w.screen):\n            bpy.ops.render.render('INVOKE_DEFAULT', write_still=True)\n"),
    ("bpy.app.timers.register(_tick, first_interval=1.0)\n",
     "if bpy.app.background:\n    while _tick() is not None:\n        pass\nelse:\n    bpy.app.timers.register(_tick, first_interval=1.0)\n"),
])
