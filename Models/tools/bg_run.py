# bg_run.py — выполнить код в ОТДЕЛЬНОМ фоновом Blender (когда открытый Blender недоступен): см. tools/bg.sh.
# Код берётся из переменной окружения BG_CODE. Помощники: run('скрипт.py', ИМЯ=значение…) — выполнить скрипт из tools
# как отдельный запуск (с глобальными переменными); load('файл.blend') — открыть файл из src; fresh() — пустая сцена.
import bpy, os, sys, traceback

TOOLS = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(TOOLS), 'src')


def run(name, **g):
    f = os.path.join(TOOLS, name)
    ns = {'__name__': '__main__', '__file__': f}
    ns.update(g)
    exec(compile(open(f, encoding='utf-8').read(), f, 'exec'), ns)
    return ns


def load(name):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(SRC, name))


def fresh():
    bpy.ops.wm.read_homefile(use_empty=True, use_factory_startup=True)


try:
    exec(compile(os.environ.get('BG_CODE', ''), '<bg>', 'exec'), {'__name__': '__bg__', 'run': run, 'load': load, 'fresh': fresh, 'bpy': bpy, 'os': os})
    print('BG_RUN OK')
except Exception:
    traceback.print_exc()
    print('BG_RUN FAILED')
    sys.stdout.flush()
    os._exit(1)
