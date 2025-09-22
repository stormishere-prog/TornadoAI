#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="/storage/emulated/0/Download/TornadoAI"
DB="$ROOT/corpus.db"
BKDIR="$ROOT/backups"
LOG="$ROOT/harvester.log"
mkdir -p "$BKDIR"

ts() { date +%Y%m%d-%H%M%S; }

# quick integrity
if ! sqlite3 -cmd ".timeout 4000" "$DB" "PRAGMA integrity_check;" >/dev/null 2>&1; then
  echo "[db_guard][$(date -Is)] integrity FAIL, snapshotting" >>"$LOG"
fi

# hot snapshot (sqlite3 built-in)
SNAP="$BKDIR/corpus.$(ts).db"
sqlite3 "$DB" ".backup '$SNAP'"

# vacuum into compact copy
VAC="$BKDIR/corpus.$(ts).vacuum.db"
sqlite3 -cmd ".timeout 4000" "$DB" "VACUUM INTO '$VAC';" || true

# rotate: keep last 10 backups
ls -1t "$BKDIR"/corpus.*.db 2>/dev/null | sed -n '11,$p' | xargs -r rm -f

echo "[db_guard][$(date -Is)] backup=$SNAP vacuum=$VAC" >>"$LOG"
