#!/usr/bin/env bash
# Blender без окна:  bash tools/bl.sh [файл.blend] скрипт.py [-- аргументы]
B="$HOME/AppData/Local/Programs/Blender 3D/blender.exe"
if [[ "$1" == *.blend ]]; then BLEND="$1"; shift; "$B" -b "$BLEND" --python "$@" 2>&1; else "$B" -b --factory-startup --python "$@" 2>&1; fi \
  | grep -vE "^(Read |Fra:|Saved:| Time:|Info:|Color management|Blender quit|$)|DeprecationWarning|use_nodes|CUEW|^[0-9:.]+ +(render|blend|cycles) +\| *(Saved|Sample|Rendering|Loading|Updating|Building|Finished|Initializ|Synchron|Denois|Time|Mem|Peak|Compositing|Reading|Path Tracing|Use |Scene|Start|Waiting|Remaining)"
