#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="/storage/emulated/0/Download/TornadoAI"
cd "$ROOT" || exit 1
STAMP="$ROOT/.news_hourly_stamp"
NOW=$(date +%s)

if [ -f "$STAMP" ]; then
  LAST=$(cat "$STAMP" 2>/dev/null || echo 0)
  [ $((NOW - LAST)) -lt 3600 ] && exit 0
fi

sh ./safe_run.sh python3 news_poll.py >> "$ROOT/harvester.log" 2>&1 || true
echo "$NOW" > "$STAMP"
sh ./safe_run.sh python3 url_canon.py >> "$ROOT/harvester.log" 2>&1 || true
sh ./safe_run.sh python3 fetch_x.py >>"$ROOT/harvester.log" 2>&1 || true
