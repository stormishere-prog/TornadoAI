#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="/storage/emulated/0/Download/TornadoAI"
LOG="$ROOT/harvester.log"
mkdir -p "$ROOT/reports"

echo "[post_ingest] tagging sources…" >>"$LOG"
sh ./safe_run.sh python3 tag_sources.py >>"$LOG" 2>&1 || true

echo "[post_ingest] building echo clusters…" >>"$LOG"
sh ./safe_run.sh python3 echo_cluster.py >>"$LOG" 2>&1 || true

echo "[post_ingest] scanning contradictions…" >>"$LOG"
sh ./safe_run.sh python3 contradiction_scan.py >>"$LOG" 2>&1 || true

# ---- Reports (TSV) ----

# Echo duplicates
sqlite3 -tabs -noheader "$ROOT/corpus.db" "
WITH g AS (
  SELECT canon, COUNT(*) AS n
  FROM echo_edges GROUP BY canon
  HAVING n > 1
)
SELECT g.n AS dupes, g.canon,
       (SELECT root_url FROM echo_clusters ec WHERE ec.canon=g.canon) AS example
FROM g
ORDER BY g.n DESC, g.canon
LIMIT 200;
" > "$ROOT/reports/echo_dupes.tsv" || true

# Contradictions  (alias as 'ts', not 'when')
sqlite3 -tabs -noheader "$ROOT/corpus.db" "
SELECT substr(a_url,1,120) AS a,
       substr(b_url,1,120) AS b,
       reason,
       datetime(ts_utc,'unixepoch') AS ts
FROM contradictions
ORDER BY ts_utc DESC
LIMIT 200;
" > "$ROOT/reports/contradictions.tsv" || true

# Propaganda (only if column exists)
HAS_PROP=`sqlite3 "$ROOT/corpus.db" "SELECT 1 FROM pragma_table_info('doc_pages') WHERE name='propaganda_score' LIMIT 1;"`
if [ "$HAS_PROP" = "1" ]; then
  sqlite3 -tabs -noheader "$ROOT/corpus.db" "
  WITH p AS (
    SELECT url, MAX(COALESCE(propaganda_score,0.0)) AS max_score
    FROM doc_pages GROUP BY url
  )
  SELECT printf('%.2f',p.max_score) AS score,
         IFNULL(d.title,''), d.url
  FROM p JOIN docs d USING(url)
  ORDER BY p.max_score DESC, d.ts_utc DESC
  LIMIT 200;
  " > "$ROOT/reports/propaganda.tsv" || true
fi

# Confidence buckets by source_tag
sqlite3 -tabs -noheader "$ROOT/corpus.db" "
WITH ranked AS (
  SELECT
    CASE
      WHEN source_tag LIKE 'official%'     THEN 0.85
      WHEN source_tag LIKE 'independent%'  THEN 0.65
      WHEN source_tag LIKE 'state_media%'  THEN 0.45
      WHEN source_tag LIKE 'propaganda_%'  THEN 0.25
      ELSE 0.50
    END AS trust_score,
    CASE
      WHEN source_tag LIKE 'official%'     THEN 'official'
      WHEN source_tag LIKE 'independent%'  THEN 'independent'
      WHEN source_tag LIKE 'state_media%'  THEN 'state_media'
      WHEN source_tag LIKE 'propaganda_%'  THEN 'propaganda'
      ELSE 'unknown'
    END AS bucket,
    IFNULL(title,'' ) AS title,
    url,
    ts_utc
  FROM docs
)
SELECT printf('%.2f',trust_score) AS trust,
       bucket,
       substr(title,1,120),
       url
FROM ranked
ORDER BY ts_utc DESC
LIMIT 300;
" > "$ROOT/reports/confidence.tsv" || true
