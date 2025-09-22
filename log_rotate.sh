#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="/storage/emulated/0/Download/TornadoAI"
LOG="$ROOT/harvester.log"
[ -f "$LOG" ] || exit 0
SZ=$(stat -c%s "$LOG" 2>/dev/null || stat -f%z "$LOG")
# rotate if > 5 MB
if [ "${SZ:-0}" -gt $((5*1024*1024)) ]; then
  mv "$LOG" "$LOG.$(date +%Y%m%d-%H%M%S)"
  touch "$LOG"
  # keep latest 7 rotated files
  ls -1t "$LOG".2* 2>/dev/null | sed -n '8,$p' | xargs -r rm -f
fi
