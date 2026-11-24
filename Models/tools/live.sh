#!/usr/bin/env bash
# Запуск сборочного скрипта в ОТКРЫТОМ Blender (через аддон, порт 9876):  bash tools/live.sh chaika_ext.py [таймаут_с]
#   bash tools/live.sh @reset        — пустой файл (read_homefile) и чистка неиспользуемых данных
#   bash tools/live.sh @code "print(1)"  — выполнить строку кода
cd "$(dirname "$0")/.."
export PYTHONIOENCODING=utf-8
case "$1" in
  @reset) CODE="exec(open(r'C:\UnrealScenes\Models\tools\live_reset.py', encoding='utf-8').read())" ;;
  @code) CODE="$2"; shift ;;
  *) CODE="LIVE_SCRIPT='$1'; exec(open(r'C:\UnrealScenes\Models\tools\live_run.py', encoding='utf-8').read())" ;;
esac
python tools/bmcp.py "$CODE" "${2:-900}" 2>&1 | tail -1 | python -c "
import sys, json
t = sys.stdin.read()
try:
    r = json.loads(t)
    t = (r.get('result') or {}).get('result') if isinstance(r.get('result'), dict) else None
    t = t or r.get('message') or str(r)
except Exception:
    pass
print(t)"
