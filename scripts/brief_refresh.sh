#!/data/data/com.termux/files/usr/bin/sh
# Rebuild the Daily Brief safely; skip if already running.

ROOT="/storage/emulated/0/Download/TornadoAI"
LOG="$ROOT/harvester.log"
LOCK="$ROOT/.brief.lock"

# simple lock using mkdir (atomic on POSIX)
if mkdir "$LOCK" 2>/dev/null; then
  trap 'rmdir "$LOCK"' EXIT
else
  echo "[brief] $(date '+%F %T') already running, skip." >>"$LOG"
  exit 0
fi

echo "[brief] $(date '+%F %T') rebuild start" >>"$LOG"
python3 "$ROOT/daily_brief.py"        >>"$LOG" 2>&1 || true
python3 "$ROOT/build_brief_page.py"   >>"$LOG" 2>&1 || true
echo "[brief] $(date '+%F %T') rebuild done"  >>"$LOG"
