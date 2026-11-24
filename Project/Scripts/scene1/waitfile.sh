#!/bin/bash
# waitfile.sh <path> [timeout_s] - waits until the file exists and stops growing
f="$1"; t="${2:-100}"; last=-1
for i in $(seq 1 "$t"); do
  if [ -f "$f" ]; then s=$(stat -c %s "$f"); if [ "$s" -gt 0 ] && [ "$s" = "$last" ]; then echo "ready after ${i}s: $s bytes"; exit 0; fi; last=$s; fi
  ping -n 2 127.0.0.1 > /dev/null
done
echo "timeout: $f"; exit 1
