#!/usr/bin/env bash
# Отдельный фоновый Blender (без окна, заводские настройки, аддоны пользователя не грузятся):
#   bash tools/bg.sh "fresh(); run('svetlyak.py'); run('d_bake.py', BAKE_ID='svetlyak', BAKE_SEPARATE=['sv_head'])"
#   bash tools/bg.sh "load('svetlyak.blend'); os.environ['D_ID']='svetlyak'; run('d_final.py')"
# Нужен, когда открытый Blender занят или не принимает команды. Не запускать одновременно с тяжёлым рендером в окне.
cd "$(dirname "$0")/.."
export PYTHONIOENCODING=utf-8
export BG_CODE="$1"
BL="/c/Users/Пользователь/AppData/Local/Programs/Blender 3D/blender.exe"
"$BL" -b --factory-startup --python tools/bg_run.py 2>&1 | grep -v "^$" | grep -v "^Fra:\|^Blender 5\|Saved: \|^ *Time: \| INFO: \|^Sample \|Rendering\|Finished$\|Path Tracing\|Updating \|Loading \|Building \|Waiting for\|Synchronizing\|Initializing\|Finishing\|Denoising\|Copying " | tail -${BG_TAIL:-20}
