#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="/storage/emulated/0/Download/TornadoAI"
ALERTDIR="$ROOT/alerts"
OUTDIR="$ROOT/reports/alerts"
mkdir -p "$OUTDIR"

WEEK="$(date +%G-%V)"     # ISO year-week, e.g. 2025-38
OUT="$OUTDIR/alerts_$WEEK.tar.gz"

# If nothing to archive, exit quietly
have_any=0
for f in "$ALERTDIR"/alerts*.jsonl "$ALERTDIR"/alerts*.log "$ALERTDIR"/alerts_case*.log; do
  [ -e "$f" ] && have_any=1 && break
done
[ "$have_any" -eq 0 ] && { echo "[alerts_zip] no alerts to archive"; exit 0; }

# Create tar.gz (portable; busybox tar works too)
cd "$ROOT"
tar -czf "$OUT" alerts/alerts*.jsonl alerts/alerts*.log alerts/alerts_case*.log 2>/dev/null || true

echo "[alerts_zip] wrote $OUT"
