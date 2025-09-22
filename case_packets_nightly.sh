#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="/storage/emulated/0/Download/TornadoAI"
cd "$ROOT" || exit 1

# Find cases with new evidence in last 24h
CASES="$(sqlite3 corpus.db \
  "SELECT DISTINCT case_name
   FROM v_case_bundle
   WHERE case_name IS NOT NULL
     AND case_name <> ''
     AND ts_utc >= strftime('%s','now')-86400
   ORDER BY case_name;")"

[ -z "$CASES" ] && { echo "[case-packets] none to update"; exit 0; }

echo "$CASES" | while IFS= read -r CASE; do
  [ -z "$CASE" ] && continue
  echo "[case-packets] building: $CASE"
  # safe_run will ensure schema + guard/backup
  sh ./safe_run.sh python3 case_packet.py --case "$CASE" --zip || true
done
