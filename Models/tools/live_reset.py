# live_reset.py — открыть в живом Blender пустой файл и вычистить неиспользуемые данные (освобождает память).
# Выполняется отложенно (таймером), чтобы смена файла не случилась внутри обработчика команды аддона.
# Готовность — файл shots/_tmp/reset_done.txt.
import bpy, os

_done = r'C:\UnrealScenes\Models\shots\_tmp\reset_done.txt'
if os.path.exists(_done):
    os.remove(_done)


def _reset():
    msg = 'ok'
    try:
        w = bpy.context.window_manager.windows[0]
        with bpy.context.temp_override(window=w):
            bpy.ops.wm.read_homefile(use_empty=True)
    except Exception as e:
        msg = 'read_homefile: %s' % e
    try:
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    except Exception as e:
        msg += ' | purge: %s' % e
    open(_done, 'w', encoding='utf-8').write(msg)
    return None


bpy.app.timers.register(_reset, first_interval=0.5)
print('сброс запланирован')
