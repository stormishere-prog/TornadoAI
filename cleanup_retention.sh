#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="/storage/emulated/0/Download/TornadoAI"
DB="$ROOT/corpus.db"
REP="$ROOT/reports"
TMP="$ROOT/tmp"; mkdir -p "$TMP" "$REP"

DAYS="${1:-90}"                    # how many days to keep (default 90)
KEEP_OFFICIAL="${KEEP_OFFICIAL:-1}"# 1 = keep official% sources; 0 = allow deletion
SECS=$((DAYS*86400))
STAMP="$(date +%Y%m%d-%H%M%S)"
SQL="$TMP/retention.$STAMP.sql"

# Preview + delete plan, cascades children then docs
cat > "$SQL" <<SQL
PRAGMA foreign_keys=ON;
BEGIN IMMEDIATE;

-- collect deletion candidates
CREATE TEMP TABLE dels(url TEXT PRIMARY KEY);

INSERT OR IGNORE INTO dels(url)
SELECT url
FROM docs
WHERE ts_utc < strftime('%s','now') - $SECS
  AND url NOT IN (SELECT DISTINCT url FROM evidence)                -- protect evidence
  AND ($KEEP_OFFICIAL=0 OR IFNULL(source_tag,'') NOT LIKE 'official%'); -- optionally protect official

-- write preview rows to a temp table we can SELECT after deletes too
CREATE TEMP TABLE dels_preview AS
SELECT d.url, IFNULL(d.title,'') AS title, d.ts_utc
FROM docs d JOIN dels x ON x.url=d.url;

-- purge children first
DELETE FROM doc_pages       WHERE url IN (SELECT url FROM dels);
DELETE FROM doc_summaries   WHERE url IN (SELECT url FROM dels);
DELETE FROM echo_edges      WHERE url IN (SELECT url FROM dels);
DELETE FROM contradictions  WHERE a_url IN (SELECT url FROM dels) OR b_url IN (SELECT url FROM dels);

-- finally purge docs
DELETE FROM docs WHERE url IN (SELECT url FROM dels);

COMMIT;

-- quick check
PRAGMA quick_check;
SQL

# Run with a safe wrapper (takes backup before changes)
sh ./safe_run.sh sqlite3 "$DB" < "$SQL" >/dev/null 2>&1 || true

# Export report TSVs
# Deleted list (url, title, ts)
sh ./safe_run.sh sqlite3 "$DB" "
.mode tabs
.headers off
SELECT strftime('%Y-%m-%d %H:%M:%S', ts_utc, 'unixepoch') AS deleted_ts,
       title, url
FROM dels_preview
ORDER BY ts_utc;
" > "$REP/retention_deleted.$STAMP.tsv" || true

# Counts summary
sh ./safe_run.sh sqlite3 "$DB" "
.mode tabs
.headers off
WITH c AS (
  SELECT COUNT(*) AS n FROM dels_preview
)
SELECT 'deleted_rows', n FROM c
UNION ALL
SELECT 'docs_now', COUNT(*) FROM docs
UNION ALL
SELECT 'pages_now', COUNT(*) FROM doc_pages;
" > "$REP/retention_summary.$STAMP.tsv" || true

# Compact database
sh ./safe_run.sh sqlite3 "$DB" "PRAGMA wal_checkpoint(FULL); VACUUM;" >/dev/null 2>&1 || true

echo "[retention] ok: kept last $DAYS days | report: $REP/retention_summary.$STAMP.tsv"
