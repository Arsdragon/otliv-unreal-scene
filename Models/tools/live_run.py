# live_run.py — выполнить сборочный скрипт в ОТКРЫТОМ окне Blender так, как если бы он был запущен отдельно:
#   python tools/bmcp.py "LIVE_SCRIPT='chaika_ext.py'; exec(open(r'C:\UnrealScenes\Models\tools\live_run.py', encoding='utf-8').read())" 900
# Вывод print() скрипта возвращается в ответе (последние строки).
import bpy, os, io, contextlib, traceback
_f = os.path.join(r'C:\UnrealScenes\Models\tools', LIVE_SCRIPT)
_buf = io.StringIO()
try:
    with contextlib.redirect_stdout(_buf):
        exec(compile(open(_f, encoding='utf-8').read(), _f, 'exec'), {'__name__': '__main__', '__file__': _f})
    _ok = True
except Exception:
    _ok = False
    _buf.write(traceback.format_exc())
print('LIVE_RUN', 'OK' if _ok else 'FAILED', LIVE_SCRIPT)
print('\n'.join(_buf.getvalue().splitlines()[-12:]))
