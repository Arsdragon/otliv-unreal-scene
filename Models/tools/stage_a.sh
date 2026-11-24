#!/usr/bin/env bash
# Этап A целиком: сборка блок-модели, чистовые кадры (Cycles), план и разрез (Workbench), листы.
cd "$(dirname "$0")/.."
bash tools/bl.sh tools/chaika_block.py | grep -E "ГАБАРИТЫ|днище|SAVED|Error|Traceback"
bash tools/bl.sh src/chaika_blockA.blend tools/shots_a.py -- "$@" | grep -E "RENDERED|TIME|Error|Traceback"
bash tools/bl.sh src/chaika_blockA.blend tools/shots_quick.py -- A plan section | grep -E "RENDERED|Error|Traceback"
python tools/sheet_a.py
echo STAGE_A_DONE
