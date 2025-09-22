#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="/storage/emulated/0/Download/TornadoAI"
DB="$ROOT/corpus.db"
OUTDIR="$ROOT/reports/daily"
mkdir -p "$OUTDIR"

DAY="$(date +%F)"
OUT="$OUTDIR/$DAY.md"

since_secs="$(date -d 'now -1 day' +%s 2>/dev/null || busybox date -D '%Y-%m-%d %H:%M:%S' -d "$(date -u -d 'now -1 day' +'%Y-%m-%d %H:%M:%S' 2>/dev/null || date -u +'%Y-%m-%d %H:%M:%S')" +%s)"

{
  echo "# Daily Digest – $DAY"
  echo
  echo "Generated: $(date -Is)"
  echo

  echo "## Ingest (last 24h)"
  sqlite3 "$DB" "
    .mode list
    SELECT 'New docs: '||COUNT(*) FROM docs WHERE IFNULL(ts_utc,0) >= $since_secs;
  "
  echo

  echo "## Evidence added (last 24h)"
  sqlite3 "$DB" "
    .headers off
    .mode list
    SELECT 'New evidence: '||COUNT(*) FROM evidence WHERE IFNULL(ts_utc,0) >= $since_secs;
  "
  echo

  echo "## Latest Evidence (10 most recent)"
  echo
  sqlite3 "$DB" "
    .mode tabs
    SELECT
      datetime(e.ts_utc,'unixepoch') as when,
      IFNULL(d.title,'') as title,
      'p.'||IFNULL(e.page_no,1) as page,
      e.url,
      substr(replace(replace(e.quote, char(10), ' '), char(13), ' '),1,220) as snippet
    FROM evidence e
    LEFT JOIN docs d ON d.url=e.url
    WHERE IFNULL(e.ts_utc,0) >= $since_secs
    ORDER BY e.ts_utc DESC
    LIMIT 10;
  " | awk -F '\t' 'BEGIN{print "| When | Title | Page | URL | Snippet |"; print "|---|---|---|---|---|"} {printf("| %s | %s | %s | %s | %s |\n",$1,$2,$3,$4,$5)}'
  echo

  echo "## Propaganda (top 10, last 24h)"
  echo
  sqlite3 "$DB" "
    .mode tabs
    SELECT
      printf('%.2f', p.propaganda_score) as score,
      IFNULL(d.title,'') as title,
      'p.'||IFNULL(p.page_no,1) as page,
      p.url
    FROM propaganda p
    LEFT JOIN docs d ON d.url=p.url
    WHERE IFNULL(p.ts_utc,0) >= $since_secs
    ORDER BY p.propaganda_score DESC
    LIMIT 10;
  " | awk -F '\t' 'BEGIN{print "| Score | Title | Page | URL |"; print "|---:|---|---|---|"} {printf("| %s | %s | %s | %s |\n",$1,$2,$3,$4)}'
  echo
} > "$OUT"

echo "[daily_digest] wrote $OUT"
