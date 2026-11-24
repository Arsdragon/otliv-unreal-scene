#!/usr/bin/env bash
# Этап B целиком:  bash tools/stage_b.sh [build] [tex] [final] [export] [shots <виды…>]
# build — сборка модели и развёрток; tex — рисование текстур; final — материалы (без экспорта);
# export — материалы + glb/fbx/manifest; shots — приёмочные рендеры Cycles (виды из tools/shots_b.py).
cd "$(dirname "$0")/.."
export PYTHONIOENCODING=utf-8
while [ $# -gt 0 ]; do
  case "$1" in
    build) bash tools/bl.sh tools/chaika_ext.py | grep -E "ГАБАРИТЫ|ТРЕУГОЛЬНИКОВ|SAVED|Error|Traceback" ;;
    tex) python tools/chaika_tex.py chaika_ext | grep -E "сохранено|Error|Traceback" ;;
    final) bash tools/bl.sh src/chaika_ext.blend tools/chaika_final.py -- --noexport | grep -E "SAVED|Error|Traceback" ;;
    export) bash tools/bl.sh src/chaika_ext.blend tools/chaika_final.py | grep -E "SAVED|EXPORT|треугольников|Error|Traceback" ;;
    shots) shift; bash tools/bl.sh src/chaika_ext_final.blend tools/shots_b.py -- "$@" | grep -E "RENDERED|TIME|Error|Traceback"; break ;;
  esac
  shift
done
echo STAGE_B_DONE
