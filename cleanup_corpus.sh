#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="/storage/emulated/0/Download/TornadoAI"
DB="$ROOT/corpus.db"
LOG="$ROOT/harvester.log"

# ---- Defaults (locked) ----
DAYS="${DAYS:-90}"              # age cutoff in days
KEEP_OFFICIAL=1                 # LOCKED: official sources protected by default

# Optional explicit override (you must pass this flag to allow pruning officials)
if [ "${1-}" = "--allow-official-prune" ]; then
  KEEP_OFFICIAL=0
  shift
fi

echo "[cleanup] start DAYS=$DAYS KEEP_OFFICIAL=$KEEP_OFFICIAL $(date +%F\ %T)" >>"$LOG"

# Build the WHERE guard for officials
if [ "$KEEP_OFFICIAL" = "1" ]; then
  OFFICIAL_GUARD="AND source_tag NOT LIKE 'official%'"
else
  OFFICIAL_GUARD=""  # allow pruning officials
fi

# Compose SQL: delete old, non-evidence docs (respecting official guard), then vacuum
CUTOFF="$(date -u +%s)"
CUTOFF="$(( CUTOFF - DAYS*86400 ))"

SQL="
PRAGMA foreign_keys=ON;

-- collect doomed urls first
WITH doomed AS (
  SELECT url FROM docs
  WHERE ts_utc < $CUTOFF
    $OFFICIAL_GUARD
    AND url NOT IN (SELECT url FROM evidence)
)

DELETE FROM doc_pages     WHERE url IN doomed;
DELETE FROM doc_summaries WHERE url IN doomed;
DELETE FROM docs          WHERE url IN doomed;

-- quick health pass
PRAGMA quick_check;
"

# Run
sqlite3 -cmd ".timeout 4000" "$DB" "$SQL" >>"$LOG" 2>&1 || true

# Light vacuum to reclaim space
sqlite3 "$DB" "VACUUM;" >>"$LOG" 2>&1 || true

echo "[cleanup] done $(date +%F\ %T)" >>"$LOG"
